# What's new — former README notes / frühere README-Neuigkeiten

Moved here unchanged from the old `README.md` (v1.1 → v1.56). Current summary: [CHANGELOG.md](../CHANGELOG.md).<br>
Unverändert aus der alten `README.md` hierher verschoben (v1.1 → v1.56). Aktuelle Kurzfassung: [CHANGELOG.md](../CHANGELOG.md).

**[🇬🇧 English](#english) · [🇩🇪 Deutsch](#deutsch)**

---

<a id="english"></a>

# 🇬🇧 English

## What's New (August 2026 – v1.44 → v1.56)

- **Switched to WireGuard + Mullvad.** The built-in VPN now runs **WireGuard** instead of OpenVPN — much faster and far more CPU-efficient (in practice ~6× the throughput of the old OpenVPN tunnel). OpenVPN was removed from the UI; upload is `.conf` only.
- **Mullvad auto-import.** Upload a single Mullvad `.conf` and SelfStream pulls every WireGuard server from Mullvad's API (optionally by country), generating one config per server automatically — no more uploading hundreds of files by hand.
- **Seamless server switch (no interruption).** Changing the exit server no longer tears down the tunnel. The `wg0` interface stays up and only the peer (server + endpoint) is swapped live — practically zero interruption, **even while viewers are watching**. Both "Activate" and "Switch" use this path.
- **Auto-Best for WireGuard (seamless).** A background watcher reacts to **real stuttering** (measured from actual viewer segments) and seamlessly switches to the fastest reachable alternative server, with a configurable throughput threshold and cooldown to prevent flapping. Candidate ranking uses a **stream-safe latency probe** (test packets never go through the tunnel). New endpoints `GET/POST /api/vpn/wg-autobest`.
- **Two-leg buffering visibility.** Traffic now measures both legs separately: **provider → SelfStream** (from real viewer segments, shown per user) and **SelfStream → device** (the outbound `→ USER` speed, per user) — so you can tell at a glance whether a viewer's problem is the provider/server or that person's own connection (e.g. their 5G). Buffering events keep a real 30-day history with a user filter.
- **Canary is line-friendly.** SelfStream's own test-viewer uses the real viewers' segments when someone is watching (self-fetches only when idle) and pauses near the connection limit, so it never steals a line from a real viewer.

---

## What's New (August 2026 – v1.27)

- **Measurement is now PASSIVE — no more active probing that disrupts streams.** The old "auto-switch on poor performance" watchdog pulled extra segments from the provider every 2 minutes, competing with live streams and causing stutter (especially on a limited/slow provider, and with many users there's practically never "0 viewers"). **Removed.** Instead, SelfStream now reads the fetch time of every real segment the viewers already request (`_get_segment`) and derives the actually experienced quality (median fetch time, error rate, throughput → ok/slow/bad). **Zero added load, works while watching, can't disrupt the stream.** The health sampler, self-check and email alert all run on this passive signal; only when idle (no real traffic) does a single light check keep the history graph alive. On a mid-viewing drop: **alert only, no auto-switch.** Emergency failover, nightly Auto-Best (0 viewers) and manual tools stay.

---

## What's New (August 2026 – v1.26)

- **Bug fixes from a code review:** alert email now retries each sample until one actually goes out (a failed first send no longer silences the whole outage); a failed VPN restart is no longer counted as a successful switch (no more 30-min blind cooldown); the health sampler pauses during a VPN server comparison (no false-alarm email for a deliberate test); a manual "compare only" no longer postpones the scheduled Auto-Best run; the "Test now" button can't get stuck on "Measuring…".

---

## What's New (August 2026 – v1.25)

- **Self-check + email alerts.** SelfStream monitors itself (VPN tunnel, provider reachability, throughput/latency via the 5-min sample) and sends **one** email on a **sustained** problem, plus an **all-clear** when it recovers (deduped — no spam). Optional **daily heartbeat** ("all ok"). Fully configurable SMTP (server/port/STARTTLS·SSL/user/password/recipient). Config + status light + "Send test email" at the top of the Diagnostics page. New endpoints `GET/POST /api/alerts`, `POST /api/alerts/test`.

---

## What's New (August 2026 – v1.24)

- **Automatic VPN switches now only happen with 0 viewers.** A server switch always briefly interrupts ALL streams (single tunnel). The performance watchdog no longer switches mid-viewing: if it detects a weak server while someone is watching, it waits (log "⏸️ … switch only at 0 viewers") and switches once free. Auto-Best already ran only with 0 viewers. The emergency failover (dead tunnel) stays — it only recovers already-broken streams.

---

## What's New (August 2026 – v1.23)

- **Fixed: Auto-Best comparison was far too slow** (minutes per server). The sweep measured with the full target stream count (e.g. 10), hitting the provider's ~10-connection limit → stalls/timeouts. It now measures a moderate parallel load (max 5 streams) and derives "handles ~N streams" from total throughput (target = N × 8 Mbit/s). Much faster and easier on the limit.

---

## What's New (August 2026 – v1.22)

- **Auto-Best: automatically pick the best VPN server** (opt-in). SelfStream periodically measures ALL uploaded .ovpn files and switches to the fastest on its own. The full comparison briefly interrupts all streams (single tunnel), so it runs **only with 0 viewers** and at most every `vpn_autobest_hours` hours (configurable). Complements the self-baseline performance watchdog (fast reaction to drops) with the question "which server is absolutely the best?".
- **Configurable target "must be good for N streams"** (`vpn_min_streams`, default 10). The comparison measures with that many streams and reports "handles ~N streams" per server (target = N × 8 Mbit/s ≈ Full-HD). Warns when even the best server can't safely reach the target (then it's the provider/line, not the VPN).
- New endpoints `GET/POST /api/vpn/autobest` and `POST /api/vpn/autobest-now`, plus a "🔍 Find & switch to best now" button.

---

## What's New (August 2026 – v1.21)

- **Provider capacity test: set the stream count yourself.** Instead of a fixed 1–20, there's now an input field "up to N concurrent streams" (2–50). The test stages adapt automatically.

---

## What's New (August 2026 – v1.20)

- **Performance watchdog: fixed flapping / over-eager switching.** The perf check took a single 1-segment probe, which is noisy (14 %↔55 % on the same server in the log) and caused false "weak" readings plus server flapping. Three fixes: it now measures over multiple streams/segments (stable number instead of noise), the baseline is the **median** (typical value) instead of a percentile best-value, and the current value is **smoothed** (median of the last 3 measurements). Only a real, sustained drop triggers a switch now.

---

## What's New (August 2026 – v1.19)

- **Automatic VPN-server switch on poor performance** (opt-in). A new performance watchdog continuously measures the currently connected VPN server (throughput + response time/ping to the provider, gently via a single connection) and compares it against its *own* usual performance ("self-baseline", percentile over a rolling window). If throughput drops **below a configurable percentage** of its best, OR latency rises **above a configurable percentage**, SelfStream switches to the next uploaded `.ovpn` after 3 weak measurements in a row — with a 30-minute cooldown against flip-flopping. Both thresholds are set in the panel; a **"Test now"** button shows current vs. baseline and whether it would switch, without switching. Complements the existing emergency failover (which only reacts to a dead tunnel). New endpoints: `GET/POST /api/vpn/perf`, `POST /api/vpn/perf/test`.

---

## What's New (July 2026 – v1.18)

- **Removed provider-server switching** (server comparison, "force preferred server", auto-switch, server discovery). These didn't work with providers that bind the token to a fixed server: rewriting to another server triggered a "SERVER CHANGED" block at the provider, and latency measurements of other servers were actually measuring that notice rather than real streams. To avoid misdiagnosis and interrupted streams they were removed entirely. Everything else stays: VPN watchdog with outage detection/failover, speedtest incl. capacity test, latency/jitter display, VPN-server comparison, and the automatic history with early warning.

---

## What's New (July 2026 – v1.17)

- **Auto-switch to the best server** – New in the "preferred server" box. A **"🎯 Find & switch to the best server now"** button checks all servers immediately and sets the preferred one to the lowest-latency server. Plus an **automatic mode**: enable via checkbox with a **configurable interval** (every X hours, 1–168) — SelfStream then regularly finds the best server and switches on its own. Automatic switching only happens on a **clear** improvement (>30% lower latency) to avoid flip-flopping; the button always switches to the best. Every switch is logged to diagnostics.

---

## What's New (July 2026 – v1.16)

- **Auto-discover new provider servers** – SelfStream now keeps a **server registry** (which servers it has seen) and **looks for new ones automatically**: the server comparison and a daily background check also probe numbered servers **beyond the highest known number**. When a new server appears you get a hint — a **"🆕 newly discovered: …"** banner in the comparison and an entry in diagnostics. So you won't miss a new, possibly faster server. Generic (no provider-specific servers in code); the background check skips when the connection limit is nearly full.

---

## What's New (July 2026 – v1.15)

- **Force a preferred server** – New field in the server comparison. Enter a server (e.g. `6` or `6.example.net`) and SelfStream rewrites **all channels to that server** at play time — regardless of which server the provider playlist hands out. This lets you move to a lower-latency server even if your provider panel doesn't allow it (the token is preserved). Takes effect **immediately** and, thanks to the stable channel ids (`/live`), **without reloading devices**. Empty = off. Live only; catchup is untouched.

---

## What's New (July 2026 – v1.14)

- **Server comparison: clearer Mbit/s column** – The Mbit/s in the server comparison is only a rough single-connection probe (it falls with latency for physical reasons) and is now labelled accordingly; latency is what decides, and real capacity is shown in the main speedtest.

---

## What's New (July 2026 – v1.13)

- **Server comparison: enter full domains** – You can now enter the **complete server domains** in the field (one per line or comma-separated, e.g. `de.example.net`) – full URLs are accepted too (only the host is used). Short labels (`de`, `2`) still work and get appended to your current server's domain. The input field is now multi-line.

---

## What's New (July 2026 – v1.12)

- **Server comparison: enter your own servers** – The servers to compare are now entered in a field (labels like `de`, `nl`, `2`, or full hostnames) — **no provider-specific servers are hardcoded**. Works with any provider/setup, and nothing about a specific provider ends up in the repository.

---

## What's New (July 2026 – v1.11)

- **Server comparison (find the lowest latency)** – New button in the speedtest. It tries the servers you entered through your VPN by inserting them into a real channel URL, and measures **latency + a quick throughput** per server. This finds the server with the **lowest latency from your VPN exit** — the direct lever against sluggish channel switching. Servers whose token is bound to a fixed server show as "unusable"; switching then only works via the provider panel.

---

## What's New (July 2026 – v1.10)

- **Background sample can't disturb viewers** – The automatic history sample now uses only one provider connection and skips entirely when the connection limit is nearly full.

---

## What's New (July 2026 – v1.9)

- **VPN server comparison now ranks meaningfully** – It used to compare servers via the internet speedtest, which is unreliable through a VPN (throttled/blocked VPN IPs). It now measures **IPTV provider throughput + latency** per server and ranks by that — i.e. by how well your streams actually run over each server.
- **Latency & jitter** – Stutter often comes from latency/jitter, not bandwidth. The IPTV test now reports **latency + jitter** to the provider and warns on an unstable connection.
- **Steadier measurement** – The IPTV test now measures each stream over **several segments** instead of one tiny chunk that finished in under a second, so results are far less noisy.
- **Automatic history + early warning** – SelfStream takes a light background sample (latency, throughput, VPN state) every 5 minutes and keeps a **24 h history**, so **intermittent** problems become visible (e.g. "slow in the evenings") that a one-off test misses. New "Show history" button with a bar chart; sustained problems are also logged to diagnostics. Samples are skipped when the connection limit is nearly full, to avoid disturbing viewers.

---

## What's New (July 2026 – v1.8)

- **Provider capacity test (1–20 streams)** – New button in the speedtest. Measures the IPTV provider at **increasing concurrency** (1, 2, 4, 8, 12, 16, 20) and shows in a table how per-stream throughput develops and **at what point failures start** — which directly reveals your **subscription's connection limit** (the level where streams begin to fail) and the point where per-stream bandwidth drops below Full-HD. Green = smooth, yellow = HD only, red = failure. A deliberate button with a warning, since it briefly uses up to 20 provider connections and can disturb active viewers.

---

## What's New (July 2026 – v1.7)

- **Speedtest now answers "can my setup handle X viewers?"** – The IPTV test now simulates **8 concurrent streams** (instead of 5) — the realistic case of several viewers over the same VPN — and gives a clear traffic-light verdict: "✅ 8 concurrent streams no problem — enough for 8× Full-HD/4K", or a warning if it isn't enough or some test channels are unreachable. The verdict uses the **per-stream throughput under full load** (total ÷ streams), i.e. exactly what each viewer actually gets at peak. The banner is green for "all good", red for a real warning.

---

## What's New (July 2026 – v1.6)

- **Internet speedtest now parallel + honest** – Public speedtest servers throttle or block VPN IPs, so the internet figure sometimes showed absurdly low numbers (e.g. 3 Mbps) even though the tunnel does 400+ over the same path (the IPTV test proved it). The measurement now runs **in parallel** (multiple connections, aggregated) like the IPTV test to pull the realistic throughput from throttled mirrors; and if it's still implausibly far below the real tunnel throughput, it's flagged as **unreliable** (pointing to the trustworthy IPTV parallel figure) instead of showing a misleading number. A per-server diagnostic is included too.

---

## What's New (July 2026 – v1.5)

- **Fixed: internet speedtest sometimes showed absurdly low numbers** – It used the first server that responded at all; if that was a throttled mirror (e.g. OVH at 2–3 Mbps) that figure was shown, even though the tunnel easily did 300+ Mbps over the same path (the IPTV test confirmed it). It now takes the **fastest** of several servers, puts a reliable one (Hetzner, DE) first, and stops early once a clearly good measurement is in.

---

## What's New (July 2026 – v1.4)

- **More reliable speedtest** – On fast links the 10 MB download finished in under a second, so it mostly measured the TCP ramp-up (slow-start), not the real bandwidth, and results were noisy. It now downloads a larger file, discards the first ~1.2 s and measures only the steady-state throughput — noticeably more stable, realistic numbers.
- **Proactive VPN data-flow check** – In addition to the log-based state, the watchdog now actively verifies that data really flows through the tunnel (a tiny request to a DNS-free target). This catches a "connected but nothing gets through" tunnel *before* streams stall, not after. Deliberately conservative: it takes several consecutive failures (~2 min without data) before acting, so a single hiccup won't cause a false alarm.

---

## What's New (July 2026 – v1.3)

- **VPN server comparison** – New "Compare all VPN servers" button in the speedtest. Connects each uploaded `.ovpn` in turn, measures internet speed through it, and shows a ranking with the fastest location. The watchdog is paused during the run and the previously active server is restored afterwards. Note: with a single tunnel, streams are briefly interrupted during the ~2-minute comparison, so it's a deliberate button with a warning, not automatic.
- **Fixed: misleading speedtest verdict** – The verdict compared the provider against the neutral speedtest server and flagged a "bottleneck" whenever it was slower — even at speeds far above what any stream needs. It now judges the provider in absolute terms against streaming needs (below 8 Mbps too slow, below 25 tight for 4K, otherwise no bottleneck, including an estimated number of parallel 4K streams).

---

## What's New (July 2026 – v1.2)

Stability release around provider server switches and VPN. Fully backward compatible — no config changes, existing tokens/playlists stay valid. The database migrates automatically on first start.

- **Provider server switches without reloading playlists** – Every channel gets a stable, server-independent id. The device playlist points to `/iptv/{token}/live/{id}` instead of the baked-in provider URL, and the current upstream URL is resolved from the database at play time. When the provider's server changes, a single **↻ Refresh** is enough — devices don't have to reload anything. Legacy `?url=` playlists keep working; devices switch over once, on their next reload.
- **VPN failover to another server** – If repeated restarts don't help (typical when the remote server stops answering entirely), the watchdog automatically switches to another uploaded `.ovpn`. Requires at least two configurations.
- **Hardened VPN connection** – Stability options are written into a working copy of the config at start (the original file is left untouched): shorter retry pauses (`connect-retry 5 30` instead of up to 300 s), faster switching across multiple `remote` entries (`server-poll-timeout 15`), `resolv-retry infinite`, and `remote-cert-tls server` replacing the deprecated `ns-cert-type`.
- **Fixed: VPN watchdog missed real outages** – Health was "process alive **and** tun0 has an IP". Both survive a soft OpenVPN restart (`SIGUSR1[soft,tls-error]`) — the process doesn't exit, and `persist-tun` keeps the old IP — so a dead tunnel looked healthy and the watchdog never stepped in. Link state is now derived from OpenVPN's own messages.
- **Fixed: group order didn't match the numbering** – Two separate sort controls wrote to different sources. Both now come from one place (Groups page → "Group order"); the conflicting control in the user dialog was removed.
- **Fixed: playlists could be served stale** – The response now carries `Cache-Control: no-cache, no-store, must-revalidate`.
- **Fixed: speedtest reported the provider as too slow** – Bytes from all segments were divided by the total wall time, including time when finished segments were no longer loading, which produced a false "provider is the bottleneck" verdict. Each segment is now timed individually (median per connection, plus best value, parallel total and failed count).
- **Fixed: database migration broke existing installs** – The index on the new channel column was created before the column existed on an existing database, making provider refresh fail with `table channels has no column named stable_uid`.

---

## What's New (June 2026 – v1.1)

Security & stability release. Fully backward compatible — no config changes, existing tokens/logins stay valid.

- **SSRF protection** – The public proxy validates target URLs before fetching (only `http`/`https`, internal/private targets blocked) — **including redirect hops**, so a malicious upstream can't redirect into your LAN.
- **Admin token hashed** – Stored as PBKDF2-HMAC-SHA256 instead of plaintext; existing plaintext tokens migrate automatically on next login.
- **Cryptographically secure short tokens** – `secrets` instead of `random` for public short URLs.
- **"Max. streams" / "Banned" as a real video clip** – Players now show a short notice clip instead of a skipped JPEG segment (no ffmpeg, no runtime CPU load).
- **Admin panel XSS hardening** – Server-supplied names/IDs in inline handlers are encoded so playlist data can't break out.

> Full release notes (features, security, fixes, tooling) are in the **[CHANGELOG](../CHANGELOG.md)**.

---

## What's New (May 2026)

- **Catchup auto-live default changed** – `catchup_auto_live_on_program_change` now defaults to `0` (off) to avoid unwanted jumps from catchup to live.
- **Global diagnostics switch** – New setting `diagnostics_enabled` lets you turn all diagnostic logging on/off from the admin panel when needed.
- **Catchup diagnostics improved** – Logs now make it clearer whether behavior comes from DVR timeline progression, redirects, or session timeout handling.

---

<a id="deutsch"></a>

# 🇩🇪 Deutsch

## Neu seit August 2026 (v1.44 → v1.56)

- **Umstieg auf WireGuard + Mullvad.** Das integrierte VPN läuft jetzt mit **WireGuard** statt OpenVPN — deutlich schneller und viel CPU-schonender (in der Praxis ~6× Durchsatz gegenüber dem alten OpenVPN-Tunnel). OpenVPN wurde aus der Oberfläche entfernt; Upload nur noch `.conf`.
- **Mullvad-Auto-Import.** Eine einzige Mullvad-`.conf` hochladen, und SelfStream zieht alle WireGuard-Server aus Mullvads API (optional nach Land) und legt automatisch pro Server eine Config an — kein manuelles Hochladen hunderter Dateien mehr.
- **Nahtloser Server-Wechsel (keine Unterbrechung).** Ein Serverwechsel reißt den Tunnel nicht mehr ab. Das `wg0`-Interface bleibt oben, nur der Peer (Server + Endpoint) wird live getauscht — praktisch keine Unterbrechung, **auch während Zuschauer schauen**. „Aktivieren" und „Wechseln" nutzen beide diesen Weg.
- **Auto-Best für WireGuard (nahtlos).** Ein Hintergrund-Wächter reagiert auf **echtes Ruckeln** (gemessen aus echten Zuschauer-Segmenten) und schaltet nahtlos auf den schnellsten erreichbaren Alternativ-Server – mit einstellbarer Durchsatz-Schwelle und Cooldown gegen Hin-und-Her. Die Server-Auswahl nutzt eine **stream-sichere Latenz-Messung** (Test-Pakete gehen nie durch den Tunnel). Neue Endpunkte `GET/POST /api/vpn/wg-autobest`.
- **Beide Strecken sichtbar.** Traffic misst jetzt beide Strecken getrennt: **Anbieter → SelfStream** (aus echten Zuschauer-Segmenten, pro User) und **SelfStream → Gerät** (die Auslieferungs-Geschwindigkeit `→ USER`, pro User) — so siehst du sofort, ob das Problem eines Zuschauers am Anbieter/Server liegt oder an dessen eigener Verbindung (z.B. sein 5G). Buffering-Ereignisse mit echtem 30-Tage-Verlauf und User-Filter.
- **Canary ist line-schonend.** SelfStreams eigener Test-Zuschauer nutzt bei aktiven Zuschauern deren Segmente (holt nur bei Leerlauf selbst) und pausiert nahe am Verbindungslimit, klaut also nie einem echten Zuschauer eine Line.

---

## Neu seit August 2026 (v1.27)

- **Messung ist jetzt PASSIV — kein aktives Extra-Messen mehr, das Streams stört.** Der frühere „Auto-Wechsel bei schlechter Leistung"-Wächter zog alle 2 Min zusätzliche Segmente vom Anbieter → Konkurrenz mit laufenden Streams → Ruckeln (bei vielen Nutzern gibt es nie „0 Zuschauer"). **Entfernt.** Stattdessen liest SelfStream die Ladezeit jedes echten Segment-Abrufs mit, den die Zuschauer eh auslösen, und leitet daraus die real erlebte Qualität ab (Median-Ladezeit, Fehlerrate, Durchsatz → ok/träge/schlecht). **Null Extra-Last, funktioniert während des Schauens, kann den Stream nicht mehr stören.** Health-Sampler, Selbst-Check und E-Mail-Alarm laufen auf diesem passiven Signal; nur bei Leerlauf hält ein Mini-Check die Kurve am Leben. Bei Einbruch während des Schauens: nur Alarm, kein Auto-Wechsel. Not-Failover, Auto-Best (nachts) und manuelle Knöpfe bleiben.

---

## Neu seit August 2026 (v1.26)

- **Bugfixes aus einem Code-Review:** Alarm-Mail wird bei anhaltender Störung erneut versucht, bis eine wirklich rausging; ein fehlgeschlagener VPN-Neustart gilt nicht mehr als erfolgreicher Wechsel (keine 30-Min-Blindzeit); der Health-Sampler pausiert während eines Server-Vergleichs (kein Fehlalarm); ein manueller „reiner Vergleich" verschiebt den Auto-Best-Lauf nicht mehr; der „Jetzt testen"-Knopf kann nicht mehr hängen bleiben.

---

## Neu seit August 2026 (v1.25)

- **Selbst-Check + E-Mail-Alarm.** SelfStream überwacht sich selbst (VPN, Anbieter erreichbar, Durchsatz/Antwortzeit) und schickt bei anhaltendem Problem **eine** E-Mail + Entwarnung, wenn wieder ok (kein Spam). Optional tägliches Lebenszeichen. SMTP frei konfigurierbar; Konfiguration + Status-Ampel + „Test-E-Mail" oben auf der Diagnose-Seite. Endpunkte `GET/POST /api/alerts`, `POST /api/alerts/test`.

---

## Neu seit August 2026 (v1.24)

- **Automatische VPN-Wechsel nur noch bei 0 Zuschauern.** Ein Serverwechsel unterbricht immer kurz ALLE Streams (nur ein Tunnel). Der Leistungs-Wächter schaltet nicht mehr mitten im Gucken um: erkennt er einen schwachen Server, während jemand schaut, wartet er (Log „⏸️ … Wechsel erst bei 0 Zuschauern") und wechselt erst, sobald frei. Auto-Best lief schon nur bei 0 Zuschauern. Der Not-Failover (toter Tunnel) bleibt.

---

## Neu seit August 2026 (v1.23)

- **Behoben: Auto-Best-Vergleich war viel zu langsam** (Minuten pro Server). Der Sweep maß mit der vollen Ziel-Stream-Zahl (z.B. 10) und traf so das Anbieter-Verbindungslimit (~10) → Stalls/Timeouts. Jetzt misst er eine moderate Parallel-Last (max. 5 Streams) und leitet „schafft ~N Streams" aus dem Gesamtdurchsatz ab. Deutlich schneller.

---

## Neu seit August 2026 (v1.22)

- **Auto-Best: automatisch den besten VPN-Server wählen** (opt-in). SelfStream misst regelmäßig ALLE hochgeladenen .ovpn durch und schaltet automatisch auf den schnellsten. Der Rundum-Vergleich unterbricht kurz alle Streams (nur ein Tunnel), läuft daher **nur bei 0 Zuschauern** und höchstens alle `vpn_autobest_hours` Stunden (einstellbar). Ergänzt den Leistungs-Wächter (schnelle Reaktion auf Einbrüche).
- **Ziel „muss gut sein für N Streams" einstellbar** (`vpn_min_streams`, Standard 10). Der Vergleich misst mit so vielen Streams und meldet je Server „schafft ~N Streams" (Ziel = N × 8 Mbit/s ≈ Full-HD). Warnt, wenn selbst der beste Server das Ziel nicht sicher packt.
- Neue Endpunkte `GET/POST /api/vpn/autobest`, `POST /api/vpn/autobest-now` + Knopf „🔍 Jetzt besten suchen & draufschalten".

---

## Neu seit August 2026 (v1.21)

- **Anbieter-Kapazitätstest: Stream-Zahl selbst einstellbar.** Statt fest 1–20 gibt es jetzt ein Eingabefeld „bis N gleichzeitige Streams" (2–50). Die Test-Stufen passen sich automatisch an.

---

## Neu seit August 2026 (v1.20)

- **Leistungs-Wächter: Zappeln / zu häufiges Auslösen behoben.** Die Perf-Messung nahm nur eine einzelne 1-Segment-Probe – die schwankt stark (im Log 14 %↔55 % beim selben Server) und erzeugte Fehl-„schwach" plus Server-Flappen. Drei Korrekturen: es wird über mehrere Streams/Segmente gemessen (stabile Zahl statt Rauschen), die Baseline ist jetzt der **Median** (typischer Wert) statt eines Perzentil-Bestwerts, und der aktuelle Wert wird **geglättet** (Median der letzten 3 Messungen). Nur noch ein echter, anhaltender Einbruch löst aus.

---

## Neu seit August 2026 (v1.19)

- **Automatischer VPN-Server-Wechsel bei schlechter Leistung** (opt-in). Ein neuer Leistungs-Wächter misst den aktuell verbundenen VPN-Server laufend (Durchsatz + Antwortzeit/Ping zum Anbieter, schonend über 1 Verbindung) und vergleicht ihn mit seiner *eigenen* üblichen Leistung („self-baseline", Perzentil aus einem rollierenden Fenster). Fällt der Durchsatz **unter eine einstellbare Prozent-Schwelle** der Bestleistung ODER steigt die Latenz **über eine einstellbare Prozent-Schwelle**, wird nach 3 schwachen Messungen in Folge auf die nächste hochgeladene `.ovpn` gewechselt – mit 30-Min-Sperre gegen Hin-und-Her. Beide Schwellen sind im Panel setzbar; ein Knopf **„Jetzt testen"** zeigt aktuell vs. Baseline + ob gewechselt würde, ohne zu wechseln. Ergänzt den bestehenden Not-Failover (der nur bei totem Tunnel greift). Neue Endpunkte: `GET/POST /api/vpn/perf`, `POST /api/vpn/perf/test`.

---

## Neu seit Juli 2026 (v1.18)

- **Anbieter-Server-Umschaltung wieder entfernt** (Server-Vergleich, „bevorzugter Server", Auto-Wechsel, Server-Entdeckung). Funktionierte nicht bei Anbietern mit server-gebundenem Token: das Umschreiben löste eine „SERVER CHANGED"-Sperre aus, und die Latenz-Messungen anderer Server maßen diese Hinweis-Meldung statt echter Streams. Komplett raus, um Fehldiagnosen und unterbrochene Streams zu vermeiden. Rest bleibt: VPN-Wächter mit Failover, Speedtest inkl. Kapazitätstest, Latenz/Jitter, VPN-Server-Vergleich, automatischer Verlauf.

---

## Neu seit Juli 2026 (v1.17)

- **Automatisch auf den besten Server umschalten** – Neu im „Bevorzugter Server"-Kasten. Knopf **„🎯 Jetzt besten Server suchen & wechseln"** prüft sofort alle Server und setzt den bevorzugten auf den latenzärmsten. Dazu eine **Automatik** (Häkchen) mit **einstellbarem Intervall** (alle X Stunden, 1–168): SelfStream sucht regelmäßig selbst den besten Server und schaltet um. Automatisch nur bei **deutlicher** Verbesserung (>30 % weniger Latenz), kein Hin-und-Her; per Knopf immer auf den Besten. Umschaltungen stehen in der Diagnose.

---

## Neu seit Juli 2026 (v1.16)

- **Neue Anbieter-Server automatisch entdecken** – SelfStream führt ein **Server-Register** und sucht **automatisch nach neuen**: Server-Vergleich + täglicher Hintergrund-Check proben auch nummerierte Server **über die höchste bekannte Nummer hinaus**. Neuer Server → Hinweis („🆕 Neu entdeckt: …"-Banner + Diagnose). Generisch, keine Anbieter-Namen im Code; Hintergrund-Check lässt bei vollem Verbindungslimit aus.

---

## Neu seit Juli 2026 (v1.15)

- **Bevorzugten Server erzwingen** – Neues Feld im Server-Vergleich. Trägst du einen Server ein (z.B. `6` oder `6.example.net`), schreibt SelfStream beim Abspielen **alle Kanäle auf diesen Server um** – egal welchen Server die Anbieter-Playlist ausgibt. So kommst du auf einen latenzärmeren Server, auch wenn das Anbieter-Panel es nicht zulässt (Token bleibt erhalten). Gilt **sofort** und dank stabiler Kanal-IDs (`/live`) **ohne Geräte-Neuladen**. Leer = aus. Nur Live, Catchup unberührt.

---

## Neu seit Juli 2026 (v1.14)

- **Server-Vergleich: Mbit/s-Spalte klarer** – Die Mbit/s dort sind nur eine grobe Einzelverbindungs-Stichprobe (sinkt physikalisch mit der Latenz) und jetzt so gekennzeichnet; die Latenz entscheidet, die echte Kapazität steht im Haupt-Speedtest.

---

## Neu seit Juli 2026 (v1.13)

- **Server-Vergleich: ganze Domains eintragbar** – Im Feld kannst du jetzt die **kompletten Server-Domains** eintragen (einen pro Zeile oder per Komma, z.B. `de.example.net`) – auch ganze URLs werden akzeptiert (nur der Host zählt). Kurze Kürzel (`de`, `2`) gehen weiter und werden an die Domain deines aktuellen Servers gehängt. Feld jetzt mehrzeilig.

---

## Neu seit Juli 2026 (v1.12)

- **Server-Vergleich: Server selbst eintragen** – Die zu vergleichenden Server trägst du jetzt selbst ein (Kürzel wie `de`, `nl`, `2` oder ganze Hostnamen) – **keine anbieterspezifischen Server im Code**. Funktioniert mit jedem Anbieter/Setup, und im Repo landet nichts zu einem bestimmten Anbieter.

---

## Neu seit Juli 2026 (v1.11)

- **Server-Vergleich (beste Latenz finden)** – Neuer Knopf im Speedtest. Probiert die von dir eingetragenen Server durch dein VPN, indem er sie in eine echte Kanal-URL einsetzt, und misst pro Server **Latenz + kurzen Durchsatz**. Findet den Server mit der **niedrigsten Latenz von deinem VPN-Ausgang aus** – der direkte Hebel gegen träges Zappen. Server mit server-gebundenem Token erscheinen als „nicht nutzbar"; dann geht Umstellen nur im Anbieter-Panel.

---

## Neu seit Juli 2026 (v1.10)

- **Hintergrund-Stichprobe stört Zuschauer garantiert nicht** – Nutzt nur noch eine Anbieter-Verbindung und setzt bei fast vollem Verbindungslimit komplett aus.

---

## Neu seit Juli 2026 (v1.9)

- **VPN-Server-Vergleich rankt jetzt sinnvoll** – Vorher über den Internet-Speedtest (durchs VPN unzuverlässig). Jetzt misst er pro Server **IPTV-Anbieter-Durchsatz + Latenz** und rankt danach, wie gut deine Streams über den Server laufen.
- **Latenz & Jitter** – Ruckeln kommt oft von Latenz/Jitter, nicht von Bandbreite. Der IPTV-Test zeigt jetzt Latenz + Jitter und warnt bei unruhiger Verbindung.
- **Stabilere Messung** – Der IPTV-Test misst pro Stream über mehrere Segmente statt eines winzigen Häppchens – weniger Rauschen.
- **Automatischer Verlauf + Frühwarnung** – Hintergrund-Stichprobe alle 5 Min (Latenz, Durchsatz, VPN-Zustand), 24-h-Verlauf → intermittierende Probleme werden sichtbar. Knopf „Verlauf anzeigen" mit Balkengrafik; anhaltende Probleme zusätzlich in der Diagnose. Stichprobe wird bei fast vollem Verbindungslimit ausgelassen.

---

## Neu seit Juli 2026 (v1.8)

- **Anbieter-Kapazitätstest (1–20 Streams)** – Neuer Knopf im Speedtest. Misst den IPTV-Anbieter mit **steigend vielen gleichzeitigen Streams** (1, 2, 4, 8, 12, 16, 20) und zeigt in einer Tabelle, wie sich der Durchsatz pro Stream entwickelt und **ab wann Ausfälle beginnen** — das deckt dein **Abo-Verbindungslimit** direkt auf (ab welcher Stufe Streams scheitern) und den Punkt, ab dem die Bandbreite pro Stream unter Full-HD fällt. Grün = flüssig, Gelb = nur HD, Rot = Ausfall. Bewusster Knopf mit Warnung (belegt kurz bis zu 20 Anbieter-Verbindungen).

---

## Neu seit Juli 2026 (v1.7)

- **Speedtest beantwortet „packt mein Setup X Zuschauer?"** – Der IPTV-Test simuliert jetzt **8 gleichzeitige Streams** (statt 5) — den realistischen Fall mehrerer Zuschauer über dasselbe VPN — und gibt eine klare **Ampel**: „✅ 8 gleichzeitige Streams kein Problem – reicht für 8× Full-HD/4K" bzw. eine Warnung, wenn es nicht reicht oder Test-Kanäle nicht erreichbar sind. Bewertet wird nach dem **Durchsatz pro Stream unter Volllast** (Gesamt ÷ Streams). Banner grün bei „alles gut", rot bei echter Warnung.

---

## Neu seit Juli 2026 (v1.6)

- **Internet-Speedtest jetzt parallel + ehrlich** – Öffentliche Speedtest-Server drosseln/blockieren VPN-IPs, daher zeigte der Internet-Wert teils absurd niedrige Zahlen (z.B. 3 Mbit/s), obwohl der Tunnel über denselben Weg 400+ schafft (der IPTV-Test bewies es). Die Messung läuft jetzt **parallel** (aggregiert) wie der IPTV-Test; und liegt der Wert trotzdem unplausibel weit unter dem echten Tunnel-Durchsatz, wird er als **unzuverlässig gekennzeichnet** (mit Verweis auf den belastbaren IPTV-Parallel-Wert) statt irreführend groß angezeigt. Inkl. Server-Diagnose.

---

## Neu seit Juli 2026 (v1.5)

- **Behoben: Internet-Speedtest zeigte teils absurd niedrige Werte** – Der Test nahm den ersten Server, der überhaupt antwortete; war das ein gedrosselter Mirror (z.B. OVH mit 2–3 Mbit/s), stand diese Zahl da, obwohl der Tunnel über denselben Weg locker 300+ Mbit/s schaffte (der IPTV-Test zeigte das auch). Jetzt wird der **schnellste** mehrerer Server genommen, ein zuverlässiger (Hetzner, DE) steht vorn, und sobald eine klar gute Messung vorliegt, wird früh abgebrochen.

---

## Neu seit Juli 2026 (v1.4)

- **Belastbarer Speedtest** – Auf schnellen Leitungen war die 10-MB-Messung in unter einer Sekunde durch und maß vor allem die TCP-Anlaufphase, nicht die echte Bandbreite. Jetzt größere Datei, die ersten ~1,2 s werden verworfen, nur der eingeschwungene Durchsatz zählt — deutlich stabilere, realistischere Werte.
- **Proaktiver VPN-Datenfluss-Check** – Der Wächter prüft zusätzlich zum Log-Zustand aktiv, ob wirklich Daten durch den Tunnel fließen (winzige Anfrage an ein DNS-freies Ziel). Erkennt einen „verbunden, aber nichts kommt durch"-Tunnel, *bevor* die Streams stehen. Bewusst konservativ: erst nach mehreren Fehlern am Stück (~2 Min) wird eingegriffen, damit ein einzelner Aussetzer keinen Fehlalarm auslöst.

---

## Neu seit Juli 2026 (v1.3)

- **VPN-Server-Vergleich** – Neuer Knopf „Alle VPN-Server vergleichen" im Speedtest. Verbindet jede hochgeladene `.ovpn` nacheinander, misst die Internet-Geschwindigkeit über diesen Server und zeigt eine Rangliste mit dem schnellsten Standort. Der Wächter pausiert währenddessen, der zuvor aktive Server wird danach wiederhergestellt. Hinweis: Da es nur einen Tunnel gibt, sind Streams während des Vergleichs (~2 Min) kurz unterbrochen — daher ein bewusster Knopf mit Warnung, kein Automatismus.
- **Behoben: irreführende Speedtest-Bewertung** – Das Verdikt verglich den Anbieter stur mit dem neutralen Speedtest-Server und meldete „Flaschenhals", sobald er langsamer war — auch bei Geschwindigkeiten, die für jeden Stream mehr als reichen. Jetzt absolute Bewertung am Streaming-Bedarf (unter 8 Mbit/s zu langsam, unter 25 für 4K knapp, sonst kein Flaschenhals inkl. geschätzter paralleler 4K-Streams).

---

## Neu seit Juli 2026 (v1.2)

Stabilitäts-Release rund um Anbieter-Serverwechsel und VPN. Voll abwärtskompatibel — keine Konfigurationsänderung, bestehende Tokens/Playlists bleiben gültig. Die Datenbank wird beim ersten Start automatisch migriert.

- **Anbieter-Serverwechsel ohne Playlist-Neuladen** – Jeder Kanal bekommt eine stabile, serverunabhängige ID. Die Geräte-Playlist verweist auf `/iptv/{token}/live/{id}` statt auf die fest eingebackene Anbieter-URL; die aktuelle Upstream-URL wird erst beim Abspielen aus der Datenbank aufgelöst. Wechselt der Anbieter-Server, genügt ein Klick auf **↻ Aktualisieren** — die Geräte müssen nichts neu laden. Alte Playlists (`?url=`) funktionieren unverändert weiter; Geräte stellen beim nächsten Neuladen einmalig um.
- **VPN-Ausweichen auf einen anderen Server** – Bringen mehrere Neustarts nichts (typisch, wenn der Gegenserver gar nicht mehr antwortet), wechselt der Wächter automatisch auf eine andere hochgeladene `.ovpn`. Voraussetzung: mindestens zwei Konfigurationen.
- **Gehärtete VPN-Verbindung** – Beim Start werden Stabilitäts-Optionen in eine Arbeitskopie der Konfiguration geschrieben (Original bleibt unangetastet): kürzere Wiederholungspausen (`connect-retry 5 30` statt bis zu 300 s), schnelleres Umschalten bei mehreren `remote`-Einträgen (`server-poll-timeout 15`), `resolv-retry infinite` sowie `remote-cert-tls server` statt des veralteten `ns-cert-type`.
- **Behoben: VPN-Wächter erkannte echte Ausfälle nicht** – Die Prüfung war „Prozess lebt **und** tun0 hat eine IP". Beides überlebt einen weichen OpenVPN-Neustart (`SIGUSR1[soft,tls-error]`) — der Prozess beendet sich nicht, und `persist-tun` behält die alte IP. Ein toter Tunnel galt damit als gesund. Der Zustand wird jetzt aus den Meldungen von OpenVPN selbst abgeleitet.
- **Behoben: Gruppen-Reihenfolge passte nicht zur Nummerierung** – Zwei getrennte Sortier-Regler schrieben in unterschiedliche Quellen. Beides kommt jetzt aus einer Quelle (Gruppen-Seite → „Gruppen-Reihenfolge"); der widersprüchliche Regler im Benutzer-Dialog wurde entfernt.
- **Behoben: Playlist konnte veraltet ausgeliefert werden** – Die Antwort trägt jetzt `Cache-Control: no-cache, no-store, must-revalidate`.
- **Behoben: Speedtest maß den Anbieter zu langsam** – Die Datenmenge aller Segmente wurde durch die Gesamtdauer geteilt, auch durch Zeit, in der fertige Segmente nichts mehr luden → falsche Meldung „Anbieter ist der Flaschenhals". Jetzt misst jedes Segment seine eigene Zeit (Median je Verbindung, zusätzlich Bestwert, Parallel-Summe und Zahl fehlgeschlagener Segmente).
- **Behoben: Datenbank-Migration brach bestehende Installationen** – Der Index auf die neue Kanal-Spalte wurde angelegt, bevor die Spalte auf einer bestehenden Datenbank existierte → Anbieter-Abruf scheiterte mit `table channels has no column named stable_uid`.

---

## Neu seit Juni 2026 (v1.1)

Sicherheits- und Stabilitäts-Release. Voll abwärtskompatibel — keine Konfigurationsänderung, bestehende Tokens/Logins bleiben gültig.

- **SSRF-Schutz** – Der öffentliche Proxy prüft Ziel-URLs vor dem Abruf (nur `http`/`https`, interne/private Ziele blockiert) — **inklusive Redirect-Zielen**, sodass ein bösartiger Anbieter nicht per Weiterleitung in dein LAN zeigen kann.
- **Admin-Token gehasht** – Speicherung als PBKDF2-HMAC-SHA256 statt Klartext; bestehende Klartext-Tokens werden beim nächsten Login automatisch migriert.
- **Kryptografisch sichere Short-Tokens** – `secrets` statt `random` für öffentliche Short-URLs.
- **„Max. Streams" / „Gesperrt" als echter Video-Clip** – Player zeigen jetzt einen kurzen Hinweis-Clip statt eines übersprungenen JPEG-Segments (kein ffmpeg, keine Laufzeit-CPU-Last).
- **XSS-Härtung im Admin-Panel** – Server-gelieferte Namen/IDs in Inline-Handlern werden kodiert, sodass Playlist-Daten nicht ausbrechen können.

> Vollständige Release-Notes (Funktionen, Sicherheit, Fixes, Tooling) im **[CHANGELOG](../CHANGELOG.md)**.

---

## Neu seit Mai 2026

- **Catchup Auto-Live Standard geändert** – `catchup_auto_live_on_program_change` steht standardmäßig auf `0` (Aus), damit es keine ungewollten Sprünge von Catchup auf Live gibt.
- **Globaler Diagnose-Schalter** – Neue Einstellung `diagnostics_enabled`, um Diagnose-Logging im Admin-Panel bei Bedarf komplett ein-/auszuschalten.
- **Bessere Catchup-Diagnose** – Logs unterscheiden klarer zwischen DVR-Zeitfortschritt, Redirect-Verhalten und Session-Timeout-Ursachen.
