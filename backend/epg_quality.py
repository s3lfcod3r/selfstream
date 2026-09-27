"""EPG-Qualitätsprüfung: erkennt vermischte Programmlisten in XMLTV-Quellen.

Hintergrund: Manche EPG-Anbieter führen zwei komplette Programmlisten (z.B. die
Kabel- und die Sat-Variante desselben Senders) unter EINER Kanal-ID zusammen.
Die Sendungen überlappen sich dann zeitlich, obwohl auf einem Kanal immer nur
eine Sendung gleichzeitig laufen kann. Im Player führt das dazu, dass ein
angeklickter Catchup-Eintrag eine völlig andere Sendung abspielt.

Erkennung per Interval Partitioning: jede Sendung kommt auf die erste "Spur",
deren letzte Sendung bereits beendet ist. Bleibt es bei einer Spur, ist der
Sender sauber. Werden mehrere Spuren gebraucht, sind Programmlisten vermischt.

Das Modul liest die Datei streamend (iterparse + clear) und baut bewusst KEINEN
ElementTree im Speicher auf — eine 600-MB-XMLTV-Datei würde als Objektbaum
mehrere Gigabyte belegen.

Ehrlich zum Speicher (bis v1.82 stand hier zu wenig): die Sendezeiten MUSS das
Modul sammeln, sonst lassen sich die Spuren nicht bilden. Der Verbrauch wächst
also mit der Zahl der Sendungen im gewählten Zeitraum. Zwei Bremsen dagegen:

* Titel werden im ersten Durchlauf NICHT mitgenommen (sie waren der größte
  Posten). Erst für die wenigen auffälligen Sender der Detailansicht liest ein
  zweiter, gefilterter Durchlauf die Titel nach.
* MAX_PROGRAMMES begrenzt die Gesamtzahl gesammelter Sendungen hart; wird die
  Grenze erreicht, steht "truncated": true im Ergebnis.

Mit `day="YYYY-MM-DD"` bleibt der Verbrauch in jedem Fall klein — das ist der
empfohlene Weg bei sehr großen Quellen.
"""
from __future__ import annotations

import datetime
import xml.etree.ElementTree as ET

# Titel werden nur für die Detailansicht gebraucht — gekürzt halten spart Speicher.
_TITLE_MAX = 80

# Obergrenze der gesammelten Sendungen (Start/Stop-Paare). 400.000 Paare sind
# großzügig für jede realistische Tagesabfrage und liegen im zweistelligen
# MB-Bereich; die Vollquelle aus v1.81 (1,27 Mio. Sendungen) läuft dagegen in
# die Grenze und wird sauber als abgeschnitten gemeldet statt den Prozess zu
# füllen — auf dem Board teilt sich die Prüfung den Speicher mit den Streams.
MAX_PROGRAMMES = 400_000


def _fmt(ts: str, offset_h: int) -> str:
    """XMLTV-Zeitstempel (YYYYMMDDHHMMSS) -> HH:MM in der Anzeigezeitzone."""
    try:
        dt = datetime.datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
        return (dt + datetime.timedelta(hours=offset_h)).strftime("%H:%M")
    except Exception:
        return "??:??"


def _tracks(programmes: list) -> list:
    """Sendungen auf überlappungsfreie Spuren verteilen (Interval Partitioning).

    programmes: Liste von (start, stop, titel), Zeiten als 14-stelliger String.
    Der Vergleich bleibt rein lexikografisch — das ist zeitzonensicher, solange
    alle Einträge denselben Offset tragen (bei XMLTV praktisch immer der Fall).
    """
    tracks: list = []      # je Spur: Liste der Sendungen
    track_end: list = []   # je Spur: Ende der zuletzt eingefügten Sendung
    for item in sorted(programmes, key=lambda x: (x[0], x[1])):
        start = item[0]
        for i, end in enumerate(track_end):
            if start >= end:           # Spur ist zu dieser Zeit frei
                tracks[i].append(item)
                track_end[i] = item[1]
                break
        else:
            tracks.append([item])
            track_end.append(item[1])
    return tracks


def _collect(path: str, day_prefix: str, max_programmes: int = MAX_PROGRAMMES):
    """XMLTV streamend einlesen -> (namen{id:name}, zeiten{id:[(start,stop)]}, abgeschnitten).

    OHNE Titel — die holt _collect_titles() später nur für die Sender der
    Detailansicht nach. Bei mehr als max_programmes Sendungen wird abgebrochen
    und das dritte Rückgabefeld ist True.
    """
    names: dict = {}
    programmes: dict = {}
    gezaehlt = 0
    abgeschnitten = False
    for _event, elem in ET.iterparse(path, events=("end",)):
        tag = elem.tag
        if tag == "channel":
            cid = elem.get("id") or ""
            if cid:
                disp = elem.findtext("display-name") or cid
                names[cid] = " ".join(disp.split())[:60]
            elem.clear()
        elif tag == "programme":
            if abgeschnitten:
                elem.clear()
                continue
            cid = elem.get("channel") or ""
            start = (elem.get("start") or "")[:14]
            stop = (elem.get("stop") or "")[:14]
            if cid and len(start) == 14 and len(stop) == 14 and (
                not day_prefix or start.startswith(day_prefix)
            ):
                programmes.setdefault(cid, []).append((start, stop))
                gezaehlt += 1
                if max_programmes and gezaehlt >= max_programmes:
                    # Kanalnamen weiter einlesen (die sind billig), Sendungen nicht mehr.
                    abgeschnitten = True
            elem.clear()
    return names, programmes, abgeschnitten


def _collect_titles(path: str, day_prefix: str, cids: set) -> dict:
    """Zweiter, gefilterter Durchlauf: {id: [(start, stop, titel)]} für wenige Sender."""
    out: dict = {}
    if not cids:
        return out
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "programme":
            if elem.tag == "channel":
                elem.clear()
            continue
        cid = elem.get("channel") or ""
        if cid in cids:
            start = (elem.get("start") or "")[:14]
            stop = (elem.get("stop") or "")[:14]
            if len(start) == 14 and len(stop) == 14 and (
                not day_prefix or start.startswith(day_prefix)
            ):
                title = " ".join((elem.findtext("title") or "?").split())[:_TITLE_MAX]
                out.setdefault(cid, []).append((start, stop, title))
        elem.clear()
    return out


def analyze(path: str, *, tz_offset_h: int = 2, day: str = "",
            name_filter: str = "", detail_limit: int = 3,
            sample_limit: int = 10) -> dict:
    """EPG-Datei auf vermischte Programmlisten prüfen.

    day:          "YYYY-MM-DD" — nur diesen Tag betrachten ("" = alle)
    name_filter:  nur Sender, deren Name (oder tvg_id) diesen Text enthält
    detail_limit: für so viele der auffälligsten Sender die Spuren ausgeben
    """
    day_prefix = day.replace("-", "") if day else ""
    names, programmes, abgeschnitten = _collect(path, day_prefix)

    needle = name_filter.strip().lower()
    checked = 0
    hits: list = []

    for cid, plist in programmes.items():
        name = names.get(cid, cid)
        if needle and needle not in name.lower() and needle not in cid.lower():
            continue
        checked += 1
        tracks = _tracks(plist)
        if len(tracks) > 1:
            hits.append({
                "tvg_id": cid,
                "name": name,
                "tracks": len(tracks),
                "programmes": len(plist),
                "_tracks": tracks,
            })

    # Auffälligste zuerst: viele Spuren wiegen schwerer als viele Sendungen.
    hits.sort(key=lambda h: (-h["tracks"], -h["programmes"]))

    # Titel erst jetzt nachladen — nur für die Sender, die in die Detailansicht kommen.
    detail_hits = hits[:max(0, detail_limit)]
    titel = _collect_titles(path, day_prefix, {h["tvg_id"] for h in detail_hits})

    details = []
    for hit in detail_hits:
        mit_titel = _tracks(titel.get(hit["tvg_id"], []))
        details.append({
            "tvg_id": hit["tvg_id"],
            "name": hit["name"],
            "tracks": [
                {
                    "count": len(track),
                    "sample": [
                        {"start": _fmt(s, tz_offset_h),
                         "stop": _fmt(e, tz_offset_h),
                         "title": t}
                        for s, e, t in track[:sample_limit]
                    ],
                }
                for track in mit_titel
            ],
        })

    for hit in hits:
        del hit["_tracks"]

    return {
        "checked": checked,
        "clean": checked - len(hits),
        "affected": len(hits),
        "day": day,
        "tz_offset_h": tz_offset_h,
        "channels": hits,
        "details": details,
        # True = die Quelle war großer als MAX_PROGRAMMES, es wurde nur ein Teil geprüft
        "truncated": abgeschnitten,
    }
