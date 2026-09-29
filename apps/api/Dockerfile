FROM node:24-alpine

WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy monorepo config
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/api/package.json ./apps/api/

# Install dependencies
RUN pnpm install --frozen-lockfile --filter api

# Copy source
COPY apps/api ./apps/api

# Build typescript (just checking types as we use ts-node or similar in dev, but for production we'd emit. The package.json has tsc --noEmit right now, so we run via tsx or similar. Let's install tsx globally or just run via node --experimental-strip-types or similar, or better: compile it.)
# For now, we will just use `npx tsx src/index.ts` or similar since Effect 3 works well with node --experimental-strip-types.
# Actually, node 24 supports running TS files directly with --experimental-strip-types, or we can use tsx. Let's just use tsx.
RUN pnpm add -g tsx

WORKDIR /app/apps/api

EXPOSE 3000

CMD ["tsx", "src/index.ts"]
