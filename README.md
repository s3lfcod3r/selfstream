# selfstream

<p align="center">
  <img src="https://raw.githubusercontent.com/kabelsalatundklartext/selfstream/main/frontend/logo.png" width="120" alt="selfstream logo">
</p>

<p align="center">
  Selbst gehosteter IPTV-Proxy mit User-Management, Stream-Schutz, EPG-Integration und Watch-Tracking.<br>
  Ein einzelner Docker-Container – kein Redis, keine externe Datenbank.
</p>

---

## Features

- **User-Management** – Jedes User bekommt eine eigene M3U-URL mit Token
- **Max. Streams pro User** – Konfigurierbar, blockiert zusätzliche Geräte mit HTTP 429
- **Catchup / Timeshift** – Vergangene Sendungen schauen, funktioniert mit IPTV Pro & TiviMate
- **EPG-Integration** – Programm-Info wird im Dashboard angezeigt (was läuft gerade, was wurde geschaut)
- **Watch-Tracking** – Kanal, Sendung, Dauer, Zeitpunkt – alles gespeichert
- **Admin-Dashboard** – Live Sessions, Live Catchup, Verlauf, Benutzer, Kanäle, EPG, Einstellungen
- **Short URLs** – Kurze Playlist-URLs über eigene Domain
- **Kanal-Manager** – Kanäle aktivieren/deaktivieren, sortieren, nach Gruppen filtern
- **EPG-Manager** – Mehrere EPG-Quellen, Zeitfilter (1/3/7 Tage), Auto-Refresh
- **Custom Logo** – Eigenes Logo im Admin-Panel hochladbar
- **Setup-Wizard** – Beim ersten Start, kein manuelles Config-Editing nötig
- **Single Container** – Python + FastAPI + SQLite, kein Redis, kein Nginx nötig

---

## Schnellstart

### Option 1 – Unraid Community Apps (empfohlen)

1. Community Apps öffnen → nach **selfstream** suchen
2. Installieren
3. Browser öffnen: `http://DEINE-IP:8000/admin`
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

Diese Variablen können beim Container-Start gesetzt werden:

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `ADMIN_TOKEN` | *(leer)* | Admin-Passwort. Leer lassen → Setup-Wizard beim ersten Start. Wenn gesetzt, kann das Passwort nicht über die UI geändert werden. |
| `BASE_URL` | *(leer)* | Öffentliche URL des Admin-Panels, z.B. `http://192.168.1.69:8080`. Leer lassen → wird im Setup-Wizard gesetzt. |
| `DB_PATH` | `/data/selfstream.db` | Pfad zur SQLite-Datenbank. Normalerweise nicht ändern. |

---

## Admin-Panel Einstellungen

Diese Einstellungen werden in der Datenbank gespeichert und können im Admin-Panel unter **Einstellungen** geändert werden:

### Basis

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| Base URL | *(Setup-Wizard)* | URL des Admin-Panels (z.B. `http://192.168.1.69:8080`). Wird für interne Links verwendet. |
| Proxy URL | *(Setup-Wizard)* | URL des IPTV-Proxys (z.B. `http://192.168.1.69:8000`). Wird in M3U-URLs eingebettet. |
| Short Domain | *(leer)* | Eigene Domain für kurze Playlist-URLs, z.B. `https://meine-domain.de` |
| M3U Quell-URL | *(leer)* | URL der Master-M3U-Playlist deines IPTV-Anbieters |

### HLS / Stream

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| `hls_timeout` | `10` | Verbindungs-Timeout in Sekunden beim Abruf von Playlists/Segmenten |
| `hls_read_timeout` | `30` | Lese-Timeout in Sekunden für laufende Streams |
| `hls_chunk_size` | `65536` | Chunk-Größe in Bytes beim Streamen von TS-Segmenten (64 KB) |
| `hls_user_agent` | `VLC/3.0 LibVLC/3.0` | User-Agent für ausgehende Requests zum IPTV-Anbieter |
| `hls_referer` | *(leer)* | Referer-Header für ausgehende Requests (falls vom Anbieter benötigt) |
| `hls_follow_redirects` | `1` | HTTP-Redirects folgen (`1` = ja, `0` = nein) |

### EPG

| Einstellung | Standard | Beschreibung |
|-------------|---------|-------------|
| `epg_refresh_hours` | `6` | Wie oft der EPG-Cache erneuert wird (in Stunden) |
| `epg_filter_channels` | `0` | EPG auf Kanäle aus dem Kanal-Manager filtern (`1` = ja, `0` = alle) |

---

## Unraid Template Variablen

Beim Installieren über Unraid Community Apps werden folgende Felder angezeigt:

| Feld | Container-Variable | Pflicht | Beschreibung |
|------|-------------------|---------|-------------|
| Daten-Pfad | `/data` | ✅ | Host-Pfad wo Datenbank & Logs gespeichert werden. Standard: `/mnt/user/appdata/selfstream/data` |
| IPTV Proxy Port | `8000/tcp` | ✅ | Host-Port für den IPTV-Proxy. Kommt in die IPTV-App. |
| Admin Panel Port | `8080/tcp` | ✅ | Host-Port für das Admin-Panel. Standard: `8080` |
| Admin Token | `ADMIN_TOKEN` | ❌ | Leer lassen für Setup-Wizard. Oder hier direkt setzen. |
| Base URL | `BASE_URL` | ❌ | Leer lassen für Setup-Wizard. Beispiel: `http://192.168.1.69:8080` |
| DB Pfad | `DB_PATH` | ❌ | Normalerweise nicht ändern. Standard: `/data/selfstream.db` |

---

## Benutzer einrichten

1. Admin Panel öffnen → **Benutzer** → **+ Benutzer hinzufügen**
2. Name eingeben (z.B. "User1", "User2")
3. M3U-URL des IPTV-Anbieters eintragen
4. Max. Streams einstellen (Standard: 1)
5. Generierte Playlist-URL an User weitergeben:

```
http://DEINE-IP:8000/iptv/TOKEN/playlist.m3u
```

Diese URL in TiviMate, IPTV Pro, VLC oder einer anderen IPTV-App eintragen.

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

### Admin (Port 8080)

| URL | Beschreibung |
|-----|-------------|
| `/admin` | Admin-Dashboard |
| `/setup` | Setup-Wizard (nur beim ersten Start) |
| `/api/stats` | Aktive Sessions, Verlauf, Statistiken |
| `/api/users` | User-Management |
| `/api/channels` | Kanal-Liste |
| `/api/epg` | EPG-Quellen |
| `/api/logs` | Watch-Verlauf |
| `/api/settings` | Einstellungen lesen/schreiben |

---

## Stream-Schutz

- Stream startet → Session wird in SQLite gespeichert
- Zweites Gerät versucht zu streamen → blockiert mit **HTTP 429**
- Session endet automatisch wenn keine Segmente mehr angefragt werden (TTL: 35 Sekunden)
- Fallback TTL: 4 Stunden (Datenbank)
- Catchup-Streams zählen **nicht** gegen das Stream-Limit

---

## Catchup / Timeshift

selfstream unterstützt Catchup (vergangene Sendungen schauen) für IPTV-Anbieter die es unterstützen.

- Funktioniert mit **IPTV Pro**, **TiviMate** und anderen Apps die `utc`-Parameter unterstützen
- Catchup-Zugriffe werden im Verlauf mit ⏪ gekennzeichnet
- EPG-Titel der geschauten Sendung wird gespeichert
- Dauer des Catchup-Streams wird getrackt

---

## EPG

1. Admin Panel → **EPG** → **+ Quelle hinzufügen**
2. Name und URL der EPG-Quelle eingeben
3. **EPG einlesen** klicken
4. **Auto-Match** aktivieren um Kanäle automatisch zuzuordnen
5. Globale EPG-URL in der IPTV-App eintragen:

```
http://DEINE-IP:8000/iptv/epg.xml
```

EPG wird automatisch alle 6 Stunden erneuert (konfigurierbar).

---

## Dateistruktur

```
selfstream/
├── backend/
│   ├── main.py          # FastAPI App (Proxy + Admin)
│   ├── database.py      # SQLite Datenbankschicht
│   ├── m3u_parser.py    # M3U Parser und Builder
│   ├── server.py        # Entrypoint (zwei uvicorn Instanzen)
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Admin-Panel (Single Page App)
│   ├── setup.html       # Setup-Wizard
│   ├── logo.png         # selfstream Logo
│   └── favicon.ico      # Browser-Icon
├── Dockerfile
├── docker-compose.yml
├── selfstream.xml       # Unraid Community Apps Template
├── setup.sh
├── update.sh
└── .env.example
```

---

## Datenpersistenz

Alle persistenten Daten liegen unter `/data` im Container:

| Datei | Beschreibung |
|-------|-------------|
| `selfstream.db` | SQLite-Datenbank (User, Sessions, Verlauf, Einstellungen) |
| `epg_cache.xml` | Gecachte EPG-Daten (wird automatisch erneuert) |
| `error-max-streams.jpg` | Fehlerbild bei Max-Streams-Überschreitung |
| `custom_login_logo.png` | Eigenes Logo (optional, via Admin hochgeladen) |

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Setup-Seite erscheint wieder | Browser-Cache leeren (Strg+Shift+R) |
| Stream startet nicht | M3U-URL des Anbieters im Admin prüfen → Kanäle → Refresh |
| „Max. Streams erreicht" | Anderen Stream beenden oder 35 Sekunden warten |
| Admin Panel nicht erreichbar | Port 8080 in Firewall freigeben; bei Unraid: Docker-Einstellungen prüfen |
| EPG wird nicht angezeigt | Admin → EPG → EPG einlesen klicken; danach Auto-Match |
| Catchup funktioniert nicht | IPTV-Anbieter muss Catchup unterstützen (`tvg-rec` in M3U) |
| WebUI Button in Unraid geht auf falschen Port | `selfstream.xml` aktualisieren, Container neu speichern |

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

Bei Weitergabe oder Veröffentlichung: Namensnennung + GPL-3.0-Lizenz beibehalten.

> *"selfstream" von kabelsalatundklartext — [GitHub](https://github.com/kabelsalatundklartext/selfstream)*
