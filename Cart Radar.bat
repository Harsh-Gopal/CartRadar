@echo off
setlocal EnableDelayedExpansion
:: ============================================================
::  Cart Radar — Windows Launcher
::  Double-click this file in Windows Explorer to start Cart Radar.
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

:: ── 1. Check Docker ────────────────────────────────────────────
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker is not installed.
    echo   Please run "Cart Radar Install.bat" first.
    pause
    exit /b 1
)

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

:: ── 2. Check for Updates ──────────────────────────────────────
echo.
echo   Checking for updates...
docker compose -f "%COMPOSE_FILE%" pull -q >nul 2>&1

:: ── 3. Start Cart Radar ──────────────────────────────────────
echo.
echo   Starting Cart Radar...
docker compose -f "%COMPOSE_FILE%" up --remove-orphans -d
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Failed to start Cart Radar.
    echo   Check the output above for details.
    pause
    exit /b 1
)
echo   OK - Containers started.

:: ── 4. Wait for the app to become ready ─────────────────────
echo.
echo   Waiting for Cart Radar to be ready...
set /a ELAPSED=0
:wait_ready
timeout /t 2 /nobreak >nul
curl -s --max-time 2 --output nul %APP_URL%/api/ping
if %ERRORLEVEL% equ 0 goto app_ready
curl -s --max-time 2 --output nul %APP_URL%
if %ERRORLEVEL% equ 0 goto app_ready
set /a ELAPSED+=2
if !ELAPSED! geq 180 (
    echo.
    echo   ERROR: Cart Radar did not become ready within 3 minutes.
    echo   Check logs with:  docker compose logs --tail=50
    pause
    exit /b 1
)
<nul set /p "=."
goto wait_ready

:app_ready
echo.
echo   OK - Cart Radar is ready!

:: ── 5. Open in the default browser ──────────────────────────
echo.
echo   Opening Cart Radar in your browser...
timeout /t 1 /nobreak >nul
start "" "%APP_URL%"

echo.
echo   ====================================================
echo    Cart Radar is running at %APP_URL%
echo   ====================================================
echo.
echo   To stop Cart Radar, close this window.
echo.
echo   Leave this window open while you use Cart Radar.
echo.
pause
