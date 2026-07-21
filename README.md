
<p align="center">
  <img src="https://raw.githubusercontent.com/s3lfcod3r/selfstream/refs/heads/main/assets/logo.png" width="240" alt="selfstream logo">
</p>

<p align="center">
  <a href="#english">🇬🇧 English</a> &nbsp;|&nbsp; <a href="#deutsch">🇩🇪 Deutsch</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-GPL--3.0-00ff88?style=flat-square">
  <img src="https://img.shields.io/badge/docker-ghcr.io-2496ED?style=flat-square&logo=docker">
  <img src="https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python">
  <img src="https://img.shields.io/badge/platform-Unraid%20%7C%20Docker-orange?style=flat-square">
</p>

---

<a name="english"></a>

# 🇬🇧 English

## What is selfstream?

> [!WARNING]
> **HLS providers only.** selfstream requires an M3U playlist with `.m3u8` streams. Xtream Codes API, STRM files and other formats are not supported.

selfstream is a self-hosted IPTV proxy with user management, stream protection, EPG integration, watch tracking, built-in VPN support and traffic analysis — running as a single Docker container. No Redis, no external database needed.

## Features

### Core
- **User Management** – Every user gets their own M3U URL with token
- **Max. Streams per User** – Configurable, blocks additional devices with HTTP 429
- **Catchup / Timeshift** – Watch past content, works with IPTV Pro & TiviMate
- **EPG Integration** – Program info shown in dashboard (what's on now, what was watched)
- **Watch Tracking** – Channel, show title, duration, timestamp — all stored
- **IP Tracking** – IP address logged per stream session and in watch history
- **Admin Dashboard** – Live Sessions, Live Catchup, History, Users, Channels, EPG, Settings
- **Custom Groups** – Create your own channel groups (e.g. Kids, Sports, Docs) and assign users
- **Group & Provider Sorting** – Drag & drop to sort both custom and provider groups; numbering forces order in IPTV Pro (e.g. "01. Kids", "02. Sports")
- **Brute-Force Protection** – Admin login locked after 10 failed attempts
- **Short URLs** – Short playlist URLs via custom domain (e.g. `https://iptv.yourdomain.com/AbCd1234.m3u`)
- **Channel Manager** – Enable/disable, sort, filter channels by group
- **EPG Manager** – Multiple EPG sources, time filter (1/3/7 days), auto-refresh, channel whitelist
- **M3U Auto-Refresh** – Automatically reload channels on schedule per provider
- **M3U Import** – Import via URL; optionally update all existing users at once
- **Setup Wizard** – On first start, no manual config editing needed
- **Single Container** – Python + FastAPI + SQLite, no Redis, no Nginx needed

### 🌐 Subdomain / Reverse Proxy Support
- **Public URL** – Set your subdomain as the public domain; all M3U and stream links are automatically built with that URL
- **`X-Accel-Buffering: no`** – selfstream sends this header so reverse proxies (Zoraxy, Nginx, Caddy) stream segments through without buffering
- **Full URL chain** – playlist → stream playlist → segments, all consistently using your public domain
- **Local test button** – Each user has a 🏠 button in the admin panel that generates a local test URL (`?local=1`) with internal IP for quick diagnostics without touching the public setup
- **`PROXY_URL` env variable** – Set the public proxy URL via environment variable for docker-compose setups

### 🔒 VPN (Built-in OpenVPN)
- **Integrated OpenVPN** – Start/stop VPN directly from the admin panel, no extra container needed
- **Multiple .ovpn Profiles** – Upload and switch between multiple provider profiles (e.g. ExpressVPN Switzerland, Germany)
- **Live Status** – Shows connection status and current public IP
- **Live Log** – Real-time OpenVPN log stream in the browser
- **Auto-Start** – VPN reconnects automatically on container restart
- **Local Route Preservation** – Admin panel stays fast even when VPN is active (local network routed via eth0)
- **Requires:** `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` (or Privileged mode in Unraid)

### 📊 Traffic Analysis
- **Live Stream Monitor** – See all active streams with user, IP, channel, show title and duration
- **Estimated Bandwidth** – Real-time Mbit/s estimate based on active streams
- **Stream History Chart** – Canvas chart with Y-axis labels, peak markers and time labels; selectable time range (5 min / 15 min / 30 min / 1h / all)
- **Peak Tracking** – Highest concurrent stream count tracked per session
- **Buffering Events** – Automatic detection and logging of slow/delayed segments
  - 🔴 Slow (>2s) = Buffering very likely
  - 🟡 Delayed (>1s) = Buffering possible
  - Shows: timestamp, user, duration, segment size, download speed, segment name

### 🚀 Speedtest
- **Dual Speedtest** – Measures internet/VPN speed AND IPTV provider speed separately
- **Bottleneck Detection** – Automatically identifies whether the VPN tunnel or IPTV provider is the limiting factor
- **Parallel IPTV Test** – Downloads 5 segments from 5 different channels simultaneously for a realistic load test
- **Stream Capacity Estimate** – Calculates max. concurrent HD / FHD / 4K streams

### ⚡ Performance
- **Segment Pre-buffering** – selfstream fully downloads each TS segment before delivering it to the player; player receives segments at local LAN speed (~900 Mbit/s) instead of provider speed
- **Segment Prefetch Cache** – While you watch one segment, selfstream already downloads the next 2 in the background; cache hits result in near-instant delivery
- **Tiny Segment Retry** – Broken segments (<1 KB) are automatically retried once
- **Shared Segment Cache** – Multiple users watching the same channel share the segment cache; the provider is only hit once per segment

### 👥 User Management (improved)
- **Per-user log view** – Click **Log** on any user to open their watch history in a modal
- **Date filter** – Filter user logs by date range (from / to)
- **Pagination** – 25 / 50 / 100 entries per page with page navigation
- **Delete user logs** – 🗑 button in the log modal to clear only that user's history
- **Token display** – Click 👁 to reveal the full token (breaks across lines, fully readable)
- **Local test URL** – 🏠 button copies a local playlist URL for admin testing without affecting users

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

> Full release notes (features, security, fixes, tooling) are in the **[CHANGELOG](CHANGELOG.md)**.

---

## What's New (May 2026)

- **Catchup auto-live default changed** – `catchup_auto_live_on_program_change` now defaults to `0` (off) to avoid unwanted jumps from catchup to live.
- **Global diagnostics switch** – New setting `diagnostics_enabled` lets you turn all diagnostic logging on/off from the admin panel when needed.
- **Catchup diagnostics improved** – Logs now make it clearer whether behavior comes from DVR timeline progression, redirects, or session timeout handling.

---

## Quick Start

### Option 1 – Unraid Community Apps (recommended)

1. Open Community Apps → search for **selfstream**
2. Install
3. Open browser: `http://YOUR-IP:8080/admin`
4. Follow the Setup Wizard
5. Done ✓

### Option 2 – Docker run

```bash
docker run -d \
  --name selfstream \
  --restart unless-stopped \
  --cap-add=NET_ADMIN \
  --device=/dev/net/tun \
  -p 8000:8000 \
  -p 8080:8080 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/s3lfcod3r/selfstream:latest
```

Then open `http://YOUR-IP:8080/admin` and follow the Setup Wizard.

> **Note:** `--cap-add=NET_ADMIN` and `--device=/dev/net/tun` are only required if you want to use the built-in VPN feature. You can omit them if you don't need VPN.

### Option 3 – docker-compose

```bash
git clone https://github.com/s3lfcod3r/selfstream.git
cd selfstream
docker-compose up -d
```

---

## Ports

| Port | Usage | Who needs it? |
|------|-------|--------------|
| `8000` | IPTV Proxy – M3U playlists, streams, EPG | All users, IPTV apps |
| `8080` | Admin Panel | Only you |

> **Tip:** Port 8080 doesn't need to be publicly accessible. You can remap it, e.g. `8888:8080`.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_TOKEN` | *(empty)* | Admin password. Leave empty → Setup Wizard on first start. If set, password cannot be changed via UI. |
| `BASE_URL` | *(empty)* | Public URL of the admin panel, e.g. `http://192.168.1.69:8080`. Leave empty → set in Setup Wizard. |
| `PROXY_URL` | *(empty)* | Public URL of the IPTV proxy (e.g. `https://iptv.yourdomain.com`). If set, overrides the proxy URL from the database. All M3U and stream links will use this URL. |
| `DB_PATH` | `/data/selfstream.db` | Path to SQLite database. Usually no need to change. |

---

## Admin Panel Settings

### URLs

| Setting | Default | Description |
|---------|---------|-------------|
| Admin Panel URL | *(Setup Wizard)* | Internal URL of the admin panel. Used for internal links. |
| Proxy URL | *(Setup Wizard)* | Internal IP:port of the IPTV proxy (e.g. `http://192.168.1.69:8000`). Used by the server itself. |
| Public Domain / Short URL | *(empty)* | Your public subdomain (e.g. `https://iptv.yourdomain.com`). **This URL is embedded in all M3U stream links.** Leave empty = local IP is used (home network only). |

> **Important:** If you use a reverse proxy (Zoraxy, Nginx, Caddy), set your subdomain as the **Public Domain**. Without it, streams only work on your local network.

### HLS / Stream

| Setting | Default | Description |
|---------|---------|-------------|
| `hls_timeout` | `15` | Connection timeout in seconds (outbound to provider) |
| `hls_read_timeout` | `60` | Read timeout in seconds between chunks (Catchup / langsame CDN oft 45–60s+) |
| `hls_chunk_size` | `65536` | Chunk size in bytes for TS segment streaming (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User-Agent for outgoing requests to IPTV provider |
| `hls_referer` | *(empty)* | Referer header (if required by provider) |
| `hls_follow_redirects` | `1` | Follow HTTP redirects (`1` = yes, `0` = no) |
| `prefetch_segments` | `2` | How many segments to prefetch ahead (0 = disabled) |
| `diagnostics_enabled` | `1` | Global diagnostics master switch (`1` = write diagnostics logs, `0` = disable new diagnostics entries) |

### EPG

| Setting | Default | Description |
|---------|---------|-------------|
| `epg_refresh_hours` | `6` | How often the EPG cache is renewed (in hours) |
| `epg_filter_channels` | `0` | Filter EPG to channels in Channel Manager only |

---

## Recommended Catchup Settings (stable baseline)

For most setups (especially with IPTV Pro / TiviMate), this profile gives stable catchup behavior with fewer unexpected jumps:

- `catchup_guard_master = 1`
- `catchup_strict_mode = 1`
- `catchup_sticky_recover = 1`
- `catchup_auto_live_on_program_change = 0` (prevents auto-jumps to live on programme boundary)
- `catchup_auto_live_keep_utc = 0` (only relevant if auto-live is enabled)
- `catchup_force_same_channel_live = 1`
- `catchup_hard_lock = 0` (enable only if your client keeps escaping to live)
- `diagnostics_enabled = 0` in daily use, set to `1` only during troubleshooting
- `player_request_debug = 0` in daily use, set to `1` only for short diagnostic sessions

Tip: after changing catchup guard settings, save and run one complete catchup test from start to programme boundary to verify behavior on your provider.

---

## Setting Up Users

1. Open Admin Panel → **Users** → **+ Add User**
2. Enter name (e.g. "Kids Tablet", "Living Room TV")
3. Set max streams (default: 1)
4. Optionally assign custom groups (e.g. Kids, Sports)
5. Share the generated playlist URLs:

| URL | Use case |
|-----|----------|
| 📋 (teal button) | External URL via subdomain — for users outside your network |
| 🏠 (yellow button) | Local test URL — for admin testing on your local network |

Enter the external URL in TiviMate, IPTV Pro, VLC or any other IPTV app.

---

## Subdomain Setup (Reverse Proxy)

To make streams accessible from outside your home network:

1. Point your subdomain (e.g. `iptv.yourdomain.com`) to your server's public IP
2. Configure your reverse proxy (Zoraxy, Nginx, Caddy) to forward port 80/443 → `192.168.1.x:8000`
3. In selfstream Admin → **Settings** → enter your subdomain in **Public Domain / Short URL**
4. Click **Save** — all M3U and stream links are instantly updated

**Important for Zoraxy / Nginx:** Make sure proxy buffering is disabled for streaming to work correctly. selfstream sends `X-Accel-Buffering: no` automatically.

---

## VPN Setup

1. Admin Panel → **VPN**
2. Enter your OpenVPN credentials (username & password from your provider)
3. Click **Choose File** → upload your `.ovpn` file (download from your VPN provider's website under Manual Configuration → OpenVPN)
4. Click **▶ Start VPN**
5. The live log shows the connection progress; once connected, the public IP is displayed

**Switching profiles:** Upload multiple `.ovpn` files (e.g. different countries) and click **Activate** to switch between them. Stop and restart the VPN after switching.

**Tested providers:** ExpressVPN — other OpenVPN-compatible providers should work too.

---

## Speedtest

Admin Panel → **VPN** → scroll down to **Speedtest – Bottleneck Analysis**

- Click **▶ Start Speedtest**
- Two tests run simultaneously:
  1. **Internet / VPN** – downloads from Cloudflare/OVH to measure raw tunnel speed
  2. **IPTV Provider** – downloads 5 real segments from 5 channels in parallel
- The bottleneck banner shows which side is limiting your stream capacity

**Interpreting results:**
- If IPTV provider speed << Internet speed → provider is the bottleneck (common with VPN)
- If both are similar → no bottleneck, VPN overhead is minimal
- Concurrent stream estimates assume ~4 Mbit/s (HD), ~8 Mbit/s (FHD), ~25 Mbit/s (4K)

---

## Traffic Analysis

Admin Panel → **Traffic**

- **Live Streams** – Shows all active sessions with user, IP, channel, show title, duration, estimated bandwidth
- **Stream History Chart** – Select time range (5 min to all); Y-axis shows stream count; red dots mark peak times
- **Buffering Events** – Automatic log of slow segment downloads; helps diagnose freezing/stuttering

**Reading the buffering log:**
- 🔴 >2s download time → player very likely buffered
- 🟡 >1s download time → player may have briefly paused
- High speed (>20 Mbit/s) but still slow = large segments (normal for some providers)
- Low speed (<4 Mbit/s) = provider/VPN bottleneck

---

## Custom Groups

Create your own channel groups independent of provider groups:

1. Admin Panel → **Groups** → Enter group name → **+ New Group**
2. Click **✏ Edit Channels** → select channels from any provider group
3. Assign to user → click **🔒 Groups** on the user → check your custom group
4. User sees only the channels in their group — regardless of what the provider calls them

**IPTV Pro category order:** Enable numbering in the Groups tab to force the right sort order in IPTV Pro (e.g. "01. Kids", "02. Sports", "03. Docs").

**Provider group order:** Use the drag & drop list in the Groups tab to sort all groups (custom and provider) in one unified list — the saved order is applied to every playlist.

---

## URLs & Endpoints

### Proxy (Port 8000)

| URL | Description |
|-----|-------------|
| `/iptv/{token}/playlist.m3u` | M3U playlist for user |
| `/iptv/{token}/playlist.m3u?local=1` | Local test playlist (uses internal IP in all links) |
| `/iptv/{token}/playlist.m3u8` | M3U8 playlist (alternative) |
| `/iptv/{token}/epg.xml` | EPG for user |
| `/{short_token}.m3u` | Compact short playlist URL |
| `/s/{short_token}/playlist.m3u` | Short playlist URL |
| `/iptv/epg.xml` | Global EPG URL (same for all users) |
| `/iptv/epg-1d.xml` | EPG filtered – 1 day back **and** 1 day forward |
| `/iptv/epg-3d.xml` | EPG filtered – 3 days back **and** 3 days forward |
| `/iptv/epg-7d.xml` | EPG filtered – 7 days back **and** 7 days forward |

---

## Stream Protection

- Stream starts → session stored in SQLite
- Second device tries to stream → blocked with **HTTP 429**
- Session ends automatically when no segments requested (TTL: 35 seconds)
- Fallback TTL: 4 hours (database)
- Catchup streams do **not** count against the stream limit

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Setup page appears again | Clear browser cache (Ctrl+Shift+R) |
| Stream won't start | Check M3U URL in Admin → Channels → Refresh |
| "Max. Streams reached" | Stop another stream or wait 35 seconds |
| Admin Panel unreachable | Open port 8080 in firewall; on Unraid: check Docker settings |
| EPG not showing | Admin → EPG → click "Load EPG"; then Auto-Match |
| Catchup not working | IPTV provider must support catchup (`tvg-rec` in M3U) |
| Channel switch slow | Lower Connect Timeout to 3–5s in Settings → HLS |
| VPN won't connect | Try a different server or switch from UDP to TCP in your `.ovpn` file (`proto tcp`) |
| VPN active but streams broken | Check that Privileged mode or `--cap-add=NET_ADMIN` is set |
| Buffering with VPN | Test with Speedtest; try a geographically closer VPN server |
| Stream stutters without VPN | Check Buffering Events in Traffic tab; large segments (>5 MB) are normal for some providers |
| External streams not working | Set your subdomain in Settings → Public Domain. Without it, stream links contain your local IP |
| Streams work locally but not externally | Check that your reverse proxy forwards to port 8000 (not 8080) |
| M3U import updates channels but users still use old URL | Enable "Update all users to new URL" checkbox in the import dialog |

---

## Optional: Catchup HLS debug (browser)

A **separate** small Docker image for debugging catchup in the browser (hls.js + event log): **[catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug)**. You paste your **public M3U and EPG URLs**; stream lines already include the selfstream path and token (`…/stream?url=…&utc=…`). It does **not** replace selfstream — run it alongside on another port.

| | |
|--|--|
| **Repository** | [github.com/kabelsalatundklartext/catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug) |
| **Image** | `ghcr.io/kabelsalatundklartext/catchup-hls-debug:latest` (built via Actions on `main`) |
| **Unraid “Template URL”** | `https://raw.githubusercontent.com/kabelsalatundklartext/catchup-hls-debug/main/unraid/catchup-hls-debug.xml` |

---

## Technology

- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow
- **VPN:** OpenVPN (installed in container)
- **Database:** SQLite (no external server needed)
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Container:** Python 3.12 slim, ~200 MB image

---

## License

**GNU General Public License v3.0 (GPL-3.0)**

|  |  |
|--|--|
| ✅ Private & homelab use | ✅ Modify & adapt |
| ✅ Share & distribute | ✅ Publish your own versions |
| ✅ Commercial use allowed | ❌ Closed-source forks forbidden |
| ✅ Forks must stay GPL-3.0 | ✅ Source code must always be open |

> *"selfstream" by s3lfcod3r — [GitHub](https://github.com/s3lfcod3r/selfstream)*

---
---

<a name="deutsch"></a>

# 🇩🇪 Deutsch

## Was ist selfstream?

> [!WARNING]
> **Nur für HLS-Anbieter.** selfstream benötigt eine M3U-Playlist mit `.m3u8` Streams. Xtream Codes API, STRM-Dateien und andere Formate werden nicht unterstützt.

selfstream ist ein selbst gehosteter IPTV-Proxy mit User-Management, Stream-Schutz, EPG-Integration, Watch-Tracking, integriertem VPN und Traffic-Analyse — als einzelner Docker-Container. Kein Redis, keine externe Datenbank nötig.

## Features

### Kern
- **User-Management** – Jeder User bekommt eine eigene M3U-URL mit Token
- **Max. Streams pro User** – Konfigurierbar, blockiert zusätzliche Geräte mit HTTP 429
- **Catchup / Timeshift** – Vergangene Sendungen schauen, funktioniert mit IPTV Pro & TiviMate
- **EPG-Integration** – Programm-Info wird im Dashboard angezeigt (was läuft gerade, was wurde geschaut)
- **Watch-Tracking** – Kanal, Sendung, Dauer, Zeitpunkt – alles gespeichert
- **IP-Tracking** – IP-Adresse wird pro Stream-Session und im Watch-Verlauf protokolliert
- **Admin-Dashboard** – Live Sessions, Live Catchup, Verlauf, Benutzer, Kanäle, EPG, Einstellungen
- **Eigene Gruppen** – Eigene Kanalgruppen erstellen (z.B. Kinder, Sport, Doku) und Usern zuweisen
- **Gruppen- & Anbieter-Sortierung** – Drag & Drop zum Sortieren aller Gruppen; Nummerierung erzwingt Reihenfolge in IPTV Pro (z.B. "01. Kinder", "02. Sport")
- **Brute-Force-Schutz** – Admin-Login wird nach 10 Fehlversuchen gesperrt
- **Short URLs** – Kurze Playlist-URLs über eigene Domain (z.B. `https://iptv.deinedomain.de/AbCd1234.m3u`)
- **Kanal-Manager** – Kanäle aktivieren/deaktivieren, sortieren, nach Gruppen filtern
- **EPG-Manager** – Mehrere EPG-Quellen, Zeitfilter (1/3/7 Tage), Auto-Refresh, Kanal-Whitelist
- **M3U Auto-Refresh** – Kanäle automatisch nach Zeitplan neu laden (pro Anbieter konfigurierbar)
- **M3U Import** – Import per URL; optional alle bestehenden User auf einmal umstellen
- **Setup-Wizard** – Beim ersten Start, kein manuelles Config-Editing nötig
- **Single Container** – Python + FastAPI + SQLite, kein Redis, kein Nginx nötig

### 🌐 Subdomain / Reverse Proxy Support
- **Öffentliche URL** – Subdomain als Public Domain eintragen; alle M3U- und Stream-Links werden automatisch mit dieser URL gebaut
- **`X-Accel-Buffering: no`** – selfstream sendet diesen Header damit Reverse Proxies (Zoraxy, Nginx, Caddy) Segmente direkt durchleiten ohne zu puffern
- **Vollständige URL-Kette** – Playlist → Stream-Playlist → Segmente, alles konsequent mit deiner Public Domain
- **Lokaler Test-Button** – Jeder User hat einen 🏠 Button der eine lokale Test-URL (`?local=1`) mit interner IP generiert — für schnelle Diagnose ohne die öffentliche URL zu beeinflussen
- **`PROXY_URL` Umgebungsvariable** – Öffentliche Proxy-URL per Umgebungsvariable setzen für docker-compose Setups

### 🔒 VPN (Integriertes OpenVPN)
- **Integriertes OpenVPN** – VPN direkt im Admin-Panel starten/stoppen, kein Extra-Container nötig
- **Mehrere .ovpn Profile** – Mehrere Anbieter-Profile hochladen und zwischen ihnen wechseln (z.B. ExpressVPN Schweiz, Deutschland)
- **Live-Status** – Zeigt Verbindungsstatus und aktuelle öffentliche IP
- **Live-Log** – Echtzeit-OpenVPN-Log-Stream im Browser
- **Auto-Start** – VPN verbindet sich automatisch beim Container-Neustart
- **Lokale Route** – Admin-Panel bleibt schnell auch wenn VPN aktiv ist (lokales Netz via eth0 geroutet)
- **Voraussetzung:** `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` (oder Privileged-Modus in Unraid)

### 📊 Traffic-Analyse
- **Live-Stream-Monitor** – Alle aktiven Streams mit User, IP, Kanal, Sendung und Dauer
- **Geschätzte Bandbreite** – Echtzeit-Mbit/s-Schätzung basierend auf aktiven Streams
- **Stream-Verlauf-Chart** – Canvas-Chart mit Y-Achsen-Beschriftung, Peak-Markierungen und Zeitstempeln; wählbarer Zeitbereich (5 Min / 15 Min / 30 Min / 1h / Alles)
- **Peak-Tracking** – Höchste gleichzeitige Stream-Anzahl wird pro Session verfolgt
- **Buffering-Ereignisse** – Automatische Erkennung und Protokollierung langsamer/verzögerter Segmente
  - 🔴 Langsam (>2s) = Buffering sehr wahrscheinlich
  - 🟡 Verzögert (>1s) = Buffering möglich
  - Zeigt: Zeitpunkt, User, Dauer, Segmentgröße, Download-Speed, Segmentname

### 🚀 Speedtest
- **Dual-Speedtest** – Misst Internet-/VPN-Geschwindigkeit UND IPTV-Anbieter-Geschwindigkeit getrennt
- **Flaschenhals-Erkennung** – Erkennt automatisch ob VPN-Tunnel oder IPTV-Anbieter der limitierende Faktor ist
- **Paralleler IPTV-Test** – Lädt 5 Segmente von 5 verschiedenen Kanälen gleichzeitig für einen realistischen Lasttest
- **Stream-Kapazitäts-Schätzung** – Berechnet max. gleichzeitige HD / FHD / 4K Streams

### ⚡ Performance
- **Segment-Vorpuffern** – selfstream lädt jedes TS-Segment vollständig herunter bevor es zum Player geliefert wird; Player empfängt Segmente mit lokaler LAN-Geschwindigkeit (~900 Mbit/s) statt Anbieter-Geschwindigkeit
- **Segment-Prefetch-Cache** – Während ein Segment abgespielt wird, lädt selfstream bereits die nächsten 2 im Hintergrund; Cache-Treffer = sofortige Lieferung
- **Tiny-Segment-Retry** – Kaputte Segmente (<1 KB) werden automatisch einmal neu angefragt
- **Geteilter Segment-Cache** – Mehrere User die denselben Kanal schauen teilen den Cache; der Anbieter wird nur einmal pro Segment angefragt

### 👥 Benutzer-Verwaltung (erweitert)
- **User-Log-Ansicht** – Klick auf **Log** bei jedem User öffnet dessen Watch-Verlauf in einem Modal
- **Datumsfilter** – User-Logs nach Zeitraum filtern (Von / Bis)
- **Seitenzahlen** – 25 / 50 / 100 Einträge pro Seite mit Seitennavigation ◀ ▶
- **User-Logs löschen** – 🗑 Button im Log-Modal löscht nur die Logs dieses Users
- **Token-Anzeige** – Klick auf 👁 zeigt den vollständigen Token (umbrechend, vollständig lesbar)
- **Lokale Test-URL** – 🏠 Button kopiert eine lokale Playlist-URL für Admin-Tests ohne User zu beeinflussen

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

> Vollständige Release-Notes (Funktionen, Sicherheit, Fixes, Tooling) im **[CHANGELOG](CHANGELOG.md)**.

---

## Neu seit Mai 2026

- **Catchup Auto-Live Standard geändert** – `catchup_auto_live_on_program_change` steht standardmäßig auf `0` (Aus), damit es keine ungewollten Sprünge von Catchup auf Live gibt.
- **Globaler Diagnose-Schalter** – Neue Einstellung `diagnostics_enabled`, um Diagnose-Logging im Admin-Panel bei Bedarf komplett ein-/auszuschalten.
- **Bessere Catchup-Diagnose** – Logs unterscheiden klarer zwischen DVR-Zeitfortschritt, Redirect-Verhalten und Session-Timeout-Ursachen.

---

## Schnellstart

### Option 1 – Unraid Community Apps (empfohlen)

1. Community Apps öffnen → nach **selfstream** suchen
2. Installieren
3. Browser öffnen: `http://DEINE-IP:8080/admin`
4. Setup-Wizard folgen
5. Fertig ✓

### Option 2 – Docker run

```bash
docker run -d \
  --name selfstream \
  --restart unless-stopped \
  --cap-add=NET_ADMIN \
  --device=/dev/net/tun \
  -p 8000:8000 \
  -p 8080:8080 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/s3lfcod3r/selfstream:latest
```

Dann `http://DEINE-IP:8080/admin` öffnen und Setup-Wizard folgen.

> **Hinweis:** `--cap-add=NET_ADMIN` und `--device=/dev/net/tun` sind nur nötig wenn du das integrierte VPN nutzen möchtest. Ohne VPN können diese Flags weggelassen werden.

### Option 3 – docker-compose

```bash
git clone https://github.com/s3lfcod3r/selfstream.git
cd selfstream
docker-compose up -d
```

---

## Ports

| Port | Verwendung | Wer braucht ihn? |
|------|-----------|-----------------|
| `8000` | IPTV Proxy – M3U-Playlists, Streams, EPG | Alle User, IPTV-Apps |
| `8080` | Admin Panel | Nur du |

> **Tipp:** Port 8080 muss nicht nach außen erreichbar sein. Du kannst ihn auf einen anderen Port mappen, z.B. `8888:8080`.

---

## Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `ADMIN_TOKEN` | *(leer)* | Admin-Passwort. Leer lassen → Setup-Wizard beim ersten Start. Wenn gesetzt, kann das Passwort nicht über die UI geändert werden. |
| `BASE_URL` | *(leer)* | Öffentliche URL des Admin-Panels, z.B. `http://192.168.1.69:8080`. Leer lassen → wird im Setup-Wizard gesetzt. |
| `PROXY_URL` | *(leer)* | Öffentliche URL des IPTV-Proxys (z.B. `https://iptv.deinedomain.de`). Wenn gesetzt, überschreibt die Proxy-URL aus der Datenbank. Alle M3U- und Stream-Links verwenden diese URL. |
| `DB_PATH` | `/data/selfstream.db` | Pfad zur SQLite-Datenbank. Normalerweise nicht ändern. |

---

## Admin-Panel Einstellungen

### URLs

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| Admin Panel URL | *(Setup-Wizard)* | Interne URL des Admin-Panels. Wird für interne Links verwendet. |
| Proxy URL | *(Setup-Wizard)* | Interne IP:Port des IPTV-Proxys (z.B. `http://192.168.1.69:8000`). Wird vom Server selbst verwendet. |
| Öffentliche Domain / Short URL | *(leer)* | Deine öffentliche Subdomain (z.B. `https://iptv.deinedomain.de`). **Diese URL wird in alle M3U Stream-Links eingebaut.** Leer lassen = lokale IP wird verwendet (nur Heimnetz). |

> **Wichtig:** Wenn du einen Reverse Proxy verwendest (Zoraxy, Nginx, Caddy), trage deine Subdomain als **Öffentliche Domain** ein. Ohne diese Einstellung funktionieren Streams nur im lokalen Netzwerk.

### HLS / Stream

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| `hls_timeout` | `15` | Verbindungs-Timeout in Sekunden (zum Anbieter) |
| `hls_read_timeout` | `60` | Lese-Timeout in Sekunden zwischen Chunks (Catchup / langsame CDN) |
| `hls_chunk_size` | `65536` | Chunk-Größe in Bytes beim Streamen von TS-Segmenten (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User-Agent für ausgehende Requests zum IPTV-Anbieter |
| `hls_referer` | *(leer)* | Referer-Header (falls vom Anbieter benötigt) |
| `hls_follow_redirects` | `1` | HTTP-Redirects folgen (`1` = ja, `0` = nein) |
| `prefetch_segments` | `2` | Wie viele Segmente vorab geladen werden (0 = deaktiviert) |
| `diagnostics_enabled` | `1` | Globaler Diagnose-Master (`1` = Diagnose-Logs schreiben, `0` = neue Diagnose-Einträge deaktivieren) |

### EPG

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| `epg_refresh_hours` | `6` | Wie oft der EPG-Cache erneuert wird (in Stunden) |
| `epg_filter_channels` | `0` | EPG auf Kanäle aus dem Kanal-Manager filtern |

---

## Empfohlene Catchup-Einstellungen (stabile Basis)

Für die meisten Setups (vor allem IPTV Pro / TiviMate) liefert dieses Profil stabiles Catchup-Verhalten mit weniger ungewollten Sprüngen:

- `catchup_guard_master = 1`
- `catchup_strict_mode = 1`
- `catchup_sticky_recover = 1`
- `catchup_auto_live_on_program_change = 0` (verhindert Auto-Sprünge auf Live am Sendungswechsel)
- `catchup_auto_live_keep_utc = 0` (nur relevant, wenn Auto-Live aktiviert ist)
- `catchup_force_same_channel_live = 1`
- `catchup_hard_lock = 0` (nur aktivieren, wenn dein Client ständig auf Live ausbricht)
- `diagnostics_enabled = 0` im Alltag, für Fehlersuche kurz auf `1`
- `player_request_debug = 0` im Alltag, für Diagnose-Sessions kurz auf `1`

Tipp: Nach Änderungen an Catchup-Guards speichern und einen kompletten Catchup-Test bis zur Sendungsgrenze durchlaufen lassen, um das Verhalten beim Anbieter zu prüfen.

---

## Benutzer einrichten

1. Admin Panel öffnen → **Benutzer** → **+ Benutzer hinzufügen**
2. Name eingeben (z.B. "Kinder-Tablet", "Wohnzimmer TV")
3. Max. Streams einstellen (Standard: 1)
4. Optional eigene Gruppen zuweisen (z.B. Kinder, Sport)
5. Playlist-URLs weitergeben:

| URL | Verwendung |
|-----|-----------|
| 📋 (türkiser Button) | Externe URL via Subdomain — für User außerhalb des Heimnetzes |
| 🏠 (gelber Button) | Lokale Test-URL — für Admin-Tests im lokalen Netzwerk |

Die externe URL in TiviMate, IPTV Pro, VLC oder einer anderen IPTV-App eintragen.

---

## Subdomain einrichten (Reverse Proxy)

Damit Streams auch von außerhalb des Heimnetzes erreichbar sind:

1. Subdomain (z.B. `iptv.deinedomain.de`) auf die öffentliche IP des Servers zeigen lassen
2. Reverse Proxy (Zoraxy, Nginx, Caddy) so konfigurieren dass Port 80/443 → `192.168.1.x:8000` weitergeleitet wird
3. Im selfstream Admin → **Einstellungen** → Subdomain unter **Öffentliche Domain / Short URL** eintragen
4. **Speichern** klicken — alle M3U- und Stream-Links werden sofort aktualisiert

**Wichtig für Zoraxy / Nginx:** Proxy-Buffering muss deaktiviert sein damit Streaming korrekt funktioniert. selfstream sendet automatisch `X-Accel-Buffering: no`.

---

## VPN einrichten

1. Admin Panel → **VPN**
2. OpenVPN-Zugangsdaten eintragen (Benutzername & Passwort von deinem VPN-Anbieter)
3. **Datei wählen** → `.ovpn`-Datei hochladen (vom VPN-Anbieter unter Manuelle Konfiguration → OpenVPN herunterladen)
4. **▶ VPN Starten** klicken
5. Das Live-Log zeigt den Verbindungsfortschritt; nach erfolgreicher Verbindung wird die öffentliche IP angezeigt

**Profile wechseln:** Mehrere `.ovpn`-Dateien hochladen (z.B. verschiedene Länder) und mit **Aktivieren** zwischen ihnen wechseln. VPN danach stoppen und neu starten.

**Getestete Anbieter:** ExpressVPN — andere OpenVPN-kompatible Anbieter sollten ebenfalls funktionieren.

---

## Speedtest

Admin Panel → **VPN** → nach unten scrollen zu **Speedtest – Flaschenhals-Analyse**

- **▶ Speedtest starten** klicken
- Zwei Tests laufen gleichzeitig:
  1. **Internet / VPN** – Lädt von Cloudflare/OVH um die reine Tunnel-Geschwindigkeit zu messen
  2. **IPTV-Anbieter** – Lädt 5 echte Segmente von 5 Kanälen parallel
- Das Flaschenhals-Banner zeigt welche Seite deine Stream-Kapazität begrenzt

**Ergebnisse interpretieren:**
- IPTV-Anbieter-Speed << Internet-Speed → Anbieter ist der Flaschenhals (häufig mit VPN)
- Beide ähnlich → kein Flaschenhals, VPN-Overhead minimal
- Stream-Schätzungen: ~4 Mbit/s (HD), ~8 Mbit/s (FHD), ~25 Mbit/s (4K)

---

## Traffic-Analyse

Admin Panel → **Traffic**

- **Live Streams** – Alle aktiven Sessions mit User, IP, Kanal, Sendung, Dauer, geschätzter Bandbreite
- **Stream-Verlauf-Chart** – Zeitbereich wählbar (5 Min bis Alles); Y-Achse zeigt Stream-Anzahl; rote Punkte markieren Spitzenzeiten
- **Buffering-Ereignisse** – Automatisches Log langsamer Segment-Downloads; hilft beim Diagnostizieren von Stottern/Einfrieren

**Buffering-Log lesen:**
- 🔴 >2s Download-Zeit → Player hat sehr wahrscheinlich gepuffert
- 🟡 >1s Download-Zeit → Player hat möglicherweise kurz pausiert
- Hoher Speed (>20 Mbit/s) trotzdem langsam = große Segmente (normal bei manchen Anbietern)
- Niedriger Speed (<4 Mbit/s) = Anbieter-/VPN-Flaschenhals

---

## Eigene Gruppen

Eigene Kanalgruppen erstellen, unabhängig von Anbieter-Gruppen:

1. Admin Panel → **Gruppen** → Gruppenname eingeben → **+ Neue Gruppe**
2. Klick auf **✏ Kanäle bearbeiten** → Kanäle aus beliebigen Anbieter-Gruppen auswählen
3. User zuweisen → **🔒 Gruppen** beim User → eigene Gruppe anhaken
4. User sieht nur die Kanäle seiner Gruppe — egal wie der Anbieter sie nennt

**IPTV Pro Sortierung:** Nummerierung im Gruppen-Tab aktivieren um die Kategorien-Reihenfolge in IPTV Pro zu erzwingen (z.B. "01. Kinder", "02. Sport", "03. Doku").

**Anbieter-Gruppen Reihenfolge:** Im Gruppen-Tab per Drag & Drop alle Gruppen (eigene + Anbieter) in einer gemeinsamen Liste sortieren — die gespeicherte Reihenfolge wird auf jede Playlist angewendet.

---

## URLs & Endpunkte

### Proxy (Port 8000)

| URL | Beschreibung |
|-----|-------------|
| `/iptv/{token}/playlist.m3u` | M3U-Playlist für den User |
| `/iptv/{token}/playlist.m3u?local=1` | Lokale Test-Playlist (alle Links mit interner IP) |
| `/iptv/{token}/playlist.m3u8` | M3U8-Playlist (alternativ) |
| `/iptv/{token}/epg.xml` | EPG für den User |
| `/{short_token}.m3u` | Kompakte Short-Playlist-URL |
| `/s/{short_token}/playlist.m3u` | Short-Playlist-URL |
| `/iptv/epg.xml` | Globale EPG-URL (für alle gleich) |
| `/iptv/epg-1d.xml` | EPG gefiltert – 1 Tag zurück **und** 1 Tag voraus |
| `/iptv/epg-3d.xml` | EPG gefiltert – 3 Tage zurück **und** 3 Tage voraus |
| `/iptv/epg-7d.xml` | EPG gefiltert – 7 Tage zurück **und** 7 Tage voraus |

---

## Stream-Schutz

- Stream startet → Session wird in SQLite gespeichert
- Zweites Gerät versucht zu streamen → blockiert mit **HTTP 429**
- Session endet automatisch wenn keine Segmente mehr angefragt werden (TTL: 35 Sekunden)
- Fallback TTL: 4 Stunden (Datenbank)
- Catchup-Streams zählen **nicht** gegen das Stream-Limit

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Setup-Seite erscheint wieder | Browser-Cache leeren (Strg+Shift+R) |
| Stream startet nicht | M3U-URL im Admin prüfen → Kanäle → Refresh |
| „Max. Streams erreicht" | Anderen Stream beenden oder 35 Sekunden warten |
| Admin Panel nicht erreichbar | Port 8080 in Firewall freigeben; bei Unraid: Docker-Einstellungen prüfen |
| EPG wird nicht angezeigt | Admin → EPG → EPG einlesen klicken; danach Auto-Match |
| Catchup funktioniert nicht | IPTV-Anbieter muss Catchup unterstützen (`tvg-rec` in M3U) |
| Senderwechsel dauert lange | Connect Timeout auf 3–5s senken in Einstellungen → HLS |
| VPN verbindet nicht | Anderen Server probieren oder in der `.ovpn`-Datei auf TCP wechseln (`proto tcp`) |
| VPN aktiv aber Streams kaputt | Prüfen ob Privilegierter Modus oder `--cap-add=NET_ADMIN` gesetzt ist |
| Buffering mit VPN | Speedtest machen; geografisch näheren VPN-Server probieren |
| Stream stottert ohne VPN | Buffering-Ereignisse im Traffic-Tab prüfen; große Segmente (>5 MB) sind bei manchen Anbietern normal |
| Externe Streams funktionieren nicht | Subdomain unter Einstellungen → Öffentliche Domain eintragen. Ohne diese Einstellung enthalten Stream-Links die lokale IP |
| Lokal geht es, extern nicht | Prüfen ob Reverse Proxy auf Port 8000 weiterleitet (nicht 8080) |
| M3U-Import aktualisiert Kanäle aber User nutzen noch alte URL | Beim Import-Dialog die Option „Alle bestehenden User auf neue URL umstellen" aktivieren |

---

## Optional: Catchup HLS-Debug (Browser)

Eigenes kleines Docker-Image zum Debuggen von Catchup im Browser (**hls.js** + Ereignis-Log): **[catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug)**. Öffentliche **M3U- und EPG-URLs** eintragen; Stream-Zeilen enthalten bereits Pfad und Token. **Ersetzt** selfstream **nicht** — parallel auf einem anderen Port starten.

| | |
|--|--|
| **Repository** | [github.com/kabelsalatundklartext/catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug) |
| **Image** | `ghcr.io/kabelsalatundklartext/catchup-hls-debug:latest` (GitHub Actions bei Push auf `main`) |
| **Unraid „Template URL“** | `https://raw.githubusercontent.com/kabelsalatundklartext/catchup-hls-debug/main/unraid/catchup-hls-debug.xml` |

---

## Technologie

- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow
- **VPN:** OpenVPN (im Container installiert)
- **Datenbank:** SQLite (kein externer Server nötig)
- **Frontend:** Vanilla HTML/CSS/JS (kein Framework)
- **Container:** Python 3.12 slim, ~200 MB Image

---

## Lizenz

**GNU General Public License v3.0 (GPL-3.0)**

|  |  |
|--|--|
| ✅ Privat & Homelab nutzen | ✅ Verändern & anpassen |
| ✅ Weitergeben & teilen | ✅ Eigene Versionen veröffentlichen |
| ✅ Kommerzieller Einsatz erlaubt | ❌ Closed-Source-Abwandlungen verboten |
| ✅ Forks müssen GPL-3.0 bleiben | ✅ Quellcode muss immer offen bleiben |

> *"selfstream" von s3lfcod3r — [GitHub](https://github.com/s3lfcod3r/selfstream)*
