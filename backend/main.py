import os
import uuid
import time
import httpx
import asyncio
import logging
import urllib.parse
import re
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from database import Database
from m3u_parser import parse_m3u, build_m3u

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    _generate_error_video()
    logger.info("selfstream started")


def _generate_error_video():
    """Generate error video .ts files using FFmpeg, with Pillow as fallback."""
    import subprocess, shutil

    def _make_with_ffmpeg(out_ts, title, subtitle, sub2, color_hex):
        """Generate a 10s looping error video with text using FFmpeg."""
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return False
        logo_path = "/data/custom_login_logo.png"
        if not os.path.exists(logo_path):
            logo_path = "/app/frontend/logo.png"

        # Build drawtext filter
        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

        drawtext = (
            f"drawtext=fontfile={font}:text='{title}':"
            f"fontcolor={color_hex}:fontsize=52:x=(w-text_w)/2:y=490,"
            f"drawtext=fontfile={font_reg}:text='{subtitle}':"
            f"fontcolor=0xB4BEC8:fontsize=26:x=(w-text_w)/2:y=556,"
            f"drawtext=fontfile={font_reg}:text='{sub2}':"
            f"fontcolor=0x8B949E:fontsize=20:x=(w-text_w)/2:y=596"
        )

        # Check if logo exists and has transparency
        overlay_filter = ""
        if os.path.exists(logo_path):
            overlay_filter = f"[0:v][1:v]overlay=(W-w)/2:45[bg];[bg]"
            inputs = ["-f", "lavfi", "-i", f"color=c=0x0D1117:size=1280x720:rate=25",
                     "-i", logo_path]
            vf = f"{overlay_filter}{drawtext}"
        else:
            inputs = ["-f", "lavfi", "-i", f"color=c=0x0D1117:size=1280x720:rate=25"]
            vf = drawtext

        cmd = [ffmpeg, "-y"] + inputs + [
            "-vf", vf,
            "-t", "10",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-an", "-f", "mpegts", out_ts
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode == 0 and os.path.exists(out_ts):
                logger.info(f"FFmpeg error video generated: {out_ts}")
                return True
            else:
                logger.warning(f"FFmpeg failed: {result.stderr.decode()[:300]}")
                return False
        except Exception as e:
            logger.warning(f"FFmpeg error: {e}")
            return False

    def _make_with_pillow(out_jpg, title, subtitle, sub2, accent):
        """Fallback: generate JPEG with Pillow."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            BG = (13, 17, 23)
            img = Image.new("RGB", (1280, 720), BG)
            draw = ImageDraw.Draw(img)
            logo_path = "/data/custom_login_logo.png"
            if not os.path.exists(logo_path):
                logo_path = "/app/frontend/logo.png"
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo.thumbnail((220, 236), Image.LANCZOS)
                data = logo.load()
                for y in range(logo.height):
                    for x in range(logo.width):
                        r,g,b,a = data[x,y]
                        if r<35 and g<42 and b<50: data[x,y]=(r,g,b,0)
                img.paste(logo, ((1280-logo.width)//2, 45), logo)
            except Exception: pass
            cx, cy = 640, 385
            if accent == (248,81,73):
                draw.ellipse([cx-85,cy-85,cx+85,cy+85], outline=accent, width=8)
                draw.rectangle([cx-40,cy-40,cx+40,cy+40], fill=accent)
            else:
                draw.rounded_rectangle([cx-52,cy-12,cx+52,cy+68], radius=10, fill=accent)
                draw.arc([cx-37,cy-68,cx+37,cy+28], start=180, end=0, fill=accent, width=11)
                draw.ellipse([cx-13,cy+10,cx+13,cy+36], fill=BG)
                draw.rectangle([cx-7,cy+23,cx+7,cy+52], fill=BG)
            try:
                fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
                fm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
                fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            except: fb = fm = fs = ImageFont.load_default()
            for font, text, y, color in [
                (fb, title, 492, accent),
                (fm, subtitle, 556, (180,190,200)),
                (fs, sub2, 596, (139,148,158)),
            ]:
                bb = draw.textbbox((0,0), text, font=font)
                draw.text(((1280-(bb[2]-bb[0]))//2, y), text, font=font, fill=color)
            draw.rectangle([16,16,1264,704], outline=(30,40,55), width=2)
            img.save(out_jpg, "JPEG", quality=90)
            logger.info(f"Pillow error image generated: {out_jpg}")
            return True
        except Exception as e:
            logger.warning(f"Pillow error: {e}")
            return False

    # Generate max-streams error
    ts_path = "/data/error-max-streams.ts"
    jpg_path = "/data/error-max-streams.jpg"
    if not _make_with_ffmpeg(ts_path,
            "Max. Streams erreicht",
            "Bitte beende einen anderen Stream und versuche es erneut.",
            f"Neue Verbindung moeglich nach ca. {SESSION_MEM_TTL} Sekunden.",
            "0xF85149"):
        _make_with_pillow(jpg_path, "Max. Streams erreicht",
            "Bitte beende einen anderen Stream und versuche es erneut.",
            f"Neue Verbindung moeglich nach ca. {SESSION_MEM_TTL} Sekunden.",
            (248,81,73))

    # Generate banned error
    ban_ts = "/data/error-banned.ts"
    ban_jpg = "/data/error-banned.jpg"
    if not _make_with_ffmpeg(ban_ts,
            "Zugang gesperrt",
            "Dein Zugang wurde vom Administrator deaktiviert.",
            "Bitte wende dich an den Administrator.",
            "0xD29922"):
        _make_with_pillow(ban_jpg, "Zugang gesperrt",
            "Dein Zugang wurde vom Administrator deaktiviert.",
            "Bitte wende dich an den Administrator.",
            (210,153,34))


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
    base = original_url.rsplit("/", 1)[0] + "/"
    lines = content.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped == "#EXT-X-ENDLIST":
            continue
        if stripped.startswith("#"):
            out.append(line)
            continue
        if not stripped:
            out.append(line)
            continue
        if stripped.startswith("http"):
            abs_url = stripped
        else:
            abs_url = base + stripped
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
                     "tvg_logo": c["tvg_logo"], "group_title": c["group"],
                     "tvg_rec": c.get("tvg_rec", "")} for c in channels_raw]

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


@proxy_app.get("/iptv/error-stream.jpg")
async def error_stream_jpg():
    from fastapi.responses import FileResponse, Response
    jpg_path = "/data/error-max-streams.jpg"
    if os.path.exists(jpg_path):
        return FileResponse(jpg_path, media_type="image/jpeg")
    return Response(content=b"", media_type="image/jpeg")

@proxy_app.get("/iptv/error-banned.jpg")
async def error_banned_jpg():
    from fastapi.responses import FileResponse, Response
    jpg_path = "/data/error-banned.jpg"
    if os.path.exists(jpg_path):
        return FileResponse(jpg_path, media_type="image/jpeg")
    return Response(content=b"", media_type="image/jpeg")

@proxy_app.get("/iptv/error-max-streams.m3u8")
async def error_max_streams_m3u8():
    """HLS playlist for max-streams error video."""
    from fastapi.responses import Response
    proxy_url = db.get_proxy_url()
    # Use .ts if FFmpeg generated it, else fallback to jpg
    ts_path = "/data/error-max-streams.ts"
    if os.path.exists(ts_path):
        seg_url = f"{proxy_url}/iptv/error-max-streams.ts"
    else:
        seg_url = f"{proxy_url}/iptv/error-stream.jpg"
    m3u8 = (
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n"
        "#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n"
        f"#EXTINF:10.0,\n{seg_url}\n"
        f"#EXTINF:10.0,\n{seg_url}\n"
        f"#EXTINF:10.0,\n{seg_url}\n"
        "#EXT-X-ENDLIST\n"
    )
    return Response(content=m3u8, media_type="application/x-mpegURL")

@proxy_app.get("/iptv/error-max-streams.ts")
async def error_max_streams_ts():
    from fastapi.responses import FileResponse, Response
    ts_path = "/data/error-max-streams.ts"
    if os.path.exists(ts_path):
        return FileResponse(ts_path, media_type="video/mp2t")
    return Response(content=b"", media_type="video/mp2t")

@proxy_app.get("/iptv/error-banned.m3u8")
async def error_banned_m3u8():
    from fastapi.responses import Response
    proxy_url = db.get_proxy_url()
    ts_path = "/data/error-banned.ts"
    if os.path.exists(ts_path):
        seg_url = f"{proxy_url}/iptv/error-banned.ts"
    else:
        seg_url = f"{proxy_url}/iptv/error-banned.jpg"
    m3u8 = (
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n"
        "#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n"
        f"#EXTINF:10.0,\n{seg_url}\n"
        f"#EXTINF:10.0,\n{seg_url}\n"
        f"#EXTINF:10.0,\n{seg_url}\n"
        "#EXT-X-ENDLIST\n"
    )
    return Response(content=m3u8, media_type="application/x-mpegURL")

@proxy_app.get("/iptv/error-banned.ts")
async def error_banned_ts():
    from fastapi.responses import FileResponse, Response
    ts_path = "/data/error-banned.ts"
    if os.path.exists(ts_path):
        return FileResponse(ts_path, media_type="video/mp2t")
    return Response(content=b"", media_type="video/mp2t")


@proxy_app.get("/iptv/error-max-streams.png")
async def error_image():
    """Serves a PNG error image for max streams reached."""
    import base64
    # Simple PNG with error message (generated SVG-as-PNG fallback)
    error_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stream gesperrt</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0e15;display:flex;align-items:center;justify-content:center;
  min-height:100vh;font-family:'Segoe UI',Arial,sans-serif;
  background-image:radial-gradient(ellipse 80% 60% at 50% 30%,rgba(248,81,73,.08) 0%,transparent 70%);}
.box{text-align:center;padding:48px 32px;max-width:480px;}
.logo{width:160px;height:auto;margin-bottom:28px;
  filter:drop-shadow(0 0 24px rgba(0,229,200,.35));}
.icon{font-size:56px;margin-bottom:16px;display:block;}
h1{color:#f85149;font-size:24px;font-weight:700;margin:0 0 12px;letter-spacing:-.01em;}
.sub{color:#8b949e;font-size:14px;line-height:1.6;margin-bottom:24px;}
.badge{display:inline-flex;align-items:center;gap:8px;
  background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.25);
  color:#f85149;padding:10px 20px;font-size:11px;letter-spacing:.12em;
  font-family:monospace;text-transform:uppercase;}
</style>
</head>
<body>
<div class="box">
  <img class="logo" src="data:image/png;base64,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y8WhBaN0S5vJ3eYy1zlL+o6lzc1HOcm395b+CWyXxHxgGHoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH//2Q==" alt="selfstream">
  <span class="icon">⛔</span>
  <h1>Stream nicht verfügbar</h1>
  <p class="sub">
    Die maximale Anzahl gleichzeitiger Streams wurde erreicht.<br>
    Bitte beende einen anderen Stream und versuche es erneut.
  </p>
  <div class="badge">MAX STREAMS ERREICHT</div>
</div>
</body>
</html>"""
    return HTMLResponse(content=error_html, media_type="text/html")


@proxy_app.get("/iptv/{token}/stream")
async def proxy_stream(token: str, url: str, utc: str = None, lutc: str = None, request: Request = None):
    """
    Entry point for a channel.
    - Normal mode: fetches live .m3u8 and rewrites segment URLs
    - Catchup mode (utc param): builds archive playlist from timestamp
    """
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid token")

    if not user["active"]:
        # User is banned – return error image M3U
        proxy_url = db.get_proxy_url()
        banned_url = f"{proxy_url}/iptv/error-banned.jpg"
        banned_m3u = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:10.0,\n" + banned_url + "\n#EXT-X-ENDLIST\n"
        return HTMLResponse(content=banned_m3u, media_type="application/x-mpegURL",
                           headers={"Cache-Control": "no-cache"})

    decoded_url = urllib.parse.unquote(url)
    hls = get_hls_settings()
    proxy_url = db.get_proxy_url()

    # Get friendly channel name from DB
    ch_record = db.get_channel_by_url(decoded_url)
    channel_name = ch_record["name"] if ch_record else (
        decoded_url.split("/")[-2] if "/ch" in decoded_url else decoded_url.split("/")[-1].split("?")[0]
    )

    # ── CHECK MAX STREAMS
    max_s = user.get("max_streams", 1) or 0
    if max_s > 0:
        import time as _t
        _cleanup_sessions()
        uid = user["id"]
        stable = [s for s in _sessions.values() if s["user_id"]==uid and (_t.time()-s["start"])>35]
        if len(stable) >= max_s:
            logger.warning(f"Stream blocked: {user['name']} {len(stable)}/{max_s}")
            _pu = db.get_proxy_url()
            _eu = f"{_pu}/iptv/error-stream.jpg"
            _em = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:10.0,\n" + _eu + "\n#EXT-X-ENDLIST\n"
            return HTMLResponse(content=_em, media_type="application/x-mpegURL", headers={"Cache-Control":"no-cache"})
    # ── CATCHUP MODE ──────────────────────────────────────────────────────────
    if utc:
        try:
            # Build archive URL: replace mono.m3u8 with index.m3u8 + utc param
            base_cdn = decoded_url.rsplit("/mono.m3u8", 1)[0]
            ch_token = decoded_url.split("token=")[-1] if "token=" in decoded_url else ""
            archive_url = f"{base_cdn}/index.m3u8?token={ch_token}&utc={utc}"

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"]),
                follow_redirects=True,
                headers=make_headers(hls)
            ) as client:
                resp = await client.get(archive_url)
                resp.raise_for_status()
                archive_content = resp.text

            # Rewrite segment URLs through our proxy
            rewritten = rewrite_hls_playlist(archive_content, archive_url, proxy_url, token)
            dt_str = datetime.fromtimestamp(int(utc), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            logger.info(f"Catchup playlist: {user['name']} → {channel_name} @ {dt_str}")
            return HTMLResponse(
                content=rewritten,
                media_type="application/vnd.apple.mpegurl",
                headers={"Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*"}
            )
        except Exception as e:
            logger.error(f"Catchup error: {e}")
            # Fall through to live

    # ── LIVE MODE ─────────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"]),
            follow_redirects=hls["hls_follow_redirects"],
            headers=make_headers(hls)
        ) as client:
            resp = await client.get(decoded_url)
            resp.raise_for_status()
            playlist_content = resp.text

        rewritten = rewrite_hls_playlist(playlist_content, decoded_url, proxy_url, token)
        logger.info(f"HLS playlist served: {user['name']} → {channel_name}")
        return HTMLResponse(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Failed to fetch stream for {user['name']}: {e}")
        raise HTTPException(status_code=502, detail=f"Stream fetch failed: {e}")


# In-memory session tracking
# {session_key: {"channel": str, "log_id": int, "start": float, "last_seen": float, "user_id": int, "token": str}}
_sessions: dict = {}
SESSION_MEM_TTL = 35  # seconds without segment = session dead

def _cleanup_sessions():
    """Remove stale sessions from memory and end their DB records."""
    now = time.time()
    stale = [k for k, v in _sessions.items() if now - v["last_seen"] > SESSION_MEM_TTL]
    for k in stale:
        s = _sessions.pop(k)
        try:
            db.session_end(s["token"])
            db.end_watch_log(s["log_id"], int(now - s["start"]))
            logger.info(f"Session expired (TTL): {k}")
        except Exception:
            pass

def _user_stream_count(user_id: int) -> int:
    _cleanup_sessions()
    return sum(1 for s in _sessions.values() if s["user_id"] == user_id)

def _user_has_session(user_id: int, session_key: str) -> bool:
    return session_key in _sessions


@proxy_app.get("/iptv/{token}/segment")
async def proxy_segment(token: str, url: str, request: Request = None):
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid token")

    if not user["active"]:
        # User is banned – return error image M3U
        proxy_url = db.get_proxy_url()
        banned_url = f"{proxy_url}/iptv/error-banned.jpg"
        banned_m3u = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:10.0,\n" + banned_url + "\n#EXT-X-ENDLIST\n"
        return HTMLResponse(content=banned_m3u, media_type="application/x-mpegURL",
                           headers={"Cache-Control": "no-cache"})

    decoded_url = urllib.parse.unquote(url)
    hls = get_hls_settings()
    proxy_url = db.get_proxy_url()
    is_ts = not (decoded_url.endswith(".m3u8") or "m3u8" in decoded_url.split("?")[0])

    if is_ts:
        parts = decoded_url.split("/")
        ch_record = db.get_channel_by_url_fragment(decoded_url)
        if ch_record:
            channel_name = ch_record["name"]
        else:
            ch_idx = next((i for i, p in enumerate(parts) if p.startswith("ch")), None)
            channel_name = parts[ch_idx] if ch_idx else parts[-1].split("?")[0]

        # Get client IP
        client_ip = ""
        if request:
            forwarded = request.headers.get("x-forwarded-for")
            client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")

        # Session fingerprint = token + IP + User-Agent
        # Same IP but different User-Agent = different device (e.g. brother at home with router NAT)
        ua = request.headers.get("user-agent", "") if request else ""
        # Normalize UA: take first 40 chars to avoid tiny differences
        ua_short = ua[:40].strip()
        session_key = f"{token}::{client_ip}::{ua_short}"
        user_id = user["id"]

        now = time.time()

        if session_key in _sessions:
            existing = _sessions[session_key]
            if existing["channel"] != channel_name:
                # Channel switched – close old
                _sessions.pop(session_key)
                db.session_end(token)
                db.end_watch_log(existing["log_id"], int(now - existing["start"]))
                logger.info(f"Channel switch: {user['name']} ({client_ip}) → {channel_name}")
            else:
                # Same channel – just refresh
                _sessions[session_key]["last_seen"] = now
                db.session_refresh(token)

        if session_key not in _sessions:
            # Check max_streams (cleanup stale first)
            max_s = user.get("max_streams", 1) or 0
            if max_s > 0:
                active_count = _user_stream_count(user_id)
                if active_count >= max_s:
                    active_ips = list(set(s["session_key"].split("::")[1] for s in _sessions.values() if s["user_id"] == user_id))
                    logger.warning(f"Max streams blocked: {user['name']} {active_count}/{max_s} from {client_ip}")
                    raise HTTPException(status_code=429, detail=f"Max. {max_s} Stream(s) erlaubt")
            db.session_start(token, channel_name, ip_address=client_ip)
            log_id = db.start_watch_log(user_id=user["id"], channel=channel_name, stream_url=decoded_url, ip_address=client_ip)
            _sessions[session_key] = {
                "channel": channel_name, "log_id": log_id, "start": now,
                "last_seen": now, "user_id": user_id, "token": token, "session_key": session_key
            }
            logger.info(f"Session started: {user['name']} ({client_ip}) → {channel_name}")

    async def stream_segment():
        try:
            timeout = httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"])
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=hls["hls_follow_redirects"],
                headers=make_headers(hls)
            ) as client:
                if not is_ts:
                    resp = await client.get(decoded_url)
                    resp.raise_for_status()
                    rewritten = rewrite_hls_playlist(resp.text, decoded_url, proxy_url, token)
                    yield rewritten.encode()
                    return
                else:
                    async with client.stream("GET", decoded_url) as resp:
                        async for chunk in resp.aiter_bytes(chunk_size=hls["hls_chunk_size"]):
                            yield chunk
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Segment error: {e}")
            if session_key in _sessions:
                s = _sessions.pop(session_key)
                db.session_end(token)
                db.end_watch_log(s["log_id"], int(time.time() - s["start"]))

    media_type = "application/vnd.apple.mpegurl" if not is_ts else "video/mp2t"
    return StreamingResponse(stream_segment(), media_type=media_type,
                             headers={"Cache-Control": "no-cache"})


@proxy_app.get("/iptv/{token}/stop")
async def stop_stream(token: str, request: Request = None):
    # Clean up any session for this token
    stale = [k for k, s in _sessions.items() if s["token"] == token]
    for k in stale:
        s = _sessions.pop(k)
        db.end_watch_log(s["log_id"], int(time.time() - s["start"]))
    db.session_end(token)
    return {"ok": True}


@proxy_app.get("/iptv/{token}/catchup/{channel_id}")
async def proxy_catchup(token: str, channel_id: str, utc: str = None, lutc: str = None):
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        raise HTTPException(status_code=403, detail="Invalid or disabled token")
    with db.conn() as con:
        row = con.execute(
            "SELECT * FROM channels WHERE tvg_id = ? LIMIT 1", (channel_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")
    import sqlite3
    ch = dict(row)
    stream_url = ch["stream_url"]
    encoded = urllib.parse.quote(stream_url, safe="")
    redirect_url = f"/iptv/{token}/stream?url={encoded}"
    if utc:
        redirect_url += f"&utc={utc}"
    if lutc:
        redirect_url += f"&lutc={lutc}"
    return RedirectResponse(url=redirect_url)


# EPG cache: (content, fetched_at_timestamp, source_url)
_epg_cache: dict = {"content": None, "fetched_at": 0, "url": ""}

@proxy_app.get("/iptv/epg.xml")
async def global_epg(force: str = None):
    """Global EPG URL – no token needed, same for all users. Cached."""
    global _epg_cache
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]
    if not epg_sources:
        raise HTTPException(status_code=404, detail="No EPG source configured")

    source_url = epg_sources[0]
    refresh_hours = int(db.get_setting("epg_refresh_hours", "6"))
    refresh_secs = refresh_hours * 3600
    now = int(time.time())
    cache_valid = (
        _epg_cache["content"] is not None and
        _epg_cache["url"] == source_url and
        (now - _epg_cache["fetched_at"]) < refresh_secs and
        force != "1"
    )

    if cache_valid:
        age_min = (now - _epg_cache["fetched_at"]) // 60
        logger.info(f"EPG served from cache (age: {age_min}min)")
        return HTMLResponse(
            content=_epg_cache["content"],
            media_type="application/xml",
            headers={"X-EPG-Cache": "HIT", "X-EPG-Age-Minutes": str(age_min)}
        )

    try:
        logger.info(f"Fetching EPG from {source_url}")
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(source_url)
            resp.raise_for_status()
            content_text = resp.text

        # Filter EPG to only include channels we have in DB
        filter_epg = db.get_setting("epg_filter_channels", "0") == "1"
        if filter_epg:
            content_text = _filter_epg_xml(content_text)

        _epg_cache = {"content": content_text, "fetched_at": now, "url": source_url}
        logger.info(f"EPG cached ({len(content_text)//1024}KB)")
        return HTMLResponse(content=content_text, media_type="application/xml",
                           headers={"X-EPG-Cache": "MISS"})
    except Exception as e:
        if _epg_cache["content"]:
            logger.warning(f"EPG fetch failed, serving stale cache: {e}")
            return HTMLResponse(content=_epg_cache["content"], media_type="application/xml",
                               headers={"X-EPG-Cache": "STALE"})
        raise HTTPException(status_code=502, detail=f"EPG fetch failed: {e}")


def _filter_epg_xml(xml_content: str, days_back: int = 1, days_forward: int = 7) -> str:
    """Filter EPG XML – channel whitelist + day range + sorted by channel order."""
    try:
        import xml.etree.ElementTree as ET
        from datetime import datetime, timezone, timedelta

        known_ids = db.get_enabled_epg_ids()
        if not known_ids:
            chs = db.get_channels(enabled_only=False)
            known_ids = {c["tvg_id"] for c in chs if c.get("tvg_id")}

        epg_order = {ch["tvg_id"]: ch["sort_order"] for ch in db.get_epg_channels() if ch["enabled"]}

        root = ET.fromstring(xml_content)
        new_root = ET.Element("tv")
        new_root.set("generator-info-name", "selfstream")

        now = datetime.now(timezone.utc)
        t_from = now - timedelta(days=days_back)
        t_to = now + timedelta(days=days_forward)

        ch_map = {ch.get("id"): ch for ch in root.findall("channel")}
        sorted_ids = sorted(
            [cid for cid in known_ids if cid in ch_map],
            key=lambda x: epg_order.get(x, 9999)
        )
        for cid in sorted_ids:
            new_root.append(ch_map[cid])

        for prog in root.findall("programme"):
            ch_id = prog.get("channel", "")
            if known_ids and ch_id not in known_ids:
                continue
            try:
                start_str = prog.get("start", "")
                if start_str:
                    dt = datetime.strptime(start_str[:14], "%Y%m%d%H%M%S")
                    tz_str = start_str[15:] if len(start_str) > 15 else "+0000"
                    sign = 1 if tz_str[0] == "+" else -1
                    tz_h, tz_m = int(tz_str[1:3]), int(tz_str[3:5])
                    tz_offset = timezone(timedelta(hours=sign*tz_h, minutes=sign*tz_m))
                    dt = dt.replace(tzinfo=tz_offset)
                    if not (t_from <= dt <= t_to):
                        continue
            except Exception:
                pass
            new_root.append(prog)

        return ET.tostring(new_root, encoding="unicode", xml_declaration=True)
    except Exception as e:
        logger.error(f"EPG filter failed: {e}")
        return xml_content


@proxy_app.get("/iptv/epg-{days}d.xml")
async def global_epg_days(days: int, force: str = None):
    """EPG filtered to N days: /iptv/epg-1d.xml /iptv/epg-3d.xml /iptv/epg-7d.xml"""
    global _epg_cache
    if days not in (1, 3, 7):
        raise HTTPException(status_code=400, detail="days must be 1, 3, or 7")
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]
    if not epg_sources:
        raise HTTPException(status_code=404, detail="No EPG source")
    source_url = epg_sources[0]
    now_ts = int(time.time())
    refresh_secs = int(db.get_setting("epg_refresh_hours", "6")) * 3600
    cache_valid = (
        _epg_cache.get("content") and _epg_cache.get("url") == source_url and
        (now_ts - _epg_cache.get("fetched_at", 0)) < refresh_secs and force != "1"
    )
    if not cache_valid:
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                resp = await client.get(source_url)
                resp.raise_for_status()
                raw = resp.text
            _epg_cache = {"content": raw, "fetched_at": now_ts, "url": source_url}
        except Exception as e:
            raw = _epg_cache.get("content") or ""
            if not raw:
                raise HTTPException(status_code=502, detail=str(e))
    else:
        raw = _epg_cache["content"]
    filtered = _filter_epg_xml(raw, days_back=1, days_forward=days)
    return HTMLResponse(content=filtered, media_type="application/xml",
                       headers={"Cache-Control": "max-age=3600"})


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
    short_domain = db.get_setting("short_domain", "")
    short_base = short_domain.rstrip("/") if short_domain else proxy_url
    for u in users:
        u["playlist_url"] = f"{proxy_url}/iptv/{u['token']}/playlist.m3u"
        u["epg_url"] = f"{proxy_url}/iptv/epg.xml"
        short_tok = u.get("short_token") or ""
        if not short_tok:
            short_tok = db.generate_short_token(u["id"])
            u["short_token"] = short_tok
        u["short_playlist_url"] = f"{short_base}/s/{short_tok}/playlist.m3u"
    return users

@admin_app.post("/api/users")
def create_user(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    notes = body.get("notes", "").strip()
    max_streams = body.get("max_streams", 1)
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    m3u_source = db.get_setting("source_m3u_url", "")
    token = str(uuid.uuid4()).replace("-", "")[:24]
    user = db.create_user(name=name, token=token, m3u_source=m3u_source, notes=notes)
    short_token = db.generate_short_token(user["id"])
    proxy_url = db.get_proxy_url()
    short_domain = db.get_setting("short_domain", "")
    short_base = short_domain.rstrip("/") if short_domain else proxy_url
    return {**user,
            "short_token": short_token,
            "playlist_url": f"{proxy_url}/iptv/{token}/playlist.m3u",
            "short_playlist_url": f"{short_base}/s/{short_token}/playlist.m3u",
            "epg_url": f"{proxy_url}/iptv/epg.xml"}

@proxy_app.get("/s/{short_token}/playlist.m3u")
@proxy_app.get("/s/{short_token}/playlist.m3u8")
async def short_playlist(short_token: str):
    """Short URL redirect for playlists."""
    user = db.get_user_by_short_token(short_token)
    if not user or not user["active"]:
        raise HTTPException(status_code=404, detail="Not found")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/iptv/{user['token']}/playlist.m3u")

@proxy_app.get("/s/{short_token}/epg.xml")
async def short_epg(short_token: str):
    """Short URL for EPG."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/iptv/epg.xml")

@admin_app.post("/api/users/{user_id}/regenerate-token")
def regenerate_token(user_id: int, _=Depends(check_admin)):
    new_token = db.regenerate_token(user_id)
    proxy_url = db.get_proxy_url()
    return {
        "ok": True,
        "token": new_token,
        "playlist_url": f"{proxy_url}/iptv/{new_token}/playlist.m3u",
        "epg_url": f"{proxy_url}/iptv/{new_token}/epg.xml"
    }

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

@admin_app.get("/api/epg/download")
async def download_epg_xml(days: int = 0, _=Depends(check_admin)):
    """Download the filtered EPG XML. days=0 means all, days=1/3/7 filters by day range."""
    global _epg_cache
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]
    if not epg_sources:
        raise HTTPException(status_code=404, detail="No active EPG source configured")

    source_url = epg_sources[0]
    now_ts = int(time.time())
    refresh_hours = int(db.get_setting("epg_refresh_hours", "6"))
    cache_valid = (
        _epg_cache.get("content") and
        _epg_cache.get("url") == source_url and
        (now_ts - _epg_cache.get("fetched_at", 0)) < refresh_hours * 3600
    )

    if not cache_valid:
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                resp = await client.get(source_url)
                resp.raise_for_status()
                raw = resp.text
            _epg_cache = {"content": raw, "fetched_at": now_ts, "url": source_url}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"EPG fetch failed: {e}")
    else:
        raw = _epg_cache["content"]

    days_forward = days if days in (1, 3, 7) else 7
    filtered = _filter_epg_xml(raw, days_back=1, days_forward=days_forward)
    fname = f"epg-{days}d.xml" if days in (1, 3, 7) else "epg.xml"

    from fastapi.responses import Response
    return Response(
        content=filtered.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )

@admin_app.get("/api/epg/channels")
def list_epg_channels(_=Depends(check_admin)):
    return db.get_epg_channels()

@admin_app.put("/api/epg/channels/{tvg_id}")
def update_epg_channel(tvg_id: str, body: dict, _=Depends(check_admin)):
    db.update_epg_channel(tvg_id, body)
    return {"ok": True}

@admin_app.post("/api/epg/channels/reorder")
def reorder_epg_channels(body: dict, _=Depends(check_admin)):
    """Reorder: body = {"order": ["ch265", "ch266", ...]}"""
    order = body.get("order", [])
    for i, tvg_id in enumerate(order):
        db.update_epg_channel(tvg_id, {"sort_order": i})
    return {"ok": True}

@admin_app.post("/api/epg/scan")
async def scan_epg_channels(_=Depends(check_admin)):
    """Parse active EPG source and populate epg_channel_filter table."""
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]
    if not epg_sources:
        raise HTTPException(status_code=404, detail="No active EPG source")
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(epg_sources[0])
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"EPG fetch failed: {e}")

    # Parse channels from XML
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
        # Get channel manager data for icon fallback + sort order
        ch_manager_list = db.get_channels()
        ch_manager = {c["tvg_id"]: c["sort_order"] for c in ch_manager_list if c.get("tvg_id")}
        ch_logos = {c["tvg_id"]: c.get("tvg_logo","") for c in ch_manager_list if c.get("tvg_id")}

        channels = []
        for ch in root.findall("channel"):
            cid = ch.get("id", "")
            name_el = ch.find("display-name")
            name = name_el.text if name_el is not None else cid
            icon_el = ch.find("icon")
            # Try EPG icon first, then fall back to M3U logo
            icon_url = ""
            if icon_el is not None:
                icon_url = icon_el.get("src", "")
            if not icon_url and cid in ch_logos:
                icon_url = ch_logos[cid]  # Use M3U channel logo as fallback
            if cid:
                sort_order = ch_manager.get(cid, 9999)
                channels.append({"tvg_id": cid, "name": name, "icon_url": icon_url, "sort_order": sort_order})

        channels.sort(key=lambda x: x["sort_order"])
        db.upsert_epg_channels(channels)
        return {"ok": True, "found": len(channels)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XML parse failed: {e}")

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
    _cleanup_sessions()
    active_sessions = db.get_active_sessions()
    ch_stats = db.get_channels_count()
    recent_logs = db.get_all_logs(limit=10)
    return {
        "total_users": len(users),
        "active_streams": len(active_sessions),
        "active_sessions": [{"user": s["user_name"], "channel": s["channel"], "started_at": s.get("started_at"), "ip": s.get("ip_address","")} for s in active_sessions],
        "recent_logs": [{"user": l["user_name"], "channel": l["channel"], "started_at": l["started_at"], "duration": l["duration_seconds"], "ip": l.get("ip_address","")} for l in recent_logs],
        "watch_logs_today": db.get_logs_today_count(),
        "total_channels": ch_stats["total"] or 0,
        "enabled_channels": ch_stats["enabled"] or 0,
    }

@admin_app.get("/api/logs")
def get_all_logs(limit: int = 200, _=Depends(check_admin)):
    return db.get_all_logs(limit)

@admin_app.post("/api/logs/clear")
def clear_logs(body: dict, _=Depends(check_admin)):
    days = body.get("days", 0)
    db.clear_logs(days)
    return {"ok": True}

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
        "epg_refresh_hours":    s.get("epg_refresh_hours", "6"),
        "epg_filter_channels":  s.get("epg_filter_channels", "0"),
        "log_retention_days":   s.get("log_retention_days", "-1"),
        "short_domain":         s.get("short_domain", ""),
    }

@admin_app.post("/api/settings")
def update_settings(body: dict, _=Depends(check_admin)):
    allowed = {"base_url", "proxy_url", "source_m3u_url",
               "hls_timeout", "hls_read_timeout", "hls_chunk_size",
               "hls_user_agent", "hls_referer", "hls_follow_redirects",
               "epg_refresh_hours", "epg_filter_channels", "log_retention_days",
               "short_domain"}
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
    # Check for custom logo first
    custom = "/data/custom_login_logo.png"
    if os.path.exists(custom):
        return FileResponse(custom)
    return FileResponse(f"{FRONTEND}/logo.png", media_type="image/png")

@admin_app.get("/logo-app.png")
async def logo_app():
    from fastapi.responses import FileResponse
    custom = "/data/custom_app_logo.png"
    if os.path.exists(custom):
        return FileResponse(custom)
    custom_login = "/data/custom_login_logo.png"
    if os.path.exists(custom_login):
        return FileResponse(custom_login)
    return FileResponse(f"{FRONTEND}/logo.png", media_type="image/png")

@admin_app.post("/api/settings/upload-logo")
async def upload_logo(request: Request, _=Depends(check_admin)):
    from fastapi import UploadFile, Form
    import shutil
    form = await request.form()
    logo_type = form.get("type", "login")  # login or app
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="No file")
    filename = f"/data/custom_{logo_type}_logo.png"
    with open(filename, "wb") as f:
        content_bytes = await file.read()
        f.write(content_bytes)
    return {"ok": True, "path": filename}

@admin_app.delete("/api/settings/upload-logo")
async def delete_logo(body: dict, _=Depends(check_admin)):
    logo_type = body.get("type", "login")
    filename = f"/data/custom_{logo_type}_logo.png"
    if os.path.exists(filename):
        os.remove(filename)
    return {"ok": True}