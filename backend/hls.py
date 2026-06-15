"""HLS-Playlist-Umschreibung (rein, ohne DB/Netzwerk).

Schreibt Segment-URLs einer .m3u8-Playlist so um, dass sie über den Proxy laufen.
Aus main.py ausgelagert; main.py importiert die Funktion wieder.
"""
import urllib.parse


def rewrite_hls_playlist(content: str, original_url: str, proxy_base: str, token: str,
                         sid: str = None, catchup: bool = False) -> str:
    # Base URL: directory of the playlist file
    # For DVR playlists like .../tracks-v1a1/index-xxx.m3u8
    # segments may be like dvr-2026/05/01/.../xx.ts (relative to tracks-v1a1/)
    base = original_url.rsplit("/", 1)[0] + "/"
    lines = content.splitlines()
    out = []
    _oul = original_url.lower()
    # Treat archive catchup master (/index.m3u8) like DVR for ENDLIST handling so logs and client both see ENDLIST.
    is_dvr = "dvr" in original_url or "index-" in original_url or "/index.m3u8" in _oul
    for line in lines:
        stripped = line.strip()
        # Strip ENDLIST for plain live/VOD masters so players keep polling; keep ENDLIST for DVR/archive playlists.
        if stripped == "#EXT-X-ENDLIST" and not is_dvr:
            continue
        if stripped.startswith("#"):
            out.append(line)
            continue
        if not stripped:
            out.append(line)
            continue
        # Resolve relative URLs against the playlist base directory
        if stripped.startswith("http"):
            abs_url = stripped
        elif stripped.startswith("//"):
            scheme = "https" if original_url.startswith("https") else "http"
            abs_url = scheme + ":" + stripped
        else:
            abs_url = base + stripped
        encoded = urllib.parse.quote(abs_url, safe="")
        if catchup:
            out.append(f"{proxy_base}/iptv/{token}/segment?catchup=1&url={encoded}")
        elif sid:
            out.append(f"{proxy_base}/iptv/{token}/segment?sid={sid}&url={encoded}")
        else:
            out.append(f"{proxy_base}/iptv/{token}/segment?url={encoded}")
    return "\n".join(out)
