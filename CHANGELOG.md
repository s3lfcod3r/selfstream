# 📰 Changelog

Newest version first. Full release notes are linked per version (in German).
Neueste Version zuerst. Die ausführlichen Release-Notes sind je Version verlinkt.

> **⚠️ Update tip / Update-Hinweis:** Update by pulling `ghcr.io/s3lfcod3r/selfstream:latest`; `update.sh` is a live patch for hotfixes and is lost when the container is recreated. ·
> Aktualisieren per `ghcr.io/s3lfcod3r/selfstream:latest`; `update.sh` ist ein Live-Patch für Hotfixes und geht beim Neuerstellen des Containers verloren.

---

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
