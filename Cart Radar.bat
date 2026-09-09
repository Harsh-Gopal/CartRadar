@echo off
setlocal EnableDelayedExpansion
:: ============================================================
::  Cart Radar — Windows one-click launcher
::  Double-click this file in Windows Explorer to start Cart Radar.
::
::  Requires: Docker Desktop (free) — https://www.docker.com/products/docker-desktop/
::  No Python, Node.js, or coding knowledge required.
:: ============================================================

:: Run from the folder containing this script
cd /d "%~dp0"

set APP_URL=http://localhost:3000
set COMPOSE_FILE=%~dp0docker-compose.yml

echo.
echo   ╔══════════════════════════════╗
echo   ║        🎯  Cart Radar        ║
echo   ╚══════════════════════════════╝
echo.

:: ── 1. Check Docker is installed ────────────────────────────
echo [1/5] Checking Docker Desktop...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker is not installed.
    echo.
    echo   Cart Radar uses Docker, which keeps your PC clean
    echo   (no Python/Node installation needed).
    echo.
    echo   Install Docker Desktop (free) from:
    echo     https://www.docker.com/products/docker-desktop/
    echo.
    echo   After installing, open Docker Desktop, wait for it to show
    echo   "Docker Desktop is running" in the taskbar, then
    echo   double-click this file again.
    echo.
    start https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: ── 2. Check Docker daemon is running ───────────────────────
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
        echo   Please start Docker Desktop manually and try again.
        pause
        exit /b 1
    )
    goto wait_docker
    :docker_ready
    echo   OK - Docker Desktop is now running.
)
echo   OK - Docker Desktop is running.

:: ── 3. Pull the latest pre-built images ─────────────────────
echo.
echo [2/5] Downloading Cart Radar images...
echo   (First launch downloads approximately 1-2 GB.)
echo   (After that, updates are much smaller and launches are instant.)
echo.

docker compose -f "%COMPOSE_FILE%" pull
if %ERRORLEVEL% neq 0 (
    echo.
    echo   WARNING: Could not download latest images.
    echo   Trying to start with locally cached images...
)
echo   OK - Images ready.

:: ── 4. Start Cart Radar ──────────────────────────────────────
echo.
echo [3/5] Starting Cart Radar...
docker compose -f "%COMPOSE_FILE%" up --remove-orphans -d
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Failed to start Cart Radar.
    echo   Check the output above for details.
    echo   For help: https://github.com/Harsh-Gopal/CartRadar/issues
    pause
    exit /b 1
)
echo   OK - Containers started.

:: ── 5. Wait for the app to become ready ─────────────────────
echo.
echo [4/5] Waiting for Cart Radar to be ready...
echo   (Backend initializes on first start - may take up to 90 seconds.)
set /a ELAPSED=0
:wait_ready
timeout /t 2 /nobreak >nul
curl -s --max-time 2 --output nul %APP_URL%
if %ERRORLEVEL% equ 0 goto app_ready
set /a ELAPSED+=2
if !ELAPSED! geq 180 (
    echo.
    echo   ERROR: Cart Radar did not become ready within 3 minutes.
    echo   Check logs with:  docker compose logs --tail=50
    echo   For help: https://github.com/Harsh-Gopal/CartRadar/issues
    pause
    exit /b 1
)
<nul set /p "=."
goto wait_ready

:app_ready
echo.
echo   OK - Cart Radar is ready!

:: ── 6. Open in the default browser ──────────────────────────
echo.
echo [5/5] Opening Cart Radar in your browser...
timeout /t 1 /nobreak >nul
start "" "%APP_URL%"

echo.
echo   ====================================================
echo    Cart Radar is running at %APP_URL%
echo   ====================================================
echo.
echo   To update to the latest version, close this window and
echo   double-click this launcher file again.
echo.
echo   To stop Cart Radar, close this window.
echo.
echo   Leave this window open while you use Cart Radar.
echo.
pause
