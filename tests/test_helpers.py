"""Charakterisierungs-Tests für reine Hilfsfunktionen in main.py.

Diese Funktionen haben keine DB-/Netzwerk-Abhängigkeit. Die Tests fixieren ihr
Verhalten, damit der Umbau von main.py (Aufteilung in Module) nichts verändert.
"""
import urllib.parse
from datetime import datetime, timezone

import main


def test_parse_xmltv_datetime_with_space_offset():
    dt = main._parse_xmltv_datetime("20260501120000 +0200")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 1 and dt.hour == 12


def test_parse_xmltv_datetime_without_space_offset():
    dt = main._parse_xmltv_datetime("20260501120000+0200")
    assert dt is not None and dt.hour == 12


def test_parse_xmltv_datetime_invalid_returns_none():
    assert main._parse_xmltv_datetime("") is None
    assert main._parse_xmltv_datetime("garbage") is None


def test_parse_catchup_wall_time_full_and_legacy():
    full = main._parse_catchup_wall_time("2026-05-01 12:30:00")
    legacy = main._parse_catchup_wall_time("2026-05-01 12:30")
    assert full is not None and full.tzinfo == timezone.utc and full.minute == 30
    assert legacy is not None and legacy.tzinfo == timezone.utc
    assert main._parse_catchup_wall_time("") is None


def test_epg_window_inclusive_vs_half_open():
    ps = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    pe = datetime(2026, 5, 1, 13, 0, tzinfo=timezone.utc)
    boundary = pe  # exakt auf der Stop-Grenze
    assert main._epg_programme_contains_instant(ps, pe, boundary) is True
    assert main._epg_programme_contains_instant_half_open(ps, pe, boundary) is False
    mid = datetime(2026, 5, 1, 12, 30, tzinfo=timezone.utc)
    assert main._epg_programme_contains_instant(ps, pe, mid) is True
    assert main._epg_programme_contains_instant_half_open(ps, pe, mid) is True


def test_dvr_wall_time_from_url_variants():
    assert main._dvr_wall_time_from_url(
        "http://x/2026/05/01/12/30/seg.ts") == "2026-05-01 12:30:00"
    assert main._dvr_wall_time_from_url(
        "http://x/dvr-2026/05/01/12/05/seg.ts") == "2026-05-01 12:05:00"
    assert main._dvr_wall_time_from_url("http://x/live/seg.ts") is None


def test_sanitize_diagnostic_timezone():
    assert main._sanitize_diagnostic_timezone("") == "browser"
    assert main._sanitize_diagnostic_timezone("browser") == "browser"
    assert main._sanitize_diagnostic_timezone("Europe/Berlin") == "Europe/Berlin"
    # ungültige Zeichen -> Fallback
    assert main._sanitize_diagnostic_timezone("bad; rm -rf") == "Europe/Berlin"


def test_rewrite_hls_strips_endlist_for_live():
    content = "#EXTM3U\n#EXT-X-ENDLIST\nseg1.ts"
    out = main.rewrite_hls_playlist(content, "http://prov/live/stream.m3u8",
                                    "http://proxy", "TKN")
    assert "#EXT-X-ENDLIST" not in out
    enc = urllib.parse.quote("http://prov/live/seg1.ts", safe="")
    assert f"http://proxy/iptv/TKN/segment?url={enc}" in out


def test_rewrite_hls_keeps_endlist_for_dvr():
    content = "#EXTM3U\n#EXT-X-ENDLIST\nseg1.ts"
    out = main.rewrite_hls_playlist(content, "http://prov/tracks/index-1.m3u8",
                                    "http://proxy", "TKN")
    assert "#EXT-X-ENDLIST" in out


def test_rewrite_hls_catchup_and_sid_flags():
    content = "#EXTM3U\nseg.ts"
    out_c = main.rewrite_hls_playlist(content, "http://p/live/s.m3u8",
                                      "http://proxy", "TKN", catchup=True)
    assert "/segment?catchup=1&url=" in out_c
    out_s = main.rewrite_hls_playlist(content, "http://p/live/s.m3u8",
                                      "http://proxy", "TKN", sid="abc")
    assert "/segment?sid=abc&url=" in out_s
