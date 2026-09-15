.PHONY: help deploy deploy-backend deploy-frontend up down restart logs check ruff-lint ruff-format ruff-format-check pytest test-backend lint-frontend typecheck-frontend build-frontend test-frontend test docs clean

# No docker-compose.yml/compose.yaml exists - only the explicit dev/prod files
# below - so every docker compose call here must be pointed at one via -f.
COMPOSE = docker compose -f docker-compose.prod.yml

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Pull latest images and deploy all services
	$(COMPOSE) pull && \
	$(COMPOSE) up -d && \
	docker image prune -af

deploy-frontend: ## Pull and deploy only the frontend
	$(COMPOSE) pull frontend && \
	$(COMPOSE) up -d frontend && \
	docker image prune -af

deploy-backend: ## Pull and deploy only the backend
	$(COMPOSE) pull backend && \
	$(COMPOSE) up -d backend && \
	docker image prune -af

down: ## Stop and remove services
	$(COMPOSE) down

restart: ## Restart services
	$(COMPOSE) restart

logs: ## View logs from services
	$(COMPOSE) logs -f

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

clean: ## Clean up Python cache and Docker resources
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -r {} + 2>/dev/null || true
	rm -rf backend/docs/_build
	docker system prune -af
