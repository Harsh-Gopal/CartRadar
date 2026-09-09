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

echo "==> Checking Node.js version..."
if ! command -v node >/dev/null 2>&1; then
  echo "❌ ERROR: Node.js is not installed."
  echo "Please install Node.js 22 (e.g. 'brew install node@22' or 'nvm install 22')."
  exit 1
fi

NODE_MAJOR=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "❌ ERROR: Node.js v22 or higher is required (current: $(node -v))."
  echo "This is required by pnpm 11+ and for 'node:sqlite' support."
  echo ""
  echo "To upgrade on macOS Apple Silicon:"
  echo "  Using nvm:  nvm install 22 && nvm use 22"
  echo "  Using brew: brew install node@22"
  echo ""
  exit 1
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
