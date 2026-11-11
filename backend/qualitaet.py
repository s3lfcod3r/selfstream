"""Qualitätsauswertung für die Seite „Traffic“ (rein, ohne DB/Netzwerk).

Maßstab ist überall die Reserve: Spielzeit eines Segments ÷ Zeit, die es unterwegs war.
Reserve 1 heißt, das Segment kommt genau so schnell an, wie es abgespielt wird – darunter
ruckelt es. Gemessen wird auf zwei Strecken:

  rein = Anbieter → VPN → SelfStream   (Abruf des Segments)

Die Strecke zum Gerät lässt sich so NICHT messen: Zwischen SelfStream und Player sitzt in
der Regel ein Reverse-Proxy, der jedes Segment sofort komplett abnimmt. Die Auslieferzeit
war deshalb praktisch immer 0 (gemessen am 11.11.2026). Stattdessen zählt der Rückstand:
Ein Player bleibt im Normalbetrieb gleich weit hinter dem neuesten Segment. Kommt ein Gerät
(oder dessen Leitung) nicht hinterher, fragt es immer ältere Segmente an – der Abstand wächst.
Fällt es ganz aus der Playlist (die hält nur wenige Segmente vor), springt der Player nach
vorn: Dann fehlen ihm Segmente. Beides zusammen ist das Zeichen für die Geräte-Strecke.
"""
from typing import Optional

import alerting

RESERVE_KNAPP = round(1.0 / alerting.QUOTE_LANGSAM, 2)   # darunter „knapp“ (≈ 1,67)
RESERVE_MAX = 99.0            # Anzeige-Obergrenze
GERAET_URTEIL = "Gerät kommt nicht hinterher"
ZUSCHAUER_FENSTER = 120.0     # s: so alte Proben zählen für „wer schaut gerade“
RUECK_PROBEN = 3              # so viele Anfragen am Stück müssen den Rückstand zeigen
RUECK_KNAPP = 1               # Segmente über dem Start-Abstand: ab hier „knapp“
RUECK_SCHLECHT = 2            # … ab hier kommt das Gerät nicht mehr hinterher
SKIP_SCHLECHT = 2             # übersprungene Segmente im Fenster: ab hier „schlecht“
STOER_LUECKE = 120.0          # s ohne späte Segmente → Störung zu Ende
STOER_MIN = 3                 # ab so vielen späten Segmenten ist es eine Störung
PROBE_FENSTER = 600.0         # s: so lange nach Störungsbeginn zählt eine Netz-Probe
PROBE_SCHNELL = 20.0          # Mbit/s: neutraler Download durch den Tunnel gilt als schnell
RANG_MIN = 50                 # Segmente, ab denen ein Sender in die Rangliste kommt


def stufe(elapsed: float, dur: Optional[float]) -> str:
    """'ok' | 'delayed' | 'slow' für eine Strecke – gemessen an der Spielzeit des Segments."""
    if dur and dur > 0:
        quote = elapsed / dur
        if quote >= alerting.QUOTE_SCHLECHT:
            return "slow"
        return "delayed" if quote >= alerting.QUOTE_LANGSAM else "ok"
    if elapsed >= alerting.OHNE_DAUER_SCHLECHT:
        return "slow"
    return "delayed" if elapsed >= alerting.OHNE_DAUER_LANGSAM else "ok"


def reserve(elapsed: Optional[float], dur: Optional[float]) -> Optional[float]:
    """Spielzeit ÷ Laufzeit, auf eine Nachkommastelle; None, wenn etwas fehlt."""
    if not dur or dur <= 0 or elapsed is None:
        return None
    if elapsed <= 0:
        return RESERVE_MAX
    return min(RESERVE_MAX, round(dur / elapsed, 1))


def ampel(res: Optional[float]) -> str:
    """'gut' | 'knapp' | 'schlecht' | 'unbekannt' für eine Reserve."""
    if res is None:
        return "unbekannt"
    if res < 1.0:
        return "schlecht"
    return "knapp" if res < RESERVE_KNAPP else "gut"


def rueckstand(letzte: list) -> Optional[int]:
    """Gesicherter Rückstand aus den letzten Anfragen einer Sitzung (Segmente über dem
    Start-Abstand). Es zählt der KLEINSTE der letzten RUECK_PROBEN Werte: Der Abstand
    schwankt von Natur aus um ein Segment, je nachdem, ob das neueste schon angekündigt ist.
    None, solange zu wenige Anfragen vorliegen."""
    werte = [w for w in letzte if w is not None]
    if len(werte) < RUECK_PROBEN:
        return None
    return int(min(werte[-RUECK_PROBEN:]))


def rueck_ampel(rueck: Optional[int], uebersprungen: int = 0) -> str:
    """Ampel der Geräte-Strecke aus gesichertem Rückstand und übersprungenen Segmenten."""
    if uebersprungen >= SKIP_SCHLECHT or (rueck is not None and rueck >= RUECK_SCHLECHT):
        return "schlecht"
    if uebersprungen >= 1 or (rueck is not None and rueck >= RUECK_KNAPP):
        return "knapp"
    return "unbekannt" if rueck is None else "gut"


def _median(werte: list) -> Optional[float]:
    return alerting.perzentil(werte, 50)


def zuschauer(proben: list, jetzt: float, fenster: float = ZUSCHAUER_FENSTER) -> list:
    """Je Nutzer die Anlieferung (Reserve) und ob sein Gerät Schritt hält (Rückstand).

    Probe: {"ts","user","channel","elapsed","dur","cached","rueck","skip"}. Segmente aus
    dem Zwischenspeicher sagen nichts über die Anlieferung. "rueck" ist der gesicherte
    Rückstand der Sitzung zum Zeitpunkt der Probe (siehe rueckstand()), "skip" die Zahl
    der Segmente, die der Player vor dieser Anfrage ausgelassen hat.
    """
    nach_nutzer: dict = {}
    for p in proben:
        if jetzt - p.get("ts", 0) <= fenster:
            nach_nutzer.setdefault(p.get("user") or "?", []).append(p)
    out = []
    for name, ps in nach_nutzer.items():
        rein = [reserve(p.get("elapsed"), p.get("dur")) for p in ps if not p.get("cached")]
        rein = [r for r in rein if r is not None]
        r_rein = _median(rein)
        neueste = max(ps, key=lambda p: p.get("ts", 0))
        rueck = neueste.get("rueck")
        skips = sum(int(p.get("skip") or 0) for p in ps)
        a_rein, a_rueck = ampel(r_rein), rueck_ampel(rueck, skips)
        if a_rein in ("schlecht", "knapp"):
            urteil, level = "Anlieferung langsam", a_rein
        elif a_rueck in ("schlecht", "knapp"):
            urteil, level = GERAET_URTEIL, a_rueck
        elif a_rein == "unbekannt" and a_rueck == "unbekannt":
            urteil, level = "noch keine Messung", "unbekannt"
        else:
            urteil, level = "flüssig", "gut"
        out.append({
            "user": name,
            "channel": max(ps, key=lambda p: p.get("ts", 0)).get("channel", ""),
            "rein": round(r_rein, 1) if r_rein is not None else None,
            "rueck": rueck, "skips": skips,
            "rein_level": a_rein, "rueck_level": a_rueck,
            "urteil": urteil, "level": level, "samples": len(ps),
        })
    out.sort(key=lambda z: z["user"].lower())
    return out


def _gruppen(ereignisse: list, luecke: float) -> list:
    gruppen, aktuell = [], []
    for e in sorted(ereignisse, key=lambda e: e["ts"]):
        if aktuell and e["ts"] - aktuell[-1]["ts"] > luecke:
            gruppen.append(aktuell)
            aktuell = []
        aktuell.append(e)
    if aktuell:
        gruppen.append(aktuell)
    return gruppen


def _probe_zu(von: float, bis: float, netz_proben: list) -> Optional[dict]:
    passend = [p for p in netz_proben if von - 60 <= p["ts"] <= max(bis, von + PROBE_FENSTER)]
    return min(passend, key=lambda p: abs(p["ts"] - von)) if passend else None


def _eintrag(gruppe: list, ursache: str, probe: Optional[dict] = None) -> dict:
    von, bis = gruppe[0]["ts"], gruppe[-1]["ts"]
    sender = sorted({e.get("channel") or "?" for e in gruppe})
    nutzer = sorted({e.get("user") or "?" for e in gruppe})
    return {
        "ursache": ursache, "von": von, "bis": bis, "dauer": int(bis - von),
        "anzahl": len(gruppe), "sender": sender[:5], "sender_anzahl": len(sender),
        "nutzer": nutzer[:5], "nutzer_anzahl": len(nutzer),
        "probe_mbps": probe.get("mbps") if probe else None, "probe": probe is not None,
    }


def stoerungen(ereignisse: list, netz_proben: list = (), luecke: float = STOER_LUECKE) -> dict:
    """Späte Segmente zu Störungen bündeln und die wahrscheinliche Ursache benennen.

    Ereignis: {"ts","user","channel","type"}; type 'slow'/'delayed' = Anlieferung zu spät,
    'geraet' = das Gerät fällt zurück, obwohl die Anlieferung pünktlich war. Ursachen:
      'sender'   nur ein Sender betroffen → Anbieter, einzelner Sender
      'anbieter' mehrere Sender, neutraler Download durch den Tunnel war schnell
      'vpn'      mehrere Sender, neutraler Download langsam oder gescheitert
      'netz'     mehrere Sender, keine Probe → Anbieter oder VPN, nicht zu trennen
      'geraet'   nur die Strecke zu einem Nutzer
    """
    netz_proben = list(netz_proben)
    rein = [e for e in ereignisse if e.get("type") in ("slow", "delayed")]
    raus = [e for e in ereignisse if e.get("type") == "geraet"]
    liste, einzelne = [], 0
    for g in _gruppen(rein, luecke):
        if len(g) < STOER_MIN:
            einzelne += len(g)
            continue
        if len({e.get("channel") for e in g}) < 2:
            liste.append(_eintrag(g, "sender"))
            continue
        probe = _probe_zu(g[0]["ts"], g[-1]["ts"], netz_proben)
        if probe is None:
            ursache = "netz"
        elif probe.get("mbps") is not None and probe["mbps"] >= PROBE_SCHNELL:
            ursache = "anbieter"
        else:
            ursache = "vpn"
        liste.append(_eintrag(g, ursache, probe))
    nach_nutzer: dict = {}
    for e in raus:
        nach_nutzer.setdefault(e.get("user") or "?", []).append(e)
    for es in nach_nutzer.values():
        for g in _gruppen(es, luecke):
            if len(g) < STOER_MIN:
                einzelne += len(g)
            else:
                liste.append(_eintrag(g, "geraet"))
    liste.sort(key=lambda s: s["von"], reverse=True)
    return {"stoerungen": liste, "einzelne": einzelne}


def rangliste(zeilen: list, mindestens: int = RANG_MIN) -> list:
    """Sender nach Anteil später Segmente. zeilen: [{"channel","gesamt","spaet"}, …]."""
    summe: dict = {}
    for z in zeilen:
        s = summe.setdefault(z.get("channel") or "?", [0, 0])
        s[0] += int(z.get("gesamt") or 0)
        s[1] += int(z.get("spaet") or 0)
    out = [{"channel": ch, "gesamt": g, "spaet": sp, "anteil": round(100.0 * sp / g, 1)}
           for ch, (g, sp) in summe.items() if g >= mindestens]
    out.sort(key=lambda r: (-r["anteil"], -r["spaet"], r["channel"].lower()))
    return out


def urteil(anbieter_level: Optional[str], vpn_an: bool, vpn_traegt: bool,
           probe_mbps: Optional[float], probe_da: bool, knappe_nutzer: list) -> dict:
    """Ein Satz, wo es gerade hakt. level: 'gut' | 'knapp' | 'schlecht' | 'unbekannt'."""
    if vpn_an and not vpn_traegt:
        return {"level": "schlecht", "text": "Der VPN-Tunnel steht nicht. Solange kommt kein Bild."}
    if anbieter_level in ("bad", "slow"):
        level = "schlecht" if anbieter_level == "bad" else "knapp"
        if not probe_da:
            text = "Die Anlieferung ist langsam. Ob Anbieter oder VPN, ist noch nicht gemessen."
        elif probe_mbps is not None and probe_mbps >= PROBE_SCHNELL:
            text = "Der Anbieter liefert langsam. Das VPN ist schnell."
        else:
            text = "Das VPN oder die Leitung ist langsam, nicht der Anbieter allein."
        return {"level": level, "text": text}
    if knappe_nutzer:
        namen = ", ".join(knappe_nutzer[:3])
        return {"level": "knapp",
                "text": f"Anbieter und VPN sind schnell. Bei {namen} kommt das Gerät oder "
                        f"dessen Leitung nicht hinterher."}
    if anbieter_level is None:
        return {"level": "unbekannt", "text": "Gerade schaut niemand, deshalb gibt es keine Messung."}
    return {"level": "gut", "text": "Alles flüssig."}
