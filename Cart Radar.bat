@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
:: ============================================================
::  Cart Radar — Windows Launcher
::  Double-click this file in Windows Explorer to start Cart Radar.
:: ============================================================

:: Run from the folder containing this script
cd /d "%~dp0"

set APP_URL=http://localhost:3000
set COMPOSE_FILE=%~dp0docker-compose.yml

echo.
echo   ================================================
echo           Starting Cart Radar...
echo   ================================================
echo.

:: ── 1. Check Docker ────────────────────────────────────────────
echo [1/4] Checking Docker...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker Desktop is not installed.
    echo   Please run "Cart Radar Install.bat" first.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   Docker Desktop is installed but not running.
    echo   Attempting to start Docker Desktop...
    echo.
    start "" "Docker Desktop"
    echo   Waiting up to 60 seconds for Docker Engine to start...
    set /a WAITED=0
    :wait_docker
    timeout /t 2 /nobreak >nul
    docker info >nul 2>&1
    if !ERRORLEVEL! equ 0 goto docker_ready
    set /a WAITED+=2
    if !WAITED! geq 60 (
        echo.
        echo   ERROR: Docker did not start within 60 seconds.
        echo   Please start Docker Desktop manually and try again.
        echo.
        pause
        exit /b 1
    )
    goto wait_docker
    :docker_ready
    echo   OK - Docker Engine is now running.
) else (
    echo   OK - Docker Engine is running.
)
echo.

:: ── 2. Check for Updates & Start ───────────────────────────────
echo [2/4] Starting containers...
docker compose -f "%COMPOSE_FILE%" pull -q >nul 2>&1
docker compose -f "%COMPOSE_FILE%" up --remove-orphans -d
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Failed to start Cart Radar containers.
    echo   Please check if port 3000 is already in use by another application.
    echo   If the error says 'registry: denied', the GHCR packages are Private.
    echo.
    pause
    exit /b 1
)
echo   OK - Containers started.
echo.

:: ── 3. Wait for Readiness ──────────────────────────────────────
echo [3/4] Waiting for Cart Radar to be ready...
set /a ELAPSED=0
:wait_ready
timeout /t 2 /nobreak >nul
curl -s --max-time 2 --output nul %APP_URL%/api/ping
if !ERRORLEVEL! equ 0 goto app_ready
curl -s --max-time 2 --output nul %APP_URL%
if !ERRORLEVEL! equ 0 goto app_ready
set /a ELAPSED+=2
if !ELAPSED! geq 180 (
    echo.
    echo.
    echo   ERROR: Cart Radar did not become ready within 3 minutes.
    echo   Check logs with: docker compose logs --tail=50
    echo.
    pause
    exit /b 1
)
<nul set /p "=."
goto wait_ready

:app_ready
echo.
echo.
echo   OK - Cart Radar backend is responding.
echo.

:: ── 4. Open Browser ─────────────────────────────────────────────
echo [4/4] Opening browser...
timeout /t 1 /nobreak >nul
start "" "%APP_URL%"
echo.

echo   ====================================================
echo    Cart Radar is ready!
echo    %APP_URL%
echo   ====================================================
echo.
echo   To stop Cart Radar, press any key in this window.
echo   Leave this window open while you use Cart Radar.
echo.
pause

echo.
echo   Stopping Cart Radar...
docker compose -f "%COMPOSE_FILE%" down
echo   Cart Radar stopped successfully.
timeout /t 2 /nobreak >nul
