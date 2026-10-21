#!/bin/sh
# Weekly cleanup of CI leftovers on steyaert-mgr, run as root by
# ci-disk-cleanup.timer. Everything deleted here gets rebuilt or
# re-downloaded on the next run that needs it.
set -eu

KUBECTL="/usr/local/bin/kubectl"

# Skip the e2e cache while an e2e run is using it (make test-e2e creates and
# deletes this namespace around every run).
if "$KUBECTL" get namespace gradpace-e2e >/dev/null 2>&1; then
  echo "gradpace-e2e namespace exists, e2e run in progress - skipping /srv/e2e-cache"
else
  # pnpm's store inside the node_modules cache keeps every old package
  # version it has ever downloaded. The next e2e run reinstalls cold
  # (about 1-2 minutes slower), then the cache is warm again.
  rm -rf /srv/e2e-cache/backend-venv /srv/e2e-cache/backend-pycache /srv/e2e-cache/frontend-node-modules
  echo "cleared /srv/e2e-cache"
fi

# GradPace runner: tool versions (Node, uv, Python) and caches untouched
# for 30 days.
RUNNER_HOME=/home/deploy
for dir in "$RUNNER_HOME/actions-runner/_work/_tool" "$RUNNER_HOME/.cache"; do
  if [ -d "$dir" ]; then
    find "$dir" -mindepth 2 -maxdepth 2 -mtime +30 -exec rm -rf {} + 2>/dev/null || true
    echo "pruned entries older than 30 days in $dir"
  fi
done

df -h / | tail -1
