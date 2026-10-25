<div align="center">

<img src="assets/logo.png" width="240" alt="SelfStream logo" />

**Self-hosted IPTV proxy — with user management, stream protection, EPG, a built-in WireGuard VPN and traffic analysis.**<br>
*Selbstgehosteter IPTV-Proxy — mit Benutzerverwaltung, Stream-Schutz, EPG, integriertem WireGuard-VPN und Traffic-Analyse.*

[![Build](https://github.com/s3lfcod3r/selfstream/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/s3lfcod3r/selfstream/actions/workflows/docker-publish.yml)
![Version](https://img.shields.io/badge/version-1.83-33A78C)
![License](https://img.shields.io/badge/license-All%20rights%20reserved-8A9CAA)
![Backend](https://img.shields.io/badge/backend-FastAPI-1F7763)
![Web](https://img.shields.io/badge/web-Vanilla%20JS-43D3AD)
![Deploy](https://img.shields.io/badge/deploy-Docker%20%7C%20Unraid-6F95AD)

**[🇬🇧 English](#-english) · [🇩🇪 Deutsch](#-deutsch)**

📰 **What's new / Neuigkeiten** → [CHANGELOG.md](CHANGELOG.md)

</div>

---

<a id="-english"></a>

## 🇬🇧 English

A single Docker container that sits between your **IPTV provider** and your players: every family member gets their **own M3U URL with a token**, a **stream limit**, their own **channel groups** — and you see who watches what. It adds **EPG**, **catchup**, a **built-in WireGuard VPN** and **traffic analysis**, with no Redis and no external database. It is **not** a provider and **not** a player — and it only works with **HLS providers** (M3U with `.m3u8` streams); Xtream Codes API, STRM files and other formats are not supported.

Part of the **Self** family (SelfMailer, SelfArchiver, SelfDashboard …) — same design system, same deploy style (GHCR → Unraid).

> **TL;DR** — IPTV proxy for HLS providers · one M3U URL per user · stream limit (HTTP 429) · EPG + catchup · watch & IP tracking · built-in WireGuard/Mullvad VPN · speedtest + traffic analysis · single container · SQLite.

### 📑 Table of contents

[Features](#en-features) · [Architecture](#en-architecture) · [Users](#en-users) · [Custom groups](#en-groups) · [Subdomain](#en-subdomain) · [VPN](#en-vpn) · [Speedtest](#en-speedtest) · [Traffic analysis](#en-traffic) · [Stream protection](#en-stream-protection) · [Quick start](#en-quick-start) · [Unraid](#en-unraid) · [Configuration](#en-configuration) · [API](#en-api) · [Security](#en-security) · [Tech stack](#en-tech-stack) · [Development](#en-development) · [Roadmap](#en-roadmap)

<a id="en-features"></a>

### ✨ Features

**📺 Core**
- **User management** — every user gets their own M3U URL with token
- **Max. streams per user** — configurable, additional devices are blocked with **HTTP 429**
- **Catchup / timeshift** — watch past content, works with IPTV Pro & TiviMate
- **EPG integration** — programme info in the dashboard (what's on now, what was watched)
- **Watch tracking** — channel, show title, duration, timestamp — all stored
- **IP tracking** — IP address logged per stream session and in the watch history
- **Admin dashboard** — live sessions, live catchup, history, users, channels, EPG, settings
- **Custom groups** — create your own channel groups (e.g. Kids, Sports, Docs) and assign users
- **Group & provider sorting** — drag & drop for custom and provider groups; numbering forces the order in IPTV Pro (e.g. "01. Kids", "02. Sports")
- **Brute-force protection** — admin login locked after 10 failed attempts
- **Short URLs** — short playlist URLs via your own domain (e.g. `https://iptv.yourdomain.com/AbCd1234.m3u`)
- **Channel manager** — enable/disable, sort, filter channels by group
- **EPG manager** — multiple EPG sources, time filter (1/3/7 days), auto-refresh, channel whitelist
- **M3U auto-refresh** — reload channels on a schedule per provider
- **M3U import** — import via URL; optionally update all existing users at once
- **Setup wizard** — on first start, no manual config editing needed
- **Single container** — Python + FastAPI + SQLite, no Redis, no Nginx

**🌐 Subdomain / reverse proxy**
- **Public URL** — set your subdomain as the public domain; all M3U and stream links are built with it
- **`X-Accel-Buffering: no`** — sent by SelfStream so reverse proxies (Zoraxy, Nginx, Caddy) pass segments through without buffering
- **Full URL chain** — playlist → stream playlist → segments, all consistently on your public domain
- **Local test button** — the 🏠 button per user generates a local test URL (`?local=1`) with the internal IP, for quick diagnostics without touching the public setup
- **`PROXY_URL`** — set the public proxy URL via environment variable for docker-compose setups

**🔒 VPN (built-in WireGuard / Mullvad)**
- **Integrated WireGuard** — start/stop the tunnel in the admin panel, no extra container (much faster and more CPU-efficient than OpenVPN)
- **Mullvad auto-import** — upload one Mullvad `.conf`, pull every WireGuard server from Mullvad's API (optionally by country) and get one config per server
- **Seamless server switch** — only the peer (server + endpoint) is swapped on the live interface — practically no interruption, **even while viewers are watching**
- **Auto-Best (WireGuard, seamless)** — reacts to real stuttering (measured from viewer segments) and switches to the fastest reachable server, with throughput threshold and cooldown (no flapping)
- **Find fastest server (latency)** — non-disruptive ranking via a stream-safe direct route (probes never go through the tunnel)
- **Live status + log** — connection status, current public IP and a real-time tunnel log in the browser
- **Auto-start & local route** — the tunnel reconnects on container restart; the admin panel stays fast while the VPN is active (local network routed via `eth0`)
- **Requires** `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` (or privileged mode in Unraid)

**📊 Traffic analysis**
- **Live stream monitor** — all active streams with user, IP, channel, show title and duration
- **Estimated bandwidth** — real-time Mbit/s estimate from the active streams
- **Stream history chart** — Y-axis labels, peak markers, time labels; range 5 min / 15 min / 30 min / 1 h / all
- **Peak tracking** — highest concurrent stream count per session
- **Buffering events** — automatic detection of slow (> 2 s, buffering very likely) and delayed (> 1 s, buffering possible) segments, with timestamp, user, duration, segment size, download speed and segment name

**🚀 Speedtest**
- **Dual speedtest** — internet/VPN speed and IPTV provider speed measured separately
- **Bottleneck detection** — tells whether the VPN tunnel or the IPTV provider is the limiting factor
- **Parallel IPTV test** — 5 segments from 5 different channels at once for a realistic load test
- **Stream capacity estimate** — max. concurrent HD / FHD / 4K streams

**⚡ Performance**
- **Segment pre-buffering** — each TS segment is fully downloaded before it goes to the player, so the player gets it at LAN speed (~900 Mbit/s) instead of provider speed
- **Segment prefetch cache** — while one segment plays, the next 2 are already loading; cache hits are delivered almost instantly
- **Tiny segment retry** — broken segments (< 1 KB) are retried once
- **Shared segment cache** — users watching the same channel share the cache; the provider is hit only once per segment

**👥 User management**
- **Per-user log view** — **Log** opens a user's watch history in a modal
- **Date filter** — filter user logs by date range (from / to)
- **Pagination** — 25 / 50 / 100 entries per page
- **Delete user logs** — 🗑 in the log modal clears only that user's history
- **Token display** — 👁 reveals the full token (wraps, fully readable)
- **Local test URL** — 🏠 copies a local playlist URL for admin testing without affecting users

<a id="en-architecture"></a>

### 🧭 Architecture

```text
   ┌────────────────────────────┐        ┌──────────────────┐
   │ IPTV apps                  │        │  You (browser)   │
   │ TiviMate · IPTV Pro · VLC  │        │  admin panel     │
   └─────────────┬──────────────┘        └────────┬─────────┘
       M3U · HLS · EPG (token)             /api · X-Admin-Token
                 │ :8000                          │ :8080
          ┌──────▼────────────────────────────────▼──────┐
          │                SelfStream                    │
          │  proxy: playlist rewrite · stream limit      │
          │         segment cache + prefetch · catchup   │
          │  admin: users · groups · EPG · VPN · traffic │
          │  SQLite (/data)                              │
          └──────────────────────┬───────────────────────┘
                                 │ optional WireGuard tunnel (wg0)
                    ┌────────────▼────────────┐
                    │ IPTV provider (HLS)     │
                    │ EPG sources (XMLTV)     │
                    └─────────────────────────┘
```

<a id="en-users"></a>

### 👥 Setting up users

1. Admin panel → **Users** → **+ Add User**
2. Enter a name (e.g. "Kids Tablet", "Living Room TV")
3. Set max streams (default: 1)
4. Optionally assign custom groups (e.g. Kids, Sports)
5. Share the generated playlist URLs:

| Button | Use case |
|---|---|
| 📋 (teal) | External URL via subdomain — for users outside your network |
| 🏠 (yellow) | Local test URL — for admin testing on your local network |

Enter the external URL in TiviMate, IPTV Pro, VLC or any other IPTV app.

<a id="en-groups"></a>

### 🗂️ Custom groups

Create your own channel groups, independent of the provider groups:

1. Admin panel → **Groups** → enter a group name → **+ New Group**
2. **✏ Edit Channels** → select channels from any provider group
3. Assign to a user → **🔒 Groups** on the user → tick your custom group
4. The user sees only the channels in their group — regardless of what the provider calls them

**IPTV Pro category order:** enable numbering in the Groups tab to force the order in IPTV Pro (e.g. "01. Kids", "02. Sports", "03. Docs").

**Provider group order:** sort all groups (custom and provider) in one drag & drop list in the Groups tab — the saved order is applied to every playlist.

<a id="en-subdomain"></a>

### 🌐 Subdomain setup (reverse proxy)

To make streams reachable from outside your home network:

1. Point your subdomain (e.g. `iptv.yourdomain.com`) to your server's public IP
2. Configure your reverse proxy (Zoraxy, Nginx, Caddy) to forward 80/443 → `192.168.1.x:8000`
3. SelfStream admin → **Settings** → enter the subdomain under **Public Domain / Short URL**
4. **Save** — all M3U and stream links are updated instantly

> **⚠️ Zoraxy / Nginx:** proxy buffering must be disabled for streaming to work. SelfStream sends `X-Accel-Buffering: no` automatically.

<a id="en-vpn"></a>

### 🔒 VPN setup

1. Admin panel → **VPN**
2. **Choose File** → upload one WireGuard `.conf` (from your provider; for Mullvad: download a WireGuard config with **IPv4 only**)
3. **Mullvad only:** pick a country in the import box and click **Import all** — one config per Mullvad server is created from the key/address in your `.conf`
4. **Activate** a server, then **▶ Start VPN**
5. The live log shows the progress; once connected, the public IP is displayed

**Switching servers:** click **Switch** (or **Activate**) on any server — with WireGuard it changes **seamlessly** on the live tunnel, no restart, no interruption (even while viewers are watching).

**Find the best server:** use **Find fastest server (latency)** for a stream-safe ranking, or turn on **🏆 Auto-Best** to switch to the fastest server automatically whenever quality drops.

**Tested providers:** Mullvad (WireGuard). Any WireGuard `.conf` should work.

<a id="en-speedtest"></a>

### 📈 Speedtest

Admin panel → **VPN** → scroll down to **Speedtest – Bottleneck Analysis** → **▶ Start Speedtest**. Two tests run at the same time:

1. **Internet / VPN** — downloads from Cloudflare/OVH to measure the raw tunnel speed
2. **IPTV provider** — downloads 5 real segments from 5 channels in parallel

The bottleneck banner shows which side limits your stream capacity.

**Interpreting results:**
- IPTV provider speed far below internet speed → the provider is the bottleneck (common with VPN)
- Both similar → no bottleneck, VPN overhead is minimal
- Stream estimates assume ~4 Mbit/s (HD), ~8 Mbit/s (FHD), ~25 Mbit/s (4K)

<a id="en-traffic"></a>

### 📊 Traffic analysis

Admin panel → **Traffic**

- **Live streams** — all active sessions with user, IP, channel, show title, duration, estimated bandwidth
- **Stream history chart** — time range 5 min to all; Y-axis = stream count; red dots mark peak times
- **Buffering events** — automatic log of slow segment downloads; helps diagnose freezing/stuttering

**Reading the buffering log:**
- \> 2 s download time (red) → the player very likely buffered
- \> 1 s download time (yellow) → the player may have paused briefly
- High speed (> 20 Mbit/s) but still slow = large segments (normal for some providers)
- Low speed (< 4 Mbit/s) = provider/VPN bottleneck

<a id="en-stream-protection"></a>

### 🚦 Stream protection

- Stream starts → session stored in SQLite
- A second device tries to stream → blocked with **HTTP 429**
- The session ends automatically when no segments are requested (TTL: 35 seconds)
- Fallback TTL: 4 hours (database)
- Catchup streams do **not** count against the stream limit

<a id="en-quick-start"></a>

### 🚀 Quick start (Docker)

```bash
git clone https://github.com/s3lfcod3r/selfstream.git
cd selfstream
cp .env.example .env    # optional — all values may stay empty
docker compose up -d
```

Open `http://<host>:8080/admin` → the **setup wizard** sets the admin token and URLs → then add your provider's M3U.

<details>
<summary><b>Setup — docker run (with and without VPN)</b></summary>

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

`--cap-add=NET_ADMIN` and `--device=/dev/net/tun` are only needed for the built-in VPN; omit them if you don't need it.

**Optional non-root mode (no VPN):** set `SELFSTREAM_UID` to the UID of the host user that owns the `/data` volume. Only for setups **without** VPN.

```bash
docker run -d \
  -e SELFSTREAM_UID=1000 \
  -p 8000:8000 \
  -p 8080:8080 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/s3lfcod3r/selfstream:latest
```

The UID must match the host user that owns `/data` (on Unraid the UID of the user running the container, e.g. 1000 or 101) — otherwise the container cannot write the database and refuses to start.
</details>

<a id="en-unraid"></a>

### 📦 Unraid

Open **Community Apps** → search for **selfstream** → install (recommended). Or add the template from
`https://raw.githubusercontent.com/s3lfcod3r/selfstream/main/unraid/selfstream.xml`
under *Docker → Add Container → Template*. Then open `http://<host>:8080/admin` and follow the setup wizard.

> **⚠️ Permissions:** the container runs as **root** by default — the VPN needs `--cap-add=NET_ADMIN` and `--device=/dev/net/tun` (already set in the template). For setups without VPN, see `SELFSTREAM_UID` under [Configuration](#en-configuration).

<a id="en-configuration"></a>

### ⚙️ Configuration

Environment variables (no common prefix). All are optional — empty values start the setup wizard on first run.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ADMIN_TOKEN` | – | – | Admin password. Empty → setup wizard on first start. If set, the password **cannot** be changed in the UI. |
| `BASE_URL` | – | – | Public URL of the admin panel, e.g. `http://192.168.1.69:8080`. Empty → set in the setup wizard. |
| `PROXY_URL` | – | – | Public URL of the IPTV proxy (e.g. `https://iptv.yourdomain.com`). Overrides the proxy URL from the database; all M3U and stream links use it. |
| `DB_PATH` | – | `/data/selfstream.db` | Path to the SQLite database. Usually no need to change. |
| `SELFSTREAM_UID` | – | – | Run as this non-root UID (only **without** VPN). Must match the owner of `/data`. |

#### Ports

| Port | Usage | Who needs it? |
|---|---|---|
| `8000` | IPTV proxy — M3U playlists, streams, EPG | All users, IPTV apps |
| `8080` | Admin panel | Only you |

> **💡 Tip:** port 8080 doesn't need to be public. You can remap it, e.g. `8888:8080`.

#### Admin panel settings

**URLs**

| Setting | Default | Description |
|---|---|---|
| Admin Panel URL | *(setup wizard)* | Internal URL of the admin panel, used for internal links. |
| Proxy URL | *(setup wizard)* | Internal IP:port of the IPTV proxy (e.g. `http://192.168.1.69:8000`), used by the server itself. |
| Public Domain / Short URL | – | Your public subdomain (e.g. `https://iptv.yourdomain.com`). **Embedded in all M3U stream links.** Empty = local IP (home network only). |

> **⚠️ Reverse proxy:** if you use Zoraxy, Nginx or Caddy, set your subdomain as the **Public Domain** — without it, streams only work on your local network.

**HLS / stream**

| Setting | Default | Description |
|---|---|---|
| `hls_timeout` | `15` | Connection timeout in seconds (outbound to the provider) |
| `hls_read_timeout` | `60` | Read timeout in seconds between chunks (catchup / slow CDNs often need 45–60 s+) |
| `hls_chunk_size` | `65536` | Chunk size in bytes for TS segment streaming (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User agent for outgoing requests to the provider |
| `hls_referer` | – | Referer header (if the provider requires one) |
| `hls_follow_redirects` | `1` | Follow HTTP redirects (`1` = yes, `0` = no) |
| `prefetch_segments` | `2` | Segments to prefetch ahead (`0` = off) |
| `diagnostics_enabled` | `1` | Global diagnostics switch (`1` = write diagnostic logs, `0` = no new entries) |

**EPG**

| Setting | Default | Description |
|---|---|---|
| `epg_refresh_hours` | `6` | How often the EPG cache is renewed (hours) |
| `epg_filter_channels` | `0` | Filter the EPG to channels in the channel manager |

#### Recommended catchup settings (stable baseline)

For most setups (especially IPTV Pro / TiviMate) this profile gives stable catchup with fewer unexpected jumps:

```text
catchup_guard_master = 1
catchup_strict_mode = 1
catchup_sticky_recover = 1
catchup_auto_live_on_program_change = 0   # no auto-jump to live at the programme boundary
catchup_auto_live_keep_utc = 0            # only relevant if auto-live is on
catchup_force_same_channel_live = 1
catchup_hard_lock = 0                     # enable only if your client keeps escaping to live
diagnostics_enabled = 0                   # set to 1 only while troubleshooting
player_request_debug = 0                  # set to 1 only for short diagnostic sessions
```

> **💡 Tip:** after changing catchup guard settings, save and run one complete catchup test up to the programme boundary to verify the behaviour with your provider.

For debugging catchup in the browser there is a **separate** small image (hls.js + event log): [catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug). Paste your **public M3U and EPG URLs**; stream lines already contain the SelfStream path and token (`…/stream?url=…&utc=…`). It does **not** replace SelfStream — run it alongside on another port.

| | |
|---|---|
| **Repository** | [github.com/kabelsalatundklartext/catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug) |
| **Image** | `ghcr.io/kabelsalatundklartext/catchup-hls-debug:latest` (built via Actions on `main`) |
| **Unraid template URL** | `https://raw.githubusercontent.com/kabelsalatundklartext/catchup-hls-debug/main/unraid/catchup-hls-debug.xml` |

#### Troubleshooting

| Problem | Solution |
|---|---|
| Setup page appears again | Clear the browser cache (Ctrl+Shift+R) |
| Stream won't start | Check the M3U URL: Admin → Channels → Refresh |
| "Max. streams reached" | Stop another stream or wait 35 seconds |
| Admin panel unreachable | Open port 8080 in the firewall; on Unraid check the Docker settings |
| EPG not showing | Admin → EPG → "Load EPG", then Auto-Match |
| Catchup not working | The provider must support catchup (`tvg-rec` in the M3U) |
| Channel switch slow | Lower the connect timeout to 3–5 s in Settings → HLS |
| VPN won't connect | Try another server (Activate + Start); make sure the Mullvad `.conf` was downloaded as **IPv4 only** |
| VPN active but streams broken | Check that privileged mode or `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` is set |
| Buffering with VPN | **Find fastest server (latency)** and switch (seamless), or turn on **🏆 Auto-Best** |
| Stream stutters without VPN | Check buffering events in the Traffic tab; large segments (> 5 MB) are normal for some providers |
| External streams not working | Set your subdomain in Settings → Public Domain; without it, stream links contain your local IP |
| Works locally but not externally | Make sure the reverse proxy forwards to port 8000 (not 8080) |
| M3U import updates channels but users still use the old URL | Tick "Update all users to new URL" in the import dialog |

<a id="en-api"></a>

### 🔌 API overview

Admin API on port 8080 under `/api`, authentication via the `X-Admin-Token` header. Interactive docs: `http://<host>:8080/docs`.

| Group | Endpoints (excerpt) |
|---|---|
| **Setup** | `setup`, `setup/status`, `settings`, `settings/change-password` |
| **Users & groups** | `users`, `users/{user_id}/logs`, `users/{user_id}/regenerate-token`, `user-groups` |
| **Channels & providers** | `channels`, `channels/import`, `channels/refresh`, `providers`, `providers/{provider_id}/refresh` |
| **EPG** | `epg`, `epg/refresh`, `epg/quality`, `epg/archive`, `epg/archive/browse`, `epg/channels/orphans` |
| **VPN** | `vpn/upload`, `vpn/start`, `vpn/stop`, `vpn/switch`, `vpn/mullvad-import`, `vpn/wg-autobest`, `vpn/server-latency`, `vpn/canary` |
| **Diagnostics** | `stats`, `memstats`, `segment-events`, `alerts`, `alerts/test`, `diagnostic-logs`, `vpn/speedtest`, `iptv/capacity` |

**Proxy (port 8000)** — for players:

| URL | Description |
|---|---|
| `/iptv/{token}/playlist.m3u` | M3U playlist for the user |
| `/iptv/{token}/playlist.m3u?local=1` | Local test playlist (internal IP in all links) |
| `/iptv/{token}/playlist.m3u8` | M3U8 playlist (alternative) |
| `/iptv/{token}/epg.xml` | EPG for the user |
| `/{short_token}.m3u` | Compact short playlist URL |
| `/s/{short_token}/playlist.m3u` | Short playlist URL |
| `/iptv/epg.xml` | Global EPG URL (same for all users) |
| `/iptv/epg-1d.xml` | EPG filtered — 1 day back **and** 1 day forward |
| `/iptv/epg-3d.xml` | EPG filtered — 3 days back **and** 3 days forward |
| `/iptv/epg-7d.xml` | EPG filtered — 7 days back **and** 7 days forward |

<a id="en-security"></a>

### 🛡️ Security

- Admin token stored as **PBKDF2-HMAC-SHA256** (600k rounds); login locked after **10 failed attempts**
- Wrong tokens on the proxy are counted per IP — after 30 in 5 minutes the proxy answers **429** with `Retry-After`
- **SSRF guard** on the public proxy: only `http`/`https`, internal/private targets blocked — **including redirect hops**
- **No credentials in the logs:** user tokens, short links and provider credentials are masked in the access log
- CORS on the admin panel limited to local/LAN origins; security headers incl. HSTS and `Permissions-Policy`
- OpenVPN configs (legacy) are stripped of script directives and run with `--script-security 0`; uploads are size-limited and names/endpoints strictly validated
- **Deliberate trade-offs** (documented in [SECURITY.md](SECURITY.md)): the container runs as **root** with `CAP_NET_ADMIN` + `/dev/net/tun` for the VPN, the root filesystem is writable; during setup over plain HTTP in the LAN the new admin token travels unencrypted; the admin panel (port 8080) is meant for a trusted LAN and should **not** be exposed to the internet
- Report vulnerabilities privately — see [SECURITY.md](SECURITY.md)

Security update history → [CHANGELOG.md](CHANGELOG.md) (entries marked 🔒).

<a id="en-tech-stack"></a>

### 🧱 Tech stack

| Part | Tech |
|---|---|
| Backend | Python 3.12 · FastAPI · uvicorn · httpx · Pillow |
| Database | SQLite (no external server) |
| Web | Vanilla HTML · CSS · JS (no framework) |
| VPN | WireGuard (wireguard-tools in the container) · OpenVPN (legacy fallback) |
| Deploy | Docker (`python:3.12-slim`, ~200 MB) · GHCR (amd64 + arm64) · Unraid |
| License | All rights reserved — private, non-commercial use only; no copying, modifying, redistributing or selling ([LICENSE](LICENSE)) |

<a id="en-development"></a>

### 🛠️ Development

```bash
pip install -r backend/requirements.txt -r requirements-dev.txt
cd backend && DB_PATH=./selfstream.db python server.py   # proxy :8000, admin :8080
```

**Tests:**

```bash
pytest -v
flake8 backend/ tests/ --max-line-length=120 --extend-ignore=E501,W503,F401   # report only in CI
black --check --diff backend/ tests/                                          # report only in CI
```

`setup.sh` creates `/mnt/user/appdata/selfstream` with a `.env` and starts the stack; `update.sh` live-patches `backend/` and `frontend/` from `main` into a running container (hotfixes only).

<a id="en-roadmap"></a>

### 🗺️ Roadmap

- [x] Users with own M3U URL · stream limit · watch & IP tracking · custom groups
- [x] Stable channel ids — provider server changes without reloading playlists
- [x] Built-in WireGuard + Mullvad auto-import · seamless server switch · Auto-Best
- [x] Speedtest with bottleneck analysis · capacity test · canary self-viewer · e-mail alerts
- [x] Multiple EPG sources · own EPG archive · cleanup of mixed programme lists
- [x] Security hardening (SSRF, PBKDF2, CORS, no credentials in logs)
- [ ] Drop root: `--read-only` + `--tmpfs /tmp` first, then `USER` with capabilities on the VPN binaries
- [ ] `VACUUM` for the SQLite file in a maintenance window
- [ ] Split `main.py` into route modules

<p align="right"><a href="#-english">⬆ back to top</a></p>

---

<a id="-deutsch"></a>

## 🇩🇪 Deutsch

Ein einzelner Docker-Container zwischen deinem **IPTV-Anbieter** und deinen Playern: Jedes Familienmitglied bekommt eine **eigene M3U-URL mit Token**, ein **Stream-Limit** und eigene **Kanalgruppen** — und du siehst, wer was schaut. Dazu kommen **EPG**, **Catchup**, ein **integriertes WireGuard-VPN** und **Traffic-Analyse**, ohne Redis und ohne externe Datenbank. Er ist **kein** Anbieter und **kein** Player — und funktioniert nur mit **HLS-Anbietern** (M3U mit `.m3u8`-Streams); Xtream Codes API, STRM-Dateien und andere Formate werden nicht unterstützt.

Teil der **Self**-Familie (SelfMailer, SelfArchiver, SelfDashboard …) — gleiches Design-System, gleicher Deploy-Stil (GHCR → Unraid).

> **Kurz** — IPTV-Proxy für HLS-Anbieter · eine M3U-URL pro Nutzer · Stream-Limit (HTTP 429) · EPG + Catchup · Watch- & IP-Tracking · integriertes WireGuard-/Mullvad-VPN · Speedtest + Traffic-Analyse · ein Container · SQLite.

### 📑 Inhaltsverzeichnis

[Funktionen](#de-funktionen) · [Architektur](#de-architektur) · [Benutzer](#de-benutzer) · [Eigene Gruppen](#de-gruppen) · [Subdomain](#de-subdomain) · [VPN](#de-vpn) · [Speedtest](#de-speedtest) · [Traffic-Analyse](#de-traffic) · [Stream-Schutz](#de-stream-schutz) · [Schnellstart](#de-schnellstart) · [Unraid](#de-unraid) · [Konfiguration](#de-konfiguration) · [API](#de-api) · [Sicherheit](#de-sicherheit) · [Tech-Stack](#de-tech-stack) · [Entwicklung](#de-entwicklung) · [Roadmap](#de-roadmap)

<a id="de-funktionen"></a>

### ✨ Funktionen

**📺 Kern**
- **Benutzerverwaltung** — jeder Nutzer bekommt eine eigene M3U-URL mit Token
- **Max. Streams pro Nutzer** — einstellbar, weitere Geräte werden mit **HTTP 429** blockiert
- **Catchup / Timeshift** — vergangene Sendungen schauen, funktioniert mit IPTV Pro & TiviMate
- **EPG-Integration** — Programminfo im Dashboard (was läuft gerade, was wurde geschaut)
- **Watch-Tracking** — Kanal, Sendung, Dauer, Zeitpunkt — alles gespeichert
- **IP-Tracking** — IP-Adresse pro Stream-Sitzung und im Watch-Verlauf
- **Admin-Dashboard** — Live-Sitzungen, Live-Catchup, Verlauf, Benutzer, Kanäle, EPG, Einstellungen
- **Eigene Gruppen** — eigene Kanalgruppen anlegen (z. B. Kinder, Sport, Doku) und Nutzern zuweisen
- **Gruppen- & Anbieter-Sortierung** — Drag & Drop für eigene und Anbieter-Gruppen; die Nummerierung erzwingt die Reihenfolge in IPTV Pro (z. B. „01. Kinder“, „02. Sport“)
- **Brute-Force-Schutz** — Admin-Login wird nach 10 Fehlversuchen gesperrt
- **Kurz-URLs** — kurze Playlist-URLs über die eigene Domain (z. B. `https://iptv.deinedomain.de/AbCd1234.m3u`)
- **Kanal-Manager** — Kanäle aktivieren/deaktivieren, sortieren, nach Gruppe filtern
- **EPG-Manager** — mehrere EPG-Quellen, Zeitfilter (1/3/7 Tage), Auto-Refresh, Kanal-Whitelist
- **M3U-Auto-Refresh** — Kanäle nach Zeitplan neu laden, je Anbieter einstellbar
- **M3U-Import** — Import per URL; optional alle bestehenden Nutzer auf einmal umstellen
- **Setup-Assistent** — beim ersten Start, kein manuelles Bearbeiten von Konfigdateien
- **Ein Container** — Python + FastAPI + SQLite, kein Redis, kein Nginx

**🌐 Subdomain / Reverse Proxy**
- **Öffentliche URL** — Subdomain als öffentliche Domain eintragen; alle M3U- und Stream-Links werden damit gebaut
- **`X-Accel-Buffering: no`** — SelfStream sendet den Header, damit Reverse Proxys (Zoraxy, Nginx, Caddy) Segmente ungepuffert durchreichen
- **Durchgehende URL-Kette** — Playlist → Stream-Playlist → Segmente, alles konsequent auf deiner öffentlichen Domain
- **Lokaler Test-Knopf** — der 🏠-Knopf je Nutzer erzeugt eine lokale Test-URL (`?local=1`) mit interner IP, für schnelle Diagnose ohne die öffentliche Einrichtung anzufassen
- **`PROXY_URL`** — öffentliche Proxy-URL per Umgebungsvariable für docker-compose-Setups

**🔒 VPN (integriertes WireGuard / Mullvad)**
- **Integriertes WireGuard** — Tunnel im Admin-Panel starten/stoppen, kein Extra-Container (deutlich schneller und CPU-schonender als OpenVPN)
- **Mullvad-Auto-Import** — eine Mullvad-`.conf` hochladen, alle WireGuard-Server aus Mullvads API ziehen (optional nach Land) und pro Server eine Config bekommen
- **Nahtloser Serverwechsel** — nur der Peer (Server + Endpoint) wird auf dem laufenden Interface getauscht — praktisch keine Unterbrechung, **auch während Zuschauer schauen**
- **Auto-Best (WireGuard, nahtlos)** — reagiert auf echtes Ruckeln (gemessen an Zuschauer-Segmenten) und wechselt auf den schnellsten erreichbaren Server, mit Durchsatz-Schwelle und Cooldown (kein Hin und Her)
- **Schnellsten Server finden (Latenz)** — störungsfreie Rangliste über eine stream-sichere Direktroute (Testpakete gehen nie durch den Tunnel)
- **Live-Status + Log** — Verbindungsstatus, aktuelle öffentliche IP und Echtzeit-Tunnel-Log im Browser
- **Autostart & lokale Route** — der Tunnel verbindet sich nach einem Container-Neustart wieder; das Admin-Panel bleibt bei aktivem VPN schnell (lokales Netz über `eth0`)
- **Voraussetzung:** `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` (oder privilegierter Modus in Unraid)

**📊 Traffic-Analyse**
- **Live-Stream-Monitor** — alle aktiven Streams mit Nutzer, IP, Kanal, Sendung und Dauer
- **Geschätzte Bandbreite** — Mbit/s-Schätzung in Echtzeit aus den aktiven Streams
- **Stream-Verlauf** — Diagramm mit Y-Achse, Spitzen-Markierungen und Zeitachse; Zeitraum 5 Min / 15 Min / 30 Min / 1 h / alles
- **Spitzenwert** — höchste Zahl gleichzeitiger Streams pro Sitzung
- **Buffering-Ereignisse** — automatische Erkennung langsamer (> 2 s, Buffering sehr wahrscheinlich) und verzögerter (> 1 s, Buffering möglich) Segmente, mit Zeitpunkt, Nutzer, Dauer, Segmentgröße, Download-Tempo und Segmentname

**🚀 Speedtest**
- **Doppelter Speedtest** — Internet-/VPN-Tempo und Tempo des IPTV-Anbieters getrennt gemessen
- **Flaschenhals-Erkennung** — zeigt, ob der VPN-Tunnel oder der IPTV-Anbieter bremst
- **Paralleler IPTV-Test** — 5 Segmente von 5 verschiedenen Kanälen gleichzeitig für einen realistischen Lasttest
- **Kapazitäts-Schätzung** — max. gleichzeitige HD-/FHD-/4K-Streams

**⚡ Performance**
- **Segment-Vorpuffern** — jedes TS-Segment wird komplett geladen, bevor es an den Player geht; der Player bekommt es mit LAN-Tempo (~900 Mbit/s) statt Anbieter-Tempo
- **Segment-Prefetch-Cache** — während ein Segment läuft, laden die nächsten 2 schon; Cache-Treffer kommen fast sofort
- **Wiederholung kleiner Segmente** — kaputte Segmente (< 1 KB) werden einmal neu angefragt
- **Geteilter Segment-Cache** — Nutzer auf demselben Kanal teilen sich den Cache; der Anbieter wird pro Segment nur einmal angefragt

**👥 Benutzerverwaltung**
- **Log je Nutzer** — **Log** öffnet den Watch-Verlauf eines Nutzers in einem Fenster
- **Datumsfilter** — Nutzer-Logs nach Zeitraum filtern (von / bis)
- **Seitenweise Anzeige** — 25 / 50 / 100 Einträge pro Seite
- **Nutzer-Logs löschen** — 🗑 im Log-Fenster löscht nur den Verlauf dieses Nutzers
- **Token-Anzeige** — 👁 zeigt den vollständigen Token (umbrechend, gut lesbar)
- **Lokale Test-URL** — 🏠 kopiert eine lokale Playlist-URL für Admin-Tests, ohne Nutzer zu beeinflussen

<a id="de-architektur"></a>

### 🧭 Architektur

```text
   ┌────────────────────────────┐        ┌──────────────────┐
   │ IPTV-Apps                  │        │  Du (Browser)    │
   │ TiviMate · IPTV Pro · VLC  │        │  Admin-Panel     │
   └─────────────┬──────────────┘        └────────┬─────────┘
       M3U · HLS · EPG (Token)             /api · X-Admin-Token
                 │ :8000                          │ :8080
          ┌──────▼────────────────────────────────▼──────┐
          │                SelfStream                    │
          │  Proxy: Playlist-Umschreiben · Stream-Limit  │
          │         Segment-Cache + Prefetch · Catchup   │
          │  Admin: Nutzer · Gruppen · EPG · VPN         │
          │         Traffic                              │
          │  SQLite (/data)                              │
          └──────────────────────┬───────────────────────┘
                                 │ optionaler WireGuard-Tunnel (wg0)
                    ┌────────────▼────────────┐
                    │ IPTV-Anbieter (HLS)     │
                    │ EPG-Quellen (XMLTV)     │
                    └─────────────────────────┘
```

<a id="de-benutzer"></a>

### 👥 Benutzer einrichten

1. Admin-Panel → **Benutzer** → **+ Benutzer hinzufügen**
2. Namen eingeben (z. B. „Kinder-Tablet“, „Wohnzimmer-TV“)
3. Max. Streams einstellen (Standard: 1)
4. Optional eigene Gruppen zuweisen (z. B. Kinder, Sport)
5. Die erzeugten Playlist-URLs weitergeben:

| Knopf | Verwendung |
|---|---|
| 📋 (türkis) | Externe URL über die Subdomain — für Nutzer außerhalb deines Netzes |
| 🏠 (gelb) | Lokale Test-URL — für Admin-Tests im lokalen Netz |

Die externe URL in TiviMate, IPTV Pro, VLC oder einer anderen IPTV-App eintragen.

<a id="de-gruppen"></a>

### 🗂️ Eigene Gruppen

Eigene Kanalgruppen anlegen, unabhängig von den Anbieter-Gruppen:

1. Admin-Panel → **Gruppen** → Gruppennamen eingeben → **+ Neue Gruppe**
2. **✏ Kanäle bearbeiten** → Kanäle aus beliebigen Anbieter-Gruppen auswählen
3. Nutzer zuweisen → **🔒 Gruppen** beim Nutzer → eigene Gruppe anhaken
4. Der Nutzer sieht nur die Kanäle seiner Gruppe — egal, wie der Anbieter sie nennt

**IPTV-Pro-Reihenfolge:** Nummerierung im Gruppen-Tab einschalten, um die Reihenfolge in IPTV Pro zu erzwingen (z. B. „01. Kinder“, „02. Sport“, „03. Doku“).

**Reihenfolge der Anbieter-Gruppen:** im Gruppen-Tab alle Gruppen (eigene und Anbieter) in einer gemeinsamen Drag-&-Drop-Liste sortieren — die gespeicherte Reihenfolge gilt für jede Playlist.

<a id="de-subdomain"></a>

### 🌐 Subdomain einrichten (Reverse Proxy)

Damit Streams auch von außerhalb des Heimnetzes erreichbar sind:

1. Subdomain (z. B. `iptv.deinedomain.de`) auf die öffentliche IP des Servers zeigen lassen
2. Reverse Proxy (Zoraxy, Nginx, Caddy) so einrichten, dass 80/443 → `192.168.1.x:8000` weitergeleitet wird
3. SelfStream-Admin → **Einstellungen** → Subdomain unter **Public Domain / Short URL** eintragen
4. **Speichern** — alle M3U- und Stream-Links werden sofort aktualisiert

> **⚠️ Zoraxy / Nginx:** Proxy-Buffering muss aus sein, damit Streaming funktioniert. SelfStream sendet `X-Accel-Buffering: no` automatisch.

<a id="de-vpn"></a>

### 🔒 VPN einrichten

1. Admin-Panel → **VPN**
2. **Datei wählen** → eine WireGuard-`.conf` hochladen (vom Anbieter; bei Mullvad: WireGuard-Config mit **nur IPv4** herunterladen)
3. **Nur Mullvad:** in der Import-Box ein Land wählen und **Alle importieren** klicken — aus Schlüssel/Adresse deiner `.conf` entsteht pro Mullvad-Server eine Config
4. Bei einem Server **Aktivieren**, dann **▶ VPN starten**
5. Das Live-Log zeigt den Fortschritt; nach dem Verbinden erscheint die öffentliche IP

**Server wechseln:** bei einem Server **Wechseln** (oder **Aktivieren**) klicken — mit WireGuard läuft der Wechsel **nahtlos** auf dem laufenden Tunnel, ohne Neustart und ohne Unterbrechung (auch während Zuschauer schauen).

**Besten Server finden:** **Schnellsten Server finden (Latenz)** für eine stream-sichere Rangliste nutzen, oder **🏆 Auto-Best** einschalten — dann wechselt SelfStream bei Qualitätseinbruch selbst auf den schnellsten Server.

**Getestete Anbieter:** Mullvad (WireGuard). Jede WireGuard-`.conf` sollte funktionieren.

<a id="de-speedtest"></a>

### 📈 Speedtest

Admin-Panel → **VPN** → nach unten zu **Speedtest – Flaschenhals-Analyse** → **▶ Speedtest starten**. Zwei Tests laufen gleichzeitig:

1. **Internet / VPN** — lädt von Cloudflare/OVH, um das reine Tunnel-Tempo zu messen
2. **IPTV-Anbieter** — lädt 5 echte Segmente von 5 Kanälen parallel

Das Flaschenhals-Banner zeigt, welche Seite deine Stream-Kapazität begrenzt.

**Ergebnisse lesen:**
- Anbieter-Tempo weit unter dem Internet-Tempo → der Anbieter ist der Flaschenhals (häufig mit VPN)
- Beide ähnlich → kein Flaschenhals, der VPN-Aufschlag ist minimal
- Die Stream-Schätzung rechnet mit ~4 Mbit/s (HD), ~8 Mbit/s (FHD), ~25 Mbit/s (4K)

<a id="de-traffic"></a>

### 📊 Traffic-Analyse

Admin-Panel → **Traffic**

- **Live-Streams** — alle aktiven Sitzungen mit Nutzer, IP, Kanal, Sendung, Dauer, geschätzter Bandbreite
- **Stream-Verlauf** — Zeitraum 5 Min bis alles; Y-Achse = Zahl der Streams; rote Punkte markieren Spitzenzeiten
- **Buffering-Ereignisse** — automatisches Log langsamer Segment-Downloads; hilft bei Stottern und Einfrieren

**Buffering-Log lesen:**
- \> 2 s Download-Zeit (rot) → der Player hat sehr wahrscheinlich gepuffert
- \> 1 s Download-Zeit (gelb) → der Player hat womöglich kurz pausiert
- Hohes Tempo (> 20 Mbit/s) und trotzdem langsam = große Segmente (bei manchen Anbietern normal)
- Niedriges Tempo (< 4 Mbit/s) = Flaschenhals bei Anbieter/VPN

<a id="de-stream-schutz"></a>

### 🚦 Stream-Schutz

- Stream startet → Sitzung wird in SQLite gespeichert
- Ein zweites Gerät versucht zu streamen → blockiert mit **HTTP 429**
- Die Sitzung endet automatisch, wenn keine Segmente mehr angefragt werden (TTL: 35 Sekunden)
- Rückfall-TTL: 4 Stunden (Datenbank)
- Catchup-Streams zählen **nicht** gegen das Stream-Limit

<a id="de-schnellstart"></a>

### 🚀 Schnellstart (Docker)

```bash
git clone https://github.com/s3lfcod3r/selfstream.git
cd selfstream
cp .env.example .env    # optional — alle Werte dürfen leer bleiben
docker compose up -d
```

`http://<host>:8080/admin` öffnen → der **Setup-Assistent** legt Admin-Token und URLs fest → danach die M3U deines Anbieters hinzufügen.

<details>
<summary><b>Einrichtung — docker run (mit und ohne VPN)</b></summary>

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

`--cap-add=NET_ADMIN` und `--device=/dev/net/tun` sind nur fürs integrierte VPN nötig; ohne VPN kannst du sie weglassen.

**Optional ohne Root (ohne VPN):** `SELFSTREAM_UID` auf die UID des Host-Nutzers setzen, dem das `/data`-Volume gehört. Nur für Setups **ohne** VPN.

```bash
docker run -d \
  -e SELFSTREAM_UID=1000 \
  -p 8000:8000 \
  -p 8080:8080 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/s3lfcod3r/selfstream:latest
```

Die UID muss zum Besitzer von `/data` passen (unter Unraid die UID des Nutzers, der den Container startet, z. B. 1000 oder 101) — sonst kann der Container die Datenbank nicht schreiben und startet nicht.
</details>

<a id="de-unraid"></a>

### 📦 Unraid

**Community Apps** öffnen → nach **selfstream** suchen → installieren (empfohlen). Oder die Vorlage von
`https://raw.githubusercontent.com/s3lfcod3r/selfstream/main/unraid/selfstream.xml`
unter *Docker → Add Container → Template* hinzufügen. Danach `http://<host>:8080/admin` öffnen und dem Setup-Assistenten folgen.

> **⚠️ Rechte:** der Container läuft standardmäßig als **root** — das VPN braucht `--cap-add=NET_ADMIN` und `--device=/dev/net/tun` (in der Vorlage schon gesetzt). Für Setups ohne VPN siehe `SELFSTREAM_UID` unter [Konfiguration](#de-konfiguration).

<a id="de-konfiguration"></a>

### ⚙️ Konfiguration

Umgebungsvariablen (ohne gemeinsames Präfix). Alle sind optional — leere Werte starten beim ersten Start den Setup-Assistenten.

| Variable | Pflicht | Standard | Zweck |
|---|---|---|---|
| `ADMIN_TOKEN` | – | – | Admin-Passwort. Leer → Setup-Assistent beim ersten Start. Wenn gesetzt, lässt sich das Passwort in der Oberfläche **nicht** ändern. |
| `BASE_URL` | – | – | Öffentliche URL des Admin-Panels, z. B. `http://192.168.1.69:8080`. Leer → wird im Setup-Assistenten gesetzt. |
| `PROXY_URL` | – | – | Öffentliche URL des IPTV-Proxys (z. B. `https://iptv.deinedomain.de`). Überschreibt die Proxy-URL aus der Datenbank; alle M3U- und Stream-Links nutzen sie. |
| `DB_PATH` | – | `/data/selfstream.db` | Pfad zur SQLite-Datenbank. Normalerweise nicht ändern. |
| `SELFSTREAM_UID` | – | – | Läuft ohne Root unter dieser UID (nur **ohne** VPN). Muss zum Besitzer von `/data` passen. |

#### Ports

| Port | Verwendung | Wer braucht ihn? |
|---|---|---|
| `8000` | IPTV-Proxy — M3U-Playlists, Streams, EPG | Alle Nutzer, IPTV-Apps |
| `8080` | Admin-Panel | Nur du |

> **💡 Tipp:** Port 8080 muss nicht öffentlich erreichbar sein. Du kannst ihn umlegen, z. B. `8888:8080`.

#### Einstellungen im Admin-Panel

**URLs**

| Einstellung | Standard | Beschreibung |
|---|---|---|
| Admin Panel URL | *(Setup-Assistent)* | Interne URL des Admin-Panels, für interne Links. |
| Proxy URL | *(Setup-Assistent)* | Interne IP:Port des IPTV-Proxys (z. B. `http://192.168.1.69:8000`), vom Server selbst genutzt. |
| Public Domain / Short URL | – | Deine öffentliche Subdomain (z. B. `https://iptv.deinedomain.de`). **Steckt in allen M3U-Stream-Links.** Leer = lokale IP (nur Heimnetz). |

> **⚠️ Reverse Proxy:** nutzt du Zoraxy, Nginx oder Caddy, trag deine Subdomain als **Public Domain** ein — sonst laufen Streams nur im lokalen Netz.

**HLS / Stream**

| Einstellung | Standard | Beschreibung |
|---|---|---|
| `hls_timeout` | `15` | Verbindungs-Timeout in Sekunden (zum Anbieter) |
| `hls_read_timeout` | `60` | Lese-Timeout in Sekunden zwischen Chunks (Catchup / langsame CDNs brauchen oft 45–60 s+) |
| `hls_chunk_size` | `65536` | Chunk-Größe in Bytes beim Streamen von TS-Segmenten (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User-Agent für ausgehende Anfragen an den Anbieter |
| `hls_referer` | – | Referer-Header (falls der Anbieter einen verlangt) |
| `hls_follow_redirects` | `1` | HTTP-Weiterleitungen folgen (`1` = ja, `0` = nein) |
| `prefetch_segments` | `2` | Wie viele Segmente vorab geladen werden (`0` = aus) |
| `diagnostics_enabled` | `1` | Globaler Diagnose-Schalter (`1` = Diagnose-Logs schreiben, `0` = keine neuen Einträge) |

**EPG**

| Einstellung | Standard | Beschreibung |
|---|---|---|
| `epg_refresh_hours` | `6` | Wie oft der EPG-Cache erneuert wird (Stunden) |
| `epg_filter_channels` | `0` | EPG auf die Kanäle aus dem Kanal-Manager filtern |

#### Empfohlene Catchup-Einstellungen (stabile Basis)

Für die meisten Setups (vor allem IPTV Pro / TiviMate) liefert dieses Profil stabiles Catchup mit weniger ungewollten Sprüngen:

```text
catchup_guard_master = 1
catchup_strict_mode = 1
catchup_sticky_recover = 1
catchup_auto_live_on_program_change = 0   # kein Auto-Sprung auf Live am Sendungswechsel
catchup_auto_live_keep_utc = 0            # nur relevant, wenn Auto-Live an ist
catchup_force_same_channel_live = 1
catchup_hard_lock = 0                     # nur einschalten, wenn dein Client ständig auf Live springt
diagnostics_enabled = 0                   # nur zur Fehlersuche auf 1
player_request_debug = 0                  # nur für kurze Diagnose-Sitzungen auf 1
```

> **💡 Tipp:** nach Änderungen an den Catchup-Guards speichern und einen kompletten Catchup-Test bis zur Sendungsgrenze laufen lassen, um das Verhalten bei deinem Anbieter zu prüfen.

Zum Debuggen von Catchup im Browser gibt es ein **eigenes** kleines Image (hls.js + Ereignis-Log): [catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug). Dort deine **öffentlichen M3U- und EPG-URLs** eintragen; die Stream-Zeilen enthalten bereits SelfStream-Pfad und Token (`…/stream?url=…&utc=…`). Es **ersetzt** SelfStream **nicht** — parallel auf einem anderen Port starten.

| | |
|---|---|
| **Repository** | [github.com/kabelsalatundklartext/catchup-hls-debug](https://github.com/kabelsalatundklartext/catchup-hls-debug) |
| **Image** | `ghcr.io/kabelsalatundklartext/catchup-hls-debug:latest` (per GitHub Actions bei Push auf `main`) |
| **Unraid-Vorlagen-URL** | `https://raw.githubusercontent.com/kabelsalatundklartext/catchup-hls-debug/main/unraid/catchup-hls-debug.xml` |

#### Fehlersuche

| Problem | Lösung |
|---|---|
| Setup-Seite erscheint wieder | Browser-Cache leeren (Strg+Umschalt+R) |
| Stream startet nicht | M3U-URL prüfen: Admin → Kanäle → Refresh |
| „Max. Streams erreicht“ | Anderen Stream beenden oder 35 Sekunden warten |
| Admin-Panel nicht erreichbar | Port 8080 in der Firewall freigeben; unter Unraid die Docker-Einstellungen prüfen |
| EPG wird nicht angezeigt | Admin → EPG → „EPG einlesen“, danach Auto-Match |
| Catchup funktioniert nicht | Der Anbieter muss Catchup unterstützen (`tvg-rec` in der M3U) |
| Senderwechsel dauert lange | Connect-Timeout unter Einstellungen → HLS auf 3–5 s senken |
| VPN verbindet nicht | Anderen Server probieren (Aktivieren + Starten); sicherstellen, dass die Mullvad-`.conf` als **nur IPv4** geladen wurde |
| VPN aktiv, aber Streams kaputt | Prüfen, ob privilegierter Modus oder `--cap-add=NET_ADMIN` + `--device=/dev/net/tun` gesetzt ist |
| Buffering mit VPN | **Schnellsten Server finden (Latenz)** und nahtlos wechseln, oder **🏆 Auto-Best** einschalten |
| Stream stottert ohne VPN | Buffering-Ereignisse im Traffic-Tab prüfen; große Segmente (> 5 MB) sind bei manchen Anbietern normal |
| Externe Streams gehen nicht | Subdomain unter Einstellungen → Public Domain eintragen; sonst enthalten Stream-Links deine lokale IP |
| Lokal geht es, extern nicht | Prüfen, ob der Reverse Proxy auf Port 8000 weiterleitet (nicht 8080) |
| M3U-Import aktualisiert Kanäle, Nutzer haben aber noch die alte URL | Im Import-Dialog „Alle bestehenden User auf neue URL umstellen“ anhaken |

<a id="de-api"></a>

### 🔌 API-Übersicht

Admin-API auf Port 8080 unter `/api`, Anmeldung per Header `X-Admin-Token`. Interaktive Doku: `http://<host>:8080/docs`.

| Bereich | Endpunkte (Auszug) |
|---|---|
| **Einrichtung** | `setup`, `setup/status`, `settings`, `settings/change-password` |
| **Nutzer & Gruppen** | `users`, `users/{user_id}/logs`, `users/{user_id}/regenerate-token`, `user-groups` |
| **Kanäle & Anbieter** | `channels`, `channels/import`, `channels/refresh`, `providers`, `providers/{provider_id}/refresh` |
| **EPG** | `epg`, `epg/refresh`, `epg/quality`, `epg/archive`, `epg/archive/browse`, `epg/channels/orphans` |
| **VPN** | `vpn/upload`, `vpn/start`, `vpn/stop`, `vpn/switch`, `vpn/mullvad-import`, `vpn/wg-autobest`, `vpn/server-latency`, `vpn/canary` |
| **Diagnose** | `stats`, `memstats`, `segment-events`, `alerts`, `alerts/test`, `diagnostic-logs`, `vpn/speedtest`, `iptv/capacity` |

**Proxy (Port 8000)** — für die Player:

| URL | Beschreibung |
|---|---|
| `/iptv/{token}/playlist.m3u` | M3U-Playlist für den Nutzer |
| `/iptv/{token}/playlist.m3u?local=1` | Lokale Test-Playlist (interne IP in allen Links) |
| `/iptv/{token}/playlist.m3u8` | M3U8-Playlist (Alternative) |
| `/iptv/{token}/epg.xml` | EPG für den Nutzer |
| `/{short_token}.m3u` | Kompakte Kurz-URL der Playlist |
| `/s/{short_token}/playlist.m3u` | Kurz-URL der Playlist |
| `/iptv/epg.xml` | Globale EPG-URL (für alle gleich) |
| `/iptv/epg-1d.xml` | EPG gefiltert — 1 Tag zurück **und** 1 Tag voraus |
| `/iptv/epg-3d.xml` | EPG gefiltert — 3 Tage zurück **und** 3 Tage voraus |
| `/iptv/epg-7d.xml` | EPG gefiltert — 7 Tage zurück **und** 7 Tage voraus |

<a id="de-sicherheit"></a>

### 🛡️ Sicherheit

- Admin-Token als **PBKDF2-HMAC-SHA256** gespeichert (600k Runden); Login-Sperre nach **10 Fehlversuchen**
- Falsche Token am Proxy werden pro IP gezählt — nach 30 in 5 Minuten antwortet der Proxy mit **429** und `Retry-After`
- **SSRF-Schutz** am öffentlichen Proxy: nur `http`/`https`, interne/private Ziele blockiert — **auch bei Weiterleitungen**
- **Keine Zugangsdaten im Log:** Nutzer-Token, Kurzlinks und Anbieter-Zugangsdaten werden im Zugriffslog maskiert
- CORS am Admin-Panel auf lokale/LAN-Herkünfte begrenzt; Sicherheits-Header inkl. HSTS und `Permissions-Policy`
- OpenVPN-Configs (Altbestand) werden von Script-Direktiven befreit und laufen mit `--script-security 0`; Uploads sind größenbegrenzt, Namen und Endpunkte werden streng geprüft
- **Bewusste Kompromisse** (dokumentiert in [SECURITY.md](SECURITY.md)): der Container läuft als **root** mit `CAP_NET_ADMIN` + `/dev/net/tun` fürs VPN, das Root-Dateisystem ist beschreibbar; bei der Einrichtung über reines HTTP im LAN geht das neue Admin-Token unverschlüsselt übers Netz; das Admin-Panel (Port 8080) ist für ein vertrauenswürdiges LAN gedacht und sollte **nicht** aus dem Internet erreichbar sein
- Sicherheitslücken bitte vertraulich melden — siehe [SECURITY.md](SECURITY.md)

Verlauf der Sicherheitsupdates → [CHANGELOG.md](CHANGELOG.md) (Einträge mit 🔒).

<a id="de-tech-stack"></a>

### 🧱 Tech-Stack

| Teil | Technik |
|---|---|
| Backend | Python 3.12 · FastAPI · uvicorn · httpx · Pillow |
| Datenbank | SQLite (kein externer Server) |
| Web | Vanilla HTML · CSS · JS (kein Framework) |
| VPN | WireGuard (wireguard-tools im Container) · OpenVPN (Altbestand als Rückfall) |
| Deploy | Docker (`python:3.12-slim`, ~200 MB) · GHCR (amd64 + arm64) · Unraid |
| Lizenz | Alle Rechte vorbehalten — nur private, nicht-kommerzielle Nutzung; kein Kopieren, Verändern, Weitergeben oder Verkaufen ([LICENSE](LICENSE)) |

<a id="de-entwicklung"></a>

### 🛠️ Entwicklung

```bash
pip install -r backend/requirements.txt -r requirements-dev.txt
cd backend && DB_PATH=./selfstream.db python server.py   # Proxy :8000, Admin :8080
```

**Tests:**

```bash
pytest -v
flake8 backend/ tests/ --max-line-length=120 --extend-ignore=E501,W503,F401   # in der CI nur als Bericht
black --check --diff backend/ tests/                                          # in der CI nur als Bericht
```

`setup.sh` legt `/mnt/user/appdata/selfstream` mit einer `.env` an und startet den Stack; `update.sh` spielt `backend/` und `frontend/` von `main` live in einen laufenden Container ein (nur für Hotfixes).

<a id="de-roadmap"></a>

### 🗺️ Roadmap

- [x] Nutzer mit eigener M3U-URL · Stream-Limit · Watch- & IP-Tracking · eigene Gruppen
- [x] Stabile Kanal-IDs — Anbieter-Serverwechsel ohne Playlist-Neuladen
- [x] Integriertes WireGuard + Mullvad-Auto-Import · nahtloser Serverwechsel · Auto-Best
- [x] Speedtest mit Flaschenhals-Analyse · Kapazitätstest · Canary-Selbst-Zuschauer · E-Mail-Alarm
- [x] Mehrere EPG-Quellen · eigenes EPG-Archiv · Bereinigung vermischter Programmlisten
- [x] Sicherheits-Härtung (SSRF, PBKDF2, CORS, keine Zugangsdaten im Log)
- [ ] Root ablegen: zuerst `--read-only` + `--tmpfs /tmp`, danach `USER` mit Capabilities auf den VPN-Programmen
- [ ] `VACUUM` für die SQLite-Datei in einem Wartungsfenster
- [ ] `main.py` in Routen-Module aufteilen

<p align="right"><a href="#-deutsch">⬆ nach oben</a></p>

---

## ⚖️ Lizenz / License

**🇩🇪 Alle Rechte vorbehalten.** © 2026 s3lfcod3r / SelfCoder

Du darfst die Software **privat und nicht-kommerziell** installieren und benutzen (z. B. im Homelab, über Docker oder Unraid).

**Ohne schriftliche Erlaubnis verboten:** kommerzielle Nutzung · Kopieren · Verändern · Weitergeben · Einbauen in eigene Projekte (auch Closed Source) · Verkaufen.

Details: [LICENSE](LICENSE)

**🇬🇧 All rights reserved.** © 2026 s3lfcod3r / SelfCoder

You may install and use the software **privately and non-commercially** (e.g. in your home lab, via Docker or Unraid).

**Not permitted without written permission:** commercial use · copying · modifying · redistributing · incorporating into other projects (including closed source) · selling.

Details: [LICENSE](LICENSE)

---

<div align="center">

**SelfStream** · part of the Self family · Teil der Self-Familie<br>
made with 📺 for self-hosting

</div>
