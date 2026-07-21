# Changelog

## v1.16

### Funktionen
- **Neue Anbieter-Server automatisch entdecken:** SelfStream führt jetzt ein
  **Server-Register** (welche Server schon gesehen wurden) und sucht **automatisch
  nach neuen**: Beim Server-Vergleich und einmal täglich im Hintergrund werden auch
  nummerierte Server **über die höchste bekannte Nummer hinaus** geprobt. Taucht ein
  neuer Server auf, gibt es einen Hinweis – im Server-Vergleich als **„🆕 Neu
  entdeckt: …"**-Banner und zusätzlich in der Diagnose (Frühwarnung). So verpasst du
  keinen neuen, evtl. schnelleren Server. Generisch (keine anbieterspezifischen
  Server im Code); der Hintergrund-Check lässt bei fast vollem Verbindungslimit aus.

### Funktionen
- **Bevorzugter Server erzwingen:** Neues Feld im Server-Vergleich. Trägst du dort
  einen Server ein (z.B. `6` oder `6.example.net`), schreibt SelfStream beim
  Abspielen **alle Kanäle auf diesen Server um** – unabhängig davon, welchen Server
  die Anbieter-Playlist ausgibt. Damit kannst du auf einen latenzärmeren Server
  wechseln, auch wenn dein Anbieter-Panel das nicht zulässt (der Token bleibt
  erhalten). Gilt **sofort** und dank der stabilen Kanal-IDs (`/live`) **ohne
  Geräte-Neuladen**. Leeres Feld = aus (Anbieter-Standard). Wirkt nur für Live,
  Catchup bleibt unberührt.

### Verbesserungen
- **Server-Vergleich: Mbit/s-Spalte klarer:** Die Mbit/s im Server-Vergleich sind
  nur eine **grobe Einzelverbindungs-Stichprobe** und sinken schon physikalisch mit
  steigender Latenz – sie sagen nichts über die echte Kapazität. Das ist jetzt
  deutlich gekennzeichnet („Mbit/s (grob)") plus Hinweis, dass die **Latenz**
  entscheidet und die echte Kapazität im Haupt-Speedtest (8 Streams parallel) steht.

## v1.13

### Verbesserungen
- **Server-Vergleich: ganze Domains eintragbar:** Im Feld kannst du jetzt die
  **kompletten Server-Domains** eintragen (einen pro Zeile oder per Komma, z.B.
  `de.example.net`) – auch ganze URLs werden akzeptiert (es wird nur der Host
  genommen). Kurze Kürzel (`de`, `2`) funktionieren weiterhin und werden an die
  Domain deines aktuellen Servers gehängt. Das Eingabefeld ist jetzt mehrzeilig.

## v1.12

### Verbesserungen
- **Server-Vergleich: Server selbst eintragen:** Die zu vergleichenden Server
  trägst du jetzt selbst in ein Feld ein (Kürzel wie `de`, `nl`, `2` oder ganze
  Hostnamen) – es sind **keine anbieterspezifischen Server im Code hinterlegt**.
  Damit funktioniert der Vergleich mit jedem Anbieter/Setup, und im Repository
  landen keine Angaben zu einem bestimmten Anbieter.

## v1.11

### Funktionen
- **Server-Vergleich (beste Latenz finden):** Neuer Knopf im Speedtest. Probiert die
  von dir eingetragenen Server durch dein VPN, indem er sie in eine echte Kanal-URL
  einsetzt, und misst pro Server **Latenz + kurzen Durchsatz**. So findest du den
  Server mit der **niedrigsten Latenz von deinem VPN-Ausgang aus** – der direkte
  Hebel gegen träges Zappen (hohe Latenz kommt oft vom weit entfernten Server, nicht
  vom VPN). Server, deren Token an einen festen Server gebunden ist, werden als
  „nicht nutzbar" ausgewiesen; dann ist die Umstellung nur im Anbieter-Panel möglich.

## v1.10

### Verbesserungen
- **Hintergrund-Stichprobe stört Zuschauer garantiert nicht:** Die automatische
  Verlaufs-Messung nutzt jetzt nur noch **eine** Anbieter-Verbindung (statt zwei)
  und setzt weiterhin komplett aus, wenn das Verbindungslimit fast voll ist. Damit
  kann sie das Limit nie füllen und keinen laufenden Stream verdrängen. (Die
  **manuellen** Tests – Speedtest, VPN-Vergleich, Kapazitätstest – können Zuschauer
  weiterhin kurz stören; dafür gibt es die Warnhinweise, sie am besten bei wenig
  Betrieb zu starten.)

## v1.9

### Verbesserungen
- **VPN-Server-Vergleich rankt jetzt sinnvoll:** Vorher verglich er die Server über
  den Internet-Speedtest – der ist durchs VPN aber unzuverlässig (gedrosselte/
  blockierte VPN-IPs), die Rangliste war also kaum aussagekräftig. Jetzt misst er
  pro Server den **IPTV-Anbieter-Durchsatz + Latenz** und rankt danach – also genau
  danach, wie gut deine Streams über den jeweiligen Server laufen.
- **Latenz & Jitter werden gemessen:** Ruckeln kommt oft nicht von zu wenig
  Bandbreite, sondern von hoher Latenz oder Schwankung. Der IPTV-Test zeigt jetzt
  **Latenz + Jitter** zum Anbieter und warnt bei unruhiger Verbindung („kann trotz
  genug Speed ruckeln").
- **Stabilere Messung:** Der IPTV-Test misst pro Stream über **mehrere Segmente**
  statt eines einzigen winzigen Häppchens (das in <1 s durch war) – die Werte
  schwanken dadurch deutlich weniger.
- **Automatischer Verlauf + Frühwarnung:** SelfStream nimmt im Hintergrund alle
  5 Minuten eine **leichte Stichprobe** (Latenz, Durchsatz, VPN-Zustand) und führt
  einen **Verlauf über 24 h** – so werden **intermittierende** Probleme sichtbar
  (z.B. „abends langsam"), die ein einzelner Handtest verpasst. Neuer Knopf
  „Verlauf anzeigen" mit einer Balken-Grafik; anhaltende Probleme landen zusätzlich
  in der Diagnose. Die Stichprobe wird bei fast vollem Verbindungslimit ausgelassen,
  um Zuschauer nicht zu stören.

## v1.8

### Funktionen
- **Anbieter-Kapazitätstest (1–20 Streams):** Neuer Knopf im Speedtest. Misst den
  IPTV-Anbieter mit **steigend vielen gleichzeitigen Streams** (1, 2, 4, 8, 12, 16,
  20) und zeigt in einer Tabelle, wie der Durchsatz pro Stream sich entwickelt und
  **ab wann es Ausfälle gibt** — das deckt das **Verbindungslimit deines Abos**
  direkt auf (ab welcher Stufe Streams scheitern) und den Punkt, ab dem die
  Bandbreite pro Stream unter Full-HD fällt. Grün = flüssig, Gelb = nur HD, Rot =
  Ausfall. Bewusster Knopf mit Warnung, da er kurz bis zu 20 Anbieter-Verbindungen
  belegt und laufende Zuschauer stören kann.

## v1.7

### Verbesserungen
- **Speedtest beantwortet jetzt „packt mein Setup X Zuschauer?":** Der IPTV-Test
  simuliert jetzt **8 gleichzeitige Streams** (statt 5) — den realistischen Fall
  mehrerer Zuschauer über dasselbe VPN — und gibt eine **klare Ampel** aus:
  „✅ 8 gleichzeitige Streams kein Problem – reicht für 8× Full-HD/4K" bzw. eine
  Warnung, wenn es dafür nicht reicht oder Test-Kanäle nicht erreichbar sind. Die
  Bewertung nutzt den **Durchsatz pro Stream unter Volllast** (Gesamt ÷ Streams),
  also genau das, was jeder Zuschauer bei voller Auslastung tatsächlich bekommt.
  Das Banner ist grün bei „alles gut" und rot bei einer echten Warnung.

## v1.6

### Verbesserungen
- **Internet-Speedtest jetzt parallel + ehrlich:** Öffentliche Speedtest-Server
  drosseln oder blockieren VPN-IP-Adressen — dadurch zeigte der Internet-Wert teils
  absurd niedrige Zahlen (z.B. 3 Mbit/s), obwohl der Tunnel über denselben Weg 400+
  schafft (der IPTV-Test bewies das). Zwei Änderungen: die Messung läuft jetzt
  **parallel** (mehrere Verbindungen, aggregiert) wie der IPTV-Test und holt so den
  realistischen Durchsatz aus gedrosselten Mirrors; und wenn der Internet-Wert
  trotzdem unplausibel weit unter dem echten Tunnel-Durchsatz liegt, wird er als
  **unzuverlässig gekennzeichnet** (mit Hinweis auf den belastbaren IPTV-Parallel-
  Wert) statt eine irreführende Zahl groß anzuzeigen. Zusätzlich liefert der Test
  eine Server-Diagnose mit, warum welcher Speedtest-Server ausfiel.

## v1.5

### Fehlerbehebungen
- **Internet-Speedtest zeigte teils absurd niedrige Werte:** Der Test nahm den
  ersten Server, der überhaupt antwortete — war das ein gedrosselter Mirror (z.B.
  OVH mit 2–3 Mbit/s), stand diese Zahl da, obwohl der Tunnel über denselben Weg
  problemlos 300+ Mbit/s schaffte (der IPTV-Test zeigte das auch). Jetzt wird der
  **schnellste** mehrerer Server genommen, ein zuverlässiger Server (Hetzner, DE)
  steht vorn, und sobald eine klar gute Messung vorliegt, wird früh abgebrochen.

## v1.4

### Verbesserungen
- **Speedtest misst jetzt belastbar:** Auf schnellen Leitungen war die 10-MB-
  Messung in unter einer Sekunde durch — gemessen wurde damit vor allem die
  TCP-Anlaufphase (Slow-Start), nicht die echte Bandbreite, und die Werte
  schwankten stark. Jetzt wird eine größere Datei geladen, die ersten ~1,2 s
  verworfen und nur der **eingeschwungene Durchsatz** gezählt. Die angezeigten
  Zahlen sind dadurch deutlich stabiler und realistischer.
- **Proaktiver VPN-Datenfluss-Check:** Der Wächter prüft zusätzlich zum Log-
  Zustand aktiv, ob wirklich Daten durch den Tunnel fließen (winzige Anfrage an
  ein DNS-freies Ziel). Damit wird ein „verbunden, aber es kommt nichts durch"-
  Tunnel erkannt, **bevor** die Streams stehen — nicht erst danach. Bewusst sehr
  konservativ: Es muss mehrfach hintereinander (~2 Min) kein Datenfluss vorliegen,
  bevor eingegriffen wird, damit ein einzelner Aussetzer keinen Fehlalarm auslöst.

## v1.3

### Funktionen
- **VPN-Server-Vergleich:** Neuer Knopf „Alle VPN-Server vergleichen" im Speedtest.
  Verbindet jede hochgeladene `.ovpn` nacheinander, misst die Internet-
  Geschwindigkeit über diesen Server und zeigt eine Rangliste mit dem schnellsten
  Standort. Der Wächter pausiert während des Laufs, und der zuvor aktive Server
  wird am Ende garantiert wiederhergestellt. **Hinweis:** Da es nur einen Tunnel
  gibt, sind Streams während des Vergleichs (~2 Min) kurz unterbrochen — daher ein
  bewusster Knopf mit Warnung, kein Automatismus.

### Fehlerbehebungen
- **Speedtest-Bewertung war irreführend:** Das Verdikt verglich den Anbieter stur
  mit dem neutralen Speedtest-Server und meldete „Flaschenhals", sobald er
  langsamer war — auch bei Geschwindigkeiten, die für jeden Stream mehr als
  reichen. Die Bewertung erfolgt jetzt **absolut am Streaming-Bedarf** (unter
  8 Mbit/s zu langsam, unter 25 für 4K knapp, sonst kein Flaschenhals inklusive
  geschätzter Zahl paralleler 4K-Streams).

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
