# Backend optimizations

Findings from a review of the backend on `main` (October 2026). Nothing here
has been implemented yet. Part 1 is framework config (Django/DRF settings)
and should go first: it's cheap, and some items make Part 2 easier. Part 2 is
app-level and infra fixes.

Paths are relative to `backend/` unless noted.

## Summary

| # | Change | Effort | Risk | Frontend impact |
|---|--------|--------|------|-----------------|
| 1.1 | JSON-only renderer in prod | Tiny | Low | None |
| 1.2 | JSON-only parser | Tiny | Low | None |
| 1.3 | Throttle auth endpoints | Medium | Low | 429s on abuse |
| 1.4 | Cache the OpenAPI schema | Tiny | Low | None |
| 1.5 | Default pagination | Small | Medium | Response shape changes |
| 2.1 | Send reset emails outside the request | Small | Low | None |
| 2.2 | Case-insensitive unique email | Medium | Medium | None |
| 2.3 | Flush expired JWTs on a schedule | Small | Low | None |
| 2.4 | Bulk-blacklist tokens | Tiny | Low | None |
| 2.5 | Capacity for password hashing | Small | Low | None |
| 2.6 | Minor cleanups | Tiny | Low | None |

**Suggested order:** 1.1, 1.2, 1.4, then 2.1 and 2.3 (with 2.4), then 1.3 once
the cache is decided, then the rest.

---

## Part 1: Django / DRF configuration

### 1.1 Turn off the browsable API in prod

`REST_FRAMEWORK` (`config/settings/base.py:120`) doesn't set
`DEFAULT_RENDERER_CLASSES`, so DRF's default applies, and that includes
`BrowsableAPIRenderer`. Any browser hitting an endpoint gets a full HTML page
rendered from templates, and the whole API can be clicked through publicly.
The frontend only ever needs JSON.

```python
# config/settings/prod.py
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer']
```

Keep the browsable API in dev for poking around locally.

### 1.2 Accept only JSON request bodies

`DEFAULT_PARSER_CLASSES` isn't set either, so every endpoint also accepts
form-encoded and multipart bodies. Nothing uploads files, so JSON-only skips
needless parsing work and leaves less input to handle.

```python
'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
```

### 1.3 Throttle the auth endpoints

Password hashing is deliberately CPU-heavy, and nothing limits how often
login, register, refresh or password reset can be called. A burst of login
attempts can pin the pod's CPU (see 2.5). Throttling also slows down anyone
exploiting the reset timing leak (see 2.1).

- Add `rest_framework.throttling.ScopedRateThrottle` with per-scope rates,
  e.g. `'login': '10/min'`, `'register': '5/min'`, `'password_reset': '5/hour'`.
- Set `throttle_scope` on those views. Login and refresh are simplejwt's
  `TokenObtainPairView` / `TokenRefreshView` (`accounts/urls.py`), so subclass
  them to set the scope.
- **Decision needed: which cache.** DRF counts requests in Django's cache, and
  no `CACHES` is configured, so it's the default in-process cache. That means
  counts are per worker and reset when a pod restarts. It's still useful, but
  for real limits across pods use a shared cache: Redis, or Django's database
  cache (`DatabaseCache`, no new service needed).

### 1.4 Cache the OpenAPI schema

`/api/schema/` (`config/urls.py:9`) is public (drf-spectacular's default
`SERVE_PERMISSIONS`) and walks every view and serializer to regenerate the
schema on every request, which makes it the most expensive GET we serve.
Either:

- wrap it in `cache_page(60 * 60)`, since the schema only changes on deploy, or
- stop serving `/api/schema/` and `/api/docs/` in prod if only the team uses them.

### 1.5 Default pagination

List endpoints (taken classes, certificates, skills) return every row. That's
fine at per-student sizes today, but setting it globally means every future
list endpoint (e.g. an admin-wide one) is paginated automatically.

```python
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
'PAGE_SIZE': 50,
```

**Frontend impact:** responses become `{count, next, previous, results}`
instead of a bare list, so the frontend needs updating in the same PR.

### Not recommended: switching password hashers

Argon2 is a security choice, not a speedup: it's deliberately slow too. The
CPU fix for auth is throttling (1.3) plus capacity (2.5).

---

## Part 2: App-level and infrastructure

### 2.1 Send password-reset emails outside the request

`PasswordResetRequestView` (`accounts/views.py:103`) calls `email.send()`
(line 136) before responding.

- **Speed:** every reset request waits on the mail server.
- **Account-enumeration leak:** a registered email gets a slow response while
  an unknown one returns 200 instantly. Timing the endpoint reveals which emails
  have accounts, which is what that view's docstring says it prevents.
- **Thread starvation:** `MAILERS` (`config/settings/prod.py:105`) has no
  timeout. A hung mail server can hold one of the pod's 4 request threads
  while using almost no CPU, so the autoscaler (CPU-based) won't add pods.

**Fix:** send the email in the background (a thread is enough at our scale, a
task queue later) and set a connection timeout on the mailer.

### 2.2 Case-insensitive unique constraint on email

Registration (`accounts/serializers/auth.py`, `validate_email`) and password
reset look users up with `email__iexact`. In Postgres that becomes an
uppercase comparison, which the plain unique index on `email`
(`accounts/models.py:42`) can't use, so each lookup scans the users table.

That index is also case-sensitive, so two concurrent registrations for
`Foo@x.com` and `foo@x.com` can both pass the serializer's `.exists()` check
and both insert. A later reset request for either address would then crash
with `MultipleObjectsReturned`.

**Fix:** add `UniqueConstraint(Lower('email'), name='unique_email_ci')` to
`CustomUser.Meta`. It speeds up the lookups and closes the race in one
change. **Before migrating, check prod for existing case-only duplicates**,
since the migration fails if any exist.

### 2.3 Flush expired JWTs on a schedule

simplejwt records every issued refresh token in `OutstandingToken`, and with
`ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` every refresh adds rows.
Nothing cleans them up: there's no CronJob in `k8s/` and the deploy workflow
doesn't do it either, so both tables only ever grow.

**Fix:** a daily k8s CronJob running `manage.py flushexpiredtokens` (ships
with simplejwt), using the backend image and env.

### 2.4 Bulk-blacklist tokens on password change/reset

`_blacklist_all_outstanding_tokens` (`accounts/views.py:37`) runs one
`get_or_create` per outstanding token, i.e. two queries per token, on every
password change and reset.

```python
outstanding = OutstandingToken.objects.filter(user=user)
BlacklistedToken.objects.bulk_create(
    [BlacklistedToken(token=t) for t in outstanding], ignore_conflicts=True
)
```

2.3 also keeps that list short.

### 2.5 Capacity for password hashing

Each pod runs 1 Gunicorn worker with 4 threads (`entrypoint.prod.sh`), with a
500m CPU limit (`k8s/backend-deployment.yaml`), and the autoscaler starts at 1
replica (`k8s/backend-hpa.yaml`). Python's GIL lets only one thread hash a
password at a time, so concurrent logins and registrations effectively queue.

**Fix:** set `minReplicas: 2`, or run 2 workers per pod, so hashing actually
runs in parallel. Size it against the CI runner budget on the worker node.

The connection-count comment in `config/settings/prod.py:58` says "3 backend
replicas x 4 threads", but the autoscaler allows 1–6 replicas. 6 x 4 = 24
connections is still well under Postgres's default limit of 100, so this is
only an outdated comment.

### 2.6 Minor cleanups

- **Role lookup on every registration:** `RegisterSerializer.create`
  (`accounts/serializers/auth.py:59`) calls `Role.objects.get_or_create`, but
  migration `0002_seed_roles` already creates the roles, so a plain `get` is
  enough.
- **Slow first password check:** `NoDictionaryWordValidator`'s word list
  (`accounts/validators.py:58`, `lru_cache`) loads on the first password check
  in each worker, so that request is slow. It could be warmed at startup
  (e.g. in `AccountsConfig.ready()`).
