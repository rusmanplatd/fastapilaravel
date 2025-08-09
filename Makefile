# FastAPI Laravel Makefile

# Python and environment settings
PYTHON := python3
PIP := pip
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

# Project settings
PROJECT_NAME := fastapi-laravel
SRC_DIR := .


# Help target
.PHONY: help
help: ## Show this help message
	@echo "$(PROJECT_NAME) - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment setup
.PHONY: install
install: ## Install dependencies
	$(PIP) install -r requirements.txt

.PHONY: install-dev
install-dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install black isort pre-commit

.PHONY: venv
venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

# Type checking
.PHONY: type-check
type-check: ## Run mypy type checking
	$(PYTHON) scripts/type_check.py

.PHONY: type-check-strict
type-check-strict: ## Run strict mypy type checking with enhanced rules
	$(PYTHON) scripts/type_check_strict.py --level strict

.PHONY: type-check-progressive
type-check-progressive: ## Run progressive type checking (all strictness levels)
	$(PYTHON) scripts/type_check_strict.py --progressive

.PHONY: type-check-extreme
type-check-extreme: ## Run extreme strict type checking
	$(PYTHON) scripts/type_check_strict.py --level extreme

.PHONY: type-check-module
type-check-module: ## Run type checking on specific module (usage: make type-check-module MODULE=app/Http/Controllers)
	$(PYTHON) scripts/type_check_strict.py --module $(MODULE) --level strict

.PHONY: type-coverage
type-coverage: ## Generate type coverage report
	mypy --config-file=mypy.ini --html-report=type_coverage $(SRC_DIR)
	@echo "Type coverage report generated in type_coverage/"

.PHONY: type-check-core
type-check-core: ## Run type checking on core modules
	$(PYTHON) scripts/strict_type_check.py

.PHONY: clean-type-ignores
clean-type-ignores: ## Clean up unused type: ignore comments
	$(PYTHON) scripts/clean_unused_ignores.py

# Code quality
.PHONY: format
format: ## Format code with black and isort
	black --line-length 100 $(SRC_DIR)
	isort --profile black --line-length 100 $(SRC_DIR)

.PHONY: format-check
format-check: ## Check code formatting
	black --check --line-length 100 $(SRC_DIR)
	isort --check-only --profile black --line-length 100 $(SRC_DIR)

.PHONY: lint
lint: ## Run all linting checks
	$(MAKE) format-check
	$(MAKE) type-check

# Artisan command
.PHONY: art
art: ## Run Artisan commands (e.g., make art CMD="list")
	@if [ -z "$(CMD)" ]; then \
		$(PYTHON) artisan.py list; \
	else \
		$(PYTHON) artisan.py $(CMD); \
	fi

# Development server
.PHONY: dev
dev: ## Start development server
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

.PHONY: dev-debug
dev-debug: ## Start development server with debug logging
	uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Testing (placeholder for future tests)
.PHONY: test
test: ## Run tests (to be implemented)
	@echo "Tests not yet implemented"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage (to be implemented)
	@echo "Test coverage not yet implemented"

# Docker commands
.PHONY: docker-build
docker-build: ## Build Docker image
	docker build -t $(PROJECT_NAME) .

.PHONY: docker-run
docker-run: ## Run Docker container
	docker run -d -p 8000:8000 --name $(PROJECT_NAME)-container $(PROJECT_NAME)

.PHONY: docker-up
docker-up: ## Start all services with docker-compose
	docker-compose up -d

.PHONY: docker-down
docker-down: ## Stop all services
	docker-compose down

.PHONY: docker-restart
docker-restart: ## Restart all services
	docker-compose restart

.PHONY: docker-logs
docker-logs: ## View logs from all services
	docker-compose logs -f

.PHONY: docker-logs-app
docker-logs-app: ## View logs from app service only
	docker-compose logs -f app

.PHONY: docker-shell
docker-shell: ## Access shell in running app container
	docker-compose exec app /bin/bash

.PHONY: docker-clean
docker-clean: ## Clean up Docker containers and images
	docker-compose down -v --remove-orphans
	docker system prune -f

.PHONY: docker-rebuild
docker-rebuild: ## Rebuild and restart services
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

.PHONY: docker-status
docker-status: ## Show status of all containers
	docker-compose ps

# Cleanup
.PHONY: clean
clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .mypy_cache/
	rm -rf type_coverage/
	rm -rf dist/
	rm -rf build/

.PHONY: clean-all
clean-all: clean ## Clean up everything including venv
	rm -rf $(VENV)

# Git hooks
.PHONY: install-hooks
install-hooks: ## Install pre-commit hooks
	pre-commit install

# CI/CD simulation
.PHONY: ci
ci: ## Run CI pipeline locally
	$(MAKE) format-check
	$(MAKE) type-check
	$(MAKE) test
	@echo "✅ All CI checks passed!"

# Project info
.PHONY: info
info: ## Show project information
	@echo "Project: $(PROJECT_NAME)"
	@echo "Python: $(shell python --version)"
	@echo "Pip: $(shell pip --version)"
	@echo "MyPy: $(shell mypy --version)"
	@echo "FastAPI: $(shell python -c 'import fastapi; print(f\"FastAPI {fastapi.__version__}\")')"
# Database Operations
.PHONY: db-seed
db-seed: ## Seed all default data (users, permissions, oauth2)
	$(PYTHON) database/seeders/DatabaseSeeder.py

.PHONY: db-seed-oauth2
db-seed-oauth2: ## Seed only OAuth2 clients and scopes
	$(PYTHON) database/seeders/oauth2_seeder.py

.PHONY: db-reset
db-reset: ## Reset PostgreSQL database (drop and recreate tables)
	$(PYTHON) -c "from config.database import engine, Base; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); print('✅ PostgreSQL database reset complete')"

.PHONY: db-migrate
db-migrate: ## Run database migrations
	$(PYTHON) migrate.py

.PHONY: db-status
db-status: ## Show database connection status
	$(PYTHON) -c "from config.database import engine; print('✅ PostgreSQL connection successful') if engine.execute('SELECT 1').fetchone() else print('❌ Database connection failed')"

