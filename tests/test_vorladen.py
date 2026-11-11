"""Tests für das Vorladen (vorladen.py) und den Einstellungs-Zwischenspeicher."""
import database
import vorladen as v

PL = "http://anbieter.example/kanal/mono.m3u8?token=abc"
LISTE = """#EXTM3U
#EXT-X-TARGETDURATION:6
#EXTINF:6.0,
a1.ts?token=abc
#EXTINF:6.0,
a2.ts?token=abc
#EXTINF:6.0,
http://cdn.example/a3.ts
#EXTINF:6.0,
a4.ts?token=abc
"""
BASIS = "http://anbieter.example/kanal/"


# ── Segmente einer Playlist ─────────────────────────────────────────────────

def test_segment_urls_absolut_und_in_reihenfolge():
    assert v.segment_urls(LISTE, PL) == [
        BASIS + "a1.ts?token=abc", BASIS + "a2.ts?token=abc",
        "http://cdn.example/a3.ts", BASIS + "a4.ts?token=abc",
    ]


def test_unterplaylists_sind_keine_segmente():
    master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\ntracks-v1a1/mono.m3u8?token=abc\n"
    assert v.segment_urls(master, PL) == []


def test_leere_playlist():
    assert v.segment_urls("", PL) == []
    assert v.segment_urls(None, PL) == []


# ── Auswahl beim Umschalten ─────────────────────────────────────────────────

def _liste(ziel, dauern):
    zeilen = ["#EXTM3U"] + ([f"#EXT-X-TARGETDURATION:{ziel}"] if ziel else [])
    for i, d in enumerate(dauern, 1):
        zeilen += ([f"#EXTINF:{d},"] if d else []) + [f"s{i}.ts"]
    return "\n".join(zeilen)


def _namen(urls):
    return [u.rsplit("/", 1)[1] for u in urls]


def test_zap_beginnt_drei_zieldauern_vor_dem_ende():
    # So sieht die Playlist des Anbieters aus (11.11.2026): Zieldauer 9, sechs Segmente
    # von rund 6,5 s. 39,1 s − 27 s = 12,1 s → das zweite Segment.
    pl = _liste(9, [6.369, 6.555, 6.555, 6.259, 6.370, 7.037])
    assert _namen(v.zap_auswahl(pl, PL)) == ["s2.ts", "s3.ts"]


def test_zap_bei_gleich_langen_segmenten():
    assert _namen(v.zap_auswahl(_liste(6, [6.0] * 5), PL)) == ["s3.ts", "s4.ts"]


def test_zap_playlist_kuerzer_als_der_abstand_beginnt_vorn():
    assert _namen(v.zap_auswahl(_liste(10, [6.0, 6.0, 6.0]), PL)) == ["s1.ts", "s2.ts"]


def test_zap_ohne_zeitangaben_beginnt_drei_vor_dem_ende():
    assert _namen(v.zap_auswahl(_liste(None, [6.0] * 5), PL)) == ["s3.ts", "s4.ts"]
    assert _namen(v.zap_auswahl(_liste(6, [None] * 5), PL)) == ["s3.ts", "s4.ts"]


def test_zap_leer_und_null():
    assert v.zap_auswahl("", PL) == []
    assert v.zap_auswahl(_liste(6, [6.0] * 5), PL, 0) == []
    assert _namen(v.zap_auswahl(_liste(6, [6.0]), PL)) == ["s1.ts"]


# ── Nachfolger im laufenden Betrieb ─────────────────────────────────────────

def test_naechste_segmente():
    folge = {}
    v.folge_merken(folge, ["s1", "s2", "s3", "s4"])
    assert v.naechste(folge, "s1", 2) == ["s2", "s3"]
    assert v.naechste(folge, "s3", 2) == ["s4"]
    assert v.naechste(folge, "s4", 2) == []
    assert v.naechste(folge, "fremd", 2) == []
    assert v.naechste(folge, "s1", 0) == []


def test_folge_waechst_mit_der_naechsten_playlist():
    folge = {}
    v.folge_merken(folge, ["s1", "s2", "s3"])
    v.folge_merken(folge, ["s2", "s3", "s4"])
    assert v.naechste(folge, "s2", 3) == ["s3", "s4"]


def test_folge_bleibt_begrenzt_und_wirft_das_aelteste_weg():
    folge = {}
    v.folge_merken(folge, [f"s{i}" for i in range(10)], grenze=4)
    assert len(folge) == 4
    assert "s0" not in folge and "s8" in folge


def test_schleife_in_der_folge_endet():
    folge = {"a": "b", "b": "a"}
    assert v.naechste(folge, "a", 5) == ["b"]


# ── Einstellungen werden kurz gemerkt ───────────────────────────────────────

def _db(tmp_path):
    d = database.Database()
    d.db_path = str(tmp_path / "t.db")
    d.init()
    return d


def test_einstellung_schreiben_wirkt_sofort(tmp_path):
    d = _db(tmp_path)
    assert d.get_setting("x", "leer") == "leer"
    d.set_setting("x", "1")
    assert d.get_setting("x") == "1"
    d.set_setting("x", "2")
    assert d.get_setting("x") == "2"


def test_einstellungen_werden_nicht_jedes_mal_gelesen(tmp_path, monkeypatch):
    d = _db(tmp_path)
    d.set_setting("x", "1")
    gezaehlt = []
    echt = d.get_all_settings
    monkeypatch.setattr(d, "get_all_settings", lambda: gezaehlt.append(1) or echt())
    for _ in range(20):
        assert d.get_setting("x") == "1"
    assert len(gezaehlt) == 1


def test_fremde_aenderung_kommt_nach_ablauf_an(tmp_path, monkeypatch):
    d = _db(tmp_path)
    d.set_setting("x", "1")
    assert d.get_setting("x") == "1"
    with d.conn() as con:                     # an set_setting vorbei, wie ein zweiter Prozess
        con.execute("UPDATE settings SET value='9' WHERE key='x'")
    assert d.get_setting("x") == "1"
    monkeypatch.setattr(database, "SETTINGS_CACHE_SEC", 0.0)
    assert d.get_setting("x") == "9"
