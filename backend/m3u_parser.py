"""M3U playlist parser - supports #EXTGRP and group-title attribute."""
import re
from typing import List, Dict


# Lines starting with these prefixes are metadata/options — skip, don't reset state
_SKIP_PREFIXES = (
    "#EXTVLCOPT", "#EXTOPT", "#EXTALB", "#EXTART", "#EXTGENRE",
    "#EXTBG", "#PLAYLIST", "#EXT-X-", "#KODIPROP",
)

# URL scheme prefixes we accept as stream URLs (http/https only — selfstream proxies HTTP)
_URL_PREFIXES = ("http://", "https://")


def _first_comma_outside_quotes(s: str) -> int:
    """Index des ersten Kommas außerhalb von Anführungszeichen, sonst -1."""
    in_quotes = False
    for i, ch in enumerate(s):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            return i
    return -1


def parse_m3u(content: str) -> List[Dict]:
    channels = []
    lines = content.splitlines()
    current_extinf = None
    current_group = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            continue
        elif any(line.startswith(p) for p in _SKIP_PREFIXES):
            # Metadata lines — keep current_extinf alive, just ignore this line
            continue
        elif line.startswith("#EXTGRP:"):
            current_group = line[8:].strip()
        elif line.startswith("#EXTINF"):
            current_extinf = line
        elif any(line.startswith(p) for p in _URL_PREFIXES):
            if current_extinf:
                ch = _parse_extinf(current_extinf, line, current_group)
                channels.append(ch)
            current_extinf = None
            current_group = ""
        # All other lines (unknown protocols etc.): skip silently

    return channels


def _parse_extinf(extinf: str, url: str, extgrp: str = "") -> Dict:
    def attr(key: str) -> str:
        m = re.search(rf'{key}="([^"]*)"', extinf, re.IGNORECASE)
        return m.group(1) if m else ""

    # Name: alles nach dem ersten Komma außerhalb von Anführungszeichen.
    # Kommas in Anführungszeichen (z. B. tvg-name="A, B") sind kein Trenner,
    # und ein Name mit Komma wird nicht mehr am Ende abgeschnitten.
    comma = _first_comma_outside_quotes(extinf)
    name = extinf[comma + 1:].strip() if comma != -1 else "Unknown"
    group = attr("group-title") or extgrp

    return {
        "name":      name,
        "url":       url,
        "group":     group,
        "tvg_id":    attr("tvg-id"),
        "tvg_logo":  attr("tvg-logo"),
        "tvg_name":  attr("tvg-name"),
        "tvg_rec":   attr("tvg-rec"),
        "raw_extinf": extinf,
    }


def _escape_attr_value(value: str) -> str:
    """Ersetzt Anführungszeichen in Attributwerten durch &quot;, damit
    sie die Attributliste nicht zerlegen."""
    return value.replace('"', "&quot;")


def build_m3u(channels: List[Dict], proxy_base: str, user_token: str,
              epg_urls: List[str] = None) -> str:
    import urllib.parse

    lines = []
    epg_attr = ""
    if epg_urls:
        epg_attr = f' url-tvg="{",".join(epg_urls)}"'
    lines.append(f"#EXTM3U{epg_attr}")

    for ch in channels:
        group = ch.get("group_title") or ch.get("group", "")
        tvg_rec = ch.get("tvg_rec") or ""
        tvg_id = ch.get("tvg_id", "")
        # Name bleibt, aber Zeilenumbrüche raus, sonst zerbricht die Zeile.
        # (Kein &quot; im Namen: der steht außerhalb der Attributliste.)
        name = (ch.get("name") or "").replace("\r", "").replace("\n", "")

        # Build catchup attributes if tvg_rec > 0
        catchup_attrs = ""
        if tvg_rec and tvg_rec != "0":
            catchup_source = (
                f"{proxy_base}/iptv/{user_token}/catchup/"
                f"{tvg_id}?utc={{utc}}&lutc={{lutc}}"
            )
            catchup_attrs = (
                f' catchup="shift" catchup-days="{_escape_attr_value(tvg_rec)}" '
                f'catchup-source="{_escape_attr_value(catchup_source)}"'
            )

        extinf = (
            f'#EXTINF:-1 tvg-id="{_escape_attr_value(tvg_id)}" '
            f'tvg-logo="{_escape_attr_value(ch.get("tvg_logo",""))}" '
            f'group-title="{_escape_attr_value(group)}" '
            f'tvg-rec="{_escape_attr_value(tvg_rec)}"'
            f'{catchup_attrs},'
            f'{name}'
        )
        lines.append(extinf)
        # Prefer the stable, server-independent id: /live/{uid} resolves the CURRENT
        # upstream URL from the DB at play time, so switching provider servers needs
        # no playlist reload on the device. Fall back to the legacy ?url= form for
        # channels without a stored uid (e.g., raw-parsed, no DB row).
        stable_uid = str(ch.get("stable_uid") or "").strip()
        if stable_uid:
            lines.append(f"{proxy_base}/iptv/{user_token}/live/{stable_uid}")
        else:
            encoded = urllib.parse.quote(ch["stream_url"], safe="")
            lines.append(f"{proxy_base}/iptv/{user_token}/stream?url={encoded}")

    return "\n".join(lines)
