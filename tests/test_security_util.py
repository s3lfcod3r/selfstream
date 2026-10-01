"""Tests für security_util.py (SSRF-Schutz).

Benötigt fastapi (HTTPException). Läuft in der CI (Deps aus requirements.txt).
"""
import pytest
from fastapi import HTTPException
import security_util


def test_block_localhost():
    with pytest.raises(HTTPException) as exc:
        security_util.assert_safe_upstream_url("http://localhost:8000/admin")
    assert exc.value.status_code == 403


def test_block_loopback_ip():
    with pytest.raises(HTTPException) as exc:
        security_util.assert_safe_upstream_url("http://127.0.0.1:8000")
    assert exc.value.status_code == 403


def test_block_loopback_ipv6():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("http://[::1]:8000")


def test_block_private_192_168():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("http://192.168.1.100:8080")


def test_block_private_10():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("http://10.0.0.1")


def test_block_private_172_16():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("http://172.16.254.1")


def test_block_link_local():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("http://169.254.1.1")


def test_allow_public_ip_google():
    # 8.8.8.8 ist eine echte öffentliche IP (nicht private/reserved).
    security_util.assert_safe_upstream_url("https://8.8.8.8:443")


def test_allow_public_ip_cloudflare():
    security_util.assert_safe_upstream_url("https://1.1.1.1")


def test_allow_public_domain_via_hostname():
    # Ein echter öffentlicher Domäne-Name (außerhalb privater/reservierter Bereiche).
    # Wird per DNS aufgelöst; in der CI mit Netzwerk funktioniert das.
    security_util.assert_safe_upstream_url("https://example.com")


def test_block_invalid_scheme():
    with pytest.raises(HTTPException) as exc:
        security_util.assert_safe_upstream_url("ftp://example.com/file")
    assert exc.value.status_code == 400


def test_block_malformed_url():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("not a valid url at all")


def test_block_empty_host():
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("http://")


def test_block_unresolvable_hostname():
    # Nicht auflösbarer Hostname wird sicherheitshalber blockiert.
    with pytest.raises(HTTPException):
        security_util.assert_safe_upstream_url("https://definitely-not-a-real-host-xyz123.localtest")
