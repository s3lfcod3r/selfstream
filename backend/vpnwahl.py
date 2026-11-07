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
GUT_GENUG_MBPS = 80      # … und der aktuelle darf nicht ohnehin schnell genug sein


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


def besten_waehlen(aktuell: float, kandidaten: dict, notfall: bool) -> Optional[str]:
    """Server, auf den gewechselt wird – oder None (aktueller bleibt).

    notfall=True: Zuschauer werden gerade ausgebremst.
    notfall=False: Routine-Check im Leerlauf, nur bei deutlichem Vorsprung wechseln.
    """
    gemessen = {k: v for k, v in kandidaten.items() if v and v > 0}
    if not gemessen:
        return None
    name = max(gemessen, key=gemessen.get)
    bester = gemessen[name]
    if aktuell <= 0:
        return name
    if notfall:
        return name if bester >= aktuell * NOTFALL_FAKTOR else None
    if aktuell >= GUT_GENUG_MBPS:
        return None
    return name if bester >= aktuell * ROUTINE_FAKTOR else None
