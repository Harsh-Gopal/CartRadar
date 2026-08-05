# Running Cart Radar Locally

A step-by-step guide to get the app running on your own machine — from
scratch, no prior setup assumed. Works on **macOS**, **Linux**, and **Windows**.

When you're done you'll have the app open at **http://localhost:5173**.

> ⚠️ **You need an Indian internet connection.**
> Zepto, Swiggy Instamart and BigBasket only answer requests from Indian IP
> addresses. If you're in India you're all set. If you're outside India (or on
> a non-Indian VPN) searches will fail — see
> [Optional: proxy setup](#optional-proxy-setup-outside-india) below.

---

## What you need (3 tools)

| Tool | What it's for |
|---|---|
| **git** | Download the code |
| **uv** | Runs the Python backend (installs the right Python version for you) |
| **Node.js + pnpm** | Runs the React frontend |

You don't need to install Python manually — `uv` handles that.

---

## Step 1 — Install the tools

Pick your OS and run the commands below, then **close and reopen your
terminal** afterwards.

### 🍎 macOS

```bash
# Install Homebrew first if you don't have it (https://brew.sh):
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install everything at once:
brew install git uv node pnpm
```

### 🐧 Linux (Debian / Ubuntu)

```bash
# 1. git + curl
sudo apt update && sudo apt install -y git curl

# 2. uv (Python runner)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. pnpm (frontend runner)
curl -fsSL https://get.pnpm.io/install.sh | sh -

# --- close and reopen your terminal here, then: ---

# 4. Node.js (pnpm can install it for you)
pnpm env use --global lts
```

### 🪟 Windows

Open **PowerShell** (winget is built into Windows 10/11) and run:

```powershell
winget install -e --id Git.Git
winget install -e --id astral-sh.uv
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id pnpm.pnpm
```

Then **close and reopen PowerShell**.

> 💡 If you have **WSL** or **Git Bash**, follow the Linux steps instead and
> use the single `./dev.sh` command in Step 3.

---

## Step 2 — Get the code

```bash
git clone https://github.com/Harsh-Gopal/CartRadar.git
cd CartRadar/cart-radar
```

---

## Step 3 — Start the app

### 🚀 One command (macOS / Linux / WSL)

```bash
./dev.sh
```

This single script:
1. Installs backend Python dependencies (`uv sync`)
2. Installs frontend Node dependencies (`pnpm install`)
3. Starts the FastAPI backend on **port 8000**
4. Starts the Vite dev server on **port 5173**
5. Waits for the backend to be ready before opening the frontend

Press **Ctrl+C** to stop both services.

---

### 🪟 Windows (manual steps)

Open **two terminal windows** side by side.

**Terminal 1 — Backend:**
```powershell
cd CartRadar\cart-radar\backend
uv sync
$env:DEV_MODE="true"; $env:ENABLED_PLATFORMS="zepto,swiggy,bigbasket,blinkit,bbnow"; uv run uvicorn app.main:app --port 8000 --reload
```

**Terminal 2 — Frontend:**
```powershell
cd CartRadar\cart-radar\frontend
pnpm install
pnpm dev
```

---

## Step 4 — Open in your browser

Navigate to **[http://localhost:5173](http://localhost:5173)**

---

## Optional: proxy setup (outside India)

If you're not on an Indian IP, quick-commerce platforms will block requests
with HTTP 403 / empty results.

1. Get an Indian residential proxy URL (e.g. from Oxylabs, Bright Data, or
   a trusted provider).
2. Create a `.env` file in the `cart-radar/` directory:

   ```bash
   PROXY_URL=http://user:pass@your-proxy-host:port
   ```

3. `dev.sh` automatically loads this file — just restart with `./dev.sh`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `./dev.sh: Permission denied` | Run `chmod +x dev.sh` first |
| `uv: command not found` | Close and reopen your terminal after install |
| `pnpm: command not found` | Close and reopen your terminal after install |
| Port 8000 already in use | Stop the other process: `lsof -ti:8000 \| xargs kill` |
| Port 5173 already in use | Stop the other process: `lsof -ti:5173 \| xargs kill` |
| Searches return "Not found" | Check you're on an Indian IP (see proxy section above) |
| BigBasket shows no results | BigBasket has Akamai bot protection — try with `PROXY_URL` set |

---

## Environment variables (optional)

All variables have sensible defaults for local dev. `DEV_MODE=true` (set
automatically by `dev.sh`) lifts rate limits and radius caps so you can test
freely.

| Variable | Default | Description |
|---|---|---|
| `DEV_MODE` | `false` | Disables auth + lifts rate limits |
| `APP_TOKEN` | — | Required auth token (when `DEV_MODE=false`) |
| `MAX_RADIUS_KM` | `50` | Maximum search radius in km |
| `SWEEP_SPACING_KM` | `2.0` | Hex-grid probe spacing |
| `MAX_CONCURRENT` | `5` | Max concurrent platform requests |
| `RATE_LIMIT_RPM` | `10` | Max requests / minute / IP |
| `RATE_LIMIT_DAILY` | `200` | Max requests / day / IP |
| `ENABLED_PLATFORMS` | all | Comma-separated list of active platforms |
| `PROXY_URL` | — | Optional HTTP proxy for requests |
