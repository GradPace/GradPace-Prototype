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
  - [Loading job data](#loading-job-data)
- [Encrypted fields](#encrypted-fields)
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
and supplied by `k8s/backend-configmap.yaml` + the `k8s/examples/secrets.example-*`
files (real secrets live in the cluster, not this repo).

## Common tasks

```bash
make ruff-lint              # lint
make ruff-format            # reformat
make pytest                  # run the test suite
make test-backend            # check + lint + format-check + pytest, same as CI
make schema-docs             # regenerate docs/schema.md FK table + diagram
```

(all run from the repo root - see the root `Makefile`)

### Changed a model?

```bash
uv run manage.py makemigrations
uv run manage.py migrate
```

Review the generated migration before committing it - GradPace doesn't
squash or hand-edit migrations.

### Loading job data

The `intelligence` app holds tech occupations (BLS + O*NET), their skills,
and 400 synthetic job postings. Load them after migrating:

```bash
uv run manage.py migrate
uv run manage.py seed_jobs   # safe to rerun; --dry-run validates only
```

See [intelligence/data/README.md](intelligence/data/README.md) for where the
data comes from and how it was built.

## Encrypted fields

Sensitive columns are encrypted at rest with
[django-fernet-encrypted-fields](https://pypi.org/project/django-fernet-encrypted-fields/),
through the thin subclass in `accounts/fields.py` (it keeps `''` as `''`
instead of NULL, and drops a flag upstream sets on the shared field
instance that isn't thread-safe). Encrypted by migration
`accounts/0005_encrypt_sensitive_fields`:

| Model            | Fields                        |
|------------------|-------------------------------|
| `CustomUser`     | `first_name`, `last_name`     |
| `StudentProfile` | `major`, `uni`, `location`    |
| `TakenClass`     | `grade`                       |
| `Certificate`    | `credential_url`              |

**Limits.** The same value encrypts differently every time, so these
fields can't be filtered, sorted, searched, indexed or made unique -
`filter(major='CS')` silently matches nothing. Before encrypting another
field, check nothing queries it. `email` (login, password reset,
`unique_email_ci`), `student_id` (unique) and `Skill.name`
(`unique_together`) stay plaintext for that reason.

**Keys.** The Fernet key is derived from `SECRET_KEY` + `SALT_KEY` (PBKDF2,
100,000 iterations, once per field per process). `SALT_KEY` is a fixed dummy
in `dev.py`/`test.py`; prod reads it from the `backend-salt-key` Secret (see
`k8s/examples/secrets.example-backend-salt-key.yaml`).

- **Back up `SECRET_KEY` and `SALT_KEY` outside the cluster.** Losing
  either one loses every encrypted value. A wrong key doesn't raise either -
  the field just returns the raw ciphertext - so a bad rotation shows up as
  `gAAAAA...` strings in the API, not as errors.
- **Rotating the salt:** set the Secret to `new-salt,old-salt` (newest
  first). Old rows still decrypt; rows are re-encrypted with the new salt
  as they're saved.
- **Rotating `SECRET_KEY`:** put the old value in `SECRET_KEY_FALLBACKS`
  (comma-separated, read by `prod.py`) first - without it nothing decrypts.

**Uploaded files** aren't stored. The one upload so far, the transcript
(`POST /api/auth/profile/transcript/`, `accounts/transcript.py`), is parsed in
memory and only the resulting `TakenClass` rows are saved, so their `grade`
is encrypted like any other. If an upload ever does need keeping, encrypt the
bytes with `cryptography.fernet.Fernet` in a small custom `Storage` subclass.
backend pods have no persistent volume, so it can't be the local filesystem
either. Don't use `django-encrypted-fields-and-files` for it: it installs a
module also named `encrypted_fields`.

## Deploying

Pushing to `main` with changes under `backend/` triggers
`.github/workflows/backend-build-and-push.yml`: runs the test suite, runs
the e2e suite (`.github/workflows/e2e-tests.yml`) against a throwaway dev
stack, builds the image, and pushes it to GHCR. A successful push then
triggers `backend-deploy.yml`, which rolls the new image out to the k3s
cluster via `kubectl set image` (see the root README's architecture
overview and `k8s/backend-deployment.yaml`).
