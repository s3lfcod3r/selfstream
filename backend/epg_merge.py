"""Mehrere EPG-Quellen zu einer zusammenführen.

Kein EPG-Anbieter ist fehlerfrei: mal fehlen Sendungen, mal liegen zwei
Programmlisten unter einer Kanal-ID. Mit mehreren Quellen lässt sich das
abfedern — die erste Quelle gibt den Ton an, die weiteren füllen nur, was
dort fehlt.

Bewusst KEIN Ratespiel darüber, welche Quelle "recht hat": Die Reihenfolge der
Quellen entscheidet. Ergänzt wird ausschließlich, wo die höherrangige Quelle
eine echte Lücke lässt — so kann eine schwächere Quelle die gute nie
überschreiben.

Alles läuft streamend (iterparse) und schreibt direkt in die Zieldatei, damit
auch mehrere große Quellen keinen Objektbaum im Speicher aufbauen.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from bisect import bisect_left, insort

# Zusätze, die je nach Anbieter dranstehen oder fehlen und für die Zuordnung
# unerheblich sind.
_BALLAST = re.compile(r"\b(hd|uhd|fhd|sd|deutschland|germany|austria|de|at)\b")


def normalisiere(name: str) -> str:
    """Sendernamen auf eine vergleichbare Form bringen.

    'Sky Cinema Highlights HD' und 'Sky.Cinema.Highlights.HD.de' ergeben beide
    'skycinemahighlights'.
    """
    n = (name or "").lower()
    n = re.sub(r"\.(de|at)\b", "", n)
    n = n.replace(".", " ").replace("_", " ")
    n = _BALLAST.sub("", n)
    return re.sub(r"[^a-z0-9]+", "", n)


def lies_kanaele(pfad: str) -> dict:
    """{kanal_id: anzeigename} aus einer XMLTV-Datei."""
    namen = {}
    for _ev, elem in ET.iterparse(pfad, events=("end",)):
        # Nur die beiden Container leeren. Würde man jedes Element leeren, wären
        # <display-name> und <title> bereits entwertet, wenn der Vater drankommt.
        if elem.tag == "channel":
            cid = elem.get("id") or ""
            if cid:
                namen[cid] = " ".join((elem.findtext("display-name") or cid).split())
            elem.clear()
        elif elem.tag == "programme":
            elem.clear()
    return namen


def ordne_zu(haupt: dict, zweit: dict) -> dict:
    """{kanal_id_der_zweitquelle: kanal_id_der_hauptquelle} über Namensgleichheit."""
    nach_name = {}
    for cid, name in haupt.items():
        nach_name.setdefault(normalisiere(name), cid)
    zuordnung = {}
    for cid, name in zweit.items():
        ziel = nach_name.get(normalisiere(name))
        if ziel:
            zuordnung[cid] = ziel
    return zuordnung


def _sendungen(pfad: str, erlaubt=None, umbenennen: dict = None):
    """Sendungen streamend liefern: (kanal, start_key, stop_key, xml_text)."""
    for _ev, elem in ET.iterparse(pfad, events=("end",)):
        # Unterelemente NICHT leeren — sonst gingen Titel und Beschreibung verloren,
        # bevor die Sendung selbst geschrieben wird.
        if elem.tag != "programme":
            if elem.tag == "channel":
                elem.clear()
            continue
        cid = elem.get("channel") or ""
        if umbenennen is not None:
            cid = umbenennen.get(cid, "")
        start = (elem.get("start") or "").strip()
        stop = (elem.get("stop") or "").strip()
        if cid and len(start[:14]) == 14 and len(stop[:14]) == 14 and (
                erlaubt is None or cid in erlaubt):
            elem.set("channel", cid)
            yield cid, start[:14], stop[:14], ET.tostring(elem, encoding="unicode")
        elem.clear()


def zusammenfuehren(quellen: list, ziel: str, erlaubt=None) -> dict:
    """Quellen der Reihe nach zusammenführen und als XMLTV schreiben.

    quellen: Dateipfade, wichtigste zuerst.
    erlaubt: Menge der Kanal-IDs, die übernommen werden sollen (None = alle).

    Rückgabe: Statistik je Quelle, wie viele Sendungen sie beigesteuert hat.
    """
    if not quellen:
        return {"channels": 0, "programmes": 0, "sources": []}

    haupt_kanaele = lies_kanaele(quellen[0])
    belegt: dict = {}          # kanal -> sortierte [(start, stop)]
    beitrag = []
    gesamt = 0

    # Erst in eine Nebendatei schreiben und am Ende umbenennen: bricht etwas ab,
    # bleibt die bisherige Zieldatei unangetastet statt halb überschrieben.
    tmp = ziel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<tv generator-info-name="selfstream">\n')

        # Kanaldefinitionen zuerst — so wie es Player erwarten.
        for cid, name in haupt_kanaele.items():
            if erlaubt is not None and cid not in erlaubt:
                continue
            el = ET.Element("channel", {"id": cid})
            ET.SubElement(el, "display-name").text = name
            f.write(ET.tostring(el, encoding="unicode").strip() + "\n")

        for nr, pfad in enumerate(quellen):
            if nr == 0:
                umbenennen = None
            else:
                # Fremde Kanal-IDs auf die der Hauptquelle umschreiben
                umbenennen = ordne_zu(haupt_kanaele, lies_kanaele(pfad))
                if not umbenennen:
                    beitrag.append({"source": pfad, "added": 0, "mapped": 0})
                    continue

            hinzu = 0
            for cid, start, stop, xml_text in _sendungen(pfad, erlaubt, umbenennen):
                platz = belegt.setdefault(cid, [])
                i = bisect_left(platz, (start, ""))
                if ((i > 0 and platz[i - 1][1] > start)
                        or (i < len(platz) and platz[i][0] < stop)):
                    continue          # Sendeplatz belegt — höherrangige Quelle gewinnt
                insort(platz, (start, stop))
                f.write(xml_text.strip() + "\n")
                hinzu += 1
            gesamt += hinzu
            beitrag.append({
                "source": pfad,
                "added": hinzu,
                "mapped": len(umbenennen) if umbenennen is not None else len(haupt_kanaele),
            })

        f.write("</tv>\n")

    import os
    os.replace(tmp, ziel)
    return {"channels": len(belegt), "programmes": gesamt, "sources": beitrag}
