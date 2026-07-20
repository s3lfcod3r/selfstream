# Changelog

## v1.2

Stabilitäts-Release rund um Anbieter-Serverwechsel und VPN. Voll abwärtskompatibel —
keine Konfigurationsänderung nötig, bestehende Tokens/Playlists bleiben gültig.
Die Datenbank wird beim ersten Start automatisch migriert.

### Funktionen
- **Anbieter-Serverwechsel ohne Playlist-Neuladen:** Jeder Kanal bekommt eine
  stabile, serverunabhängige ID; die Geräte-Playlist verweist auf
  `/iptv/{token}/live/{id}` statt auf die fest eingebackene Anbieter-URL. Die
  aktuelle Upstream-URL wird erst beim Abspielen aus der Datenbank aufgelöst.
  Wechselt der Anbieter-Server, genügt ein Klick auf **↻ Aktualisieren** — die
  Geräte müssen nichts mehr neu laden. Alte Playlists (`?url=`) funktionieren
  unverändert weiter; Geräte stellen beim nächsten Neuladen einmalig um.
- **VPN-Ausweichen auf einen anderen Server:** Bringen mehrere Neustarts nichts
  (typisch, wenn der Gegenserver gar nicht mehr antwortet), wechselt der Wächter
  automatisch auf eine andere hochgeladene `.ovpn`. Voraussetzung: mindestens
  zwei Konfigurationen sind hinterlegt.
- **Gehärtete VPN-Verbindung:** Beim Start werden Stabilitäts-Optionen in eine
  Arbeitskopie der Konfiguration geschrieben (die Original-Datei bleibt
  unangetastet): kürzere Wiederholungspausen (`connect-retry 5 30` statt bis zu
  300 s), schnelleres Umschalten bei mehreren `remote`-Einträgen
  (`server-poll-timeout 15`), `resolv-retry infinite` sowie `remote-cert-tls
  server` anstelle des veralteten `ns-cert-type`.

### Fehlerbehebungen
- **VPN-Wächter erkannte echte Ausfälle nicht:** Die Gesundheitsprüfung war
  „Prozess lebt **und** tun0 hat eine IP". Beides überlebt einen weichen
  OpenVPN-Neustart (`SIGUSR1[soft,tls-error]`) — der Prozess beendet sich nicht,
  und durch `persist-tun` behält die Schnittstelle ihre alte IP. Ein toter Tunnel
  galt damit als gesund, der Wächter griff nie ein. Der Verbindungszustand wird
  jetzt aus den Meldungen von OpenVPN selbst abgeleitet
  (`Initialization Sequence Completed` gegenüber `TLS Error` / `Restart pause`).
- **Gruppen-Reihenfolge stimmte nicht mit der Nummerierung überein:** Zwei
  getrennte Sortier-Regler schrieben in unterschiedliche Quellen — die
  tatsächliche Reihenfolge kam von der Gruppen-Seite, die Nummern „01./02."
  jedoch aus dem Benutzer-Dialog. Jetzt speist sich beides aus derselben Quelle
  (Gruppen-Seite → „Gruppen-Reihenfolge"); der widersprüchliche Regler im
  Benutzer-Dialog wurde entfernt.
- **Playlist konnte veraltet ausgeliefert werden:** Die Antwort trug keine
  Cache-Vorgaben, sodass Player oder zwischengeschaltete Proxys eine alte Liste
  behalten konnten. Sie wird jetzt mit `Cache-Control: no-cache, no-store,
  must-revalidate` ausgeliefert.
- **Speedtest maß den Anbieter systematisch zu langsam:** Die Datenmenge aller
  Segmente wurde durch die Gesamtdauer geteilt — also auch durch Zeit, in der
  bereits fertige Segmente längst nichts mehr luden; fehlgeschlagene Segmente
  gingen als 0 Byte ein, während die Uhr weiterlief. Ergebnis war die falsche
  Meldung „IPTV-Anbieter ist der Flaschenhals". Jetzt misst jedes Segment seine
  eigene Zeit; ausgewiesen werden der Median je Verbindung (vergleichbar mit dem
  Internet-Test), zusätzlich Bestwert, Parallel-Summe und die Zahl
  fehlgeschlagener Segmente.
- **Datenbank-Migration brach bestehende Installationen:** Der Index auf die neue
  Kanal-Spalte wurde im Erstellungs-Skript angelegt, wo die Spalte auf einer
  bestehenden Datenbank noch nicht existierte („no such column"). Dadurch schlug
  der Anbieter-Abruf mit `table channels has no column named stable_uid` fehl.
  Der Index wird jetzt erst nach dem Hinzufügen der Spalte erzeugt.

## v1.1

Sicherheits- und Stabilitäts-Release. Voll abwärtskompatibel — keine
Konfigurationsänderung nötig, bestehende Tokens/Logins bleiben gültig.

### Funktionen
- **„Max. Streams erreicht"- und „Gesperrt"-Anzeige als echtes Video:** Öffnet ein
  Nutzer mehr gleichzeitige Streams als erlaubt (oder ist der Zugang gesperrt),
  spielt der Player jetzt einen kurzen Hinweis-**Clip** ab. Vorher wurde ein
  JPEG ausgeliefert, das VLC/Tablet-Player als HLS-„Segment" übersprungen haben –
  daher kam beim Nutzer keine Meldung an. Die Clips sind vorgerenderte MPEG-TS-
  Dateien (`backend/assets/*.ts`, erzeugt mit `tools/gen_error_clips.py`) und
  werden statisch ausgeliefert: **kein ffmpeg im Container, keine Laufzeit-CPU-Last.**
  Das Umschalten auf demselben Gerät löst weiterhin keine Sperre aus.

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
