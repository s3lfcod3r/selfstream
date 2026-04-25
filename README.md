# selfstream

Selbst gehosteter IPTV-Proxy mit User-Management, Concurrent-Stream-Schutz und Watch-Tracking.

## Features

- ✅ Eigene M3U-URL pro Familienmitglied
- ✅ Max. 1 gleichzeitiger Stream pro User
- ✅ Watch-Tracking: Kanal, Dauer, Zeitpunkt
- ✅ Admin Dashboard im Browser
- ✅ First-Run Setup-Wizard (kein manuelles Config-Editing)
- ✅ Einzelner Docker-Container (kein Redis nötig)
- ✅ Funktioniert mit jeder IPTV-App (TiviMate, VLC, Kodi, etc.)

---

## Installation auf Unraid

### Option 1: Unraid Community Apps (empfohlen)

1. Community Apps öffnen → nach **selfstream** suchen
2. Installieren
3. Browser öffnen: `http://DEINE-IP:8000`
4. Setup-Wizard folgen (Passwort + IP eingeben)
5. Fertig ✓

### Option 2: Manuell via Docker

```bash
docker run -d \
  --name selfstream \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /mnt/user/appdata/selfstream/data:/data \
  ghcr.io/kabelsalatundklartext/selfstream:latest
```

Dann `http://DEINE-IP:8000` öffnen und Setup-Wizard folgen.

### Option 3: docker-compose

```bash
git clone https://github.com/kabelsalatundklartext/selfstream.git
cd selfstream
docker-compose up -d
```

---

## Erster Start

Beim ersten Öffnen von `http://DEINE-IP:8000` erscheint automatisch der Setup-Wizard:

1. **Admin-Passwort** wählen (min. 8 Zeichen)
2. **Server-IP** bestätigen (wird automatisch erkannt)
3. Fertig → Admin Panel öffnet sich

---

## Benutzer anlegen

1. Admin Panel → **Benutzer hinzufügen**
2. Name + M3U-URL des Anbieters eingeben
3. Generierte Playlist-URL an Familienmitglied schicken:
   ```
   http://DEINE-IP:8000/iptv/TOKEN/playlist.m3u
   ```
4. In IPTV-App eintragen (TiviMate, VLC, etc.) – fertig

---

## Wie funktioniert der Stream-Schutz?

- Stream startet → Session wird in SQLite gespeichert
- Zweites Gerät versucht zu streamen → blockiert (HTTP 409)
- Session endet automatisch wenn Stream stoppt
- Fallback TTL: 4 Stunden

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Setup-Seite erscheint wieder | Browser-Cache leeren |
| Stream startet nicht | M3U-URL des Anbieters prüfen |
| "Already active" Fehler | Alten Stream beenden oder 4h warten |
| Admin Panel nicht erreichbar | Port 8000 in Unraid Firewall freigeben |

