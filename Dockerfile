FROM python:3.12-slim

LABEL org.opencontainers.image.title="selfstream"
LABEL org.opencontainers.image.description="Self-hosted IPTV proxy with user management, stream protection and EPG support"
LABEL org.opencontainers.image.source="https://github.com/kabelsalatundklartext/selfstream"
LABEL org.opencontainers.image.licenses="GPL-3.0"

WORKDIR /app

# Install OpenVPN + microsocks (SOCKS5 proxy for split-tunnel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openvpn \
    iproute2 \
    git \
    build-essential \
    && git clone https://github.com/rofl0r/microsocks.git /tmp/microsocks \
    && make -C /tmp/microsocks \
    && cp /tmp/microsocks/microsocks /usr/local/bin/ \
    && rm -rf /tmp/microsocks \
    && apt-get remove -y git build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY frontend/ ./frontend/

EXPOSE 8000 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["python", "server.py"]
