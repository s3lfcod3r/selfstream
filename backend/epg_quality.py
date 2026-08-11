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
"""
from __future__ import annotations

import datetime
import xml.etree.ElementTree as ET

# Titel werden nur für die Detailansicht gebraucht — gekürzt halten spart Speicher.
_TITLE_MAX = 80


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


def _collect(path: str, day_prefix: str):
    """XMLTV streamend einlesen -> (namen{id:name}, sendungen{id:[(start,stop,titel)]})."""
    names: dict = {}
    programmes: dict = {}
    for _event, elem in ET.iterparse(path, events=("end",)):
        tag = elem.tag
        if tag == "channel":
            cid = elem.get("id") or ""
            if cid:
                disp = elem.findtext("display-name") or cid
                names[cid] = " ".join(disp.split())[:60]
            elem.clear()
        elif tag == "programme":
            cid = elem.get("channel") or ""
            start = (elem.get("start") or "")[:14]
            stop = (elem.get("stop") or "")[:14]
            if cid and len(start) == 14 and len(stop) == 14 and (
                not day_prefix or start.startswith(day_prefix)
            ):
                title = " ".join((elem.findtext("title") or "?").split())[:_TITLE_MAX]
                programmes.setdefault(cid, []).append((start, stop, title))
            elem.clear()
    return names, programmes


def analyze(path: str, *, tz_offset_h: int = 2, day: str = "",
            name_filter: str = "", detail_limit: int = 3,
            sample_limit: int = 10) -> dict:
    """EPG-Datei auf vermischte Programmlisten prüfen.

    day:          "YYYY-MM-DD" — nur diesen Tag betrachten ("" = alle)
    name_filter:  nur Sender, deren Name (oder tvg_id) diesen Text enthält
    detail_limit: für so viele der auffälligsten Sender die Spuren ausgeben
    """
    day_prefix = day.replace("-", "") if day else ""
    names, programmes = _collect(path, day_prefix)

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

    details = []
    for hit in hits[:max(0, detail_limit)]:
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
                for track in hit["_tracks"]
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
    }
