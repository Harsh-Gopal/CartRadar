FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Playwright's install-deps requires some base utilities to run on debian
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# Copy uv dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (including Playwright)
RUN uv sync --frozen --no-dev

# Install Playwright browser (Chromium only for Blinkit)
RUN uv run playwright install chromium && uv run playwright install-deps chromium

# Copy the rest of the application
COPY . .

# Ensure data directory exists for SQLite cache
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run the FastAPI app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
