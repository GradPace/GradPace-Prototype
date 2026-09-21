# syntax=docker/dockerfile:1

# ---- Stage 1: build the static bundle ----
FROM node:26-alpine AS builder

WORKDIR /app

# Node 26 no longer bundles Corepack, so it must be installed before it can be enabled.
RUN npm install -g corepack && corepack enable

# Resolve deps first so this layer is cached until the lockfile changes.
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY . .
RUN pnpm build


# ---- Stage 2: serve the bundle ----
# Just the static files behind a minimal nginx - the existing nginx-proxy
# reverse-proxies to this container via VIRTUAL_HOST/VIRTUAL_PORT, same
# pattern as the backend service in docker-compose.prod.yml.
#
# The "unprivileged" image runs as a non-root user out of the box (uid 101)
# and listens on 8080 instead of 80, since binding <1024 needs root.
FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER nginx

EXPOSE 8080
