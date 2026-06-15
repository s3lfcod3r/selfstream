"""DB-Layer-Tests gegen eine isolierte temporäre SQLite-Datenbank.

Enthält u.a. den Regressions-Test für den delete_group_mapping-Bug.
"""
import string


def _add_channel(db, name, group_title, url):
    with db.conn() as con:
        con.execute(
            "INSERT INTO channels (name, group_title, stream_url) VALUES (?, ?, ?)",
            (name, group_title, url),
        )


def test_create_and_get_user(fresh_db):
    user = fresh_db.create_user(name="Max", token="tok123", m3u_source="http://src")
    assert user["id"] > 0
    fetched = fresh_db.get_user_by_token("tok123")
    assert fetched is not None
    assert fetched["name"] == "Max"
    assert fetched["active"] == 1


def test_short_token_unique_and_alphanumeric(fresh_db):
    u1 = fresh_db.create_user(name="A", token="t-a", m3u_source="x")
    u2 = fresh_db.create_user(name="B", token="t-b", m3u_source="x")
    s1 = fresh_db.generate_short_token(u1["id"])
    s2 = fresh_db.generate_short_token(u2["id"])
    valid = set(string.ascii_letters + string.digits)
    assert len(s1) == 8 and len(s2) == 8
    assert s1 != s2
    assert all(c in valid for c in s1 + s2)


def test_short_token_high_uniqueness(fresh_db):
    # 100 Tokens sollten praktisch immer eindeutig sein (Kollisionsschutz greift in DB)
    tokens = set()
    for i in range(100):
        u = fresh_db.create_user(name=f"U{i}", token=f"tok{i}", m3u_source="x")
        tokens.add(fresh_db.generate_short_token(u["id"]))
    assert len(tokens) == 100


def test_update_user_ignores_unknown_fields(fresh_db):
    u = fresh_db.create_user(name="X", token="tx", m3u_source="s")
    fresh_db.update_user(u["id"], {"notes": "hallo", "evil_col": "drop"})
    assert fresh_db.get_user_by_token("tx")["notes"] == "hallo"


def test_rename_group_updates_channels(fresh_db):
    _add_channel(fresh_db, "C1", "Sport", "http://p/1")
    fresh_db.rename_group("Sport", "Sport HD")
    assert fresh_db.get_channel_by_name("C1")["group_title"] == "Sport HD"
    mappings = {m["original_name"]: m["custom_name"]
                for m in fresh_db.get_group_mappings()}
    assert mappings.get("Sport") == "Sport HD"


def test_delete_group_mapping_reverts_channel_group(fresh_db):
    """Regression: Nach dem Löschen einer Gruppen-Umbenennung muss der Kanal
    wieder seinen ORIGINAL-Gruppennamen tragen (vorher Bug: blieb auf custom)."""
    _add_channel(fresh_db, "C1", "Sport", "http://p/1")
    fresh_db.rename_group("Sport", "Sport HD")
    assert fresh_db.get_channel_by_name("C1")["group_title"] == "Sport HD"

    fresh_db.delete_group_mapping("Sport")

    assert fresh_db.get_channel_by_name("C1")["group_title"] == "Sport"
    assert fresh_db.get_group_mappings() == []
