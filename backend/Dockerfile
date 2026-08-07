FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy uv dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (including Playwright)
RUN uv sync --frozen --no-dev

# Install Playwright browser (Chromium only for Blinkit)
RUN uv run playwright install chromium

# Copy the rest of the application
COPY . .

# Ensure data directory exists for SQLite cache
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run the FastAPI app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
