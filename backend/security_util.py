"""Sicherheits-Helfer: SSRF-Schutz und Admin-Token-Hashing.

Rein (nur stdlib + FastAPI-Exception). Aus main.py ausgelagert; main.py importiert
die Symbole wieder, sodass alle bestehenden Aufrufstellen unverändert bleiben.
"""
import os
import hmac
import hashlib
import socket
import ipaddress
import urllib.parse

from fastapi import HTTPException


# ── SSRF-Schutz ────────────────────────────────────────────────────────────────
def _host_is_internal(host: str) -> bool:
    host = (host or "").strip().strip("[]")
    if not host or host.lower() == "localhost":
        return True
    candidate_ips = []
    try:
        candidate_ips = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
            candidate_ips = [ipaddress.ip_address(info[4][0]) for info in infos]
        except Exception:
            return True  # nicht auflösbar -> sicherheitshalber blocken
    for ip in candidate_ips:
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return True
    return False


def assert_safe_upstream_url(url: str) -> None:
    """Wirft HTTPException, wenn die Ziel-URL kein erlaubtes Schema hat oder
    auf eine interne/private Adresse zeigt."""
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Unsupported URL scheme")
    if _host_is_internal(parsed.hostname or ""):
        raise HTTPException(status_code=403, detail="Blocked internal target")


# ── Admin-Token-Hashing ─────────────────────────────────────────────────────────
# Token werden gehasht (PBKDF2-HMAC-SHA256) statt im Klartext in der DB gespeichert.
# Alt-Bestände im Klartext werden beim ersten erfolgreichen Login automatisch migriert.
_PBKDF2_ITERATIONS = 200_000


def _hash_admin_token(token: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", token.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_admin_token(candidate: str, stored: str) -> bool:
    """Vergleicht zeitkonstant. Unterstützt gehashte UND alte Klartext-Werte."""
    if not stored or not candidate:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt_hex, dk_hex = stored.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"),
                                     bytes.fromhex(salt_hex), int(iters))
            return hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False
    # Legacy: Klartext (z.B. aus ADMIN_TOKEN-Env oder altem Setup)
    return hmac.compare_digest(candidate, stored)
