# Runner image

The image the ARC runner pools run on, published as
`ghcr.io/gradpace/actions-runner`. It's the official
`ghcr.io/actions/actions-runner` image plus three tools our workflows call:

| Tool | Used by |
|---|---|
| `make` | GradPace test jobs (`make test-backend`, `make test-frontend`), Stephen-Steyaert-Projects deploys (`make k8s-deploy`) |
| `kubectl` | Stephen-Steyaert-Projects deploys. Runner pods can't use the `k3s` binary on the host, so they need their own copy. In-cluster it authenticates with the pod's service account. |
| `gh` | The build and deploy path-check jobs (`gh api .../jobs`) |

The official image already ships `git`, `curl`, `jq`, `docker` and `buildx`.

Every download is pinned to an exact version and checked against its
SHA-256. To bump one, change its `*_VERSION` and `*_SHA256` build args
together:

- Runner: tag in the `FROM` line, from [actions/runner releases](https://github.com/actions/runner/releases)
- kubectl: keep it at the cluster's Kubernetes version (`k3s --version`); checksum from `https://dl.k8s.io/release/<version>/bin/linux/amd64/kubectl.sha256`
- gh: checksum from the release's `gh_<version>_checksums.txt`

`.github/workflows/runner-image.yml` rebuilds it on any change here and
tags it `sha-<short sha>` (plus `latest` on main). Runner pools pin the
`sha-` tag.
