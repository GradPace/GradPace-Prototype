.PHONY: help deploy deploy-backend deploy-frontend up down restart logs check ruff-lint ruff-format ruff-format-check pytest test docs clean

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

# TODO: once frontend/ has its own test/lint setup, check/pytest/test should
# also run it (e.g. a check-frontend / test-frontend target folded into these).

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

test: check ruff-lint ruff-format-check pytest ## Run everything: system check + lint + format check + test suite

docs: ## Build the Sphinx docs (backend/docs/_build/html)
	cd backend && uv run --group docs sphinx-build -b html docs docs/_build/html

clean: ## Clean up Python cache and Docker resources
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -r {} + 2>/dev/null || true
	rm -rf backend/docs/_build
	docker system prune -af
