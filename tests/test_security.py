"""Sicherheits-Tests auf Endpoint-Ebene (FastAPI TestClient, kein Netzwerk).

Deckt SSRF-Schutz, Admin-Authentifizierung, Token-Hashing/-Migration und
Security-Header ab.
"""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    main.db.db_path = str(tmp_path / "sec.db")
    main.db.init()
    main._startup_done = True          # schwere Startup-Hintergrundtasks überspringen
    main._failed_attempts.clear()      # globalen Brute-Force-Zähler isolieren
    return TestClient(main.proxy_app), TestClient(main.admin_app)


def _make_active_user(token="usertok"):
    return main.db.create_user(name="T", token=token, m3u_source="http://prov/list")


# ── SSRF ─────────────────────────────────────────────────────────────────────
def test_ssrf_blocks_loopback(clients):
    proxy, _ = clients
    _make_active_user("utok")
    r = proxy.get("/iptv/utok/stream", params={"url": "http://127.0.0.1/admin"})
    assert r.status_code == 403


def test_ssrf_blocks_link_local_metadata(clients):
    proxy, _ = clients
    _make_active_user("utok")
    r = proxy.get("/iptv/utok/stream",
                  params={"url": "http://169.254.169.254/latest/meta-data/"})
    assert r.status_code == 403


def test_ssrf_blocks_private_range(clients):
    proxy, _ = clients
    _make_active_user("utok")
    r = proxy.get("/iptv/utok/stream", params={"url": "http://192.168.1.1/"})
    assert r.status_code == 403


def test_ssrf_rejects_non_http_scheme(clients):
    proxy, _ = clients
    _make_active_user("utok")
    r = proxy.get("/iptv/utok/stream", params={"url": "file:///etc/passwd"})
    assert r.status_code == 400


# ── Admin-Auth ────────────────────────────────────────────────────────────────
def test_admin_endpoint_requires_token_header(clients):
    _, admin = clients
    assert admin.get("/api/users").status_code == 422  # Header fehlt -> Validierung


def test_admin_endpoint_rejects_wrong_token(clients):
    _, admin = clients
    main.db.set_setting("admin_token", main._hash_admin_token("right"))
    assert admin.get("/api/users",
                     headers={"x-admin-token": "wrong"}).status_code == 401


# ── Token-Hashing & Migration ────────────────────────────────────────────────
def test_setup_stores_hashed_token(clients):
    _, admin = clients
    r = admin.post("/api/setup",
                   json={"admin_token": "supersecret", "base_url": "http://x"})
    assert r.status_code == 200
    stored = main.db.get_setting("admin_token")
    assert stored.startswith("pbkdf2_sha256$")
    assert "supersecret" not in stored
    assert admin.get("/api/users",
                     headers={"x-admin-token": "supersecret"}).status_code == 200


def test_legacy_plaintext_token_verifies_and_migrates(clients):
    _, admin = clients
    main.db.set_setting("admin_token", "oldplaintext")  # Altbestand simulieren
    ok = admin.get("/api/users", headers={"x-admin-token": "oldplaintext"})
    assert ok.status_code == 200
    # nach erfolgreichem Login automatisch zu Hash migriert
    assert main.db.get_setting("admin_token").startswith("pbkdf2_sha256$")


# ── Security-Header ───────────────────────────────────────────────────────────
def test_security_headers_present(clients):
    proxy, _ = clients
    r = proxy.get("/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
