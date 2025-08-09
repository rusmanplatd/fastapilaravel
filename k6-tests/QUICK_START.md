# K6 Tests - Quick Start Guide

This guide gets you up and running with K6 tests in under 5 minutes using Docker.

## 🚀 TL;DR - Get Testing Now

```bash
# Navigate to k6-tests directory
cd k6-tests

# Start everything and run tests
make quick-start  # Starts PostgreSQL, Redis, FastAPI
make test        # Runs all K6 tests

# Clean up when done
make clean
```

## 📋 Prerequisites

- **Docker**: Ensure Docker is installed and running
- **Docker Compose**: Should be available with modern Docker installations
- **Environment File**: Copy `.env.k6.example` to `.env.k6` (or use defaults)

## ⚡ Quick Commands

### Setup & Start
```bash
make quick-start    # Start all services + setup database
make start         # Start services only (no database setup)
make db-setup      # Setup database with seed data
```

### Run Tests
```bash
make test           # All tests
make test-auth      # Authentication tests
make test-rbac      # Role-based access control
make test-security  # MFA and WebAuthn
make test-features  # Notifications, storage, queues, etc.
```

### Monitor & Debug
```bash
make status         # Show service status
make health         # Check service health
make logs           # View all service logs
make logs-app       # View FastAPI logs only
```

### Cleanup
```bash
make stop           # Stop all services
make clean          # Stop and remove containers/volumes
```

## 🌐 Service URLs (When Running)

- **FastAPI Application**: http://localhost:8001
- **PostgreSQL Database**: localhost:5433
- **Redis Cache**: localhost:6380

## 🔍 Service Status Check

```bash
# Check if services are healthy
make health

# Expected output:
# 🏥 Checking service health...
# FastAPI: 200
# PostgreSQL: ✅ Healthy
# Redis: PONG
```

## 📊 Test Categories

| Command | Description | Duration |
|---------|-------------|----------|
| `make test` | All tests | ~5-10 min |
| `make test-auth` | JWT & OAuth2 authentication | ~2 min |
| `make test-rbac` | Users, roles, permissions | ~2 min |
| `make test-security` | MFA, WebAuthn | ~2 min |
| `make test-features` | Notifications, storage, queues | ~3 min |
| `make test-compliance` | OAuth2 RFC compliance | ~1 min |

## 🐛 Troubleshooting

### Services Won't Start
```bash
# Check Docker is running
docker info

# Check port conflicts
make status
```

### Database Issues
```bash
# Reset database completely
make db-reset

# Connect to database directly
make db-connect
```

### Test Failures
```bash
# Check application health
curl http://localhost:8001/monitoring/health

# View application logs
make logs-app

# Run single test with debug
docker compose -f docker-compose.k6.yml --profile testing run --rm k6-runner run --log-level=debug tests/auth/jwt-auth-test.js
```

## 📝 Example Full Workflow

```bash
# 1. Navigate to k6-tests
cd k6-tests

# 2. Setup environment file (optional - defaults work fine)
cp .env.k6.example .env.k6

# 3. Start everything (includes database setup)
make quick-start

# 3. Verify everything is healthy
make health

# 4. Run authentication tests first (fastest)
make test-auth

# 5. Run all tests if auth tests pass
make test

# 6. Check application logs if needed
make logs-app

# 7. Clean up when done
make clean
```

## 🎯 What Gets Tested

### Authentication & Authorization
- JWT token generation and validation
- OAuth2 flows (Authorization Code, Client Credentials, etc.)
- Role-based access control (RBAC)
- Permission checking and assignment

### Security Features
- Multi-Factor Authentication (MFA)
- WebAuthn registration and authentication
- Rate limiting and security headers

### Core Features
- Multi-channel notifications (Email, SMS, Slack, etc.)
- File upload and storage (Local, S3, Azure, etc.)
- Background job queues and processing
- Pagination and query filtering
- Activity logging and auditing

### Compliance
- OAuth2 RFC compliance validation
- Security best practices verification

## 💡 Tips

1. **Start Small**: Begin with `make test-auth` before running all tests
2. **Monitor Resources**: Use `docker stats` to monitor container resource usage
3. **Check Logs**: Always check `make logs-app` if tests fail unexpectedly
4. **Clean Between Runs**: Use `make clean` to ensure fresh test environment
5. **Database State**: Each test run gets a fresh database with seeded data

## 📚 More Information

- **Detailed Setup**: See `DOCKER_SETUP.md` for comprehensive Docker configuration
- **PostgreSQL Guide**: See `POSTGRESQL_SETUP.md` for database-specific information
- **Full Documentation**: See `README.md` for complete test suite documentation

---

**Happy Testing! 🎉**

Need help? Check the logs with `make logs` or refer to the troubleshooting section in `DOCKER_SETUP.md`.