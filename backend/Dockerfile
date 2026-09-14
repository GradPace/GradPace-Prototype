# syntax=docker/dockerfile:1

# Official uv image, Alpine variant (Python 3.14 + uv preinstalled).
ARG UV_IMAGE=ghcr.io/astral-sh/uv:python3.14-alpine

# ---- Stage 1: build the virtualenv ----
FROM ${UV_IMAGE} AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Resolve deps first so this layer is cached until the lockfile changes.
# Main deps + the "prod" group (gunicorn, psycopg); dev group excluded.
# psycopg[binary]: the pure-Python binding locates libpq via ctypes'
# find_library(), which needs ldconfig - absent on Alpine/musl, so it can't
# find libpq even when installed via apk. The binary wheel bundles libpq
# statically and sidesteps the lookup entirely.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-default-groups --group prod


# ---- Stage 2: runtime ----
FROM ${UV_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings \
    PIPELINE=production

# netcat: DB wait in the entrypoint. libpq no longer needed here - psycopg's
# binary wheel (see builder stage) bundles its own.
RUN apk add --no-cache netcat-openbsd

RUN adduser -D appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser . .

# collectstatic (run in the entrypoint) writes here as the non-root user.
RUN mkdir -p /app/staticfiles && chown appuser:appuser /app/staticfiles

RUN chmod +x entrypoint.prod.sh

USER appuser

EXPOSE 8000

# No collectstatic / staticfiles dirs: this is a JSON API and serves no static.
CMD ["./entrypoint.prod.sh"]
