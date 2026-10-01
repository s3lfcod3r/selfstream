#!/bin/sh
# selfstream entrypoint
#
# Default: läuft als root (erforderlich für den VPN: NET_ADMIN + /dev/net/tun).
#
# Optional: SELFSTREAM_UID=<uid> setzen, um auf einen Nicht-Root-User zu fallen
# (verringert die Angriffsfläche). Nur für Setups OHNE VPN verwenden.
#
# Der UID muss zum Host-User passen, der das /data-Volume besitzt (Unraid:
# UID des Benutzers, der den Container läuft), sonst kann der Container die
# Datenbank nicht schreiben.
#
# Beispiel: SELFSTREAM_UID=1000 docker run ... selfstream
set -e
if [ -n "$SELFSTREAM_UID" ]; then
    # Kurztest: kann der Ziel-User /data schreiben? (als dieser User prüfen)
    if ! setpriv --reuid "$SELFSTREAM_UID" --regid "$SELFSTREAM_UID" \
        --clear-groups sh -c 'touch /data/.ss_wtest 2>/dev/null && rm -f /data/.ss_wtest'; then
        echo "ERROR: User UID=$SELFSTREAM_UID kann /data nicht schreiben." >&2
        echo "   SELFSTREAM_UID muss zum Host-User passen, der das /data-Volume besitzt." >&2
        echo "   (Unraid: UID des Benutzers, der den Container läuft, z.B. 1000/101)." >&2
        exit 1
    fi
    exec setpriv --reuid "$SELFSTREAM_UID" --regid "$SELFSTREAM_UID" \
        --clear-groups python /app/server.py
else
    exec python /app/server.py
fi
