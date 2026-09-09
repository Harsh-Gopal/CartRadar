@echo off
setlocal EnableDelayedExpansion
:: ============================================================
::  Cart Radar — Windows Installer
::  Double-click this file to set up Cart Radar for the first time.
::
::  Requires: Docker Desktop (free)
:: ============================================================

:: Run from the folder containing this script
cd /d "%~dp0"

set COMPOSE_FILE=%~dp0docker-compose.yml

echo.
echo   ╔══════════════════════════════════════╗
echo   ║        🎯 Cart Radar Installer       ║
echo   ╚══════════════════════════════════════╝
echo.

:: ── 1. Check Docker is installed ────────────────────────────
echo [1/4] Checking Docker Desktop...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker is not installed.
    echo   Docker Desktop is required to run Cart Radar.
    echo.
    echo   ➡ Please install Docker Desktop (free) from:
    echo     https://www.docker.com/products/docker-desktop/
    echo.
    echo   Once installed, open Docker Desktop, wait for it to show
    echo   "Docker Desktop is running" in the taskbar, then
    echo   run this installer again.
    echo.
    start https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: ── 2. Check Docker daemon is running ───────────────────────
echo [2/4] Checking if Docker is running...
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   Docker Desktop is installed but not running.
    echo   Opening Docker Desktop — please wait for it to start...
    echo.
    start "" "Docker Desktop"
    echo   Waiting up to 60 seconds for Docker to start...
    set /a WAITED=0
    :wait_docker
    timeout /t 2 /nobreak >nul
    docker info >nul 2>&1
    if %ERRORLEVEL% equ 0 goto docker_ready
    set /a WAITED+=2
    if !WAITED! geq 60 (
        echo.
        echo   ERROR: Docker did not start within 60 seconds.
        echo   Please start Docker Desktop manually and run this installer again.
        pause
        exit /b 1
    )
    goto wait_docker
    :docker_ready
    echo   OK - Docker Desktop is now running.
) else (
    echo   OK - Docker Desktop is running.
)

:: ── 3. Check Docker Compose ─────────────────────────────────
echo [3/4] Verifying Docker Compose...
docker compose version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker Compose is not available. 
    echo   Please ensure Docker Desktop is fully updated.
    pause
    exit /b 1
)
echo   OK - Docker Compose is ready.

:: ── 4. Pull the latest pre-built images ─────────────────────
echo.
echo [4/4] Downloading Cart Radar...
echo   Downloading pre-built images from GitHub Container Registry.
echo   This requires ~1-2 GB and may take a few minutes.
echo.

docker compose -f "%COMPOSE_FILE%" pull
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Failed to download Cart Radar images.
    echo   Check your internet connection and try again.
    pause
    exit /b 1
)
echo   OK - Successfully downloaded Cart Radar.

echo.
echo   ====================================================
echo    ✅ Installation Complete!
echo   ====================================================
echo.
echo   You can now start the application anytime by double-clicking:
echo   Cart Radar.bat
echo.
pause
