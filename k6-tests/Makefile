# K6 Testing Makefile
# Provides convenient commands for managing K6 testing infrastructure

# Docker Compose file and environment
COMPOSE_FILE := docker-compose.k6.yml
ENV_FILE := .env.k6
COMPOSE_CMD := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)

# Default targets
.PHONY: help
help: ## Show this help message
	@echo "K6 Testing Infrastructure - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Infrastructure Management
.PHONY: start
start: ## Start K6 testing infrastructure (PostgreSQL, Redis, FastAPI)
	$(COMPOSE_CMD) up -d postgres-k6 redis-k6 app-k6
	@echo "⏳ Waiting for services to be healthy..."
	$(COMPOSE_CMD) exec postgres-k6 pg_isready -U postgres -d test_k6_db
	@echo "✅ K6 testing infrastructure is ready!"
	@echo "📊 FastAPI app available at: http://localhost:8001"
	@echo "🐘 PostgreSQL available at: localhost:5433"
	@echo "🔴 Redis available at: localhost:6380"

.PHONY: stop
stop: ## Stop K6 testing infrastructure
	$(COMPOSE_CMD) down
	@echo "🛑 K6 testing infrastructure stopped"

.PHONY: restart
restart: ## Restart K6 testing infrastructure
	$(COMPOSE_CMD) restart
	@echo "🔄 K6 testing infrastructure restarted"

.PHONY: status
status: ## Show status of K6 testing services
	$(COMPOSE_CMD) ps

.PHONY: logs
logs: ## View logs from all K6 testing services
	$(COMPOSE_CMD) logs -f

.PHONY: logs-app
logs-app: ## View logs from FastAPI application only
	$(COMPOSE_CMD) logs -f app-k6

.PHONY: logs-postgres
logs-postgres: ## View logs from PostgreSQL only
	$(COMPOSE_CMD) logs -f postgres-k6

# Database Management
.PHONY: db-setup
db-setup: ## Setup fresh test database with seed data
	$(COMPOSE_CMD) run --rm db-setup
	@echo "✅ Test database setup complete"

.PHONY: db-reset
db-reset: ## Reset test database (drop and recreate)
	$(COMPOSE_CMD) exec postgres-k6 psql -U postgres -c "DROP DATABASE IF EXISTS test_k6_db;"
	$(COMPOSE_CMD) exec postgres-k6 psql -U postgres -c "CREATE DATABASE test_k6_db;"
	$(MAKE) db-setup
	@echo "🔄 Test database reset complete"

.PHONY: db-connect
db-connect: ## Connect to test database with psql
	$(COMPOSE_CMD) exec postgres-k6 psql -U postgres -d test_k6_db

.PHONY: db-backup
db-backup: ## Backup test database
	$(COMPOSE_CMD) exec postgres-k6 pg_dump -U postgres test_k6_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "💾 Database backup created"

# K6 Test Execution
.PHONY: test
test: ## Run all K6 tests
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run run-all-tests.js

.PHONY: test-auth
test-auth: ## Run authentication tests only
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/auth/jwt-auth-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/auth/oauth2-auth-test.js

.PHONY: test-rbac
test-rbac: ## Run RBAC tests only
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/rbac/user-management-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/rbac/permissions-test.js

.PHONY: test-security
test-security: ## Run security tests only
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/security/mfa-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/security/webauthn-test.js

.PHONY: test-features
test-features: ## Run feature tests only
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/features/notifications-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/features/storage-upload-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/features/queue-system-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/features/pagination-querybuilder-test.js
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/features/activity-logging-test.js

.PHONY: test-compliance
test-compliance: ## Run OAuth2 compliance tests
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run tests/oauth2/rfc-compliance-test.js

.PHONY: test-load
test-load: ## Run load tests with higher VU count
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run --vus 20 --duration 5m tests/auth/jwt-auth-test.js

.PHONY: test-stress
test-stress: ## Run stress tests with maximum load
	$(COMPOSE_CMD) --profile testing run --rm k6-runner run --vus 50 --duration 10m run-all-tests.js

# Development & Debugging
.PHONY: shell-app
shell-app: ## Access shell in FastAPI container
	$(COMPOSE_CMD) exec app-k6 /bin/bash

.PHONY: shell-postgres
shell-postgres: ## Access shell in PostgreSQL container
	$(COMPOSE_CMD) exec postgres-k6 /bin/bash

.PHONY: shell-k6
shell-k6: ## Access shell in K6 container
	$(COMPOSE_CMD) --profile testing run --rm k6-runner /bin/sh

# Health Checks
.PHONY: health
health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@echo "FastAPI: $(shell curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/monitoring/health)"
	@echo "PostgreSQL: $(shell $(COMPOSE_CMD) exec postgres-k6 pg_isready -U postgres -d test_k6_db >/dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy")"
	@echo "Redis: $(shell $(COMPOSE_CMD) exec redis-k6 redis-cli ping 2>/dev/null || echo "❌ Unhealthy")"

.PHONY: wait-ready
wait-ready: ## Wait for all services to be ready
	@echo "⏳ Waiting for services to be ready..."
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if $(COMPOSE_CMD) exec postgres-k6 pg_isready -U postgres -d test_k6_db >/dev/null 2>&1 && \
		   curl -s -f http://localhost:8001/monitoring/health >/dev/null 2>&1; then \
			echo "✅ All services are ready!"; \
			exit 0; \
		fi; \
		sleep 2; \
		timeout=$$((timeout-2)); \
	done; \
	echo "❌ Timeout waiting for services"; \
	exit 1

# Cleanup & Maintenance
.PHONY: clean
clean: ## Clean up containers and volumes
	$(COMPOSE_CMD) down -v --remove-orphans
	docker system prune -f
	@echo "🧹 Cleanup complete"

.PHONY: clean-data
clean-data: ## Remove all K6 test data volumes
	$(COMPOSE_CMD) down -v
	docker volume rm fastapilaravel_k6_postgres_data fastapilaravel_k6_redis_data fastapilaravel_k6_app_storage fastapilaravel_k6_app_logs fastapilaravel_k6_results 2>/dev/null || true
	@echo "🗑️  All K6 test data removed"

.PHONY: rebuild
rebuild: ## Rebuild and restart all services
	$(COMPOSE_CMD) down
	$(COMPOSE_CMD) build --no-cache
	$(COMPOSE_CMD) up -d postgres-k6 redis-k6 app-k6
	$(MAKE) wait-ready
	@echo "🔨 Rebuild complete"

# Results & Reports
.PHONY: results
results: ## View K6 test results
	docker run --rm -v fastapilaravel_k6_results:/results alpine ls -la /results

.PHONY: results-clean
results-clean: ## Clean K6 test results
	docker volume rm fastapilaravel_k6_results 2>/dev/null || true
	@echo "📊 Results cleaned"

# Quick Setup Commands
.PHONY: quick-start
quick-start: start wait-ready db-setup ## Quick start: bring up infrastructure and setup database
	@echo "🚀 K6 testing environment is ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  make test          # Run all tests"
	@echo "  make test-auth     # Run authentication tests"
	@echo "  make health        # Check service health"
	@echo "  make logs          # View service logs"

.PHONY: full-test
full-test: quick-start test ## Full test: setup environment and run all tests
	@echo "🎉 Full K6 test suite completed!"

# Information
.PHONY: info
info: ## Show K6 testing environment information
	@echo "K6 Testing Environment Information:"
	@echo "=================================="
	@echo "FastAPI Application: http://localhost:8001"
	@echo "PostgreSQL Database: localhost:5433 (test_k6_db)"
	@echo "Redis Cache:         localhost:6380"
	@echo "Docker Network:      fastapilaravel-k6-network"
	@echo ""
	@echo "Key Commands:"
	@echo "  make quick-start   # Setup and start everything"
	@echo "  make test         # Run all K6 tests"
	@echo "  make clean        # Clean up everything"