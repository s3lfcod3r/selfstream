"""M3U playlist parser."""
import re
from typing import List, Dict


def parse_m3u(content: str) -> List[Dict]:
    """Parse M3U/M3U8 content into channel list."""
    channels = []
    lines = content.splitlines()
    current_extinf = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line
        elif line.startswith("http") or line.startswith("rtmp"):
            if current_extinf:
                ch = _parse_extinf(current_extinf, line)
                channels.append(ch)
            current_extinf = None

    return channels


def _parse_extinf(extinf: str, url: str) -> Dict:
    """Parse a single #EXTINF line + URL into channel dict."""
    def attr(key: str) -> str:
        m = re.search(rf'{key}="([^"]*)"', extinf)
        return m.group(1) if m else ""

    # Channel name: everything after the last comma
    name_match = re.search(r',(.+)$', extinf)
    name = name_match.group(1).strip() if name_match else "Unknown"

    return {
        "name": name,
        "url": url,
        "group": attr("group-title"),
        "tvg_id": attr("tvg-id"),
        "tvg_logo": attr("tvg-logo"),
        "tvg_name": attr("tvg-name"),
        "raw_extinf": extinf,
    }


def build_m3u(channels: List[Dict], proxy_base: str, user_token: str,
              epg_urls: List[str] = None) -> str:
    """Build a proxied M3U playlist from channel list."""
    import urllib.parse

    lines = []

    # Header with EPG
    epg_attr = ""
    if epg_urls:
        combined = ",".join(epg_urls)
        epg_attr = f' url-tvg="{combined}"'

    lines.append(f"#EXTM3U{epg_attr}")

    for ch in channels:
        # Reconstruct EXTINF with original attributes
        extinf = ch.get("raw_extinf", "")
        if not extinf:
            extinf = (
                f'#EXTINF:-1 tvg-id="{ch.get("tvg_id","")}" '
                f'tvg-logo="{ch.get("tvg_logo","")}" '
                f'group-title="{ch.get("group_title", ch.get("group",""))}",'
                f'{ch["name"]}'
            )
        lines.append(extinf)

        # Proxied stream URL
        encoded = urllib.parse.quote(ch["stream_url"], safe="")
        lines.append(f"{proxy_base}/iptv/{user_token}/stream?url={encoded}")

    return "\n".join(lines)
