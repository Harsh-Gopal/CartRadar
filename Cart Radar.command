#!/usr/bin/env bash
# ============================================================
#  Cart Radar — macOS one-click launcher
#  Double-click this file in Finder to start Cart Radar.
# ============================================================
set -euo pipefail

# Always run from the directory that contains this script,
# regardless of where the project folder is placed.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_URL="http://localhost:3000"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

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
    echo "  Cart Radar runs inside Docker, which keeps your Mac clean"
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
            ok "Docker is now running."
            break
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

# ── 3. Start Cart Radar with Docker Compose ─────────────────
banner "Starting Cart Radar..."
echo "  (First launch downloads/builds images — this may take a few minutes.)"
echo "  Subsequent launches are much faster."
echo ""

# Pull/build and start in the background
docker compose -f "$COMPOSE_FILE" up --build --remove-orphans -d 2>&1

# ── 4. Wait for the frontend to be ready ────────────────────
banner "Waiting for Cart Radar to be ready..."
MAX_WAIT=180
ELAPSED=0
printf "  "
while true; do
    if curl -s --max-time 2 "$APP_URL" &>/dev/null; then
        echo ""
        ok "Cart Radar is ready!"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    printf "."
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo ""
        fail "Cart Radar did not become ready within ${MAX_WAIT}s."
        echo "  Check the logs for errors:"
        echo "    docker compose logs --tail=50"
        echo ""
        docker compose -f "$COMPOSE_FILE" logs --tail=30 2>&1 || true
        read -r -p "  Press Enter to exit..." _
        exit 1
    fi
done

# ── 5. Open in the default browser ──────────────────────────
banner "Opening Cart Radar in your browser..."
sleep 1
open "$APP_URL"

echo ""
echo -e "${BOLD}  Cart Radar is running at ${CYAN}${APP_URL}${RESET}"
echo ""
echo "  To stop Cart Radar, close this window and run:"
echo "    docker compose down"
echo ""
echo "  Or run:  docker compose down   in the project folder."
echo ""
echo -e "${YELLOW}  Leave this window open while you use Cart Radar.${RESET}"
echo "  Press Ctrl+C to stop all services and exit."
echo ""

# Keep running so the user can see logs; Ctrl+C triggers cleanup
trap 'echo -e "\n\nStopping Cart Radar..."; docker compose -f "$COMPOSE_FILE" down; echo "Stopped. Goodbye!"; exit 0' INT TERM

# Stream logs so the window stays alive and informative
docker compose -f "$COMPOSE_FILE" logs -f 2>&1
