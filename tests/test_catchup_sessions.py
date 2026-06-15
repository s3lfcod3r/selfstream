"""Charakterisierungs-Tests für die Catchup-/Session-Logik in main.py.

Diese Logik hängt an globalem Zustand (_sessions, _catchup_sessions) und ist
beim geplanten Modul-Umbau am stärksten gefährdet. Die Tests fixieren das
aktuelle Verhalten als Sicherheitsnetz.
"""
import time

import pytest

import main


@pytest.fixture(autouse=True)
def isolate_state(tmp_path):
    main.db.db_path = str(tmp_path / "catchup.db")
    main.db.init()
    main._sessions.clear()
    main._catchup_sessions.clear()
    main._last_cleanup = 0.0
    yield
    main._sessions.clear()
    main._catchup_sessions.clear()


# ── Session-Auflösung ─────────────────────────────────────────────────────────
def test_resolve_none_when_no_sessions():
    assert main._resolve_catchup_session_key("tok", "http://p/x") is None


def test_resolve_single_session_wins():
    main._catchup_sessions["catchup::tok::Chan"] = {"token": "tok", "start": 1.0, "last_seen": time.time()}
    assert main._resolve_catchup_session_key("tok", "http://p/x") == "catchup::tok::Chan"


def test_resolve_multiple_newest_start_wins():
    now = time.time()
    main._catchup_sessions["catchup::tok::A"] = {"token": "tok", "start": 1.0, "last_seen": now}
    main._catchup_sessions["catchup::tok::B"] = {"token": "tok", "start": 5.0, "last_seen": now}
    assert main._resolve_catchup_session_key("tok", "http://p/seg.ts") == "catchup::tok::B"


def test_resolve_ignores_other_token():
    main._catchup_sessions["catchup::other::A"] = {"token": "other", "start": 1.0, "last_seen": time.time()}
    assert main._resolve_catchup_session_key("tok", "http://p/x") is None


# ── Zustandsänderungen ────────────────────────────────────────────────────────
def test_touch_last_seen_updates():
    main._catchup_sessions["catchup::tok::A"] = {"token": "tok", "start": 1.0, "last_seen": 1.0}
    main._touch_catchup_last_seen("tok", "http://p/x")
    assert main._catchup_sessions["catchup::tok::A"]["last_seen"] > 1.0


def test_mark_endlist_sets_flag_once():
    main._catchup_sessions["catchup::tok::A"] = {"token": "tok", "start": 1.0, "last_seen": time.time()}
    main._catchup_mark_endlist("tok", "http://p/x")
    cv = main._catchup_sessions["catchup::tok::A"]
    assert cv["saw_endlist"] is True
    assert cv["endlist_seen_at"] > 0


# ── Stream-Zählung ────────────────────────────────────────────────────────────
def test_user_stream_count_per_user():
    now = time.time()
    main._last_cleanup = now  # Cleanup-Body via Throttle überspringen
    main._sessions["s1"] = {"user_id": 1, "last_seen": now}
    main._sessions["s2"] = {"user_id": 1, "last_seen": now}
    main._sessions["s3"] = {"user_id": 2, "last_seen": now}
    assert main._user_stream_count(1) == 2
    assert main._user_stream_count(2) == 1


def test_user_has_session():
    main._sessions["abc"] = {"user_id": 1, "last_seen": time.time()}
    assert main._user_has_session(1, "abc") is True
    assert main._user_has_session(1, "nope") is False


def test_cleanup_removes_stale_live_session():
    now = time.time()
    main._last_cleanup = 0.0
    main._sessions["old"] = {
        "user_id": 1, "last_seen": now - 100, "token": "tok",
        "channel": "C", "log_id": 1, "start": now - 200, "log_start": now - 200,
    }
    main._cleanup_sessions()
    assert "old" not in main._sessions


# ── TTL-Logik ─────────────────────────────────────────────────────────────────
def test_catchup_idle_ttl_normal_vs_endlist():
    main.db.set_setting("catchup_ttl", "900")
    main.db.set_setting("catchup_ttl_after_endlist", "120")
    assert main._catchup_idle_ttl_seconds({}) == 900
    assert main._catchup_idle_ttl_seconds({"saw_endlist": True}) == 900  # max(900,120)
    main.db.set_setting("catchup_ttl", "60")
    assert main._catchup_idle_ttl_seconds({"saw_endlist": True}) == 120  # max(60,120)


def test_get_catchup_ttl_has_floor():
    main.db.set_setting("catchup_ttl", "1")
    assert main.get_catchup_ttl() == 5


def test_is_catchup_strict_mode_default_and_off():
    assert main.is_catchup_strict_mode() is True  # Default "1"
    main.db.set_setting("catchup_strict_mode", "0")
    assert main.is_catchup_strict_mode() is False
