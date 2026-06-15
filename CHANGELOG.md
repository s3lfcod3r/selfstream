# Changelog

## v1.1

Sicherheits- und Stabilitäts-Release. Voll abwärtskompatibel — keine
Konfigurationsänderung nötig, bestehende Tokens/Logins bleiben gültig.

### Sicherheit
- **SSRF-Schutz:** Der öffentliche Proxy (`/iptv/{token}/stream` und `/segment`)
  prüft Ziel-URLs jetzt vor dem Abruf. Nur `http`/`https`; interne/private Ziele
  (Loopback, RFC-1918, Link-Local `169.254.*`, Multicast, reservierte Bereiche)
  werden blockiert.
- **Admin-Token gehasht:** Der Admin-Token wird nicht mehr im Klartext in der DB
  gespeichert, sondern als PBKDF2-HMAC-SHA256-Hash. Bestehende Klartext-Tokens
  werden beim nächsten erfolgreichen Login **automatisch migriert** — kein
  Aussperren, kein Neu-Setup.
- **Short-Token kryptografisch sicher:** `secrets` statt `random` (Short-URLs sind
  öffentlich). Endlosschleife bei Kollision durch Abbruchlimit ersetzt.
- **Brute-Force-Schutz** nutzt jetzt die echte Verbindungs-IP statt des fälschbaren
  `X-Forwarded-For`-Headers; abgelaufene Sperren werden aufgeräumt.
- **CORS** entschärft (`allow_credentials=false`; die App nutzt Header-Token, keine
  Cookies).
- **Security-Header** auf allen Antworten: `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`.
- **Logo-Upload/-Delete** validiert den Typ (`login`/`app`) gegen eine Whitelist
  (vorher Pfad-Manipulation möglich).

### Fehlerbehebungen
- **Gruppen-Mapping löschen:** Kanäle erhalten beim Löschen einer Gruppen-
  Umbenennung wieder ihren Original-Gruppennamen (Reihenfolge der DB-Operationen
  korrigiert).
- **Admin-Panel:** Namen mit Apostroph (z.B. `Sport's Best`) zerschießen die
  Buttons nicht mehr; `esc()` escaped jetzt auch `'` und `` ` `` (behebt zugleich
  eine XSS-Lücke in `onclick`-Handlern).

### Deployment / Tooling
- `setup.sh`: korrekter Admin-Port (8080) in der Abschlussmeldung,
  `set -euo pipefail`, Image-Pull statt `--build`.
- `docker-compose.yml`: liest `ADMIN_TOKEN`/`BASE_URL`/`PROXY_URL` jetzt aus einer
  `.env` (die `setup.sh` anlegt) — vorher kamen diese Werte nie im Container an.
- `update.sh`: `set -euo pipefail`, `docker cp`-Fehler werden nicht mehr verschluckt.
- `.gitignore`: irreführende Zeile entfernt; `.venv/`/`.pytest_cache/` ergänzt.
- Unraid-Template: `Privileged=false` (für VPN reichen `NET_ADMIN` + `/dev/net/tun`).
  Betrifft nur Neu-Installationen aus dem Template.

### Code-Qualität
- Reine Hilfsfunktionen in eigene Module ausgelagert: `timeparse.py`
  (Zeit-/EPG-Parser), `hls.py` (Playlist-Rewrite), `security_util.py`
  (SSRF + Token-Hashing).
- **Test-Suite eingeführt** (`tests/`, 43 Tests): M3U-Parser, Zeit-/HLS-Logik,
  DB-Layer, Sicherheit (SSRF/Auth/Hashing) und Catchup-/Session-Logik.

### Offen / zurückgestellt
- VPN-Passwort-Schwärzung in der API + OVPN-`script-security`-Härtung
  (LAN-only Admin-Panel; brauchen koordinierte Frontend-Änderung).
- Vollständige Aufteilung von `main.py` in Routen-Module → geplant für **v1.2**
  (jetzt mit Test-Sicherheitsnetz machbar).
