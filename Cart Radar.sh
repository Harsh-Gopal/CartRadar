#!/usr/bin/env bash
# ============================================================
#  Cart Radar — Linux one-click launcher
#  Run this script, or double-click "Cart Radar.desktop".
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_URL="http://localhost:3000"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() { echo -e "\n${CYAN}${BOLD}$1${RESET}"; }
ok()     { echo -e "  ${GREEN}✓${RESET} $1"; }
fail()   { echo -e "\n${RED}✗ ERROR:${RESET} $1\n"; }

clear
echo -e "${BOLD}"
echo "  ╔══════════════════════════════╗"
echo "  ║        🎯  Cart Radar        ║"
echo "  ╚══════════════════════════════╝"
echo -e "${RESET}"

# ── 1. Check Docker ──────────────────────────────────────────
banner "Checking Docker..."

if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    echo "  Install Docker Engine (or Docker Desktop) for Linux:"
    echo "    https://docs.docker.com/engine/install/"
    echo ""
    echo "  After installing, run:  sudo usermod -aG docker \$USER"
    echo "  Then log out and back in, and run this script again."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    fail "Docker is installed but not running."
    echo "  Try starting it with:  sudo systemctl start docker"
    echo "  Then run this script again."
    exit 1
fi
ok "Docker is running."

# ── 2. Start Cart Radar ──────────────────────────────────────
banner "Starting Cart Radar..."
echo "  (First launch builds images — may take a few minutes.)"
docker compose -f "$COMPOSE_FILE" up --build --remove-orphans -d 2>&1

# ── 3. Wait for readiness ────────────────────────────────────
banner "Waiting for Cart Radar to be ready..."
MAX_WAIT=180; ELAPSED=0
printf "  "
while true; do
    if curl -s --max-time 2 "$APP_URL" &>/dev/null; then
        echo ""; ok "Cart Radar is ready!"; break
    fi
    sleep 2; ELAPSED=$((ELAPSED + 2)); printf "."
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo ""
        fail "Cart Radar did not become ready within ${MAX_WAIT}s."
        echo "  Logs:"; docker compose -f "$COMPOSE_FILE" logs --tail=30 2>&1 || true
        exit 1
    fi
done

# ── 4. Open browser ──────────────────────────────────────────
banner "Opening Cart Radar in your browser..."
sleep 1
# Try common Linux browser openers
xdg-open "$APP_URL" 2>/dev/null || \
  sensible-browser "$APP_URL" 2>/dev/null || \
  firefox "$APP_URL" 2>/dev/null || \
  google-chrome "$APP_URL" 2>/dev/null || \
  chromium "$APP_URL" 2>/dev/null || \
  echo "  Please open $APP_URL in your browser."

echo ""
echo -e "${BOLD}  Cart Radar is running at ${CYAN}${APP_URL}${RESET}"
echo ""
echo "  To stop Cart Radar:"
echo "    docker compose down"
echo ""
echo -e "${YELLOW}  Leave this terminal open while you use Cart Radar.${RESET}"
echo "  Press Ctrl+C to stop all services and exit."
echo ""

trap 'echo -e "\n\nStopping Cart Radar..."; docker compose -f "$COMPOSE_FILE" down; echo "Stopped."; exit 0' INT TERM
docker compose -f "$COMPOSE_FILE" logs -f 2>&1
