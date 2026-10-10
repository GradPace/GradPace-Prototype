.PHONY: help deploy deploy-backend deploy-frontend rollback-backend rollback-frontend up down restart logs logs-backend logs-frontend logs-db logs-mail check ruff-lint ruff-format ruff-format-check pytest test-backend lint-frontend typecheck-frontend build-frontend test-frontend-unit test-frontend test-e2e test docs schema-diagram clean

# Prod runs on k3s (see k8s/) - kubectl against that cluster, not Docker
# Swarm. Dev is still a single host with plain `docker compose`.
NAMESPACE = gradpace
DEV_COMPOSE = docker compose -f docker-compose.dev.yml
REGISTRY_IMAGE = ghcr.io/gradpace/gradpace-prototype

# deploy-frontend/deploy-backend pin to this tag instead of `:latest` so
# `kubectl set image` always sees a changed image reference. CI passes
# TAG=sha-<short sha> (see frontend-deploy.yml/backend-deploy.yml) so every
# deploy targets a distinct, unambiguous image. Defaults to latest for
# manual use.
TAG ?= latest

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Apply/update every manifest in k8s/ against the cluster
	kubectl apply -f k8s/

up-dev: ## Start dev compose
	$(DEV_COMPOSE) up -d && \
	docker image prune -af

deploy-frontend: ## Roll the frontend deployment to TAG=<tag> (defaults to latest) and wait for it to finish
	kubectl set image deployment/frontend frontend=$(REGISTRY_IMAGE)/frontend:$(TAG) -n $(NAMESPACE)
	kubectl rollout status deployment/frontend -n $(NAMESPACE)

deploy-backend: ## Roll the backend deployment to TAG=<tag> (defaults to latest) and wait for it to finish
	kubectl set image deployment/backend backend=$(REGISTRY_IMAGE)/backend:$(TAG) -n $(NAMESPACE)
	kubectl set image cronjob/flush-expired-tokens flush-expired-tokens=$(REGISTRY_IMAGE)/backend:$(TAG) -n $(NAMESPACE)
	kubectl rollout status deployment/backend -n $(NAMESPACE)

rollback-frontend: ## Roll the frontend deployment back to its previous revision
	kubectl rollout undo deployment/frontend -n $(NAMESPACE)

rollback-backend: ## Roll the backend deployment back to its previous revision
	kubectl rollout undo deployment/backend -n $(NAMESPACE)

down: ## Delete every resource in k8s/ from the cluster
	kubectl delete -f k8s/

down-dev: ## Stop and remove services
	$(DEV_COMPOSE) down

restart: ## Force a rolling restart of every deployment/statefulset in the stack
	kubectl rollout restart deployment/backend deployment/frontend deployment/mail statefulset/db -n $(NAMESPACE)

logs-backend: ## Tail logs from the backend deployment
	kubectl logs -f deployment/backend -n $(NAMESPACE)

logs-frontend: ## Tail logs from the frontend deployment
	kubectl logs -f deployment/frontend -n $(NAMESPACE)

logs-db: ## Tail logs from the db statefulset
	kubectl logs -f statefulset/db -n $(NAMESPACE)

logs-mail: ## Tail logs from the mail deployment
	kubectl logs -f deployment/mail -n $(NAMESPACE)

logs: logs-backend ## Tail logs from the backend service (see logs-frontend/logs-db/logs-mail for the others)

check: ## Run Django's system check
	cd backend && uv run manage.py check

ruff-lint: ## Run ruff's linter over the backend
	cd backend && uv run ruff check .

ruff-format: ## Reformat the backend with ruff
	cd backend && uv run ruff format .

ruff-format-check: ## Check backend formatting without changing files
	cd backend && uv run ruff format --check .

pytest: ## Run the backend test suite
	cd backend && uv run pytest

test-backend: check ruff-lint ruff-format-check pytest ## Run everything for the backend: check + lint + format check + tests

lint-frontend: ## Run eslint over the frontend
	cd frontend && pnpm lint

typecheck-frontend: ## Type-check the frontend (no build output)
	cd frontend && pnpm typecheck

build-frontend: ## Build the frontend for production (writes frontend/dist)
	cd frontend && pnpm build

test-frontend-unit: ## Run the frontend's Vitest unit/component suite
	cd frontend && pnpm test

test-frontend: lint-frontend typecheck-frontend test-frontend-unit ## Run everything for the frontend: lint + typecheck + unit tests

# Runs the dev stack as two throwaway pods in the k3s cluster (see k8s/e2e/)
# instead of docker-compose.dev.yml - this only ever runs on the self-hosted
# runner, which is the k3s control-plane node itself (steyaert-mgr), so
# hostNetwork + a hostPath mount of $(CURDIR) reaches the same
# localhost:8000/:5173 Playwright already expects, no docker daemon needed.
test-e2e: ## Run Playwright e2e tests against a throwaway k3s namespace (wipes backend/db.sqlite3 before and after)
	rm -f backend/db.sqlite3
	trap 'kubectl delete namespace gradpace-e2e --ignore-not-found --wait=true; rm -f backend/db.sqlite3' EXIT; \
	kubectl apply -f k8s/e2e/namespace.yaml && \
	sed "s#__CHECKOUT_PATH__#$(CURDIR)#g" k8s/e2e/backend-pod.yaml | kubectl apply -f - && \
	sed "s#__CHECKOUT_PATH__#$(CURDIR)#g" k8s/e2e/frontend-pod.yaml | kubectl apply -f - && \
	wait_for() { i=0; until curl -sf "$$1" >/dev/null; do i=$$((i+1)); [ $$i -ge 180 ] && echo "$$1 did not become healthy in time" >&2 && exit 1; sleep 1; done; }; \
	wait_for http://localhost:8000/core/healthcheck/ && \
	wait_for http://localhost:5173/ && \
	(cd e2e && pnpm exec playwright test)

# Local convenience only - runs both toolchains, so it needs uv AND
# node/pnpm available. CI jobs call test-backend / test-frontend separately
# since each runner only sets up the one toolchain it needs.
test: test-backend test-frontend ## Run everything: backend + frontend checks (needs both toolchains)

docs: ## Build the Sphinx docs (backend/docs/_build/html)
	cd backend && uv run --group docs sphinx-build -b html docs docs/_build/html

schema-diagram: ## Regenerate the accounts app ER diagram (backend/docs/schema.svg)
	docker compose -f docker-compose.dev.yml run --rm backend sh -c \
		"uv sync && uv run manage.py graph_models accounts --pydot -o docs/schema.svg"

clean: ## Clean up Python cache and Docker resources
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -r {} + 2>/dev/null || true
	rm -rf backend/docs/_build
	docker system prune -af
