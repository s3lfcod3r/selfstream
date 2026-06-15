"""Test-Setup: backend importierbar machen + isolierte Test-Datenbank.

Die Tests brauchen weder Docker noch Netzwerk. Sie sichern das Verhalten der
reinen Hilfsfunktionen und des DB-Layers ab, damit der spätere Umbau von
main.py keine Regressionen einschleppt.
"""
import os
import sys
from pathlib import Path

# DB_PATH auf eine temporäre Datei setzen, BEVOR backend-Module importiert werden
# (database.py liest DB_PATH beim Import; main.py legt beim Import ein Database()-Objekt an).
_TMP_DB = Path(__file__).resolve().parent / "_import_only.db"
os.environ.setdefault("DB_PATH", str(_TMP_DB))

# backend/ in den Importpfad legen
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from database import Database  # noqa: E402


@pytest.fixture
def fresh_db(tmp_path):
    """Frische, leere Datenbank pro Test – komplett isoliert."""
    db = Database()
    db.db_path = str(tmp_path / "test.db")
    db.init()
    return db
