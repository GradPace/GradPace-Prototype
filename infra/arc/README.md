# Actions Runner Controller (ARC)

Runs GitHub Actions jobs for GradPace and Stephen-Steyaert-Projects as
pods in this k3s cluster. See the CI runners plan for the reasoning and
sizing.

| File | What |
|---|---|
| `namespaces.yaml` | `arc-systems` (controller), `arc-runners` (pools, listeners, secrets) |
| `priorityclass.yaml` | `ci-low`: every CI pod's priority - evicted first, never evicts others |
| `controller.yaml` | The ARC controller, installed by k3s's built-in Helm controller |

Nothing here is applied by `make deploy` (`kubectl apply -f k8s/` doesn't
reach this folder).

## Apply

From a machine with `kubectl` access to the cluster:

```bash
kubectl apply -f infra/arc/namespaces.yaml -f infra/arc/priorityclass.yaml
kubectl apply -f infra/arc/controller.yaml
kubectl -n arc-systems rollout status deploy -l app.kubernetes.io/name=gha-rs-controller
```

## GitHub App secrets

One GitHub App per org, each installed on all of its repos with
"Self-hosted runners: read and write" (org) and "Metadata: read-only"
(repo). The IDs aren't secret; the private keys are, and never go in this
repo.

| Org | App | App ID | Installation ID | Secret |
|---|---|---|---|---|
| GradPace | `gp-arc` | 5203432 | 168303170 | `gp-arc-github-app` |
| Stephen-Steyaert-Projects | `stephen-arc` | 5203504 | 168303981 | `stephen-arc-github-app` |

Create each secret straight from the downloaded `.pem`, so the key is
never written anywhere else:

```bash
kubectl -n arc-runners create secret generic gp-arc-github-app \
  --from-literal=github_app_id=5203432 \
  --from-literal=github_app_installation_id=168303170 \
  --from-file=github_app_private_key=gp-arc.<date>.private-key.pem
```

Same for `stephen-arc-github-app` with its own IDs and `.pem`. To rotate a
key: generate a new one in the app's settings, delete and recreate the
secret, then delete the old key in GitHub.
