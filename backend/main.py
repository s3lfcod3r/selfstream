import os
import uuid
import time
import hmac
import hashlib
import sqlite3
import httpx
import asyncio
import math
import logging
import threading
import subprocess
import urllib.parse
import re
import json
import io
import csv
import socket
import ipaddress
import xml.etree.ElementTree as ET
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from database import Database
from m3u_parser import parse_m3u, build_m3u
from timeparse import (
    _sanitize_diagnostic_timezone, _parse_xmltv_datetime, _parse_catchup_wall_time,
    _epg_programme_contains_instant, _epg_programme_contains_instant_half_open,
    _DVR_PATH_RE, _dvr_wall_time_from_url,
)
from hls import rewrite_hls_playlist
from security_util import (
    _host_is_internal, assert_safe_upstream_url,
    _PBKDF2_ITERATIONS, _hash_admin_token, _verify_admin_token,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

proxy_app = FastAPI(title="selfstream proxy")
admin_app = FastAPI(title="selfstream admin")

for a in (proxy_app, admin_app):
    # allow_credentials=False: die App authentifiziert über den X-Admin-Token-Header
    # bzw. Pfad-Token, nicht über Cookies. Die Kombination "*" + credentials=True ist
    # laut CORS-Spec ungültig und wäre eine unnötige Angriffsfläche.
    a.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                     allow_methods=["*"], allow_headers=["*"])


@proxy_app.middleware("http")
@admin_app.middleware("http")
async def _security_headers(request: Request, call_next):
    """Setzt grundlegende Sicherheits-Header auf allen Antworten beider Apps."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# SSRF-Schutz (_host_is_internal, assert_safe_upstream_url) liegt in security_util.py

db = Database()


def is_diagnostics_enabled() -> bool:
    """Global switch for writing diagnostic logs."""
    return db.get_setting("diagnostics_enabled", "1") == "1"


def diag_log(level: str, source: str, message: str):
    """Persist server diagnostics for the admin UI (~30 days). Must never affect requests."""
    if not is_diagnostics_enabled():
        return
    try:
        db.add_diagnostic_log(level, source, message)
    except Exception:
        pass


def _clip_text(v, max_len: int = 6000) -> str:
    s = str(v)
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"... [truncated {len(s) - max_len} chars]"


def is_player_request_debug_enabled() -> bool:
    """Log detailed player HTTP requests/responses to diagnostics."""
    return db.get_setting("player_request_debug", "1") == "1"


def _log_player_request(stage: str, request: Request | None, token: str, extra: dict | None = None, level: str = "INFO"):
    """Structured request tracing for playlist/stream/segment/catchup endpoints."""
    if not is_player_request_debug_enabled():
        return
    try:
        hdrs = {}
        if request:
            for k, v in request.headers.items():
                hdrs[k.lower()] = v
        payload = {
            "stage": stage,
            "token_prefix": (token or "")[:8],
            "method": request.method if request else "",
            "path": request.url.path if request else "",
            "query": dict(request.query_params) if request else {},
            "headers": hdrs,
            "client": {
                "x_forwarded_for": (request.headers.get("x-forwarded-for", "") if request else ""),
                "remote_addr": (request.client.host if request and request.client else ""),
            },
            "extra": extra or {},
        }
        msg = _clip_text(json.dumps(payload, ensure_ascii=True, sort_keys=True))
        diag_log(level, "player-request", msg)
    except Exception:
        pass


# Reine Zeit-/EPG-Parser (_sanitize_diagnostic_timezone, _parse_xmltv_datetime,
# _parse_catchup_wall_time, _epg_programme_contains_instant[_half_open]) liegen in
# timeparse.py und werden oben importiert.


def _epg_title_at_time(channel_name: str, catchup_time_str: str, root) -> str:
    """Resolve programme title for channel at catchup wall time (UTC)."""
    if not root or not channel_name or not catchup_time_str:
        return ""
    ct = _parse_catchup_wall_time(catchup_time_str)
    if not ct:
        return ""
    ch_rec = db.get_channel_by_name(channel_name) or {}
    tvg_id = ch_rec.get("tvg_id", "").strip()
    if not tvg_id:
        for ch_el in root.findall("channel"):
            disp = ch_el.findtext("display-name") or ""
            if channel_name.lower() in disp.lower() or disp.lower() in channel_name.lower():
                tvg_id = ch_el.get("id", "")
                break
    if not tvg_id:
        return ""
    for prog in root.findall("programme"):
        if prog.get("channel", "") != tvg_id:
            continue
        ps = _parse_xmltv_datetime(prog.get("start", ""))
        pe = _parse_xmltv_datetime(prog.get("stop", ""))
        if _epg_programme_contains_instant(ps, pe, ct):
            return (prog.findtext("title") or "").strip()
    return ""


def _epg_title_at_time_half_open(channel_name: str, catchup_time_str: str, root) -> str:
    """Same as _epg_title_at_time but [start,stop) — matches Catchup-DVR-Sync and ENDLIST diagnostics."""
    if not root or not channel_name or not catchup_time_str:
        return ""
    ct = _parse_catchup_wall_time(catchup_time_str)
    if not ct:
        return ""
    ch_rec = db.get_channel_by_name(channel_name) or {}
    tvg_id = ch_rec.get("tvg_id", "").strip()
    if not tvg_id:
        for ch_el in root.findall("channel"):
            disp = ch_el.findtext("display-name") or ""
            if channel_name.lower() in disp.lower() or disp.lower() in channel_name.lower():
                tvg_id = ch_el.get("id", "")
                break
    if not tvg_id:
        return ""
    for prog in root.findall("programme"):
        if prog.get("channel", "") != tvg_id:
            continue
        ps = _parse_xmltv_datetime(prog.get("start", ""))
        pe = _parse_xmltv_datetime(prog.get("stop", ""))
        if _epg_programme_contains_instant_half_open(ps, pe, ct):
            return (prog.findtext("title") or "").strip()
    return ""


# Segment timing events for buffering diagnosis
_segment_events: list = []

async def _fetch_and_cache_epg():
    """Fetch EPG from source, update memory + disk cache."""
    global _epg_cache
    try:
        epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]
        if not epg_sources:
            return False
        source_url = epg_sources[0]
        async with make_iptv_client(timeout=120, follow_redirects=True) as client:
            resp = await client.get(source_url)
            resp.raise_for_status()
            content = resp.text
        filter_epg = db.get_setting("epg_filter_channels", "0") == "1"
        if filter_epg:
            content = _filter_epg_xml(content, days_back=7)
        now = int(time.time())
        _epg_cache = {"content": content, "fetched_at": now, "url": source_url}
        with open("/data/epg_cache.xml", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"EPG auto-fetched and cached ({len(content)//1024}KB)")
        return True
    except Exception as e:
        logger.warning(f"EPG auto-fetch failed: {e}")
        diag_log("WARNING", "epg", f"EPG auto-fetch failed: {e}")
        return False


async def _epg_watchdog():
    """Background task: ensure EPG cache is always populated."""
    global _epg_cache
    await asyncio.sleep(5)  # wait for startup to complete

    while True:
        try:
            refresh_hours = int(db.get_setting("epg_refresh_hours", "6") or "6")
            refresh_secs = refresh_hours * 3600
            now = int(time.time())
            cache_age = now - _epg_cache.get("fetched_at", 0)
            cache_ok = _epg_cache.get("content") and cache_age < refresh_secs

            if not cache_ok:
                # Try memory cache missing → load from disk first
                if not _epg_cache.get("content"):
                    try:
                        with open("/data/epg_cache.xml", "r", encoding="utf-8") as f:
                            content = f.read()
                        if content:
                            _epg_cache["content"] = content
                            _epg_cache["fetched_at"] = int(os.path.getmtime("/data/epg_cache.xml"))
                            logger.info("EPG loaded from disk cache")
                            cache_age = now - _epg_cache["fetched_at"]
                            cache_ok = cache_age < refresh_secs
                    except Exception:
                        pass

                if not cache_ok:
                    logger.info("EPG watchdog: cache stale or missing, fetching...")
                    await _fetch_and_cache_epg()

        except Exception as e:
            logger.warning(f"EPG watchdog error: {e}")
            diag_log("WARNING", "epg", f"EPG watchdog error: {e}")

        await asyncio.sleep(300)  # check every 5 minutes


async def _m3u_watchdog():
    """Background task: auto-refresh M3U channels on schedule (global + per-provider)."""
    await asyncio.sleep(10)  # wait for startup
    while True:
        try:
            # Legacy global refresh — nur ohne Anbieter-Tabelle. Sonst würde source_m3u_url
            # (oft noch alte URL vom ersten Import) alle Kanäle aller Anbieter überschreiben.
            if db.get_m3u_refresh_due() and not db.has_m3u_providers():
                url = db.get_setting("source_m3u_url", "")
                if url:
                    logger.info("M3U watchdog: refreshing global channels...")
                    try:
                        async with make_iptv_client(timeout=60, follow_redirects=True) as client:
                            resp = await client.get(url)
                            resp.raise_for_status()
                            channels = parse_m3u(resp.text)
                        db.upsert_channels(channels)
                        db.set_m3u_last_refresh()
                        logger.info(f"M3U global auto-refresh: {len(channels)} channels updated")
                    except Exception as e:
                        logger.warning(f"M3U global auto-refresh failed: {e}")
                        diag_log("WARNING", "m3u", f"M3U global auto-refresh failed: {e}")
            # Per-provider refresh
            due_providers = db.get_providers_due_refresh()
            for p in due_providers:
                url = p.get("source_url", "")
                if not url or url.startswith("local://"):
                    continue
                logger.info(f"M3U provider auto-refresh: {p['name']} ({url[:60]})")
                try:
                    async with make_iptv_client(timeout=60, follow_redirects=True) as client:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        channels = parse_m3u(resp.text)
                    db.upsert_channels(channels, provider_id=p["id"])
                    db.set_provider_last_refresh(p["id"])
                    logger.info(f"M3U provider auto-refresh OK: {p['name']} → {len(channels)} channels")
                except Exception as e:
                    logger.warning(f"M3U provider auto-refresh failed ({p['name']}): {e}")
                    diag_log("WARNING", "m3u", f"M3U provider auto-refresh failed ({p.get('name')}): {e}")
        except Exception as e:
            logger.warning(f"M3U watchdog error: {e}")
            diag_log("WARNING", "m3u", f"M3U watchdog error: {e}")
        await asyncio.sleep(300)  # check every 5 minutes


_startup_lock = threading.Lock()
_startup_done = False


@proxy_app.on_event("startup")
@admin_app.on_event("startup")
async def startup():
    """server.py startet proxy_app und admin_app in zwei eigenen Threads mit
    je eigenem Event-Loop. Ohne diesen Guard würden alle Watchdogs (EPG, M3U,
    Catchup-EPG, Live-EPG) in BEIDEN Loops laufen → konkurrierende Splits beim
    Sendungswechsel → doppelte watch_logs-Einträge."""
    global _startup_done
    with _startup_lock:
        if _startup_done:
            logger.info("startup already ran in another event loop — skipping")
            return
        _startup_done = True
    db.init()
    db.migrate_watch_logs()
    try:
        db.purge_diagnostic_logs(30)
    except Exception:
        pass
    _generate_error_video()
    asyncio.create_task(_epg_watchdog())
    asyncio.create_task(_m3u_watchdog())
    asyncio.create_task(_catchup_epg_watchdog())
    asyncio.create_task(_live_epg_watchdog())
    # Auto-start VPN if it was enabled before
    if db.get_setting("vpn_enabled", "0") == "1":
        result = vpn_start()
        if result.get("ok"):
            logger.info("VPN auto-start: OK")
        else:
            logger.warning(f"VPN auto-start failed: {result.get('error')}")
            diag_log("WARNING", "vpn", f"VPN auto-start failed: {result.get('error')}")
    logger.info("selfstream started")


def _generate_error_video():
    """Generate an error JPEG image using Pillow for max-streams display."""
    out_path = "/data/error-max-streams.jpg"
    # Always regenerate to pick up new logo
    # if os.path.exists(out_path): return

    try:
        from PIL import Image, ImageDraw, ImageFont
        import base64

        # Canvas 1280x720 dark background
        img = Image.new("RGB", (1280, 720), color=(10, 14, 21))
        draw = ImageDraw.Draw(img)

        # Try to load selfstream logo
        logo_path = "/data/custom_login_logo.png"
        if not os.path.exists(logo_path):
            logo_path = "/app/frontend/logo.png"

        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((220, 220), Image.LANCZOS)
            # Create background patch same color as canvas, then paste logo with alpha
            logo_bg = Image.new("RGBA", logo.size, (10, 14, 21, 255))
            logo_bg.paste(logo, (0, 0), logo)
            logo_final = logo_bg.convert("RGB")
            lx = (1280 - logo_final.width) // 2
            img.paste(logo_final, (lx, 60))
        except Exception:
            pass

        # Draw stop symbol
        draw.ellipse([540, 280, 740, 480], outline=(248, 81, 73), width=8)
        draw.rectangle([600, 350, 680, 410], fill=(248, 81, 73))

        # Main error text
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except Exception:
            font_large = ImageFont.load_default()
            font_med = font_large
            font_small = font_large

        text1 = "Max. Streams erreicht"
        text2 = "Bitte beende einen anderen Stream"
        text3 = "und versuche es erneut."

        # Center text
        for font, text, y, color in [
            (font_large, text1, 500, (248, 81, 73)),
            (font_med, text2, 558, (180, 190, 200)),
            (font_small, text3, 596, (139, 148, 158)),
        ]:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            draw.text(((1280 - w) // 2, y), text, font=font, fill=color)

        # Subtle border
        draw.rectangle([20, 20, 1260, 700], outline=(30, 40, 55), width=2)

        img.save(out_path, "JPEG", quality=85)
        logger.info(f"Error image generated: {out_path}")

    except Exception as e:
        logger.warning(f"Error image generation failed: {e}")


def vpn_make_transport() -> Optional[httpx.AsyncHTTPTransport]:
    """Return an httpx transport bound to tun0 IP for split-tunnel VPN routing."""
    if not vpn_is_running():
        return None
    tun_ip = vpn_get_tun_ip()
    if not tun_ip:
        return None
    try:
        return httpx.AsyncHTTPTransport(local_address=tun_ip)
    except Exception as e:
        logger.warning(f"VPN transport error: {e}")
        diag_log("WARNING", "vpn", f"VPN transport error: {e}")
        return None


SOCKS_PORT = 1080
_socks_process: Optional[subprocess.Popen] = None


def make_iptv_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx client with browser-like headers so IPTV servers don't block us."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Chromecast) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 CrKey/1.56.500000",
        "Accept": "*/*",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }
    # Merge with any headers passed in
    if "headers" in kwargs:
        merged = {**default_headers, **kwargs["headers"]}
        kwargs["headers"] = merged
    else:
        kwargs["headers"] = default_headers
    return httpx.AsyncClient(**kwargs)


def _start_socks_proxy(tun_ip: str):
    pass  # Reserved for future use


def _vpn_wait_for_tun(timeout: int = 30):
    """Wait for tun0 to be ready, then fix local routing."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        tun_ip = vpn_get_tun_ip()
        if tun_ip:
            _vpn_log_add(f"🌐 tun0 bereit: {tun_ip} – VPN aktiv!")
            # Keep local network (192.168.x.x) routed via eth0, not VPN
            try:
                result = subprocess.run(
                    ["ip", "route", "show", "default"],
                    capture_output=True, text=True, timeout=2
                )
                # Find original gateway from eth0
                for line in result.stdout.splitlines():
                    if "eth0" in line and "via" in line:
                        gw = line.split("via")[1].strip().split()[0]
                        # Add route for local subnet via eth0
                        subprocess.run(
                            ["ip", "route", "add", "192.168.0.0/16", "via", gw, "dev", "eth0"],
                            capture_output=True, timeout=2
                        )
                        _vpn_log_add(f"🏠 Lokales Netz via eth0 ({gw}) – Admin-Panel bleibt schnell")
                        break
            except Exception as e:
                _vpn_log_add(f"⚠️ Route fix: {e}")
            return
        time.sleep(0.5)
    _vpn_log_add("⚠️ tun0 Timeout")


def get_hls_settings() -> dict:
    # Defaults tuned for slow CDN / Catchup (vgl. Browser hls.js längere fragLoadingTimeOut).
    return {
        "hls_timeout":        int(db.get_setting("hls_timeout", "15")),
        "hls_read_timeout":   int(db.get_setting("hls_read_timeout", "60")),
        "hls_chunk_size":     int(db.get_setting("hls_chunk_size", "65536")),
        "hls_user_agent":     db.get_setting("hls_user_agent", "VLC/3.0 LibVLC/3.0"),
        "hls_referer":        db.get_setting("hls_referer", ""),
        "hls_follow_redirects": db.get_setting("hls_follow_redirects", "1") == "1",
    }


def catchup_upstream_httpx_timeout(hls: dict) -> httpx.Timeout:
    """
    Upstream catchup/DVR playlists are often much larger than a live mono.m3u8.
    Use a more generous read bound than live (similar idea to iptv-proxy catchup_* timeouts).
    """
    connect = max(5.0, float(hls["hls_timeout"]))
    base_read = float(hls["hls_read_timeout"])
    read_sec = max(base_read, min(300.0, base_read * 2.0))
    return httpx.Timeout(connect, read=read_sec)


def make_headers(hls: dict) -> dict:
    h = {"User-Agent": hls["hls_user_agent"]}
    if hls["hls_referer"]:
        h["Referer"] = hls["hls_referer"]
    return h


# rewrite_hls_playlist liegt jetzt in hls.py und wird oben importiert.


# ══════════════════════════════════════════════════════════════════════════════
# PROXY APP  (port 8000)
# ══════════════════════════════════════════════════════════════════════════════

@proxy_app.get("/iptv/{token}/playlist.m3u")
@proxy_app.get("/iptv/{token}/playlist.m3u8")
async def serve_playlist(token: str, local: str = None, request: Request = None):
    _log_player_request("playlist:request", request, token, {"local": local})
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        _log_player_request("playlist:forbidden", request, token, {"reason": "invalid_or_disabled"}, level="WARNING")
        raise HTTPException(status_code=403, detail="Invalid or disabled token")

    channels = db.get_channels(enabled_only=True)
    proxy_url = db.get_proxy_url()
    # local=1 → benutze interne IP (für Testzwecke vom Admin)
    # sonst → öffentliche Subdomain
    if local == "1":
        public_url = proxy_url
    else:
        short_domain = db.get_setting("short_domain", "")
        public_url = short_domain.rstrip("/") if short_domain else proxy_url
    epg_sources = [e["url"] for e in db.get_epg_sources() if e["active"]]

    if not channels:
        try:
            hls = get_hls_settings()
            async with make_iptv_client(timeout=30, headers=make_headers(hls)) as client:
                resp = await client.get(user["m3u_source"])
                resp.raise_for_status()
                channels_raw = parse_m3u(resp.text)
        except Exception as e:
            logger.error(f"Failed to fetch m3u for {user['name']}: {e}")
            diag_log("ERROR", "m3u", f"Failed to fetch m3u for {user['name']}: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch source playlist")
        channels = [{"name": c["name"], "raw_extinf": c["raw_extinf"],
                     "stream_url": c["url"], "tvg_id": c["tvg_id"],
                     "tvg_logo": c["tvg_logo"], "group_title": c["group"],
                     "tvg_rec": c.get("tvg_rec", "")} for c in channels_raw]

    # Filter by user's allowed_groups if set
    allowed_groups_raw = user.get("allowed_groups", "") or ""
    if allowed_groups_raw.strip():
        group_names = [g.strip() for g in allowed_groups_raw.split(",") if g.strip()]
        all_user_group_names = set(db.get_all_user_group_names())
        custom_groups = [g for g in group_names if g in all_user_group_names]
        provider_groups = [g for g in group_names if g not in all_user_group_names]
        result_channels = []

        # Position in the sorted list (ORDER BY sort_order, name) gives a stable,
        # unique 1-based index for the IPTV app prefix — even when sort_order is
        # 0 for every group (e.g. before the user reorders via drag & drop).
        _ug_sorted = db.get_user_groups()
        group_position = {g["name"]: idx for idx, g in enumerate(_ug_sorted)}
        use_prefix = db.get_setting("group_sort_prefix", "1") == "1"

        # Channels from custom user groups — override group_title with sorted name
        for ug_name in custom_groups:
            ug_channels = db.get_channels_for_user_groups([ug_name])
            sort_idx = group_position.get(ug_name, len(_ug_sorted))
            if use_prefix:
                display_name = f"{sort_idx + 1:02d}. {ug_name}"
            else:
                display_name = ug_name
            for ch in ug_channels:
                ch = dict(ch)
                ch["group_title"] = display_name
                result_channels.append(ch)

        # Channels from provider groups (by group_title) — keep original group_title
        if provider_groups:
            provider_set = set(provider_groups)
            result_channels.extend([c for c in channels if c.get("group_title", "") in provider_set])

        # Deduplicate by channel id (custom group takes priority)
        seen = set()
        channels = []
        for c in result_channels:
            cid = c.get("id")
            if cid not in seen:
                seen.add(cid)
                channels.append(c)

    # Sort channels: use unified saved order (covers both custom and provider groups)
    _saved_order = db.get_provider_group_order()

    def _group_sort_key(ch):
        gt = ch.get("group_title", "")
        # Strip numeric prefix like "01. Kinder" to get base name for lookup
        m = re.match(r"^[0-9]+\.\s*(.+)$", gt)
        base = m.group(1) if m else gt
        # Check saved order by display name or base name
        if gt in _saved_order:
            return (0, _saved_order[gt], gt)
        if base in _saved_order:
            return (0, _saved_order[base], gt)
        return (1, 0, gt)

    channels.sort(key=_group_sort_key)

    content = build_m3u(channels, public_url, token, epg_sources)
    db.log_playlist_access(user["id"])
    _log_player_request("playlist:response", request, token, {"channels": len(channels), "public_url": public_url})
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
        async with make_iptv_client(timeout=60, follow_redirects=True) as client:
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


@proxy_app.get("/iptv/error-max-streams.jpg")
async def error_max_streams_jpg():
    """Liefert das generierte 'Max. Streams erreicht'-JPEG für die Player-Anzeige."""
    from fastapi.responses import FileResponse, Response
    jpg_path = "/data/error-max-streams.jpg"
    if os.path.exists(jpg_path):
        return FileResponse(jpg_path, media_type="image/jpeg")
    return Response(content=b"", media_type="image/jpeg")


# Vorgerenderte MPEG-TS-Clips (committet in backend/assets, im Image unter
# /app/assets). HLS-Player überspringen ein JPEG-"Segment", spielen aber ein
# echtes TS-Video ab. Erzeugt von tools/gen_error_clips.py — kein ffmpeg auf
# dem Server, reine statische Auslieferung (keine CPU-Last).
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _build_loop_playlist(clip_url: str) -> str:
    """Endlos-Live-Playlist (KEIN #EXT-X-ENDLIST), die denselben Hinweis-Clip in
    einer gleitenden Fenster-Sequenz loopt. Eine VOD-Playlist mit ENDLIST endet
    nach 8 s → der Player denkt 'Stream zu Ende' und zappt automatisch auf den
    nächsten Sender / lädt neu. Als Live-Stream ohne Ende bleibt der Player auf
    dem Sender und zeigt die Meldung dauerhaft.

    #EXT-X-DISCONTINUITY vor jedem Segment, weil jeder Clip-Durchlauf bei PTS 0
    neu startet (ohne den Tag gäbe es Timestamp-Rücksprünge → Freeze/Sprung).
    """
    seq = int(time.time() // 8)
    sep = "&" if "?" in clip_url else "?"
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:9",
        f"#EXT-X-MEDIA-SEQUENCE:{seq}",
        f"#EXT-X-DISCONTINUITY-SEQUENCE:{seq}",
    ]
    for i in range(3):
        lines.append("#EXT-X-DISCONTINUITY")
        lines.append("#EXTINF:8.000,")
        lines.append(f"{clip_url}{sep}s={seq + i}")
    return "\n".join(lines) + "\n"


def _serve_error_clip(name: str):
    from fastapi.responses import FileResponse, Response
    ts_path = os.path.join(_ASSETS_DIR, name)
    if os.path.exists(ts_path):
        return FileResponse(
            ts_path,
            media_type="video/mp2t",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    return Response(content=b"", media_type="video/mp2t")


@proxy_app.get("/iptv/error-max-streams.ts")
async def error_max_streams_ts():
    """Liefert den 'Max. Streams erreicht'-Videoclip (MPEG-TS) für den Player."""
    return _serve_error_clip("error-max-streams.ts")


@proxy_app.get("/iptv/error-banned.ts")
async def error_banned_ts():
    """Liefert den 'Zugang gesperrt'-Videoclip (MPEG-TS) für den Player."""
    return _serve_error_clip("error-banned.ts")


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
    _log_player_request("stream:request", request, token, {"utc": utc, "lutc": lutc, "url_raw": url})
    user = db.get_user_by_token(token)
    if not user:
        _log_player_request("stream:forbidden", request, token, {"reason": "invalid_token"}, level="WARNING")
        raise HTTPException(status_code=403, detail="Invalid token")

    if not user["active"]:
        # User is banned – return error image M3U
        proxy_url = db.get_proxy_url()
        _short = db.get_setting("short_domain", "")
        _pub = _short.rstrip("/") if _short else proxy_url
        banned_url = f"{_pub}/iptv/error-banned.ts"
        banned_m3u = _build_loop_playlist(banned_url)
        return HTMLResponse(content=banned_m3u, media_type="application/x-mpegURL",
                           headers={"Cache-Control": "no-cache"})

    decoded_url = urllib.parse.unquote(url)
    assert_safe_upstream_url(decoded_url)  # SSRF-Schutz
    hls = get_hls_settings()
    proxy_url = db.get_proxy_url()
    short_domain = db.get_setting("short_domain", "")
    public_url = short_domain.rstrip("/") if short_domain else proxy_url

    # Get friendly channel name from DB
    ch_record = db.get_channel_by_url(decoded_url)
    channel_name = ch_record["name"] if ch_record else (
        decoded_url.split("/")[-2] if "/ch" in decoded_url else decoded_url.split("/")[-1].split("?")[0]
    )

    _req_ip_common = ""
    if request:
        _fwd_ip_common = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        _req_ip_common = _fwd_ip_common or (request.client.host if request.client else "")
    _now_common = time.time()
    _catchup_live_break_active = False
    _catchup_live_break_lock_url = ""
    _catchup_live_break_lock_channel = channel_name
    _catchup_live_break_until = 0.0
    for _k_cb, _cv_cb in _catchup_sessions.items():
        if _cv_cb.get("token") != token:
            continue
        _sess_ip_cb = (_cv_cb.get("ip") or "").strip()
        if _req_ip_common and _sess_ip_cb and _sess_ip_cb != _req_ip_common:
            continue
        if (_now_common - float(_cv_cb.get("last_seen", 0))) > max(30, _catchup_idle_ttl_seconds(_cv_cb)):
            continue
        _allow_until = float(_cv_cb.get("allow_live_until", 0))
        if _now_common >= _allow_until:
            continue
        _cb_channel = _k_cb.split("::")[-1] if "::" in _k_cb else channel_name
        _cb_live_url = (_cv_cb.get("live_url") or "").strip()
        if _allow_until > _catchup_live_break_until:
            _catchup_live_break_until = _allow_until
            _catchup_live_break_lock_url = _cb_live_url
            _catchup_live_break_lock_channel = _cb_channel
            _catchup_live_break_active = True

    # During the live-break window, ignore incoming utc catchup requests for this channel
    # so clients cannot immediately pull us back into catchup after auto-live redirect.
    if utc and _catchup_live_break_active:
        if _catchup_live_break_lock_url:
            decoded_url = _catchup_live_break_lock_url
            channel_name = _catchup_live_break_lock_channel or channel_name
        diag_log(
            "INFO",
            "catchup",
            f"Catchup live-break: ignore utc and keep live for {user['name']} → {channel_name}",
        )
        _log_player_request(
            "stream:ignore_utc_live_break",
            request,
            token,
            {"channel": channel_name, "utc_in": utc},
        )
        utc = None

    # During the live-break window, only allow the lock channel in live mode.
    # Any accidental live jump to a different channel is forced back.
    if (
        not utc
        and _catchup_live_break_active
        and _catchup_live_break_lock_url
        and decoded_url != _catchup_live_break_lock_url
    ):
        _redir_lb = f"/iptv/{token}/stream?url={urllib.parse.quote(_catchup_live_break_lock_url, safe='')}"
        diag_log(
            "INFO",
            "catchup",
            f"Catchup live-break channel lock: redirect {channel_name} -> {_catchup_live_break_lock_channel} for {user['name']}",
        )
        _log_player_request(
            "stream:redirect_live_break_same_channel",
            request,
            token,
            {"requested_channel": channel_name, "redirect_channel": _catchup_live_break_lock_channel},
        )
        return RedirectResponse(url=_redir_lb)

    # Catchup hard lock:
    # While a catchup session is active, force plain live stream requests back to catchup utc.
    if not utc and (not _catchup_live_break_active) and is_catchup_guard_master_enabled() and is_catchup_hard_lock_enabled():
        _req_ip_hl = ""
        if request:
            _fwd_ip_hl = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            _req_ip_hl = _fwd_ip_hl or (request.client.host if request.client else "")
        _now_hl = time.time()
        _best_key = ""
        _best_cv = None
        for _k_hl, _cv_hl in _catchup_sessions.items():
            if _cv_hl.get("token") != token:
                continue
            _sess_ip_hl = (_cv_hl.get("ip") or "").strip()
            if _req_ip_hl and _sess_ip_hl and _sess_ip_hl != _req_ip_hl:
                continue
            _idle_gap_hl = _now_hl - float(_cv_hl.get("last_seen", 0))
            if _idle_gap_hl > max(30, _catchup_idle_ttl_seconds(_cv_hl)):
                continue
            if _best_cv is None:
                _best_key = _k_hl
                _best_cv = _cv_hl
                continue
            _best_ch = _best_key.split("::")[-1] if "::" in _best_key else ""
            _cur_ch = _k_hl.split("::")[-1] if "::" in _k_hl else ""
            if _cur_ch == channel_name and _best_ch != channel_name:
                _best_key = _k_hl
                _best_cv = _cv_hl
                continue
            if float(_cv_hl.get("last_seen", 0)) > float(_best_cv.get("last_seen", 0)):
                _best_key = _k_hl
                _best_cv = _cv_hl

        if _best_cv and _best_key:
            _cw_hl = (_best_cv.get("catchup_time") or "").strip()
            _ct_hl = _parse_catchup_wall_time(_cw_hl) if _cw_hl else None
            _live_url_hl = (_best_cv.get("live_url") or "").strip() or decoded_url
            _hl_channel = _best_key.split("::")[-1] if "::" in _best_key else channel_name
            if _ct_hl and _live_url_hl:
                _utc_hl = int(_ct_hl.timestamp())
                _redir_hl = f"/iptv/{token}/stream?url={urllib.parse.quote(_live_url_hl, safe='')}&utc={_utc_hl}"
                diag_log(
                    "INFO",
                    "catchup",
                    f"Catchup hard-lock: redirect live->catchup for {user['name']} → {_hl_channel} @ {_cw_hl}",
                )
                _log_player_request(
                    "stream:redirect_catchup_hard_lock",
                    request,
                    token,
                    {"requested_channel": channel_name, "lock_channel": _hl_channel, "catchup_time": _cw_hl, "redirect_utc": _utc_hl},
                )
                return RedirectResponse(url=_redir_hl)

    # Sticky catchup recovery:
    # Some clients switch to live URL after a transient catchup failure.
    # If a recent catchup session exists for the same token/channel, redirect back to catchup UTC.
    if not utc and (not _catchup_live_break_active) and is_catchup_guard_master_enabled() and is_catchup_force_same_channel_live_enabled():
        _req_ip = ""
        if request:
            _fwd_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            _req_ip = _fwd_ip or (request.client.host if request.client else "")
        _now = time.time()
        _recent_cv = None
        _recent_ck = ""
        for _k, _v in _catchup_sessions.items():
            if _v.get("token") != token:
                continue
            if _req_ip and (_v.get("ip") or "").strip() and (_v.get("ip") or "").strip() != _req_ip:
                continue
            if (_now - float(_v.get("last_seen", 0))) > 75:
                continue
            if _recent_cv is None or float(_v.get("last_seen", 0)) > float(_recent_cv.get("last_seen", 0)):
                _recent_cv = _v
                _recent_ck = _k
        if _recent_cv and _recent_ck:
            _cu_channel = _recent_ck.split("::")[-1] if "::" in _recent_ck else ""
            _cu_live_url = (_recent_cv.get("live_url") or "").strip()
            if _cu_channel and _cu_live_url and _cu_channel != channel_name:
                _redir_live_same = f"/iptv/{token}/stream?url={urllib.parse.quote(_cu_live_url, safe='')}"
                diag_log(
                    "INFO",
                    "catchup",
                    f"Catchup live channel guard: {user['name']} requested live {channel_name}, redirect to {_cu_channel}",
                )
                _log_player_request(
                    "stream:redirect_live_same_channel",
                    request,
                    token,
                    {"requested_channel": channel_name, "redirect_channel": _cu_channel},
                )
                return RedirectResponse(url=_redir_live_same)

    if not utc and (not _catchup_live_break_active) and is_catchup_guard_master_enabled() and is_catchup_sticky_recover_enabled():
        _ck = f"catchup::{token}::{channel_name}"
        _cv = _catchup_sessions.get(_ck)
        if _cv:
            _now = time.time()
            _idle_ttl = _catchup_idle_ttl_seconds(_cv)
            _is_recent = (_now - float(_cv.get("last_seen", 0))) <= max(30, _idle_ttl)
            _same_ip = True
            if request:
                _fwd_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                _req_ip = _fwd_ip or (request.client.host if request.client else "")
                _sess_ip = (_cv.get("ip") or "").strip()
                if _sess_ip and _req_ip:
                    _same_ip = _sess_ip == _req_ip
            _cw = (_cv.get("catchup_time") or "").strip()
            _ct = _parse_catchup_wall_time(_cw) if _cw else None
            if _is_recent and _same_ip and _ct:
                _utc_rec = int(_ct.timestamp())
                _redir = f"/iptv/{token}/stream?url={urllib.parse.quote(decoded_url, safe='')}&utc={_utc_rec}"
                diag_log(
                    "INFO",
                    "catchup",
                    f"Sticky catchup recover: redirect live->catchup for {user['name']} → {channel_name} @ {_cw}",
                )
                _log_player_request("stream:redirect_sticky_catchup", request, token, {"channel": channel_name, "catchup_time": _cw, "redirect_utc": _utc_rec})
                return RedirectResponse(url=_redir)

    # ── CATCHUP MODE ──────────────────────────────────────────────────────────
    # Catchup requests bypass max-stream check – they don't hold a live session
    if utc:
        try:
            # Build archive URL: replace mono.m3u8 with index.m3u8 + utc param
            base_cdn = decoded_url.rsplit("/mono.m3u8", 1)[0]
            ch_token = decoded_url.split("token=")[-1] if "token=" in decoded_url else ""
            archive_url = f"{base_cdn}/index.m3u8?token={ch_token}&utc={utc}"

            _cu_to = catchup_upstream_httpx_timeout(hls)
            archive_content = None
            for _cu_attempt in range(3):
                try:
                    async with make_iptv_client(
                        timeout=_cu_to,
                        follow_redirects=True,
                        headers=make_headers(hls),
                    ) as client:
                        resp = await client.get(archive_url)
                        resp.raise_for_status()
                        archive_content = resp.text
                    break
                except httpx.HTTPStatusError as _cu_http:
                    _code = _cu_http.response.status_code if _cu_http.response is not None else 0
                    if _cu_attempt < 2 and _code in (408, 429, 500, 502, 503, 504):
                        await asyncio.sleep(0.2 * (_cu_attempt + 1))
                        diag_log(
                            "WARNING",
                            "catchup",
                            f"Catchup index.m3u8 HTTP {_code}, retry {_cu_attempt + 2}/3",
                        )
                        continue
                    raise
                except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as _cu_net:
                    if _cu_attempt >= 2:
                        diag_log("ERROR", "catchup", f"Catchup index.m3u8 failed after retries: {_cu_net!r}")
                        raise
                    await asyncio.sleep(0.2 * (_cu_attempt + 1))
                    diag_log(
                        "WARNING",
                        "catchup",
                        f"Catchup index.m3u8 {_cu_net.__class__.__name__}, retry {_cu_attempt + 2}/3",
                    )

            # Rewrite segment URLs through our proxy (catchup=True skips session tracking)
            rewritten = rewrite_hls_playlist(archive_content, archive_url, public_url, token, catchup=True)
            # Extract real catchup time from DVR segment URLs (e.g. dvr-2026/05/01/13/24/...)
            import re as _re_dvr
            _dvr_m = _re_dvr.search(r'dvr-(\d{4})/(\d{2})/(\d{2})/(\d{2})/(\d{2})', archive_content)
            if _dvr_m:
                _y,_mo,_d,_h,_mi = _dvr_m.groups()
                dt_str = f"{_y}-{_mo}-{_d} {_h}:{_mi}:00"
            else:
                dt_str = datetime.fromtimestamp(int(utc), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Catchup playlist: {user['name']} → {channel_name} @ {dt_str}")
            # Log catchup access (no session, just a single log entry)
            try:
                # Look up EPG title for this catchup timestamp
                _catchup_epg_title = None
                try:
                    _epg_content = _epg_cache.get("content")
                    if not _epg_content:
                        try:
                            with open("/data/epg_cache.xml","r",encoding="utf-8") as _ef:
                                _epg_content = _ef.read()
                        except Exception:
                            pass
                    if _epg_content:
                        _root = ET.fromstring(_epg_content)
                        _t = _epg_title_at_time_half_open(channel_name, dt_str, _root)
                        _catchup_epg_title = _t if _t else None
                except Exception:
                    pass
                _catchup_ip = ""
                if request:
                    _fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                    _catchup_ip = _fwd or (request.client.host if request.client else "")
                _catchup_key = f"catchup::{token}::{channel_name}"
                now_cu = time.time()
                existing_cu = _catchup_sessions.get(_catchup_key)

                if existing_cu and now_cu - existing_cu.get("last_seen", 0) < _catchup_idle_ttl_seconds(existing_cu):
                    # Player may request the catchup master playlist repeatedly.
                    # Reuse the active log instead of creating one watch_log row per request.
                    existing_cu["last_seen"] = now_cu
                    existing_cu["live_url"] = decoded_url
                    existing_cu["catchup_time"] = dt_str
                    existing_cu["last_dvr_dt_str"] = dt_str
                    db.session_refresh(token)

                    old_epg = (existing_cu.get("epg_title") or "").strip()
                    new_epg = (_catchup_epg_title or "").strip()
                    if new_epg and old_epg and new_epg != old_epg:
                        _split_watch_log_on_show_change(
                            existing_cu,
                            new_epg,
                            is_catchup=True,
                            catchup_time=dt_str,
                            channel=channel_name,
                        )
                    else:
                        if new_epg and not old_epg:
                            existing_cu["epg_title"] = new_epg
                        try:
                            with db.conn() as con:
                                if new_epg:
                                    con.execute(
                                        "UPDATE watch_logs SET catchup_time = ?, epg_title = ? WHERE id = ?",
                                        (dt_str, new_epg, existing_cu["log_id"]),
                                    )
                                else:
                                    con.execute(
                                        "UPDATE watch_logs SET catchup_time = ? WHERE id = ?",
                                        (dt_str, existing_cu["log_id"]),
                                    )
                        except Exception:
                            pass
                    _cu_msg = f"Catchup session reused: {user['name']} → {channel_name} @ {dt_str} ({_catchup_epg_title or 'no epg'})"
                    logger.info(_cu_msg)
                    diag_log("INFO", "catchup", _cu_msg)
                else:
                    if existing_cu:
                        # Stale memory entry that cleanup has not processed yet.
                        try:
                            db.end_watch_log(
                                existing_cu["log_id"],
                                int(now_cu - existing_cu.get("log_start", existing_cu.get("start", now_cu))),
                                epg_title=existing_cu.get("epg_title") or None,
                            )
                        except Exception:
                            pass
                        _catchup_sessions.pop(_catchup_key, None)

                    log_id = db.start_watch_log(
                        user_id=user["id"], channel=channel_name, stream_url=decoded_url,
                        ip_address=_catchup_ip,
                        is_catchup=1, catchup_time=dt_str, epg_title=_catchup_epg_title
                    )
                    # Don't end immediately – track duration via segment requests
                    _catchup_sessions[_catchup_key] = {
                        "log_id": log_id, "start": now_cu, "log_start": now_cu,
                        "last_seen": now_cu,
                        "token": token, "ip": _catchup_ip,
                        "user_id": user["id"],
                        "channel": channel_name,
                        "epg_title": _catchup_epg_title or "",
                        "catchup_time": dt_str,
                        "live_url": decoded_url,
                        "auto_live_pending": False,
                        "allow_live_until": 0.0,
                        "last_dvr_dt_str": dt_str,
                        "saw_endlist": False,
                        "endlist_seen_at": None,
                    }
                    # Show catchup in live sessions view
                    db.session_start(token, channel_name, _catchup_ip)
                    _cu_msg = f"Catchup logged: {user['name']} → {channel_name} @ {dt_str} ({_catchup_epg_title or 'no epg'})"
                    logger.info(_cu_msg)
                    diag_log("INFO", "catchup", _cu_msg)
                if "#EXT-X-ENDLIST" in archive_content:
                    _catchup_mark_endlist(token, archive_url)
                    _diag_log_catchup_endlist_epg_context(
                        user.get("name", "") or "",
                        channel_name,
                        dt_str,
                        where="index.m3u8 (Catchup-Start)",
                    )
            except Exception as _ce:
                logger.warning(f"Catchup log failed: {_ce}")
                diag_log("WARNING", "catchup", f"Catchup log failed: {_ce}")
            _log_player_request(
                "stream:catchup_playlist_response",
                request,
                token,
                {"channel": channel_name, "utc": utc, "playlist_len": len(rewritten)},
            )
            return HTMLResponse(
                content=rewritten,
                media_type="application/vnd.apple.mpegurl",
                headers={"Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*"}
            )
        except Exception as e:
            logger.error(f"Catchup error: {e}")
            diag_log("ERROR", "catchup", f"Catchup error: {e}")
            if is_catchup_strict_mode():
                diag_log(
                    "INFO",
                    "catchup",
                    f"Catchup strict mode active: no live fallback for {user['name']} → {channel_name} (utc={utc})",
                )
                raise HTTPException(status_code=502, detail=f"Catchup fetch failed: {e}")
            diag_log(
                "WARNING",
                "catchup",
                f"Catchup failed, fallback to live enabled: {user['name']} → {channel_name} (utc={utc})",
            )
            _log_player_request("stream:catchup_error_fallback_live", request, token, {"channel": channel_name, "utc": utc}, level="WARNING")
            # Fall through to live when strict mode is disabled.

    # ── LIVE MODE ─────────────────────────────────────────────────────────────
    # Check max concurrent streams only for live mode
    max_s = user.get("max_streams", 1) or 0
    if max_s > 0:
        _cleanup_sessions()
        uid = user["id"]
        _fwd3 = request.headers.get("x-forwarded-for","").split(",")[0].strip()
        _ip3 = _fwd3 or (request.client.host if request.client else "")
        _ua3 = request.headers.get("user-agent","")[:60]
        _sid3 = hashlib.md5(f"{token}::{_ip3}::{_ua3}".encode()).hexdigest()[:16]
        _this_key = f"{token}::sid::{_sid3}"
        other = [s for s in _sessions.values()
                 if s["user_id"] == uid and s.get("session_key") != _this_key]
        if len(other) >= max_s:
            logger.warning(f"Stream blocked: {user['name']} {len(other)}/{max_s} from {_ip3}")
            diag_log("WARNING", "stream", f"Stream blocked: {user['name']} {len(other)}/{max_s} from {_ip3}")
            _ms_url = f"{public_url}/iptv/error-max-streams.ts"
            _ms_m3u = _build_loop_playlist(_ms_url)
            return HTMLResponse(content=_ms_m3u, media_type="application/x-mpegURL", headers={"Cache-Control": "no-cache"})

    try:
        live_timeout = httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"])
        live_headers = make_headers(hls)

        # For .ts URLs (Xtream live streams): check if it's really an M3U8 or a direct TS stream
        # HLS .m3u8 stream — fetch playlist and rewrite segment URLs
        async with make_iptv_client(
            timeout=live_timeout,
            follow_redirects=hls["hls_follow_redirects"],
            headers=live_headers
        ) as client:
            resp = await client.get(decoded_url)
            resp.raise_for_status()
            playlist_content = resp.text

        # Generate stable SID: same device = same SID = same session
        _fwd2 = request.headers.get("x-forwarded-for","").split(",")[0].strip()
        _ip2 = _fwd2 or (request.client.host if request.client else "")
        _ua2 = request.headers.get("user-agent","")[:60]
        sid = hashlib.md5(f"{token}::{_ip2}::{_ua2}".encode()).hexdigest()[:16]
        rewritten = rewrite_hls_playlist(playlist_content, decoded_url, public_url, token, sid=sid)
        logger.info(f"HLS playlist served: {user['name']} → {channel_name}")

        # Keep live session alive on playlist refreshes (ExoPlayer polls m3u8 frequently).
        # Without this, cleanup can kill an active session while segments are still slow/blocked.
        try:
            _now_ls = time.time()
            _sk_ls = f"{token}::sid::{sid}"
            if _sk_ls in _sessions:
                _sessions[_sk_ls]["last_seen"] = _now_ls
                db.session_refresh(token)
                _live_check_show_change(_sessions[_sk_ls], channel_name, _now_ls)
            else:
                # If not started yet (edge cases), align with segment path by creating a session here too.
                max_s_ls = user.get("max_streams", 1) or 0
                if max_s_ls > 0:
                    _cleanup_sessions()
                    _other_ls = [
                        s for s in _sessions.values()
                        if s["user_id"] == user["id"] and s.get("session_key") != _sk_ls
                    ]
                    if len(_other_ls) >= max_s_ls:
                        logger.warning(f"Stream blocked: {user['name']} {len(_other_ls)}/{max_s_ls} from {_ip2}")
                        diag_log("WARNING", "stream", f"Stream blocked: {user['name']} {len(_other_ls)}/{max_s_ls} from {_ip2}")
                        _ms_url = f"{public_url}/iptv/error-max-streams.ts"
                        _ms_m3u = _build_loop_playlist(_ms_url)
                        return HTMLResponse(content=_ms_m3u, media_type="application/x-mpegURL", headers={"Cache-Control": "no-cache"})
                db.session_start(token, channel_name, ip_address=_ip2)
                _epg_now_ls = _get_now_playing(channel_name)
                _epg_title_ls = _epg_now_ls.get("title") if _epg_now_ls else None
                _log_id_ls = db.start_watch_log(
                    user_id=user["id"],
                    channel=channel_name,
                    stream_url=decoded_url,
                    ip_address=_ip2,
                    epg_title=_epg_title_ls,
                )
                _sessions[_sk_ls] = {
                    "channel": channel_name,
                    "log_id": _log_id_ls,
                    "start": _now_ls,
                    "log_start": _now_ls,
                    "last_seen": _now_ls,
                    "user_id": user["id"],
                    "token": token,
                    "session_key": _sk_ls,
                    "epg_title": _epg_title_ls,
                    "user_name": user["name"],
                    "stream_url": decoded_url,
                    "ip_address": _ip2,
                }
                logger.info(f"Session started (playlist): {user['name']} ({_ip2}) → {channel_name}")
        except HTTPException:
            raise
        except Exception as _e_ls_sess:
            logger.warning(f"Live session touch failed: {_e_ls_sess}")

        # Prefetch next segments in background
        try:
            base_url = "/".join(decoded_url.split("/")[:-1])
            seg_urls = []
            prefetch_count = get_prefetch_count()
            for line in playlist_content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and (".ts" in line or ".aac" in line):
                    full_url = line if line.startswith("http") else f"{base_url}/{line}"
                    if full_url not in _prefetch_cache:
                        seg_urls.append(full_url)
                    if len(seg_urls) >= prefetch_count:
                        break
            if prefetch_count > 0:
                for seg_url in seg_urls:
                    asyncio.create_task(_prefetch_segment(seg_url, hls))
        except Exception:
            pass
        _log_player_request(
            "stream:live_playlist_response",
            request,
            token,
            {"channel": channel_name, "playlist_len": len(rewritten), "sid": sid},
        )
        return HTMLResponse(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        _log_player_request("stream:error", request, token, {"channel": channel_name, "error": repr(e)}, level="ERROR")
        logger.error(f"Failed to fetch stream for {user['name']}: {e}")
        diag_log("ERROR", "stream", f"Failed to fetch stream for {user['name']}: {e}")
        raise HTTPException(status_code=502, detail=f"Stream fetch failed: {e}")


# In-memory session tracking
# {session_key: {"channel": str, "log_id": int, "start": float, "last_seen": float, "user_id": int, "token": str}}
_sessions: dict = {}
SESSION_MEM_TTL = 35  # seconds without segment = session dead

# Shared segment cache: {url: bytes} – downloaded segments shared across users
# Prevents downloading the same segment multiple times when users watch the same channel
_segment_cache: dict = {}
_segment_cache_time: dict = {}  # {url: timestamp}
_segment_in_progress: dict = {}  # {url: asyncio.Event} – deduplication lock
SEGMENT_CACHE_TTL = 30  # seconds

def _get_segment_cache_max() -> int:
    """Dynamic cache size: base 30 + 10 per active stream (prefetch 2 ahead each).
    Ensures segments are never evicted while another user might need them."""
    active = len(_sessions)
    prefetch = get_prefetch_count()
    return max(30, active * (prefetch + 2) + 10)

# Keep SEGMENT_CACHE_MAX as a fallback constant
SEGMENT_CACHE_MAX = 30

def get_prefetch_count() -> int:
    """How many segments to prefetch ahead. 0 = disabled."""
    try:
        return int(db.get_setting("prefetch_segments", "2"))
    except Exception:
        return 2

# Keep _prefetch_cache as alias for compatibility
_prefetch_cache = _segment_cache


_segment_cache_elapsed: dict = {}  # {url: elapsed_seconds} – original download time

async def _get_segment(url: str, hls: dict) -> tuple:
    """Download a segment, sharing the result if another coroutine is already fetching it.
    Returns (data: bytes, elapsed: float, from_cache: bool).
    elapsed = actual download time for fresh fetch, near-zero for cache hits."""
    now = time.time()

    # Clean expired cache entries
    expired = [u for u, t in _segment_cache_time.items() if now - t > SEGMENT_CACHE_TTL]
    for u in expired:
        _segment_cache.pop(u, None)
        _segment_cache_time.pop(u, None)
        _segment_cache_elapsed.pop(u, None)

    # Cache hit – return instantly with near-zero elapsed (local delivery)
    if url in _segment_cache:
        t_cache = time.time()
        data = _segment_cache[url]
        cache_elapsed = time.time() - t_cache  # effectively 0
        return data, cache_elapsed, True

    # Another coroutine is already fetching this segment – wait for it
    if url in _segment_in_progress:
        t_wait_start = time.time()
        evt = _segment_in_progress[url]
        await asyncio.wait_for(evt.wait(), timeout=30)
        wait_elapsed = time.time() - t_wait_start
        # Leader only caches bodies >100 bytes. If upstream was empty/short, cache is empty
        # but we must not treat that as a cache hit — otherwise every waiter logs LEER for the same URL.
        data_wait = _segment_cache.get(url, b"")
        if len(data_wait) > 100:
            return data_wait, wait_elapsed, True
        return await _get_segment(url, hls)

    # We are the first – fetch it
    evt = asyncio.Event()
    _segment_in_progress[url] = evt
    try:
        buf = bytearray()
        t_start = time.time()
        async with make_iptv_client(
            timeout=httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"]),
            follow_redirects=hls["hls_follow_redirects"],
            headers=make_headers(hls)
        ) as client:
            async with client.stream("GET", url) as resp:
                # Manche CDNs liefern kurzzeitig 204/empty body oder 200 mit 0 bytes,
                # bevor das Segment wirklich verfügbar ist. Ohne Status-Check landet das als "leeres Segment"
                # im Cache-Pfad und bricht Clients + Live-Sessions weg.
                if resp.status_code not in (200, 206):
                    elapsed = time.time() - t_start
                    return b"", elapsed, False
                async for chunk in resp.aiter_bytes(chunk_size=131072):
                    buf.extend(chunk)
        elapsed = time.time() - t_start
        data = bytes(buf)
        if len(data) > 100:
            _segment_cache[url] = data
            _segment_cache_time[url] = now
            _segment_cache_elapsed[url] = elapsed
            cache_max = _get_segment_cache_max()
            while len(_segment_cache) > cache_max:
                oldest = min(_segment_cache_time, key=_segment_cache_time.get)
                _segment_cache.pop(oldest, None)
                _segment_cache_time.pop(oldest, None)
                _segment_cache_elapsed.pop(oldest, None)
        return data, elapsed, False
    finally:
        _segment_in_progress.pop(url, None)
        evt.set()


async def _prefetch_segment(url: str, hls: dict):
    """Prefetch a segment in the background using the shared cache."""
    if url in _segment_cache:
        return
    try:
        await _get_segment(url, hls)
    except Exception:
        pass
# Catchup session tracking (log_id → {start, last_seen, token})
_catchup_sessions: dict = {}


def _resolve_catchup_session_key(token: str, decoded_url: str) -> Optional[str]:
    """Pick which catchup::* session a segment URL belongs to (same token can have multiple channels)."""
    keys = [_ck for _ck, _cv in _catchup_sessions.items() if _cv.get("token") == token]
    if not keys:
        return None
    if len(keys) == 1:
        return keys[0]
    ch_rec = db.get_channel_by_url_fragment(decoded_url)
    if ch_rec:
        ck = f"catchup::{token}::{ch_rec['name']}"
        if ck in _catchup_sessions:
            return ck
    # Newest session wins if URL does not contain /chNNN/ (avoids starving active catchup).
    return max(keys, key=lambda k: float(_catchup_sessions[k].get("start", 0)))


def _touch_catchup_last_seen(token: str, decoded_url: str) -> None:
    ck = _resolve_catchup_session_key(token, decoded_url)
    if ck and ck in _catchup_sessions:
        _catchup_sessions[ck]["last_seen"] = time.time()


async def _catchup_segment_idle_heartbeat(token: str, decoded_url: str) -> None:
    """Refresh last_seen during long TS downloads so idle cleanup cannot fire mid-segment (catchup_ttl)."""
    try:
        while True:
            await asyncio.sleep(30)
            _touch_catchup_last_seen(token, decoded_url)
    except asyncio.CancelledError:
        return


# _DVR_PATH_RE und _dvr_wall_time_from_url liegen jetzt in timeparse.py.


def _epg_title_from_wall_time_channel(channel_name: str, wall_dt_str: str) -> Optional[str]:
    try:
        ct = _parse_catchup_wall_time(wall_dt_str)
        if not ct:
            return None
        epg_c = _epg_cache.get("content")
        if not epg_c:
            try:
                with open("/data/epg_cache.xml", "r", encoding="utf-8") as f:
                    epg_c = f.read()
            except Exception:
                return None
        if not epg_c:
            return None
        root = ET.fromstring(epg_c)
        ch_rec = db.get_channel_by_name(channel_name) or {}
        tvg = ch_rec.get("tvg_id", "").strip()
        if not tvg:
            return None
        for prog in root.findall("programme"):
            if prog.get("channel", "") != tvg:
                continue
            ps = _parse_xmltv_datetime(prog.get("start", ""))
            pe = _parse_xmltv_datetime(prog.get("stop", ""))
            # Half-open: minute-rounded DVR times sit on boundaries less often on the wrong programme.
            if _epg_programme_contains_instant_half_open(ps, pe, ct):
                t = (prog.findtext("title") or "").strip()
                return t or None
        return None
    except Exception:
        return None


def _epg_programme_stop_for_title_at_dt(channel_name: str, ct: datetime, title_wanted: str):
    """XMLTV stop time for the programme half-open-containing ct with this title (for sticky catchup titles)."""
    if not channel_name or not title_wanted or not ct:
        return None
    tw = title_wanted.strip()
    if not tw:
        return None
    try:
        epg_c = _epg_cache.get("content")
        if not epg_c:
            try:
                with open("/data/epg_cache.xml", "r", encoding="utf-8") as f:
                    epg_c = f.read()
            except Exception:
                return None
        if not epg_c:
            return None
        root = ET.fromstring(epg_c)
        ch_rec = db.get_channel_by_name(channel_name) or {}
        tvg = ch_rec.get("tvg_id", "").strip()
        if not tvg:
            return None
        for prog in root.findall("programme"):
            if prog.get("channel", "") != tvg:
                continue
            ps = _parse_xmltv_datetime(prog.get("start", ""))
            pe = _parse_xmltv_datetime(prog.get("stop", ""))
            if not _epg_programme_contains_instant_half_open(ps, pe, ct):
                continue
            if (prog.findtext("title") or "").strip() != tw:
                continue
            return pe
        return None
    except Exception:
        return None


def _epg_slot_detail_at_dt(channel_name: str, ct: datetime) -> Optional[dict]:
    """Half-open EPG slot containing ct — for diagnostic explanations."""
    if not channel_name or not ct:
        return None
    try:
        epg_c = _epg_cache.get("content")
        if not epg_c:
            try:
                with open("/data/epg_cache.xml", "r", encoding="utf-8") as f:
                    epg_c = f.read()
            except Exception:
                return None
        if not epg_c:
            return None
        root = ET.fromstring(epg_c)
        ch_rec = db.get_channel_by_name(channel_name) or {}
        tvg = ch_rec.get("tvg_id", "").strip()
        if not tvg:
            return None
        for prog in root.findall("programme"):
            if prog.get("channel", "") != tvg:
                continue
            ps = _parse_xmltv_datetime(prog.get("start", ""))
            pe = _parse_xmltv_datetime(prog.get("stop", ""))
            if not _epg_programme_contains_instant_half_open(ps, pe, ct):
                continue
            title = (prog.findtext("title") or "").strip()
            return {
                "title": title,
                "start_xmltv": (prog.get("start") or "").strip(),
                "stop_xmltv": (prog.get("stop") or "").strip(),
                "start_iso": ps.isoformat() if ps else "",
                "stop_iso": pe.isoformat() if pe else "",
            }
        return None
    except Exception:
        return None


def _diag_log_catchup_endlist_epg_context(
    user_name: str,
    channel_name: str,
    catchup_wall_str: str,
    *,
    where: str,
) -> None:
    """When upstream playlist contains #EXT-X-ENDLIST: explain vs EPG nominal programme length."""
    uname = user_name or ""
    ch = (channel_name or "").strip()
    cw = (catchup_wall_str or "").strip()
    ct = _parse_catchup_wall_time(cw) if cw else None
    head = (
        f"Catchup ENDLIST ({where}): {uname} → {ch or '?'} | Session-Positionszeit {cw or '(unbekannt)'}. "
        "Die Playlist enthält #EXT-X-ENDLIST vom Anbieter — danach liefert dieses Stück keine weiteren Segmente."
    )
    if not ch or not ct:
        diag_log(
            "INFO",
            "catchup",
            head
            + "\nEPG-Vergleich übersprungen (Kanal oder Zeit fehlt). "
            "Schwankende Abspiellängen trotz gleichem Film: oft anderer utc-/Startzeitpunkt oder CDN-Fenster — "
            "selfstream kann ohne neue Anbieter-Playlist nicht verlängern.",
        )
        return
    slot = _epg_slot_detail_at_dt(ch, ct)
    if not slot:
        diag_log(
            "INFO",
            "catchup",
            head
            + "\nEPG: keine Sendung zur Positionsminute (tvg_id/Lücke). "
            "Hinweis: variable Enden bei gleicher Auswahl passieren häufig durch Archiv-Fenster/Limits beim IPTV-Anbieter.",
        )
        return
    ps = _parse_xmltv_datetime(slot["start_xmltv"])
    pe = _parse_xmltv_datetime(slot["stop_xmltv"])
    tit = slot.get("title") or "(ohne Titel)"
    tail_parts = [head]
    if ps and pe:
        dur_min = max(0.0, (pe - ps).total_seconds()) / 60.0
        pos_min = max(0.0, (ct - ps).total_seconds()) / 60.0 if ct >= ps else 0.0
        rem_sec = (pe - ct).total_seconds()
        rem_min = rem_sec / 60.0
        h_epg = dur_min // 60
        m_epg = dur_min % 60
        len_human = f"{int(h_epg)}h {int(m_epg)}m" if h_epg >= 1 else f"{dur_min:.0f} Min"
        tail_parts.append(
            f"EPG (Vergleich zur Positionsminute): „{tit}“ geplant "
            f"{slot['start_xmltv']} → {slot['stop_xmltv']} (nominal ~{len_human} Sendelänge)."
        )
        tail_parts.append(
            f"Diese Minute liegt ~{pos_min:.1f} Min nach EPG-Sendungsbeginn; bis zum EPG-Endzeitpunkt noch ~{rem_min:.1f} Min."
        )
        if rem_sec > 15 * 60:
            tail_parts.append(
                "ACHTUNG: Playlist-Ende (ENDLIST), aber EPG lässt die Sendung noch deutlich länger laufen — "
                "typisch kurzes Archiv-/Rolling-Fenster beim Anbieter, nicht eine von selfstream gewählte Abbruchdauer."
            )
        elif rem_sec > 0:
            tail_parts.append(
                "Einordnung: noch Restlaufzeit im EPG; kurzes CDN-Fenster oder nächste Playlist-Generation beim Anbieter möglich."
            )
        else:
            tail_parts.append(
                "Einordnung: Positionszeit liegt am oder nach dem EPG-Endzeitpunkt — Ende der Playlist kann zur Rasterzeit passen."
            )
    else:
        tail_parts.append(f"EPG-Slot „{tit}“ gefunden, Start/Stopp nicht eindeutig parsebar.")
    tail_parts.append(
        "Was wir nicht zuverlässig clientseitig fixen können: fehlende oder verkürzte Mediensegmente nach ENDLIST; "
        "andere Längen bei identischer Auswahl prüfen bei Anbieter (utc, Zeitzone, Gerät, parallele Live-Session)."
    )
    diag_log("INFO", "catchup", "\n".join(tail_parts))


def _catchup_diag_segment_tail(decoded_url: str) -> str:
    try:
        return decoded_url.split("/")[-1].split("?")[0][:96]
    except Exception:
        return ""


def _catchup_format_dvr_sync_message(
    *,
    user_name: str,
    ch_name: str,
    source: str,
    old_dt: str,
    new_dt_str: str,
    old_epg: str,
    disp_epg: str,
    decoded_url: str,
    new_epg: Optional[str],
    old_epg_clean: str,
    sticky: bool,
    cur_parsed,
    new_parsed,
    pe_slot,
) -> str:
    seg = _catchup_diag_segment_tail(decoded_url)
    head = (
        f"Catchup DVR ({source}): {user_name} → {ch_name} | Positionszeit {old_dt} → {new_dt_str} "
        f"| Anzeige-Titel {old_epg!r} → {disp_epg!r}"
    )
    if seg:
        head += f" | Segment …/{seg}"

    slot_new = _epg_slot_detail_at_dt(ch_name, new_parsed) if new_parsed else None
    slot_cur = _epg_slot_detail_at_dt(ch_name, cur_parsed) if cur_parsed else None

    parts = [
        "Ursache: Die Positionsminute kommt aus dem DVR-/CDN-Pfad im Segment oder der Playlist (nicht aus der Wanduhr des TVs)."
    ]
    if slot_new:
        parts.append(
            f"EPG-Zuordnung für die neue Minute (XMLTV halb-offen [start,stop)): „{slot_new['title']}“ "
            f"(start={slot_new['start_xmltv'] or slot_new['start_iso']}, stop={slot_new['stop_xmltv'] or slot_new['stop_iso']})."
        )
    elif new_parsed:
        parts.append(
            "Für die neue Minute liefert das EPG keine Sendung (Lücke, falsche tvg_id oder Zeit nicht im Cache)."
        )

    if sticky and pe_slot is not None:
        parts.append(
            f"Titelwechsel zunächst unterdrückt (sticky): Die zuletzt angezeigte Sendung „{old_epg_clean}“ hat laut EPG Endzeit {pe_slot.isoformat()}; "
            f"die neue DVR-Minute liegt noch davor — es wird nur die Zeit fortgeschrieben, der Titel bleibt."
        )
    elif new_epg and old_epg_clean and new_epg.strip() != old_epg_clean:
        same_half_open_slot = bool(
            slot_cur
            and slot_new
            and (slot_cur.get("title") or "").strip() == (slot_new.get("title") or "").strip()
            and (slot_cur.get("start_xmltv") or slot_cur.get("start_iso"))
            == (slot_new.get("start_xmltv") or slot_new.get("start_iso"))
        )
        if same_half_open_slot:
            parts.append(
                "Titelkorrektur (kein Sendungswechsel): Der beim Start gespeicherte Titel entsprach nicht der halb-offenen "
                "XMLTV-Zuordnung zu dieser DVR-Minute (Start nutzte früher inklusive Grenzen). Der EPG-Slot ist durchgehend "
                f"„{slot_new['title']}“ — der Anzeigename wird an den DVR-/EPG-Pfad angeglichen."
            )
        else:
            parts.append(
                "Der Titel wechselt, weil die neue DVR-Minute in einen anderen EPG-Slot fällt als vorher (nach geladenem XMLTV)."
            )
            if slot_cur:
                parts.append(
                    f"Vorherige Minute lag im EPG-Slot „{slot_cur['title']}“ "
                    f"(start={slot_cur['start_xmltv'] or slot_cur['start_iso']}, stop={slot_cur['stop_xmltv'] or slot_cur['stop_iso']})."
                )
            if pe_slot is not None and new_parsed:
                parts.append(
                    f"Sticky griff nicht: neue DVR-Zeit liegt nicht mehr vor dem EPG-Ende ({pe_slot.isoformat()}) "
                    "der zuvor angezeigten Sendung — oder der alte Slot war im EPG nicht eindeutig."
                )
    else:
        parts.append(
            "Kein Titelwechsel nötig — gleiche Sendung laut EPG oder keine zweite Zuordnung."
        )

    return head + "\n" + " ".join(parts)


def _catchup_sync_epg_from_dvr_url(token: str, decoded_url: str, user: dict, source: str) -> bool:
    """If URL contains .../YYYY/MM/DD/HH/MM/..., advance watch_log catchup_time + EPG (also for .ts)."""
    new_dt_str = _dvr_wall_time_from_url(decoded_url)
    if not new_dt_str:
        return False
    ck = _resolve_catchup_session_key(token, decoded_url)
    if not ck or ck not in _catchup_sessions:
        return True
    cv = _catchup_sessions[ck]
    if cv.get("last_dvr_dt_str") == new_dt_str:
        return True
    # CDN paths sometimes oscillate ±1 min — never move catchup_time backwards.
    new_parsed = _parse_catchup_wall_time(new_dt_str)
    cur_wall = (cv.get("catchup_time") or "").strip()
    cur_parsed = _parse_catchup_wall_time(cur_wall) if cur_wall else None
    if new_parsed and cur_parsed and new_parsed < cur_parsed:
        _now = time.time()
        if _now - float(cv.get("_dvr_skip_back_ts", 0)) >= 60:
            cv["_dvr_skip_back_ts"] = _now
            diag_log(
                "INFO",
                "catchup",
                f"DVR-Pfad älter als aktuelle Position — ignoriert: {new_dt_str} < {cur_wall}",
            )
        return True
    ch_name = ck.split("::")[-1] if "::" in ck else ""
    if not ch_name:
        try:
            with db.conn() as con:
                row = con.execute(
                    "SELECT channel FROM watch_logs WHERE id = ?", (cv["log_id"],)
                ).fetchone()
            ch_name = row["channel"] if row else ""
        except Exception:
            ch_name = ""
    if not ch_name:
        return True
    new_epg = _epg_title_from_wall_time_channel(ch_name, new_dt_str)
    old_dt = (cv.get("catchup_time") or "").strip() or "(start)"
    old_epg = (cv.get("epg_title") or "").strip() or "(none)"
    old_epg_clean = (cv.get("epg_title") or "").strip()
    sticky = False
    pe_slot = None
    if (
        new_epg
        and old_epg_clean
        and new_epg.strip() != old_epg_clean
        and cur_parsed
        and new_parsed
    ):
        pe_slot = _epg_programme_stop_for_title_at_dt(ch_name, cur_parsed, old_epg_clean)
        if pe_slot is not None and new_parsed < pe_slot:
            sticky = True
    resolved_epg = old_epg_clean if sticky else new_epg
    real_show_change = (
        not sticky
        and bool(old_epg_clean)
        and bool(new_epg)
        and new_epg.strip() != old_epg_clean
    )
    if real_show_change:
        # Split: alten Log-Eintrag mit alter Sendung + bisheriger Dauer schließen,
        # neuen Eintrag für die neue Sendung anlegen. Catchup_time wird im neuen
        # Eintrag gesetzt — der alte behält seinen ursprünglichen catchup_time.
        if _split_watch_log_on_show_change(
            cv,
            new_epg,
            is_catchup=True,
            catchup_time=new_dt_str,
            channel=ch_name,
        ):
            # Auto-Live-on-Programme-Change wie vorher armieren.
            if (
                is_catchup_guard_master_enabled()
                and is_catchup_auto_live_on_program_change_enabled()
            ):
                cv["auto_live_pending"] = True
                diag_log(
                    "INFO",
                    "catchup",
                    f"Catchup programme changed ({old_epg_clean!r} -> {new_epg!r}) for {ch_name}; switch to live is armed.",
                )
            disp_epg = (cv.get("epg_title") or "").strip() or old_epg
            diag_log(
                "INFO",
                "catchup",
                _catchup_format_dvr_sync_message(
                    user_name=user.get("name", "") or "",
                    ch_name=ch_name,
                    source=source,
                    old_dt=old_dt,
                    new_dt_str=new_dt_str,
                    old_epg=old_epg,
                    disp_epg=disp_epg,
                    decoded_url=decoded_url,
                    new_epg=new_epg,
                    old_epg_clean=old_epg_clean,
                    sticky=sticky,
                    cur_parsed=cur_parsed,
                    new_parsed=new_parsed,
                    pe_slot=pe_slot,
                ),
            )
            return True
    try:
        with db.conn() as con:
            if resolved_epg:
                con.execute(
                    "UPDATE watch_logs SET catchup_time = ?, epg_title = ? WHERE id = ?",
                    (new_dt_str, resolved_epg, cv["log_id"]),
                )
            else:
                con.execute(
                    "UPDATE watch_logs SET catchup_time = ? WHERE id = ?",
                    (new_dt_str, cv["log_id"]),
                )
                diag_log(
                    "WARNING",
                    "catchup",
                    f"Catchup DVR {new_dt_str} ({source}) aber kein EPG-Titel (tvg_id/EPG?): {ch_name}",
                )
    except Exception:
        return True
    cv["catchup_time"] = new_dt_str
    cv["last_dvr_dt_str"] = new_dt_str
    if resolved_epg:
        cv["epg_title"] = resolved_epg
    if (
        is_catchup_guard_master_enabled()
        and is_catchup_auto_live_on_program_change_enabled()
        and not sticky
        and old_epg_clean
        and new_epg
        and new_epg.strip() != old_epg_clean
    ):
        cv["auto_live_pending"] = True
        diag_log(
            "INFO",
            "catchup",
            f"Catchup programme changed ({old_epg_clean!r} -> {new_epg!r}) for {ch_name}; switch to live is armed.",
        )
    disp_epg = (cv.get("epg_title") or "").strip() or old_epg
    diag_log(
        "INFO",
        "catchup",
        _catchup_format_dvr_sync_message(
            user_name=user.get("name", "") or "",
            ch_name=ch_name,
            source=source,
            old_dt=old_dt,
            new_dt_str=new_dt_str,
            old_epg=old_epg,
            disp_epg=disp_epg,
            decoded_url=decoded_url,
            new_epg=new_epg,
            old_epg_clean=old_epg_clean,
            sticky=sticky,
            cur_parsed=cur_parsed,
            new_parsed=new_parsed,
            pe_slot=pe_slot,
        ),
    )
    return True


def _catchup_warn_if_no_dvr_in_url(token: str, decoded_url: str) -> None:
    if _dvr_wall_time_from_url(decoded_url):
        return
    low = decoded_url.lower()
    if "utc=" in low or "lutc=" in low:
        # Fenster-/Master-Playlist: Position steckt in utc=, nicht im Pfad — kein False Positive.
        return
    ck = _resolve_catchup_session_key(token, decoded_url)
    if not ck or ck not in _catchup_sessions:
        return
    cv = _catchup_sessions[ck]
    now = time.time()
    if now - float(cv.get("_no_dvr_diag_ts", 0)) < 120:
        return
    cv["_no_dvr_diag_ts"] = now
    tail = decoded_url[-120:] if len(decoded_url) > 120 else decoded_url
    diag_log(
        "WARNING",
        "catchup",
        f"Catchup-Anfrage ohne DVR-Datum im Pfad (Titel folgt nur Start/Watchdog): …{tail}",
    )


def get_catchup_ttl() -> int:
    try:
        return max(5, int(db.get_setting("catchup_ttl", "900")))
    except Exception:
        return 120


def get_catchup_ttl_after_endlist() -> int:
    """Idle window once provider playlist contained #EXT-X-ENDLIST."""
    try:
        return max(30, int(db.get_setting("catchup_ttl_after_endlist", "900")))
    except Exception:
        return 900


def is_catchup_strict_mode() -> bool:
    """If enabled, catchup errors return 502 instead of silently falling back to live."""
    return db.get_setting("catchup_strict_mode", "1") == "1"


def is_catchup_guard_master_enabled() -> bool:
    """Master switch for catchup guard/recovery redirects."""
    return db.get_setting("catchup_guard_master", "1") == "1"


def is_catchup_sticky_recover_enabled() -> bool:
    """If enabled, accidental live fallback requests are redirected back into recent catchup."""
    return db.get_setting("catchup_sticky_recover", "1") == "1"


def is_catchup_auto_live_on_program_change_enabled() -> bool:
    """If enabled, catchup switches to live when the watched programme changes."""
    return db.get_setting("catchup_auto_live_on_program_change", "0") == "1"


def is_catchup_auto_live_keep_utc_enabled() -> bool:
    """If enabled, auto-live redirect keeps utc parameter (stays in catchup timeline)."""
    return db.get_setting("catchup_auto_live_keep_utc", "1") == "1"


def is_catchup_force_same_channel_live_enabled() -> bool:
    """If enabled, unexpected live-channel jumps after catchup are redirected to the catchup channel."""
    return db.get_setting("catchup_force_same_channel_live", "1") == "1"


def is_catchup_hard_lock_enabled() -> bool:
    """If enabled, active catchup sessions force /stream requests back to catchup utc."""
    return db.get_setting("catchup_hard_lock", "1") == "1"


def _catchup_idle_ttl_seconds(cv: dict) -> int:
    if cv.get("saw_endlist"):
        # Never shorten below normal catchup ttl; ENDLIST can appear early on some providers.
        return max(get_catchup_ttl(), get_catchup_ttl_after_endlist())
    return get_catchup_ttl()


def _catchup_mark_endlist(token: str, decoded_url: str) -> None:
    """Set flag for shorter idle TTL. Nur bei echtem Archiv-Ende im Catchup-**Master** (index.m3u8 Start),
    nicht bei Unter-Playlisten: die liefern bei Sliding Window oft ENDLIST ohne dass Playback stoppt —
    direkte Anbieter-M3U hat keine vergleichbare Session-TTL und wirkt dann stabiler."""
    ck = _resolve_catchup_session_key(token, decoded_url)
    if not ck or ck not in _catchup_sessions:
        return
    cv = _catchup_sessions[ck]
    if cv.get("saw_endlist"):
        return
    cv["saw_endlist"] = True
    cv["endlist_seen_at"] = time.time()

_last_cleanup = 0.0


_split_global_lock = threading.Lock()


def _live_check_show_change(sess: dict, channel_name: str, now_ts: float, min_interval: float = 15.0) -> None:
    """Eager EPG-Sendungswechsel-Erkennung beim Touch einer laufenden Live-Session
    (Playlist- oder Segment-Anfrage). Gedrosselt auf 1 Aufruf alle ~15s pro
    Session, damit das XML-Parsing nicht bei jeder TS-Anfrage läuft. Das ergibt
    eine effektive Erkennungslatenz von 0–15s statt der 45s-Watchdog-Periode.
    """
    try:
        _last = float(sess.get("_last_epg_check", 0.0))
    except Exception:
        _last = 0.0
    if now_ts - _last < min_interval:
        return
    sess["_last_epg_check"] = now_ts
    try:
        np = _get_now_playing(channel_name)
        new_t = ((np.get("title") if np else "") or "").strip()
        if not new_t:
            return
        old_t = (sess.get("epg_title") or "").strip()
        if not old_t:
            log_id = sess.get("log_id")
            if not log_id:
                return
            try:
                with db.conn() as con:
                    con.execute(
                        "UPDATE watch_logs SET epg_title=? WHERE id=?",
                        (new_t, log_id),
                    )
                sess["epg_title"] = new_t
            except Exception:
                pass
            return
        if old_t == new_t:
            return
        _split_watch_log_on_show_change(
            sess,
            new_t,
            is_catchup=False,
            channel=channel_name,
        )
    except Exception:
        pass


def _split_watch_log_on_show_change(
    sess: dict,
    new_title: str,
    *,
    is_catchup: bool = False,
    catchup_time: str = None,
    channel: str = None,
) -> bool:
    """Bei Sendungswechsel innerhalb einer Session: aktuellen watch_logs-Eintrag mit
    bisheriger Watch-Dauer + ALTEM Titel schließen und einen NEUEN Eintrag für die
    neue Sendung anlegen. So bekommt jede Sendung ihre eigene Dauer in der History.

    Liefert True, wenn gesplittet wurde. Liefert False, wenn nichts zu tun ist
    (Titel unverändert, kein alter Titel vorhanden, keine log_id, …) — der Aufrufer
    muss dann ggf. den Titel an Ort und Stelle aktualisieren (z.B. wenn EPG-Titel
    erst NACHTRÄGLICH bekannt wird).

    Idempotent gegen parallele Aufrufe: ein per-Session Lock + Compare-and-Swap
    auf `log_id` verhindert, dass zwei gleichzeitige Codepfade (z.B. zwei
    Watchdogs in zwei Event-Loops, oder Watchdog + Catchup-DVR-Sync) doppelte
    Einträge erzeugen.
    """
    new_title_clean = (new_title or "").strip()
    if not new_title_clean:
        return False

    # Per-Session Lock holen (lazy, damit alte Sessions ohne das Feld weiterlaufen)
    sess_lock = sess.get("_split_lock")
    if sess_lock is None:
        with _split_global_lock:
            sess_lock = sess.get("_split_lock")
            if sess_lock is None:
                sess_lock = threading.Lock()
                sess["_split_lock"] = sess_lock

    with sess_lock:
        # Innerhalb des Locks: aktuellen Stand frisch lesen (CAS)
        old_title = (sess.get("epg_title") or "").strip()
        if not old_title:
            return False
        if old_title == new_title_clean:
            return False

        log_id_old = sess.get("log_id")
        if not log_id_old:
            return False

        user_id = sess.get("user_id")
        if not user_id:
            try:
                tok = sess.get("token")
                if tok:
                    _u = db.get_user_by_token(tok)
                    if _u:
                        user_id = _u["id"]
                        sess["user_id"] = user_id
            except Exception:
                pass
        if not user_id:
            return False

        now = time.time()
        log_start = float(sess.get("log_start", sess.get("start", now)))
        duration_old = max(0, int(now - log_start))

        ch_name = channel or sess.get("channel") or ""
        stream_url = sess.get("stream_url") or sess.get("live_url") or ""
        ip_address = sess.get("ip_address") or sess.get("ip") or ""

        try:
            db.end_watch_log(log_id_old, duration_old, epg_title=old_title)
        except Exception as _e:
            logger.warning(f"split log end failed: {_e}")
            return False

        try:
            new_log_id = db.start_watch_log(
                user_id=user_id,
                channel=ch_name,
                stream_url=stream_url,
                ip_address=ip_address,
                is_catchup=1 if is_catchup else 0,
                catchup_time=catchup_time if is_catchup else None,
                epg_title=new_title_clean,
            )
        except Exception as _e:
            logger.warning(f"split log start failed: {_e}")
            return False

        sess["log_id"] = new_log_id
        sess["log_start"] = now
        sess["epg_title"] = new_title_clean
        if is_catchup and catchup_time:
            sess["catchup_time"] = catchup_time
            sess["last_dvr_dt_str"] = catchup_time

        diag_log(
            "INFO",
            "catchup" if is_catchup else "session",
            f"Sendungswechsel → Log-Split: {ch_name} \"{old_title}\" ({duration_old}s) → \"{new_title_clean}\"",
        )
        return True


def _cleanup_sessions():
    """Remove stale sessions from memory and end their DB records."""
    global _last_cleanup
    now = time.time()
    # Throttle: only run cleanup every 10 seconds
    if now - _last_cleanup < 10:
        return
    _last_cleanup = now
    stale = [k for k, v in _sessions.items() if now - v["last_seen"] > SESSION_MEM_TTL]
    for k in stale:
        s = _sessions.pop(k)
        try:
            db.session_end(s["token"])
            # Try EPG title at end - more reliable than at start
            epg_end = _get_now_playing(s["channel"])
            epg_title_end = s.get("epg_title") or (epg_end.get("title") if epg_end else None)
            db.end_watch_log(s["log_id"], int(now - s.get("log_start", s["start"])), epg_title=epg_title_end)
            logger.info(f"Session expired (TTL): {k} epg={epg_title_end}")
            diag_log(
                "INFO",
                "session",
                f"Session expired (TTL): {k} epg={epg_title_end}. "
                f"Ursache: Live-Stream seit >{SESSION_MEM_TTL}s ohne Traffic über den Proxy-Segmentpfad "
                f"(keine TS- und keine Playlist-Anfragen mehr; nicht Catchup/catchup_ttl).",
            )
        except Exception:
            pass
    # Cleanup stale catchup sessions (idle TTL; shorter after #EXT-X-ENDLIST seen)
    stale_cu = [k for k, v in _catchup_sessions.items() if now - v["last_seen"] > _catchup_idle_ttl_seconds(v)]
    for k in stale_cu:
        s = _catchup_sessions.pop(k)
        try:
            duration = int(now - s.get("log_start", s["start"]))
            db.end_watch_log(s["log_id"], duration)
            tok = s.get("token", "")
            try:
                db.session_end(tok)
            except Exception:
                pass
            idle_gap = int(now - float(s.get("last_seen", now)))
            if s.get("saw_endlist"):
                ttl_used = get_catchup_ttl_after_endlist()
                els = float(s.get("endlist_seen_at") or 0)
                detail = f"Catchup session ended (nach ENDLIST-Marker, Idle): {k} duration={duration}s"
                explain = (
                    f"Ursache: Mindestens eine Anbieter-Playlist hatte #EXT-X-ENDLIST — dann gilt das kürzere Idle-Limit ({ttl_used}s), "
                    f"nicht catchup_ttl für „normales“ Ende."
                )
                if els > 0:
                    secs_after_start = max(0, int(els - float(s.get("start", els))))
                    wall_since_endlist = max(0, int(now - els))
                    explain += (
                        f" ENDLIST zuerst ~{secs_after_start}s nach Catchup-Start erkannt; seitdem sind ~{wall_since_endlist}s Wandzeit vergangen "
                        f"(Playback lief oft weiter über andere Playlist-Anfragen)."
                    )
                explain += (
                    f" Zuletzt ~{idle_gap}s keine Segment-/Playlist-Anfragen mehr durch diesen Pfad (≥{ttl_used}s Schwelle) — Session geschlossen. "
                    "Das bedeutet nicht zwingend „Film im EPG zu Ende“; typisch Player-Stopp, Netz oder CDN ohne Folge-Segmente."
                )
                detail = detail + "\n" + explain
            else:
                ttl_used = get_catchup_ttl()
                detail = (
                    f"Catchup session ended (idle timeout): {k} duration={duration}s\n"
                    f"Ursache: ~{idle_gap}s keine Catchup-Anfragen mehr (Schwelle catchup_ttl={ttl_used}s); "
                    "kein ENDLIST-Marker in dieser Session gesetzt."
                )
            logger.info(detail.split("\n")[0])
            diag_log("INFO", "catchup", detail)
        except Exception:
            pass

def _user_stream_count(user_id: int) -> int:
    _cleanup_sessions()
    return sum(1 for s in _sessions.values() if s["user_id"] == user_id)

def _user_has_session(user_id: int, session_key: str) -> bool:
    return session_key in _sessions

async def _catchup_epg_watchdog():
    """Every ~2 min: reconcile catchup epg_title with DB catchup_time (DVR/playlist), not wall-clock playback."""
    await asyncio.sleep(30)  # wait for startup
    while True:
        try:
            now = time.time()
            for _ck, _cv in list(_catchup_sessions.items()):
                if now - _cv["last_seen"] >= _catchup_idle_ttl_seconds(_cv):
                    continue
                try:
                    # Get current catchup_time and channel from DB
                    with db.conn() as con:
                        row = con.execute(
                            "SELECT wl.catchup_time, wl.channel, wl.epg_title FROM watch_logs wl WHERE wl.id = ?",
                            (_cv["log_id"],)
                        ).fetchone()
                    if not row or not row["catchup_time"]:
                        continue

                    # Playback position must come from DB catchup_time (updated from DVR paths in playlists).
                    # Wall-clock + elapsed is wrong after buffering/pauses — shows next programme too early.
                    _current_dt = _parse_catchup_wall_time(row["catchup_time"])
                    if not _current_dt:
                        continue

                    # Look up EPG title at stored catchup_time
                    _new_epg = None
                    try:
                        import xml.etree.ElementTree as _ET3
                        _epg_c3 = _epg_cache.get("content")
                        if not _epg_c3:
                            try:
                                with open("/data/epg_cache.xml", "r", encoding="utf-8") as _ef3:
                                    _epg_c3 = _ef3.read()
                            except Exception:
                                pass
                        if _epg_c3:
                            _root3 = _ET3.fromstring(_epg_c3)
                            _ch_rec3 = db.get_channel_by_name(row["channel"]) or {}
                            _tvg3 = _ch_rec3.get("tvg_id", "").strip()
                            if _tvg3:
                                for _prog3 in _root3.findall("programme"):
                                    if _prog3.get("channel", "") != _tvg3:
                                        continue
                                    _ps3 = _parse_xmltv_datetime(_prog3.get("start", ""))
                                    _pe3 = _parse_xmltv_datetime(_prog3.get("stop", ""))
                                    if _epg_programme_contains_instant_half_open(_ps3, _pe3, _current_dt):
                                        _new_epg = _prog3.findtext("title") or None
                                        break
                    except Exception:
                        pass

                    # Update DB only if title changed (reconcile cache vs EPG at same catchup_time)
                    if _new_epg and _new_epg != (row["epg_title"] or ""):
                        _old_t = (row["epg_title"] or "").strip() or "(none)"
                        _slot_w = _epg_slot_detail_at_dt(row["channel"], _current_dt)
                        _why = (
                            "Ursache: Alle ~2 Min prüft der Catchup-Watchdog, ob der gespeicherte Titel noch zur "
                            f"gleichen catchup_time {row['catchup_time']!r} passt (XMLTV halb-offen)."
                        )
                        if _slot_w:
                            _why += (
                                f" EPG-Slot jetzt: „{_slot_w['title']}“ "
                                f"(start={_slot_w['start_xmltv'] or _slot_w['start_iso']}, "
                                f"stop={_slot_w['stop_xmltv'] or _slot_w['stop_iso']})."
                            )
                        # Sync cv state with DB (catchup_time may have advanced via DVR sync)
                        _cv["catchup_time"] = row["catchup_time"]
                        if not _cv.get("channel"):
                            _cv["channel"] = row["channel"]
                        # Bei echtem Sendungswechsel splitten (alter Eintrag bekommt seine
                        # eigene Dauer mit altem Titel; neuer Eintrag startet jetzt).
                        _did_split = False
                        if (row["epg_title"] or "").strip():
                            _did_split = _split_watch_log_on_show_change(
                                _cv,
                                _new_epg,
                                is_catchup=True,
                                catchup_time=row["catchup_time"],
                                channel=row["channel"],
                            )
                        if _did_split:
                            logger.info(f"Catchup EPG split: {row['channel']} {_old_t!r} → {_new_epg!r}")
                            diag_log(
                                "INFO",
                                "catchup",
                                f"Catchup EPG reconcile @ {row['catchup_time']}: {row['channel']} title {_old_t!r} → {_new_epg!r} (Log-Split). {_why}",
                            )
                        else:
                            try:
                                with db.conn() as con:
                                    con.execute(
                                        "UPDATE watch_logs SET epg_title=? WHERE id=?",
                                        (_new_epg, _cv["log_id"])
                                    )
                                _cv["epg_title"] = _new_epg
                                logger.info(f"Catchup EPG updated: {row['channel']} → {_new_epg}")
                                diag_log(
                                    "INFO",
                                    "catchup",
                                    f"Catchup EPG reconcile @ {row['catchup_time']}: {row['channel']} title {_old_t!r} → {_new_epg!r}. {_why}",
                                )
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(120)  # check every 2 minutes


async def _live_epg_watchdog():
    """Periodisch prüfen, ob bei laufenden LIVE-Sessions die EPG-Sendung gewechselt
    hat. Wenn ja: aktuellen watch_logs-Eintrag mit der alten Sendung + bisheriger
    Watch-Dauer schließen und einen NEUEN Eintrag für die neue Sendung anlegen.
    So bekommt jede Sendung in der History ihre eigene Dauer."""
    await asyncio.sleep(20)  # wait for startup
    while True:
        try:
            now = time.time()
            for _sk, _s in list(_sessions.items()):
                try:
                    # Skip stale sessions (cleanup will handle them)
                    if now - _s.get("last_seen", now) > SESSION_MEM_TTL:
                        continue
                    _ch = _s.get("channel")
                    if not _ch:
                        continue
                    _now_play = _get_now_playing(_ch)
                    _new_title = (_now_play.get("title") if _now_play else None) or ""
                    _new_title = _new_title.strip()
                    if not _new_title:
                        continue
                    _old_title = (_s.get("epg_title") or "").strip()
                    if not _old_title:
                        # EPG wurde erst jetzt verfügbar — Titel im laufenden Eintrag setzen,
                        # nicht splitten (dieselbe Sendung läuft die ganze Zeit).
                        try:
                            with db.conn() as con:
                                con.execute(
                                    "UPDATE watch_logs SET epg_title=? WHERE id=?",
                                    (_new_title, _s["log_id"]),
                                )
                            _s["epg_title"] = _new_title
                        except Exception:
                            pass
                        continue
                    if _old_title == _new_title:
                        continue
                    # Echter Sendungswechsel — Log splitten.
                    _split_watch_log_on_show_change(
                        _s,
                        _new_title,
                        is_catchup=False,
                        channel=_ch,
                    )
                except Exception:
                    pass
        except Exception as _we:
            logger.warning(f"Live EPG watchdog error: {_we}")
        await asyncio.sleep(45)  # check every 45s


@proxy_app.get("/iptv/{token}/segment")
async def proxy_segment(token: str, url: str, sid: str = None, catchup: str = None, request: Request = None):
    _log_player_request("segment:request", request, token, {"catchup": catchup, "sid": sid, "url_raw": url})
    user = db.get_user_by_token(token)
    if not user:
        _log_player_request("segment:forbidden", request, token, {"reason": "invalid_token"}, level="WARNING")
        raise HTTPException(status_code=403, detail="Invalid token")

    if not user["active"]:
        proxy_url = db.get_proxy_url()
        _short2 = db.get_setting("short_domain", "")
        _pub2 = _short2.rstrip("/") if _short2 else proxy_url
        banned_url = f"{_pub2}/iptv/error-banned.ts"
        banned_m3u = _build_loop_playlist(banned_url)
        return HTMLResponse(content=banned_m3u, media_type="application/x-mpegURL",
                           headers={"Cache-Control": "no-cache"})

    decoded_url = urllib.parse.unquote(url)
    assert_safe_upstream_url(decoded_url)  # SSRF-Schutz
    hls = get_hls_settings()
    proxy_url = db.get_proxy_url()
    short_domain_seg = db.get_setting("short_domain", "")
    public_url_seg = short_domain_seg.rstrip("/") if short_domain_seg else proxy_url
    is_ts = not (decoded_url.endswith(".m3u8") or "m3u8" in decoded_url.split("?")[0])
    _log_player_request("segment:decoded", request, token, {"catchup": catchup, "is_ts": is_ts, "decoded_url": decoded_url})

    # Live session tracking (TS *and* playlist refreshes).
    # Important: ExoPlayer polls playlists frequently even while still buffering segments.
    # If we only touch sessions on TS downloads, idle cleanup can kill a perfectly active live session.
    session_key = None
    if catchup != "1":
        parts0 = decoded_url.split("/")
        ch_record0 = db.get_channel_by_url_fragment(decoded_url)
        if ch_record0:
            channel_name0 = ch_record0["name"]
        else:
            ch_idx0 = next((i for i, p in enumerate(parts0) if p.startswith("ch")), None)
            channel_name0 = parts0[ch_idx0] if ch_idx0 else parts0[-1].split("?")[0]

        client_ip0 = ""
        if request:
            forwarded0 = request.headers.get("x-forwarded-for")
            client_ip0 = forwarded0.split(",")[0].strip() if forwarded0 else (request.client.host if request.client else "")

        ua0 = request.headers.get("user-agent", "") if request else ""
        # Must match proxy_stream sid derivation, otherwise we create duplicate session keys
        # (token::IP::UA vs token::sid::<md5>) and TTL cleanup looks "random".
        ua_sid0 = ua0[:60]
        if not sid:
            sid = hashlib.md5(f"{token}::{client_ip0}::{ua_sid0}".encode()).hexdigest()[:16]
        session_key = f"{token}::sid::{sid}"

        user_id0 = user["id"]
        now0 = time.time()

        if session_key in _sessions:
            existing0 = _sessions[session_key]
            if existing0["channel"] != channel_name0:
                _sessions.pop(session_key)
                db.session_end(token)
                epg_sw0 = _get_now_playing(existing0["channel"])
                epg_title_sw0 = existing0.get("epg_title") or (epg_sw0.get("title") if epg_sw0 else None)
                db.end_watch_log(existing0["log_id"], int(now0 - existing0.get("log_start", existing0["start"])), epg_title=epg_title_sw0)
                logger.info(f"Channel switch: {user['name']} ({client_ip0}) → {channel_name0}")
            else:
                _sessions[session_key]["last_seen"] = now0
                db.session_refresh(token)
                _live_check_show_change(_sessions[session_key], channel_name0, now0)

        if session_key not in _sessions:
            max_s0 = user.get("max_streams", 1) or 0
            if max_s0 > 0:
                active_count0 = _user_stream_count(user_id0)
                if active_count0 >= max_s0:
                    logger.warning(f"Max streams blocked: {user['name']} {active_count0}/{max_s0} from {client_ip0}")
                    diag_log(
                        "WARNING",
                        "stream",
                        f"Max streams blocked: {user['name']} {active_count0}/{max_s0} from {client_ip0}",
                    )
                    raise HTTPException(status_code=429, detail=f"Max. {max_s0} Stream(s) erlaubt")
            db.session_start(token, channel_name0, ip_address=client_ip0)
            epg_now0 = _get_now_playing(channel_name0)
            epg_title_now0 = epg_now0.get("title") if epg_now0 else None
            log_id0 = db.start_watch_log(
                user_id=user["id"],
                channel=channel_name0,
                stream_url=decoded_url,
                ip_address=client_ip0,
                epg_title=epg_title_now0,
            )
            _sessions[session_key] = {
                "channel": channel_name0,
                "log_id": log_id0,
                "start": now0,
                "log_start": now0,
                "last_seen": now0,
                "user_id": user_id0,
                "token": token,
                "session_key": session_key,
                "epg_title": epg_title_now0,
                "user_name": user["name"],
                "stream_url": decoded_url,
                "ip_address": client_ip0,
            }
            logger.info(f"Session started: {user['name']} ({client_ip0}) → {channel_name0}")

    # Catchup segments bypass session tracking
    if catchup == "1":
        _touch_catchup_last_seen(token, decoded_url)
        _catchup_src = "segment" if is_ts else "playlist"
        if not _catchup_sync_epg_from_dvr_url(token, decoded_url, user, _catchup_src):
            _catchup_warn_if_no_dvr_in_url(token, decoded_url)
        try:
            timeout = catchup_upstream_httpx_timeout(hls)
            async with make_iptv_client(timeout=timeout, follow_redirects=hls["hls_follow_redirects"], headers=make_headers(hls)) as client:
                _ck_live = _resolve_catchup_session_key(token, decoded_url)
                _cv_live = _catchup_sessions.get(_ck_live) if _ck_live else None
                if is_catchup_guard_master_enabled() and _cv_live and _cv_live.get("auto_live_pending"):
                    _live_url = (_cv_live.get("live_url") or "").strip()
                    if _live_url:
                        _cw_live = (_cv_live.get("catchup_time") or "").strip()
                        _ct_live = _parse_catchup_wall_time(_cw_live) if _cw_live else None
                        _cv_live["auto_live_pending"] = False
                        if _ct_live and is_catchup_auto_live_keep_utc_enabled():
                            _redir_live = f"/iptv/{token}/stream?url={urllib.parse.quote(_live_url, safe='')}&utc={int(_ct_live.timestamp())}"
                            _mode = "keep_utc"
                        else:
                            _redir_live = f"/iptv/{token}/stream?url={urllib.parse.quote(_live_url, safe='')}"
                            _mode = "true_live"
                            _cv_live["allow_live_until"] = time.time() + 180
                        diag_log(
                            "INFO",
                            "catchup",
                            f"Catchup -> live hard redirect ({_mode}) for {user.get('name', token[:8])}: {(_ck_live or '').split('::')[-1] or '?'}",
                        )
                        _log_player_request(
                            "segment:catchup_auto_live_redirect",
                            request,
                            token,
                            {"redirect_url": _redir_live, "trigger": "auto_live_pending", "is_ts": is_ts, "mode": _mode},
                        )
                        return RedirectResponse(url=_redir_live)
                if not is_ts:
                    resp = await client.get(decoded_url)
                    resp.raise_for_status()
                    raw_pl = resp.text
                    if "#EXT-X-ENDLIST" in raw_pl:
                        _ck_el = _resolve_catchup_session_key(token, decoded_url)
                        _cv_el = _catchup_sessions.get(_ck_el) if _ck_el else None
                        # Unter-Playlist ENDLIST nicht für Idle-Verkürzung werten (Sliding Window / CDN-Artefakt).
                        # Diagnose einmal pro Session — ohne saw_endlist, siehe _catchup_mark_endlist-Docstring.
                        if _cv_el and not _cv_el.get("_diag_endlist_nested_logged"):
                            _cv_el["_diag_endlist_nested_logged"] = True
                            _ch_el = (_ck_el.split("::")[-1] if _ck_el and "::" in _ck_el else "").strip()
                            _cw_el = _cv_el.get("catchup_time") or ""
                            _diag_log_catchup_endlist_epg_context(
                                user.get("name", "") or "",
                                _ch_el,
                                _cw_el,
                                where="nachgelagerte Playlist (.m3u8)",
                            )
                    rewritten = rewrite_hls_playlist(raw_pl, decoded_url, public_url_seg, token, catchup=True)
                    _log_player_request(
                        "segment:catchup_playlist_response",
                        request,
                        token,
                        {"decoded_url": decoded_url, "playlist_len": len(rewritten)},
                    )
                    return HTMLResponse(content=rewritten, media_type="application/vnd.apple.mpegurl",
                                        headers={"Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*"})
                else:
                    max_cu_attempts = 4
                    _cu_data = b""
                    _cu_elapsed = 0.0
                    for _cu_try in range(max_cu_attempts):
                        _hb = asyncio.create_task(_catchup_segment_idle_heartbeat(token, decoded_url))
                        try:
                            _cu_t0 = time.time()
                            _buf = bytearray()
                            async with make_iptv_client(timeout=timeout, follow_redirects=hls["hls_follow_redirects"], headers=make_headers(hls)) as c2:
                                async with c2.stream("GET", decoded_url) as r2:
                                    if r2.status_code not in (200, 206):
                                        raise HTTPException(status_code=502, detail=f"Catchup segment upstream HTTP {r2.status_code}")
                                    async for chunk in r2.aiter_bytes(chunk_size=hls["hls_chunk_size"]):
                                        _buf.extend(chunk)
                            _cu_elapsed = time.time() - _cu_t0
                            _cu_data = bytes(_buf)
                            if len(_cu_data) >= 1_000:
                                break
                            raise HTTPException(status_code=502, detail=f"Catchup segment too small ({len(_cu_data)} bytes)")
                        except Exception as _cu_err:
                            if _cu_try >= max_cu_attempts - 1:
                                raise
                            diag_log(
                                "WARNING",
                                "catchup",
                                f"Catchup TS retry {_cu_try + 2}/{max_cu_attempts}: {_cu_err}",
                            )
                            await asyncio.sleep(min(1.5, 0.2 * (2 ** _cu_try)))
                        finally:
                            _hb.cancel()
                            try:
                                await _hb
                            except asyncio.CancelledError:
                                pass

                    _cu_size_kb = len(_cu_data) / 1024
                    _cu_speed = min((len(_cu_data) * 8) / (max(_cu_elapsed, 0.001) * 1_000_000), 10000.0)
                    _cu_seg = decoded_url.split("/")[-1].split("?")[0]
                    _cu_user = user.get("name", token[:8])
                    _ck_cu = _resolve_catchup_session_key(token, decoded_url)
                    _cu_ch = _ck_cu.split("::")[-1] if _ck_cu and "::" in _ck_cu else ""
                    # Get provider_id from channel record
                    _cu_provider_id = user.get("provider_id")
                    if not _cu_provider_id and _cu_ch:
                        try:
                            _cu_ch_rec = db.get_channel_by_name(_cu_ch) or {}
                            _cu_provider_id = _cu_ch_rec.get("provider_id")
                        except Exception:
                            pass
                    if _cu_elapsed > 2.0:
                        logger.warning(f"⚠️ SLOW CATCHUP [{_cu_user}] {_cu_seg}: {_cu_elapsed:.1f}s, {_cu_speed:.1f}Mbit/s")
                        diag_log(
                            "WARNING",
                            "segment",
                            f"SLOW CATCHUP [{_cu_user}] {_cu_seg}: {_cu_elapsed:.1f}s, {_cu_speed:.1f}Mbit/s",
                        )
                        _cu_ev = {"time": time.time(), "user": _cu_user, "channel": f"[Catchup] {_cu_ch}",
                                  "type": "slow", "elapsed": round(_cu_elapsed, 2),
                                  "size_kb": round(_cu_size_kb), "mbps": round(_cu_speed, 1),
                                  "seg": _cu_seg, "provider_id": _cu_provider_id}
                        _segment_events.append(_cu_ev)
                        if len(_segment_events) > 500: _segment_events.pop(0)
                        try: db.add_segment_event(_cu_ev)
                        except Exception: pass
                    elif _cu_elapsed > 1.0:
                        _cu_ev = {"time": time.time(), "user": _cu_user, "channel": f"[Catchup] {_cu_ch}",
                                  "type": "delayed", "elapsed": round(_cu_elapsed, 2),
                                  "size_kb": round(_cu_size_kb), "mbps": round(_cu_speed, 1),
                                  "seg": _cu_seg, "provider_id": _cu_provider_id}
                        _segment_events.append(_cu_ev)
                        if len(_segment_events) > 500: _segment_events.pop(0)
                        try: db.add_segment_event(_cu_ev)
                        except Exception: pass
                    elif db.get_setting("segment_debug", "0") == "1":
                        _cu_ev = {"time": time.time(), "user": _cu_user, "channel": f"[Catchup] {_cu_ch}",
                                  "type": "ok", "elapsed": round(_cu_elapsed, 2),
                                  "size_kb": round(_cu_size_kb), "mbps": round(_cu_speed, 1),
                                  "seg": _cu_seg, "provider_id": _cu_provider_id}
                        _segment_events.append(_cu_ev)
                        if len(_segment_events) > 500: _segment_events.pop(0)
                        try: db.add_segment_event(_cu_ev)
                        except Exception: pass

                    async def stream_catchup_ts():
                        chunk_size = 524288
                        for i in range(0, len(_cu_data), chunk_size):
                            yield _cu_data[i:i + chunk_size]

                    _log_player_request(
                        "segment:catchup_ts_response",
                        request,
                        token,
                        {"decoded_url": decoded_url, "bytes": len(_cu_data), "elapsed": round(_cu_elapsed, 3)},
                    )
                    return StreamingResponse(stream_catchup_ts(), media_type="video/mp2t",
                                            headers={
                                                "Cache-Control": "no-cache, no-store",
                                                "X-Accel-Buffering": "no",
                                                "Access-Control-Allow-Origin": "*",
                                                "Connection": "keep-alive",
                                                "X-Accel-Timeout": "0",
                                            })
        except Exception as e:
            _log_player_request("segment:catchup_error", request, token, {"decoded_url": decoded_url, "error": repr(e)}, level="ERROR")
            logger.error(f"Catchup segment error: {e}")
            diag_log("ERROR", "catchup", f"Catchup segment error: {e}")
            raise HTTPException(status_code=502, detail=f"Catchup segment failed: {e}")

    ts_prefetch: tuple[bytes, float, bool] | None = None
    if is_ts:
        max_attempts = 6
        seg_name_pf = decoded_url.split("/")[-1].split("?")[0]
        user_name_pf = _sessions.get(session_key, {}).get("user_name") or token[:8]
        channel_name_pf = _sessions.get(session_key, {}).get("channel", "")
        data_pf = b""
        elapsed_pf = 0.0
        from_cache_pf = False
        for attempt in range(max_attempts):
            data_pf, elapsed_pf, from_cache_pf = await _get_segment(decoded_url, hls)
            total_pf = len(data_pf)
            if total_pf >= 1_000:
                break
            logger.warning(f"⚠️ EMPTY SEGMENT [{user_name_pf}] {seg_name_pf}: {total_pf} bytes")
            diag_log(
                "WARNING",
                "segment",
                f"EMPTY SEGMENT [{user_name_pf}] {channel_name_pf} {seg_name_pf}: {total_pf} bytes",
            )
            _ev0 = {
                "time": time.time(), "user": user_name_pf, "channel": channel_name_pf,
                "type": "slow", "elapsed": round(elapsed_pf, 2),
                "size_kb": round(total_pf / 1024, 1), "mbps": 0.0,
                "seg": f"⚠️ LEER: {seg_name_pf}", "provider_id": user.get("provider_id")
            }
            _segment_events.append(_ev0)
            if len(_segment_events) > 500: _segment_events.pop(0)
            try:
                db.add_segment_event(_ev0)
            except Exception:
                pass
            if attempt < max_attempts - 1:
                _segment_cache.pop(decoded_url, None)
                await asyncio.sleep(min(2.0, 0.25 * (2 ** attempt)))
                continue
            raise HTTPException(status_code=502, detail="Empty segment after retries")

        ts_prefetch = (data_pf, elapsed_pf, from_cache_pf)

    async def stream_segment():
        try:
            if is_ts:
                assert ts_prefetch is not None
                data, elapsed, _from_cache = ts_prefetch
                total = len(data)

                size_kb = total / 1024
                safe_elapsed = max(elapsed, 0.001)
                speed_mbps = min((total * 8) / (safe_elapsed * 1_000_000), 10000.0)
                seg_name = decoded_url.split("/")[-1].split("?")[0]
                user_name = _sessions.get(session_key, {}).get("user_name") or token[:8]
                channel_name_log = _sessions.get(session_key, {}).get("channel", "")
                debug_mode = db.get_setting("segment_debug", "0") == "1"

                if _from_cache:
                    if debug_mode:
                        _ev_cache = {"time": time.time(), "user": user_name, "channel": channel_name_log,
                                "type": "ok", "elapsed": round(elapsed, 2),
                                "size_kb": round(size_kb), "mbps": round(speed_mbps, 1),
                                "seg": f"⚡ {seg_name}", "provider_id": user.get("provider_id")}
                        _segment_events.append(_ev_cache)
                        try: db.add_segment_event(_ev_cache)
                        except Exception: pass
                elif elapsed > 2.0:
                    logger.warning(f"⚠️ SLOW SEGMENT [{user_name}] {seg_name}: {elapsed:.1f}s, {speed_mbps:.1f}Mbit/s")
                    diag_log(
                        "WARNING",
                        "segment",
                        f"SLOW SEGMENT [{user_name}] {channel_name_log} {seg_name}: {elapsed:.1f}s, {speed_mbps:.1f}Mbit/s",
                    )
                    _ev1 = {"time": time.time(), "user": user_name, "channel": channel_name_log,
                            "type": "slow", "elapsed": round(elapsed, 2),
                            "size_kb": round(size_kb), "mbps": round(speed_mbps, 1),
                            "seg": seg_name, "provider_id": user.get("provider_id")}
                    _segment_events.append(_ev1)
                    try: db.add_segment_event(_ev1)
                    except Exception: pass
                elif elapsed > 1.0:
                    _ev2 = {"time": time.time(), "user": user_name, "channel": channel_name_log,
                            "type": "delayed", "elapsed": round(elapsed, 2),
                            "size_kb": round(size_kb), "mbps": round(speed_mbps, 1),
                            "seg": seg_name, "provider_id": user.get("provider_id")}
                    _segment_events.append(_ev2)
                    try: db.add_segment_event(_ev2)
                    except Exception: pass
                elif debug_mode:
                    _ev3 = {"time": time.time(), "user": user_name, "channel": channel_name_log,
                            "type": "ok", "elapsed": round(elapsed, 2),
                            "size_kb": round(size_kb), "mbps": round(speed_mbps, 1),
                            "seg": seg_name, "provider_id": user.get("provider_id")}
                    _segment_events.append(_ev3)
                    try: db.add_segment_event(_ev3)
                    except Exception: pass

                if len(_segment_events) > 500: _segment_events.pop(0)

                chunk_size = 524288
                for i in range(0, len(data), chunk_size):
                    yield data[i:i + chunk_size]
                return

            timeout = httpx.Timeout(hls["hls_timeout"], read=hls["hls_read_timeout"])
            async with make_iptv_client(
                timeout=timeout,
                follow_redirects=hls["hls_follow_redirects"],
                headers=make_headers(hls)
            ) as client:
                resp = await client.get(decoded_url)
                resp.raise_for_status()
                rewritten = rewrite_hls_playlist(resp.text, decoded_url, public_url_seg, token)
                yield rewritten.encode()
                return
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _log_player_request("segment:error", request, token, {"decoded_url": decoded_url, "is_ts": is_ts, "error": repr(e)}, level="ERROR")
            logger.error(f"Segment error: {e}")
            diag_log("ERROR", "segment", f"Segment error: {e}")
            if session_key and session_key in _sessions:
                s = _sessions.pop(session_key)
                db.session_end(token)
                db.end_watch_log(s["log_id"], int(time.time() - s.get("log_start", s["start"])))

    media_type = "application/vnd.apple.mpegurl" if not is_ts else "video/mp2t"
    _log_player_request("segment:response_streaming", request, token, {"decoded_url": decoded_url, "is_ts": is_ts, "media_type": media_type})
    return StreamingResponse(stream_segment(), media_type=media_type,
                             headers={
                                 "Cache-Control": "no-cache, no-store",
                                 "X-Accel-Buffering": "no",
                                 "Access-Control-Allow-Origin": "*",
                             })


@proxy_app.get("/iptv/{token}/stop")
async def stop_stream(token: str, request: Request = None):
    # Clean up any session for this token
    stale = [k for k, s in _sessions.items() if s["token"] == token]
    for k in stale:
        s = _sessions.pop(k)
        db.end_watch_log(s["log_id"], int(time.time() - s.get("log_start", s["start"])))
    db.session_end(token)
    return {"ok": True}


@proxy_app.get("/iptv/{token}/catchup/{channel_id}")
async def proxy_catchup(token: str, channel_id: str, utc: str = None, lutc: str = None, request: Request = None):
    _log_player_request("catchup:request", request, token, {"channel_id": channel_id, "utc": utc, "lutc": lutc})
    user = db.get_user_by_token(token)
    if not user or not user["active"]:
        _log_player_request("catchup:forbidden", request, token, {"channel_id": channel_id}, level="WARNING")
        raise HTTPException(status_code=403, detail="Invalid or disabled token")
    with db.conn() as con:
        row = con.execute(
            "SELECT * FROM channels WHERE tvg_id = ? LIMIT 1", (channel_id,)
        ).fetchone()
    if not row:
        _log_player_request("catchup:not_found", request, token, {"channel_id": channel_id}, level="WARNING")
        raise HTTPException(status_code=404, detail="Channel not found")
    ch = dict(row)
    stream_url = ch["stream_url"]
    encoded = urllib.parse.quote(stream_url, safe="")
    redirect_url = f"/iptv/{token}/stream?url={encoded}"
    if utc:
        redirect_url += f"&utc={utc}"
    if lutc:
        redirect_url += f"&lutc={lutc}"
    _log_player_request("catchup:redirect_stream", request, token, {"channel_id": channel_id, "redirect_url": redirect_url})
    return RedirectResponse(url=redirect_url)


# EPG cache: (content, fetched_at_timestamp, source_url)
_epg_cache: dict = {"content": None, "fetched_at": 0, "url": ""}

# Parsed EPG tree cache — avoid re-parsing XML on every channel switch
_epg_tree_cache: dict = {"root": None, "content_hash": None}

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
        async with make_iptv_client(timeout=120, follow_redirects=True) as client:
            resp = await client.get(source_url)
            resp.raise_for_status()
            content_text = resp.text

        # Filter EPG to only include channels we have in DB
        filter_epg = db.get_setting("epg_filter_channels", "0") == "1"
        if filter_epg:
            content_text = _filter_epg_xml(content_text, days_back=7)

        _epg_cache = {"content": content_text, "fetched_at": now, "url": source_url}
        _epg_tree_cache["root"] = None  # invalidate parsed tree
        _tvg_id_cache.clear()           # invalidate tvg_id lookup cache
        logger.info(f"EPG cached ({len(content_text)//1024}KB)")
        # Write to disk so admin-app thread can read it too
        try:
            with open("/data/epg_cache.xml", "w", encoding="utf-8") as _f:
                _f.write(content_text)
        except Exception as _e:
            logger.warning(f"EPG disk cache write failed: {_e}")
            diag_log("WARNING", "epg", f"EPG disk cache write failed: {_e}")
        return HTMLResponse(content=content_text, media_type="application/xml",
                           headers={"X-EPG-Cache": "MISS"})
    except Exception as e:
        if _epg_cache["content"]:
            logger.warning(f"EPG fetch failed, serving stale cache: {e}")
            diag_log("WARNING", "epg", f"EPG fetch failed, serving stale cache: {e}")
            return HTMLResponse(content=_epg_cache["content"], media_type="application/xml",
                               headers={"X-EPG-Cache": "STALE"})
        raise HTTPException(status_code=502, detail=f"EPG fetch failed: {e}")


def _filter_epg_xml(xml_content: str, days_back: int = 1, days_forward: int = 7) -> str:
    """Filter EPG XML – channel whitelist + time window [now−days_back, now+days_forward] + channel order."""
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
            start_str = prog.get("start", "")
            if start_str:
                dt = _parse_xmltv_datetime(start_str)
                if dt is not None and not (t_from <= dt <= t_to):
                    continue
            new_root.append(prog)

        return ET.tostring(new_root, encoding="unicode", xml_declaration=True)
    except Exception as e:
        logger.error(f"EPG filter failed: {e}")
        diag_log("ERROR", "epg", f"EPG filter failed: {e}")
        return xml_content


@proxy_app.get("/iptv/epg-{days}d.xml")
async def global_epg_days(days: int, force: str = None):
    """EPG filtered to N days back and N days forward from UTC now (symmetric window)."""
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
            async with make_iptv_client(timeout=120, follow_redirects=True) as client:
                resp = await client.get(source_url)
                resp.raise_for_status()
                raw = resp.text
            _epg_cache = {"content": raw, "fetched_at": now_ts, "url": source_url}
            try:
                with open("/data/epg_cache.xml", "w", encoding="utf-8") as _f:
                    _f.write(raw)
            except Exception as _e:
                logger.warning(f"EPG disk cache write failed: {_e}")
                diag_log("WARNING", "epg", f"EPG disk cache write failed: {_e}")
        except Exception as e:
            raw = _epg_cache.get("content") or ""
            if not raw:
                raise HTTPException(status_code=502, detail=str(e))
    else:
        raw = _epg_cache["content"]
    # „7d“ = gleiches Fenster nach hinten und vorn (Catchup braucht Historie; vorher war days_back=1 irreführend).
    filtered = _filter_epg_xml(raw, days_back=days, days_forward=days)
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

# Admin-Token-Hashing (_hash_admin_token, _verify_admin_token, _PBKDF2_ITERATIONS)
# liegt in security_util.py und wird oben importiert.


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
    db.set_setting("admin_token", _hash_admin_token(token))
    db.set_setting("base_url", base_url)
    if proxy_url:
        db.set_setting("proxy_url", proxy_url)
    return {"ok": True}

# Brute-force protection: track failed attempts per IP
_failed_attempts: dict = {}  # {ip: {"count": int, "blocked_until": float}}
MAX_ATTEMPTS = 10
BLOCK_SECONDS = 300  # 5 minutes

def check_admin(x_admin_token: str = Header(...), request: Request = None):
    # Echte Verbindungs-IP verwenden. X-Forwarded-For ist client-seitig fälschbar und
    # würde den Brute-Force-Zähler aushebeln; das Admin-Panel läuft ohnehin nur im LAN.
    ip = ""
    if request and request.client:
        ip = request.client.host

    now = time.time()
    # Abgelaufene Sperren aufräumen (verhindert unbegrenztes Wachstum des Dicts)
    for _k in [k for k, v in _failed_attempts.items() if v.get("blocked_until", 0) < now and v.get("count", 0) == 0]:
        _failed_attempts.pop(_k, None)
    attempt = _failed_attempts.get(ip, {"count": 0, "blocked_until": 0})

    # Check if blocked
    if attempt["blocked_until"] > now:
        remaining = int(attempt["blocked_until"] - now)
        raise HTTPException(status_code=429, detail=f"Too many failed attempts. Try again in {remaining}s.")

    admin_token = db.get_admin_token()

    if not admin_token or not _verify_admin_token(x_admin_token, admin_token):
        attempt["count"] += 1
        if attempt["count"] >= MAX_ATTEMPTS:
            attempt["blocked_until"] = now + BLOCK_SECONDS
            logger.warning(f"Admin login blocked for {ip} after {MAX_ATTEMPTS} failed attempts")
            diag_log("WARNING", "admin", f"Admin login blocked for {ip} after {MAX_ATTEMPTS} failed attempts")
        _failed_attempts[ip] = attempt
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Erfolg: alten Klartext-Token transparent auf einen Hash migrieren
    # (nur wenn er in der DB liegt – nicht bei festem ADMIN_TOKEN aus der Env).
    if not os.getenv("ADMIN_TOKEN") and not admin_token.startswith("pbkdf2_sha256$"):
        try:
            db.set_setting("admin_token", _hash_admin_token(x_admin_token))
        except Exception:
            pass

    # Success – reset counter
    if ip in _failed_attempts:
        del _failed_attempts[ip]

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
        u["short_playlist_url"] = f"{short_base}/{short_tok}.m3u"
    return users

@admin_app.post("/api/users")
def create_user(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    notes = body.get("notes", "").strip()
    max_streams = body.get("max_streams", 1)
    allowed_groups = body.get("allowed_groups", "").strip() if body.get("allowed_groups") else None
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    provider_id = body.get("provider_id")
    m3u_source = db.get_setting("source_m3u_url", "")
    if provider_id is not None:
        try:
            provider_id = int(provider_id)
            p = db.get_provider(provider_id)
            if p:
                m3u_source = p.get("source_url") or m3u_source
        except Exception:
            provider_id = None
    token = str(uuid.uuid4()).replace("-", "")[:24]
    user = db.create_user(name=name, token=token, m3u_source=m3u_source, notes=notes, provider_id=provider_id)
    if allowed_groups:
        db.update_user(user["id"], {"allowed_groups": allowed_groups})
    short_token = db.generate_short_token(user["id"])
    proxy_url = db.get_proxy_url()
    short_domain = db.get_setting("short_domain", "")
    short_base = short_domain.rstrip("/") if short_domain else proxy_url
    return {**user,
            "short_token": short_token,
            "playlist_url": f"{proxy_url}/iptv/{token}/playlist.m3u",
            "short_playlist_url": f"{short_base}/{short_token}.m3u",
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

@proxy_app.get("/{short_token}.m3u")
@proxy_app.get("/{short_token}.m3u8")
async def short_playlist_compact(short_token: str):
    """Compact short URL redirect, e.g. /AbCd1234.m3u"""
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
    if "provider_id" in body:
        try:
            pid = int(body.get("provider_id")) if body.get("provider_id") is not None else None
        except Exception:
            pid = None
        if pid:
            p = db.get_provider(pid)
            if p:
                body["m3u_source"] = p.get("source_url", "")
                body["provider_id"] = pid
            else:
                body["provider_id"] = None
        else:
            body["provider_id"] = None
    db.update_user(user_id, body)
    return {"ok": True}

@admin_app.put("/api/users/{user_id}/groups")
def update_user_groups(user_id: int, body: dict, _=Depends(check_admin)):
    """Set allowed channel groups for a user. Empty list = all groups allowed."""
    groups = body.get("allowed_groups", [])
    if isinstance(groups, list):
        value = ",".join(g.strip() for g in groups if g.strip()) or None
    else:
        value = str(groups).strip() or None
    db.update_user(user_id, {"allowed_groups": value})
    return {"ok": True}

@admin_app.get("/api/users/{user_id}/logs")
def get_user_logs(user_id: int, limit: int = 200, offset: int = 0, date_from: str = "", date_to: str = "", _=Depends(check_admin)):
    return db.get_user_logs(user_id, limit=limit, offset=offset, date_from=date_from, date_to=date_to)

@admin_app.delete("/api/users/{user_id}/logs")
def delete_user_logs(user_id: int, _=Depends(check_admin)):
    db.clear_user_logs(user_id)
    return {"ok": True}

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

@admin_app.get("/api/channels/group-mappings")
def get_group_mappings(_=Depends(check_admin)):
    return db.get_group_mappings()

@admin_app.post("/api/channels/group-rename")
def rename_group(body: dict, _=Depends(check_admin)):
    old_name = body.get("old_name", "").strip()
    new_name = body.get("new_name", "").strip()
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="old_name and new_name required")
    db.rename_group(old_name, new_name)
    return {"ok": True}

@admin_app.post("/api/channels/group-mapping-delete")
def delete_group_mapping(body: dict, _=Depends(check_admin)):
    original_name = body.get("original_name", "").strip()
    if not original_name:
        raise HTTPException(status_code=400, detail="original_name required")
    db.delete_group_mapping(original_name)
    return {"ok": True}

# ── User Group CRUD ────────────────────────────────────────────────────────────

@admin_app.get("/api/user-groups")
def list_user_groups(_=Depends(check_admin)):
    return db.get_user_groups()

@admin_app.post("/api/user-groups")
def create_user_group(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    try:
        return db.create_user_group(name)
    except Exception as e:
        err = str(e)
        if "UNIQUE" in err or "already exists" in err.lower():
            raise HTTPException(status_code=409, detail="Gruppe bereits vorhanden")
        logger.error(f"create_user_group error: {e}")
        diag_log("ERROR", "admin", f"create_user_group error: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler: {err}")

@admin_app.put("/api/user-groups/{group_id}/rename")
def rename_user_group_alt(group_id: int, body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    if not name: raise HTTPException(status_code=400, detail="name required")
    db.rename_user_group(group_id, name)
    return {"ok": True}

@admin_app.put("/api/user-groups/{group_id}")
def update_user_group(group_id: int, body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    db.rename_user_group(group_id, name)
    return {"ok": True}

@admin_app.delete("/api/user-groups/{group_id}")
def delete_user_group(group_id: int, _=Depends(check_admin)):
    db.delete_user_group(group_id)
    return {"ok": True}

@admin_app.post("/api/user-groups/reorder")
def reorder_user_groups(body: dict, _=Depends(check_admin)):
    ordered_ids = body.get("ordered_ids", [])
    db.reorder_user_groups([int(i) for i in ordered_ids])
    return {"ok": True}

@admin_app.get("/api/channels/provider-group-order")
def get_provider_group_order(_=Depends(check_admin)):
    return db.get_provider_group_order()

@admin_app.post("/api/channels/provider-group-order")
def set_provider_group_order(body: dict, _=Depends(check_admin)):
    ordered_names = body.get("ordered_names", [])
    db.set_provider_group_order(ordered_names)
    return {"ok": True}


@admin_app.get("/api/user-groups/{group_id}/channels")
def get_user_group_channels(group_id: int, _=Depends(check_admin)):
    return db.get_user_group_channels(group_id)

@admin_app.post("/api/user-groups/{group_id}/channels")
def set_user_group_channels(group_id: int, body: dict, _=Depends(check_admin)):
    channel_ids = body.get("channel_ids", [])
    db.set_user_group_channels(group_id, channel_ids)
    return {"ok": True}

@admin_app.post("/api/user-groups/{group_id}/channels/add")
def add_channel_to_group(group_id: int, body: dict, _=Depends(check_admin)):
    channel_id = body.get("channel_id")
    if not channel_id:
        raise HTTPException(status_code=400, detail="channel_id required")
    db.add_channel_to_user_group(group_id, channel_id)
    return {"ok": True}

@admin_app.delete("/api/user-groups/{group_id}/channels/{channel_id}")
def remove_channel_from_group(group_id: int, channel_id: int, _=Depends(check_admin)):
    db.remove_channel_from_user_group(group_id, channel_id)
    return {"ok": True}

@admin_app.post("/api/channels/import")
async def import_channels(body: dict, _=Depends(check_admin)):
    url = body.get("url", "").strip()
    update_users = body.get("update_users", False)
    provider_name = body.get("provider_name", "").strip() or "Provider"
    provider_lines = body.get("provider_lines", 0)
    source_type = body.get("source_type", "m3u")
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    db.set_setting("source_m3u_url", url)
    try:
        async with make_iptv_client(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            channels = parse_m3u(resp.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch M3U: {e}")
    provider = db.upsert_provider(provider_name, url, provider_lines, source_type)
    db.upsert_channels(channels, provider_id=provider.get("id"))
    updated_users = 0
    if update_users:
        users = db.get_all_users()
        for u in users:
            db.update_user(u["id"], {"m3u_source": url, "provider_id": provider.get("id")})
            updated_users += 1
    return {"ok": True, "imported": len(channels), "updated_users": updated_users, "provider_id": provider.get("id")}

@admin_app.post("/api/channels/import-file")
async def import_channels_from_file(request: Request, _=Depends(check_admin)):
    """Accept a multipart upload of an .m3u file and import channels."""
    import io
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        raise HTTPException(status_code=400, detail="multipart/form-data required")
    form = await request.form()
    file_field = form.get("file")
    provider_name = (form.get("provider_name") or "").strip() or "Provider"
    provider_lines = int(form.get("provider_lines") or 0)
    source_type = (form.get("source_type") or "m3u").strip().lower()
    update_users_raw = form.get("update_users", "false")
    update_users = update_users_raw in ("true", "1", "yes")

    if file_field is None:
        raise HTTPException(status_code=400, detail="file field required")

    raw_bytes = await file_field.read()
    try:
        m3u_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        m3u_text = raw_bytes.decode("latin-1", errors="replace")

    channels = parse_m3u(m3u_text)
    if not channels:
        raise HTTPException(status_code=400, detail="No channels found in uploaded M3U file")

    import base64, hashlib
    file_hash = hashlib.md5(raw_bytes).hexdigest()[:8]
    fake_url = f"local://uploaded/{file_hash}/{file_field.filename or 'playlist.m3u'}"
    provider = db.upsert_provider(provider_name, fake_url, provider_lines, source_type)
    db.upsert_channels(channels, provider_id=provider.get("id"))

    updated_users = 0
    if update_users:
        users = db.get_all_users()
        for u in users:
            db.update_user(u["id"], {"provider_id": provider.get("id")})
            updated_users += 1

    return {"ok": True, "imported": len(channels), "updated_users": updated_users, "provider_id": provider.get("id")}

@admin_app.get("/api/providers")
def list_providers(_=Depends(check_admin)):
    return db.get_m3u_providers()

@admin_app.get("/api/providers/capacity")
def provider_capacity(_=Depends(check_admin)):
    result = db.get_provider_capacity()
    # Count active streams from in-memory sessions (most accurate)
    _cleanup_sessions()
    total_active = len(_sessions)
    # Since we no longer assign users to providers, show total active on all providers
    for p in result:
        p["active_streams"] = total_active
        cap = int(p.get("line_capacity") or 0)
        p["overbooked_by"] = max(0, total_active - cap) if cap > 0 else 0
    return result


async def _reload_provider_m3u_channels(provider_id: int) -> tuple[int, Optional[str]]:
    """Fetch M3U for this provider and replace only that provider's channels in DB.

    Returns (imported_count, error_message). error_message is None on success.
    """
    p = db.get_provider(provider_id)
    if not p:
        return 0, "provider not found"
    url = (p.get("source_url") or "").strip()
    if not url:
        return 0, "no source URL"
    if url.startswith("local://"):
        return 0, "local file — upload a new M3U file to replace channels"
    try:
        async with make_iptv_client(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            channels = parse_m3u(resp.text)
        db.upsert_channels(channels, provider_id=provider_id)
        db.set_provider_last_refresh(provider_id)
        return len(channels), None
    except Exception as e:
        return 0, str(e)


@admin_app.post("/api/providers")
def create_provider(body: dict, _=Depends(check_admin)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    url = (body.get("source_url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="source_url required")
    line_capacity = int(body.get("line_capacity") or 0)
    source_type = (body.get("source_type") or "m3u").strip().lower()
    refresh_hours = int(body.get("refresh_hours") or 0)
    p = db.upsert_provider(name, url, line_capacity, source_type, refresh_hours)
    return p

@admin_app.post("/api/providers/{provider_id}/refresh")
async def refresh_provider_now(provider_id: int, _=Depends(check_admin)):
    """Manually trigger an immediate M3U refresh for a specific provider."""
    p = db.get_provider(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="provider not found")
    url = (p.get("source_url") or "").strip()
    if not url or url.startswith("local://"):
        raise HTTPException(status_code=400, detail="Provider has no refreshable URL (uploaded file)")
    count, err = await _reload_provider_m3u_channels(provider_id)
    if err:
        raise HTTPException(status_code=502, detail=f"Refresh fehlgeschlagen: {err}")
    return {"ok": True, "imported": count}

@admin_app.put("/api/providers/{provider_id}")
async def update_provider(provider_id: int, body: dict, _=Depends(check_admin)):
    p = db.get_provider(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="provider not found")
    old_url = (p.get("source_url") or "").strip()
    name = (body.get("name") or p["name"]).strip()
    url = (body.get("source_url") or p["source_url"]).strip()
    line_capacity = int(body.get("line_capacity") if body.get("line_capacity") is not None else p.get("line_capacity") or 0)
    source_type = (body.get("source_type") or p.get("source_type") or "m3u").strip().lower()
    refresh_hours = int(body.get("refresh_hours") if body.get("refresh_hours") is not None else p.get("refresh_hours") or 0)
    updated = db.update_provider(provider_id, name, url, line_capacity, source_type, refresh_hours)
    new_url = (updated.get("source_url") or "").strip()

    extra: dict = {}
    if new_url != old_url:
        for u in db.get_all_users():
            src = (u.get("m3u_source") or "").strip()
            if u.get("provider_id") == provider_id or (old_url and src == old_url):
                db.update_user(u["id"], {"m3u_source": new_url})
        if old_url and (db.get_setting("source_m3u_url", "") or "").strip() == old_url:
            db.set_setting("source_m3u_url", new_url)
        if new_url and not new_url.startswith("local://"):
            count, err = await _reload_provider_m3u_channels(provider_id)
            if err:
                extra["channel_refresh_error"] = err
            else:
                extra["channels_refreshed"] = count

    return {**updated, **extra} if extra else updated

@admin_app.delete("/api/providers/{provider_id}")
def delete_provider(provider_id: int, _=Depends(check_admin)):
    p = db.get_provider(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="provider not found")
    db.delete_provider(provider_id)
    return {"ok": True}

@admin_app.post("/api/channels/refresh")
async def refresh_channels(_=Depends(check_admin)):
    if db.has_m3u_providers():
        raise HTTPException(
            status_code=400,
            detail="Anbieter-Modus aktiv: bitte unter Anbieter pro Eintrag ↻ verwenden. "
            "Der globale Refresh nutzt nur die gespeicherte Legacy-URL und würde sonst alle Kanäle überschreiben.",
        )
    url = db.get_setting("source_m3u_url", "")
    if not url:
        raise HTTPException(status_code=400, detail="No source URL saved.")
    try:
        async with make_iptv_client(timeout=60, follow_redirects=True) as client:
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
            async with make_iptv_client(timeout=120, follow_redirects=True) as client:
                resp = await client.get(source_url)
                resp.raise_for_status()
                raw = resp.text
            _epg_cache = {"content": raw, "fetched_at": now_ts, "url": source_url}
            try:
                with open("/data/epg_cache.xml", "w", encoding="utf-8") as _f:
                    _f.write(raw)
            except Exception as _e:
                logger.warning(f"EPG disk cache write failed: {_e}")
                diag_log("WARNING", "epg", f"EPG disk cache write failed: {_e}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"EPG fetch failed: {e}")
    else:
        raw = _epg_cache["content"]

    if days in (1, 3, 7):
        filtered = _filter_epg_xml(raw, days_back=days, days_forward=days)
        fname = f"epg-{days}d.xml"
    else:
        filtered = _filter_epg_xml(raw)
        fname = "epg.xml"

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
        async with make_iptv_client(timeout=120, follow_redirects=True) as client:
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

@admin_app.get("/api/epg/status")
def epg_status(_=Depends(check_admin)):
    fetched_at = _epg_cache.get("fetched_at", 0)
    content = _epg_cache.get("content", "")
    size_kb = len(content) // 1024 if content else 0
    return {
        "fetched_at": fetched_at,
        "size_kb": size_kb,
        "source_url": _epg_cache.get("url", ""),
    }

@admin_app.post("/api/epg")
def add_epg(body: dict, _=Depends(check_admin)):
    name = body.get("name", "").strip()
    url = body.get("url", "").strip()
    provider_id = body.get("provider_id")
    if provider_id is not None:
        try: provider_id = int(provider_id)
        except: provider_id = None
    if not name or not url:
        raise HTTPException(status_code=400, detail="name and url required")
    return db.add_epg_source(name, url, provider_id)

@admin_app.put("/api/epg/{epg_id}")
def update_epg(epg_id: int, body: dict, _=Depends(check_admin)):
    db.update_epg_source(epg_id, body)
    return {"ok": True}

@admin_app.delete("/api/epg/{epg_id}")
def delete_epg(epg_id: int, _=Depends(check_admin)):
    db.delete_epg_source(epg_id)
    return {"ok": True}

def _get_epg_root():
    """Get parsed EPG XML root, using cached version if content unchanged."""
    content = _epg_cache.get("content")
    if not content:
        try:
            with open("/data/epg_cache.xml", "r", encoding="utf-8") as _f:
                content = _f.read()
        except Exception:
            return None
    if not content:
        return None
    # Must reflect content bytes, not only length (same-size EPG updates used to leave a stale tree).
    content_hash = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()
    if _epg_tree_cache["root"] is not None and _epg_tree_cache["content_hash"] == content_hash:
        return _epg_tree_cache["root"]
    try:
        root = ET.fromstring(content)
        _epg_tree_cache["root"] = root
        _epg_tree_cache["content_hash"] = content_hash
        return root
    except Exception:
        return None


# Channel name → tvg_id lookup cache
_tvg_id_cache: dict = {}

def _get_now_playing(channel_name: str) -> dict:
    """Look up what is currently playing on a channel from the EPG cache."""
    try:
        root = _get_epg_root()
        if root is None:
            return {}

        now = datetime.now(timezone.utc)

        # tvg_id lookup with cache
        if channel_name not in _tvg_id_cache:
            ch_record = db.get_channel_by_name(channel_name) or {}
            tvg_id = ch_record.get("tvg_id", "").strip()
            if not tvg_id:
                for ch_el in root.findall("channel"):
                    disp = ch_el.findtext("display-name") or ""
                    if channel_name.lower() in disp.lower() or disp.lower() in channel_name.lower():
                        tvg_id = ch_el.get("id", "")
                        break
            _tvg_id_cache[channel_name] = tvg_id

        tvg_id = _tvg_id_cache.get(channel_name, "")
        if not tvg_id:
            return {}

        # Find currently running programme
        for programme in root.findall("programme"):
            if programme.get("channel", "") != tvg_id:
                continue
            start = _parse_xmltv_datetime(programme.get("start", ""))
            stop = _parse_xmltv_datetime(programme.get("stop", ""))
            if start is None or stop is None:
                continue
            if start <= now <= stop:
                return {
                    "title": programme.findtext("title") or "",
                    "desc":  (programme.findtext("desc") or "")[:120],
                    "start": start.strftime("%H:%M"),
                    "stop":  stop.strftime("%H:%M"),
                }
        return {}
    except Exception as e:
        logger.debug(f"EPG now_playing error for '{channel_name}': {e}")
        return {}


def _stats_title_at_catchup_time(channel: str, catchup_time_str: str, epg_root) -> str:
    """Programme title at the catchup wall-clock position — overrides stale stored epg_title."""
    if not channel or not catchup_time_str or epg_root is None:
        return ""
    try:
        t = _epg_title_at_time_half_open(channel, catchup_time_str.strip(), epg_root)
        return (t or "").strip()
    except Exception:
        return ""


@admin_app.get("/api/stats")
def get_stats(_=Depends(check_admin)):
    users = db.get_all_users()
    _cleanup_sessions()
    active_sessions = db.get_active_sessions()
    ch_stats = db.get_channels_count()
    recent_logs = db.get_all_logs(limit=20)
    epg_root_for_logs = _get_epg_root()
    now_ts = time.time()
    sessions_out = []
    for s in active_sessions:
        now_playing = _get_now_playing(s["channel"])
        tok = (s.get("token") or "").strip()
        ch = (s.get("channel") or "").strip()
        cu_key = f"catchup::{tok}::{ch}"
        cv_cu = _catchup_sessions.get(cu_key)
        if cv_cu and now_ts - cv_cu["last_seen"] < _catchup_idle_ttl_seconds(cv_cu):
            ct = (cv_cu.get("catchup_time") or "").strip()
            t_at = _stats_title_at_catchup_time(ch, ct, epg_root_for_logs)
            disp = t_at or (cv_cu.get("epg_title") or "").strip()
            if disp:
                np_live = now_playing if isinstance(now_playing, dict) else {}
                now_playing = {
                    "title": disp,
                    "desc": np_live.get("desc", ""),
                    "start": np_live.get("start", ""),
                    "stop": np_live.get("stop", ""),
                }
        sessions_out.append({
            "user": s["user_name"],
            "channel": s["channel"],
            "started_at": s.get("started_at"),
            "ip": s.get("ip_address", ""),
            "now_playing": now_playing,
        })
    logs_out = []
    for l in recent_logs:
        epg_title = (l.get("epg_title") or "").strip()
        if l.get("is_catchup") and l.get("catchup_time"):
            # For catchup: look up what was on at that time (reuse parsed EPG — not ET.fromstring per row).
            try:
                if epg_root_for_logs is not None:
                    ch_rec = db.get_channel_by_name(l["channel"]) or {}
                    tvg_id = ch_rec.get("tvg_id", "").strip()
                    if not tvg_id:
                        for ch_el in epg_root_for_logs.findall("channel"):
                            disp = ch_el.findtext("display-name") or ""
                            if l["channel"].lower() in disp.lower() or disp.lower() in l["channel"].lower():
                                tvg_id = ch_el.get("id", "")
                                break
                    if tvg_id:
                        ct = _parse_catchup_wall_time(l["catchup_time"])
                        if ct:
                            for prog in epg_root_for_logs.findall("programme"):
                                if prog.get("channel", "") != tvg_id:
                                    continue
                                ps = _parse_xmltv_datetime(prog.get("start", ""))
                                pe = _parse_xmltv_datetime(prog.get("stop", ""))
                                if _epg_programme_contains_instant_half_open(ps, pe, ct):
                                    epg_title = prog.findtext("title") or epg_title
                                    break
            except Exception:
                pass
        logs_out.append({
            "user": l["user_name"],
            "channel": l["channel"],
            "started_at": l["started_at"],
            "duration": l["duration_seconds"],
            "ip": l.get("ip_address",""),
            "is_catchup": l.get("is_catchup", 0),
            "catchup_time": l.get("catchup_time",""),
            "epg_title": epg_title,
        })
    # Build active catchup list from in-memory _catchup_sessions
    _cleanup_sessions()
    active_catchup_out = []
    for ck, cv in list(_catchup_sessions.items()):
        if now_ts - cv["last_seen"] < _catchup_idle_ttl_seconds(cv):
            # Get user name and epg title from DB log
            try:
                with db.conn() as con:
                    row = con.execute(
                        "SELECT wl.channel, wl.epg_title, wl.catchup_time, u.name as user_name "
                        "FROM watch_logs wl JOIN users u ON u.id = wl.user_id "
                        "WHERE wl.id = ?", (cv["log_id"],)
                    ).fetchone()
                if row:
                    _ct = (cv.get("catchup_time") or row["catchup_time"] or "").strip()
                    _from_epg = _stats_title_at_catchup_time(row["channel"], _ct, epg_root_for_logs)
                    _cu_title = _from_epg or (cv.get("epg_title") or row["epg_title"] or "").strip()
                    if _from_epg and _from_epg != (cv.get("epg_title") or "").strip():
                        _catchup_sessions[ck]["epg_title"] = _from_epg
                    active_catchup_out.append({
                        "user": row["user_name"],
                        "channel": row["channel"],
                        "epg_title": _cu_title,
                        "catchup_time": cv.get("catchup_time") or row["catchup_time"] or "",
                        "duration": int(now_ts - cv["start"]),
                        "ip": cv.get("ip", ""),
                    })
            except Exception:
                pass

    return {
        "total_users": len(users),
        "active_streams": len(active_sessions) + len([cv for cv in _catchup_sessions.values() if time.time() - cv["last_seen"] < _catchup_idle_ttl_seconds(cv)]),
        "active_sessions": sessions_out,
        "active_catchup": active_catchup_out,
        "recent_logs": logs_out,
        "watch_logs_today": db.get_logs_today_count(),
        "total_channels": ch_stats["total"] or 0,
        "enabled_channels": ch_stats["enabled"] or 0,
    }

@admin_app.get("/api/logs")
def get_all_logs(limit: int = 200, _=Depends(check_admin)):
    return db.get_all_logs(limit)

@admin_app.get("/api/logs/query")
def query_logs(
    page: int = 1,
    page_size: int = 100,
    user: str = "",
    date_from: str = "",
    date_to: str = "",
    _=Depends(check_admin)
):
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 500))
    result = db.query_logs(
        limit=page_size,
        offset=(page - 1) * page_size,
        user_query=user,
        date_from=date_from,
        date_to=date_to,
    )
    total = int(result.get("total", 0))
    return {
        "items": result.get("items", []),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)) if total else 1,
        "stored_total": result.get("stored_total", total),
        "oldest": result.get("oldest"),
        "newest": result.get("newest"),
    }

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
        "m3u_refresh_hours":    s.get("m3u_refresh_hours", "0"),
        "m3u_last_refresh":     s.get("m3u_last_refresh", ""),
        "prefetch_segments":    s.get("prefetch_segments", "2"),
        "segment_debug":        s.get("segment_debug", "0"),
        "diagnostics_enabled":  s.get("diagnostics_enabled", "1"),
        "player_request_debug": s.get("player_request_debug", "1"),
        "catchup_ttl":                  s.get("catchup_ttl", "900"),
        "catchup_ttl_after_endlist":    s.get("catchup_ttl_after_endlist", "900"),
        "catchup_guard_master":         s.get("catchup_guard_master", "1"),
        "catchup_strict_mode":          s.get("catchup_strict_mode", "1"),
        "catchup_sticky_recover":       s.get("catchup_sticky_recover", "1"),
        "catchup_auto_live_on_program_change": s.get("catchup_auto_live_on_program_change", "0"),
        "catchup_auto_live_keep_utc":   s.get("catchup_auto_live_keep_utc", "1"),
        "catchup_force_same_channel_live": s.get("catchup_force_same_channel_live", "1"),
        "catchup_hard_lock":            s.get("catchup_hard_lock", "1"),
        "diagnostic_timezone":  s.get("diagnostic_timezone", "Europe/Berlin"),
    }

@admin_app.post("/api/settings")
def update_settings(body: dict, _=Depends(check_admin)):
    allowed = {"base_url", "proxy_url", "source_m3u_url",
               "hls_timeout", "hls_read_timeout", "hls_chunk_size",
               "hls_user_agent", "hls_referer", "hls_follow_redirects",
               "epg_refresh_hours", "epg_filter_channels", "log_retention_days",
               "short_domain", "m3u_refresh_hours", "group_sort_prefix", "prefetch_segments", "segment_debug", "diagnostics_enabled", "player_request_debug",
               "catchup_ttl", "catchup_ttl_after_endlist", "catchup_guard_master", "catchup_strict_mode", "catchup_sticky_recover",
               "catchup_auto_live_on_program_change",
               "catchup_auto_live_keep_utc",
               "catchup_force_same_channel_live",
               "catchup_hard_lock",
               "diagnostic_timezone"}

    old_ret_raw = db.get_setting("log_retention_days", "-1")
    try:
        old_ret = int(old_ret_raw)
    except Exception:
        old_ret = -1
    new_ret = old_ret
    if "log_retention_days" in body:
        try:
            new_ret = int(str(body.get("log_retention_days", old_ret)).strip())
        except Exception:
            new_ret = old_ret

    for key, val in body.items():
        if key in allowed:
            if key == "diagnostic_timezone":
                val = _sanitize_diagnostic_timezone(val)
            db.set_setting(key, str(val))

    # Apply retention immediately when tightened.
    # -1: unlimited, 0: disabled (delete all), N>0: keep only last N days.
    if new_ret != old_ret:
        if new_ret == 0:
            db.clear_logs(0)
        elif new_ret > 0 and (old_ret == -1 or old_ret == 0 or new_ret < old_ret):
            db.clear_logs(new_ret)
    return {"ok": True}

@admin_app.post("/api/settings/change-password")
def change_password(body: dict, _=Depends(check_admin)):
    new_token = body.get("new_token", "").strip()
    if len(new_token) < 8:
        raise HTTPException(status_code=400, detail="Min 8 characters")
    if os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=400, detail="Password set via environment variable")
    db.set_setting("admin_token", _hash_admin_token(new_token))
    return {"ok": True}

FRONTEND = "/app/frontend"

@admin_app.get("/")
async def root():
    return RedirectResponse(url="/admin")

@admin_app.get("/admin")
async def admin_page():
    with open(f"{FRONTEND}/index.html") as f:
        return HTMLResponse(f.read(), headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })

@admin_app.get("/setup")
async def setup_page():
    with open(f"{FRONTEND}/setup.html") as f:
        return HTMLResponse(f.read())

@admin_app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    favicon_path = "/data/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return FileResponse(f"{FRONTEND}/favicon.ico", media_type="image/x-icon")

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
    if logo_type not in ("login", "app"):
        raise HTTPException(status_code=400, detail="Invalid logo type")
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
    if logo_type not in ("login", "app"):
        raise HTTPException(status_code=400, detail="Invalid logo type")
    filename = f"/data/custom_{logo_type}_logo.png"
    if os.path.exists(filename):
        os.remove(filename)
    return {"ok": True}


# ── VPN (OpenVPN) Integration ──────────────────────────────────────────────────

VPN_SETTINGS_KEYS = {
    "vpn_enabled", "vpn_user", "vpn_password", "vpn_ovpn_path"
}

_vpn_process: Optional[subprocess.Popen] = None
_vpn_log: list = []
VPN_OVPN_DIR = "/data/vpn"
VPN_AUTH_FILE = "/data/vpn/auth.txt"
VPN_LOG_MAX = 200


def _vpn_log_add(line: str):
    _vpn_log.append(line)
    if len(_vpn_log) > VPN_LOG_MAX:
        _vpn_log.pop(0)


def _vpn_reader(proc: subprocess.Popen):
    """Read OpenVPN stdout/stderr in background thread."""
    try:
        for line in proc.stdout:
            line = line.strip()
            if line:
                _vpn_log_add(line)
                logger.info(f"[openvpn] {line}")
    except Exception:
        pass


def vpn_is_running() -> bool:
    global _vpn_process
    # Check process is alive
    if _vpn_process is not None and _vpn_process.poll() is None:
        return True
    # Fallback: check if tun0 interface exists
    try:
        result = subprocess.run(["ip", "link", "show", "tun0"],
                                capture_output=True, timeout=2)
        return result.returncode == 0
    except Exception:
        return False


def vpn_get_tun_ip() -> str:
    """Get the IP address assigned to tun0 interface."""
    try:
        result = subprocess.run(
            ["ip", "addr", "show", "tun0"],
            capture_output=True, text=True, timeout=2
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return ""


def vpn_start() -> dict:
    global _vpn_process, _vpn_log

    if vpn_is_running():
        return {"ok": False, "error": "VPN läuft bereits"}

    ovpn_path = db.get_setting("vpn_ovpn_path", "")
    vpn_user  = db.get_setting("vpn_user", "")
    vpn_pass  = db.get_setting("vpn_password", "")

    if not ovpn_path or not os.path.exists(ovpn_path):
        return {"ok": False, "error": f"OVPN-Datei nicht gefunden: {ovpn_path}"}

    os.makedirs(VPN_OVPN_DIR, exist_ok=True)

    # Write auth file
    if vpn_user and vpn_pass:
        with open(VPN_AUTH_FILE, "w") as f:
            f.write(f"{vpn_user}\n{vpn_pass}\n")
        os.chmod(VPN_AUTH_FILE, 0o600)

    # Write a modified ovpn with auth-nocache
    split_ovpn_path = "/data/vpn/split.ovpn"
    with open(ovpn_path, "r") as f:
        ovpn_content = f.read()
    if "auth-nocache" not in ovpn_content:
        ovpn_content += "\nauth-nocache\n"
    with open(split_ovpn_path, "w") as f:
        f.write(ovpn_content)

    cmd = [
        "openvpn",
        "--config", split_ovpn_path,
    ]
    if vpn_user and vpn_pass:
        cmd += ["--auth-user-pass", VPN_AUTH_FILE]

    _vpn_log = []
    _vpn_log_add("⏳ OpenVPN wird gestartet (Split-Tunnel via SOCKS5)…")

    try:
        _vpn_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        t = threading.Thread(target=_vpn_reader, args=(_vpn_process,), daemon=True)
        t.start()
        # Wait for tun0 and start SOCKS5 proxy in background
        w = threading.Thread(target=_vpn_wait_for_tun, daemon=True)
        w.start()
        db.set_setting("vpn_enabled", "1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def vpn_stop() -> dict:
    global _vpn_process, _socks_process
    # Set DB flag FIRST to prevent auto-restart
    db.set_setting("vpn_enabled", "0")

    # Stop SOCKS proxy
    if _socks_process is not None and _socks_process.poll() is None:
        try:
            _socks_process.terminate()
            _socks_process.wait(timeout=5)
        except Exception:
            pass
    _socks_process = None

    if _vpn_process is not None:
        try:
            _vpn_process.terminate()
            _vpn_process.wait(timeout=10)
        except Exception:
            try:
                _vpn_process.kill()
            except Exception:
                pass
    _vpn_process = None

    # Kill any remaining openvpn processes
    try:
        subprocess.run(["pkill", "-f", "openvpn"], capture_output=True, timeout=3)
    except Exception:
        pass

    # Wait for tun interfaces to disappear (max 5s)
    import time
    for _ in range(10):
        try:
            result = subprocess.run(["ip", "link", "show"],
                                    capture_output=True, text=True, timeout=2)
            if "tun" not in result.stdout:
                break
        except Exception:
            break
        time.sleep(0.5)

    _vpn_log_add("🔴 OpenVPN + SOCKS5 Proxy gestoppt.")
    return {"ok": True}


@admin_app.get("/api/vpn")
def get_vpn_settings(_=Depends(check_admin)):
    s = db.get_all_settings()
    # List uploaded .ovpn files
    ovpn_files = []
    if os.path.exists(VPN_OVPN_DIR):
        ovpn_files = [f for f in os.listdir(VPN_OVPN_DIR) if f.endswith(".ovpn") and f != "split.ovpn"]
    return {
        "vpn_enabled":  s.get("vpn_enabled", "0"),
        "vpn_user":     s.get("vpn_user", ""),
        "vpn_password": s.get("vpn_password", ""),
        "vpn_ovpn_path": s.get("vpn_ovpn_path", ""),
        "vpn_running":  vpn_is_running(),
        "ovpn_files":   ovpn_files,
    }


@admin_app.post("/api/vpn")
def update_vpn_settings(body: dict, _=Depends(check_admin)):
    for key, val in body.items():
        if key in VPN_SETTINGS_KEYS:
            db.set_setting(key, str(val))
    return {"ok": True}


@admin_app.post("/api/vpn/start")
def vpn_start_endpoint(_=Depends(check_admin)):
    return vpn_start()


@admin_app.post("/api/vpn/stop")
def vpn_stop_endpoint(_=Depends(check_admin)):
    return vpn_stop()


_vpn_public_ip_cache: dict = {"ip": "", "ts": 0.0}
VPN_IP_CACHE_TTL = 60  # only check public IP every 60 seconds


@admin_app.get("/api/vpn/status")
async def get_vpn_status(_=Depends(check_admin)):
    running = vpn_is_running()
    public_ip = ""
    if running:
        now = time.time()
        # Use cached IP if fresh enough
        if _vpn_public_ip_cache["ip"] and now - _vpn_public_ip_cache["ts"] < VPN_IP_CACHE_TTL:
            public_ip = _vpn_public_ip_cache["ip"]
        else:
            for url in ["https://ifconfig.me/ip", "https://api.ipify.org", "https://checkip.amazonaws.com"]:
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        r = await client.get(url)
                        if r.status_code == 200:
                            public_ip = r.text.strip()
                            _vpn_public_ip_cache["ip"] = public_ip
                            _vpn_public_ip_cache["ts"] = now
                            break
                except Exception:
                    continue
    else:
        # VPN stopped – clear cache
        _vpn_public_ip_cache["ip"] = ""
        _vpn_public_ip_cache["ts"] = 0.0
    return {
        "running": running,
        "public_ip": public_ip,
        "log": _vpn_log[-50:],
    }


@admin_app.post("/api/vpn/upload")
async def vpn_upload_ovpn(request: Request, _=Depends(check_admin)):
    try:
        os.makedirs(VPN_OVPN_DIR, exist_ok=True)
        form = await request.form()
        file = form.get("file")
        if not file:
            raise HTTPException(status_code=400, detail="Keine Datei")
        filename = os.path.basename(file.filename)
        if not filename.endswith(".ovpn"):
            raise HTTPException(status_code=400, detail="Nur .ovpn Dateien erlaubt")
        dest = os.path.join(VPN_OVPN_DIR, filename)
        content = await file.read()
        with open(dest, "wb") as f:
            f.write(content)
        os.chmod(dest, 0o600)
        db.set_setting("vpn_ovpn_path", dest)
        logger.info(f"VPN: ovpn uploaded to {dest}")
        return {"ok": True, "filename": filename, "path": dest}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VPN upload error: {e}")
        diag_log("ERROR", "vpn", f"VPN upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_app.delete("/api/vpn/ovpn/{filename}")
def vpn_delete_ovpn(filename: str, _=Depends(check_admin)):
    path = os.path.join(VPN_OVPN_DIR, os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
    current = db.get_setting("vpn_ovpn_path", "")
    if current == path:
        db.set_setting("vpn_ovpn_path", "")
    return {"ok": True}


@admin_app.get("/api/segment-events")
def get_segment_events(days: int = 30, limit: int = 500, debug: int = 0, _=Depends(check_admin)):
    """Return segment events from DB (persistent, up to 30 days by default)."""
    try:
        include_ok = debug == 1 or db.get_setting("segment_debug", "0") == "1"
        return db.get_segment_events(limit=limit, days=days, include_ok=include_ok)
    except Exception:
        # Fallback to in-memory if DB not ready yet
        evs = list(reversed(_segment_events[-limit:]))
        if not include_ok:
            evs = [e for e in evs if e.get("type") != "ok"]
        return evs

@admin_app.get("/api/segment-events/stats")
def get_segment_stats(days: int = 30, _=Depends(check_admin)):
    """Aggregate buffering stats per channel from DB."""
    try:
        return db.get_segment_stats(days=days)
    except Exception:
        # Fallback to in-memory
        from collections import defaultdict
        stats = defaultdict(lambda: {"channel": "", "slow": 0, "delayed": 0, "total": 0, "elapsed_sum": 0.0, "mbps_sum": 0.0})
        for e in _segment_events:
            ch = e.get("channel", "?") or "?"
            s = stats[ch]; s["channel"] = ch
            if e["type"] == "slow": s["slow"] += 1
            elif e["type"] == "delayed": s["delayed"] += 1
            if e["type"] in ("slow", "delayed"):
                s["total"] += 1; s["elapsed_sum"] += e["elapsed"]; s["mbps_sum"] += e["mbps"]
        result = [{"channel": ch, "slow": s["slow"], "delayed": s["delayed"], "total": s["total"],
                   "avg_elapsed": round(s["elapsed_sum"]/s["total"],2) if s["total"] else 0,
                   "avg_mbps": round(s["mbps_sum"]/s["total"],1) if s["total"] else 0,
                   "score": s["slow"]*2+s["delayed"]} for ch, s in stats.items() if s["slow"]+s["delayed"]>0]
        result.sort(key=lambda x: x["score"], reverse=True)
        return result

@admin_app.delete("/api/segment-events")
def clear_segment_events(_=Depends(check_admin)):
    _segment_events.clear()
    try: db.clear_segment_events()
    except Exception: pass
    return {"ok": True}


@admin_app.get("/api/diagnostic-logs")
def get_diagnostic_logs_api(
    page: int = 1,
    page_size: int = 100,
    days: int = 30,
    level: str = "",
    source: str = "",
    _=Depends(check_admin),
):
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 500))
    days = max(1, min(int(days), 366))
    offset = (page - 1) * page_size
    lvl = level.strip() or None
    src_f = source.strip() or None
    result = db.get_diagnostic_logs(
        days=days, limit=page_size, offset=offset, level=lvl, source=src_f
    )
    total = int(result.get("total", 0))
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    return {
        "items": result.get("items", []),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "days": days,
    }


@admin_app.get("/api/diagnostic-logs/download")
def download_diagnostic_logs_api(
    days: int = 30,
    level: str = "",
    source: str = "",
    _=Depends(check_admin),
):
    days = max(1, min(int(days), 366))
    lvl = level.strip() or None
    src_f = source.strip() or None
    where = "WHERE datetime(created_at) >= datetime('now', ?)"
    params = [f"-{days} days"]
    if lvl:
        where += " AND UPPER(level) = UPPER(?)"
        params.append(lvl[:16])
    if src_f:
        where += " AND LOWER(source) = LOWER(?)"
        params.append(src_f[:80])

    with db.conn() as con:
        rows = con.execute(
            f"""
            SELECT id, level, source, message, created_at
            FROM diagnostic_logs
            {where}
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            tuple(params),
        ).fetchall()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "created_at", "level", "source", "message"])
    for r in rows:
        d = dict(r)
        w.writerow([
            d.get("id", ""),
            d.get("created_at", ""),
            d.get("level", ""),
            d.get("source", ""),
            d.get("message", ""),
        ])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"diagnostic-logs-{days}d-{ts}.csv"
    return Response(
        content=out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_app.delete("/api/diagnostic-logs")
def clear_diagnostic_logs_api(_=Depends(check_admin)):
    db.clear_diagnostic_logs()
    return {"ok": True}


@admin_app.get("/api/vpn/speedtest")
async def vpn_speedtest(_=Depends(check_admin)):
    """Run dual speedtest: internet speed + IPTV provider speed."""
    import time

    async def measure_url(url: str, max_bytes: int = 10_000_000, timeout_sec: int = 10) -> dict:
        try:
            start = time.monotonic()
            downloaded = 0
            async with make_iptv_client(
                timeout=httpx.Timeout(5, read=timeout_sec),
                follow_redirects=True
            ) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code not in (200, 206):
                        return {"ok": False, "error": f"HTTP {resp.status_code}"}
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        downloaded += len(chunk)
                        if downloaded >= max_bytes or (time.monotonic() - start) > timeout_sec:
                            break
            elapsed = time.monotonic() - start
            if elapsed > 0 and downloaded > 50_000:
                mbps = (downloaded * 8) / (elapsed * 1_000_000)
                return {"ok": True, "mbps": round(mbps, 1), "mb": round(downloaded/1_000_000, 2), "seconds": round(elapsed, 2)}
            return {"ok": False, "error": "Zu wenig Daten"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def streams_estimate(mbps: float) -> dict:
        return {
            "hd_720p":   int(mbps / 4),
            "fhd_1080p": int(mbps / 8),
            "uhd_4k":    int(mbps / 25),
        }

    # ── Test 1: Internet/VPN Speed ─────────────────────────────────────────
    internet_result = {"ok": False, "error": "Alle Server nicht erreichbar"}
    for url in [
        "https://speed.cloudflare.com/__down?bytes=10000000",
        "https://proof.ovh.net/files/10Mb.dat",
        "https://bouygues.testdebit.info/10M.iso",
    ]:
        r = await measure_url(url)
        if r["ok"]:
            internet_result = r
            internet_result["server"] = url.split("/")[2]
            break

    # ── Test 2: IPTV Provider Speed (parallel segments) ───────────────────
    iptv_result = {"ok": False, "error": "Kein IPTV-Kanal verfügbar"}

    # Collect up to 5 different channel segment URLs for parallel test
    segment_urls = []
    channels = db.get_channels(enabled_only=True)

    for ch in channels[:30]:
        if len(segment_urls) >= 5:
            break
        url = ch.get("stream_url", "")
        if not url or not url.startswith("http"):
            continue
        try:
            async with make_iptv_client(timeout=httpx.Timeout(4, read=8), follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                seg_url = None
                base = "/".join(url.split("/")[:-1])
                for line in resp.text.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and (".ts" in line or ".aac" in line):
                        seg_url = line if line.startswith("http") else f"{base}/{line}"
                        break
                if seg_url:
                    segment_urls.append(seg_url)
        except Exception:
            continue

    if segment_urls:
        import time
        # Download all segments in parallel
        async def fetch_seg(url: str) -> int:
            try:
                downloaded = 0
                async with make_iptv_client(timeout=httpx.Timeout(4, read=10), follow_redirects=True) as client:
                    async with client.stream("GET", url) as resp:
                        if resp.status_code not in (200, 206):
                            return 0
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            downloaded += len(chunk)
                return downloaded
            except Exception:
                return 0

        start = time.monotonic()
        results_parallel = await asyncio.gather(*[fetch_seg(u) for u in segment_urls])
        elapsed = time.monotonic() - start
        total_bytes = sum(results_parallel)

        if elapsed > 0 and total_bytes > 10_000:
            mbps = (total_bytes * 8) / (elapsed * 1_000_000)
            iptv_result = {
                "ok": True,
                "mbps": round(mbps, 1),
                "mb": round(total_bytes / 1_000_000, 2),
                "seconds": round(elapsed, 2),
                "server": segment_urls[0].split("/")[2] if segment_urls else "",
                "parallel": len(segment_urls),
            }
        else:
            iptv_result = {"ok": False, "error": "Zu wenig Daten von Segmenten"}

    # ── Bottleneck Analysis ────────────────────────────────────────────────
    bottleneck = None
    if internet_result.get("ok") and iptv_result.get("ok"):
        inet_mbps = internet_result["mbps"]
        iptv_mbps = iptv_result["mbps"]
        ratio = iptv_mbps / inet_mbps if inet_mbps > 0 else 0
        if ratio < 0.5:
            bottleneck = f"IPTV-Anbieter ist der Flaschenhals ({iptv_result['server']}) – nur {round(ratio*100)}% der VPN-Geschwindigkeit"
        elif ratio < 0.8:
            bottleneck = f"IPTV-Anbieter etwas langsamer ({round(ratio*100)}% der VPN-Geschwindigkeit)"
        else:
            bottleneck = f"Kein Flaschenhals – IPTV-Anbieter liefert {round(ratio*100)}% der VPN-Geschwindigkeit"

    return {
        "ok": True,
        "via_vpn": vpn_is_running(),
        "internet": {**internet_result, "streams": streams_estimate(internet_result.get("mbps", 0)) if internet_result.get("ok") else {}},
        "iptv":     {**iptv_result,     "streams": streams_estimate(iptv_result.get("mbps", 0))     if iptv_result.get("ok") else {}},
        "bottleneck": bottleneck,
    }