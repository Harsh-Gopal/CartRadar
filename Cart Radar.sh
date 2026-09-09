#!/usr/bin/env bash
# ============================================================
#  Cart Radar — Linux one-click launcher
#  Run this script, or double-click "Cart Radar.desktop".
#
#  Requires: Docker Engine or Docker Desktop (free)
#  https://docs.docker.com/engine/install/
#  No Python, Node.js, or coding knowledge required.
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
banner "Checking Docker..."

if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    echo "  Install Docker Engine for Linux:"
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

# ── 2. Pull the latest pre-built images ─────────────────────
banner "Downloading Cart Radar images..."
echo "  (First launch downloads ~1-2 GB — subsequent launches are instant.)"
echo "  Pulling from GitHub Container Registry..."

docker compose -f "$COMPOSE_FILE" pull 2>&1 || {
    warn "Pull failed (you may be offline). Trying to start with cached images..."
}
ok "Images ready."

# ── 3. Start Cart Radar ──────────────────────────────────────
banner "Starting Cart Radar..."
docker compose -f "$COMPOSE_FILE" up --remove-orphans -d 2>&1
ok "Containers started."

# ── 4. Wait for readiness ────────────────────────────────────
banner "Waiting for Cart Radar to be ready..."
echo "  (Backend initializes on first start — may take up to 90 seconds.)"
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
        echo "  Showing recent logs:"
        docker compose -f "$COMPOSE_FILE" logs --tail=30 2>&1 || true
        echo "  For help: https://github.com/Harsh-Gopal/CartRadar/issues"
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
echo "  To update to the latest version, re-run this launcher."
echo "  To stop Cart Radar, press Ctrl+C."
echo ""
echo -e "${YELLOW}  Leave this terminal open while you use Cart Radar.${RESET}"
echo ""

trap 'echo -e "\n\n  Stopping Cart Radar..."; docker compose -f "$COMPOSE_FILE" down; echo "  Stopped."; exit 0' INT TERM
docker compose -f "$COMPOSE_FILE" logs -f 2>&1
