import os
import uuid
import time
import httpx
import asyncio
import logging
import urllib.parse
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="selfstream")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

db = Database()

@app.on_event("startup")
async def startup():
    db.init()
    logger.info("selfstream started")


# ── Setup / Auth ──────────────────────────────────────────────────────────────

@app.get("/api/setup/status")
def setup_status():
    return {"setup_done": db.is_setup_done()}

@app.post("/api/setup")
def do_setup(body: dict):
    if db.is_setup_done():
        raise HTTPException(status_code=400, detail="Already configured")
    token = body.get("admin_token", "").strip()
    base_url = body.get("base_url", "").strip().rstrip("/")
    if not token or len(token) < 8:
        raise HTTPException(status_code=400, detail="Token must be at least 8 characters")
    if not base_url:
        raise HTTPException(status_code=400, detail="Base URL required")
    db.set_setting("admin_token", token)
    db.set_setting("base_url", base_url)
    return {"ok": True}

def check_admin(x_admin_token: str = Header(...)):
    admin_token = db.get_admin_token()
    if not admin_token or x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Admin API ─────────────────────────────────────────────────────────────────

@app.get("/api/users")
def list_users(_=Depends(check_admin)):
    return db.get_all_users()

@app.post("/api/users")
def create_user(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    m3u_source = body.get("m3u_source", "").strip()
    notes = body.get("notes", "").strip()
    if not name or not m3u_source:
        raise HTTPException(status_code=400, detail="name and m3u_source required")
    token = str(uuid.uuid4()).replace("-", "")[:24]
    user = db.create_user(name=name, token=token, m3u_source=m3u_source, notes=notes)
    base_url = db.get_base_url()
    return {**user, "playlist_url": f"{base_url}/iptv/{token}/playlist.m3u"}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, _=Depends(check_admin)):
    db.delete_user(user_id)
    return {"ok": True}

@app.put("/api/users/{user_id}")
def update_user(user_id: int, body: dict, _=Depends(check_admin)):
    db.update_user(user_id, body)
    return {"ok": True}

@app.get("/api/users/{user_id}/logs")
def get_user_logs(user_id: int, _=Depends(check_admin)):
    return db.get_user_logs(user_id)

@app.get("/api/logs")
def get_all_logs(limit: int = 200, _=Depends(check_admin)):
    return db.get_all_logs(limit)

@app.get("/api/stats")
def get_stats(_=Depends(check_admin)):
    users = db.get_all_users()
    active_sessions = db.get_active_sessions()
    return {
        "total_users": len(users),
        "active_streams": len(active_sessions),
        "active_sessions": [{"user": s["user_name"], "channel": s["channel"]} for s in active_sessions],
        "watch_logs_today": db.get_logs_today_count(),
    }

@app.get("/api/settings")
def get_settings(_=Depends(check_admin)):
    return {
        "base_url": db.get_base_url(),
    }

@app.post("/api/settings")
def update_settings(body: dict, _=Depends(check_admin)):
    if "base_url" in body:
        db.set_setting("base_url", body["base_url"].strip().rstrip("/"))
    if "admin_token" in body and len(body["admin_token"]) >= 8:
        # Only allow changing DB-stored token (not env-var one)
        if not os.getenv("ADMIN_TOKEN"):
            db.set_setting("admin_token", body["admin_token"])
    return {"ok": True}


# ── IPTV Proxy ────────────────────────────────────────────────────────────────

@app.get("/iptv/{token}/playlist.m3u")
async def serve_playlist(token: str):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(user["m3u_source"])
            resp.raise_for_status()
            original_m3u = resp.text
    except Exception as e:
        logger.error(f"Failed to fetch m3u for {user['name']}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch source playlist")

    base_url = db.get_base_url()
    lines = original_m3u.splitlines()
    rewritten = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            encoded = urllib.parse.quote(stripped, safe="")
            rewritten.append(f"{base_url}/iptv/{token}/stream?url={encoded}")
        else:
            rewritten.append(line)

    db.log_playlist_access(user["id"])
    return HTMLResponse(content="\n".join(rewritten), media_type="application/x-mpegURL")


@app.get("/iptv/{token}/stream")
async def proxy_stream(token: str, url: str):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    decoded_url = urllib.parse.unquote(url)
    channel_name = decoded_url.split("/")[-1].split("?")[0] or decoded_url

    if not db.session_start(token, channel_name):
        raise HTTPException(status_code=409, detail="Stream already active on another device")

    log_id = db.start_watch_log(user_id=user["id"], channel=channel_name, stream_url=decoded_url)
    start_time = time.time()

    async def stream_generator():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10, read=3600)) as client:
                async with client.stream("GET", decoded_url) as resp:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        yield chunk
                        db.session_refresh(token)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Stream error for {user['name']}: {e}")
        finally:
            db.session_end(token)
            duration = int(time.time() - start_time)
            db.end_watch_log(log_id, duration)
            logger.info(f"Stream ended: {user['name']} | '{channel_name}' | {duration}s")

    return StreamingResponse(
        stream_generator(),
        media_type="video/mp2t",
        headers={"Cache-Control": "no-cache"},
    )


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return RedirectResponse(url="/admin")

@app.get("/admin")
async def admin_page():
    with open("/app/frontend/index.html") as f:
        return HTMLResponse(f.read())

@app.get("/setup")
async def setup_page():
    with open("/app/frontend/setup.html") as f:
        return HTMLResponse(f.read())
