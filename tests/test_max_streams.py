"""Test: Bei Überschreitung von max_streams liefert /stream die 'Max Streams'-
Bild-M3U (wie der Gesperrt-Fall) statt eines nackten HTTP-429-Fehlers.
"""
import time

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def proxy(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    main.db.db_path = str(tmp_path / "ms.db")
    main.db.init()
    main._startup_done = True
    main._sessions.clear()
    main._catchup_sessions.clear()
    main._last_cleanup = time.time()  # Cleanup-Body via Throttle überspringen
    return TestClient(main.proxy_app)


def test_second_device_gets_max_streams_image(proxy):
    user = main.db.create_user(name="Limit", token="limittok", m3u_source="http://prov")
    main.db.update_user(user["id"], {"max_streams": 1})

    # Simuliere ein bereits aktives ANDERES Gerät desselben Users
    now = time.time()
    main._sessions["other-device"] = {
        "user_id": user["id"],
        "session_key": "other-device-key",
        "last_seen": now,
    }

    # Öffentliche Upstream-URL (besteht SSRF-Prüfung); der Max-Streams-Block
    # greift VOR dem Abruf, daher kein echter Netzwerkzugriff.
    r = proxy.get("/iptv/limittok/stream", params={"url": "http://8.8.8.8/live.m3u8"})

    assert r.status_code == 200
    assert "application/x-mpegURL" in r.headers.get("content-type", "")
    # Player überspringen ein JPEG-"Segment"; daher zeigt die M3U jetzt auf einen
    # echten MPEG-TS-Clip (vorgerendert, statisch ausgeliefert).
    assert "error-max-streams.ts" in r.text
    assert "#EXT-X-ENDLIST" in r.text


def test_max_streams_clip_endpoint_serves_mpegts(proxy):
    # Vorgerenderter Clip wird als MPEG-TS ausgeliefert und beginnt mit dem
    # TS-Sync-Byte 0x47 (echtes Video, nicht leer).
    r = proxy.get("/iptv/error-max-streams.ts")
    assert r.status_code == 200
    assert "video/mp2t" in r.headers.get("content-type", "")
    assert r.content[:1] == b"\x47"


def test_banned_clip_endpoint_serves_mpegts(proxy):
    r = proxy.get("/iptv/error-banned.ts")
    assert r.status_code == 200
    assert "video/mp2t" in r.headers.get("content-type", "")
    assert r.content[:1] == b"\x47"
