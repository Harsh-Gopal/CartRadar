@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
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
echo   ================================================
echo           CART RADAR INSTALLER
echo   ================================================
echo.

:: ── 1. Check WSL 2 (Windows Prerequisites) ────────────────────
echo [1/5] Checking Windows prerequisites (WSL 2)...
wsl --status >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: WSL 2 (Windows Subsystem for Linux) is missing.
    echo   Docker Desktop requires WSL 2 to run properly on Windows.
    echo.
    echo   Please install it by opening PowerShell as Administrator and running:
    echo     wsl --install
    echo.
    echo   WSL 2 is required. Please install it, restart Windows, then run Cart Radar Install.bat again.
    echo.
    pause
    exit /b 1
)
echo   OK - WSL is available.
echo.

:: ── 2. Check Docker Desktop ─────────────────────────────────
echo [2/5] Checking Docker Desktop...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker Desktop is not installed.
    echo   Docker Desktop is required to run Cart Radar.
    echo.
    echo   Please install Docker Desktop (free) from:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    echo   Once installed, open Docker Desktop, wait for it to start,
    echo   then run this installer again.
    echo.
    start https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo   OK - Docker Desktop is installed.
echo.

:: ── 3. Check Docker Engine ──────────────────────────────────
echo [3/5] Checking if Docker Engine is running...
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
        echo   Please start Docker Desktop manually from the Start Menu,
        echo   wait for it to finish starting, and run this installer again.
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

:: ── 4. Downloading Images ───────────────────────────────────
echo [4/5] Downloading Cart Radar Docker images...
echo   Downloading pre-built images from GitHub Container Registry.
echo   This requires ~1-2 GB and may take a few minutes.
echo.

docker compose -f "%COMPOSE_FILE%" pull
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Failed to download Cart Radar images.
    echo   If you see 'registry: denied', the packages might be Private.
    echo   Otherwise, please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo.
echo   OK - Images downloaded successfully.
echo.

:: ── 5. Verifying Installation ───────────────────────────────
echo [5/5] Verifying installation...
docker compose -f "%COMPOSE_FILE%" config >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Docker Compose configuration is invalid.
    echo   Please ensure you extracted all files from the ZIP before running.
    echo.
    pause
    exit /b 1
)
echo   OK - Configuration is valid.
echo.

echo   ====================================================
echo    Installation complete!
echo   ====================================================
echo.
echo   You can now start the application anytime by double-clicking:
echo.
echo     Cart Radar.bat
echo.
pause
