#!/usr/bin/env bash
# ============================================================
#  Cart Radar — Linux Installer
#  Run this script to set up Cart Radar for the first time.
#
#  Requires: Docker Engine or Docker Desktop (free)
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

# ── 1. Check Docker ──────────────────────────────────────────
banner "1. Checking Docker..."

if ! command -v docker &>/dev/null; then
    fail "Docker is not installed."
    echo "  Install Docker Engine for Linux:"
    echo "    https://docs.docker.com/engine/install/"
    echo ""
    echo "  After installing, you must add your user to the docker group:"
    echo "    sudo usermod -aG docker \$USER"
    echo "  Then log out and back in, and run this script again."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    fail "Docker is installed but not running (or requires sudo)."
    echo "  Try starting it with:"
    echo "    sudo systemctl start docker"
    echo ""
    echo "  If it is running, you may need to add yourself to the docker group:"
    echo "    sudo usermod -aG docker \$USER"
    echo "  Then log out, log back in, and run this script again."
    exit 1
fi
ok "Docker is installed and running."

# ── 2. Check Docker Compose ──────────────────────────────────
banner "2. Verifying Docker Compose..."
if ! docker compose version &>/dev/null; then
    fail "Docker Compose is not available. Please ensure the Docker compose-plugin is installed."
    exit 1
fi
ok "Docker Compose is ready."

# ── 3. Pull the latest pre-built images ─────────────────────
banner "3. Downloading Cart Radar images..."
echo "  Downloading pre-built images from GitHub Container Registry."
echo "  This requires ~1-2 GB and may take a few minutes."
echo ""

docker compose -f "$COMPOSE_FILE" pull
if [ $? -ne 0 ]; then
    fail "Failed to download Cart Radar images. Check your internet connection and try again."
    exit 1
fi
ok "Successfully downloaded Cart Radar."

# ── 4. Setup Desktop Shortcuts (Optional) ────────────────────
banner "4. Making Launchers Executable..."
chmod +x "$SCRIPT_DIR/Cart Radar Install.desktop" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/Cart Radar.desktop" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/Cart Radar.sh" 2>/dev/null || true
ok "Permissions updated."

echo ""
echo -e "${BOLD}${GREEN}  ✅ Installation Complete!${RESET}"
echo ""
echo "  You can now start the application anytime by running:"
echo -e "  ${CYAN}./Cart Radar.sh${RESET}"
echo "  (Or by double-clicking 'Cart Radar.desktop' if your file manager supports it)"
echo ""
read -r -p "  Press Enter to exit..." _
exit 0
