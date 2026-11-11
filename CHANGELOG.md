# 📰 Changelog

Newest version first. Full release notes are linked per version (in German).
Neueste Version zuerst. Die ausführlichen Release-Notes sind je Version verlinkt.

> **⚠️ Update tip / Update-Hinweis:** Update by pulling `ghcr.io/s3lfcod3r/selfstream:latest`; `update.sh` is a live patch for hotfixes and is lost when the container is recreated. ·
> Aktualisieren per `ghcr.io/s3lfcod3r/selfstream:latest`; `update.sh` ist ein Live-Patch für Hotfixes und geht beim Neuerstellen des Containers verloren.

---

## 1.99 · November 2026
- 🇬🇧 **Channels and groups on one menu item:** "Channels & groups" replaces the two separate menu items; two tabs at the top switch between the channel list and the groups. Nothing else changed on the two pages.
- 🇩🇪 **Kanäle und Gruppen unter einem Menüpunkt:** „Kanäle & Gruppen“ ersetzt die beiden einzelnen Menüpunkte; zwei Reiter oben wechseln zwischen Senderliste und Gruppen. An den beiden Seiten selbst hat sich sonst nichts geändert.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-99)

## 1.98 · November 2026
- 🇬🇧 **VPN page tidied up:** Four cards instead of eight: status (with what is flowing through the tunnel right now, the top speed and the target for the current number of users), server, VPN required and automatic server choice. The tunnel log and the Auto-Best settings fold away; latency search, speed test and self-viewer moved into "More tools". No function was removed.
- 🇩🇪 **VPN-Seite aufgeräumt:** Vier Karten statt acht: Status (mit dem, was gerade durch den Tunnel fließt, dem Höchsttempo und dem Ziel für die aktuelle Nutzerzahl), Server, VPN-Pflicht und Automatik. Das Tunnel-Protokoll und die Auto-Best-Einstellungen sind eingeklappt; Latenz-Suche, Speedtest und Selbst-Zuschauer liegen unter „Weitere Werkzeuge“. Es ist keine Funktion weggefallen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-98)

## 1.97 · November 2026
- 🇬🇧 **Dashboard answers "is everything running?":** The four lights (provider, VPN, SelfStream, devices) with the one-sentence verdict are now at the top of the dashboard. Each live viewer additionally shows whether their device keeps up and how many Mbit/s the channel consumes. "Active streams" became "Connections" with the provider limit next to it.
- 🇩🇪 **Dashboard beantwortet „läuft alles?“:** Die vier Ampeln (Anbieter, VPN, SelfStream, Geräte) mit dem Urteil-Satz stehen jetzt oben auf dem Dashboard. Bei jedem Zuschauer steht zusätzlich, ob sein Gerät Schritt hält und wie viele Mbit/s der Sender verbraucht. Aus „Aktive Streams“ wurde „Verbindungen“ mit der Grenze des Anbieters daneben.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-97)

## 1.96 · November 2026
- 🇬🇧 **Menu reordered, tunnel speed, Mbit/s in the single values:** The menu is grouped by task: Overview · Viewers (users, history) · Channels (providers, channels, groups, EPG) · Operation (quality, VPN, alerts and log) · System. "Traffic" is now called "Quality", "Diagnose" is "Alerts & log". The VPN light shows what is flowing through the tunnel right now and the top speed from the last server check. The single values show the fetch speed and the consumption of each segment in Mbit/s.
- 🇩🇪 **Menü neu sortiert, Tunnel-Tempo, Mbit/s bei den Einzelwerten:** Das Menü ist nach Aufgaben gruppiert: Übersicht · Zuschauer (Benutzer, Verlauf) · Sender (Anbieter, Kanäle, Gruppen, EPG) · Betrieb (Qualität, VPN, Alarm und Protokoll) · System. „Traffic“ heißt jetzt „Qualität“, „Diagnose“ heißt „Alarm & Protokoll“. Die VPN-Ampel zeigt, was gerade durch den Tunnel fließt, und das Höchsttempo aus der letzten Server-Prüfung. Die Einzelwerte nennen je Bildstück das Tempo beim Abholen und den Verbrauch in Mbit/s.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-96)

## 1.95 · November 2026
- 🇬🇧 **Traffic page: Mbit/s, provider speed over time, explanations:** Each viewer now shows the speed at which their channel arrives at SelfStream (Mbit/s next to the reserve) and how much the channel consumes on the way to the device. New chart "provider speed over time" (last hour up to 7 days) with average, weakest section and late segments – so you can see whether the provider or the VPN is weakening. Hovering over the lights and column headings explains what each value means. Contains 1.94.
- 🇩🇪 **Traffic-Seite: Mbit/s, Anbieter-Tempo im Verlauf, Erklärungen:** Je Zuschauer steht jetzt das Tempo, mit dem sein Sender bei SelfStream ankommt (Mbit/s neben der Reserve), und wie viel der Sender auf dem Weg zum Gerät verbraucht. Neues Bild „Anbieter-Tempo im Verlauf“ (letzte Stunde bis 7 Tage) mit Schnitt, schwächstem Abschnitt und späten Bildstücken – so sieht man, ob der Anbieter oder das VPN schwächelt. Fährt man über die Ampeln und Spaltenköpfe, wird erklärt, was der Wert bedeutet. Enthält 1.94.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-95)

## 1.94 · November 2026
- 🇬🇧 **No false "device falls behind":** With real viewers the new lag value sat at 1 in more than half of all requests although playback was smooth – one segment above the best value is normal. The limits are now 2 (tight) and 3 (cannot keep up); skipped segments count as before.
- 🇩🇪 **Kein falsches „Gerät fällt zurück“:** Bei echten Zuschauern stand der neue Rückstand in mehr als der Hälfte der Anfragen auf 1, obwohl alles flüssig lief – ein Bildstück über dem Bestwert ist normal. Die Grenzen liegen jetzt bei 2 (knapp) und 3 (kommt nicht hinterher); übersprungene Bildstücke zählen wie bisher.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-94)

## 1.93 · November 2026
- 🇬🇧 **Device leg measured properly:** The "to the device" time introduced in 1.91 was practically always 0, because a reverse proxy in front of SelfStream takes each segment at once – it said nothing about the viewer's device. The Traffic page now shows whether a player **keeps up**: if it asks for ever older segments or skips segments while SelfStream delivered on time, the device or its line cannot keep up. Viewers, the "devices" light, incidents and the single values use this signal.
- 🇩🇪 **Geräte-Strecke richtig gemessen:** Die in 1.91 eingeführte Zeit „zum Gerät“ war praktisch immer 0, weil ein Reverse-Proxy vor SelfStream jedes Bildstück sofort abnimmt – sie sagte nichts über das Gerät des Zuschauers. Die Traffic-Seite zeigt jetzt, ob ein Player **Schritt hält**: Fragt er immer ältere Bildstücke an oder überspringt er welche, obwohl SelfStream pünktlich geliefert hat, kommt das Gerät oder dessen Leitung nicht hinterher. Zuschauer, Ampel „Geräte“, Störungen und Einzelwerte nutzen dieses Zeichen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-93)

## 1.92 · November 2026
- 🇬🇧 **VPN target follows the number of users, faster server:** Auto-Best no longer uses a fixed Mbit/s threshold. The target is computed from the active users (users × demand per stream + reserve). While someone is watching, servers are no longer switched "just in case" – only on real stutter, and then to the last known fastest server first. When idle, other servers are only measured if the active one misses the target. A server that stops answering is replaced immediately. Measurements now start at the first data block (5 MB runs used to cap at about 200 Mbit/s). All outgoing requests are bound to IPv4. The database keeps one open connection per thread and writes log lines in batches – with 8 simultaneous viewers the first byte of a segment arrived after 637 ms before and 115 ms now (load test with a simulated provider).
- 🇩🇪 **VPN-Ziel richtet sich nach der Nutzerzahl, schnellerer Server:** Auto-Best arbeitet nicht mehr mit einer festen Mbit/s-Schwelle. Das Ziel ergibt sich aus den aktiven Nutzern (Nutzer × Bedarf je Stream + Reserve). Schaut jemand, wird nicht mehr „auf Verdacht“ umgeschaltet – nur bei echtem Ruckeln, und dann zuerst auf den zuletzt schnellsten Server. Im Leerlauf werden andere Server nur gemessen, wenn der aktive das Ziel verfehlt. Antwortet ein Server nicht mehr, wird sofort gewechselt. Gemessen wird ab dem ersten Datenblock (5-MB-Messungen endeten bisher bei rund 200 Mbit/s). Alle Abrufe nach außen sind an IPv4 gebunden. Die Datenbank hält je Thread eine Verbindung offen und schreibt Protokollzeilen gebündelt – bei 8 gleichzeitigen Zuschauern kam das erste Byte eines Segments vorher nach 637 ms, jetzt nach 115 ms (Lasttest mit nachgebautem Anbieter).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-92)

## 1.91 · November 2026
- 🇬🇧 **Traffic page rebuilt – where is the problem?** Four status lights (provider, VPN, SelfStream, devices) with a one-sentence verdict; per viewer both legs side by side (arriving at SelfStream / going to the device). Late segments are bundled into **incidents** with a likely cause: one channel → provider, several channels → provider or VPN (decided by a neutral test download through the tunnel, never past the VPN), one viewer only → their own line. The channel ranking now shows the share of late segments in percent. Segments are judged against their play time ("reserve") instead of fixed 1 s / 2 s limits, cache hits no longer produce fantasy values like 10,000 Mbit/s, and the delivery time to the device is stored per segment.
- 🇩🇪 **Traffic-Seite neu – wo hakt es?** Vier Ampeln (Anbieter, VPN, SelfStream, Geräte) mit einem Satz als Urteil; je Zuschauer beide Strecken nebeneinander (kommt bei SelfStream an / geht zum Gerät). Späte Bildstücke werden zu **Störungen** gebündelt, mit wahrscheinlicher Ursache: ein Sender → Anbieter, mehrere Sender → Anbieter oder VPN (entschieden durch einen neutralen Test-Download durch den Tunnel, nie am VPN vorbei), nur ein Zuschauer → dessen Leitung. Die Sender-Rangliste zeigt den Anteil später Bildstücke in Prozent. Bewertet wird gegen die Spielzeit („Reserve“) statt starr ab 1 s / 2 s, Treffer aus dem Zwischenspeicher erzeugen keine Fantasiewerte wie 10.000 Mbit/s mehr, und die Auslieferzeit ans Gerät wird je Bildstück gespeichert.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-91)

## 1.90 · November 2026
- 🇬🇧 **Prefetch hits the player's start point:** On a channel switch SelfStream now fetches the segment a player really starts with – three target durations before the end of the playlist – and the one after it. Version 1.89 fetched the last three segments; with the usual six-segment playlists the player started earlier, so the very first segment was still fetched only on request.
- 🇩🇪 **Vorladen trifft den Startpunkt des Players:** Beim Umschalten holt SelfStream jetzt das Segment, mit dem ein Player wirklich beginnt – drei Zieldauern vor dem Ende der Playlist – und das danach. Version 1.89 holte die letzten drei Segmente; bei den üblichen Playlists mit sechs Segmenten begann der Player weiter vorn, das allererste Segment wurde also weiterhin erst auf Anfrage geholt.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-90)

## 1.89 · November 2026
- 🇬🇧 **Faster channel switching:** The channel address answers directly instead of redirecting (one request less per switch), playlists use the already open connection to the provider, "now playing" is looked up per channel instead of scanning the whole guide, and settings are kept for two seconds instead of being read from the database on every request. Prefetching was reworked: on a switch the segments the player starts with are fetched right away, afterwards the segment the player asks for next – before, segments the player had already passed were fetched.
- 🇩🇪 **Schnelleres Umschalten:** Die Sender-Adresse antwortet direkt statt umzuleiten (eine Anfrage weniger je Umschalten), Playlists nutzen die schon offene Verbindung zum Anbieter, „läuft gerade“ wird je Sender nachgeschlagen statt das ganze Programm zu durchsuchen, und Einstellungen werden zwei Sekunden gemerkt statt bei jedem Abruf aus der Datenbank gelesen. Das Vorladen wurde überarbeitet: Beim Umschalten werden sofort die Segmente geholt, mit denen der Player beginnt, danach jeweils das Segment, das er als Nächstes anfragt – bisher wurden Segmente geholt, an denen der Player schon vorbei war.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-89)

## 1.88 · November 2026
- 🇬🇧 **VPN kill switch:** New setting "VPN required" (VPN page). When it is on, no request leaves the container while the tunnel does not carry the traffic – including during a tunnel restart, switch or crash. Until now the normal route was restored on teardown and running streams fetched their segments directly. Viewers see a "VPN disturbed" notice and the channel resumes by itself. LAN targets given as IP stay reachable; the alert mail still bypasses the tunnel on purpose.
- 🇩🇪 **VPN-Notschalter:** Neue Einstellung „VPN-Pflicht“ (Seite VPN). Ist sie an, verlässt kein Abruf den Container, solange der Tunnel den Verkehr nicht trägt – auch nicht beim Neustart, Wechsel oder Absturz des Tunnels. Bisher wurde beim Abbau die normale Route wiederhergestellt, und laufende Streams holten ihre Segmente direkt. Zuschauer sehen den Hinweis „VPN gestört“, der Sender startet von selbst wieder. Ziele im eigenen Netz (als IP) bleiben erreichbar; die Alarm-Mail geht weiterhin bewusst am Tunnel vorbei.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-88)

## 1.87 · November 2026
- 🇬🇧 **Auto-Best no longer disrupts the stream:** The separate measuring tunnel used the same Mullvad key and froze the live tunnel for about two minutes. Auto-Best now briefly switches the real tunnel to each candidate (seamlessly), measures there and finally stays on the fastest or returns to the previous server. Every search, measurement and switch is now written to the container log with a timestamp.
- 🇩🇪 **Auto-Best stört den Stream nicht mehr:** Der eigene Mess-Tunnel nutzte denselben Mullvad-Schlüssel und legte den echten Tunnel rund zwei Minuten lahm. Jetzt stellt Auto-Best den echten Tunnel kurz und nahtlos auf jeden Kandidaten, misst dort und bleibt am Ende auf dem schnellsten oder geht zurück auf den bisherigen Server. Jede Suche, Messung und jeder Wechsel steht jetzt mit Uhrzeit im Container-Log.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-87)

## 1.86 · November 2026
- 🇬🇧 **Auto-Best measures for real:** SelfStream now measures the actual speed of the active WireGuard server and its alternatives through a separate measuring tunnel (running streams are not touched) and switches seamlessly to the fastest. It searches when segments load slowly or stall – not only when playback stutters – and also runs a routine check while nobody is watching. The choice is based on measured speed, no longer on ping.
- 🇩🇪 **Auto-Best misst wirklich:** SelfStream misst jetzt das echte Tempo des aktiven WireGuard-Servers und der Alternativen über einen eigenen Mess-Tunnel (laufende Streams bleiben unberührt) und schaltet nahtlos auf den schnellsten. Gesucht wird, sobald Segmente langsam laden oder hängen – nicht erst bei Ruckeln – und zusätzlich per Routine-Check, wenn niemand schaut. Entschieden wird nach gemessenem Tempo statt nach Ping.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-86)

## 1.85 · November 2026
- 🇬🇧 **Reworked e-mail alerts:** fewer false alarms (the idle check tries up to three channels instead of only the first, a fair latency limit, stream quality judged by load time versus segment length), every mail says what, since when and how long, no more silently swallowed outages, at most 5 alarm mails per day. New: mail when the EPG or a channel list fails for 30 min and after an unexpected restart (e.g. out of memory), daily heartbeat at a fixed time, mail history in the panel.
- 🇩🇪 **E-Mail-Alarm überarbeitet:** weniger Fehlalarme (der Leerlauf-Check probiert bis zu drei Sender statt nur den ersten, faire Antwortzeit-Grenze, Stream-Qualität nach Ladezeit im Verhältnis zur Segmentlänge), jede Mail sagt was, seit wann und wie lange, keine verschluckten Störungen mehr, höchstens 5 Störungs-Mails pro Tag. Neu: Mail, wenn EPG oder eine Senderliste 30 Min lang fehlschlägt und nach einem unerwarteten Neustart (z. B. Speicher voll), Lebenszeichen zur festen Uhrzeit, Mail-Verlauf im Panel.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-85)

## 1.84 · November 2026
- 🇬🇧 Fixes the **container being killed for running out of memory** every few days: refreshing the EPG no longer keeps the old and new EPG in memory side by side, filtering goes file to file, and memory is returned to the system afterwards (measured: refresh peak +369 → +148 MB, idle 197 → 93 MB). All four EPG load paths now use the same memory-safe route.
- 🇩🇪 Behebt den **Speicher-Abbruch des Containers** alle paar Tage: Beim EPG-Abruf liegen alte und neue EPG nicht mehr gleichzeitig im Speicher, gefiltert wird von Datei zu Datei, und der Speicher geht danach ans System zurück (gemessen: Spitze beim Abruf +369 → +148 MB, Grundlast 197 → 93 MB). Alle vier EPG-Ladewege nutzen jetzt denselben speichersicheren Weg.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-84)

## 1.83 · September 2026 🔒
- 🇬🇧 Security update after a full code review: **no credentials in the logs** any more (uvicorn access log, httpx, URL-encoded tokens), stored XSS in the VPN area fixed, CORS limited to LAN origins, rate limit on wrong tokens, `max_streams` is saved again, longer short tokens, EPG merge and playlist-parser fixes, Unraid templates with `--restart=unless-stopped`.
- 🇩🇪 Sicherheitsupdate nach vollständiger Code-Durchsicht: **keine Zugangsdaten mehr im Log** (uvicorn-Zugriffslog, httpx, URL-kodierte Token), gespeichertes XSS im VPN-Bereich behoben, CORS auf LAN-Herkünfte begrenzt, Sperre bei falschen Token, `max_streams` wird wieder gespeichert, längere Kurz-Token, Korrekturen an EPG-Zusammenführung und Playlist-Parser, Unraid-Vorlagen mit `--restart=unless-stopped`.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-83)

## 1.82 · September 2026
- 🇬🇧 The **EPG channel filter** now applies to all three fetch paths (automatic fetch, `/iptv/epg.xml`, "Reload").
- 🇩🇪 Der **EPG-Kanalfilter** greift jetzt an allen drei Abrufwegen (automatischer Abruf, `/iptv/epg.xml`, „Neu laden“).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-82)

## 1.81 · September 2026
- 🇬🇧 Large EPG sources are **filtered down to your own channels while downloading** (measured: 622 MB → 27 MB, 93 MB peak RAM).
- 🇩🇪 Große EPG-Quellen werden **schon beim Download auf die eigenen Sender eingedampft** (gemessen: 622 MB → 27 MB, 93 MB Spitzen-RAM).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-81)

## 1.80 · August 2026
- 🇬🇧 Old EPG placeholders ("no programme information") are **deleted from the archive** so they no longer block time slots.
- 🇩🇪 Alte EPG-Platzhalter („Keine Programminformationen“) werden **aus dem Archiv gelöscht** und blockieren keine Sendeplätze mehr.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-80)

## 1.79 · August 2026
- 🇬🇧 The EPG archive only takes **priority on days where the provider really delivers mixed lists**; otherwise the provider's newer data wins.
- 🇩🇪 Das EPG-Archiv hat **nur noch an Tagen mit wirklich vermischten Listen Vorrang**; sonst gewinnt der aktuellere Anbieter.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-79)

## 1.78 · August 2026
- 🇬🇧 The EPG archive may **replace, but never delete** programmes — three documented cases of lost shows fixed.
- 🇩🇪 Das EPG-Archiv darf **ersetzen, aber nie löschen** — drei belegte Fälle verschwundener Sendungen behoben.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-78)

## 1.77 · August 2026
- 🇬🇧 New **memory indicator** in the panel (`GET /api/memstats`, dashboard tile) as an early warning against leaks/OOM.
- 🇩🇪 Neuer **Speicher-Melder** im Panel (`GET /api/memstats`, Dashboard-Kachel) als Frühwarnung gegen Lecks/OOM.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-77)

## 1.76 · August 2026
- 🇬🇧 Filling gaps from the archive no longer creates mixed EPG lists itself (slot overlap check instead of exact timestamps).
- 🇩🇪 Das Auffüllen aus dem Archiv erzeugt keine vermischten EPG-Listen mehr (Prüfung auf belegte Sendeplätze statt exakter Zeitstempel).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-76)

## 1.75 · August 2026 🔒
- 🇬🇧 Security hardening (package 1): OpenVPN script directives stripped, slimmer image, real client IP behind proxies, segment size limit, EPG `?force=1` throttle, HSTS, **PBKDF2 600k**, stricter input validation.
- 🇩🇪 Sicherheits-Härtung (Paket 1): OpenVPN-Script-Direktiven entfernt, schlankeres Image, echte Client-IP hinter Proxys, Segment-Größenlimit, Drossel für EPG `?force=1`, HSTS, **PBKDF2 600k**, strengere Eingabeprüfung.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-75)

## 1.74 · August 2026
- 🇬🇧 No more guessing on mixed EPG lists: only clean channel days are archived, new option **"own EPG has priority"** and **"🗑 Clear archive"**.
- 🇩🇪 Kein Raten mehr bei vermischten EPG-Listen: nur saubere Sendertage werden archiviert, neue Option **„Eigenes EPG hat Vorrang“** und **„🗑 Archiv leeren“**.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-74)

## 1.73 · August 2026
- 🇬🇧 The playlist now points to the **own processed EPG** (`/iptv/epg-7d.xml`) instead of the provider; the EPG archive can be **browsed** per channel and day.
- 🇩🇪 Die Playlist verweist jetzt aufs **eigene aufbereitete EPG** (`/iptv/epg-7d.xml`) statt auf den Anbieter; das EPG-Archiv ist je Sender und Tag **einsehbar**.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-73)

## 1.72 · August 2026
- 🇬🇧 **Multiple EPG sources** at once: the first one leads, the others only fill real gaps (`.xml.gz` supported).
- 🇩🇪 **Mehrere EPG-Quellen** gleichzeitig: die erste gibt den Ton an, weitere füllen nur echte Lücken (`.xml.gz` wird unterstützt).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-72)

## 1.71 · August 2026
- 🇬🇧 **"Protect first version"**: the archive rejects later overlapping changes from the provider, so it stays clean.
- 🇩🇪 **„Erststand schützen“**: das Archiv weist nachträgliche, überlappende Änderungen des Anbieters ab und bleibt sauber.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-71)

## 1.70 · August 2026
- 🇬🇧 Own **EPG archive** (default 30 days, 7–365): history stays available for catchup even after the provider drops it.
- 🇩🇪 Eigenes **EPG-Archiv** (Standard 30 Tage, 7–365): die Historie bleibt für Catchup erhalten, auch wenn der Anbieter sie fallen lässt.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-70)

## 1.69 · August 2026
- 🇬🇧 EPG cleanup only removes entries that really collide, instead of whole lists (no more gaps in the player).
- 🇩🇪 Die EPG-Bereinigung entfernt nur noch wirklich kollidierende Einträge statt ganzer Listen (keine Lücken mehr im Player).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-69)

## 1.68 · August 2026
- 🇬🇧 New option **"Clean up mixed programme lists"** so catchup starts the show you clicked; two settings were silently dropped on save — fixed.
- 🇩🇪 Neue Option **„Vermischte Programmlisten bereinigen“**, damit Catchup die angeklickte Sendung startet; zwei Einstellungen gingen beim Speichern verloren — behoben.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-68)

## 1.67 · August 2026
- 🇬🇧 The EPG channel manager only imports channels from your own list; new **"🧹 Remove foreign"** button.
- 🇩🇪 Der EPG-Kanal-Manager übernimmt nur noch Sender aus der eigenen Kanalliste; neuer Knopf **„🧹 Fremde entfernen“**.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-67)

## 1.66 · August 2026
- 🇬🇧 EPG routes no longer load the whole file into memory per request (disk cache + `FileResponse`).
- 🇩🇪 EPG-Routen laden nicht mehr pro Anfrage die ganze Datei in den Speicher (Plattencache + `FileResponse`).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-66)

## 1.65 · August 2026
- 🇬🇧 EPG times in the admin panel were two hours early (UTC) — now converted via `diagnostic_timezone`.
- 🇩🇪 EPG-Zeiten im Admin-Panel waren zwei Stunden zu früh (UTC) — jetzt über `diagnostic_timezone` umgerechnet.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-65)

## 1.64 · August 2026
- 🇬🇧 Fixed the cause of OOM-killed containers (EPG tree rebuilt repeatedly), download size limit `epg_max_mb`, new **"🔎 Check quality"** for EPG sources.
- 🇩🇪 Ursache für OOM-Abstürze behoben (EPG-Baum wurde immer wieder neu gebaut), Download-Limit `epg_max_mb`, neue **„🔎 Prüfen“**-Qualitätsprüfung der EPG-Quelle.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-64)

## 1.63 · August 2026
- 🇬🇧 New speedtest: **bottleneck VPN vs. HLS provider**, viewer-safe, plus a **server throughput comparison**.
- 🇩🇪 Neuer Speedtest: **Flaschenhals VPN vs. HLS-Anbieter**, zuschauer-sicher, dazu ein **Server-Durchsatz-Vergleich**.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-63)

## 1.62 · August 2026
- 🇬🇧 All diagnostic tools made viewer- and tunnel-safe (speedtest limited to free lines, active server route never touched).
- 🇩🇪 Alle Diagnose-Tools zuschauer- und tunnelsicher gemacht (Speedtest nur auf freien Lines, Route des aktiven Servers bleibt unberührt).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-62)

## 1.61 · August 2026
- 🇬🇧 Hotfix: the server latency check no longer tears down the tunnel.
- 🇩🇪 Hotfix: der Server-Latenz-Check reißt den Tunnel nicht mehr ab.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-61)

## 1.60 · August 2026
- 🇬🇧 Hotfix: streams aborted with `bound to a different event loop` — canary and client reset are now loop-safe.
- 🇩🇪 Hotfix: Streams brachen mit `bound to a different event loop` ab — Canary und Client-Reset sind jetzt loop-sicher.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-60)

## 1.59 · August 2026
- 🇬🇧 Alert e-mails bypass the VPN, WireGuard self-repair via handshake age, failover to another WireGuard server.
- 🇩🇪 Alarm-Mails gehen am VPN vorbei, WireGuard-Selbstreparatur über das Handshake-Alter, Ausweichen auf einen anderen WireGuard-Server.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-59)

## 1.58 · August 2026
- 🇬🇧 Day filter for buffering events (works together with the user filter).
- 🇩🇪 Tages-Filter für Buffering-Ereignisse (zusammen mit dem User-Filter).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-58)

## 1.57 · August 2026
- 🇬🇧 Canary history kept for **30 days** in its own table, day filter in the statistics popup.
- 🇩🇪 Canary-Verlauf wird **30 Tage** in eigener Tabelle aufbewahrt, Tages-Filter im Statistik-Popup.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-57)

## 1.56 · August 2026
- 🇬🇧 **Auto-Best for WireGuard**: switches seamlessly to the fastest server on real stuttering, with threshold and cooldown.
- 🇩🇪 **Auto-Best für WireGuard**: wechselt bei echtem Ruckeln nahtlos auf den schnellsten Server, mit Schwelle und Cooldown.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-56)

## 1.55 · August 2026
- 🇬🇧 **Seamless WireGuard server switch** — only the peer is swapped, no stream interruption.
- 🇩🇪 **Nahtloser WireGuard-Serverwechsel** — nur der Peer wird getauscht, keine Stream-Unterbrechung.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-55)

## 1.54 · August 2026
- 🇬🇧 The delivery speed SelfStream → device is now measured **per user**.
- 🇩🇪 Die Auslieferung SelfStream → Gerät wird jetzt **pro User** gemessen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-54)

## 1.53 · August 2026
- 🇬🇧 The canary uses real viewer segments while someone is watching (no extra line used).
- 🇩🇪 Der Canary nutzt bei aktiven Zuschauern deren echte Segmente (keine zusätzliche Line).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-53)

## 1.52 · August 2026
- 🇬🇧 The canary checks for a free line before every segment and steps aside for viewers immediately.
- 🇩🇪 Der Canary prüft vor jedem Segment, ob eine Line frei ist, und macht Zuschauern sofort Platz.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-52)

## 1.51 · August 2026
- 🇬🇧 Speedtest presented honestly for WireGuard (internet test unreliable through any VPN, canary is the reliable figure).
- 🇩🇪 Speedtest für WireGuard ehrlich dargestellt (Internet-Test durch jedes VPN unzuverlässig, der Canary ist der verlässliche Wert).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-51)

## 1.50 · August 2026
- 🇬🇧 OpenVPN removed from the UI, upload `.conf` only; server latency check rebuilt for WireGuard.
- 🇩🇪 OpenVPN aus der Oberfläche entfernt, Upload nur noch `.conf`; Server-Latenz-Prüfung auf WireGuard umgebaut.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-50)

## 1.49 · August 2026
- 🇬🇧 New **"→ USER" measurement** (SelfStream → player) to spot slow device connections.
- 🇩🇪 Neue **„→ USER“-Messung** (SelfStream → Player), um langsame Geräteverbindungen zu erkennen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-49)

## 1.48 · August 2026
- 🇬🇧 WireGuard DNS fix (Mullvad DNS + Quad9 fallback) — fixes dropped segments.
- 🇩🇪 WireGuard-DNS-Fix (Mullvad-DNS + Quad9-Fallback) — behebt Segment-Aussetzer.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-48)

## 1.47 · August 2026
- 🇬🇧 WireGuard is brought up manually instead of `wg-quick` (Docker blocks `sysctl src_valid_mark`).
- 🇩🇪 WireGuard wird manuell statt per `wg-quick` hochgefahren (Docker sperrt `sysctl src_valid_mark`).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-47)

## 1.46 · August 2026
- 🇬🇧 WireGuard start in the container fixed (`resolvconf` missing).
- 🇩🇪 WireGuard-Start im Container behoben (`resolvconf` fehlte).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-46)

## 1.45 · August 2026
- 🇬🇧 **Mullvad auto-import**: one `.conf` upload creates a config for every Mullvad server.
- 🇩🇪 **Mullvad-Auto-Import**: ein `.conf`-Upload legt für jeden Mullvad-Server eine Config an.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-45)

## 1.44 · August 2026
- 🇬🇧 **WireGuard support** (`.conf`) alongside OpenVPN.
- 🇩🇪 **WireGuard-Unterstützung** (`.conf`) neben OpenVPN.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-44)

## 1.43 · August 2026
- 🇬🇧 User filter and real 30-day retention for quality events.
- 🇩🇪 User-Filter und echte 30-Tage-Aufbewahrung für Qualitäts-Ereignisse.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-43)

## 1.42 · August 2026
- 🇬🇧 Canary statistics popup; check interval 0–9999 hours (0 = 24/7).
- 🇩🇪 Canary-Statistik-Popup; Prüf-Intervall 0–9999 Stunden (0 = 24/7).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-42)

## 1.41 · August 2026
- 🇬🇧 Stutter early warning counts missing segments as stalls.
- 🇩🇪 Der Ruckel-Frühwarner wertet fehlende Segmente als Stocker.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-41)

## 1.40 · August 2026
- 🇬🇧 Canary measures the **buffer reserve** (load time ÷ play time); browser player removed.
- 🇩🇪 Der Canary misst die **Puffer-Reserve** (Ladezeit ÷ Spielzeit); Browser-Player entfernt.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-40)

## 1.39 · August 2026
- 🇬🇧 "Open externally/VLC" button for the canary player and a hint when the browser blocks playback.
- 🇩🇪 Knopf „Extern/VLC öffnen“ für den Canary-Player und Hinweis, wenn der Browser die Wiedergabe blockt.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-39)

## 1.38 · August 2026
- 🇬🇧 Preview segment URLs end in `.ts` (VLC/ffmpeg/iOS compatible).
- 🇩🇪 Vorschau-Segment-URLs enden auf `.ts` (VLC/ffmpeg/iOS-kompatibel).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-38)

## 1.37 · August 2026
- 🇬🇧 Live diagnostics line below the player.
- 🇩🇪 Live-Diagnosezeile unter dem Player.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-37)

## 1.36 · August 2026
- 🇬🇧 Player works across devices (incl. iPhone/Safari) via a short-lived preview token in the URL.
- 🇩🇪 Player geräteübergreifend (auch iPhone/Safari) über einen kurzlebigen Vorschau-Token in der URL.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-36)

## 1.35 · August 2026
- 🇬🇧 Canary player starts automatically (muted) when the VPN page is open.
- 🇩🇪 Der Canary-Player startet automatisch (stumm), sobald die VPN-Seite offen ist.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-35)

## 1.34 · August 2026
- 🇬🇧 Canary player runs fully internal (self-hosted hls.js) and a cross-event-loop bug is fixed.
- 🇩🇪 Der Canary-Player läuft komplett intern (hls.js selbst gehostet), Cross-Event-Loop-Fehler behoben.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-34)

## 1.33 · August 2026
- 🇬🇧 Canary browser player in the panel and one-click server switch.
- 🇩🇪 Canary-Browser-Player im Panel und Server-Wechsel per Klick.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-33)

## 1.32 · August 2026
- 🇬🇧 **Self-viewer (canary)**: SelfStream watches itself so quality checks and alerts work even when nobody is watching.
- 🇩🇪 **Selbst-Zuschauer (Canary)**: SelfStream schaut sich selbst zu, damit Qualitätsprüfung und Alarm auch ohne Zuschauer greifen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-32)

## 1.31 · August 2026
- 🇬🇧 Alert e-mails no longer flap (hysteresis + throttle: ~1–2 mails instead of 12).
- 🇩🇪 Alarm-Mails flattern nicht mehr (Hysterese + Bremse: ~1–2 Mails statt 12).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-31)

## 1.30 · August 2026
- 🇬🇧 Experimental throughput comparison over a second tunnel (opt-in); more accurate latency check.
- 🇩🇪 Experimenteller Durchsatz-Vergleich über einen zweiten Tunnel (opt-in); genauere Latenzprüfung.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-30)

## 1.29
- 🇬🇧 Check server latency **without interrupting streams**.
- 🇩🇪 Server-Latenz prüfen **ohne Stream-Unterbrechung**.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-29)

## 1.28 · August 2026
- 🇬🇧 Core fix for smooth streaming: one shared **keep-alive client** instead of a new connection per segment.
- 🇩🇪 Kern-Fix für flüssiges Streaming: ein geteilter **Keep-Alive-Client** statt einer neuen Verbindung pro Segment.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-28)

## 1.27 · August 2026
- 🇬🇧 Measurement is now **passive** (from real viewer segments) — no more active probing that disrupts streams.
- 🇩🇪 Die Messung ist jetzt **passiv** (aus echten Zuschauer-Segmenten) — kein aktives Messen mehr, das Streams stört.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-27)

## 1.26 · August 2026
- 🇬🇧 Bug fixes from a code review (alert e-mail retry, failed restart no longer counted as switch, sampler pause, schedule, UI).
- 🇩🇪 Bugfixes aus einem Code-Review (Alarm-Mail-Wiederholung, fehlgeschlagener Neustart zählt nicht als Wechsel, Sampler-Pause, Zeitplan, UI).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-26)

## 1.25 · August 2026
- 🇬🇧 **Self-check + e-mail alerts** with all-clear and optional daily heartbeat.
- 🇩🇪 **Selbst-Check + E-Mail-Alarm** mit Entwarnung und optionalem täglichem Lebenszeichen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-25)

## 1.24 · August 2026
- 🇬🇧 Automatic VPN switches only happen with **0 viewers**.
- 🇩🇪 Automatische VPN-Wechsel nur noch bei **0 Zuschauern**.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-24)

## 1.23 · August 2026
- 🇬🇧 Auto-Best comparison is much faster (moderate parallel load instead of the full target count).
- 🇩🇪 Der Auto-Best-Vergleich ist deutlich schneller (moderate Parallel-Last statt voller Ziel-Stream-Zahl).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-23)

## 1.22 · August 2026
- 🇬🇧 **Auto-Best** picks the best VPN server automatically (opt-in, only with 0 viewers); configurable target `vpn_min_streams`.
- 🇩🇪 **Auto-Best** wählt automatisch den besten VPN-Server (opt-in, nur bei 0 Zuschauern); Ziel `vpn_min_streams` einstellbar.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-22)

## 1.21 · August 2026
- 🇬🇧 Provider capacity test: set the stream count yourself (2–50).
- 🇩🇪 Anbieter-Kapazitätstest: Stream-Zahl selbst einstellbar (2–50).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-21)

## 1.20 · August 2026
- 🇬🇧 Performance watchdog no longer flaps (multi-segment measurement, median baseline, smoothing).
- 🇩🇪 Der Leistungs-Wächter zappelt nicht mehr (Messung über mehrere Segmente, Median-Baseline, Glättung).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-20)

## 1.19 · August 2026
- 🇬🇧 Automatic VPN server switch on poor performance (opt-in, self-baseline, configurable thresholds).
- 🇩🇪 Automatischer VPN-Serverwechsel bei schlechter Leistung (opt-in, Self-Baseline, einstellbare Schwellen).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-19)

## 1.18 · July 2026
- 🇬🇧 Provider server switching removed again (did not work with providers that bind the token to one server).
- 🇩🇪 Anbieter-Server-Umschaltung wieder entfernt (funktionierte nicht bei Anbietern mit server-gebundenem Token).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-18)

## 1.17 · July 2026
- 🇬🇧 Auto-switch to the best provider server (button + interval).
- 🇩🇪 Automatisch auf den besten Anbieter-Server umschalten (Knopf + Intervall).
- 📄 [README-WHATS-NEW.md](docs/README-WHATS-NEW.md)

## 1.16 · July 2026
- 🇬🇧 Auto-discovery of new provider servers.
- 🇩🇪 Neue Anbieter-Server automatisch entdecken.
- 📄 [README-WHATS-NEW.md](docs/README-WHATS-NEW.md)

## 1.15 · July 2026
- 🇬🇧 Force a preferred provider server (live only).
- 🇩🇪 Bevorzugten Anbieter-Server erzwingen (nur Live).
- 📄 [README-WHATS-NEW.md](docs/README-WHATS-NEW.md)

## 1.14 · July 2026
- 🇬🇧 Server comparison: Mbit/s column labelled as a rough single-connection probe.
- 🇩🇪 Server-Vergleich: Mbit/s-Spalte als grobe Einzelverbindungs-Stichprobe gekennzeichnet.
- 📄 [README-WHATS-NEW.md](docs/README-WHATS-NEW.md)

## 1.13 · July 2026
- 🇬🇧 Server comparison accepts full domains and URLs.
- 🇩🇪 Server-Vergleich nimmt ganze Domains und URLs an.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-13)

## 1.12 · July 2026
- 🇬🇧 Server comparison: enter your own servers (nothing provider-specific in the code).
- 🇩🇪 Server-Vergleich: Server selbst eintragen (nichts Anbieterspezifisches im Code).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-12)

## 1.11 · July 2026
- 🇬🇧 Server comparison to find the lowest latency from your VPN exit.
- 🇩🇪 Server-Vergleich, um die niedrigste Latenz vom VPN-Ausgang aus zu finden.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-11)

## 1.10 · July 2026
- 🇬🇧 The background sample uses only one provider connection and never disturbs viewers.
- 🇩🇪 Die Hintergrund-Stichprobe nutzt nur eine Anbieter-Verbindung und stört keine Zuschauer.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-10)

## 1.9 · July 2026
- 🇬🇧 Meaningful VPN server ranking, latency & jitter, steadier measurement, 24 h history with early warning.
- 🇩🇪 Sinnvolle VPN-Server-Rangliste, Latenz & Jitter, stabilere Messung, 24-h-Verlauf mit Frühwarnung.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-9)

## 1.8 · July 2026
- 🇬🇧 Provider capacity test (1–20 streams) reveals your subscription's connection limit.
- 🇩🇪 Anbieter-Kapazitätstest (1–20 Streams) deckt das Verbindungslimit deines Abos auf.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-8)

## 1.7 · July 2026
- 🇬🇧 Speedtest answers "can my setup handle X viewers?" (8 concurrent streams, traffic-light verdict).
- 🇩🇪 Der Speedtest beantwortet „packt mein Setup X Zuschauer?“ (8 gleichzeitige Streams, Ampel-Urteil).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-7)

## 1.6 · July 2026
- 🇬🇧 Internet speedtest runs in parallel and flags implausible results as unreliable.
- 🇩🇪 Der Internet-Speedtest läuft parallel und kennzeichnet unplausible Werte als unzuverlässig.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-6)

## 1.5 · July 2026
- 🇬🇧 Internet speedtest takes the fastest of several servers (no more absurdly low numbers).
- 🇩🇪 Der Internet-Speedtest nimmt den schnellsten mehrerer Server (keine absurd niedrigen Werte mehr).
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-5)

## 1.4 · July 2026
- 🇬🇧 More reliable speedtest (steady-state throughput) and proactive VPN data-flow check.
- 🇩🇪 Belastbarerer Speedtest (eingeschwungener Durchsatz) und proaktiver VPN-Datenfluss-Check.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-4)

## 1.3 · July 2026
- 🇬🇧 VPN server comparison and a fixed, absolute speedtest verdict.
- 🇩🇪 VPN-Server-Vergleich und korrigiertes, absolutes Speedtest-Urteil.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-3)

## 1.2 · July 2026
- 🇬🇧 Stability release: provider server changes without reloading playlists (stable channel ids), VPN failover, hardened VPN connection, several fixes.
- 🇩🇪 Stabilitäts-Release: Anbieter-Serverwechsel ohne Playlist-Neuladen (stabile Kanal-IDs), VPN-Ausweichen, gehärtete VPN-Verbindung, mehrere Fehlerbehebungen.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-2)

## 1.1 · June 2026 🔒
- 🇬🇧 Security & stability release: SSRF protection, hashed admin token, secure short tokens, "max streams"/"banned" as a video clip, XSS hardening, first test suite.
- 🇩🇪 Sicherheits- und Stabilitäts-Release: SSRF-Schutz, gehashter Admin-Token, sichere Short-Tokens, „Max. Streams“/„Gesperrt“ als Video-Clip, XSS-Härtung, erste Test-Suite.
- 📄 [RELEASE-NOTES.md](docs/RELEASE-NOTES.md#v1-1)

---

> **Before 1.1 / Vor 1.1 (May 2026 / Mai 2026):** catchup auto-live off by default, global diagnostics switch `diagnostics_enabled`, clearer catchup diagnostics · Catchup-Auto-Live standardmäßig aus, globaler Diagnose-Schalter `diagnostics_enabled`, klarere Catchup-Diagnose — [README-WHATS-NEW.md](docs/README-WHATS-NEW.md)
