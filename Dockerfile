FROM python:3.12-slim

LABEL org.opencontainers.image.title="selfstream"
LABEL org.opencontainers.image.description="Self-hosted IPTV proxy with user management, stream protection and EPG support"
LABEL org.opencontainers.image.source="https://github.com/kabelsalatundklartext/selfstream"
LABEL org.opencontainers.image.licenses="GPL-3.0"

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY frontend/ ./frontend/

EXPOSE 8000 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["python", "server.py"]
