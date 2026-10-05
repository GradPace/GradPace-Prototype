<div align="center">

# Team Copper - GradPace

[![Build and Push Backend to GHCR](https://github.com/GradPace/GradPace-Prototype/actions/workflows/backend-build-and-push.yml/badge.svg)](https://github.com/GradPace/GradPace-Prototype/actions/workflows/backend-build-and-push.yml)
[![Deploy to Production - Backend](https://github.com/GradPace/GradPace-Prototype/actions/workflows/backend-deploy.yml/badge.svg)](https://github.com/GradPace/GradPace-Prototype/actions/workflows/backend-deploy.yml)
[![Build and Push Frontend to GHCR](https://github.com/GradPace/GradPace-Prototype/actions/workflows/frontend-build-and-push.yml/badge.svg)](https://github.com/GradPace/GradPace-Prototype/actions/workflows/frontend-build-and-push.yml)
[![Deploy to Production - Frontend](https://github.com/GradPace/GradPace-Prototype/actions/workflows/frontend-deploy.yml/badge.svg)](https://github.com/GradPace/GradPace-Prototype/actions/workflows/frontend-deploy.yml)

[![pnpm latest version](https://img.shields.io/npm/v/pnpm.svg?label=latest)](https://github.com/pnpm/pnpm/releases/latest)

</div>

## Table of contents

- [What is GradPace?](#what-is-gradpace)
- [Architecture Overview](#architecture-overview)
  - [How it fits together](#how-it-fits-together)
- [Repo layout](#repo-layout)
- [Getting Started (Local Development)](#getting-started-local-development)
  - [Prerequisites](#prerequisites)
  - [1. Start the dev stack](#1-start-the-dev-stack)
  - [2. Verify](#2-verify)
  - [3. Stop the stack](#3-stop-the-stack)
- [Common Development Tasks](#common-development-tasks)
  - [Changed a database model?](#changed-a-database-model)
  - [Deploying a change?](#deploying-a-change)
  - [Adding an environment variable?](#adding-an-environment-variable)
- [Tech Stack](#tech-stack)
- [Developer Documentation](#developer-documentation)
- [Members](#members)
- [License](#license)

## What is GradPace?

GradPace helps students track and plan their path to graduation. Students
build a profile, log completed classes, certificates, and skills, and
(alumni/admin roles aside) see their own progress in one place. The backend
is Django + Django REST Framework (JWT auth, UUID-keyed custom user model),
the frontend is React + Vite, and both run as independently deployable
services behind a shared API contract - see
[backend/docs/schema.md](backend/docs/schema.md) for the data model.

---

## Architecture Overview

```
                       ┌────────────────────┐
                       │     Cloudflare     │
                       │ (DNS + DDoS proxy) │
                       └──────────┬─────────┘
                                  │ HTTPS
                    ┌─────────────▼─────────────┐
                    │   gradpace.steyaert.xyz   │
                    │ gradpace-api.steyaert.xyz │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   Traefik Ingress (k3s)   │
                    │            :443           │
                    └────────┬─────────┬────────┘
                             │         │
                     ┌───────┘         └──────┐
                     ▼                        ▼
           ┌───────────────────┐    ┌───────────────────┐
           │      frontend     │    │      backend      │
           │ nginx + React/Vite│    │    Django + DRF   │
           │       :8080       │    │       :8000       │
           └───────────────────┘    └──────┬─────┬──────┘
                                           │     │
                                     ┌─────┘     └────┐
                                     ▼                ▼
                              ┌─────────────┐  ┌─────────────┐
                              │      db     │  │     mail    │
                              │  PostgreSQL │  │   Postfix   │
                              │    :5432    │  │     :25     │
                              └─────────────┘  └─────────────┘
```

> `db` and `mail` are pinned to `steyaert-mgr` (`nodeSelector`) since they
> hold node-local state (`hostPath` volumes) that doesn't follow a pod
> across nodes. `frontend`/`backend` are stateless and scale 1-6 replicas
> across both nodes via their own HPAs. Images are built by GitHub Actions,
> pushed to GHCR, and rolled out via `kubectl set image` from a self-hosted
> runner on `steyaert-mgr` itself (see `k8s/` and the Makefile's
> `deploy-backend`/`deploy-frontend` targets).

---

### How it fits together

- **Cloudflare** sits in front of everything - handles DNS and DDoS protection
- **Traefik** is k3s's bundled ingress controller - terminates TLS and
  routes by hostname (`gradpace.steyaert.xyz` → `frontend`,
  `gradpace-api.steyaert.xyz` → `backend`)
- **frontend** is a static React/Vite bundle served by nginx; the browser
  talks to `backend`'s REST API directly (no server-side proxying through
  `frontend`)
- **backend** is Django + DRF - JWT auth, REST API, talks to `db` for all
  persistence and to `mail` for outgoing email (password resets, etc.)
- **db** is Postgres, pinned to `steyaert-mgr` (its data directory is a
  `hostPath` volume, so it can't follow the pod to another node)
- **mail** is Postfix, pinned to `steyaert-mgr` for the same reason
  (DKIM keys on `hostPath`) - `backend`'s only SMTP relay, not
  internet-facing itself

---

## Repo layout

```
prototype/
├── backend/            # Django + DRF API (uv-managed, see pyproject.toml)
│   ├── accounts/        # Custom user model, profiles, skills/certs/classes
│   ├── core/            # Healthcheck, cross-cutting views
│   ├── config/          # Settings (dev/prod split), urls, wsgi
│   └── docs/            # Sphinx docs + the auto-generated schema diagram
├── frontend/            # React + Vite SPA (pnpm-managed, see package.json)
│   └── src/
│       ├── pages/        # HomePage, LoginPage, SignupPage, Profile(Setup)Page
│       ├── components/   # Navbar, Hero, etc.
│       └── lib/api/      # apiFetch/apiGet - the REST client
├── e2e/                 # Playwright suite - runs frontend + backend together
├── k8s/                 # Production k3s manifests
│   └── e2e/              # Throwaway manifests for `make test-e2e` only -
│                          # not part of the real deploy
├── docker-compose.dev.yml  # Local dev stack (sqlite backend, Vite dev
│                           # server, both with live reload)
└── Makefile              # Every common command (`make help` lists them all)
```

Each app also has its own README with more detail:
[backend/README.md](backend/README.md),
[frontend/README.md](frontend/README.md).

---

## Getting Started (Local Development)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for `make up-dev`'s
  compose stack) - or run `backend`/`frontend` natively, see their own
  READMEs
- Python >= 3.14 + [uv](https://docs.astral.sh/uv/) (backend)
- Node.js >= 26 + [pnpm](https://pnpm.io/) (frontend) - `corepack enable`
  picks up the exact pinned version automatically

### 1. Start the dev stack

```bash
make up-dev      # backend (:8000, sqlite) + frontend (:5173, Vite HMR)
```

No separate env/config step needed - `backend/config/settings/.env.dev`
and `frontend/.env.development` are both committed with safe dev-only
defaults (see each app's README for why those two specifically are
exceptions to the `.gitignore`'d `.env.*` pattern).

### 2. Verify

| Service          | URL                              |
|------------------|-----------------------------------|
| Frontend         | http://localhost:5173              |
| Backend API      | http://localhost:8000              |
| API docs (Swagger) | http://localhost:8000/api/docs/  |

Migrations run automatically (`uv run manage.py migrate` is part of
`docker-compose.dev.yml`'s backend command) - no manual step needed.

### 3. Stop the stack

```bash
make down-dev
```

## Common Development Tasks

```bash
make test        # backend + frontend checks (lint, typecheck, unit tests)
make test-e2e    # Playwright suite against a throwaway k3s namespace
```

See `make help` for the full list (linting, formatting, logs, deploy
targets, etc) - or each app's own README for its specific commands.

### Changed a database model?

See [backend/README.md](backend/README.md#changed-a-model) -
`makemigrations` + `migrate`, review the generated migration before
committing it.

### Deploying a change?

Nothing manual - pushing to `main` with changes under `backend/` or
`frontend/` builds, tests, and deploys automatically (see the
architecture overview above, and each app's README's "Deploying"
section). `make deploy-backend TAG=sha-<short sha>` /
`make deploy-frontend TAG=...` exist for a manual redeploy of an already-
built image, if CI's auto-deploy ever needs to be re-run by hand.

### Adding an environment variable?

Add it to both `k8s/backend-configmap.yaml` (non-secret) or a
`k8s/secrets.example-*.yaml` (secret, the real value lives only in the
cluster) and the corresponding `get_secret(...)` call in
`backend/config/settings/prod.py`. For dev-only values, add them to
`backend/config/settings/.env.dev` or `frontend/.env.development`
instead - both are committed, so keep real secrets out of them.

---

## Tech Stack

- **Backend:** Django, Django REST Framework, Simple JWT, drf-spectacular,
  PostgreSQL (prod) / sqlite (dev), managed with [uv](https://docs.astral.sh/uv/)
- **Frontend:** React, Vite, Tailwind CSS, managed with [pnpm](https://pnpm.io/)
- **Testing:** pytest + pytest-django (backend), Vitest + Testing Library
  (frontend unit), Playwright (e2e)
- **Infrastructure:** k3s (2 nodes), Traefik ingress, Docker (image builds
  only - see the architecture overview above), GHCR, Cloudflare
- **CI/CD:** GitHub Actions, a self-hosted runner on the k3s control-plane
  node for test/e2e/deploy jobs

---

## Developer Documentation

- [backend/README.md](backend/README.md) - backend setup, settings, migrations, deploying
- [frontend/README.md](frontend/README.md) - frontend setup, env vars, deploying
- [backend/docs/schema.md](backend/docs/schema.md) - auto-generated ER diagram of the accounts app

---

## Members

* Stephen Steyaert - sstey001@odu.edu - Stephen-A-Steyaert, StephenSteyaertODU
* Dawson Fromm - dfrom001@odu.edu - dasunny
* Aaron Killingbeck - akill006@odu.edu - akill006
* Carlycia Mathis - cmath022@odu.edu - CScmath022
* JJ Wile - jwile012@odu.edu - GitHub: jwile012
* Nate Balcha - Email: nbalc001@odu.edu; Discord: _nate14, GitHub: Natebalcha

## License

All rights reserved - see [`LICENSE`](./LICENSE). Ownership among team
members is covered in [`TEAM_AGREEMENT.md`](./TEAM_AGREEMENT.md).
