# Runner image for the ARC runner pools (see infra/runner-image/README.md).
# The official image already has git, curl, jq, docker and buildx; this adds
# the three tools our workflows call that it doesn't ship.
FROM ghcr.io/actions/actions-runner:2.337.0

USER root

# make: GradPace's test jobs run `make test-backend` / `make test-frontend`,
# and Stephen-Steyaert-Projects' deploys run `make k8s-deploy`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends make \
 && rm -rf /var/lib/apt/lists/*

# kubectl: deploy jobs run in a pod here, so they can't use the k3s binary
# on the host. Pinned to the cluster's version; in-cluster it authenticates
# with the pod's service account, so no kubeconfig is baked in.
ARG KUBECTL_VERSION=v1.36.5
ARG KUBECTL_SHA256=33bc88a24c3b09cf55bfd59e6ca977881b61fc3f25ab65bc80c65b430248648e
RUN curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && echo "${KUBECTL_SHA256}  /usr/local/bin/kubectl" | sha256sum -c - \
 && chmod 755 /usr/local/bin/kubectl

# gh: the build/deploy path-check jobs ask the GitHub API which upstream jobs
# actually ran (`gh api .../jobs`).
ARG GH_VERSION=2.102.0
ARG GH_SHA256=bb766f710eef8ede859c18578c72c327597cd4c8a85b06001b1f3843c6019386
RUN curl -fsSLo /tmp/gh.tar.gz "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" \
 && echo "${GH_SHA256}  /tmp/gh.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/gh.tar.gz -C /tmp \
 && install -m 755 "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" /usr/local/bin/gh \
 && rm -rf /tmp/gh.tar.gz "/tmp/gh_${GH_VERSION}_linux_amd64"

USER runner
