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
# unerheblich sind. Nur Bildqualität — Länderkennzeichen gehören NICHT hierher:
# 'ProSieben Austria' und 'ProSieben Germany' sind verschiedene Sender mit
# verschiedenem Programm. Wurden sie wegnormalisiert, ergaben beide 'prosieben',
# und die Sendungen der Ostereich-Variante landeten beim deutschen Sender.
# Der Preis dafür: ein Sender, der in einer Quelle 'ProSieben' und in der anderen
# 'ProSieben.de' heißt, wird nicht mehr zusammengeführt. Eine fehlende Ergänzung
# ist deutlich billiger als ein falsches Programm im Player.
_BALLAST = re.compile(r"\b(hd|uhd|fhd|sd)\b")


def normalisiere(name: str) -> str:
    """Sendernamen auf eine vergleichbare Form bringen.

    'Sky Cinema Highlights HD' und 'Sky.Cinema.Highlights.HD' ergeben beide
    'skycinemahighlights'. Länderkennzeichen bleiben Teil des Schlüssels.
    """
    n = (name or "").lower()
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


def ordne_zu(haupt: dict, zweit: dict) -> tuple:
    """Zuordnung über Namensgleichheit.

    Rückgabe: ({kanal_id_der_zweitquelle: kanal_id_der_hauptquelle}, anzahl_verworfen)

    Mehrdeutige Namen werden NICHT zugeordnet — vorher gewann per setdefault
    willkürlich der zuerst gelesene Kanal, und alle weiteren Kanäle mit gleichem
    Schlüssel wurden auf ihn gemappt. Das mischte fremdes Programm in einen Sender.
    Mehrdeutig ist ein Schlüssel, der in der Hauptquelle ODER in der Zweitquelle
    mehr als einen Kanal hat.
    """
    haupt_nach_name: dict = {}
    for cid, name in haupt.items():
        haupt_nach_name.setdefault(normalisiere(name), []).append(cid)
    zweit_nach_name: dict = {}
    for cid, name in zweit.items():
        zweit_nach_name.setdefault(normalisiere(name), []).append(cid)

    zuordnung = {}
    verworfen = 0
    for key, cids in zweit_nach_name.items():
        ziele = haupt_nach_name.get(key) or []
        if not ziele:
            continue                      # kein Gegenstück — kein Fund, nichts zu verwerfen
        if len(ziele) > 1 or len(cids) > 1:
            verworfen += len(cids)        # mehrdeutig — lieber nichts zuordnen
            continue
        zuordnung[cids[0]] = ziele[0]
    return zuordnung, verworfen


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

        mehrdeutig_gesamt = 0
        for nr, pfad in enumerate(quellen):
            verworfen = 0
            if nr == 0:
                umbenennen = None
            else:
                # Fremde Kanal-IDs auf die der Hauptquelle umschreiben
                umbenennen, verworfen = ordne_zu(haupt_kanaele, lies_kanaele(pfad))
                mehrdeutig_gesamt += verworfen
                if not umbenennen:
                    beitrag.append({"source": pfad, "added": 0, "mapped": 0,
                                    "ambiguous": verworfen})
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
                # Kanäle, die wegen eines mehrdeutigen Namens bewusst nicht zugeordnet wurden
                "ambiguous": verworfen,
            })

        f.write("</tv>\n")

    import os
    os.replace(tmp, ziel)
    return {"channels": len(belegt), "programmes": gesamt, "sources": beitrag,
            "ambiguous": mehrdeutig_gesamt}
