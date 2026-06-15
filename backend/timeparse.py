"""Reine Zeit-/EPG-Parser ohne DB- oder Netzwerk-Abhängigkeit.

Aus main.py ausgelagert, um die Datei zu entlasten. main.py importiert diese
Funktionen wieder, sodass alle bestehenden Aufrufstellen unverändert bleiben.
"""
import re
from datetime import datetime, timezone

# Pfad-Muster für DVR-/Catchup-Segmente: /YYYY/MM/DD/HH/MM/
_DVR_PATH_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/(\d{2})/(\d{2})")


def _sanitize_diagnostic_timezone(val) -> str:
    """IANA zone for UI, or 'browser' for client-local formatting."""
    v = str(val or "").strip()
    if not v or v.lower() == "browser":
        return "browser"
    if len(v) > 80:
        v = v[:80]
    if not re.match(r"^[A-Za-z0-9_/+\-]+$", v):
        return "Europe/Berlin"
    return v


def _parse_xmltv_datetime(value: str):
    """Parse XMLTV programme start/stop. Supports 'YYYYMMDDHHMMSS +ZZZZ' and 'YYYYMMDDHHMMSSZZZZ'."""
    if not value or not str(value).strip():
        return None
    s = str(value).strip()
    for fmt in ("%Y%m%d%H%M%S %z", "%Y%m%d%H%M%S%z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_catchup_wall_time(value: str):
    """Parse catchup_time from DB: 'YYYY-MM-DD HH:MM:SS' (preferred) or legacy 'YYYY-MM-DD HH:MM' (UTC)."""
    if not value or not str(value).strip():
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _epg_programme_contains_instant(ps: datetime, pe: datetime, ct: datetime) -> bool:
    """True if instant ct falls in the programme window (inclusive both ends — matches v1.0 / many provider EPGs)."""
    if ps is None or pe is None or ct is None:
        return False
    return ps <= ct <= pe


def _epg_programme_contains_instant_half_open(ps: datetime, pe: datetime, ct: datetime) -> bool:
    """XMLTV-style window [start, stop): avoids double-match when programmes share a boundary."""
    if ps is None or pe is None or ct is None:
        return False
    return ps <= ct < pe


def _dvr_wall_time_from_url(decoded_url: str):
    m = _DVR_PATH_RE.search(decoded_url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:00"
    # Xtream-style: ...dvr-2026/05/01/12/05/...
    m2 = re.search(r"dvr-(\d{4})/(\d{2})/(\d{2})/(\d{2})/(\d{2})", decoded_url, re.I)
    if m2:
        return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)} {m2.group(4)}:{m2.group(5)}:00"
    return None
