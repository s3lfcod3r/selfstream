FROM python:3.12-slim

LABEL org.opencontainers.image.title="selfstream"
LABEL org.opencontainers.image.description="Self-hosted IPTV proxy with user management, stream protection and EPG support"
LABEL org.opencontainers.image.source="https://github.com/s3lfcod3r/selfstream"
LABEL org.opencontainers.image.licenses="GPL-3.0"

WORKDIR /app

# Install WireGuard (aktiv) + OpenVPN (Legacy-Fallback, gehärtet: script-security 0).
# microsocks/iptables/git/build-essential entfernt — waren ungenutzt (kleinere Angriffsfläche,
# kein ungepinnter git-clone-Build im Image).
RUN apt-get update && apt-get install -y --no-install-recommends \
    openvpn \
    wireguard-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY frontend/ ./frontend/

EXPOSE 8000 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["python", "server.py"]
