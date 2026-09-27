#!/bin/bash
# selfstream – Direktes Update-Script
# Verwendung: bash update.sh
# Holt die neuesten Backend-Dateien direkt von GitHub und spielt sie in den Container ein
#
# HINWEIS: Dieses Live-Patching ist für schnelle Hotfixes gedacht. Die Dateien
# gehen bei einem 'docker pull'/Recreate wieder verloren. Für dauerhafte Updates
# das offizielle Image-Tag verwenden.

set -euo pipefail

REPO="s3lfcod3r/selfstream"
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

# WICHTIG: Hier muss JEDE Python-Datei aus backend/ stehen. Fehlt eine, entsteht ein
# stiller Mischstand (neues main.py, altes security_util.py), der erst spaeter auffaellt.
# Bis v1.82 fehlten epg_merge, epg_quality, security_util, hls und timeparse.
FILES=(
    "backend/main.py"
    "backend/database.py"
    "backend/m3u_parser.py"
    "backend/server.py"
    "backend/epg_merge.py"
    "backend/epg_quality.py"
    "backend/security_util.py"
    "backend/hls.py"
    "backend/timeparse.py"
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
        
        if docker cp "$DEST" "${CONTAINER}:${CONTAINER_PATH}"; then
            echo "   ✅ ${FILE##*/}"
            UPDATED=$((UPDATED + 1))
        else
            echo "   ⚠️  ${FILE##*/} – docker cp fehlgeschlagen"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "   ⚠️  ${FILE##*/} – nicht gefunden (übersprungen)"
        ERRORS=$((ERRORS + 1))
    fi
done

# requirements.txt wird NICHT eingespielt: ein 'docker cp' installiert nichts.
# Stattdessen vergleichen und warnen, wenn sich die Abhaengigkeiten geaendert haben —
# dann hilft nur ein echtes Image-Update (docker pull + recreate).
if curl -sf -o "${TMP}/requirements.txt" "${BASE_URL}/backend/requirements.txt"; then
    if docker exec "$CONTAINER" cat /app/requirements.txt > "${TMP}/requirements.container" 2>/dev/null; then
        if ! diff -q "${TMP}/requirements.txt" "${TMP}/requirements.container" > /dev/null; then
            echo ""
            echo "⚠️  requirements.txt hat sich geaendert – Live-Patch reicht NICHT."
            echo "   Bitte ein echtes Image-Update fahren (docker pull + Container neu anlegen)."
        fi
    fi
fi

rm -rf "$TMP"

echo ""
if [ $UPDATED -gt 0 ]; then
    echo "🔄 $UPDATED Datei(en) aktualisiert – starte Container neu..."
    docker restart "$CONTAINER"
    echo ""
    # Versionszeile aus dem Container lesen: so faellt ein Mischstand sofort auf.
    VERSION=$(docker exec "$CONTAINER" sh -c "grep -o 'selfstream v[0-9.]*' /app/frontend/index.html | head -1" 2>/dev/null || true)
    if [ -n "$VERSION" ]; then
        echo "   Version im Container: ${VERSION}"
    else
        echo "   ⚠️  Versionszeile im Container nicht gefunden – bitte Logs pruefen."
    fi
    echo ""
    echo "✅ selfstream wurde aktualisiert!"
    echo "   Logs: docker logs ${CONTAINER} --tail 20"
else
    echo "⚠️  Keine Dateien aktualisiert."
fi
echo ""
