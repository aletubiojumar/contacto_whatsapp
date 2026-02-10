FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV TZ=Europe/Stockholm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        tzdata \
        libnss3 \
        libatk-bridge2.0-0 \
        libxkbcommon0 \
        libgtk-3-0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpangocairo-1.0-0 \
        libpango-1.0-0 \
        libcairo2 \
        libatspi2.0-0 \
        libdrm2 \
        libx11-6 \
        libxext6 \
        libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install chromium

COPY . .

USER root

# crea el usuario si no existe (por si rebuilds)
RUN id -u appuser >/dev/null 2>&1 || useradd -m appuser

# logs -> /tmp (siempre escribible)
RUN rm -rf /app/logs && ln -s /tmp /app/logs

# si necesitas escribir data, da permisos
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data && mkdir -p /app/certs

# --- SSL certs for MySQL ---
COPY certs/ca.pem /app/certs/ca.pem
COPY certs/client-cert.pem /app/certs/client-cert.pem
COPY certs/client-key.pem /app/certs/client-key.pem
RUN chmod 600 /app/certs/client-key.pem \
 && chmod 644 /app/certs/ca.pem /app/certs/client-cert.pem \
 && chown -R appuser:appuser /app/certs

USER appuser

ENTRYPOINT ["bash", "entrypoint.sh"]
