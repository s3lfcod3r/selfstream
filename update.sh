#!/bin/bash
# selfstream – Direktes Update-Script
# Verwendung: bash update.sh
# Holt die neuesten Backend- und Frontend-Dateien direkt von GitHub (main)
# und spielt sie in den Container ein.
#
# HINWEIS: Dieses Live-Patching ist für schnelle Hotfixes gedacht. Die Dateien
# gehen bei einem 'docker pull'/Recreate wieder verloren. Für dauerhafte Updates
# das offizielle Image-Tag verwenden.
#
# Ab v1.84: Statt einer manuell gepflegten Dateienliste wird jetzt der gesamte
# backend/ und frontend/-Ordner aus GitHub geladen (flacher Klon) und
# Datei für Datei eingespielt. Neue Module fallen damit nicht mehr auf.

set -euo pipefail

REPO="s3lfcod3r/selfstream"
BRANCH="main"
CONTAINER="selfstream"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
GITBIN="git"

WORK=$(mktemp -d)
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     selfstream · Live Update                     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Prüfen ob Container läuft
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "❌ Container '${CONTAINER}' läuft nicht!"
    exit 1
fi

echo "📥 Lade aktuellen Stand von GitHub main..."
if ! "$GITBIN" clone --depth 1 --quiet "https://github.com/${REPO}" "${WORK}/src" 2>&1; then
    echo "❌ Klon von GitHub fehlgeschlagen. Bitte Netzwerk/Internet prüfen."
    exit 1
fi
SRC="${WORK}/src"
# Version aus dem Klon bestimmen (für die Versionsanzeige)
GIT_VERSION=$(grep -o 'selfstream v[0-9.]*' "${SRC}/frontend/index.html" | head -1 || true)

TMP="${WORK}/tmp"
mkdir -p "$TMP"
UPDATED=0
ERRORS=0

copy_file() {
    local src="$1" rel="$2"
    if docker cp "$src" "${CONTAINER}:/app/${rel}"; then
        echo "   ✅ ${rel}"
        UPDATED=$((UPDATED + 1))
    else
        echo "   ⚠️  ${rel} – docker cp fehlgeschlagen"
        ERRORS=$((ERRORS + 1))
    fi
}

# Backend: alle .py-Dateien (dynamisch – neue Module fallen nicht auf)
while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel="${f#${SRC}/}"
    copy_file "$f" "$rel"
done < <(find "${SRC}/backend" -name '*.py' -type f | sort)

# Frontend: alle .html-Dateien (dynamisch – neue Seiten fallen nicht auf)
while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel="${f#${SRC}/}"
    copy_file "$f" "$rel"
done < <(find "${SRC}/frontend" -name '*.html' -type f | sort)

# requirements.txt vergleichen (wie bisher): ein 'docker cp' installiert nichts.
if curl -sf -o "${TMP}/requirements.txt" "${BASE_URL}/backend/requirements.txt"; then
    if docker exec "${CONTAINER}" cat /app/requirements.txt > "${TMP}/requirements.container" 2>/dev/null; then
        if ! diff -q "${TMP}/requirements.txt" "${TMP}/requirements.container" > /dev/null; then
            echo ""
            echo "⚠️  requirements.txt hat sich geändert – Live-Patch reicht NICHT."
            echo "   Bitte ein echtes Image-Update fahren (docker pull + Container neu anlegen)."
        fi
    fi
fi

echo ""
if [ $UPDATED -gt 0 ]; then
    echo "🔄 $UPDATED Datei(en) aktualisiert – starte Container neu..."
    docker restart "${CONTAINER}"
    echo ""
    # Versionszeile aus dem Container lesen (Fallback: Version aus dem Klon).
    VERSION=$(docker exec "${CONTAINER}" sh -c "grep -o 'selfstream v[0-9.]*' /app/frontend/index.html | head -1" 2>/dev/null || true)
    if [ -z "$VERSION" ]; then
        VERSION="${GIT_VERSION:-}"
    fi
    if [ -n "$VERSION" ]; then
        echo "   Version: ${VERSION}"
    else
        echo "   ⚠️  Versionszeile im Container nicht gefunden – bitte Logs prüfen."
    fi
    echo ""
    echo "✅ selfstream wurde aktualisiert!"
    echo "   Logs: docker logs ${CONTAINER} --tail 20"
else
    echo "⚠️  Keine Dateien aktualisiert."
fi
echo ""
