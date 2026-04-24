import os
import uuid
import time
import httpx
import asyncio
import logging
import urllib.parse
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse

from database import Database
from m3u_parser import parse_m3u, build_m3u

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

proxy_app = FastAPI(title="selfstream proxy")
admin_app = FastAPI(title="selfstream admin")

for a in (proxy_app, admin_app):
    a.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                     allow_methods=["*"], allow_headers=["*"])

db = Database()

@proxy_app.on_event("startup")
@admin_app.on_event("startup")
async def startup():
    db.init()
    logger.info("selfstream started")


def get_hls_settings() -> dict:
    return {
        "hls_timeout":        int(db.get_setting("hls_timeout", "10")),
        "hls_read_timeout":   int(db.get_setting("hls_read_timeout", "30")),
        "hls_chunk_size":     int(db.get_setting("hls_chunk_size", "65536")),
        "hls_user_agent":     db.get_setting("hls_user_agent", "VLC/3.0 LibVLC/3.0"),
        "hls_referer":        db.get_setting("hls_referer", ""),
        "hls_follow_redirects": db.get_setting("hls_follow_redirects", "1") == "1",
    }


def make_headers(hls: dict) -> dict:
    h = {"User-Agent": hls["hls_user_agent"]}
    if hls["hls_referer"]:
        h["Referer"] = hls["hls_referer"]
    return h


def rewrite_hls_playlist(content: str, original_url: str, proxy_base: str, token: str) -> str:
    """
    Rewrite a .m3u8 playlist so all segment/sub-playlist URLs
    go through our proxy instead of directly to the CDN.
    """
    base = original_url.rsplit("/", 1)[0] + "/"
    lines = content.splitlines()
    out = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            out.append(line)
            continue
        if not stripped:
            out.append(line)
            continue

        # Resolve relative URLs to absolute
        if stripped.startswith("http"):
            abs_url = stripped
        else:
            abs_url = base + stripped

        # Proxy the segment/sub-playlist through us
        encoded = urllib.parse.quote(abs_url, safe="")
        out.append(f"{proxy_base}/iptv/{token}/segment?url={encoded}")

    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# PROXY APP  (port 8000)
# ══════════════════════════════════════════════════════════════════════════════

@proxy_app.get("/iptv/{token}/playlist.m3u")
@proxy_app.get("/iptv/{token}/playlist.m3u8")
async def serve_playlist(token: str):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    channels = db.get_channels(enabled_only=True)
    proxy_url = db.get_proxy_url()
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]

    if not channels:
        # Fallback: fetch from user's m3u_source
        try:
            hls = get_hls_settings()
            async with httpx.AsyncClient(timeout=30, headers=make_headers(hls)) as client:
                resp = await client.get(user["m3u_source"])
                resp.raise_for_status()
                channels_raw = parse_m3u(resp.text)
        except Exception as e:
            logger.error(f"Failed to fetch m3u for {user['name']}: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch source playlist")
        channels = [{"name": c["name"], "raw_extinf": c["raw_extinf"],
                     "stream_url": c["url"], "tvg_id": c["tvg_id"],
                     "tvg_logo": c["tvg_logo"], "group_title": c["group"]} for c in channels_raw]

    content = build_m3u(channels, proxy_url, token, epg_sources)
    db.log_playlist_access(user["id"])
    return HTMLResponse(content=content, media_type="application/x-mpegURL")


@proxy_app.get("/iptv/{token}/epg.xml")
async def serve_epg(token: str):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]
    if not epg_sources:
        raise HTTPException(status_code=404, detail="No EPG source configured")
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(epg_sources[0])
            resp.raise_for_status()
            return HTMLResponse(content=resp.text, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"EPG fetch failed: {e}")


@proxy_app.get("/iptv/{token}/stream")
async def proxy_stream(token: str, url: str):
    """
    Entry point for a channel. Fetches the .m3u8, rewrites segment URLs,
    returns the rewritten playlist so the client fetches segments via /segment.
    No session lock here – session starts only when first .ts segment is fetched.
    """
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    decoded_url = urllib.parse.unquote(url)
    channel_name = decoded_url.split("/")[-2] if "/ch" in decoded_url else decoded_url.split("/")[-1].split("?")[0]

    hls = get_hls_settings()
    proxy_url = db.get_proxy_url()

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"]),
            follow_redirects=hls["hls_follow_redirects"],
            headers=make_headers(hls)
        ) as client:
            resp = await client.get(decoded_url)
            resp.raise_for_status()
            content = resp.text

        rewritten = rewrite_hls_playlist(content, decoded_url, proxy_url, token)
        logger.info(f"HLS playlist served: {user["name"]} → {channel_name}")
        return HTMLResponse(content=rewritten, media_type="application/vnd.apple.mpegurl")

    except Exception as e:
        logger.error(f"Failed to fetch stream for {user["name"]}: {e}")
        raise HTTPException(status_code=502, detail=f"Stream fetch failed: {e}")


# In-memory store for active segment sessions {token: (channel, log_id, start_time)}
_active_segment_sessions: dict = {}

@proxy_app.get("/iptv/{token}/segment")
async def proxy_segment(token: str, url: str):
    """
    Proxy individual HLS segments (.ts) or sub-playlists.
    Session starts on first real .ts segment, refreshes on subsequent ones.
    """
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    decoded_url = urllib.parse.unquote(url)
    hls = get_hls_settings()
    proxy_url = db.get_proxy_url()
    is_ts = not (decoded_url.endswith(".m3u8") or "m3u8" in decoded_url.split("?")[0])

    if is_ts:
        # Extract channel from URL e.g. /ch265/2026/...
        parts = decoded_url.split("/")
        ch_idx = next((i for i, p in enumerate(parts) if p.startswith("ch")), None)
        channel_name = parts[ch_idx] if ch_idx else parts[-1].split("?")[0]

        existing = _active_segment_sessions.get(token)
        if existing and existing[0] != channel_name:
            # Channel switched – end old session silently
            _, old_log_id, old_start = _active_segment_sessions.pop(token)
            db.session_end(token)
            db.end_watch_log(old_log_id, int(time.time() - old_start))
            logger.info(f"Channel switch: {user['name']} → {channel_name}")

        if token not in _active_segment_sessions:
            # New session – just start it (no blocking, one stream per token tracked)
            db.session_start(token, channel_name)  # non-blocking, overwrites any stale
            log_id = db.start_watch_log(user_id=user["id"], channel=channel_name, stream_url=decoded_url)
            _active_segment_sessions[token] = (channel_name, log_id, time.time())
            logger.info(f"Session started: {user['name']} → {channel_name}")
        else:
            db.session_refresh(token)

    async def stream_segment():
        try:
            timeout = httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"])
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=hls["hls_follow_redirects"],
                headers=make_headers(hls)
            ) as client:
                if not is_ts:
                    # Sub-playlist (quality levels etc.) – rewrite and return
                    resp = await client.get(decoded_url)
                    resp.raise_for_status()
                    rewritten = rewrite_hls_playlist(resp.text, decoded_url, proxy_url, token)
                    yield rewritten.encode()
                else:
                    # Binary segment (.ts, .aac, etc.)
                    async with client.stream("GET", decoded_url) as resp:
                        async for chunk in resp.aiter_bytes(chunk_size=hls["hls_chunk_size"]):
                            yield chunk
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Segment error: {e}")
            # End session on persistent error
            if token in _active_segment_sessions:
                _, log_id, start_time = _active_segment_sessions.pop(token)
                db.session_end(token)
                db.end_watch_log(log_id, int(time.time() - start_time))

    media_type = "application/vnd.apple.mpegurl" if not is_ts else "video/mp2t"
    return StreamingResponse(stream_segment(), media_type=media_type,
                             headers={"Cache-Control": "no-cache"})


@proxy_app.get("/iptv/{token}/stop")
async def stop_stream(token: str):
    """Manually end a session."""
    if token in _active_segment_sessions:
        _, log_id, start_time = _active_segment_sessions.pop(token)
        db.end_watch_log(log_id, int(time.time() - start_time))
    db.session_end(token)
    return {"ok": True}


@proxy_app.get("/")
async def proxy_root():
    return JSONResponse({"service": "selfstream proxy", "status": "ok"})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN APP  (port 8080)
# ══════════════════════════════════════════════════════════════════════════════

@admin_app.get("/api/setup/status")
def setup_status():
    return {"setup_done": db.is_setup_done()}

@admin_app.post("/api/setup")
def do_setup(body: dict):
    if db.is_setup_done():
        raise HTTPException(status_code=400, detail="Already configured")
    token = body.get("admin_token", "").strip()
    base_url = body.get("base_url", "").strip().rstrip("/")
    proxy_url = body.get("proxy_url", "").strip().rstrip("/")
    if not token or len(token) < 8:
        raise HTTPException(status_code=400, detail="Token must be at least 8 characters")
    if not base_url:
        raise HTTPException(status_code=400, detail="Base URL required")
    db.set_setting("admin_token", token)
    db.set_setting("base_url", base_url)
    if proxy_url:
        db.set_setting("proxy_url", proxy_url)
    return {"ok": True}

def check_admin(x_admin_token: str = Header(...)):
    admin_token = db.get_admin_token()
    if not admin_token or x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

@admin_app.get("/api/users")
def list_users(_=Depends(check_admin)):
    users = db.get_all_users()
    proxy_url = db.get_proxy_url()
    for u in users:
        u["playlist_url"] = f"{proxy_url}/iptv/{u['token']}/playlist.m3u"
        u["epg_url"] = f"{proxy_url}/iptv/{u['token']}/epg.xml"
    return users

@admin_app.post("/api/users")
def create_user(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    notes = body.get("notes", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    m3u_source = db.get_setting("source_m3u_url", "")
    token = str(uuid.uuid4()).replace("-", "")[:24]
    user = db.create_user(name=name, token=token, m3u_source=m3u_source, notes=notes)
    proxy_url = db.get_proxy_url()
    return {**user,
            "playlist_url": f"{proxy_url}/iptv/{token}/playlist.m3u",
            "epg_url": f"{proxy_url}/iptv/{token}/epg.xml"}

@admin_app.delete("/api/users/{user_id}")
def delete_user(user_id: int, _=Depends(check_admin)):
    db.delete_user(user_id)
    return {"ok": True}

@admin_app.put("/api/users/{user_id}")
def update_user(user_id: int, body: dict, _=Depends(check_admin)):
    db.update_user(user_id, body)
    return {"ok": True}

@admin_app.get("/api/users/{user_id}/logs")
def get_user_logs(user_id: int, _=Depends(check_admin)):
    return db.get_user_logs(user_id)

@admin_app.get("/api/channels")
def list_channels(group: str = None, _=Depends(check_admin)):
    channels = db.get_channels()
    if group:
        channels = [c for c in channels if c["group_title"] == group]
    return channels

@admin_app.get("/api/channels/groups")
def list_groups(_=Depends(check_admin)):
    return db.get_channel_groups()

@admin_app.get("/api/channels/stats")
def channel_stats(_=Depends(check_admin)):
    return db.get_channels_count()

@admin_app.put("/api/channels/{channel_id}")
def update_channel(channel_id: int, body: dict, _=Depends(check_admin)):
    db.update_channel(channel_id, body)
    return {"ok": True}

@admin_app.post("/api/channels/group-toggle")
def toggle_group(body: dict, _=Depends(check_admin)):
    db.set_group_enabled(body.get("group", ""), int(body.get("enabled", 1)))
    return {"ok": True}

@admin_app.post("/api/channels/import")
async def import_channels(body: dict, _=Depends(check_admin)):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    db.set_setting("source_m3u_url", url)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            channels = parse_m3u(resp.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch M3U: {e}")
    db.upsert_channels(channels)
    return {"ok": True, "imported": len(channels)}

@admin_app.post("/api/channels/refresh")
async def refresh_channels(_=Depends(check_admin)):
    url = db.get_setting("source_m3u_url", "")
    if not url:
        raise HTTPException(status_code=400, detail="No source URL saved.")
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            channels = parse_m3u(resp.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Refresh failed: {e}")
    db.upsert_channels(channels)
    return {"ok": True, "imported": len(channels)}

@admin_app.get("/api/epg")
def list_epg(_=Depends(check_admin)):
    return db.get_epg_sources()

@admin_app.post("/api/epg")
def add_epg(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    url = body.get("url", "").strip()
    if not name or not url:
        raise HTTPException(status_code=400, detail="name and url required")
    return db.add_epg_source(name, url)

@admin_app.put("/api/epg/{epg_id}")
def update_epg(epg_id: int, body: dict, _=Depends(check_admin)):
    db.update_epg_source(epg_id, body)
    return {"ok": True}

@admin_app.delete("/api/epg/{epg_id}")
def delete_epg(epg_id: int, _=Depends(check_admin)):
    db.delete_epg_source(epg_id)
    return {"ok": True}

@admin_app.get("/api/stats")
def get_stats(_=Depends(check_admin)):
    users = db.get_all_users()
    active_sessions = db.get_active_sessions()
    ch_stats = db.get_channels_count()
    return {
        "total_users": len(users),
        "active_streams": len(active_sessions),
        "active_sessions": [{"user": s["user_name"], "channel": s["channel"]} for s in active_sessions],
        "watch_logs_today": db.get_logs_today_count(),
        "total_channels": ch_stats["total"] or 0,
        "enabled_channels": ch_stats["enabled"] or 0,
    }

@admin_app.get("/api/logs")
def get_all_logs(limit: int = 200, _=Depends(check_admin)):
    return db.get_all_logs(limit)

@admin_app.get("/api/settings")
def get_settings(_=Depends(check_admin)):
    s = db.get_all_settings()
    return {
        "base_url":             s.get("base_url", ""),
        "proxy_url":            s.get("proxy_url", ""),
        "source_m3u_url":       s.get("source_m3u_url", ""),
        "hls_timeout":          s.get("hls_timeout", "10"),
        "hls_read_timeout":     s.get("hls_read_timeout", "30"),
        "hls_chunk_size":       s.get("hls_chunk_size", "65536"),
        "hls_user_agent":       s.get("hls_user_agent", "VLC/3.0 LibVLC/3.0"),
        "hls_referer":          s.get("hls_referer", ""),
        "hls_follow_redirects": s.get("hls_follow_redirects", "1"),
    }

@admin_app.post("/api/settings")
def update_settings(body: dict, _=Depends(check_admin)):
    allowed = {"base_url", "proxy_url", "source_m3u_url",
               "hls_timeout", "hls_read_timeout", "hls_chunk_size",
               "hls_user_agent", "hls_referer", "hls_follow_redirects"}
    for key, val in body.items():
        if key in allowed:
            db.set_setting(key, str(val))
    return {"ok": True}

@admin_app.post("/api/settings/change-password")
def change_password(body: dict, _=Depends(check_admin)):
    new_token = body.get("new_token", "").strip()
    if len(new_token) < 8:
        raise HTTPException(status_code=400, detail="Min 8 characters")
    if os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=400, detail="Password set via environment variable")
    db.set_setting("admin_token", new_token)
    return {"ok": True}

FRONTEND = "/app/frontend"

@admin_app.get("/")
async def root():
    return RedirectResponse(url="/admin")

@admin_app.get("/admin")
async def admin_page():
    with open(f"{FRONTEND}/index.html") as f:
        return HTMLResponse(f.read())

@admin_app.get("/setup")
async def setup_page():
    with open(f"{FRONTEND}/setup.html") as f:
        return HTMLResponse(f.read())

@admin_app.get("/logo.png")
async def logo():
    from fastapi.responses import FileResponse
    return FileResponse(f"{FRONTEND}/logo.png", media_type="image/png")
