"""Entrypoint: runs proxy on 8000 and admin on 8080 in one process."""
import copy
import logging
import re
import uvicorn
import threading
from main import proxy_app, admin_app
from uvicorn.config import LOGGING_CONFIG


# ── Zugangsdaten aus dem Zugriffslog halten ───────────────────────────────────
# uvicorn loggt die Anfragezeile mit VOLLEM Pfad und Query. Bei selfstream steht dort
# beides drin, was nicht ins Log gehört:
#   /iptv/<nutzer-token>/segment?url=https%3A%2F%2F...%3Ftoken%3D<anbieter-token>
# Der Filter setzt an der Anfragezeile an (args[2] des uvicorn.access-Records) und
# maskiert Pfad-Token wie Query-Werte — auch URL-kodiert (%3D), denn genau so steht
# es im Zugriffslog.
_QUERY_CRED_RE = re.compile(
    r"(?i)(token|username|password|passwd|pwd|pw|api[_-]?key|auth|secret)"
    r"(=|:|%3D|%3d|%3a|%3A)([^&\s\"']+)"
)
_PATH_TOKEN_RE = re.compile(r"(/(?:iptv|s)/)[A-Za-z0-9_.\-]{6,}")


class _MaskCredsFilter(logging.Filter):
    """Maskiert Token in der uvicorn-Anfragezeile. Wirft nie — ein Fehler hier
    darf niemals eine Antwort oder einen Stream kosten."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            args = record.args
            if isinstance(args, tuple) and len(args) >= 3:
                pfad = _PATH_TOKEN_RE.sub(r"\1***", str(args[2]))
                pfad = _QUERY_CRED_RE.sub(r"\1\2***", pfad)
                record.args = args[:2] + (pfad,) + args[3:]
        except Exception:
            pass
        return True


# Der Filter muss über log_config gesetzt werden: uvicorn ruft beim Start
# dictConfig() auf und würde einen vorher direkt angehängten Filter wieder verwerfen.
# Schlüsselname gegen uvicorn 0.30.6 geprüft (LOGGING_CONFIG["loggers"]["uvicorn.access"]).
_LOG_CONFIG = copy.deepcopy(LOGGING_CONFIG)
_LOG_CONFIG["filters"] = {"mask_creds": {"()": _MaskCredsFilter}}
_LOG_CONFIG["loggers"]["uvicorn.access"]["filters"] = ["mask_creds"]


def run_proxy():
    uvicorn.run(proxy_app, host="0.0.0.0", port=8000, log_level="info",
                log_config=_LOG_CONFIG)

def run_admin():
    # Bind to 0.0.0.0 so admin panel stays reachable via local IP even when VPN is active
    uvicorn.run(admin_app, host="0.0.0.0", port=8080, log_level="info",
                log_config=_LOG_CONFIG)


if __name__ == "__main__":
    t1 = threading.Thread(target=run_proxy, daemon=True)
    t2 = threading.Thread(target=run_admin, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
