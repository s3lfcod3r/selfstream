# IPTV Proxy – Unraid Docker Setup

Ein selbst gehosteter IPTV-Proxy mit User-Management, Concurrent-Stream-Schutz und Watch-Tracking.

## Features

- ✅ Eigene M3U-URL pro Familienmitglied
- ✅ Max. 1 gleichzeitiger Stream pro User
- ✅ Watch-Tracking: Kanal, Dauer, Zeitpunkt
- ✅ Admin Dashboard im Browser
- ✅ User sperren/entsperren
- ✅ Funktioniert mit jeder IPTV-App (TiviMate, VLC, Kodi, etc.)

---

## Setup auf Unraid

### 1. Repository klonen

```bash
# Im Unraid Terminal (SSH)
cd /mnt/user/appdata
git clone https://github.com/DEIN-NAME/iptv-proxy.git
cd iptv-proxy
```

### 2. `.env` Datei anlegen

```bash
cp .env.example .env
nano .env
```

Werte anpassen:

```env
ADMIN_TOKEN=dein-sicheres-passwort
BASE_URL=http://192.168.1.100:8000
```

### 3. Starten

```bash
docker compose up -d
```

### 4. Admin Panel öffnen

```
http://DEINE-UNRAID-IP:8000/admin
```

> **Hinweis:** Die `.env` Datei ist in `.gitignore` – sie wird nie auf GitHub hochgeladen. Nur `.env.example` ist im Repo.

---

## Erstmals auf GitHub pushen

```bash
cd /pfad/zum/projekt

git init
git add .
git commit -m "Initial commit"

# GitHub Repo anlegen (github.com → New Repository → Name: iptv-proxy)
git remote add origin https://github.com/DEIN-NAME/iptv-proxy.git
git branch -M main
git push -u origin main
```

### Nach Updates vom Server ziehen

```bash
cd /mnt/user/appdata/iptv-proxy
git pull
docker compose up -d --build
```

---

## Benutzer anlegen

1. Admin Panel öffnen
2. **"Benutzer hinzufügen"** klicken
3. Name eingeben (z.B. "Mama")
4. Die M3U-URL deines Anbieters eingeben
5. Auf **"Erstellen"** klicken
6. Die generierte Playlist-URL an den Nutzer schicken:
   ```
   http://DEINE-IP:8000/iptv/abc123xyz/playlist.m3u
   ```

### In IPTV-App einrichten (z.B. TiviMate)

- Playlist-Typ: **M3U URL**
- URL: Die generierte URL aus dem Admin Panel

---

## Verzeichnisstruktur

```
iptv-proxy/
├── backend/
│   ├── main.py          # FastAPI App + Proxy-Logik
│   ├── database.py      # SQLite Datenbankschicht
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html       # Admin Dashboard
├── data/                # SQLite DB (auto-erstellt, in .gitignore)
├── .env                 # Secrets (in .gitignore, NICHT auf GitHub!)
├── .env.example         # Vorlage für .env (auf GitHub)
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Troubleshooting

| Problem | Lösung |
|--------|--------|
| Stream startet nicht | Prüfe ob die Quell-M3U-URL erreichbar ist |
| "Already active" Fehler | `docker exec selfstream-redis redis-cli del stream:TOKEN` |
| Admin Panel leer | Browser-Konsole prüfen, ADMIN_TOKEN korrekt? |
| Langsamer Stream | Proxy streamt direkt durch – Netzwerk/Anbieter prüfen |
| Nach `git pull` keine Änderung | `docker compose up -d --build` verwenden |
