#!/usr/bin/env bash
# ============================================================
#  Cart Radar — Linux Launcher
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
warn()   { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
fail()   { echo -e "\n${RED}✗ ERROR:${RESET} $1\n"; }

clear
echo -e "${BOLD}"
echo "  ╔══════════════════════════════╗"
echo "  ║        🎯  Cart Radar        ║"
echo "  ╚══════════════════════════════╝"
echo -e "${RESET}"

# ── 1. Check Docker ──────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    echo "  Please run './Cart Radar Install.sh' first."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    fail "Docker is installed but not running (or requires sudo)."
    echo "  Try starting it with:  sudo systemctl start docker"
    echo "  Then run this script again."
    exit 1
fi

# ── 2. Check for Updates ─────────────────────────────────────
echo "  Checking for updates..."
docker compose -f "$COMPOSE_FILE" pull -q 2>/dev/null || true

# ── 3. Start Cart Radar ──────────────────────────────────────
banner "Starting Cart Radar..."
docker compose -f "$COMPOSE_FILE" up --remove-orphans -d 2>&1
if [ $? -ne 0 ]; then
    fail "Failed to start Docker containers."
    echo "  Please check the error message above."
    exit 1
fi
ok "Containers started."

# ── 4. Wait for readiness ────────────────────────────────────
banner "Waiting for Cart Radar to be ready..."
MAX_WAIT=180; ELAPSED=0
printf "  "
while true; do
    if curl -s --max-time 2 "$APP_URL/api/ping" &>/dev/null || curl -s --max-time 2 "$APP_URL" &>/dev/null; then
        echo ""; ok "Cart Radar is ready!"; break
    fi
    sleep 2; ELAPSED=$((ELAPSED + 2)); printf "."
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo ""
        fail "Cart Radar did not become ready within ${MAX_WAIT}s."
        echo "  Showing recent logs:"
        docker compose -f "$COMPOSE_FILE" logs --tail=40 2>&1 || true
        exit 1
    fi
done

# ── 5. Open browser ──────────────────────────────────────────
banner "Opening Cart Radar in your browser..."
sleep 1
xdg-open "$APP_URL" 2>/dev/null || \
  sensible-browser "$APP_URL" 2>/dev/null || \
  firefox "$APP_URL" 2>/dev/null || \
  google-chrome "$APP_URL" 2>/dev/null || \
  chromium "$APP_URL" 2>/dev/null || \
  echo "  Please open $APP_URL in your browser."

echo ""
echo -e "${BOLD}  ✅ Cart Radar is running at ${CYAN}${APP_URL}${RESET}"
echo ""
echo "  To stop Cart Radar, press Ctrl+C."
echo ""
echo -e "${YELLOW}  Leave this terminal open while you use Cart Radar.${RESET}"
echo ""

trap 'echo -e "\n\n  Stopping Cart Radar..."; docker compose -f "$COMPOSE_FILE" down; echo "  Stopped."; exit 0' INT TERM
docker compose -f "$COMPOSE_FILE" logs -f 2>&1
