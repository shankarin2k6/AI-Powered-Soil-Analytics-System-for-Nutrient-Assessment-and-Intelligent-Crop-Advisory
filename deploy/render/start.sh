#!/bin/sh
# Starts the API, the web app and the front door in one container. If any of them stops, the container stops
# (the host then restarts it), so a crash is never silent.
set -e
cd /app/backend
alembic upgrade head

uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips='*' --workers 1 &
API=$!
(cd /app/web && PORT=3000 HOSTNAME=127.0.0.1 NODE_OPTIONS=--max-old-space-size=96 exec node server.js) &
WEB=$!
caddy run --config /app/Caddyfile --adapter caddyfile &
FRONT=$!

# wait until one of the three exits, then stop the others
while kill -0 $API 2>/dev/null && kill -0 $WEB 2>/dev/null && kill -0 $FRONT 2>/dev/null; do sleep 2; done
echo "a process stopped, shutting down" >&2
kill $API $WEB $FRONT 2>/dev/null || true
exit 1
