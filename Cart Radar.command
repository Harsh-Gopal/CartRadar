#!/usr/bin/env bash
# ============================================================
#  Cart Radar — macOS one-click launcher
#  Double-click this file in Finder to start Cart Radar.
#
#  Requires: Docker Desktop (free) — https://www.docker.com/products/docker-desktop/
#  No Python, Node.js, or coding knowledge required.
# ============================================================
set -euo pipefail

# Always run from the directory containing this script,
# regardless of where the project folder is placed.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_URL="http://localhost:3000"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
IMAGES=("ghcr.io/harsh-gopal/cartradar-backend:latest" "ghcr.io/harsh-gopal/cartradar-frontend:latest")

# ── Colour helpers ───────────────────────────────────────────
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

# ── 1. Check Docker Desktop is installed ────────────────────
banner "Checking Docker Desktop..."

if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    echo "  Cart Radar uses Docker, which keeps your Mac clean"
    echo "  (no Python/Node installation needed)."
    echo ""
    echo "  ➡  Install Docker Desktop (free) from:"
    echo "     https://www.docker.com/products/docker-desktop/"
    echo ""
    echo "  After installing, open Docker Desktop, wait for it to say"
    echo "  'Docker Desktop is running', then double-click this file again."
    echo ""
    read -r -p "  Press Enter to open the Docker website..." _
    open "https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# ── 2. Check Docker daemon is running ───────────────────────
if ! docker info &>/dev/null 2>&1; then
    fail "Docker Desktop is installed but not running."
    echo "  Please open Docker Desktop from your Applications folder,"
    echo "  wait until the menu-bar whale icon stops animating,"
    echo "  then double-click this file again."
    echo ""
    warn "Attempting to open Docker Desktop for you..."
    open -a "Docker Desktop" 2>/dev/null || open -a "Docker" 2>/dev/null || true

    echo ""
    echo "  Waiting up to 60 seconds for Docker to start..."
    for i in $(seq 1 60); do
        sleep 1
        if docker info &>/dev/null 2>&1; then
            ok "Docker is now running."; break
        fi
        printf "."
        if [ "$i" -eq 60 ]; then
            echo ""
            fail "Docker did not start within 60 seconds."
            echo "  Please start Docker Desktop manually and try again."
            read -r -p "  Press Enter to exit..." _
            exit 1
        fi
    done
fi
ok "Docker Desktop is running."

# ── 3. Pull the latest pre-built images ─────────────────────
banner "Downloading Cart Radar images..."
echo "  (First launch downloads ~1-2 GB — subsequent launches are instant.)"
echo "  Pulling from GitHub Container Registry..."
echo ""

docker compose -f "$COMPOSE_FILE" pull 2>&1 || {
    warn "Pull failed (you may be offline). Trying to start with cached images..."
}
ok "Images ready."

# ── 4. Start Cart Radar ──────────────────────────────────────
banner "Starting Cart Radar..."
docker compose -f "$COMPOSE_FILE" up --remove-orphans -d 2>&1
ok "Containers started."

# ── 5. Wait for the app to become ready ─────────────────────
banner "Waiting for Cart Radar to be ready..."
echo "  (Backend initializes Playwright on first start — may take up to 90 seconds.)"
MAX_WAIT=180
ELAPSED=0
printf "  "
while true; do
    if curl -s --max-time 2 "$APP_URL" &>/dev/null; then
        echo ""
        ok "Cart Radar is ready!"
        break
    fi
    sleep 2; ELAPSED=$((ELAPSED + 2)); printf "."
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo ""
        fail "Cart Radar did not become ready within ${MAX_WAIT}s."
        echo "  Showing recent logs for diagnosis:"
        docker compose -f "$COMPOSE_FILE" logs --tail=40 2>&1 || true
        echo ""
        echo "  For help, see: https://github.com/Harsh-Gopal/CartRadar/issues"
        read -r -p "  Press Enter to exit..." _
        exit 1
    fi
done

# ── 6. Open in the default browser ──────────────────────────
banner "Opening Cart Radar in your browser..."
sleep 1
open "$APP_URL"

echo ""
echo -e "${BOLD}  ✅ Cart Radar is running at ${CYAN}${APP_URL}${RESET}"
echo ""
echo -e "  To update to the latest version, re-open this launcher."
echo -e "  To stop Cart Radar, close this window (Ctrl+C)."
echo ""
echo -e "${YELLOW}  Leave this window open while you use Cart Radar.${RESET}"
echo ""

# Keep the window alive, stream logs so it stays informative
# Ctrl+C triggers cleanup via trap
trap 'echo -e "\n\n  Stopping Cart Radar..."; docker compose -f "$COMPOSE_FILE" down; echo "  Stopped. Goodbye!"; exit 0' INT TERM

docker compose -f "$COMPOSE_FILE" logs -f 2>&1
