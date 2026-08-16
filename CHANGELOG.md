# Changelog

## v1.73 — Playlist verweist aufs eigene EPG + Archiv einsehbar

### ① Die Playlist schickte den Player direkt zum Anbieter
In die Kopfzeile der M3U (`url-tvg`) wurden bisher die **rohen Anbieter-Adressen** geschrieben.
Der Player holte die Programmdaten damit **direkt bei epg.team** — und umging Bereinigung,
Archiv und Quellen-Zusammenführung vollständig. Die gesamte Aufbereitung lief ins Leere, solange
man die eigene Adresse nicht von Hand eintrug.

Jetzt trägt die Playlist standardmäßig die **eigene** Adresse ein (`/iptv/epg-7d.xml`), also den
aufbereiteten Stand. Neues Häkchen in der EPG-Ansicht: „Playlist verweist auf das eigene EPG" —
abschaltbar, wer weiterhin direkt zum Anbieter will.

### ② Ins eigene Archiv hineinschauen
Das Panel zeigte bisher nur, **wie viel** im Archiv liegt, nicht **was**. Jetzt lässt sich je
Sender (Name oder Kanal-ID) und Tag nachsehen, was gespeichert wurde — mit Uhrzeiten in Ortszeit
und der ausdrücklichen Angabe, ob der Tag **überschneidungsfrei** ist.
Endpoint `GET /api/epg/archive/browse?channel=&day=&tz=`, rein lesend. Auch Sender einsehbar, die
im Archiv liegen, aber nicht mehr im Kanal-Manager stehen.


## v1.73 — Ins eigene EPG-Archiv hineinschauen

Bisher zeigte das Panel nur, **wie viel** im Archiv liegt — nicht **was**. Jetzt lässt sich je
Sender und Tag nachsehen, was gespeichert wurde, und mit dem Fernsehprogramm abgleichen.

- Sender per Name oder Kanal-ID eingeben, Tag wählen, **👁 Anzeigen**
- Zeigt alle Sendungen mit Uhrzeit in Ortszeit
- Meldet ausdrücklich, ob der Tag **überschneidungsfrei** ist — genau das war die Ursache dafür,
  dass im Catchup etwas anderes lief als angeklickt
- Auch Sender einsehbar, die im Archiv liegen, aber nicht mehr im Kanal-Manager stehen

Endpoint `GET /api/epg/archive/browse?channel=&day=&tz=`, rein lesend.


## v1.72 — Mehrere EPG-Quellen gleichzeitig nutzen

Bisher wurde nur die **erste** aktive EPG-Quelle verwendet, alle weiteren lagen brach. Jetzt werden
alle aktiven Quellen geladen und zusammengeführt.

**Die Regel ist bewusst einfach und nachvollziehbar:** Die erste Quelle gibt den Ton an, die
weiteren füllen ausschließlich **echte Lücken**. Eine schwächere Quelle kann eine gute damit nie
überschreiben — es wird nicht geraten, welche Quelle „recht hat".

- Sender werden über ihren Namen zugeordnet: `Sky Cinema Highlights HD` und
  `Sky.Cinema.Highlights.HD.de` finden zusammen (Groß-/Kleinschreibung, Punkte sowie Zusätze wie
  HD/UHD/de werden dabei ignoriert).
- Quellen im `.xml.gz`-Format werden automatisch entpackt — viele kostenlose Anbieter liefern so aus.
- Die zusammengeführte Datei wird erst als Nebendatei geschrieben und dann umbenannt; bricht ein
  Abruf ab, bleibt der bisherige Stand unangetastet.
- Neues Modul `backend/epg_merge.py`, arbeitet streamend.

Getestet mit zwei echten Quellen: 84.464 Sendungen aus der ersten, **263 Sendungen aus der zweiten
ergänzt** (136 Sender automatisch zugeordnet), Ergebnis 290 Sender mit **null Überlappungen** —
bei 4 Sekunden Laufzeit und 35 MB Speicherbedarf.


## v1.71 — Erststand schützen: das Archiv bleibt sauber, auch wenn der Anbieter nachträglich Unsinn liefert

Messung an fünf Tagen Abstand, dieselbe Quelle, derselbe Tag:

| Tag | am 11.08. abgerufen | am 16.08. abgerufen |
|---|---|---|
| 14.08. | 4 von 277 Sendern fehlerhaft | 65 von 287 |
| 15.08. | 1 von 268 | 68 von 287 |
| 16.08. | 2 von 233 | 20 von 286 |

Die Daten sind **im Voraus fast sauber** und werden **nachträglich verschmutzt** — der Anbieter
spielt später zusätzliche Programmlisten über bereits gelieferte Tage.

Deshalb nimmt das Archiv nachgelieferte Sendungen jetzt nur noch an, wenn sie sich **nicht** mit
bereits archivierten überschneiden (Häkchen „Erststand schützen", standardmäßig an). Was zuerst
kam, bleibt. Zusätzlich werden vermischte Programmlisten schon **beim Einlagern** aufgelöst, statt
erst beim Ausliefern.

Geprüft mit den echten Dateien beider Tage: 90.077 Sendungen aus dem sauberen Stand eingelagert,
danach aus dem verschmutzten Stand 29.169 neue übernommen und **55.295 nachträgliche Änderungen
abgewiesen**. Ergebnis für den 15.08.: **0 von 287 Sendern** mit Überlappung im Archiv — gegenüber
68 von 287 in der Rohdatei des Anbieters.

Damit wird das eigene Archiv zur besseren Quelle als der Anbieter selbst.


## v1.70 — Eigenes EPG-Archiv: Historie bleibt, auch wenn der Anbieter sie fallen lässt

EPG-Anbieter liefern nur ein **gleitendes Fenster** (bei epg.team gut zwei Wochen). Was dort
herausfällt, ist weg — auch für Catchup, wo gerade die Vergangenheit zählt.

selfstream schreibt jetzt bei jedem EPG-Abruf mit. Die Sendungen landen in der eigenen Datenbank
(Tabelle `epg_archive`) und werden beim Ausliefern wieder eingesetzt, sobald der Anbieter sie nicht
mehr führt. Aufgehoben wird standardmäßig **30 Tage**, einstellbar zwischen 7 und 365.

- Häkchen **„Lücken auffüllen"** und Feld für die Aufbewahrungsdauer in der EPG-Ansicht
- Knopf **„💾 Jetzt sichern"** stößt die Sicherung sofort an (`POST /api/epg/archive`)
- Die Anzeige nennt Umfang und Zeitraum des Archivs
- Gelesen wird **streamend**; das Sichern von rund 1.000 Sendungen dauert 0,6 s bei 8 MB
  Mehrverbrauch. Geschrieben wird blockweise zu je 5.000 Einträgen.

Zusammenspiel mit der Bereinigung aus v1.68: Die Archiv-Einträge werden **vor** dem Auflösen der
vermischten Programmlisten eingesetzt, damit nicht über den Umweg des Archivs wieder fremde Listen
hereinkommen. Geprüft, indem sämtliche Sendungen eines Senders aus der Quelle entfernt wurden:
Das Archiv stellte genau die echte Liste wieder her — 8 Sendungen, lückenlos, ohne Fremdeinträge
und ohne Überlappungen.

Der Schlüssel im Archiv ist (Sender, Startzeit, Endzeit): Zwei Sendungen mit gleicher Startzeit,
aber unterschiedlichem Ende sind verschiedene Sendungen und bleiben beide erhalten — sonst hätte
bei vermischten Listen die falsche die richtige überschrieben.


## v1.69 — Bereinigung wirft nur noch weg, was wirklich kollidiert

Die Bereinigung aus v1.68 verwarf ganze Programmlisten. Enthielt die verworfene Liste Sendungen für
Zeiträume, in denen die behaltene Liste gar nichts hat, entstanden dort **Lücken im Player**
("Keine Daten"), obwohl es an dieser Stelle nie einen Konflikt gab.

Jetzt wird aus den verworfenen Listen alles übernommen, was **in eine Lücke passt**; entfernt wird
nur, was sich tatsächlich mit der Hauptliste überschneidet. Geprüft: danach bleiben **null**
überlappende Sender übrig, die Bereinigung ist also weiterhin vollständig.

Hinweis für die Fehlersuche: Lücken können auch schlicht daher kommen, dass die Quelle nichts
liefert. Bei Sky Cinema Highlights am 11.08.2026 etwa fehlen im EPG von epg.team sämtliche
Vormittagsfilme (Apollo 13, Jurassic Park, Der Terminator, Beverly Hills Cop I + II); dort stand
nur eine erfundene zehnstündige "Sendepause". Solche Löcher kann selfstream nicht füllen — die
Prüfung "🔎 Prüfen" hilft, das auseinanderzuhalten.


## v1.68 — Vermischte Programmlisten bereinigen (Catchup zeigt die richtige Sendung)

Manche EPG-Anbieter legen **zwei komplette Programmlisten unter dieselbe Kanal-ID** (etwa Kabel- und
Sat-Variante). Die Sendungen überlappen sich dann, und im Player startet ein angeklickter
Catchup-Eintrag eine völlig andere Sendung als angezeigt. Reparieren lässt sich das nur beim
Anbieter — herausfiltern aber schon.

Neues Häkchen in der EPG-Ansicht: **„Vermischte Programmlisten bereinigen"** (standardmäßig aus).
Ist es gesetzt, werden die Sendungen je Sender auf überschneidungsfreie Spuren verteilt und nur die
Spur mit der größten Gesamtsendezeit behalten.

Die Regel ist gemessen, nicht geraten: An der Quelle epg.team deckt diese Spur bei **allen 128
betroffenen Sendern** den kompletten Zeitraum ab, die übrigen sind nur Einsprengsel — MDR Fernsehen
214 Stunden gegen 2, Sky Sport Top Event 300 gegen 4, Nitro 295 gegen 67. Zusätzlich gegen eine
unabhängige TV-Zeitschrift verifiziert: Bei Sky Cinema Highlights bleibt genau das echte Programm
übrig (11.08.: aus 11 überlappenden Einträgen werden 8 lückenlose).

Wirkt auf die gefilterten EPG-Adressen (1/3/7 Tage). Nach dem Umstellen einmal „↻ Neu laden".

Außerdem: `epg_dedupe_overlaps` und das in v1.64 eingeführte `epg_max_mb` waren nicht in der
Positivliste der Einstellungen — sie wurden beim Speichern stillschweigend verworfen. Behoben.


## v1.67 — Kein fremder Ballast mehr im EPG-Kanal-Manager

EPG-Anbieter liefern reihenweise Sender mit, die man nie bestellt hat (andere Länder, fremde
Pakete). Die landeten bisher **alle** im Kanal-Manager, und weg bekam man sie nicht: Sender ließen
sich nur an- und ausschalten, einen Lösch-Weg gab es weder in der Oberfläche noch im Backend.

- **„📡 EPG einlesen" übernimmt jetzt nur noch Sender, die es auch in der eigenen Kanalliste
  gibt.** Die Meldung sagt, wie viele fremde übersprungen wurden. Wer alles will, ruft die Route
  mit `?only_known=false` auf.
- **Neuer Knopf „🧹 Fremde entfernen"** räumt den vorhandenen Ballast in einem Rutsch weg
  (`DELETE /api/epg/channels/orphans`). Betrifft nur die EPG-Kanalliste — die eigenen Sender
  bleiben unberührt.

Nebenbei spart das Einlesen deutlich Arbeitsspeicher: Es liest die Datei jetzt **streamend** und
aus dem Plattencache, statt sie erneut komplett herunterzuladen und einen Objektbaum aufzubauen.

Gemessen an einer echten Quelle mit 298 Kanälen und drei eigenen Sendern: vorher 298 Einträge,
nach dem Aufräumen 3, beim erneuten Einlesen 3 übernommen und 295 übersprungen.


## v1.66 — EPG-Abrufe fressen keinen Arbeitsspeicher mehr

Trotz v1.64 lief der Speicher weiter voll (über 3 GB). Ursache waren **drei Abruf-Routen, die pro
Anfrage die komplette EPG-Datei in den Speicher holten** — und IPTV-Apps rufen die regelmäßig ab:

- **`/iptv/epg-1d|3d|7d.xml`** filterte bei **jedem** Abruf neu: Text + Quellbaum + Zielbaum +
  Ausgabe. Gemessen rund **290 MB pro Anfrage**. Hier fehlte außerdem noch das in v1.64 eingeführte
  Größenlimit.
- **`/iptv/{token}/epg.xml`** lud die Datei bei **jedem** Abruf frisch vom Anbieter und hielt sie
  im Speicher — ohne jede Wiederverwendung.
- **`/iptv/epg.xml`** lieferte den kompletten Text aus dem Speicher aus.

Behoben:
- Das tagesgefilterte Ergebnis wird **auf der Platte zwischengespeichert** und nur neu gebaut, wenn
  die Quelle frischer ist oder das Zeitfenster weitergewandert ist (stündlich). Zweiter Abruf:
  **0 Sekunden, kein zusätzlicher Speicher.**
- Alle drei Routen liefern jetzt per `FileResponse` **direkt von der Platte**, statt die Datei
  komplett im Speicher zu halten.
- Das Filtern läuft im Hintergrund-Thread, der Dienst bleibt währenddessen ansprechbar.

Hintergrund zur Größenordnung: Eine 48-MB-XMLTV-Datei belegt als Python-Text **205 MB**, weil die
kyrillischen Zeichen der Quelle vier Byte je Zeichen erzwingen; der Objektbaum kommt mit weiteren
234 MB obendrauf.


## v1.65 — EPG-Zeiten im Admin-Panel waren zwei Stunden zu früh

Bei „läuft gerade" zeigte das Panel die Sendezeiten in UTC — im Sommer also zwei Stunden zu früh
(die Tagesschau stand als „18:00" statt 20:00). Ursache: das Backend formatierte die Uhrzeit selbst,
statt sie wie die Diagnose-Zeiten roh zu liefern.

`_get_now_playing` gibt `start`/`stop` jetzt als vollständigen Zeitstempel mit Zeitzone zurück; die
Umrechnung macht das Panel über die **bereits vorhandene Einstellung `diagnostic_timezone`**
(Standard `Europe/Berlin`, „browser" möglich). Neue Hilfsfunktion `formatEpgClock` analog zu
`formatDiagTime`.

Damit bleibt es bei einer einzigen Zeitzonen-Einstellung, das Image braucht weiterhin **kein
tzdata**, und die Sommer-/Winterzeit stimmt automatisch (18:15 UTC → 20:15 im August, 19:15 im
Januar). Liefert ein älterer Server noch „18:00", wird das unverändert angezeigt.


## v1.64 — EPG frisst keinen Arbeitsspeicher mehr + Qualitätsprüfung der EPG-Quelle

### ① Arbeitsspeicher: Ursache für abgestürzte Container behoben
Große EPG-Quellen konnten den Container per OOM-Kill beenden. XMLTV wird zum Auswerten als
Objektbaum gehalten und belegt dabei ein Vielfaches der Dateigröße — bei einer 620-MB-Quelle
mehrere Gigabyte. Verschärft wurde das durch **fünf Stellen, die diesen Baum immer wieder neu
aufbauten**, statt den vorhandenen Cache zu nutzen:
- **Catchup-Abruf:** baute den Baum bei **jedem Zuschauer-Zugriff** neu — bei mehreren
  gleichzeitigen Zuschauern der direkte Weg in den OOM-Kill.
- **Catchup-EPG-Watchdog:** baute ihn bei jedem periodischen Durchlauf neu.
- Drei EPG-Hilfsfunktionen (`_epg_title_from_wall_time_channel`,
  `_epg_programme_stop_for_title_at_dt`, `_epg_slot_detail_at_dt`) ebenso.

Alle nutzen jetzt den gemeinsamen `_get_epg_root()`-Cache. Zusätzlich:
- **Download mit Größenlimit** (`epg_max_mb`, Standard 150 MB): die Quelle wird streamend geladen
  und bei Überschreitung abgebrochen — der bisherige Cache bleibt erhalten, statt dass der Dienst
  stirbt. Gilt für automatischen Abruf, `/iptv/epg.xml` und „↻ Neu laden".
- **Prüfsumme blockweise** statt über eine komplette Zweitkopie der EPG-Datei im Speicher
  (sparte bei jedem Aufruf eine Kopie in Dateigröße).
- Das Limit steht in der EPG-Ansicht neben Ladezeitpunkt und Größe.

### ② Neu: „Qualität prüfen" — findet vermischte Programmlisten
Manche EPG-Anbieter führen **zwei komplette Programmlisten unter einer Kanal-ID** zusammen (etwa
Kabel- und Sat-Variante). Die Sendungen überlappen sich dann, und im Player startet ein
angeklickter Catchup-Eintrag eine **andere Sendung als angezeigt**. An der Software liegt das nicht
— nur an den Daten, und bisher war das von außen nicht erkennbar.

Die EPG-Ansicht hat jetzt einen Knopf **🔎 Prüfen** (optional nach Tag und Sender gefiltert):
- meldet, wie viele Sender betroffen und wie viele sauber sind,
- listet die betroffenen Sender mit Kanal-ID und Anzahl vermischter Listen,
- zeigt für die auffälligsten Sender beide Programmlisten nebeneinander, damit erkennbar ist,
  welche zum echten Feed gehört.

Umgesetzt in `backend/epg_quality.py` (Interval Partitioning) — liest die Datei **streamend**, baut
also selbst keinen Objektbaum auf: eine 50-MB-Quelle wird in unter einer Sekunde mit rund 45 MB
Spitzenverbrauch geprüft. Endpoint `GET /api/epg/quality?day=&channel=&tz=&details=`.


## v1.63 — Speedtest neu: Flaschenhals VPN vs. HLS + Server-Durchsatz-Vergleich

### ① Flaschenhals-Analyse (zuschauer-sicher UND genau)
- Der Speedtest sagt jetzt klar, **wo der Flaschenhals liegt**: 🔒 **VPN-Tunnel** oder 📡 **HLS-Anbieter**
  (Signalquelle) – mit farbigem Urteil.
- **Schauen gerade Leute:** der Anbieter-Weg wird aus ihren **echten Segmenten** gemessen (exakt, stört
  niemanden), der VPN-Weg nur per **Latenz** (keine Bandbreite). **Niemand da:** beide Wege voll gemessen.
- Kein 100-MB-Download mehr, während Zuschauer schauen → kein Ruckeln durch den Test.
- Klarere zwei Spalten (VPN-Tunnel / HLS-Anbieter) + Klartext-Urteil.

### ② Server-Durchsatz-Vergleich (welcher Mullvad-Server ist am schnellsten)
- Neuer Knopf „🏁 Server-Durchsatz vergleichen" (+ optionaler Land-Filter): rankt Server nach **echtem
  Durchsatz**, nicht nur Latenz.
- **Zuschauer-sicher:** schaut jemand → nur Latenz-Rangliste (störungsfrei). Niemand da → jeder Server
  wird kurz durchgemessen (nahtloser Peer-Wechsel) und danach **immer der ursprüngliche Server
  wiederhergestellt** (auch bei Fehler, via `finally`).
- Endpoint `GET /api/vpn/throughput-compare?country=`.


## v1.62 — Diagnose-Tools zuschauer-/tunnelsicher gemacht

Audit aller Hintergrund-/Diagnose-Funktionen, damit KEINE davon Ausfälle verursacht:
- **Speedtest – Flaschenhals-Analyse:** öffnete bisher fest 5 parallele Anbieter-Streams (= 5 Lines)
  ohne Rücksicht auf Zuschauer → konnte sie verdrängen („max streams"). Jetzt **Zuschauer-Schutz**:
  Test-Streams werden auf die freien Lines begrenzt (eine bleibt als Puffer frei); sind keine frei,
  wird der Anbieter-Test ausgesetzt (mit Hinweis) statt Zuschauer zu verdrängen.
- **Auto-Best:** Latenz-Messung fasst die /32-Route des AKTIVEN Servers jetzt garantiert nie an
  (neuer `active_ip`-Schutz in `_measure_server_latency` + gemeinsamer Helper `_active_endpoint_ip`).
  War vorher schon sicher (misst nur Kandidaten), jetzt zusätzlich hart abgesichert.
- **Canary:** bereits in v1.60 auf eigenen frischen Client umgestellt + line-schonend (pausiert nahe
  Limit); fasst keine Routen an. Bestätigt sicher.
- Alle Diagnose-Helfer nutzen frische httpx-Clients (kein Cross-Loop mit dem Proxy-Client).


## v1.61 — HOTFIX: Server-Latenz-Check riss den Tunnel ab

- **Behoben: „Server-Latenz prüfen" ließ alle Streams abbrechen.** Der Check setzt pro Server kurz
  eine /32-Direktroute und löscht sie danach. Für den **aktuell aktiven** Mullvad-Server wurde damit
  auch dessen Endpoint-Route gelöscht – genau die Route, über die WireGuard seinen Server erreicht.
  Ohne sie läuft der Verkehr zum Server in den Tunnel selbst (Routing-Schleife) → Tunnel tot → alle
  Streams weg. Der Latenz-Check lässt den aktiven Server jetzt **komplett aus** (fasst dessen Route
  nie an; er ist über die bestehende Endpoint-Route ohnehin direkt messbar).
- (Auto-Best war nie betroffen – der misst den aktiven Server ohnehin nicht mit.)


## v1.60 — HOTFIX: Streams brachen ab (Cross-Event-Loop)

- **Behoben: Streams brachen mit `RuntimeError: bound to a different event loop` ab** (VLC/Player
  „konnte nicht öffnen"). Zwei Ursachen, beide behoben:
  1. **Canary-Selbstabruf nutzte den geteilten Proxy-Client.** Der Canary läuft im Hintergrund-Loop;
     `_get_segment()` (und damit der geteilte httpx-Client) gehört aber dem Proxy-Loop. Beim
     Leerlauf-Selbstabruf band der Canary den Client an den falschen Loop → der nächste echte
     Zuschauer-Stream im Proxy-Loop starb cross-loop. Der Canary nutzt jetzt einen **eigenen
     frischen Client** (Passiv-Proben werden weiter gefüttert).
  2. **`_reset_iptv_client()` wurde aus fremden Loops aufgerufen** (Auto-Best-Wächter, `vpn_switch`)
     und schloss (`aclose`) den geteilten Proxy-Client, während der Proxy gerade Segmente lud →
     laufende Requests starben. Reset ist jetzt **loop-sicher**: `aclose` nur im eigenen Loop,
     sonst wird die Referenz nur losgelassen (nächster Proxy-Request erstellt einen frischen Client).
- Regression aus v1.55/v1.56 (nahtloser Wechsel + Auto-Best), verstärkt durch aktiviertes Auto-Best.


## v1.59

### Alarm-Mail am VPN vorbei + WireGuard-Selbstreparatur
- **E-Mail immer direkt (nicht durch den Tunnel):** Die Alarm-/Test-/Heartbeat-Mail wird jetzt
  über eine stream-sichere Direktroute zum SMTP-Server (übers echte LAN-Gateway) verschickt –
  am VPN-Tunnel vorbei. Das löst zwei Probleme: (1) Mail-Provider wie Strato blocken oft VPN-IPs
  beim SMTP; (2) bei totem Tunnel käme die Mail sonst gar nicht raus – genau dann, wenn man den
  Alarm braucht. Nur aktiv, wenn WireGuard läuft; ohne VPN unverändert direkt.
- **WireGuard-Selbstreparatur (Handshake-Check):** Der Watchdog erkennt jetzt einen leise toten
  WireGuard-Tunnel am **Handshake-Alter** (`wg show … latest-handshakes`, tot ab ~200 s ohne
  frischen Handshake) – vorher sah `wg0` immer „oben" aus. Ehrlicher „VPN unten"-Status +
  automatischer Neuaufbau.
- **Ausweichen auf anderen Server jetzt auch für WireGuard:** Die Eskalation (mehrere Neustarts
  erfolglos → anderer Server) rotiert bei WireGuard unter den `.conf`-Servern (vorher nur `.ovpn`).
  Ein toter Mullvad-Server wird so automatisch gegen einen anderen getauscht.

### Nur Anbieter-Verkehr durch den Tunnel – klargestellt
- Anbieter (m3u/m3u8/HLS) und EPG laufen weiterhin durch den VPN-Tunnel; die einzige bewusste
  Ausnahme ist jetzt die E-Mail (siehe oben). Admin-Zugriff aus dem LAN war schon immer direkt.


## v1.58

### Tages-Filter bei den Buffering-Ereignissen
- Neuer **Tag-Filter** in der Toolbar der Buffering-Ereignisse: „Alle Tage" oder ein einzelner Tag
  (Heute, Gestern, Datum). Wirkt **zusammen** mit dem bestehenden User-Filter (Tag + User gleichzeitig).
- Läuft rein im Browser über die schon geladenen Ereignisse (lokale Tagesgrenzen, passend zur Zeit-Spalte)
  – kein zusätzlicher Server-Aufruf. Es werden nur Tage angeboten, für die auch Daten vorliegen (innerhalb
  des oben gewählten Bereichs Heute/7/30/90 Tage).


## v1.57

### Canary-Verlauf: 30 Tage + Tages-Filter im Statistik-Popup
- Der Selbst-Zuschauer-Verlauf wird jetzt **30 Tage** aufbewahrt (vorher nur die letzten
  500 Messungen ≈ ~4 Stunden). Speicherung in einer eigenen DB-Tabelle `canary_events`
  mit echtem 30-Tage-Purge (wie die Buffering-Ereignisse) statt als JSON-Blob in den
  Settings – dadurch auch bei tausenden Messungen schnell und schonend.
- **Tages-Filter** oben im Statistik-Popup: „Alle (letzte 30 Tage)" oder ein einzelner Tag
  (Heute, Gestern, Datum). Die Tagesgrenzen richten sich nach deiner lokalen Zeit (Browser),
  passend zur angezeigten Zeit-Spalte.
- Die **Statistik** (Messungen, % flüssig, Ø Reserve, Ø Mbit/s, Zähler) wird immer über den
  **ganzen** gewählten Zeitraum in SQL gerechnet; Liste + Balken zeigen die jüngsten 500.
- Bestehender Verlauf wird beim Update **einmalig migriert** (aus dem alten Setting in die
  neue Tabelle), geht also nicht verloren.
- Endpoint erweitert: `GET /api/vpn/canary/history?from=<ts>&to=<ts>` (Unix-Sekunden).


## v1.56

### Auto-Best für WireGuard (nahtlos, auch mit Zuschauern)
- Neuer Hintergrund-Wächter: läuft die Qualität schlecht (echtes Ruckeln, aus den
  Zuschauer-Segmenten gemessen – `_passive_health`), sucht SelfStream automatisch den
  schnellsten erreichbaren Alternativ-Server und schaltet **nahtlos** dorthin (Peer-Tausch
  auf dem liven wg0, kein Tunnel-Abriss – auch während Zuschauer schauen).
- Server-Auswahl per **stream-sicherer Latenz-Messung** (kurze /32-Direktroute übers echte
  LAN-Gateway, geht nicht durch den Tunnel). Ohne Land-Vorgabe bleibt er beim Land des
  aktiven Servers; sehr große Serverlisten werden gleichmäßig auf 12 Kandidaten gedünnt.
- **Cooldown** (Standard 30 Min) verhindert ständiges Hin- und Herspringen. Reagiert nur auf
  echtes Ruckeln bzw. Durchsatz unter der einstellbaren **Schwelle** (Standard 12 Mbit/s).
- Neue UI-Karte „🏆 Auto-Best (WireGuard, nahtlos)" im VPN-Bereich: An/Aus, Schwelle,
  Cooldown, Land + Anzeige des letzten automatischen Wechsels.
- Endpoints: `GET/POST /api/vpn/wg-autobest`.


## v1.55

### Nahtloser WireGuard-Server-Wechsel (kein Abbruch)
- Server umschalten reißt den Tunnel nicht mehr ab. Bei WireGuard bleibt das Interface (wg0)
  oben – nur der Peer (Server) und die Endpunkt-Route werden live getauscht
  (`wg set wg0 peer …`). Das funktioniert praktisch ohne Unterbrechung, **auch während
  Zuschauer schauen**. (Vorher: Tunnel-Neustart, Streams brachen ~10s ab.)
- „Aktivieren" und „Wechseln" in der VPN-Liste nutzen jetzt beide den nahtlosen Weg
  (Fallback auf Neustart nur, wenn kein WireGuard-Tunnel aktiv ist).
- Nach dem Wechsel wird der IPTV-Client zurückgesetzt, damit neue Segmente sofort über den
  neuen Server laufen.


## v1.54

### → USER-Strecke jetzt PRO USER
- Die Auslieferung SelfStream → Gerät wird jetzt pro User gemessen. Im Buffering-Bereich
  siehst du je User das Tempo (🔴 <15 = Geräte-Verbindung wahrscheinlich Flaschenhals,
  z.B. dessen 5G · 🟡 <40 grenzwertig · 🟢 ok). Meldet jemand Probleme, siehst du sofort,
  ob nur SEINE Auslieferung langsam ist (sein Netz/Gerät) oder alle (Server/Anbieter).
- Ergänzt den bestehenden User-Filter der Buffering-Ereignisse (Anbieter-Strecke pro User).


## v1.53

### Canary nutzt Zuschauer-Segmente (kein doppeltes Messen)
- Sind Zuschauer aktiv, misst der Canary jetzt NUR deren echte Segmente (passive Probe) –
  KEIN eigener Abruf mehr → belegt keine Line, keine Konkurrenz. Status zeigt
  „Quelle: echter Zuschauer-Verkehr".
- Nur wenn NIEMAND schaut, holt der Canary selbst 3 Test-Segmente (Reserve-Metrik).
- Statistik: Zuschauer-Messungen erscheinen mit „👥 User" statt Segment-Zähler.


## v1.52

### Canary schont die Lines noch besser (sequenziell + pro Segment prüfen)
- Der Selbst-Zuschauer prüft jetzt VOR JEDEM Segment neu, ob eine Line frei ist. Kommt
  mitten in der Messung ein Zuschauer, hört er sofort auf und lässt ihm die Line
  (nie mehr als eine Line gleichzeitig belegt).
- „Für Zuschauer aufgehört" zählt NICHT als Ruckeln mehr: eigener Status „⏸️ pausiert",
  reine Pausier-Zyklen landen nicht im Verlauf/der Statistik (keine falschen „ruckelt").
- (Zusammen mit korrektem line_capacity=4 klaut der Canary nie eine Zuschauer-Line.)


## v1.51

### Speedtest ehrlich dargestellt (WireGuard)
- Alt-Warnung der entfernten „Alle Server vergleichen"-Funktion entfernt.
- Klarer Hinweis: Internet/VPN-Speedtest ist durch JEDES VPN unzuverlässig (öffentliche
  Test-Server drosseln VPN) → der Canary ist der verlässliche Durchsatz-Wert. Anbieter-
  Kapazitäts-Test bleibt aussagekräftig (läuft durch den aktiven Tunnel).


## v1.50

### OpenVPN aus der Oberfläche entfernt · Test-Tools auf WireGuard
- ENTFERNT (OpenVPN-only): Zugangsdaten-Feld, „Automatisch besten Server", „Durchsatz-
  Vergleich (Weg 2)", „Alle VPN-Server vergleichen". Upload akzeptiert nur noch .conf
  (WireGuard). Titel/Labels WireGuard-fokussiert. ExpressVPN-Dateien gelöscht.
- Server-Latenz-Prüfung (Weg 1) auf WireGuard umgebaut: liest den `Endpoint` aus der
  .conf, misst störungsfrei zu jedem Mullvad-Server (echtes LAN-Gateway via gesichertem
  Original), Rangliste + ⇄ Wechseln-Knopf (funktioniert mit WireGuard).
- Der Canary misst den echten Durchsatz des aktiven Servers weiterhin laufend.


## v1.49

### Neu: „→ USER"-Messung (SelfStream → Player)
- Zeigt jetzt beide Strecken: bisher nur Anbieter→SelfStream (grün), jetzt auch wie schnell
  SelfStream die Segmente ans Gerät ausliefert. Niedrig bei schnellem Anbieter → Flaschenhals
  ist die Geräte-Verbindung (z.B. 5G/mobil), nicht SelfStream/VPN.
- Gemessen an der Ausliefer-Schleife (Backpressure = echtes Client-Tempo). Anzeige im
  Buffering-Bereich; Endpunkt `GET /api/segment-events/outbound`.


## v1.48

### Fix: WireGuard-DNS (behebt Segment-Aussetzer)
- Canary zeigte über WireGuard top Durchsatz (~145 Mbit/s, 0,2s) aber nur 1-2/3 Segmente
  → flaky Container-DNS. Jetzt setzt SelfStream beim WireGuard-Start Mullvads DNS
  (10.64.0.1) + Quad9-Fallback und stellt das Original beim Teardown wieder her.


## v1.47

### Fix: WireGuard startet jetzt (manuell statt wg-quick)
- wg-quick scheiterte im Container an `sysctl src_valid_mark` (Docker sperrt das).
  Jetzt bringt SelfStream WireGuard SELBST hoch: ip link + wg set + Adresse + MTU,
  Endpoint-Route via echtem Gateway (kein Rückschleifen), Default via wg0
  (redirect-gateway-Äquivalent), LAN-Ausnahme fürs Panel.
- Original-Default-Route wird gesichert und beim Teardown wiederhergestellt (Internet bleibt).


## v1.46

### Fix: WireGuard-Start im Container (resolvconf fehlte)
- wg-quick scheiterte am letzten Schritt (`resolvconf: command not found`) beim DNS-Setzen.
  Fix: DNS- (und Killswitch-)Zeilen werden vor dem Start entfernt – Container-DNS reicht
  fürs Proxying, PostUp/PreDown würden das Panel aussperren. Interface/Adresse/Routing
  kamen bereits sauber hoch → WireGuard läuft damit.


## v1.45

### Neu: Mullvad – alle Server automatisch importieren
- Eine Mullvad-.conf hochladen genügt: SelfStream zieht PrivateKey+Address daraus, holt die
  Serverliste von Mullvads öffentlicher API und erzeugt pro Server eine WireGuard-.conf
  (optional nach Land gefiltert). Kein 555×-Download mehr.
- Endpunkte `POST /api/vpn/mullvad-import` + `GET /api/vpn/mullvad-countries`; UI-Box im
  VPN-Bereich (Quelle wählen, Land wählen, „Alle importieren"). Schlüssel bleibt lokal.


## v1.44

### Neu: WireGuard-Support (neben OpenVPN, auswählbar)
- Du kannst jetzt **WireGuard-Configs (.conf)** hochladen (z.B. von Mullvad) – neben den
  bestehenden OpenVPN **.ovpn**. SelfStream erkennt den Typ automatisch an der Endung.
- WireGuard läuft über `wg-quick` (gleiche Split-Logik: alles durch den Tunnel, LAN/Panel
  bleibt via eth0 erreichbar). Kein Prozess-Zwang im Wächter – WG-Gesundheit über das
  Interface (wg0) geprüft. OpenVPN bleibt unangetastet als Fallback.
- Datei-Liste zeigt pro Config ein Typ-Badge (WireGuard/OpenVPN). Upload akzeptiert .ovpn + .conf.
- Dockerfile: wireguard-tools + iptables ergänzt.
- Hinweis: WireGuard ist schneller + CPU-schonender als OpenVPN (behebt den OpenVPN-Engpass).


## v1.43

### User-Filter + echte 30-Tage-Aufbewahrung für Qualitäts-Events
- Buffering-/Qualitäts-Events (pro User + Kanal, mit Zeit) haben jetzt einen
  **User-Filter** (Dropdown „Alle User" / einzelner User) neben dem Tages-Filter.
- **Echte 30-Tage-Löschung:** `purge_segment_events(30)` beim Start UND alle 500 Events
  (vorher wurden Zeilen nie gelöscht, nur beim Lesen gefiltert → Tabelle wuchs endlos).
- Neuer Endpunkt `/api/segment-events/users`.


## v1.42

### Canary-Statistik-Popup + 24/7 leichter einstellbar
- Neuer Knopf „📊 Statistik" beim Selbst-Zuschauer: Popup mit Verlauf der Messungen
  (persistiert, überlebt Neustart): Zusammenfassung (% flüssig, Ø/schlechteste Reserve,
  Ø Durchsatz, Ampel-Zählung), Balken-Verlauf und Tabelle. Endpunkte
  `GET /api/vpn/canary/history` + `POST /api/vpn/canary/history/clear`.
- Prüf-Intervall jetzt 0–9999 Stunden (0 = 24/7); Hinweis klarer: 0 = dauerhaft (alle 30s),
  höhere Zahl = seltener.


## v1.41

### Ruckel-Frühwarner: fehlende Segmente zählen jetzt als Stocker
- Live-Test zeigte: Reserve meldete „flüssig" (0,47), obwohl 1 von 3 Segmenten NICHT kam.
  Ein fehlendes Segment ruckelt aber garantiert. Fix: `_reserve_level(ratio, got, of)`
  wertet Segment-Verluste mit — <100% geladen ⇒ mind. „knapp", ≥50% weg ⇒ „ruckelt".


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
