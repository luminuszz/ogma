FROM node:24-alpine AS builder
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY . .
RUN npx turbo prune api --docker

FROM node:24-alpine AS installer
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install dependencies from pruned lockfile
COPY --from=builder /app/out/json/ .
RUN pnpm install --frozen-lockfile

# Copy pruned source
COPY --from=builder /app/out/full/ .

WORKDIR /app/apps/api
EXPOSE 3001

# Node 24 supports TypeScript natively via --experimental-strip-types
CMD ["node", "--experimental-strip-types", "src/index.ts"]
