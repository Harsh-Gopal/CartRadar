#!/usr/bin/env bash
# ============================================================
#  Cart Radar — macOS Installer
#  Double-click this file to set up Cart Radar for the first time.
#
#  Requires: Docker Desktop (free)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() { echo -e "\n${CYAN}${BOLD}$1${RESET}"; }
ok()     { echo -e "  ${GREEN}✓${RESET} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
fail()   { echo -e "\n${RED}✗ ERROR:${RESET} $1\n"; }

clear
echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║        🎯 Cart Radar Installer       ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${RESET}"

banner "1. Checking for Docker Desktop..."
if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    echo "  Docker Desktop is required to run Cart Radar."
    echo ""
    echo "  ➡ Please install Docker Desktop (free) from:"
    echo "     https://www.docker.com/products/docker-desktop/"
    echo ""
    echo "  Once installed, open Docker Desktop, wait for it to start,"
    echo "  and then run this installer again."
    echo ""
    read -r -p "  Press Enter to open the download page..." _
    open "https://www.docker.com/products/docker-desktop/"
    exit 1
fi

banner "2. Checking if Docker is running..."
if ! docker info &>/dev/null 2>&1; then
    fail "Docker is installed but not running."
    echo "  Please open Docker Desktop from your Applications folder."
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
            echo "  Please start Docker Desktop manually and run this installer again."
            read -r -p "  Press Enter to exit..." _
            exit 1
        fi
    done
else
    ok "Docker is running."
fi

banner "3. Verifying Docker Compose..."
if ! docker compose version &>/dev/null; then
    fail "Docker Compose is not available. Please ensure Docker Desktop is fully updated."
    exit 1
fi
ok "Docker Compose is ready."

banner "4. Downloading Cart Radar..."
echo "  Downloading pre-built images from GitHub Container Registry."
echo "  This requires ~1-2 GB and may take a few minutes depending on your connection."
echo ""

if ! docker compose -f "$COMPOSE_FILE" pull; then
    fail "Failed to download Cart Radar images."
    echo "  If you see an 'error from registry: denied' message, the GitHub"
    echo "  Container Registry packages might currently be set to Private."
    echo "  Please see docs/DOCKER_SETUP.md for instructions on how the"
    echo "  repository owner must make them Public."
    echo ""
    echo "  Otherwise, check your internet connection and try again."
    read -r -p "  Press Enter to exit..." _
    exit 1
fi
ok "Successfully downloaded Cart Radar."

echo ""
echo -e "${BOLD}${GREEN}  ✅ Installation Complete!${RESET}"
echo ""
echo "  You can now start the application anytime by double-clicking:"
echo -e "  ${CYAN}Cart Radar.command${RESET}"
echo ""
read -r -p "  Press Enter to close this window..." _
exit 0
