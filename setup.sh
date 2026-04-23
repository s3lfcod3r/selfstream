#!/bin/bash
# selfstream – Unraid Setup Script
# Ausführen mit: bash setup.sh

set -e

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

  read -p "   Admin Token (Passwort für Admin Panel): " ADMIN_TOKEN
  read -p "   Deine Unraid IP (z.B. 192.168.1.100):  " UNRAID_IP

  cat > "$INSTALL_DIR/.env" << EOF
ADMIN_TOKEN=$ADMIN_TOKEN
BASE_URL=http://$UNRAID_IP:8000
EOF
  echo "   ✅ .env gespeichert"
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
echo "🐳 Docker Container werden gebaut und gestartet..."
cd "$INSTALL_DIR"
docker compose up -d --build

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  selfstream läuft!                               ║"
echo "║                                                      ║"

UNRAID_IP_DISPLAY=$(grep BASE_URL "$INSTALL_DIR/.env" | cut -d'/' -f3 | cut -d':' -f1)
echo "║  Admin Panel:  http://$UNRAID_IP_DISPLAY:8000/admin        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
