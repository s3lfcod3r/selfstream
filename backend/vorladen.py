"""Vorladen von Segmenten (rein, ohne DB/Netzwerk).

Beim Umschalten beginnt ein Player wenige Segmente vor dem Ende der Live-Playlist.
Diese Segmente holt SelfStream schon, während der Player die Playlist noch auswertet.
Im laufenden Betrieb wird jeweils das Segment geholt, das der Player als Nächstes
anfragt. Welche Segmente das sind, entscheidet dieses Modul; geladen wird in main.py.
"""
from hls import _absolute_url

ZAP_VORLADEN = 3       # so viele Segmente vom Ende der Playlist beim Umschalten
FOLGE_MAX = 3000       # gemerkte Nachfolger (Einfügereihenfolge = Alter)


def segment_urls(content: str, playlist_url: str) -> list:
    """Absolute Adressen der Mediensegmente einer Playlist, in Abspielreihenfolge.

    Unterplaylists (.m3u8) zählen nicht: Die holt der Player selbst.
    """
    base = playlist_url.rsplit("/", 1)[0] + "/"
    out = []
    for line in (content or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "m3u8" in stripped.split("?", 1)[0].lower():
            continue
        out.append(_absolute_url(stripped, base, playlist_url))
    return out


def zap_auswahl(urls: list, anzahl: int = ZAP_VORLADEN) -> list:
    """Die letzten ``anzahl`` Segmente, älteste zuerst (so fragt der Player sie an)."""
    if anzahl <= 0:
        return []
    return list(urls[-anzahl:])


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
