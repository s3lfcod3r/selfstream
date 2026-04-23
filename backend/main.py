import os
import uuid
import time
import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from database import Database, User, WatchLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IPTV Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme-admin-secret")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

redis_client: Optional[aioredis.Redis] = None

@app.on_event("startup")
async def startup():
    global redis_client
    db.init()
    redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
    logger.info("IPTV Proxy started")

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.aclose()


# ─── Admin Auth ───────────────────────────────────────────────────────────────

def check_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ─── Admin API ────────────────────────────────────────────────────────────────

@app.get("/api/users")
def list_users(_=Depends(check_admin)):
    return db.get_all_users()

@app.post("/api/users")
def create_user(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    m3u_source = body.get("m3u_source", "").strip()
    if not name or not m3u_source:
        raise HTTPException(status_code=400, detail="name and m3u_source required")
    token = str(uuid.uuid4()).replace("-", "")[:24]
    user = db.create_user(name=name, token=token, m3u_source=m3u_source)
    return {**user, "playlist_url": f"{BASE_URL}/iptv/{token}/playlist.m3u"}

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
async def get_stats(_=Depends(check_admin)):
    users = db.get_all_users()
    active_sessions = []
    for user in users:
        key = f"stream:{user['token']}"
        val = await redis_client.get(key)
        if val:
            active_sessions.append({"user": user["name"], "channel": val})
    return {
        "total_users": len(users),
        "active_streams": len(active_sessions),
        "active_sessions": active_sessions,
        "watch_logs_today": db.get_logs_today_count(),
    }

# ─── IPTV Proxy Routes ────────────────────────────────────────────────────────

@app.get("/iptv/{token}/playlist.m3u")
async def serve_playlist(token: str, request: Request):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    m3u_url = user["m3u_source"]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(m3u_url)
            resp.raise_for_status()
            original_m3u = resp.text
    except Exception as e:
        logger.error(f"Failed to fetch m3u for user {user['name']}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch source playlist")

    # Rewrite stream URLs to go through our proxy
    lines = original_m3u.splitlines()
    rewritten = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            import urllib.parse
            encoded = urllib.parse.quote(stripped, safe="")
            rewritten.append(f"{BASE_URL}/iptv/{token}/stream?url={encoded}")
        else:
            rewritten.append(line)

    content = "\n".join(rewritten)
    db.log_playlist_access(user["id"])
    return HTMLResponse(content=content, media_type="application/x-mpegURL")


@app.get("/iptv/{token}/stream")
async def proxy_stream(token: str, url: str, request: Request):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    session_key = f"stream:{token}"
    stream_id = str(uuid.uuid4())

    # Concurrent stream check
    existing = await redis_client.get(session_key)
    if existing:
        raise HTTPException(status_code=409, detail="Stream already active on another device")

    import urllib.parse
    decoded_url = urllib.parse.unquote(url)

    # Extract channel name from URL (best effort)
    channel_name = decoded_url.split("/")[-1].split("?")[0] or decoded_url

    # Set active session (TTL 4h, refreshed by heartbeat)
    await redis_client.setex(session_key, 14400, channel_name)

    log_id = db.start_watch_log(user_id=user["id"], channel=channel_name, stream_url=decoded_url)
    start_time = time.time()

    async def stream_generator():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10, read=3600)) as client:
                async with client.stream("GET", decoded_url) as resp:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        yield chunk
                        # Refresh TTL on active streaming
                        await redis_client.expire(session_key, 14400)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Stream error for {user['name']}: {e}")
        finally:
            await redis_client.delete(session_key)
            duration = int(time.time() - start_time)
            db.end_watch_log(log_id, duration)
            logger.info(f"Stream ended: {user['name']} watched '{channel_name}' for {duration}s")

    return StreamingResponse(
        stream_generator(),
        media_type="video/mp2t",
        headers={
            "Cache-Control": "no-cache",
            "X-User": user["name"],
        }
    )


# ─── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return RedirectResponse(url="/admin")

@app.get("/admin")
async def admin_page():
    with open("/app/frontend/index.html") as f:
        return HTMLResponse(f.read())
