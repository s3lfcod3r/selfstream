# Changelog

## v1.40

### Ruckel-Frühwarner (Puffer-Reserve) im Canary + Browser-Player entfernt
- Der Canary misst jetzt die PUFFER-RESERVE: Ladezeit ÷ Spielzeit je Segment.
  <0,5 = flüssig (dicke Reserve), 0,5–0,85 = ok, 0,85–1,0 = knapp (Ruckelgefahr),
  ≥1,0 = ruckelt (Segmente kommen langsamer als sie spielen). Treffsicherer als eine
  feste Sekunden-Schwelle. Status zeigt „Flüssigkeit" + „Puffer-Reserve (X% Reserve)".
- Segmentliste mit Spieldauer (`_iptv_segments_with_dur` aus #EXTINF); `_reserve_level`.
- Sichtbaren Browser-Player (③) samt Preview-Endpunkten, hls.js und VLC-Link ENTFERNT –
  der Canary testet server-seitig, ein Zuschauen im Panel wird nicht gebraucht.


## v1.39

### Bulletproof: „Extern/VLC öffnen" + Block-Hinweis
- BEWIESEN (Playwright/Chromium + ffmpeg): der Canary-Player spielt den echten Live-Stream
  über VPN einwandfrei ab (PLAYING 1280x720, durchgehend). „Kein Bild" beim Nutzer lag an
  der Ansicht: ferngesteuerter Tab (Chromium `URL safety check`) bzw. iOS-nativ + fehlende
  .ts-Endung (v1.38 behoben).
- Neuer Knopf „🔗 Extern/VLC öffnen": erzeugt einen ~2h gültigen Stream-Link zum Abspielen in
  VLC o.ä. (garantiert, unabhängig vom Browser-Player).
- Erkennt der Player eine Browser-Blockade (Video-Fehler 4), weist er automatisch auf den
  externen Weg hin und blendet den Link ein.


## v1.38

### Segment-URLs enden auf .ts (VLC/ffmpeg/iOS-kompatibel)
- Verifiziert mit ffmpeg: die Segmente sind valides H.264 720p50 + AAC und dekodieren
  sauber (288 Frames/5,75s) – Stream einwandfrei. Strenge Player (VLC/ffmpeg/iOS-nativ)
  lehnten aber die alten `/api/preview/seg?u=` URLs ab (keine .ts-Endung).
- Segment-URLs jetzt als `/api/preview/seg/<b64>.ts` (Endung im Pfad). Neue Route
  `GET /api/preview/seg/{blob}`; Alt-Route `?u=` bleibt (Abwärtskompat.). Damit lässt
  sich der Stream auch extern (VLC) öffnen und mit ffmpeg verifizieren.


## v1.37

### Live-Diagnose im Player
- Kleine Diagnose-Zeile unter dem Player (Zweig hls.js/nativ, geladene Segmente, Puffer,
  Zeit, genauer Fehler) – damit sich Wiedergabe-Probleme im echten Browser des Nutzers
  ablesen lassen (der ferngesteuerte Test-Browser blockt Video via „URL safety check").


## v1.36

### Player geräteübergreifend (auch iPhone/Safari) + URL-Token-Auth
- Diagnose live: Backend liefert alle Segmente einwandfrei (H.264/AAC, je ~3,5 MB, 200)
  über VPN – Problem war rein clientseitig. iOS/Safari spielt HLS nur NATIV ab und kann
  keinen X-Admin-Token-HEADER mitschicken → Playlist wurde abgelehnt → kein Bild.
- Fix: Auth jetzt über kurzlebigen Preview-Token in der URL (`?pt=`, ~2h, zufällig, nur
  Vorschau – NICHT der Admin-Token). Neuer Endpunkt `POST /api/preview/token`;
  playlist+seg akzeptieren Admin-Header ODER gültigen pt.
- Player nutzt jetzt native HLS-Wiedergabe für Safari/iOS und hls.js (ohne Header) für
  Chrome/Firefox/Android. Damit läuft der Player auch am Handy.


## v1.35

### Canary-Player: Auto-Wiedergabe (kein Start-Knopf mehr)
- Der Player **läuft automatisch**, sobald die VPN-Seite offen ist – kein „▶ Ansehen"
  mehr nötig. Startet **stumm** (Autoplay-Regel der Browser); im Player oben entstummen.
- Checkbox **„Auto-Wiedergabe"** (an per Default) + Kanal-Dropdown (Wechsel startet neu).
  Beim Verlassen der VPN-Seite oder Auto-Aus wird die Verbindung sofort freigegeben
  (`nav()` ruft `canaryStop()`).
- Robustere Live-Config: `lowLatencyMode:false`, `liveSyncDurationCount:3`,
  Auto-Recover bei Netz-/Media-Fehlern (`startLoad`/`recoverMediaError`).
- Hinweis: Die eigentliche Video-Wiedergabe zeigt sich nur im normalen Browser – der
  ferngesteuerte Test-Browser blockt MediaSource-Wiedergabe („URL safety check"),
  daher wird die Bildausgabe vom Nutzer verifiziert (Datenkette ist verifiziert:
  Playlist 200, Segmente über VPN, hls.js self-hosted).

## v1.34

### Fix: Canary-Player läuft jetzt komplett intern + stabil
- **hls.js self-hosted** statt vom CDN (`/hls.min.js`, in SelfStream integriert) – der
  Player öffnet keinen externen Dienst mehr und funktioniert auch, wenn das Netz CDNs
  blockt. Kein „konnte nicht geladen werden"-Fehler mehr.
- **Cross-Event-Loop-Bug behoben:** `/api/preview/playlist.m3u8` und `/api/preview/seg`
  nutzten den geteilten HTTP-Client (an den Proxy-Loop gebunden) → sporadisch 502
  „Event bound to a different event loop". Jetzt frischer `make_iptv_client` je Anfrage
  (loop-sicher). Läuft weiterhin über den VPN-Tunnel (OS-Routing).

## v1.33

### Neu: Canary-Browser-Player (③) – selbst zusehen
- Im Canary-Bereich kann man jetzt einen Kanal **direkt im Panel ansehen** – der Stream
  läuft **durch SelfStream und den VPN-Tunnel**, genau wie beim echten Zuschauer. So
  sieht man mit eigenen Augen, ob's flüssig läuft.
- Kanal-Auswahl (Dropdown), ▶ Ansehen / ⏹ Stop. Läuft über hls.js (lazy per CDN geladen).
- Neue admin-geschützte Endpunkte: `/api/preview/channels`, `/api/preview/playlist.m3u8`
  (holt Kanal-Playlist, schreibt Segmente auf den Proxy um; folgt Master→Variante),
  `/api/preview/seg` (liefert Segmente via `_get_segment`). Auth via X-Admin-Token-Header
  (hls.js `xhrSetup`) – keine Tokens in URLs. Zählt beim Zusehen als 1 Zuschauer, „Stop" gibt frei.

### Neu: Ein-Klick-Umschalten (④)
- Neben jedem Server in **Weg 1 (Latenz)** und **Weg 2 (Durchsatz)** gibt es jetzt einen
  **⇄ Wechseln**-Knopf → bewusst-manueller Server-Wechsel per Klick.
- Neuer Endpunkt `POST /api/vpn/switch {ovpn}`: setzt den aktiven Server und startet den
  Tunnel neu. Frontend warnt vorher (Neustart unterbricht Streams ein paar Sekunden).
  Blockiert, solange ein Server-Test (Sweep/Zweittunnel) läuft.

## v1.32

### Neu: Selbst-Zuschauer (Canary) – Kern
- SelfStream kann sich jetzt selbst zuschauen: holt periodisch von einem Live-Kanal
  ein paar Segmente (wie ein echter Player) → füllt das Passiv-Qualitätssignal, damit
  Güte + E-Mail-Alarm auch dann greifen, wenn NIEMAND schaut.
- Zwei Modi (Einstellung): „Nur beobachten" (misst + alarmiert) und „Beobachten +
  handeln" (wechselt bei 0 Zuschauern + schlechter Qualität selbst auf den besten
  Server, höchstens 1×/Stunde). Zeit einstellbar: alle X Stunden oder 0 = 24/7.
- Schlau: pausiert automatisch bei fast vollem Verbindungslimit (stiehlt keinem
  Zuschauer eine Verbindung) und während laufender Server-Tests. Endpunkte
  `GET/POST /api/vpn/canary`. (Browser-Player + Ein-Klick-Umschalten folgen.)

## v1.31


### Behoben: E-Mail-Alarm flatterte (12 Mails statt 1)
- Wackelte die Stream-Qualität kurz über die Schwelle (z.B. ein einzelnes langsames
  Segment), kam sofort eine „Problem"-Mail und gleich danach eine „wieder ok"-Mail –
  bei mehrmaligem Wackeln 12+ Mails, obwohl der Durchsatz gut war (132 Mbit/s).
- Jetzt mit HYSTERESE + BREMSE: Alarm erst nach mehreren schlechten Stichproben am
  Stück (~15 min), Entwarnung erst nach mehreren guten (~15 min), und höchstens alle
  2 h eine NEUE Problem-Mail. Aus 12 Mails werden ~1–2. Die Problem-Mail nennt jetzt
  den echten Grund aus der auslösenden Messung (nicht mehr eine generische Meldung).

## v1.30


### Neu: Durchsatz-Vergleich über zweiten Tunnel (Weg 2, experimentell/opt-in)
- Neuer Knopf „🔀 Durchsatz-Vergleich (Zweittunnel)": misst den ECHTEN Anbieter-
  Durchsatz jedes VPN-Servers über einen ZWEITEN, parallelen Tunnel (tun1) – der
  Haupt-Tunnel (tun0) + alle laufenden Streams bleiben unberührt. Sicher gebaut:
  zweiter Tunnel mit route-noexec/route-nopull (fasst die Haupt-Routing-Tabelle
  nicht an); nur die Messung (Quelle = tun1-IP) läuft per Policy-Routing durch tun1.
  Manuell/opt-in, mit Schritt-Logging. Endpunkt `POST /api/vpn/dual-compare`.
- Weg-1-Genauigkeit: Server-Hostnamen werden jetzt zuerst zur IP aufgelöst, damit
  die stream-sichere Direktroute greift und die Latenz wirklich VON DER BOX gemessen
  wird (nicht durchs aktuelle Tunnel).

## v1.29


### Neu: Server-Latenz prüfen OHNE Stream-Unterbrechung (Weg 1)
- Neuer Knopf „🔍 Server-Latenz prüfen (stört nichts)" im VPN-Bereich: misst die
  Antwortzeit (TCP) zu jedem hochgeladenen VPN-Server – OHNE den Tunnel zu wechseln,
  OHNE Anbieter-Verbindung, OHNE einen einzigen Stream zu unterbrechen. Zeigt eine
  Rangliste (schnellster Server markiert), damit man bewusst manuell wechseln kann.
- Technisch stream-sicher: pro Server-IP kurz eine /32-Direktroute übers LAN-Gateway,
  danach wieder entfernt – betrifft nur die Test-Pakete zu VPN-Server-Adressen, nie
  das Standard-Routing oder laufende Streams. Endpunkt `GET /api/vpn/server-latency`.

## v1.28


### Kern-Fix: flüssiges Streaming (persistente Verbindung)
- **SelfStream öffnete für JEDES Segment eine neue Verbindung** (neuer TLS-Handshake).
  Über einen VPN mit hoher Latenz (~500 ms) kostet das ~1–2 s Handshake **pro Segment**,
  bevor ein Byte Video fliesst → Ruckeln, obwohl der Anbieter direkt (VLC) perfekt läuft.
- **Jetzt: ein geteilter Keep-Alive-Client** (`_get_iptv_client`) hält die Verbindung
  offen und verwendet sie über Segmente hinweg wieder – wie ein normaler Player. Kein
  Handshake pro Segment mehr. Bei toter Pool-Verbindung (z.B. nach VPN-Neustart) wird der
  Client automatisch erneuert (ein Retry). Lokal verifiziert: 5 Abrufe geteilt 0,09 s vs.
  neu-pro-Abruf 0,98 s (~11×; über den VPN entsprechend mehr).
- Damit ist SelfStream ein **effizienter Durchreicher** – flüssig auch ohne Vorausladen.

## v1.27

### Grundlegend geändert – Messung ist jetzt PASSIV
- **Kein aktives Extra-Messen mehr, das Streams stört.** Der frühere „Auto-Wechsel bei
  schlechter Leistung"-Wächter zog alle 2 Min zusätzliche Segmente vom Anbieter – das
  konkurrierte mit laufenden Streams und ruckelte (besonders bei begrenztem/trägem
  Anbieter, und bei vielen Nutzern gibt es praktisch nie „0 Zuschauer"). **Entfernt.**
- **Neu: passive Messung aus echtem Verkehr.** SelfStream liest jetzt die Ladezeit jedes
  echten Segment-Abrufs mit, den die Zuschauer ohnehin auslösen (`_get_segment`), und
  leitet daraus die real erlebte Qualität ab (Median-Ladezeit, Fehlerrate, Durchsatz →
  ok/träge/schlecht). **Null Extra-Last, funktioniert während des Schauens, kann den
  Stream prinzipiell nicht mehr stören.**
- **Health-Sampler/Selbst-Check laufen auf dem passiven Signal.** Nur bei Leerlauf (0
  echter Verkehr) macht ein einziger Mini-Check die Verlaufskurve am Leben.
- **E-Mail-Alarm** meldet jetzt echtes Ruckeln/Ausfälle (aus dem passiven Signal), nicht
  Test-Rauschen. Bei Einbruch während des Schauens: **nur Alarm, kein Auto-Wechsel**.
- **Bleibt:** Not-Failover bei totem Tunnel, Auto-Best nur nachts (0 Zuschauer),
  manuelle Knöpfe, billiger VPN-Lebenscheck (1.1.1.1, belastet den Anbieter nicht).

## v1.26

### Behoben (aus Code-Review)
- **Alarm-Mail:** schlug der erste SMTP-Versand bei Störungsbeginn fehl, kam für die
  ganze Störung keine Mail mehr. Jetzt wird bei anhaltendem Problem bei jeder
  Stichprobe erneut versucht, bis eine Mail wirklich rausging.
- **Leistungs-Wächter:** ein fehlgeschlagener Server-Neustart wurde als erfolgreicher
  Wechsel gewertet (30-Min-Sperre trotz nicht erfolgtem Wechsel). Jetzt zählt nur ein
  echt erfolgreicher Neustart.
- **Selbst-Check:** der Health-Sampler pausiert jetzt während eines VPN-Server-
  Vergleichs (verhindert Fehlalarm-Mail für einen absichtlichen Test).
- **Auto-Best-Zeitplan:** ein manueller „reiner Vergleich" verschob den geplanten
  Auto-Best-Lauf um bis zu 24 h. Nur echte Auto-Best-Läufe zählen jetzt fürs Intervall.
- **UI:** der „Jetzt testen"-Knopf (Leistungs-Wächter) konnte bei einem Fehler dauerhaft
  auf „Messe…" hängen bleiben (try/catch/finally ergänzt).

## v1.25

### Neu
- **Selbst-Check + E-Mail-Alarm.** SelfStream überwacht sich selbst (VPN-Tunnel,
  Anbieter erreichbar, Durchsatz/Antwortzeit – über die 5-Min-Stichprobe) und
  schickt bei einem **anhaltenden** Problem **eine** E-Mail, plus **Entwarnung**,
  wenn wieder alles läuft (Dedup: kein Spam). Optional **tägliches Lebenszeichen**
  („alles ok"). SMTP frei konfigurierbar (Server/Port/STARTTLS·SSL/Benutzer/
  Passwort/Empfänger). Konfiguration + Status-Ampel + „Test-E-Mail senden" oben auf
  der Diagnose-Seite. Neue Endpunkte `GET/POST /api/alerts`, `POST /api/alerts/test`.

## v1.24

### Geändert
- **Automatische VPN-Wechsel nur noch bei 0 Zuschauern.** Ein Serverwechsel
  unterbricht immer kurz ALLE Streams (nur ein Tunnel). Der Leistungs-Wächter
  schaltet jetzt **nicht mehr mitten im Gucken** um: erkennt er einen schwachen
  Server, während jemand schaut, wartet er (Log „⏸️ … Wechsel erst bei 0
  Zuschauern") und wechselt erst, sobald frei. Auto-Best lief schon nur bei 0
  Zuschauern. Der Not-Failover (toter Tunnel) bleibt – der rettet nur bereits
  unterbrochene Streams.

## v1.23

### Behoben
- **Auto-Best-Vergleich war viel zu langsam** (Minuten pro Server). Der Sweep hat
  mit der vollen Ziel-Stream-Zahl gemessen (z.B. 10) und damit das Anbieter-
  Verbindungslimit (~10) getroffen → Stalls/Timeouts. Jetzt misst er eine moderate
  Parallel-Last (max. 5 Streams) und leitet die „schafft ~N Streams"-Angabe aus dem
  Gesamtdurchsatz ab (Ziel = N × 8 Mbit/s). Deutlich schneller und schont das Limit.

## v1.22

### Neu
- **Auto-Best: automatisch den besten VPN-Server wählen** (opt-in). SelfStream misst
  regelmäßig ALLE hochgeladenen .ovpn durch und schaltet automatisch auf den
  schnellsten. Der Rundum-Vergleich unterbricht kurz alle Streams (nur ein Tunnel),
  läuft daher **nur bei 0 Zuschauern** und höchstens alle `vpn_autobest_hours`
  Stunden (einstellbar). Ergänzt den self-baseline-Leistungs-Wächter (schnelle
  Reaktion auf Einbrüche) um die Frage „welcher Server ist absolut der beste?".
- **Ziel „muss gut sein für N Streams" einstellbar** (`vpn_min_streams`, Standard 10).
  Der Vergleich misst mit so vielen Streams und meldet je Server „schafft ~N Streams"
  (Ziel = N × 8 Mbit/s ≈ Full-HD). Warnt, wenn selbst der beste Server das Ziel nicht
  sicher packt (dann liegt's am Anbieter/Leitung, nicht am VPN).
- Neue Endpunkte `GET/POST /api/vpn/autobest` (Einstellungen + Status) und
  `POST /api/vpn/autobest-now` (sofort suchen & auf den besten schalten). Knopf
  „🔍 Jetzt besten suchen & draufschalten" im Panel.

## v1.21

### Geändert
- **Anbieter-Kapazitätstest: Stream-Zahl selbst einstellbar.** Statt fest 1–20 gibt
  es jetzt ein Eingabefeld „bis N gleichzeitige Streams" (2–50). Die Test-Stufen
  passen sich automatisch an (`/api/iptv/capacity?max_streams=N`, Leiter bis 50).

## v1.20

### Behoben
- **Leistungs-Wächter zappelte / löste zu oft aus.** Die Perf-Messung nahm nur
  eine einzelne 1-Segment-Probe – die schwankt stark (im Log 14 %↔55 % beim selben
  Server) und erzeugte Fehl-„schwach" plus Server-Flappen. Drei Korrekturen:
  (1) es wird über mehrere Streams/Segmente gemessen (`VPN_PERF_STREAMS=2`,
  `VPN_PERF_SEGMENTS=3`) → stabile Zahl statt Rauschen; (2) die Baseline ist jetzt
  der **Median** (typischer Wert) statt eines Perzentil-Bestwerts – gegen einen
  Bestwert sah ein normaler Wert fälschlich wie „~55 %" aus; (3) der aktuelle Wert
  wird über die letzten Messungen **geglättet** (Median der letzten 3). Damit löst
  nur noch ein echter, anhaltender Einbruch aus.

## v1.19

### Neu
- **Automatischer VPN-Server-Wechsel bei schlechter Leistung** (opt-in). Ein neuer
  Leistungs-Wächter misst den aktuell verbundenen VPN-Server laufend (Durchsatz +
  Antwortzeit/Ping zum Anbieter, schonend über 1 Verbindung) und vergleicht ihn mit
  seiner *eigenen* üblichen Leistung („self-baseline", Perzentil aus einem
  rollierenden Fenster). Fällt der Durchsatz **unter eine einstellbare Prozent-Schwelle**
  der Bestleistung ODER steigt die Latenz **über eine einstellbare Prozent-Schwelle**,
  wird nach 3 schwachen Messungen in Folge automatisch auf die nächste hochgeladene
  `.ovpn` gewechselt – mit 30-Min-Sperre gegen Hin-und-Her. Beide Schwellen sind im
  Panel setzbar; ein Knopf „Jetzt testen" zeigt aktuell vs. Baseline + ob gewechselt
  würde, ohne zu wechseln. Ergänzt den bestehenden Not-Failover (der nur bei einem
  toten Tunnel greift) um eine Leistungs-Überwachung.
- Neue Endpunkte `GET/POST /api/vpn/perf` (Einstellungen + Status) und
  `POST /api/vpn/perf/test` (Sofort-Messung ohne Wechsel).

## v1.18

### Entfernt
- **Anbieter-Server-Umschaltung wieder entfernt** (Server-Vergleich, „bevorzugter
  Server erzwingen", automatische Umschaltung, Server-Entdeckung). Diese Funktionen
  haben bei Anbietern, die den Token an einen festen Server binden, nicht
  funktioniert: Das Umschreiben auf einen anderen Server löste beim Anbieter eine
  „SERVER CHANGED"-Sperre aus, und die Latenz-Messungen anderer Server maßen in
  Wahrheit diese Hinweis-Meldung statt echter Streams. Um Fehldiagnosen und
  unterbrochene Streams zu vermeiden, sind sie komplett raus. Der Rest bleibt:
  VPN-Wächter mit Ausfall-Erkennung/Failover, Speedtest inkl. Kapazitätstest
  (8/1–20 Streams), Latenz/Jitter-Anzeige, VPN-Server-Vergleich und der
  automatische Verlauf mit Frühwarnung.

### Funktionen
- **Automatisch auf den besten Server umschalten:** Neu im „Bevorzugter Server"-
  Kasten. **Knopf „🎯 Jetzt besten Server suchen & wechseln"** prüft sofort alle
  Server und setzt den bevorzugten auf den latenzärmsten. Dazu eine **Automatik**:
  aktivierbar per Häkchen, mit **einstellbarem Intervall** (alle X Stunden, 1–168) –
  SelfStream sucht dann selbstständig regelmäßig den besten Server und schaltet um.
  Automatisch wird nur bei **deutlicher** Verbesserung gewechselt (>30 % weniger
  Latenz), damit kein ständiges Hin-und-Her entsteht; per Knopf immer auf den
  Besten. Jede Umschaltung steht in der Diagnose.

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
