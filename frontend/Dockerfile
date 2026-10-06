# syntax=docker/dockerfile:1

# ---- Stage 1: build the static bundle ----
FROM node:26-alpine AS builder

WORKDIR /app

# Node 26 no longer bundles Corepack, so it must be installed before it can be enabled.
RUN npm install -g corepack && corepack enable

# canvas (a devDependency, only used by vitest/jsdom - see Hero.test.tsx) has
# no prebuilt binary for musl/Alpine, so pnpm install falls back to node-gyp
# rebuild. These are node-canvas's own documented Alpine build deps for that
# to succeed; none of this survives into the final nginx stage below.
RUN apk add --no-cache python3 make g++ pkgconfig \
    cairo-dev pango-dev jpeg-dev giflib-dev librsvg-dev

# Resolve deps first so this layer is cached until the lockfile changes.
# pnpm-workspace.yaml holds the allowBuilds approval for canvas's install
# script above - without it here too, pnpm blocks that script from running
# at all (ERR_PNPM_IGNORED_BUILDS), separately from the build tools issue.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY . .

# Vite bakes import.meta.env.VITE_* values into the bundle at build time -
# must be passed as a build-arg (see frontend-build-and-push.yml), not a
# runtime env var, since it's already compiled in by the time any container
# from this image starts.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm build


# ---- Stage 2: serve the bundle ----
# Just the static files behind a minimal nginx - k8s/ingress-frontend.yaml's
# Traefik Ingress routes gradpace.steyaert.xyz to this container's :8080
# via k8s/frontend-service.yaml, same pattern as the backend's own Ingress.
#
# The "unprivileged" image runs as a non-root user out of the box (uid 101)
# and listens on 8080 instead of 80, since binding <1024 needs root.
FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER nginx

EXPOSE 8080
