"""Tests für die Qualitätsauswertung (qualitaet.py)."""
import qualitaet as q


# ── Stufe und Reserve ───────────────────────────────────────────────────────

def test_stufe_misst_an_der_spielzeit():
    assert q.stufe(2.5, 6.0) == "ok"         # früher „langsam (>2 s)“, läuft aber flüssig
    assert q.stufe(4.0, 6.0) == "delayed"
    assert q.stufe(6.5, 6.0) == "slow"


def test_stufe_ohne_spielzeit_nutzt_sekundengrenzen():
    assert q.stufe(1.0, None) == "ok"
    assert q.stufe(2.0, None) == "delayed"
    assert q.stufe(3.5, 0) == "slow"


def test_reserve():
    assert q.reserve(0.5, 6.0) == 12.0
    assert q.reserve(6.0, 6.0) == 1.0
    assert q.reserve(0.0, 6.0) == q.RESERVE_MAX
    assert q.reserve(0.001, 6.0) == q.RESERVE_MAX
    assert q.reserve(1.0, None) is None
    assert q.reserve(None, 6.0) is None


def test_ampel():
    assert q.ampel(12.0) == "gut"
    assert q.ampel(1.3) == "knapp"
    assert q.ampel(0.8) == "schlecht"
    assert q.ampel(None) == "unbekannt"


# ── Wer schaut gerade ───────────────────────────────────────────────────────

def _p(ts, user, elapsed, rueck, cached=False, dur=6.0, channel="RTL HD", skip=0, kb=4000):
    return {"ts": ts, "user": user, "channel": channel, "elapsed": elapsed,
            "dur": dur, "rueck": rueck, "cached": cached, "skip": skip, "kb": kb}


def test_zuschauer_mbit_tempo_und_bedarf():
    # 2 × 3000 KB in je 0,5 s geholt, je 6 s Spielzeit
    z = q.zuschauer([_p(100, "Sven", 0.5, 0, kb=3000), _p(106, "Sven", 0.5, 0, kb=3000)], jetzt=110)[0]
    assert z["rein_mbps"] == 49.2       # 6000 KB × 8 ÷ 1 s
    assert z["bedarf_mbps"] == 4.1      # 6000 KB × 8 ÷ 12 s


def test_zuschauer_mbit_ohne_eigenen_abruf():
    # Segment lag schon bereit: kein Abhol-Tempo, aber der Verbrauch steht fest.
    z = q.zuschauer([_p(100, "Sven", 0.0, 0, cached=True, kb=3000)], jetzt=110)[0]
    assert z["rein_mbps"] is None and z["bedarf_mbps"] == 4.1


def _m(minute, mb=30, s=1.0, n=5, spaet=0, geliefert_mb=30):
    return {"minute": minute, "geholt_bytes": mb * 1_000_000, "geholt_s": s, "geholt_n": n,
            "spaet": spaet, "geliefert_bytes": geliefert_mb * 1_000_000}


def test_verlauf_je_minute():
    jetzt = 1000 * 60 + 30                       # Minute 1000
    v = q.verlauf([_m(999), _m(1000, mb=15, s=1.0, spaet=2)], jetzt, minuten=3)
    assert [x["t"] // 60 for x in v] == [998, 999, 1000]
    assert v[0]["mbps"] is None and v[0]["verbrauch"] == 0.0
    assert v[1]["mbps"] == 240.0 and v[1]["verbrauch"] == 4.0     # 30 MB in 1 s geholt; 30 MB in 60 s verbraucht
    assert v[2]["mbps"] == 120.0 and v[2]["spaet"] == 2


def test_verlauf_fasst_zusammen_wenn_es_mehr_minuten_als_punkte_sind():
    jetzt = 1000 * 60
    zeilen = [_m(m) for m in range(881, 1001)]   # 120 Minuten
    v = q.verlauf(zeilen, jetzt, minuten=120, punkte=60)
    assert len(v) == 60 and v[0]["min"] == 2
    assert v[-1]["mbps"] == 240.0 and v[-1]["n"] == 10 and v[-1]["verbrauch"] == 4.0


def test_verlauf_ohne_daten():
    v = q.verlauf([], 1000 * 60, minuten=60)
    assert len(v) == 60 and all(x["mbps"] is None and x["n"] == 0 for x in v)


def test_rueckstand_nimmt_den_kleinsten_der_letzten_drei():
    assert q.rueckstand([0, 1, 0]) == 0          # das übliche Schwanken um ein Segment
    assert q.rueckstand([0, 1, 2, 2, 3]) == 2    # fällt wirklich zurück
    assert q.rueckstand([2, 2]) is None          # noch zu wenige Anfragen
    assert q.rueckstand([None, 1, 1, 1]) == 1
    assert q.rueckstand([]) is None


def test_rueck_ampel():
    assert q.rueck_ampel(0) == "gut"
    assert q.rueck_ampel(1) == "gut"             # ein Segment über dem Bestwert ist normal
    assert q.rueck_ampel(2) == "knapp"
    assert q.rueck_ampel(3) == "schlecht"
    assert q.rueck_ampel(None) == "unbekannt"


def test_rueck_ampel_mit_uebersprungenen_segmenten():
    assert q.rueck_ampel(0, 1) == "knapp"
    assert q.rueck_ampel(0, 2) == "schlecht"
    assert q.rueck_ampel(None, 3) == "schlecht"      # zählt auch ohne gesicherten Rückstand


def test_zuschauer_ueberspringt_segmente():
    z = q.zuschauer([_p(100, "Dennis", 0.5, 0, skip=2), _p(106, "Dennis", 0.5, 0)], jetzt=110)
    assert z[0]["urteil"] == q.GERAET_URTEIL and z[0]["skips"] == 2 and z[0]["level"] == "schlecht"


def test_zuschauer_fluessig():
    z = q.zuschauer([_p(100, "Sven", 0.5, 0), _p(106, "Sven", 0.4, 0)], jetzt=110)
    assert z[0]["user"] == "Sven" and z[0]["urteil"] == "flüssig"
    assert z[0]["rein"] == 13.5 and z[0]["rueck"] == 0


def test_zuschauer_geraet_kommt_nicht_hinterher():
    z = q.zuschauer([_p(100, "Dennis", 0.5, 0), _p(106, "Dennis", 0.5, 3)], jetzt=110)
    assert z[0]["urteil"] == q.GERAET_URTEIL
    assert z[0]["rein_level"] == "gut" and z[0]["rueck_level"] == "schlecht"


def test_zuschauer_ein_segment_zurueck_ist_fluessig():
    z = q.zuschauer([_p(100, "Sven", 0.5, 1), _p(106, "Sven", 0.5, 1)], jetzt=110)
    assert z[0]["urteil"] == "flüssig" and z[0]["rueck_level"] == "gut"


def test_zuschauer_es_zaehlt_der_neueste_rueckstand():
    z = q.zuschauer([_p(100, "Dennis", 0.5, 3), _p(106, "Dennis", 0.5, 0)], jetzt=110)
    assert z[0]["urteil"] == "flüssig"           # hat wieder aufgeholt


def test_zuschauer_anlieferung_langsam_geht_vor():
    z = q.zuschauer([_p(100, "Sven", 7.0, 2), _p(106, "Sven", 8.0, 2)], jetzt=110)
    assert z[0]["urteil"] == "Anlieferung langsam" and z[0]["level"] == "schlecht"


def test_zwischenspeicher_zaehlt_nicht_fuer_die_anlieferung():
    z = q.zuschauer([_p(100, "Sven", 0.0, 0, cached=True)], jetzt=110)
    assert z[0]["rein"] is None and z[0]["urteil"] == "flüssig"


def test_ohne_rueckstand_und_ohne_anlieferung_keine_messung():
    z = q.zuschauer([_p(100, "Sven", 0.0, None, cached=True)], jetzt=110)
    assert z[0]["urteil"] == "noch keine Messung"


def test_alte_proben_zaehlen_nicht():
    assert q.zuschauer([_p(100, "Sven", 0.5, 0)], jetzt=100 + q.ZUSCHAUER_FENSTER + 1) == []


# ── Störungen ───────────────────────────────────────────────────────────────

def _e(ts, typ="slow", user="Sven", channel="RTL HD"):
    return {"ts": ts, "type": typ, "user": user, "channel": channel}


def test_ein_sender_ist_ein_sender_problem():
    r = q.stoerungen([_e(100), _e(110), _e(130)])
    assert len(r["stoerungen"]) == 1
    s = r["stoerungen"][0]
    assert s["ursache"] == "sender" and s["anzahl"] == 3 and s["dauer"] == 30


def test_mehrere_sender_ohne_probe_bleibt_offen():
    r = q.stoerungen([_e(100), _e(105, channel="VOX HD", user="Dennis"), _e(108)])
    assert r["stoerungen"][0]["ursache"] == "netz"
    assert r["stoerungen"][0]["nutzer_anzahl"] == 2


def test_mehrere_sender_mit_schneller_probe_ist_der_anbieter():
    r = q.stoerungen([_e(100), _e(105, channel="VOX HD"), _e(108)], [{"ts": 120, "mbps": 300.0}])
    assert r["stoerungen"][0]["ursache"] == "anbieter"
    assert r["stoerungen"][0]["probe_mbps"] == 300.0


def test_mehrere_sender_mit_langsamer_oder_gescheiterter_probe_ist_das_vpn():
    ereignisse = [_e(100), _e(105, channel="VOX HD"), _e(108)]
    assert q.stoerungen(ereignisse, [{"ts": 120, "mbps": 4.0}])["stoerungen"][0]["ursache"] == "vpn"
    assert q.stoerungen(ereignisse, [{"ts": 120, "mbps": None}])["stoerungen"][0]["ursache"] == "vpn"


def test_probe_von_einem_anderen_tag_zaehlt_nicht():
    r = q.stoerungen([_e(100), _e(105, channel="VOX HD"), _e(108)], [{"ts": 90000, "mbps": 300.0}])
    assert r["stoerungen"][0]["ursache"] == "netz"


def test_luecke_trennt_stoerungen_und_neueste_steht_oben():
    r = q.stoerungen([_e(100), _e(110), _e(120), _e(1000), _e(1010), _e(1020)])
    assert [s["von"] for s in r["stoerungen"]] == [1000, 100]


def test_zwei_spaete_stuecke_sind_noch_keine_stoerung():
    r = q.stoerungen([_e(100), _e(105, channel="VOX HD")])
    assert r["stoerungen"] == [] and r["einzelne"] == 2


def test_einzelner_aussetzer_ist_keine_stoerung():
    r = q.stoerungen([_e(100), _e(5000)])
    assert r["stoerungen"] == [] and r["einzelne"] == 2


def test_geraete_strecke_wird_je_nutzer_gebuendelt():
    r = q.stoerungen([_e(100, "geraet", "Dennis"), _e(110, "geraet", "Dennis"),
                      _e(120, "geraet", "Dennis"), _e(105, "geraet", "Sven")])
    assert [(s["ursache"], s["nutzer"]) for s in r["stoerungen"]] == [("geraet", ["Dennis"])]
    assert r["einzelne"] == 1


# ── Rangliste ───────────────────────────────────────────────────────────────

def test_rangliste_nach_anteil_nicht_nach_menge():
    r = q.rangliste([
        {"channel": "RTL HD", "gesamt": 5000, "spaet": 10},
        {"channel": "VOX HD", "gesamt": 1000, "spaet": 20},
        {"channel": "VOX HD", "gesamt": 900, "spaet": 18},     # zweiter Tag
        {"channel": "Selten", "gesamt": 10, "spaet": 5},        # zu wenig Segmente
    ])
    assert [(x["channel"], x["anteil"]) for x in r] == [("VOX HD", 2.0), ("RTL HD", 0.2)]
    assert r[0]["gesamt"] == 1900 and r[0]["spaet"] == 38


# ── Urteil ──────────────────────────────────────────────────────────────────

def test_urteil_tunnel_steht_nicht():
    assert q.urteil("ok", True, False, None, False, [])["level"] == "schlecht"


def test_urteil_anbieter_langsam_vpn_schnell():
    u = q.urteil("bad", True, True, 300.0, True, [])
    assert u["level"] == "schlecht" and "Anbieter liefert langsam" in u["text"]


def test_urteil_vpn_langsam():
    assert "VPN" in q.urteil("slow", True, True, 3.0, True, [])["text"]
    assert q.urteil("slow", True, True, None, True, [])["level"] == "knapp"


def test_urteil_ohne_probe_legt_sich_nicht_fest():
    assert "noch nicht gemessen" in q.urteil("bad", True, True, None, False, [])["text"]


def test_urteil_nur_ein_geraet_knapp():
    u = q.urteil("ok", True, True, None, False, ["Dennis"])
    assert u["level"] == "knapp" and "Dennis" in u["text"]


def test_urteil_alles_gut_und_niemand_schaut():
    assert q.urteil("ok", True, True, None, False, [])["text"] == "Alles flüssig."
    assert q.urteil(None, False, False, None, False, [])["level"] == "unbekannt"
