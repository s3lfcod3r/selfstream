"""Auto-Best für WireGuard: wann gesucht wird, wie Messungen zählen, wer gewinnt.

Reine Logik ohne Netzwerk, damit sie testbar ist. Gemessen und umgeschaltet wird
in main.py (_wg_autobest_watch).

Warum eigene Regeln statt der Alarm-Bewertung: Für eine Alarm-Mail reicht es, wenn
ein Segment schneller lädt, als es abspielt. Fürs Umschalten zählt mehr – der Player
wartet beim Senderwechsel auf die ersten Segmente. Lädt jedes 3–4 s, dauert jeder
Wechsel ~10 s, obwohl „nichts ruckelt“. Genau das passierte im November 2026 mit den
Berliner Mullvad-Servern.
"""
from typing import Optional

LADEZEIT_GRENZE = 2.0    # Median-Ladezeit je Segment (s), ab der das Umschalten zäh wird
FEHLER_GRENZE = 0.10     # Anteil fehlgeschlagener Segmente, ab dem gesucht wird
MIN_PROBEN = 4           # so viele echte Segmente braucht die Mbit/s-Regel
MESS_PROBEN = 3          # Downloads je Server bei der Tempo-Messung
NOTFALL_FAKTOR = 1.2     # beim Ruckeln reicht ein etwas schnellerer Server
ROUTINE_FAKTOR = 1.5     # im Leerlauf muss der neue deutlich schneller sein …
GUT_GENUG_MBPS = 80      # Ziel, wenn keins übergeben wird (alt; sonst aus der Nutzerzahl)


def suche_noetig(health: dict, min_mbps: float) -> tuple:
    """(True, Grund), wenn der aktuelle Server die Zuschauer ausbremst."""
    if not health or health.get("level") is None:
        return False, ""
    if health.get("level") == "bad":
        return True, "Wiedergabe ruckelt"
    fehler = health.get("err_rate") or 0
    if fehler >= FEHLER_GRENZE:
        return True, f"{round(fehler * 100)} % der Segmente fehlgeschlagen"
    median = health.get("median_s")
    if median is not None and median >= LADEZEIT_GRENZE:
        return True, f"Segmente laden langsam ({median:.1f} s)"
    mbps = health.get("mbps")
    if mbps is not None and mbps < min_mbps and (health.get("samples") or 0) >= MIN_PROBEN:
        return True, f"nur {mbps} Mbit/s"
    return False, ""


def messung_werten(werte: list) -> float:
    """Tempo-Wert eines Servers aus mehreren Downloads (Mbit/s, None = abgebrochen).

    Es zählt der SCHWÄCHSTE Download: Ein Server, der mal 600 Mbit/s schafft und
    zwischendurch hängt, ist fürs Umschalten schlechter als einer mit stabilen 300.
    """
    if not werte:
        return 0.0
    return float(min((w or 0.0) for w in werte))


def besten_waehlen(aktuell: float, kandidaten: dict, notfall: bool,
                   ziel: float = None) -> Optional[str]:
    """Server, auf den gewechselt wird – oder None (aktueller bleibt).

    notfall=True: Zuschauer werden gerade ausgebremst.
    notfall=False: Routine-Check im Leerlauf. Schafft der aktuelle Server das Ziel
    (ziel, Mbit/s), bleibt er. Sonst gewinnt ein Server, der es schafft – oder,
    wenn keiner es schafft, nur einer mit deutlichem Vorsprung.
    """
    if ziel is None:
        ziel = GUT_GENUG_MBPS
    gemessen = {k: v for k, v in kandidaten.items() if v and v > 0}
    if not gemessen:
        return None
    name = max(gemessen, key=gemessen.get)
    bester = gemessen[name]
    if aktuell <= 0:
        return name
    if notfall:
        return name if bester >= aktuell * NOTFALL_FAKTOR else None
    if aktuell >= ziel:
        return None
    if bester >= ziel:
        return name            # der aktuelle schafft das Ziel nicht, dieser schon
    return name if bester >= aktuell * ROUTINE_FAKTOR else None


# ── Ziel aus der Nutzerzahl ─────────────────────────────────────────────────

STREAM_MBPS = 10         # Bedarf eines Streams (gemessen: 2,5–10 Mbit/s je nach Sender)
RESERVE_PROZENT = 50     # Aufschlag, damit auch das Umschalten flott bleibt
GEDAECHTNIS_ALTER = 48 * 3600   # so lange gilt eine gemerkte Messung als frisch


def ziel_mbps(streams: int, je_stream: float = STREAM_MBPS, reserve_prozent: float = RESERVE_PROZENT) -> float:
    """Tempo, das der VPN-Server für so viele gleichzeitige Streams schaffen soll."""
    return round(max(0, int(streams)) * float(je_stream) * (1 + float(reserve_prozent) / 100.0), 1)


def gedaechtnis_merken(gedaechtnis: dict, server: str, mbps: float, jetzt: float) -> dict:
    """Neue Kopie des Gedächtnisses mit der Messung dieses Servers."""
    neu = dict(gedaechtnis or {})
    neu[server] = {"mbps": round(float(mbps or 0.0), 1), "ts": int(jetzt)}
    return neu


def _frisch(eintrag, jetzt: float) -> bool:
    return bool(eintrag) and (jetzt - (eintrag.get("ts") or 0)) <= GEDAECHTNIS_ALTER


def reihenfolge(kandidaten: list, gedaechtnis: dict, jetzt: float) -> list:
    """Kandidaten so ordnen, dass der zuletzt schnellste zuerst geprüft wird.

    Frisch gemessene Server nach Tempo (schnellster zuerst), danach die übrigen in der
    übergebenen Reihenfolge (dort ist nach Ping vorsortiert). Server, die zuletzt gar
    nichts lieferten (0 Mbit/s), kommen ans Ende.
    """
    g = gedaechtnis or {}
    bekannt = [k for k in kandidaten if _frisch(g.get(k), jetzt) and g[k].get("mbps", 0) > 0]
    tot = [k for k in kandidaten if _frisch(g.get(k), jetzt) and g[k].get("mbps", 0) <= 0]
    rest = [k for k in kandidaten if k not in bekannt and k not in tot]
    bekannt.sort(key=lambda k: -g[k]["mbps"])
    return bekannt + rest + tot


def notfall_reicht(wert: float, aktuell: float, bedarf: float) -> bool:
    """Im Notfall die Suche beenden, sobald ein Server klar besser ist und den Bedarf deckt."""
    return bool(wert and wert > 0 and wert >= aktuell * NOTFALL_FAKTOR and wert >= bedarf)


def ersatz_waehlen(kandidaten: list, gedaechtnis: dict, jetzt: float) -> Optional[str]:
    """Server für den Sofort-Wechsel, wenn der aktive Tunnel tot ist (ohne vorher zu messen)."""
    ordnung = reihenfolge(kandidaten, gedaechtnis, jetzt)
    return ordnung[0] if ordnung else None
