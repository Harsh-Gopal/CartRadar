<div align="center">

# 🎯 Cart Radar

**Real-time grocery stock checker across Indian quick-commerce platforms**

[![GitHub](https://img.shields.io/badge/GitHub-Harsh--Gopal-181717?logo=github)](https://github.com/Harsh-Gopal)
[![Repo](https://img.shields.io/badge/Repo-CartRadar-blue?logo=github)](https://github.com/Harsh-Gopal/CartRadar)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

*Built and maintained by [@Harsh-Gopal](https://github.com/Harsh-Gopal)*

⭐ **If you find Cart Radar useful, please consider giving it a star on GitHub!** ⭐

</div>

> [!NOTE]
> **This project is in active development.** You may occasionally encounter bugs, slow responses, or unavailable platform data — quick-commerce APIs change frequently and some platforms block automated access. If something breaks, wait a moment and try again, or [open an issue](https://github.com/Harsh-Gopal/CartRadar/issues). Contributions and bug reports are welcome!

> [!IMPORTANT]
> **Educational / Personal Project — Legal Disclaimer**
>
> Cart Radar is an independent, **non-commercial, open-source** project created for **educational and personal learning purposes only**.
>
> - It is **not affiliated with, endorsed by, or associated with** Zepto, Swiggy, BigBasket, Blinkit, Tata Neu, Flipkart or any other platform.
> - It accesses publicly available product and availability data through the same API endpoints that the platforms' own websites use — no credentials, subscriptions, or private access are involved.
> - Using automated tools to access platform APIs may be **against the Terms of Service** of the respective platforms. By running this project, you accept full responsibility for complying with the terms of the platforms you query.
> - This tool is **not intended for commercial use, data scraping at scale, or any activity that harms the platforms**.

---

## ✨ Features

Cart Radar is a web app that lets you paste any product link from a supported Indian grocery delivery platform and instantly see **which stores near you** have it in stock.

- **Real-time product availability**: See exactly which stores have stock and at what price.
- **Multi-platform search**: Auto-detects the platform from the product link.
- **Warehouse/dark-store discovery**: Performs a hex-grid sweep of the surrounding area to discover delivery zones beyond your default address.
- **Configurable search radius**: Adjust how far out you want to search (up to 30km).
- **Live SSE results**: Results stream into the UI in real-time as stores are discovered.
- **Map & store visualization**: View results on an interactive map or a detailed list.
- **Price & pack information**: Normalizes and displays prices, MRPs, and variants.
- **Address & reverse geocoding**: Built-in address search and reverse geocoding.
- **Store caching**: Stores are cached locally so subsequent searches in the same area are much faster.
- **Re-check Stock**: Force a fresh, live availability check that bypasses all stock caches.

---

## 🛒 Supported Platforms

| Platform | Stock Check | Area Sweep | Notes |
|---|---|---|---|
| **Zepto** | ✅ | ✅ | Playwright Hybrid Sweep architecture |
| **Swiggy Instamart** | ✅ | ✅ | Multi-zone sweep |
| **BigBasket** | ✅ | ✅ | Cookie-based location spoofing |
| **Blinkit** | ✅ | ✅ | Playwright-based |
| **Flipkart Minutes** | ✅ | ✅ | Robust metadata & cached coordinates |
| **BB Now** | ✅ | ❌ | Express delivery only |
| **Tata Neu** | 🚧 | 🚧 | Planned |
| **Amazon Fresh** | 🚧 | 🚧 | Planned |

---

## 📸 Screenshots

<table>
  <tr>
    <td align="center" width="50%">
      <a href="docs/screenshots/home.png" title="Home screen — paste a product link to begin">
        <img src="docs/screenshots/home.png" alt="Cart Radar home screen" width="100%" />
      </a>
      <br /><sub><b>Home Screen</b> — paste any product link to begin</sub>
    </td>
    <td align="center" width="50%">
      <a href="docs/screenshots/product_resolved.png" title="Product resolved with Zepto store sweep across Chandigarh">
        <img src="docs/screenshots/product_resolved.png" alt="Product resolved and stores loading on map" width="100%" />
      </a>
      <br /><sub><b>Product Resolved</b> — auto-detects platform, sweeps stores on map</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <a href="docs/screenshots/results_map.png" title="Live search results for an Instamart product in Lucknow">
        <img src="docs/screenshots/results_map.png" alt="Search results with store map" width="100%" />
      </a>
      <br /><sub><b>Live Results</b> — store list + map with stock and prices</sub>
    </td>
    <td align="center" width="50%">
      <a href="docs/screenshots/stores_list.png" title="Nearby Zepto stores in SAS Nagar with stock status">
        <img src="docs/screenshots/stores_list.png" alt="Stores list with stock status and distances" width="100%" />
      </a>
      <br /><sub><b>Stores List</b> — per-store stock, price, and distance at a glance</sub>
    </td>
  </tr>
</table>

### 🎬 Demo Video

<video src="https://github.com/user-attachments/assets/4c59e5bc-38eb-403c-95b5-1d6b10ada9b0" controls width="100%" style="max-width:900px;border-radius:12px;" title="Cart Radar — demo searching for a product across Zepto, Instamart and BigBasket stores"></video>

> _Can't play the video? View or download it directly from [GitHub](https://github.com/user-attachments/assets/4c59e5bc-38eb-403c-95b5-1d6b10ada9b0)._

---

## 🚀 Quick Start - Easy Setup Guide

### 🤖 Need Help Setting It Up?

If you prefer, copy the prompt below into ChatGPT, Claude, Gemini, or another capable LLM and it can guide you through the setup:

```text
I want to run the Cart Radar app locally on my computer.

GitHub repository:
https://github.com/Harsh-Gopal/CartRadar

Please help me set it up step by step.

1. First, ask me which operating system I am using:
   - macOS
   - Windows
   - Linux

2. Check the current Cart Radar GitHub repository and its README/documentation before giving setup instructions, so your instructions match the latest version of the project.

3. Guide me to either:
   - clone the repository using Git, OR
   - download the repository as a ZIP and extract it.

4. Check whether Docker Desktop is installed and running.
   If it is not installed, guide me to install Docker Desktop from:
   https://www.docker.com/products/docker-desktop/

5. Based on my operating system, tell me exactly which Cart Radar installation launcher to run:
   - macOS → Cart Radar Install.command
   - Windows → Cart Radar Install.bat
   - Linux → Cart Radar Install.sh

6. After installation, tell me which everyday launcher to use:
   - macOS → Cart Radar.command
   - Windows → Cart Radar.bat
   - Linux → Cart Radar.sh or Cart Radar.desktop

7. Tell me that Cart Radar will be available at:
   http://localhost:3000

8. If I encounter an error, first check the latest Cart Radar README and documentation and explain the error in simple steps.
   Use the repository documentation to determine the correct troubleshooting procedure.

9. Do not tell me to install Node.js, Python, pnpm, uv, or other developer tools unless the current Cart Radar documentation specifically requires them for the setup path I am using.

10. Do not ask me to manually edit source code for normal installation or troubleshooting.
    Prefer the official Cart Radar launchers and documented Docker workflow.

Always base your instructions on the current GitHub repository rather than older instructions or assumptions.
```

The easiest and recommended way to run Cart Radar is using the pre-built Docker images via our one-click launchers. You do NOT need Python, Node.js, or any other developer tools.

1. Install **Docker Desktop** (free) from [docker.com](https://www.docker.com/products/docker-desktop/) and ensure it is running.
2. Download or clone this repository and open the project folder.
3. Run the OS-specific installation launcher (this will check for Docker and download the latest images):
   - **macOS** → Double-click `Cart Radar Install.command`
   - **Windows** → Double-click `Cart Radar Install.bat`
   - **Linux** → Run `Cart Radar Install.sh`
4. After installation completes, run the everyday launcher to start Cart Radar:
   - **macOS** → Double-click `Cart Radar.command`
   - **Windows** → Double-click `Cart Radar.bat`
   - **Linux** → Run `Cart Radar.sh` or use `Cart Radar.desktop`
5. The launcher will automatically start the containers, wait for the app to become ready, and open your browser to **http://localhost:3000**.

*Docker Desktop is the **only** required runtime dependency for this workflow.*

---

## 🐳 Manual Docker Usage

For advanced users or server deployments, Cart Radar provides pre-built multi-platform (`linux/amd64` and `linux/arm64`) images on the GitHub Container Registry (GHCR).

1. Ensure Docker Compose is installed.
2. Pull the latest pre-built images:
   ```bash
   docker compose pull
   ```
3. Start the application in the background:
   ```bash
   docker compose up -d
   ```
4. Access Cart Radar at `http://localhost:3000`.
5. View logs:
   ```bash
   docker compose logs -f
   ```
6. Stop the application:
   ```bash
   docker compose down
   ```

---

## 👩‍💻 Developer Setup

If you want to work on the source code directly (hot-reload enabled), use the native development setup.

**Prerequisites:**
- Node.js 22+ & `pnpm` (Required for SQLite compatibility in the frontend tooling)
- Python `uv` (Handles Python versions automatically)

**Run locally:**
```bash
# Clone the repository
git clone https://github.com/Harsh-Gopal/CartRadar.git
cd CartRadar

# Start the dev environment (runs both frontend and backend)
./dev.sh
```

This starts the backend on port `8000` and the Vite frontend on port `5173`. Open `http://localhost:5173` in your browser.

---

## 🏗️ How It Works

**Frontend:**
- React + TypeScript + Vite
- Map visualization via Leaflet / `react-leaflet`
- Live result streaming using Server-Sent Events (SSE)

**Backend:**
- Built with FastAPI and Uvicorn
- Platform-specific clients utilizing `httpx` for standard API calls and `Playwright` for platforms with aggressive WAFs (like Zepto and Blinkit)
- Geographic hex-grid algorithms for uniform store discovery sweeps

**Caching Principle:**
- **Store Discovery Cache**: Discovered dark-stores/warehouses (their existence, coordinates, and serviceability) are cached locally in SQLite. This makes future searches in the same area much faster.
- **Stock Checks Are Live**: Cart Radar *never* caches actual product availability or stock levels. When you search, it checks cached stores first for instant live stock data, then sweeps the surrounding area to discover and cache new stores.
- **Re-check Stock**: Clicking the "Re-check Stock" button bypasses the discovery cache and forces a fresh hex-grid sweep of the entire radius.

---

## ⚙️ Configuration

Set these environment variables (or place them in a `.env` file) to configure the backend:

| Variable | Default | Description |
|---|---|---|
| `DEV_MODE` | `false` | Disables auth token requirement (set to `true` by default in local Docker) |
| `APP_TOKEN` | — | Required auth token (when `DEV_MODE=false`) |
| `ENABLED_PLATFORMS` | all | Comma-separated list of enabled platforms (e.g. `zepto,blinkit`) |
| `MAX_RADIUS_KM` | `30.0` | Maximum search radius (50.0 in DEV_MODE) |
| `PLAYWRIGHT_ENABLED` | `true` | Set to `false` to disable Playwright (disables Blinkit) |
| `DATABASE_PATH` | `data/mega.db` | Path to the SQLite store cache |
| `PROXY_URL` | — | Optional HTTP proxy URL for backend requests |
| `TRUST_FORWARDED_FOR` | `true` | Trust `X-Forwarded-For` header for rate limiting |

---

## 🐛 Troubleshooting

- **Docker Desktop not running**: Ensure Docker Desktop is open and fully started (the whale icon should be steady, not animating) before running the launchers.
- **Image pull problems**: If you get a `registry: denied` error, check your internet connection. (GHCR images must be set to Public by the repository owner).
- **Port already in use**: If `http://localhost:3000` won't open or another app is using the port, stop other applications or containers using port 3000.
- **Browser not opening / Container health failure**: Run `docker compose logs --tail=50` to see if the backend failed to start.
- **Platform data unavailable**: Quick-commerce platforms actively block scrapers. If a platform is failing, try again later or check for project updates.

For more detailed help, see [`docs/DOCKER_SETUP.md`](docs/DOCKER_SETUP.md) if it exists.



---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

<div align="center">

Made with ❤️ by [@Harsh-Gopal](https://github.com/Harsh-Gopal) | [GitHub](https://github.com/Harsh-Gopal/CartRadar)

</div>
