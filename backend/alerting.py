"""Entscheidungslogik für den E-Mail-Alarm (rein, ohne DB, Netzwerk oder Mailversand).

main.py misst, hält den Zustand und verschickt. Hier steht nur, WANN eine Mail
fällig ist und WAS drinsteht. Alles ist eine reine Funktion: Zustand rein,
neuer Zustand + Aktion raus. Dadurch lässt sich das Verhalten mit Tests festnageln
(tests/test_alerting.py), ohne dass ein Server laufen muss.
"""
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional

# ── Alarm (Gesundheits-Stichproben alle 5 min) ───────────────────────────────
SCHLECHT_SERIE = 3        # so viele schlechte Stichproben (~15 min) → Alarm
GUT_SERIE = 3             # so viele gute am Stück → Entwarnung
MAX_ALARME_PRO_TAG = 5    # Flatter-Bremse: danach nur noch im Panel, nicht per Mail

# ── Ereignisse (EPG-Abruf, Senderliste) ──────────────────────────────────────
EREIGNIS_GEDULD = 1800    # erst nach 30 min Dauerfehler melden (Wackler fangen sich)

# ── Passive Bewertung (echte Segment-Abrufe) ─────────────────────────────────
PASSIV_MIN_PROBEN = 3
# Quote = Ladezeit ÷ Spielzeit des Segments. Unter 1 kommt der Player mit.
QUOTE_SCHLECHT = 1.0
QUOTE_LANGSAM = 0.6
FEHLER_SCHLECHT = 0.30
FEHLER_LANGSAM = 0.10
# Rückfall, wenn die Segmentlänge unbekannt ist (Ladezeit in Sekunden)
OHNE_DAUER_SCHLECHT = 3.0
OHNE_DAUER_LANGSAM = 1.5

LATENZ_GRENZE_STANDARD = 1000   # ms; misst einen kompletten Verbindungsaufbau durchs VPN


def perzentil(werte: list, pct: float) -> Optional[float]:
    if not werte:
        return None
    s = sorted(werte)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] * (1 - (k - lo)) + s[hi] * (k - lo)


def passiv_bewerten(proben: list) -> dict:
    """Erlebte Qualität aus echten Segment-Abrufen ("ts","elapsed","bytes","ok","dur").

    Maßstab ist, ob ein Segment schneller lädt, als es abspielt. Vorher galt
    starr „ab 3 s Ladezeit schlecht“ – ein 10-s-Segment, das in 3 s lädt, läuft
    aber flüssig. Ohne bekannte Segmentlänge bleibt die alte Sekunden-Grenze.
    level=None → zu wenig Verkehr, um etwas zu sagen.
    """
    if len(proben) < PASSIV_MIN_PROBEN:
        return {"level": None, "samples": len(proben)}
    gute = [p for p in proben if p.get("ok")]
    fehler = 1.0 - (len(gute) / len(proben))
    lade = [p["elapsed"] for p in gute]
    median = perzentil(lade, 50)
    p90 = perzentil(lade, 90)
    quoten = [p["elapsed"] / p["dur"] for p in gute if p.get("dur")]
    quote = perzentil(quoten, 50) if len(quoten) >= PASSIV_MIN_PROBEN else None
    quote90 = perzentil(quoten, 90) if len(quoten) >= PASSIV_MIN_PROBEN else None
    tb = sum(p["bytes"] for p in gute)
    tt = sum(p["elapsed"] for p in gute) or 0.001

    if quote is not None:
        schlecht = quote >= QUOTE_SCHLECHT
        langsam = quote >= QUOTE_LANGSAM or (quote90 is not None and quote90 >= QUOTE_SCHLECHT)
    else:
        schlecht = median is not None and median >= OHNE_DAUER_SCHLECHT
        langsam = (median is not None and median >= OHNE_DAUER_LANGSAM) \
            or (p90 is not None and p90 >= OHNE_DAUER_SCHLECHT)

    level = "ok"
    if fehler >= FEHLER_SCHLECHT or schlecht:
        level = "bad"
    elif fehler >= FEHLER_LANGSAM or langsam:
        level = "slow"
    return {
        "level": level, "samples": len(proben), "err_rate": round(fehler, 2),
        "median_s": round(median, 2) if median is not None else None,
        "p90_s": round(p90, 2) if p90 is not None else None,
        "quote": round(quote, 2) if quote is not None else None,
        "mbps": round((tb * 8) / (tt * 1_000_000), 1),
    }


def stichprobe_bewerten(probe: dict, latenz_grenze_ms: float) -> tuple:
    """(schlecht, gründe) für eine Gesundheits-Stichprobe – Gründe im Klartext für die Mail."""
    gruende = []
    if probe.get("vpn_up") is False:
        gruende.append("VPN-Tunnel ist unten")
    if probe.get("source") == "passiv":
        if probe.get("level") == "bad":
            teile = []
            if probe.get("quote") is not None:
                teile.append(f"Ladezeit = {probe['quote']:.1f}× Spielzeit")
            elif probe.get("median_s") is not None:
                teile.append(f"Ladezeit ~{probe['median_s']} s je Segment")
            if probe.get("err_rate"):
                teile.append(f"{int(probe['err_rate'] * 100)} % fehlgeschlagen")
            gruende.append("Streams laufen schlecht" + (f" ({', '.join(teile)})" if teile else ""))
    else:
        if not probe.get("ok"):
            text = "Anbieter nicht erreichbar"
            if probe.get("error"):
                text += f" ({probe['error']})"
            if probe.get("kanaele"):
                text += f" – geprüft: {', '.join(probe['kanaele'])}"
            gruende.append(text)
        elif probe.get("latency_ms") is not None and probe["latency_ms"] > latenz_grenze_ms:
            gruende.append(f"Anbieter antwortet langsam ({probe['latency_ms']:.0f} ms, "
                           f"Grenze {latenz_grenze_ms:.0f} ms)")
    return bool(gruende), gruende


@dataclass(frozen=True)
class AlarmZustand:
    aktiv: bool = False          # Störung läuft (gemeldet oder wegen Tageslimit still)
    gemeldet: bool = False       # Alarm-Mail ist raus → Entwarnung fällig
    seit: float = 0.0            # erste schlechte Stichprobe dieser Störung
    gruende: tuple = ()
    schlecht: int = 0
    gut: int = 0
    erste_schlecht: float = 0.0
    tag: str = ""
    alarme_heute: int = 0

    def als_dict(self) -> dict:
        return {"aktiv": self.aktiv, "gemeldet": self.gemeldet, "seit": self.seit,
                "gruende": list(self.gruende), "schlecht": self.schlecht, "gut": self.gut,
                "erste_schlecht": self.erste_schlecht, "tag": self.tag,
                "alarme_heute": self.alarme_heute}

    @classmethod
    def aus_dict(cls, d) -> "AlarmZustand":
        if not isinstance(d, dict):
            return cls()
        try:
            return cls(aktiv=bool(d.get("aktiv")), gemeldet=bool(d.get("gemeldet")),
                       seit=float(d.get("seit") or 0), gruende=tuple(d.get("gruende") or ()),
                       schlecht=int(d.get("schlecht") or 0), gut=int(d.get("gut") or 0),
                       erste_schlecht=float(d.get("erste_schlecht") or 0),
                       tag=str(d.get("tag") or ""), alarme_heute=int(d.get("alarme_heute") or 0))
        except (TypeError, ValueError):
            return cls()


def alarm_schritt(z: AlarmZustand, schlecht: bool, gruende: list, jetzt: float, tag: str) -> tuple:
    """Eine Stichprobe einarbeiten. Rückgabe (neuer Zustand, Aktion).

    Aktion: None, "alarm", "alarm_letzter" (letzte Mail des Tages, danach still)
    oder "entwarnung". Die Zähler wie bisher: Erst SCHLECHT_SERIE schlechte
    Stichproben lösen aus, und zurückgesetzt wird erst nach GUT_SERIE guten am
    Stück – ein einzelner guter Ausreißer mitten in einer Störung zählt nicht.

    Anders als früher gibt es keine 2-Stunden-Sperre mehr: Die schluckte eine
    neue Störung kurz nach einer Entwarnung komplett. Stattdessen ein Tageslimit.
    """
    if z.tag != tag:
        z = replace(z, tag=tag, alarme_heute=0)
    if schlecht:
        z = replace(z, schlecht=z.schlecht + 1, gut=0,
                    erste_schlecht=jetzt if z.schlecht == 0 else z.erste_schlecht)
        if not z.aktiv and z.schlecht >= SCHLECHT_SERIE:
            z = replace(z, aktiv=True, seit=z.erste_schlecht, gruende=tuple(gruende))
            if z.alarme_heute < MAX_ALARME_PRO_TAG:
                z = replace(z, gemeldet=True, alarme_heute=z.alarme_heute + 1)
                return z, ("alarm_letzter" if z.alarme_heute == MAX_ALARME_PRO_TAG else "alarm")
        return z, None
    z = replace(z, gut=z.gut + 1)
    if z.gut < GUT_SERIE:
        return z, None
    aktion = "entwarnung" if (z.aktiv and z.gemeldet) else None
    return replace(z, aktiv=False, gemeldet=False, schlecht=0, seit=0.0, gruende=()), aktion


def alarm_mail_gescheitert(z: AlarmZustand) -> AlarmZustand:
    """Alarm-Mail kam nicht raus → beim nächsten Durchlauf erneut versuchen."""
    return replace(z, aktiv=False, gemeldet=False, alarme_heute=max(0, z.alarme_heute - 1))


def ereignis_schritt(ereignisse: dict, schluessel: str, ok: bool, jetzt: float, fehler: str = "") -> tuple:
    """Dauerfehler (EPG-Abruf, Senderliste) verfolgen. Rückgabe (neue Ereignisse, Aktion, Eintrag).

    Aktion: None, "stoerung" (seit EREIGNIS_GEDULD durchgehend kaputt) oder
    "behoben" (war gemeldet, klappt wieder). Der Eintrag liefert Beginn und Fehler
    für den Mailtext.
    """
    neu = dict(ereignisse or {})
    eintrag = neu.get(schluessel)
    if ok:
        if not eintrag:
            return neu, None, None
        del neu[schluessel]
        return neu, ("behoben" if eintrag.get("gemeldet") else None), eintrag
    if not eintrag:
        eintrag = {"seit": jetzt, "fehler": fehler, "gemeldet": False}
    else:
        eintrag = {**eintrag, "fehler": fehler or eintrag.get("fehler", "")}
    aktion = None
    if not eintrag["gemeldet"] and jetzt - eintrag["seit"] >= EREIGNIS_GEDULD:
        eintrag = {**eintrag, "gemeldet": True}
        aktion = "stoerung"
    neu[schluessel] = eintrag
    return neu, aktion, eintrag


def lebenszeichen_faellig(lokal: datetime, stunde: int, zuletzt_tag: str) -> bool:
    """Tägliches Lebenszeichen zur festen Stunde, einmal pro Tag (vorher: 24 h nach Start)."""
    return lokal.hour == stunde and lokal.date().isoformat() != zuletzt_tag


def neustart_unerwartet(vorher) -> bool:
    """Lief der Dienst vorher und endete NICHT sauber (OOM-Kill, Absturz, Strom weg)?"""
    return isinstance(vorher, dict) and bool(vorher.get("start")) and not vorher.get("sauber")


# ── Mailtexte ────────────────────────────────────────────────────────────────

def dauer_text(sekunden: float) -> str:
    m = max(0, int(round(sekunden / 60)))
    if m < 60:
        return f"{m} Min"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h} Std {m} Min" if m else f"{h} Std"
    d, h = divmod(h, 24)
    return f"{d} Tg {h} Std" if h else f"{d} Tg"


def _fuss(panel_url: str) -> str:
    return f"\nPanel: {panel_url}\n" if panel_url else ""


def alarm_mail(gruende: list, messwerte: list, seit_text: str, panel_url: str = "",
               letzter: bool = False) -> tuple:
    zeilen = gruende or ["Anhaltend schwache Werte"]
    text = ("SelfStream hat ein Problem erkannt:\n\n- " + "\n- ".join(zeilen) +
            f"\n\nSeit: {seit_text} (seit mindestens 15 Minuten durchgehend)\n")
    if messwerte:
        text += "\nMesswerte der letzten Prüfung:\n" + \
            "".join(f"  {name}: {wert}\n" for name, wert in messwerte)
    text += "\nDu bekommst eine Entwarnung, sobald es wieder läuft.\n"
    if letzter:
        text += (f"\nHinweis: Das ist die {MAX_ALARME_PRO_TAG}. Störungs-Mail heute. Weitere "
                 "Störungen bis Mitternacht siehst du nur noch im Panel.\n")
    kurz = zeilen[0].split(" (")[0].split(" – ")[0]   # Details stehen im Text
    return "🔴 SelfStream: " + kurz, text + _fuss(panel_url)


def entwarnung_mail(seit_text: str, bis_text: str, dauer: str, panel_url: str = "") -> tuple:
    text = (f"Die gemeldete Störung ist behoben – SelfStream läuft wieder normal.\n\n"
            f"Gestört: {seit_text} bis {bis_text} ({dauer})\n")
    return "✅ SelfStream: wieder in Ordnung", text + _fuss(panel_url)


def ereignis_mail(was: str, fehler: str, seit_text: str, behoben: bool, dauer: str = "",
                  panel_url: str = "") -> tuple:
    if behoben:
        text = f"{was} klappt wieder.\n\nGestört seit {seit_text} ({dauer}).\n"
        return f"✅ SelfStream: {was} wieder in Ordnung", text + _fuss(panel_url)
    text = (f"{was} schlägt seit {seit_text} durchgehend fehl.\n\n"
            f"Letzter Fehler: {fehler or 'unbekannt'}\n\n"
            "SelfStream versucht es alle 5 Minuten weiter und meldet sich, sobald es klappt.\n")
    return f"🟠 SelfStream: {was} schlägt fehl", text + _fuss(panel_url)


def neustart_mail(lebte_text: str, start_text: str, panel_url: str = "") -> tuple:
    text = ("SelfStream wurde unerwartet neu gestartet – der vorige Lauf endete nicht sauber.\n"
            "Typische Ursachen: Speicherlimit erreicht (OOM-Kill), Absturz, Server ohne Strom.\n\n"
            f"Letztes Lebenszeichen: {lebte_text}\n"
            f"Wieder gestartet: {start_text}\n\n"
            "Laufende Streams sind dabei abgebrochen. Ein geplantes Update oder ein Stopp in "
            "Unraid löst diese Mail nicht aus.\n")
    return "🟠 SelfStream: unerwartet neu gestartet", text + _fuss(panel_url)


def lebenszeichen_mail(level: str, hinweise: list, stoerungen_24h: int, panel_url: str = "") -> tuple:
    text = f"SelfStream lebt – Status: {level.upper()}\n\n"
    text += "Alles in Ordnung.\n" if not hinweise else "Hinweise:\n- " + "\n- ".join(hinweise) + "\n"
    text += f"\nStörungs-Mails in den letzten 24 Stunden: {stoerungen_24h}\n"
    return "✅ SelfStream: Tages-Lebenszeichen", text + _fuss(panel_url)
