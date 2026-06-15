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
    main._block_anchors.clear()
    main._resume_offsets.clear()
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
    # Endlos-Live-Loop statt VOD: KEIN ENDLIST (sonst zappt der Player nach dem
    # Clip automatisch weiter), dafür gleitende Media-Sequence + Discontinuity.
    assert "#EXT-X-ENDLIST" not in r.text
    assert "#EXT-X-MEDIA-SEQUENCE" in r.text
    assert "#EXT-X-DISCONTINUITY" in r.text


def test_max_streams_playlist_uses_low_media_sequence(proxy):
    # Die Block-Loop muss eine NIEDRIGE Media-Sequence nutzen (pro Episode bei 0
    # startend), nicht die an die Unix-Zeit gekoppelte Riesenzahl (~2e8). Sonst
    # übernimmt der Player den echten Stream nach dem Entsperren nicht, weil dessen
    # kleinere Sequence wie ein Rücksprung aussieht und verworfen wird.
    user = main.db.create_user(name="LowSeq", token="lowseqtok", m3u_source="http://prov")
    main.db.update_user(user["id"], {"max_streams": 1})
    now = time.time()
    main._sessions["other-dev"] = {
        "user_id": user["id"], "session_key": "other-key", "last_seen": now,
    }

    r = proxy.get("/iptv/lowseqtok/stream", params={"url": "http://8.8.8.8/live.m3u8"})

    seq_line = next(l for l in r.text.splitlines() if l.startswith("#EXT-X-MEDIA-SEQUENCE:"))
    seq = int(seq_line.split(":", 1)[1])
    assert seq < 100


def test_splice_resume_continues_sequence_after_block(proxy):
    # Nach dem Entsperren muss der echte Stream als Fortsetzung der Loop ausgeliefert
    # werden: Media-Sequence = letzte Loop-Sequence + GAP (kein Rücksprung) und beim
    # ersten Mal eine Discontinuity (PTS-Reset Clip→echter Stream).
    key = "tok::sid::abc"
    now = time.time()
    main._block_anchors[key] = {"t0": now - 24, "seen": now}  # last_loop_seq = 24/8 = 3
    real = ("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:5\n"
            "#EXTINF:6.0,\nseg0.ts\n#EXTINF:6.0,\nseg1.ts\n")

    out = main._splice_resume(real, key)

    assert main._parse_media_seq(out) == 3 + main.RESUME_SEQ_GAP
    assert "#EXT-X-DISCONTINUITY" in out
    assert key not in main._block_anchors          # Anker verbraucht
    assert key in main._resume_offsets             # Offset bleibt für Folge-Reloads

    # Zweiter Reload: Offset weiter angewandt, aber KEINE neue Discontinuity.
    out2 = main._splice_resume("#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:6\n#EXTINF:6.0,\nseg2.ts\n", key)
    assert main._parse_media_seq(out2) == 6 + (3 + main.RESUME_SEQ_GAP - 5)
    assert "#EXT-X-DISCONTINUITY" not in out2


def test_splice_resume_noop_for_unblocked_session(proxy):
    # Eine Session, die nie geblockt war, bleibt unverändert (normaler Live-Pfad).
    key = "tok::sid::xyz"
    real = "#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:5\n#EXTINF:6.0,\nseg.ts\n"
    assert main._splice_resume(real, key) == real


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
