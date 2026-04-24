#!/bin/bash
# selfstream – Direktes Update-Script
# Verwendung: bash update.sh
# Holt die neuesten Backend-Dateien direkt von GitHub und spielt sie in den Container ein

REPO="kabelsalatundklartext/selfstream"
BRANCH="main"
CONTAINER="selfstream"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     selfstream · Live Update         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Prüfen ob Container läuft
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "❌ Container '${CONTAINER}' läuft nicht!"
    exit 1
fi

echo "📥 Lade aktuelle Dateien von GitHub..."

FILES=(
    "backend/main.py"
    "backend/database.py"
    "backend/m3u_parser.py"
    "backend/server.py"
    "frontend/index.html"
    "frontend/setup.html"
)

TMP=$(mktemp -d)
UPDATED=0
ERRORS=0

for FILE in "${FILES[@]}"; do
    URL="${BASE_URL}/${FILE}"
    DEST="${TMP}/${FILE##*/}"
    
    if curl -sf -o "$DEST" "$URL"; then
        # Zieldatei im Container bestimmen
        if [[ "$FILE" == frontend/* ]]; then
            CONTAINER_PATH="/app/frontend/${FILE##*/}"
        else
            CONTAINER_PATH="/app/${FILE##*/}"
        fi
        
        docker cp "$DEST" "${CONTAINER}:${CONTAINER_PATH}" 2>/dev/null
        echo "   ✅ ${FILE##*/}"
        UPDATED=$((UPDATED + 1))
    else
        echo "   ⚠️  ${FILE##*/} – nicht gefunden (übersprungen)"
        ERRORS=$((ERRORS + 1))
    fi
done

rm -rf "$TMP"

echo ""
if [ $UPDATED -gt 0 ]; then
    echo "🔄 $UPDATED Datei(en) aktualisiert – starte Container neu..."
    docker restart "$CONTAINER"
    echo ""
    echo "✅ selfstream wurde aktualisiert!"
    echo "   Logs: docker logs ${CONTAINER} --tail 20"
else
    echo "⚠️  Keine Dateien aktualisiert."
fi
echo ""
