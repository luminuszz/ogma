FROM node:20-alpine AS builder
WORKDIR /app
RUN npm install -g pnpm

# Copy workspace files
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json ./apps/web/

RUN pnpm install --frozen-lockfile --filter web

COPY apps/web ./apps/web
RUN pnpm --filter web build

FROM nginx:alpine
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

# Nginx config to proxy /api to backend
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
