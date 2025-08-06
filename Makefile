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
type-check-strict: ## Run strict mypy type checking
	mypy --strict --config-file=mypy.ini $(SRC_DIR)

.PHONY: type-coverage
type-coverage: ## Generate type coverage report
	mypy --config-file=mypy.ini --html-report=type_coverage $(SRC_DIR)
	@echo "Type coverage report generated in type_coverage/"

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

# Database
.PHONY: db-seed
db-seed: ## Seed database with default data
	$(PYTHON) database/seeders/user_seeder.py
	$(PYTHON) database/seeders/permission_seeder.py
	$(PYTHON) database/seeders/oauth2_seeder.py

.PHONY: db-seed-oauth2
db-seed-oauth2: ## Seed OAuth2 clients and scopes
	$(PYTHON) database/seeders/oauth2_seeder.py seed

.PHONY: db-clean-oauth2
db-clean-oauth2: ## Clean OAuth2 data
	$(PYTHON) database/seeders/oauth2_seeder.py clean

.PHONY: db-reseed-oauth2
db-reseed-oauth2: ## Reseed OAuth2 data (clean + seed)
	$(PYTHON) database/seeders/oauth2_seeder.py reseed

.PHONY: db-reset
db-reset: ## Reset database (remove sqlite file)
	rm -f storage/database.db

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

# Docker (placeholder)
.PHONY: docker-build
docker-build: ## Build Docker image (to be implemented)
	@echo "Docker build not yet implemented"

.PHONY: docker-run
docker-run: ## Run Docker container (to be implemented)
	@echo "Docker run not yet implemented"

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