.PHONY: help deploy deploy-backend deploy-frontend rollback-backend rollback-frontend up down restart logs logs-backend logs-frontend logs-db logs-mail check ruff-lint ruff-format ruff-format-check pytest test-backend lint-frontend typecheck-frontend build-frontend test-frontend test docs schema-diagram clean

# Prod runs on a Docker Swarm (two nodes) - `docker stack deploy`, not plain
# `docker compose up`, so it can honor docker-compose.prod.yml's `deploy:`
# placement constraints and actually schedule across both nodes. Dev is a
# single host with no swarm, so it stays on plain `docker compose`.
STACK = gradpace
DEV_COMPOSE = docker compose -f docker-compose.dev.yml

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Deploy/update the full stack (re-resolves latest image digests)
	docker stack deploy -c docker-compose.prod.yml $(STACK)

up-dev: ## Start dev compose
	$(DEV_COMPOSE) up -d && \
	docker image prune -af

deploy-frontend: ## Force a fresh pull + redeploy of just the frontend service
	docker service update --with-registry-auth --force $(STACK)_frontend

deploy-backend: ## Force a fresh pull + redeploy of just the backend service
	docker service update --with-registry-auth --force $(STACK)_backend

rollback-frontend: ## Roll the frontend service back to its previous version
	docker service rollback $(STACK)_frontend

rollback-backend: ## Roll the backend service back to its previous version
	docker service rollback $(STACK)_backend

down: ## Remove the entire stack
	docker stack rm $(STACK)

down-dev: ## Stop and remove services
	$(DEV_COMPOSE) down

restart: ## Force a rolling restart of every service in the stack
	docker service update --force $(STACK)_backend
	docker service update --force $(STACK)_frontend
	docker service update --force $(STACK)_db
	docker service update --force $(STACK)_mail

logs-backend: ## Tail logs from the backend service
	docker service logs -f $(STACK)_backend

logs-frontend: ## Tail logs from the frontend service
	docker service logs -f $(STACK)_frontend

logs-db: ## Tail logs from the db service
	docker service logs -f $(STACK)_db

logs-mail: ## Tail logs from the mail service
	docker service logs -f $(STACK)_mail

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

# TODO: no frontend test runner yet - once one exists, add its command here
# alongside lint/typecheck.
test-frontend: lint-frontend typecheck-frontend ## Run everything for the frontend: lint + typecheck

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
