"""Vorladen von Segmenten (rein, ohne DB/Netzwerk).

Beim Umschalten beginnt ein Player nicht am Ende der Live-Playlist, sondern drei
Zieldauern (#EXT-X-TARGETDURATION) davor – so sieht es die HLS-Vorgabe vor, und so
halten es die üblichen Player. Dieses Segment und das folgende holt SelfStream schon,
während der Player die Playlist noch auswertet. Im laufenden Betrieb wird jeweils das
Segment geholt, das der Player als Nächstes anfragt. Welche Segmente das sind,
entscheidet dieses Modul; geladen wird in main.py.
"""
from hls import _absolute_url

ZAP_VORLADEN = 2       # so viele Segmente ab dem Startpunkt des Players beim Umschalten
START_ZIELDAUERN = 3   # Abstand des Startpunkts zum Ende der Playlist, in Zieldauern
OHNE_ZIELDAUER = 3     # Rückfall ohne Zeitangaben: so viele Segmente vor dem Ende beginnen
FOLGE_MAX = 3000       # gemerkte Nachfolger (Einfügereihenfolge = Alter)


def _lesen(content: str, playlist_url: str) -> tuple:
    """(Zieldauer oder None, [(absolute Adresse, Spielzeit oder None), …]) einer Playlist.

    Unterplaylists (.m3u8) zählen nicht als Segment: Die holt der Player selbst.
    """
    base = playlist_url.rsplit("/", 1)[0] + "/"
    ziel = None
    dauer = None
    segmente = []
    for line in (content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#EXT-X-TARGETDURATION:"):
            try:
                ziel = float(stripped.split(":", 1)[1])
            except ValueError:
                ziel = None
            continue
        if stripped.startswith("#EXTINF:"):
            try:
                dauer = float(stripped[8:].split(",", 1)[0])
            except ValueError:
                dauer = None
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if "m3u8" not in stripped.split("?", 1)[0].lower():
            segmente.append((_absolute_url(stripped, base, playlist_url), dauer))
        dauer = None
    return ziel, segmente


def segment_urls(content: str, playlist_url: str) -> list:
    """Absolute Adressen der Mediensegmente einer Playlist, in Abspielreihenfolge."""
    return [url for url, _ in _lesen(content, playlist_url)[1]]


def start_index(ziel, dauern: list) -> int:
    """Stelle des Segments, mit dem ein Player nach dem Umschalten beginnt."""
    if not dauern:
        return 0
    if not ziel or ziel <= 0 or any(not d or d <= 0 for d in dauern):
        return max(0, len(dauern) - OHNE_ZIELDAUER)
    start = sum(dauern) - START_ZIELDAUERN * ziel
    ende = 0.0
    for i, d in enumerate(dauern):
        ende += d
        if ende > start:
            return i
    return len(dauern) - 1


def zap_auswahl(content: str, playlist_url: str, anzahl: int = ZAP_VORLADEN) -> list:
    """Die Segmente, die der Player nach dem Umschalten zuerst anfragt."""
    if anzahl <= 0:
        return []
    ziel, segmente = _lesen(content, playlist_url)
    i = start_index(ziel, [d for _, d in segmente])
    return [url for url, _ in segmente[i:i + anzahl]]


def folge_merken(folge: dict, urls: list, grenze: int = FOLGE_MAX) -> None:
    """Zu jedem Segment den Nachfolger festhalten (ändert ``folge``)."""
    for vor, nach in zip(urls, urls[1:]):
        folge[vor] = nach
    while len(folge) > grenze:
        folge.pop(next(iter(folge)))


def naechste(folge: dict, url: str, anzahl: int) -> list:
    """Die bis zu ``anzahl`` Segmente, die auf ``url`` folgen."""
    out = []
    aktuell = url
    while len(out) < anzahl:
        aktuell = folge.get(aktuell)
        if aktuell is None or aktuell == url or aktuell in out:
            break
        out.append(aktuell)
    return out
