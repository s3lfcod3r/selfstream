# AGENTS.md — selfstream

Kurze Orientierung fuer KI-Assistenten (Bonsai/Claude). **Diese Datei zuerst lesen, nicht die grosse README.**
Zum Finden: `rg -n "BEGRIFF"`. Fuer Symbole: Serena `get_symbols_overview`/`find_symbol`. Grosse Dateien nur zeilenweise (`sed -n`).

## Typ & Stack

- Python: `backend/requirements.txt`

## Bauen / Testen / Starten

```bash
uvicorn <modul>:app   # FastAPI-Server (Details: Dockerfile/README)
python -m pytest -q   # falls Tests vorhanden
```

## Struktur (oberste Ebenen)

- `.github/` — CI/Workflows
- `assets/`
- `backend/` — Server (API)
- `frontend/` — Web-Oberflaeche
- `tests/` — Tests
- `unraid/`

---
*Automatisch erzeugt als Navigationshilfe. Bei Bedarf von Hand praeziser machen.*
