# selfstream

<p align="center">
  <img src="https://raw.githubusercontent.com/kabelsalatundklartext/selfstream/refs/heads/main/frontend/logo.png" width="120" alt="selfstream logo">
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

selfstream is a self-hosted IPTV proxy with user management, stream protection, EPG integration and watch tracking — running as a single Docker container. No Redis, no external database needed.

## Features

- **User Management** – Every user gets their own M3U URL with token
- **Max. Streams per User** – Configurable, blocks additional devices with HTTP 429
- **Catchup / Timeshift** – Watch past content, works with IPTV Pro & TiviMate
- **EPG Integration** – Program info shown in dashboard (what's on now, what was watched)
- **Watch Tracking** – Channel, show title, duration, timestamp — all stored
- **Admin Dashboard** – Live Sessions, Live Catchup, History, Users, Channels, EPG, Settings
- **Custom Groups** – Create your own channel groups (e.g. Kids, Sports, Docs) and assign users
- **Custom Groups** – Create your own channel groups (e.g. Kids, Sports, Docs) and assign users
- **Group & Provider Sorting** – Drag & drop to sort both custom and provider groups; numbering forces order in IPTV Pro
- **Brute-Force Protection** – Admin login locked after 10 failed attempts
- **Short URLs** – Short playlist URLs via custom domain
- **Channel Manager** – Enable/disable, sort, filter channels by group
- **EPG Manager** – Multiple EPG sources, time filter (1/3/7 days), auto-refresh
- **M3U Auto-Refresh** – Automatically reload channels on schedule
- **Custom Logo** – Upload your own logo via admin panel
- **Setup Wizard** – On first start, no manual config editing needed
- **Single Container** – Python + FastAPI + SQLite, no Redis, no Nginx needed

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
  -p 8000:8000 \
  -p 8080:8080 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/kabelsalatundklartext/selfstream:latest
```

Then open `http://YOUR-IP:8080/admin` and follow the Setup Wizard.

### Option 3 – docker-compose

```bash
git clone https://github.com/kabelsalatundklartext/selfstream.git
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
| `DB_PATH` | `/data/selfstream.db` | Path to SQLite database. Usually no need to change. |

---

## Admin Panel Settings

### Base

| Setting | Default | Description |
|---------|---------|-------------|
| Base URL | *(Setup Wizard)* | URL of the admin panel. Used for internal links. |
| Proxy URL | *(Setup Wizard)* | URL of the IPTV proxy. Embedded in M3U URLs. |
| Short Domain | *(empty)* | Custom domain for short playlist URLs |
| M3U Source URL | *(empty)* | URL of your IPTV provider's master M3U playlist |
| M3U Auto-Refresh | Disabled | Automatically reload channels every X hours |

### HLS / Stream

| Setting | Default | Description |
|---------|---------|-------------|
| `hls_timeout` | `5` | Connection timeout in seconds |
| `hls_read_timeout` | `15` | Read timeout in seconds for active streams |
| `hls_chunk_size` | `65536` | Chunk size in bytes for TS segment streaming (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User-Agent for outgoing requests to IPTV provider |
| `hls_referer` | *(empty)* | Referer header (if required by provider) |
| `hls_follow_redirects` | `1` | Follow HTTP redirects (`1` = yes, `0` = no) |

### EPG

| Setting | Default | Description |
|---------|---------|-------------|
| `epg_refresh_hours` | `6` | How often the EPG cache is renewed (in hours) |
| `epg_filter_channels` | `0` | Filter EPG to channels in Channel Manager only |

---

## Setting Up Users

1. Open Admin Panel → **Users** → **+ Add User**
2. Enter name (e.g. "Kids Tablet", "Living Room TV")
3. Set max streams (default: 1)
4. Optionally assign custom groups (e.g. Kids, Sports)
5. Share the generated playlist URL:

```
http://YOUR-IP:8000/iptv/TOKEN/playlist.m3u
```

Enter this URL in TiviMate, IPTV Pro, VLC or any other IPTV app.

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
| `/iptv/{token}/playlist.m3u8` | M3U8 playlist (alternative) |
| `/iptv/{token}/epg.xml` | EPG for user |
| `/s/{short_token}/playlist.m3u` | Short playlist URL |
| `/iptv/epg.xml` | Global EPG URL (same for all users) |
| `/iptv/epg-1d.xml` | EPG filtered – 1 day |
| `/iptv/epg-3d.xml` | EPG filtered – 3 days |
| `/iptv/epg-7d.xml` | EPG filtered – 7 days |

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

---

## Technology

- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow
- **Database:** SQLite (no external server needed)
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Container:** Python 3.12 slim, ~150 MB image

---

## License

**GNU General Public License v3.0 (GPL-3.0)**

|  |  |
|--|--|
| ✅ Private & homelab use | ✅ Modify & adapt |
| ✅ Share & distribute | ✅ Publish your own versions |
| ✅ Commercial use allowed | ❌ Closed-source forks forbidden |
| ✅ Forks must stay GPL-3.0 | ✅ Source code must always be open |

> *"selfstream" by kabelsalatundklartext — [GitHub](https://github.com/kabelsalatundklartext/selfstream)*

---
---

<a name="deutsch"></a>

# 🇩🇪 Deutsch

## Was ist selfstream?

selfstream ist ein selbst gehosteter IPTV-Proxy mit User-Management, Stream-Schutz, EPG-Integration und Watch-Tracking — als einzelner Docker-Container. Kein Redis, keine externe Datenbank nötig.

## Features

- **User-Management** – Jeder User bekommt eine eigene M3U-URL mit Token
- **Max. Streams pro User** – Konfigurierbar, blockiert zusätzliche Geräte mit HTTP 429
- **Catchup / Timeshift** – Vergangene Sendungen schauen, funktioniert mit IPTV Pro & TiviMate
- **EPG-Integration** – Programm-Info wird im Dashboard angezeigt (was läuft gerade, was wurde geschaut)
- **Watch-Tracking** – Kanal, Sendung, Dauer, Zeitpunkt – alles gespeichert
- **Admin-Dashboard** – Live Sessions, Live Catchup, Verlauf, Benutzer, Kanäle, EPG, Einstellungen
- **Eigene Gruppen** – Eigene Kanalgruppen erstellen (z.B. Kinder, Sport, Doku) und Usern zuweisen
- **Eigene Gruppen** – Eigene Kanalgruppen erstellen (z.B. Kinder, Sport, Doku) und Usern zuweisen
- **Gruppen- & Anbieter-Sortierung** – Drag & Drop zum Sortieren aller Gruppen; Nummerierung erzwingt Reihenfolge in IPTV Pro
- **Brute-Force-Schutz** – Admin-Login wird nach 10 Fehlversuchen gesperrt
- **Short URLs** – Kurze Playlist-URLs über eigene Domain
- **Kanal-Manager** – Kanäle aktivieren/deaktivieren, sortieren, nach Gruppen filtern
- **EPG-Manager** – Mehrere EPG-Quellen, Zeitfilter (1/3/7 Tage), Auto-Refresh
- **M3U Auto-Refresh** – Kanäle automatisch nach Zeitplan neu laden
- **Custom Logo** – Eigenes Logo im Admin-Panel hochladbar
- **Setup-Wizard** – Beim ersten Start, kein manuelles Config-Editing nötig
- **Single Container** – Python + FastAPI + SQLite, kein Redis, kein Nginx nötig

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
  -p 8000:8000 \
  -p 8080:8080 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/kabelsalatundklartext/selfstream:latest
```

Dann `http://DEINE-IP:8080/admin` öffnen und Setup-Wizard folgen.

### Option 3 – docker-compose

```bash
git clone https://github.com/kabelsalatundklartext/selfstream.git
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
| `DB_PATH` | `/data/selfstream.db` | Pfad zur SQLite-Datenbank. Normalerweise nicht ändern. |

---

## Admin-Panel Einstellungen

### Basis

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| Base URL | *(Setup-Wizard)* | URL des Admin-Panels. Wird für interne Links verwendet. |
| Proxy URL | *(Setup-Wizard)* | URL des IPTV-Proxys. Wird in M3U-URLs eingebettet. |
| Short Domain | *(leer)* | Eigene Domain für kurze Playlist-URLs |
| M3U Quell-URL | *(leer)* | URL der Master-M3U-Playlist deines IPTV-Anbieters |
| M3U Auto-Refresh | Deaktiviert | Kanäle automatisch alle X Stunden neu laden |

### HLS / Stream

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| `hls_timeout` | `5` | Verbindungs-Timeout in Sekunden |
| `hls_read_timeout` | `15` | Lese-Timeout in Sekunden für laufende Streams |
| `hls_chunk_size` | `65536` | Chunk-Größe in Bytes beim Streamen von TS-Segmenten (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User-Agent für ausgehende Requests zum IPTV-Anbieter |
| `hls_referer` | *(leer)* | Referer-Header (falls vom Anbieter benötigt) |
| `hls_follow_redirects` | `1` | HTTP-Redirects folgen (`1` = ja, `0` = nein) |

### EPG

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| `epg_refresh_hours` | `6` | Wie oft der EPG-Cache erneuert wird (in Stunden) |
| `epg_filter_channels` | `0` | EPG auf Kanäle aus dem Kanal-Manager filtern |

---

## Benutzer einrichten

1. Admin Panel öffnen → **Benutzer** → **+ Benutzer hinzufügen**
2. Name eingeben (z.B. "Kinder-Tablet", "Wohnzimmer TV")
3. Max. Streams einstellen (Standard: 1)
4. Optional eigene Gruppen zuweisen (z.B. Kinder, Sport)
5. Generierte Playlist-URL weitergeben:

```
http://DEINE-IP:8000/iptv/TOKEN/playlist.m3u
```

Diese URL in TiviMate, IPTV Pro, VLC oder einer anderen IPTV-App eintragen.

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
| `/iptv/{token}/playlist.m3u8` | M3U8-Playlist (alternativ) |
| `/iptv/{token}/epg.xml` | EPG für den User |
| `/s/{short_token}/playlist.m3u` | Kurze Playlist-URL |
| `/iptv/epg.xml` | Globale EPG-URL (für alle gleich) |
| `/iptv/epg-1d.xml` | EPG gefiltert – 1 Tag |
| `/iptv/epg-3d.xml` | EPG gefiltert – 3 Tage |
| `/iptv/epg-7d.xml` | EPG gefiltert – 7 Tage |

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

---

## Technologie

- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow
- **Datenbank:** SQLite (kein externer Server nötig)
- **Frontend:** Vanilla HTML/CSS/JS (kein Framework)
- **Container:** Python 3.12 slim, ~150 MB Image

---

## Lizenz

**GNU General Public License v3.0 (GPL-3.0)**

|  |  |
|--|--|
| ✅ Privat & Homelab nutzen | ✅ Verändern & anpassen |
| ✅ Weitergeben & teilen | ✅ Eigene Versionen veröffentlichen |
| ✅ Kommerzieller Einsatz erlaubt | ❌ Closed-Source-Abwandlungen verboten |
| ✅ Forks müssen GPL-3.0 bleiben | ✅ Quellcode muss immer offen bleiben |

> *"selfstream" von kabelsalatundklartext — [GitHub](https://github.com/kabelsalatundklartext/selfstream)*
