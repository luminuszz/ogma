FROM node:20-alpine AS builder
WORKDIR /app
RUN npm install -g pnpm

# Copy workspace manifests to leverage Docker layer cache
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json ./apps/web/

RUN pnpm install --frozen-lockfile --filter web

# Copy source and build
COPY apps/web ./apps/web
RUN pnpm --filter web build

# --- Production stage ---
FROM nginx:alpine
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

# nginx reverse proxy config (present in build context root = apps/web)
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
