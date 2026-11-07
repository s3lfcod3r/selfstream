"""HLS-Playlist-Umschreibung (rein, ohne DB/Netzwerk).

Schreibt Segment-URLs einer .m3u8-Playlist so um, dass sie über den Proxy laufen.
Aus main.py ausgelagert; main.py importiert die Funktion wieder.
"""
import urllib.parse


def _absolute_url(stripped: str, base: str, original_url: str) -> str:
    """Resolve a playlist line against the playlist base directory."""
    if stripped.startswith("http"):
        return stripped
    if stripped.startswith("//"):
        scheme = "https" if original_url.startswith("https") else "http"
        return scheme + ":" + stripped
    return base + stripped


def segment_durations(content: str, original_url: str) -> dict:
    """{absolute Segment-URL: Spielzeit in s} aus den #EXTINF-Zeilen einer Playlist.

    Dient der fairen Qualitätsbewertung: Ob ein Segment „zu langsam“ lädt, hängt
    von seiner Länge ab (siehe alerting.passiv_bewerten). Unterplaylists ohne
    #EXTINF liefern einfach nichts.
    """
    base = original_url.rsplit("/", 1)[0] + "/"
    out = {}
    dauer = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#EXTINF:"):
            try:
                dauer = float(stripped[8:].split(",", 1)[0])
            except ValueError:
                dauer = None
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if dauer and dauer > 0:
            out[_absolute_url(stripped, base, original_url)] = dauer
        dauer = None
    return out


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
        abs_url = _absolute_url(stripped, base, original_url)
        encoded = urllib.parse.quote(abs_url, safe="")
        if catchup:
            out.append(f"{proxy_base}/iptv/{token}/segment?catchup=1&url={encoded}")
        elif sid:
            out.append(f"{proxy_base}/iptv/{token}/segment?sid={sid}&url={encoded}")
        else:
            out.append(f"{proxy_base}/iptv/{token}/segment?url={encoded}")
    return "\n".join(out)
