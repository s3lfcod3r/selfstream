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

    name_match = re.search(r',([^,]+)$', extinf)
    name = name_match.group(1).strip() if name_match else "Unknown"
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

        # Build catchup attributes if tvg_rec > 0
        catchup_attrs = ""
        if tvg_rec and tvg_rec != "0":
            catchup_source = f"{proxy_base}/iptv/{user_token}/catchup/{tvg_id}?utc={{utc}}&lutc={{lutc}}"
            catchup_attrs = f' catchup="shift" catchup-days="{tvg_rec}" catchup-source="{catchup_source}"'

        extinf = (
            f'#EXTINF:-1 tvg-id="{tvg_id}" '
            f'tvg-logo="{ch.get("tvg_logo","")}" '
            f'group-title="{group}" tvg-rec="{tvg_rec}"{catchup_attrs},'
            f'{ch["name"]}'
        )
        lines.append(extinf)
        encoded = urllib.parse.quote(ch["stream_url"], safe="")
        lines.append(f"{proxy_base}/iptv/{user_token}/stream?url={encoded}")

    return "\n".join(lines)
