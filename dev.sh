#!/usr/bin/env bash
# Run backend (:8400) + frontend (:5173) together. Ctrl+C stops both.
set -e
cd "$(dirname "$0")"

trap 'kill 0' EXIT INT TERM

# Load local secrets from a gitignored .env, if present.
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
  [ -n "$PROXY_URL" ] && echo "==> PROXY_URL set — routing calls through the proxy"
fi

echo "==> Backend deps"
(cd backend && uv sync --quiet)
echo "==> Frontend deps"
(cd frontend && pnpm install --silent)

# DEV_MODE lifts all rate limits / search & probe budgets / radius cap locally.
# ENABLED_PLATFORMS enables all implemented platforms.
(cd backend && DEV_MODE=1 ENABLED_PLATFORMS=zepto,swiggy,bigbasket,blinkit,bbnow uv run python -m uvicorn app.main:app --port 8000 --reload) &

echo "Waiting for backend to start on port 8000..."
while ! nc -z localhost 8000; do   
  sleep 0.5
done

(cd frontend && pnpm dev) &

sleep 2
echo ""
echo "================================================"
echo "  Cart Radar"
echo "  Open:  http://localhost:5173"
echo "  API:   http://localhost:8000/api/stats"
echo "================================================"
echo ""
wait
