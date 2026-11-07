"""Tests für die Alarm-Logik (alerting.py) und die Segmentlängen (hls.py)."""
from datetime import datetime

import alerting as a
from hls import segment_durations

TAG = "2026-11-07"


def _lauf(z, folge, start=0.0, tag=TAG):
    """Folge von Stichproben (True = schlecht) einspielen, Aktionen sammeln."""
    aktionen = []
    for i, schlecht in enumerate(folge):
        z, aktion = a.alarm_schritt(z, schlecht, ["Grund"] if schlecht else [], start + i * 300, tag)
        if aktion:
            aktionen.append(aktion)
    return z, aktionen


# ── Alarm-Zustand ────────────────────────────────────────────────────────────

def test_alarm_erst_nach_drei_schlechten():
    z, akt = _lauf(a.AlarmZustand(), [True, True])
    assert akt == [] and not z.aktiv
    z, akt = _lauf(z, [True], start=600)
    assert akt == ["alarm"] and z.gemeldet
    assert z.seit == 0.0                     # Beginn = erste schlechte Stichprobe


def test_einzelner_guter_ausreisser_setzt_nicht_zurueck():
    _, akt = _lauf(a.AlarmZustand(), [True, False, True, True])
    assert akt == ["alarm"]


def test_entwarnung_nach_drei_guten():
    z, akt = _lauf(a.AlarmZustand(), [True] * 3 + [False] * 3)
    assert akt == ["alarm", "entwarnung"]
    assert not z.aktiv and z.schlecht == 0


def test_neue_stoerung_kurz_nach_entwarnung_wird_gemeldet():
    # Früher schluckte die 2-Stunden-Sperre diese zweite Störung komplett.
    _, akt = _lauf(a.AlarmZustand(), [True] * 3 + [False] * 3 + [True] * 3)
    assert akt == ["alarm", "entwarnung", "alarm"]


def test_tageslimit_und_letzte_mail():
    folge = ([True] * 3 + [False] * 3) * (a.MAX_ALARME_PRO_TAG + 2)
    _, akt = _lauf(a.AlarmZustand(), folge)
    alarme = [x for x in akt if x.startswith("alarm")]
    assert len(alarme) == a.MAX_ALARME_PRO_TAG
    assert alarme[-1] == "alarm_letzter"
    # Stille Störungen bekommen auch keine Entwarnung
    assert akt.count("entwarnung") == a.MAX_ALARME_PRO_TAG


def test_tageslimit_setzt_am_naechsten_tag_zurueck():
    z = a.AlarmZustand(tag=TAG, alarme_heute=a.MAX_ALARME_PRO_TAG)
    _, akt = _lauf(z, [True] * 3, tag="2026-11-08")
    assert akt == ["alarm"]


def test_gescheiterte_mail_wird_wiederholt():
    z, akt = _lauf(a.AlarmZustand(), [True] * 3)
    assert akt == ["alarm"]
    z = a.alarm_mail_gescheitert(z)
    z, akt = _lauf(z, [True], start=900)
    assert akt == ["alarm"] and z.alarme_heute == 1


def test_zustand_ueberlebt_speichern():
    z, _ = _lauf(a.AlarmZustand(), [True] * 3)
    assert a.AlarmZustand.aus_dict(z.als_dict()) == z
    assert a.AlarmZustand.aus_dict("kaputt") == a.AlarmZustand()


# ── Ereignisse (EPG, Senderliste) ───────────────────────────────────────────

def test_ereignis_erst_nach_geduld_und_dann_behoben():
    ev, akt, _ = a.ereignis_schritt({}, "epg", False, 0, "Timeout")
    assert akt is None
    ev, akt, _ = a.ereignis_schritt(ev, "epg", False, a.EREIGNIS_GEDULD - 1, "Timeout")
    assert akt is None
    ev, akt, e = a.ereignis_schritt(ev, "epg", False, a.EREIGNIS_GEDULD, "Timeout")
    assert akt == "stoerung" and e["seit"] == 0
    ev, akt, _ = a.ereignis_schritt(ev, "epg", False, a.EREIGNIS_GEDULD + 300, "Timeout")
    assert akt is None                       # nur einmal melden
    ev, akt, _ = a.ereignis_schritt(ev, "epg", True, a.EREIGNIS_GEDULD + 600)
    assert akt == "behoben" and ev == {}


def test_kurzer_wackler_meldet_nichts():
    ev, _, _ = a.ereignis_schritt({}, "m3u:1", False, 0, "x")
    ev, akt, _ = a.ereignis_schritt(ev, "m3u:1", True, 300)
    assert akt is None and ev == {}


# ── Bewertung ────────────────────────────────────────────────────────────────

def _proben(elapsed, dur=None, ok=True, n=5):
    return [{"ts": 0, "elapsed": elapsed, "bytes": 1_000_000, "ok": ok, "dur": dur}] * n


def test_langes_segment_mit_3s_ladezeit_ist_ok():
    # Vorher „bad“ (feste 3-s-Grenze), obwohl 10-s-Segmente in 3 s flüssig laufen.
    assert a.passiv_bewerten(_proben(3.0, dur=10))["level"] == "ok"


def test_ladezeit_ueber_spielzeit_ist_schlecht():
    assert a.passiv_bewerten(_proben(6.5, dur=6))["level"] == "bad"


def test_ohne_dauer_alte_grenzen():
    assert a.passiv_bewerten(_proben(3.2))["level"] == "bad"
    assert a.passiv_bewerten(_proben(0.5))["level"] == "ok"


def test_zu_wenig_proben():
    assert a.passiv_bewerten(_proben(1.0, n=2))["level"] is None


def test_viele_fehler_sind_schlecht():
    proben = _proben(0.5, n=3) + _proben(0.5, ok=False, n=2)
    assert a.passiv_bewerten(proben)["level"] == "bad"


def test_leerlauf_gruende_sind_konkret():
    schlecht, g = a.stichprobe_bewerten(
        {"source": "leerlauf", "ok": False, "error": "Keine Segmente erreichbar",
         "kanaele": ["Das Erste", "ZDF"]}, 1000)
    assert schlecht and "Das Erste, ZDF" in g[0] and "Keine Segmente" in g[0]
    schlecht, g = a.stichprobe_bewerten({"source": "leerlauf", "ok": True, "latency_ms": 1500}, 1000)
    assert schlecht and "1500 ms" in g[0]
    schlecht, _ = a.stichprobe_bewerten({"source": "leerlauf", "ok": True, "latency_ms": 600}, 1000)
    assert not schlecht


def test_vpn_unten_immer_schlecht():
    schlecht, g = a.stichprobe_bewerten({"source": "passiv", "level": "ok", "vpn_up": False}, 1000)
    assert schlecht and g == ["VPN-Tunnel ist unten"]


# ── Lebenszeichen, Neustart, Texte ───────────────────────────────────────────

def test_lebenszeichen_einmal_zur_stunde():
    assert a.lebenszeichen_faellig(datetime(2026, 11, 7, 8, 5), 8, "2026-11-06")
    assert not a.lebenszeichen_faellig(datetime(2026, 11, 7, 8, 10), 8, "2026-11-07")
    assert not a.lebenszeichen_faellig(datetime(2026, 11, 7, 9, 0), 8, "2026-11-06")


def test_neustart_erkennung():
    assert a.neustart_unerwartet({"start": 1, "lebt": 2, "sauber": False})
    assert not a.neustart_unerwartet({"start": 1, "sauber": True})
    assert not a.neustart_unerwartet(None)        # erster Start überhaupt


def test_dauer_text():
    assert a.dauer_text(15 * 60) == "15 Min"
    assert a.dauer_text(75 * 60) == "1 Std 15 Min"
    assert a.dauer_text(26 * 3600) == "1 Tg 2 Std"


def test_alarm_mail_nennt_grund_im_betreff():
    betreff, text = a.alarm_mail(["VPN-Tunnel ist unten"], [("VPN", "unten")], "07.11.2026 10:00",
                                 "http://nas:8080/admin")
    assert betreff == "🔴 SelfStream: VPN-Tunnel ist unten"
    assert "07.11.2026 10:00" in text and "VPN: unten" in text and "http://nas:8080/admin" in text
    betreff, text = a.alarm_mail(["Anbieter nicht erreichbar (Timeout) – geprüft: ZDF"], [], "x")
    assert betreff == "🔴 SelfStream: Anbieter nicht erreichbar"
    assert "geprüft: ZDF" in text


# ── Segmentlängen aus der Playlist ───────────────────────────────────────────

def test_segment_durations():
    pl = "#EXTM3U\n#EXTINF:6.006,\nseg1.ts\n#EXTINF:5.5,title\nhttp://cdn/x/seg2.ts\nkeine_dauer.ts\n"
    d = segment_durations(pl, "http://host/live/chan/index.m3u8")
    assert d == {"http://host/live/chan/seg1.ts": 6.006, "http://cdn/x/seg2.ts": 5.5}
