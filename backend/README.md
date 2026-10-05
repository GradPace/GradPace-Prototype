# GradPace Backend

Django + Django REST Framework API: JWT auth, a UUID-keyed custom user
model, and student profiles (classes taken, certificates, skills). See
[docs/schema.md](docs/schema.md) for the full data model.

## Table of contents

- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
- [Settings](#settings)
- [Common tasks](#common-tasks)
  - [Changed a model?](#changed-a-model)
- [Deploying](#deploying)

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) - manages the virtualenv and dependencies,
  no separate `pip install` step needed

## Getting started

```bash
uv sync                      # installs dependencies into .venv
uv run manage.py migrate     # sqlite by default in dev - see config/settings/.env.dev
uv run manage.py runserver   # http://localhost:8000
```

Or, from the repo root: `make up-dev` starts this alongside the frontend
with live reload, via `docker-compose.dev.yml`.

With the server running:

- `http://localhost:8000/api/docs/` - interactive Swagger UI (drf-spectacular)
- `http://localhost:8000/core/healthcheck/` - liveness check (no DB touched)

## Settings

`config/settings/__init__.py` picks a module based on the `PIPELINE` env var:

| `PIPELINE`             | Module           | Notes                                  |
|-------------------------|------------------|-----------------------------------------|
| unset (default)          | `dev.py`         | sqlite, `DEBUG=True`, console email      |
| `production`             | `prod.py`        | Postgres, gunicorn, real SMTP via `mail` |
| `test`                   | (pytest-django)  | used automatically by `pytest`/`make pytest` |

`config/settings/.env.dev` is committed (no secrets) and loaded by `dev.py`.
Prod's env vars are documented inline in `prod.py`'s `get_secret(...)` calls
and supplied by `k8s/backend-configmap.yaml` + the `k8s/secrets.example-*`
files (real secrets live in the cluster, not this repo).

## Common tasks

```bash
make ruff-lint              # lint
make ruff-format            # reformat
make pytest                  # run the test suite
make test-backend            # check + lint + format-check + pytest, same as CI
make schema-diagram           # regenerate docs/schema.svg
```

(all run from the repo root - see the root `Makefile`)

### Changed a model?

```bash
uv run manage.py makemigrations
uv run manage.py migrate
```

Review the generated migration before committing it - GradPace doesn't
squash or hand-edit migrations.

## Deploying

Pushing to `main` with changes under `backend/` triggers
`.github/workflows/backend-build-and-push.yml`: runs the test suite, runs
the e2e suite (`.github/workflows/e2e-tests.yml`) against a throwaway dev
stack, builds the image, and pushes it to GHCR. A successful push then
triggers `backend-deploy.yml`, which rolls the new image out to the k3s
cluster via `kubectl set image` (see the root README's architecture
overview and `k8s/backend-deployment.yaml`).
