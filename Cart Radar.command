#!/usr/bin/env bash
# ============================================================
#  Cart Radar — macOS Launcher
#  Double-click this file in Finder to start Cart Radar.
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
    echo "  Please run 'Cart Radar Install.command' first."
    read -r -p "  Press Enter to exit..." _
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    fail "Docker Desktop is not running."
    warn "Attempting to start Docker Desktop..."
    open -a "Docker Desktop" 2>/dev/null || open -a "Docker" 2>/dev/null || true
    
    echo "  Waiting up to 60 seconds for Docker to start..."
    for i in $(seq 1 60); do
        sleep 1
        if docker info &>/dev/null 2>&1; then
            break
        fi
        printf "."
        if [ "$i" -eq 60 ]; then
            echo ""
            fail "Docker did not start. Please start it manually."
            read -r -p "  Press Enter to exit..." _
            exit 1
        fi
    done
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
    read -r -p "  Press Enter to exit..." _
    exit 1
fi
ok "Containers started."

# ── 4. Wait for the app to become ready ─────────────────────
banner "Waiting for Cart Radar to be ready..."
MAX_WAIT=180
ELAPSED=0
printf "  "
while true; do
    if curl -s --max-time 2 "$APP_URL/api/ping" &>/dev/null || curl -s --max-time 2 "$APP_URL" &>/dev/null; then
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
        read -r -p "  Press Enter to exit..." _
        exit 1
    fi
done

# ── 5. Open in the default browser ──────────────────────────
banner "Opening Cart Radar in your browser..."
sleep 1
open "$APP_URL"

echo ""
echo -e "${BOLD}  ✅ Cart Radar is running at ${CYAN}${APP_URL}${RESET}"
echo ""
echo -e "  To stop Cart Radar, close this window (Ctrl+C)."
echo ""
echo -e "${YELLOW}  Leave this window open while you use Cart Radar.${RESET}"
echo ""

trap 'echo -e "\n\n  Stopping Cart Radar..."; docker compose -f "$COMPOSE_FILE" down; echo "  Stopped. Goodbye!"; exit 0' INT TERM

docker compose -f "$COMPOSE_FILE" logs -f 2>&1
