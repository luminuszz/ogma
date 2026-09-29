FROM node:24-alpine AS builder
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY . .
RUN npx turbo prune api --docker

FROM node:24-alpine AS installer
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate

# First copy pruned lockfile and package.json's to install dependencies
COPY --from=builder /app/out/json/ .
RUN pnpm install --frozen-lockfile

# Then copy the rest of the pruned source code
COPY --from=builder /app/out/full/ .

RUN pnpm add -g tsx

WORKDIR /app/apps/api
EXPOSE 3000

CMD ["tsx", "src/index.ts"]
