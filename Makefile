# PropIQ Makefile
# ================
# Common development commands. Run from the project root.
#
# Usage:
#   make setup       → copy .env.example, install all dependencies
#   make db-up       → start postgres + redis via Docker
#   make migrate     → run alembic migrations
#   make seed        → populate database with test data
#   make backend     → start FastAPI dev server
#   make frontend    → start Vite dev server
#   make test        → run pytest suite
#   make lint        → lint backend (ruff) and frontend (eslint)
#   make clean       → remove build artifacts and caches

.PHONY: setup db-up db-down migrate seed backend frontend test lint \
        type-check format clean docker-up docker-down logs help

# ─── Configuration ────────────────────────────────────────────────────────────

BACKEND_DIR  := backend
FRONTEND_DIR := frontend
PYTHON       := python
PIP          := pip
PYTEST       := pytest
UVICORN      := uvicorn
NPM          := npm

# ─── Setup ────────────────────────────────────────────────────────────────────

setup: ## Copy .env.example → .env and install all dependencies
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example"; \
		echo "  → Open .env and set SECRET_KEY, POSTGRES_PASSWORD, ANTHROPIC_API_KEY"; \
	else \
		echo "  .env already exists, skipping copy"; \
	fi
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt
	cd $(FRONTEND_DIR) && $(NPM) install
	@echo "✓ Setup complete. Run 'make db-up && make migrate && make seed' to initialise the database."

# ─── Database ─────────────────────────────────────────────────────────────────

db-up: ## Start PostgreSQL and Redis via Docker Compose
	docker compose up -d postgres redis
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec postgres pg_isready -U propiq -d propiq > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "✓ Postgres ready."

db-down: ## Stop and remove database containers (data volumes preserved)
	docker compose stop postgres redis
	docker compose rm -f postgres redis

migrate: ## Run Alembic database migrations (alembic upgrade head)
	cd $(BACKEND_DIR) && alembic upgrade head

migrate-down: ## Rollback one migration step
	cd $(BACKEND_DIR) && alembic downgrade -1

seed: ## Populate database with realistic test data (25 projects, 5 developers)
	cd $(BACKEND_DIR) && $(PYTHON) -m app.seed_data

# ─── Development servers ──────────────────────────────────────────────────────

backend: ## Start FastAPI backend with hot reload (port 8000)
	cd $(BACKEND_DIR) && $(UVICORN) app.main:app --reload --port 8000

frontend: ## Start Vite frontend dev server (port 5173)
	cd $(FRONTEND_DIR) && $(NPM) run dev

dev: ## Start both backend and frontend in parallel (requires GNU parallel or tmux)
	@echo "Starting backend and frontend..."
	@trap 'kill 0' SIGINT; \
		(cd $(BACKEND_DIR) && $(UVICORN) app.main:app --reload --port 8000) & \
		(cd $(FRONTEND_DIR) && $(NPM) run dev) & \
		wait

# ─── Docker (full stack) ──────────────────────────────────────────────────────

docker-up: ## Start all services via Docker Compose (postgres, redis, backend, frontend)
	docker compose up -d
	@echo "✓ All services started."
	@echo "  Frontend:  http://localhost:5173"
	@echo "  Backend:   http://localhost:8000"
	@echo "  Docs:      http://localhost:8000/docs"
	@echo "  Adminer:   http://localhost:8080"

docker-down: ## Stop all Docker Compose services
	docker compose down

docker-seed: ## Seed database inside Docker container
	docker compose exec backend python -m app.seed_data

logs: ## Tail logs from all Docker Compose services
	docker compose logs -f

logs-backend: ## Tail backend logs only
	docker compose logs -f backend

# ─── Testing ──────────────────────────────────────────────────────────────────

test: ## Run the full pytest test suite with verbose output
	cd $(BACKEND_DIR) && $(PYTEST) tests/ -v

test-cov: ## Run tests with coverage report
	cd $(BACKEND_DIR) && $(PYTEST) tests/ --cov=app --cov-report=term-missing --cov-report=html:htmlcov -v
	@echo "Coverage report: backend/htmlcov/index.html"

test-risk: ## Run only risk engine unit tests
	cd $(BACKEND_DIR) && $(PYTEST) tests/test_risk_engine.py -v

test-api: ## Run only API integration tests
	cd $(BACKEND_DIR) && $(PYTEST) tests/test_api_projects.py tests/test_auth.py -v

# ─── Linting & formatting ─────────────────────────────────────────────────────

lint: ## Lint backend (ruff) and frontend (eslint)
	cd $(BACKEND_DIR) && ruff check app/ tests/
	cd $(FRONTEND_DIR) && $(NPM) run lint

format: ## Auto-format backend code with ruff and black
	cd $(BACKEND_DIR) && ruff check --fix app/ tests/
	cd $(BACKEND_DIR) && black app/ tests/

type-check: ## Run mypy type checking on backend
	cd $(BACKEND_DIR) && mypy app/ --ignore-missing-imports

# ─── Build ────────────────────────────────────────────────────────────────────

build-frontend: ## Build frontend for production
	cd $(FRONTEND_DIR) && $(NPM) run build

# ─── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, and __pycache__
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/.vite 2>/dev/null || true
	@echo "✓ Cleaned."

# ─── Utilities ────────────────────────────────────────────────────────────────

gen-secret: ## Generate a secure SECRET_KEY value
	@$(PYTHON) -c "import secrets; print(secrets.token_hex(32))"

health: ## Check that the backend is running and healthy
	@curl -sf http://localhost:8000/health | python -m json.tool || echo "Backend not reachable."

help: ## Show this help message
	@echo "PropIQ Makefile — available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

.DEFAULT_GOAL := help
