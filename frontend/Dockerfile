# ── Stage 1: build the React app ─────────────────────────────────────────────
FROM node:22-alpine AS builder

# pnpm via corepack (Node 22 ships corepack)
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Install deps first (cache layer)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Build
COPY . .
# Vite picks up VITE_* env vars at build time.
# VITE_API_BASE is intentionally left empty — requests to /api
# are handled by the nginx proxy, so no absolute URL is needed.
RUN pnpm build

# ── Stage 2: serve with nginx ────────────────────────────────────────────────
FROM nginx:1.27-alpine

LABEL org.opencontainers.image.source=https://github.com/Harsh-Gopal/CartRadar

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA + proxy /api to backend container
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
