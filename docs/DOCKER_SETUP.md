# Cart Radar Docker Setup Guide

This guide explains how to install and run Cart Radar using Docker Desktop. You do not need any coding knowledge to run Cart Radar this way.

---

## Option A — One-click installation (First time only)

The installation process checks if Docker is installed, guides you if it isn't, and downloads the Cart Radar Docker images.

1. **Download Cart Radar:** Click the green **"Code"** button at the top of the [GitHub repository](https://github.com/Harsh-Gopal/CartRadar), choose **"Download ZIP"**, and extract it anywhere on your computer.
2. Open the extracted `cart-radar` folder.
3. Double-click the installer for your operating system:
   * **macOS:** Double-click `Cart Radar Install.command`
   * **Windows:** Double-click `Cart Radar Install.bat`
   * **Linux:** Double-click `Cart Radar Install.desktop` (or run `./Cart Radar Install.sh` in the terminal)
4. Follow the on-screen prompts.
   * If the script says **"Docker is not installed"**, it will provide a link to download Docker Desktop. Install it, open it, and wait for it to fully start before running the script again.
5. The script will download the pre-built Cart Radar images (~1-2 GB). This may take a few minutes depending on your internet connection.
6. Once it says **"Installation Complete"**, you are ready to use Cart Radar.

---

## Option B — One-click running (Everyday use)

Use these scripts whenever you want to start Cart Radar.

1. Open the `cart-radar` folder.
2. Double-click the launcher for your operating system:
   * **macOS:** Double-click `Cart Radar.command`
   * **Windows:** Double-click `Cart Radar.bat`
   * **Linux:** Double-click `Cart Radar.desktop` (or run `./Cart Radar.sh` in the terminal)
3. The script will automatically check for updates, start the backend and frontend, and wait for them to become ready.
4. Your default web browser will automatically open to `http://localhost:3000`.

### Stopping Cart Radar
* **macOS / Linux:** Simply close the terminal window where the script is running. It will automatically stop the containers safely.
* **Windows:** Close the command prompt window.

### Updating Cart Radar
Whenever you launch Cart Radar using the run scripts, it automatically checks for and downloads the newest pre-built image in the background.

---

## Option C — Manual Docker setup (For Developers)

If you are comfortable using the terminal, you can manage the Docker containers manually.

**Prerequisites:** Ensure [Docker Desktop](https://docs.docker.com/get-docker/) is installed and running.

**1. Pull the latest images:**
```bash
docker compose pull
```

**2. Start Cart Radar in the background:**
```bash
docker compose up -d
```
Then, open `http://localhost:3000` in your web browser.

**3. View logs:**
```bash
docker compose logs -f
```

**4. Stop Cart Radar:**
```bash
docker compose down
```

**5. Update the images and restart:**
```bash
docker compose pull
docker compose up -d --remove-orphans
```

---

## Troubleshooting

| Problem | Solution |
| :--- | :--- |
| **Docker is not installed** | Download and install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/). |
| **Docker is not running** | Open the Docker Desktop application from your Applications / Start menu. Wait for the icon in the menu bar/taskbar to stop animating and say "Docker Desktop is running". |
| **Docker Compose is not available** | Ensure your Docker Desktop is fully updated. Compose is bundled with modern Docker installations. |
| **Image pull fails / network error** | Check your internet connection. The initial download is large (1-2 GB). |
| **Port 3000 is already in use** | Stop any other application using port 3000. Alternatively, open `docker-compose.yml` in a text editor and change the frontend ports from `"3000:80"` to `"3001:80"`. |
| **Browser doesn't open automatically** | Manually open your web browser and go to `http://localhost:3000`. |
| **Container fails health check** | The backend may take up to 90 seconds to initialize Playwright on the very first run. If it fails, wait a moment and try refreshing the page. You can also view logs using `docker compose logs` to see what went wrong. |
| **Custom proxy isn't working** | Ensure you have created a `.env` file containing `PROXY_URL=http://your_proxy` in the `cart-radar` folder. Restart Cart Radar for it to take effect. |
