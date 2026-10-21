# Node config

Host-level config for the two k3s nodes, kept here so it's versioned.
Nothing in this folder is applied automatically - install it by hand
with the steps below.

| File | Installed at | Nodes |
|---|---|---|
| `k3s-config.yaml` | `/etc/rancher/k3s/config.yaml` | both |
| `journald-size.conf` | `/etc/systemd/journald.conf.d/size.conf` | both |
| `ci-disk-cleanup.sh` | `/usr/local/sbin/ci-disk-cleanup.sh` (mode 755) | steyaert-mgr |
| `ci-disk-cleanup.service`, `.timer` | `/etc/systemd/system/` | steyaert-mgr |

## Disk limits

| What grows | Cap |
|---|---|
| Unused container images | `k3s-config.yaml`: kubelet deletes them from 50% disk use down to 40% (default only starts at 85%). |
| e2e caches in `/srv/e2e-cache` | Wiped weekly by `ci-disk-cleanup.timer`, skipped if an e2e run is in progress. |
| GradPace runner tool versions and `~/.cache` | Entries untouched for 30 days deleted weekly by the same timer. |
| System logs | `journald-size.conf`: 500 MB. |

Runner pods from ARC don't need anything here: their workspace is deleted
with the pod when the job ends. The BuildKit cache is capped in its own
config (see the ARC manifests).

## Install

On steyaert-mgr:

```bash
sudo install -D -m 644 k3s-config.yaml /etc/rancher/k3s/config.yaml
sudo install -D -m 644 journald-size.conf /etc/systemd/journald.conf.d/size.conf
sudo install -m 755 ci-disk-cleanup.sh /usr/local/sbin/ci-disk-cleanup.sh
sudo install -m 644 ci-disk-cleanup.service ci-disk-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart systemd-journald
sudo systemctl enable --now ci-disk-cleanup.timer
sudo systemctl restart k3s   # picks up the kubelet image GC thresholds
```

On steyaert-worker:

```bash
sudo install -D -m 644 k3s-config.yaml /etc/rancher/k3s/config.yaml
sudo install -D -m 644 journald-size.conf /etc/systemd/journald.conf.d/size.conf
sudo systemctl restart systemd-journald
sudo systemctl restart k3s-agent
```

Restarting `k3s`/`k3s-agent` doesn't stop running pods, but the API is
unavailable for a few seconds on the manager.

To run the cleanup once by hand: `sudo systemctl start ci-disk-cleanup`,
then `journalctl -u ci-disk-cleanup` to see what it removed.
