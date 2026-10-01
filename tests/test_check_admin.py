"""Tests für check_admin (Brute-Force-Schutz, main.py).

Benötigt main.py (fastapi, httpx, uvicorn). Läuft in der CI (Deps aus
requirements.txt). Die DB wird per Mock ersetzt.
"""
import main
from main import check_admin
from fastapi import HTTPException
from unittest.mock import patch


class _MockClient:
    def __init__(self, ip):
        self.host = ip


class _MockRequest:
    def __init__(self, ip):
        self.client = _MockClient(ip)


def _req(ip):
    return _MockRequest(ip)


def _mock_db(valid_token):
    mock_db = patch.object(main, "db")
    mock = mock_db.start()
    mock.get_admin_token.return_value = valid_token
    mock.get_setting.return_value = "0"   # diagnostics off
    mock.set_setting.return_value = None
    mock.add_diagnostic_log.return_value = None
    return mock


def test_check_admin_brute_force():
    # Wrong tokens get counted per IP; after MAX_ATTEMPTS the IP is blocked (429).
    valid_token = "valid_admin_token_123"
    mock_db = _mock_db(valid_token)
    try:
        main._failed_attempts.clear()
        main._admin_token_cache.clear()
        ip = "1.2.3.4"
        status_codes = []
        for _ in range(main.MAX_ATTEMPTS + 2):
            try:
                check_admin(x_admin_token="wrong_token_xyz", request=_req(ip))
                status_codes.append(200)
            except HTTPException as e:
                status_codes.append(e.status_code)
        # First MAX_ATTEMPTS calls: 401
        assert status_codes[:main.MAX_ATTEMPTS] == [401] * main.MAX_ATTEMPTS
        # Subsequent calls: 429 (blocked)
        assert status_codes[main.MAX_ATTEMPTS] == 429
        assert status_codes[main.MAX_ATTEMPTS + 1] == 429
    finally:
        mock_db.stop()


def test_check_admin_correct_token():
    # Correct token passes (no raise) and resets the counter.
    valid_token = "valid_admin_token_123"
    mock_db = _mock_db(valid_token)
    try:
        main._failed_attempts.clear()
        # Should not raise
        check_admin(x_admin_token=valid_token, request=_req("1.2.3.4"))
        # Counter for this IP should be reset/absent
        assert "1.2.3.4" not in main._failed_attempts
    finally:
        mock_db.stop()


def test_check_admin_per_ip_counter():
    # Different IPs have independent counters.
    valid_token = "valid_admin_token_123"
    mock_db = _mock_db(valid_token)
    try:
        main._failed_attempts.clear()
        main._admin_token_cache.clear()
        # Fill IP A's counter to blocked state
        for _ in range(main.MAX_ATTEMPTS + 1):
            try:
                check_admin(x_admin_token="wrong", request=_req("9.9.9.9"))
            except HTTPException as e:
                assert e.status_code in (401, 429)
        assert "9.9.9.9" in main._failed_attempts
        # IP B is independent: correct token still passes
        check_admin(x_admin_token=valid_token, request=_req("8.8.8.8"))
        assert "8.8.8.8" not in main._failed_attempts
    finally:
        mock_db.stop()
