FROM node:24-alpine
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy workspace manifests to leverage Docker layer cache
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json ./apps/web/

RUN pnpm install --frozen-lockfile --filter web

# Copy source
COPY apps/web ./apps/web
WORKDIR /app/apps/web

EXPOSE 5173

# Run Vite dev server exposed to the network
CMD ["pnpm", "dev", "--host"]
