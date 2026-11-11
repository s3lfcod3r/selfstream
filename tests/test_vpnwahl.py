"""Tests für die Auto-Best-Logik (vpnwahl.py)."""
import vpnwahl as v


def _h(level="ok", median=0.3, mbps=300.0, err=0.0, n=10):
    return {"level": level, "median_s": median, "mbps": mbps, "err_rate": err, "samples": n}


# ── Wann gesucht wird ───────────────────────────────────────────────────────

def test_niemand_schaut_keine_notsuche():
    assert v.suche_noetig({"level": None}, 20) == (False, "")


def test_schneller_server_braucht_keine_suche():
    assert v.suche_noetig(_h(), 20) == (False, "")


def test_berlin_fall_wird_erkannt():
    # 07.11.2026: Segmente 3–4 s bei 8 Mbit/s – kein „Ruckeln“, aber zähes Umschalten.
    noetig, grund = v.suche_noetig(_h(level="ok", median=3.5, mbps=8.3), 20)
    assert noetig and "3.5 s" in grund


def test_wenig_mbit_reicht_als_grund():
    noetig, grund = v.suche_noetig(_h(median=1.0, mbps=12.0), 20)
    assert noetig and "12.0 Mbit/s" in grund


def test_mbit_regel_braucht_genug_proben():
    assert not v.suche_noetig(_h(median=1.0, mbps=12.0, n=2), 20)[0]


def test_fehler_und_ruckeln():
    assert v.suche_noetig(_h(err=0.2), 20)[0]
    assert v.suche_noetig(_h(level="bad"), 20) == (True, "Wiedergabe ruckelt")


# ── Wie gemessen wird ───────────────────────────────────────────────────────

def test_haenger_zaehlt_als_null():
    # Berlin: schnell, aber hängt zwischendurch → schlechter als stabil langsamer
    assert v.messung_werten([600, None, 400]) == 0.0
    assert v.messung_werten([300, 320, 310]) == 300.0
    assert v.messung_werten([]) == 0.0


# ── Wer gewinnt ─────────────────────────────────────────────────────────────

def test_notfall_nimmt_schnellsten():
    assert v.besten_waehlen(8.0, {"fra-001": 450.0, "fra-201": 300.0}, notfall=True) == "fra-001"


def test_notfall_wechselt_nicht_fuer_kaum_besser():
    assert v.besten_waehlen(100.0, {"fra-001": 110.0}, notfall=True) is None


def test_haengender_aktueller_wird_ersetzt():
    assert v.besten_waehlen(0.0, {"fra-001": 50.0}, notfall=False) == "fra-001"


def test_routine_laesst_guten_server_in_ruhe():
    assert v.besten_waehlen(100.0, {"fra-001": 170.0}, notfall=False) is None


def test_routine_wechselt_bei_deutlichem_vorsprung():
    # Keiner schafft das Ziel (200): dann zählt nur ein deutlicher Vorsprung (×1,5).
    assert v.besten_waehlen(60.0, {"fra-001": 100.0}, notfall=False, ziel=200) == "fra-001"
    assert v.besten_waehlen(60.0, {"fra-001": 80.0}, notfall=False, ziel=200) is None
    # Seit 1.92: Schafft der andere das Ziel und der aktuelle nicht, wird gewechselt.
    assert v.besten_waehlen(60.0, {"fra-001": 80.0}, notfall=False, ziel=80) == "fra-001"


def test_keiner_erreichbar():
    assert v.besten_waehlen(5.0, {"a": 0.0, "b": 0.0}, notfall=True) is None
    assert v.besten_waehlen(5.0, {}, notfall=True) is None


# ── Ziel aus der Nutzerzahl, Gedächtnis, Reihenfolge (1.92) ─────────────────

def test_ziel_waechst_mit_den_nutzern():
    assert v.ziel_mbps(11) == 165.0
    assert v.ziel_mbps(8) == 120.0
    assert v.ziel_mbps(0) == 0.0
    assert v.ziel_mbps(4, je_stream=8, reserve_prozent=25) == 40.0


def test_routine_bleibt_wenn_das_ziel_erreicht_ist():
    assert v.besten_waehlen(190, {"b": 600}, notfall=False, ziel=165) is None


def test_routine_wechselt_wenn_nur_ein_anderer_das_ziel_schafft():
    assert v.besten_waehlen(140, {"b": 170, "c": 150}, notfall=False, ziel=165) == "b"


def test_routine_keiner_schafft_das_ziel_dann_nur_bei_deutlichem_vorsprung():
    assert v.besten_waehlen(100, {"b": 120}, notfall=False, ziel=165) is None
    assert v.besten_waehlen(100, {"b": 155}, notfall=False, ziel=165) == "b"


def test_reihenfolge_zuletzt_schnellster_zuerst():
    g = {"b": {"mbps": 150, "ts": 1000}, "c": {"mbps": 300, "ts": 1000},
         "d": {"mbps": 0, "ts": 1000}, "alt": {"mbps": 900, "ts": 1000 - v.GEDAECHTNIS_ALTER - 1}}
    assert v.reihenfolge(["a", "alt", "b", "c", "d"], g, jetzt=1000) == ["c", "b", "a", "alt", "d"]


def test_reihenfolge_ohne_gedaechtnis_bleibt_wie_sie_ist():
    assert v.reihenfolge(["a", "b"], {}, jetzt=1000) == ["a", "b"]
    assert v.reihenfolge([], None, jetzt=1000) == []


def test_gedaechtnis_merken_aendert_das_original_nicht():
    alt = {"a": {"mbps": 1.0, "ts": 1}}
    neu = v.gedaechtnis_merken(alt, "b", 222.24, 500.9)
    assert neu == {"a": {"mbps": 1.0, "ts": 1}, "b": {"mbps": 222.2, "ts": 500}}
    assert "b" not in alt


def test_notfall_reicht_erst_wenn_klar_besser_und_bedarf_gedeckt():
    assert v.notfall_reicht(130, 100, 30)
    assert not v.notfall_reicht(110, 100, 30)      # kein klarer Vorsprung
    assert not v.notfall_reicht(25, 10, 30)        # deckt den Bedarf nicht
    assert not v.notfall_reicht(0, 0, 0)


def test_ersatz_bei_totem_tunnel():
    g = {"b": {"mbps": 150, "ts": 1000}, "c": {"mbps": 300, "ts": 1000}}
    assert v.ersatz_waehlen(["b", "c", "x"], g, jetzt=1000) == "c"
    assert v.ersatz_waehlen(["x", "y"], {}, jetzt=1000) == "x"
    assert v.ersatz_waehlen([], {}, jetzt=1000) is None
