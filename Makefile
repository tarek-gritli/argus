.PHONY: help \
	install install-python install-web \
	run-gateway run-agents run-cli run-web \
	add-dep remove-dep lock upgrade \
	build up down logs restart \
	lint fmt fix \
	migrate migrate-up migrate-down \
	test clean deps-tree

PYTHON := python3
UV     := uv
PNPM   := pnpm

# ============================================================
# Help
# ============================================================

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Install
# ============================================================

install: install-python install-web ## Install all dependencies

install-python: ## Install Python dependencies
	$(UV) sync

install-web: ## Install web dependencies
	cd apps/web && $(PNPM) install

# ============================================================
# Run
# ============================================================

run-gateway: ## Run the gateway service
	$(UV) run --package gateway gateway

run-agents: ## Run the agents service
	$(UV) run --package agents agents

run-cli: ## Run the CLI
	$(UV) run --package cli cli

run-web: ## Run the web dev server
	cd apps/web && $(PNPM) dev

# ============================================================
# Dependencies
# ============================================================

add-dep: ## Add external dep (usage: make add-dep PKG=gateway DEP=fastapi)
	$(UV) add --package $(PKG) $(DEP)

remove-dep: ## Remove a dep (usage: make remove-dep PKG=gateway DEP=fastapi)
	$(UV) remove --package $(PKG) $(DEP)

lock: ## Lock dependencies
	$(UV) lock

upgrade: ## Upgrade all dependencies to latest
	$(UV) lock --upgrade

# ============================================================
# Docker
# ============================================================

build: ## Build all Docker images
	docker compose build

up: ## Start all services in background
	docker compose up -d

down: ## Stop all services
	docker compose down

down-v: ## Stop all services and delete volumes
	docker compose down -v

logs: ## Tail logs (usage: make logs SVC=gateway)
	docker compose logs -f $(SVC)

restart: ## Restart a service (usage: make restart SVC=gateway)
	docker compose restart $(SVC)

# ============================================================
# Lint & Format
# ============================================================

lint: ## Check for lint errors
	$(UV) run ruff check .

fmt: ## Format code
	$(UV) run ruff format .

fix: ## Auto-fix lint errors
	$(UV) run ruff check --fix .

# ============================================================
# Database
# ============================================================

migrate: ## Create migration (usage: make migrate NAME="add users table")
	$(UV) run alembic revision --autogenerate -m "$(NAME)"

migrate-up: ## Apply all pending migrations
	$(UV) run alembic upgrade head

migrate-down: ## Rollback last migration
	$(UV) run alembic downgrade -1

migrate-history: ## Show migration history
	$(UV) run alembic history --verbose

# ============================================================
# Tests
# ============================================================

test: ## Run all tests
	$(UV) run pytest tests/

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/

test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration/

test-cov: ## Run tests with coverage report
	$(UV) run pytest tests/ --cov --cov-report=html

# ============================================================
# Cleanup
# ============================================================

clean: ## Remove all build artifacts and caches
	rm -rf .venv .pytest_cache .ruff_cache htmlcov .coverage build dist
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	cd apps/web && rm -rf .next out node_modules

# ============================================================
# Info
# ============================================================

deps-tree: ## Show Python dependency tree
	$(UV) tree