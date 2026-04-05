.PHONY: help install test lint format clean build up down logs

PYTHON := python3
UV := uv
PROJECT := argus

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# === Development ===

install: ## Install dependencies
	$(UV) sync

# === Running Apps ===

run-gateway: ## Run the gateway service
	$(UV) run --package argus-gateway gateway

run-cli: ## Run the CLI
	$(UV) run --package argus-cli cli

run-agents: ## Run the agents service
	$(UV) run --package argus-agents agents
	
# === Dependencies ===

add-dep: ## Add a dependency (usage: make add-dep PKG=argus-gateway DEP=fastapi)
	$(UV) add --package $(PKG) $(DEP)

add-workspace-dep: ## Add a workspace dependency (usage: make add-workspace-dep PKG=argus-gateway DEP=argus-shared)
	$(UV) add --package $(PKG) $(DEP)

remove-dep: ## Remove a dependency (usage: make remove-dep PKG=argus-gateway DEP=fastapi)
	$(UV) remove --package $(PKG) $(DEP)

lock: ## Lock dependencies
	$(UV) lock

upgrade: ## Upgrade all dependencies
	$(UV) lock --upgrade

# === Docker ===

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## View logs (usage: make logs SVC=gateway)
	docker compose logs -f $(SVC)

restart: ## Restart a service (usage: make restart SVC=gateway)
	docker compose restart $(SVC)

# === Linting & Formatting ===

lint: ## Run linter
	$(UV) run ruff check .

fmt: ## Format code
	$(UV) run ruff format .

fix: ## Fix linting issues automatically
	$(UV) run ruff check --fix .

# === Database ===

migrate: ## Create a new migration
	$(UV) run alembic revision --autogenerate -m "$(NAME)"

migrate-up: ## Apply migrations
	$(UV) run alembic upgrade head

migrate-down: ## Rollback last migration
	$(UV) run alembic downgrade -1

# === Cleanup ===

clean: ## Clean build artifacts
	rm -rf .venv .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# === Info ===

deps-tree: ## Show dependency tree
	$(UV) tree