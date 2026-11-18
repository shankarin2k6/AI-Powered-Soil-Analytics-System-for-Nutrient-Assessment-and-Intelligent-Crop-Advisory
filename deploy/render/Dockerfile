# ONE container with everything (API + web app + front door). Built for free hosts such as Render.
# Build from the project root:   docker build -f deploy/render/Dockerfile -t soil-app .
# The database is outside (Neon); photos can live inside it (STORAGE_BACKEND=db). See DEPLOY_RENDER.md.

# ---- 1. build the web app (same-origin: the browser calls /api on the same address) ----
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL="" NEXT_STANDALONE=1 NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- 2. the runtime image ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
# Node (to run the web app) and Caddy (front door) are copied from their official images
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=caddy:2 /usr/bin/caddy /usr/local/bin/caddy

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/models ./models

WORKDIR /app/web
COPY --from=web /web/.next/standalone ./
COPY --from=web /web/.next/static ./.next/static
COPY --from=web /web/public ./public

COPY deploy/render/Caddyfile /app/Caddyfile
COPY deploy/render/start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh /app/Caddyfile && chmod +x /app/start.sh \
 && useradd --create-home --uid 10001 app && mkdir -p /app/backend/uploads && chown -R app:app /app
USER app
ENV HOME=/home/app XDG_DATA_HOME=/tmp/caddy-data XDG_CONFIG_HOME=/tmp/caddy-config
# the public port comes from the host (Render sets PORT; default 10000)
EXPOSE 10000
CMD ["/app/start.sh"]
