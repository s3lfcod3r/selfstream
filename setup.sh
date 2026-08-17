#!/bin/bash
# selfstream – Unraid Setup Script
# Ausführen mit: bash setup.sh

set -euo pipefail

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        selfstream · Setup            ║"
echo "╚══════════════════════════════════════╝"
echo ""

# 1. Pfad
INSTALL_DIR="/mnt/user/appdata/selfstream"
echo "📁 Installationspfad: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data"

# 2. .env anlegen falls nicht vorhanden
if [ ! -f "$INSTALL_DIR/.env" ]; then
  echo ""
  echo "⚙️  .env Datei wird angelegt..."

  # -s: Passwort verdeckt einlesen (nicht im Terminal/Scrollback/Session-Recording sichtbar)
  read -s -p "   Admin Token (Passwort für Admin Panel): " ADMIN_TOKEN
  echo ""
  read -p "   Deine Unraid IP (z.B. 192.168.1.100):  " UNRAID_IP

  cat > "$INSTALL_DIR/.env" << EOF
ADMIN_TOKEN=$ADMIN_TOKEN
BASE_URL=http://$UNRAID_IP:8000
EOF
  chmod 600 "$INSTALL_DIR/.env"   # enthält das Admin-Token → nur für den Besitzer lesbar
  echo "   ✅ .env gespeichert (Rechte 600)"
else
  echo "   ℹ️  .env existiert bereits – wird nicht überschrieben"
fi

# 3. Dateien kopieren falls im selben Verzeichnis
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
  echo ""
  echo "📋 Dateien werden kopiert..."
  cp -r "$SCRIPT_DIR/backend" "$INSTALL_DIR/"
  cp -r "$SCRIPT_DIR/frontend" "$INSTALL_DIR/"
  cp "$SCRIPT_DIR/docker-compose.yml" "$INSTALL_DIR/"
  echo "   ✅ Dateien kopiert"
fi

# 4. Docker Compose starten
echo ""
echo "🐳 Docker Container wird geladen und gestartet..."
cd "$INSTALL_DIR"
# Image-basiertes Compose (kein lokaler Build-Kontext) -> Image ziehen und starten
docker-compose pull
docker-compose up -d

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  selfstream läuft!                               ║"
echo "║                                                      ║"

UNRAID_IP_DISPLAY=$(grep BASE_URL "$INSTALL_DIR/.env" | cut -d'/' -f3 | cut -d':' -f1)
echo "║  Admin Panel:  http://$UNRAID_IP_DISPLAY:8080/admin        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
