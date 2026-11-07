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
    assert v.besten_waehlen(60.0, {"fra-001": 100.0}, notfall=False) == "fra-001"
    assert v.besten_waehlen(60.0, {"fra-001": 80.0}, notfall=False) is None


def test_keiner_erreichbar():
    assert v.besten_waehlen(5.0, {"a": 0.0, "b": 0.0}, notfall=True) is None
    assert v.besten_waehlen(5.0, {}, notfall=True) is None
