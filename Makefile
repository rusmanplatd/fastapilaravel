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

# Artisan commands (using the new enhanced system)
ARTISAN := python artisan.py

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

# Database Migrations (Laravel-style)
.PHONY: migrate
migrate: ## Run database migrations
	$(PYTHON) -m app.Console.Commands.MigrateCommand migrate

.PHONY: migrate-rollback
migrate-rollback: ## Rollback last migration batch
	$(PYTHON) -m app.Console.Commands.MigrateCommand rollback

.PHONY: migrate-reset
migrate-reset: ## Reset all migrations
	$(PYTHON) -m app.Console.Commands.MigrateCommand reset

.PHONY: migrate-refresh
migrate-refresh: ## Reset and re-run all migrations
	$(PYTHON) -m app.Console.Commands.MigrateCommand refresh

.PHONY: migrate-status
migrate-status: ## Show migration status
	$(PYTHON) -m app.Console.Commands.MigrateCommand status

.PHONY: make-migration
make-migration: ## Create new migration (usage: make make-migration name=create_users_table)
	$(PYTHON) -m app.Console.Commands.MigrateCommand make $(name)

.PHONY: make-migration-table
make-migration-table: ## Create new table migration (usage: make make-migration-table table=users)
	$(PYTHON) -m app.Console.Commands.MigrateCommand make create_$(table)_table --create $(table)

# Database Seeding
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

.PHONY: db-fresh
db-fresh: ## Fresh database (reset + migrate + seed)
	$(MAKE) db-reset
	$(MAKE) migrate
	$(MAKE) db-seed

# Queue Management
.PHONY: queue-work
queue-work: ## Start queue worker (default queue)
	$(PYTHON) -m app.Commands.QueueWorkerCommand

.PHONY: queue-work-emails
queue-work-emails: ## Start queue worker for emails queue
	$(PYTHON) -m app.Commands.QueueWorkerCommand --queue emails

.PHONY: queue-work-notifications
queue-work-notifications: ## Start queue worker for notifications queue
	$(PYTHON) -m app.Commands.QueueWorkerCommand --queue notifications

.PHONY: queue-stats
queue-stats: ## Show queue statistics
	$(PYTHON) -m app.Commands.QueueManagementCommand stats

.PHONY: queue-clear
queue-clear: ## Clear default queue (with confirmation)
	$(PYTHON) -m app.Commands.QueueManagementCommand clear

.PHONY: queue-failed
queue-failed: ## List failed jobs
	$(PYTHON) -m app.Commands.QueueManagementCommand failed list

.PHONY: queue-retry-failed
queue-retry-failed: ## Retry all failed jobs (with confirmation)
	$(PYTHON) -m app.Commands.QueueManagementCommand failed retry-all

.PHONY: queue-clear-failed
queue-clear-failed: ## Clear all failed jobs (with confirmation)
	$(PYTHON) -m app.Commands.QueueManagementCommand failed clear

.PHONY: queue-release-reserved
queue-release-reserved: ## Release timed out reserved jobs
	$(PYTHON) -m app.Commands.QueueManagementCommand release

.PHONY: queue-example
queue-example: ## Run queue usage examples
	$(PYTHON) examples/queue_usage.py

.PHONY: queue-advanced-example
queue-advanced-example: ## Run advanced queue features demo
	$(PYTHON) examples/advanced_queue_features.py

.PHONY: queue-dashboard
queue-dashboard: ## Start real-time queue monitoring dashboard
	$(PYTHON) -m app.Commands.QueueMonitorCommand dashboard

.PHONY: queue-metrics
queue-metrics: ## Show detailed queue metrics and analytics
	$(PYTHON) -m app.Commands.QueueMonitorCommand metrics

.PHONY: queue-health
queue-health: ## Run queue health check
	$(PYTHON) -m app.Commands.QueueMonitorCommand health

.PHONY: queue-top
queue-top: ## Start htop-style queue monitor
	$(PYTHON) -m app.Commands.QueueMonitorCommand top

# Schedule management
.PHONY: schedule-run
schedule-run: ## Run scheduled commands that are due
	$(ARTISAN) schedule:run

.PHONY: schedule-list
schedule-list: ## List all scheduled commands
	$(ARTISAN) schedule:list

.PHONY: schedule-work
schedule-work: ## Start the schedule worker
	$(ARTISAN) schedule:work

.PHONY: schedule-install
schedule-install: ## Install scheduler in system cron
	$(ARTISAN) schedule:install

.PHONY: schedule-uninstall
schedule-uninstall: ## Remove scheduler from system cron
	$(ARTISAN) schedule:uninstall

.PHONY: schedule-status
schedule-status: ## Show scheduler status
	$(ARTISAN) schedule:status

.PHONY: schedule-report
schedule-report: ## Generate schedule report
	$(ARTISAN) schedule:report

.PHONY: schedule-discover
schedule-discover: ## Discover and register scheduled events
	$(ARTISAN) schedule:discover

.PHONY: schedule-logs
schedule-logs: ## View recent schedule logs
	$(ARTISAN) schedule:logs

.PHONY: schedule-cleanup
schedule-cleanup: ## Clean up old schedule logs
	$(ARTISAN) schedule:cleanup

.PHONY: schedule-test
schedule-test: ## Test a specific scheduled command
	$(ARTISAN) schedule:test $(CMD)

# Storage operations
.PHONY: storage-link
storage-link: ## Create symbolic link for public storage
	mkdir -p storage/app/public
	rm -f public/storage
	ln -sf ../storage/app/public public/storage

.PHONY: storage-test
storage-test: ## Test storage connections
	$(PYTHON) -c "from app.Storage import Storage; print('Testing local storage...'); print(Storage.disk_info('local'))"

.PHONY: storage-cleanup
storage-cleanup: ## Clean up temporary files
	find storage/app/temp -type f -mtime +1 -delete 2>/dev/null || true
	find storage/app/uploads -name "*.tmp" -delete 2>/dev/null || true

.PHONY: storage-info
storage-info: ## Show storage disk information
	$(PYTHON) -c "from app.Storage import Storage; import json; print(json.dumps(Storage.disk_info(), indent=2))"

.PHONY: storage-usage
storage-usage: ## Show storage usage statistics
	@echo "Storage Usage:"
	@du -sh storage/app/* 2>/dev/null || echo "No storage directories found"

.PHONY: storage-backup
storage-backup: ## Backup storage directory
	tar -czf storage_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz storage/

.PHONY: storage-example
storage-example: ## Run storage example server
	cd examples && $(PYTHON) storage_example.py

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

# Artisan Commands
.PHONY: artisan
artisan: ## Show available Artisan commands
	$(ARTISAN) list

.PHONY: artisan-help
artisan-help: ## Show help for a specific Artisan command (use: make artisan-help CMD=command:name)
	$(ARTISAN) help $(CMD)

.PHONY: make-controller
make-controller: ## Generate a new controller (use: make make-controller NAME=ControllerName)
	$(ARTISAN) make:controller $(NAME) $(if $(RESOURCE),--resource,)

.PHONY: make-command
make-command: ## Generate a new Artisan command (use: make make-command NAME=CommandName)
	$(ARTISAN) make:command $(NAME)

# Example commands (for demonstration)
.PHONY: example-greet
example-greet: ## Run the greeting example command
	$(ARTISAN) example:greet "FastAPI User" --shout --repeat=3

.PHONY: example-interactive
example-interactive: ## Run the interactive example command
	$(ARTISAN) example:interactive

.PHONY: example-progress
example-progress: ## Run the progress bar example command
	$(ARTISAN) example:progress --items=50 --delay=0.05

.PHONY: example-table
example-table: ## Run the table output example command
	$(ARTISAN) example:table