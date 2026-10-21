# GradPace Frontend

React + Vite SPA. Talks to the [backend](../backend/README.md)'s REST API
directly from the browser (no server-side proxying) - see `src/lib/api/`.

## Table of contents

- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
- [Common tasks](#common-tasks)
  - [canvas and Alpine](#canvas-and-alpine)
- [e2e tests](#e2e-tests)
- [Deploying](#deploying)

## Prerequisites

- Node.js >= 26
- [pnpm](https://pnpm.io/) - the repo pins an exact version via the
  `packageManager` field in `package.json`, so `corepack enable` matches
  it automatically

## Getting started

```bash
pnpm install
pnpm dev     # http://localhost:5173, HMR
```

Or, from the repo root: `make up-dev` starts this alongside the backend
with live reload, via `docker-compose.dev.yml`.

`.env.development` is committed (no secrets - just
`VITE_API_URL=http://localhost:8000`) and loaded by Vite automatically in
dev mode. Don't re-add it to `.gitignore`'s `.env.*` sweep - Vite's own
convention treats `.env.[mode]` as a committed default, distinct from
`.env.[mode].local` for real per-developer overrides. Without it, every
API call in dev hits the literal string `undefined/api/...` (this broke
the e2e suite's signup flow once - see git history on this file).

## Common tasks

```bash
pnpm lint        # eslint
pnpm typecheck   # tsc -b, no build output
pnpm test        # vitest run - unit/component suite
pnpm build       # production bundle -> dist/
```

Or from the repo root: `make lint-frontend` / `make typecheck-frontend` /
`make test-frontend-unit` / `make build-frontend` / `make test-frontend`
(lint + typecheck + unit tests together, same as CI).

### canvas and Alpine

`canvas` is a devDependency (only used by vitest/jsdom, for
`Hero.test.tsx`'s `canvas.toDataURL` check). It has no prebuilt binary for
musl/Alpine, so installing it on an Alpine-based Node image needs its
build toolchain first - already handled for you in
`docker-compose.dev.yml`, `k8s/e2e/frontend-pod.yaml`, and
`Dockerfile`, but worth knowing if `pnpm install` ever fails with a
`node-gyp`/Python error on a fresh Alpine environment.

## e2e tests

The Playwright suite in [`../e2e/`](../e2e) runs this app against the real
backend - see the root README's "Getting started" section
(`make test-e2e`).

## Deploying

Pushing to `main` with changes under `frontend/` triggers
`.github/workflows/frontend-build-and-push.yml`: runs lint/typecheck, runs
the e2e suite, builds the production image (`Dockerfile`, bakes
`VITE_API_URL` in at build time - it's compiled into the bundle, not read
at runtime), and pushes it to GHCR. A successful push then triggers
`frontend-deploy.yml`, which rolls the new image out to the k3s cluster
via `kubectl set image` (see the root README's architecture overview and
`k8s/frontend-deployment.yaml`).
