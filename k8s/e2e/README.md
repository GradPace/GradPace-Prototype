# e2e throwaway pods

`namespace.yaml`/`backend-pod.yaml`/`frontend-pod.yaml` stand up the dev
stack as two pods in k3s for `make test-e2e` (see the Makefile and
`.github/workflows/e2e-tests.yml`). They're applied and torn down around
every e2e run - nothing here is part of the real prod stack in `k8s/`.

## One-time host setup

`e2e-tests.yml` runs `pnpm exec playwright install chromium` without
`--with-deps`, since `--with-deps` needs root (`apt-get install`) and the
self-hosted runner's `deploy` user has no `sudo`. Chromium's OS-level
libraries need to be installed once, as root, directly on the runner host
(`steyaert-mgr`) instead:

```bash
# From the repo root - uses e2e/package.json's @playwright/test version.
sudo npx --yes playwright@"$(node -p "require('./e2e/package.json').devDependencies['@playwright/test']")" install-deps chromium
```

Dependabot keeps that version up to date, so re-run this after it bumps
Playwright, after an OS upgrade on that host, or whenever CI starts failing
with missing shared library errors (as opposed to the auth/permission error
`--with-deps` itself produces without root).
