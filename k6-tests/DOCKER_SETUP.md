# Docker Setup Guide for K6 Testing

This guide provides comprehensive instructions for setting up and running the K6 test suite using Docker Compose.

## 🐳 Overview

The K6 testing environment uses Docker Compose to provide:

- **Isolated Testing Environment**: Complete separation from development environment
- **PostgreSQL 17**: Dedicated test database with optimized settings
- **Redis**: Cache and queue backend for testing
- **FastAPI Application**: Containerized application instance
- **K6 Runner**: Containerized K6 for consistent test execution

## 📋 Prerequisites

- **Docker**: Version 20.0+ installed
- **Docker Compose**: Version 2.0+ installed
- **Make**: For convenient command execution (optional but recommended)
- **Environment File**: Copy `.env.k6.example` to `.env.k6` for custom configuration

### Installation

#### Ubuntu/Debian
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### macOS
```bash
# Install Docker Desktop for Mac (includes Docker Compose)
# Download from: https://docs.docker.com/desktop/mac/install/

# Or use Homebrew
brew install docker docker-compose
```

## 🚀 Quick Start

### 1. Navigate to K6 Tests Directory
```bash
cd k6-tests
```

### 2. Setup Environment Configuration
```bash
# Copy example environment file
cp .env.k6.example .env.k6

# Edit if you need custom settings (optional)
nano .env.k6
```

### 3. Start the Testing Environment
```bash
# Option 1: Using Make (recommended)
make quick-start

# Option 2: Using Docker Compose directly
docker-compose -f docker-compose.k6.yml up -d postgres-k6 redis-k6 app-k6
```

### 4. Wait for Services to be Ready
```bash
# Check service health
make health

# Or manually check
docker compose -f docker-compose.k6.yml --env-file .env.k6 ps
```

### 5. Setup Test Database
```bash
# Initialize database with seed data
make db-setup

# Or using Docker Compose directly
docker-compose -f docker-compose.k6.yml run --rm db-setup
```

### 6. Run Tests
```bash
# Run all tests
make test

# Run specific test categories
make test-auth
make test-rbac
make test-features
```

## 📊 Service Details

### PostgreSQL Database
- **Image**: postgres:17-alpine
- **Port**: 5433 (external) → 5432 (internal)
- **Database**: test_k6_db
- **Username**: postgres
- **Password**: k6_test_password
- **Connection**: `postgresql://postgres:k6_test_password@localhost:5433/test_k6_db`

### Redis Cache
- **Image**: redis:8-alpine
- **Port**: 6380 (external) → 6379 (internal)
- **Configuration**: Default Redis settings
- **Usage**: Caching, queues, and session storage

### FastAPI Application
- **Port**: 8001 (external) → 8000 (internal)
- **Environment**: Testing mode
- **URL**: http://localhost:8001
- **Features**: All features enabled for comprehensive testing

### K6 Runner
- **Image**: grafana/k6:latest
- **Purpose**: Execute K6 test scripts in isolated environment
- **Results**: Stored in dedicated volume for analysis

## 🛠️ Available Commands

### Infrastructure Management
```bash
make start              # Start all services (PostgreSQL, Redis, FastAPI)
make stop               # Stop all services
make restart            # Restart all services
make status             # Show status of all services
make logs               # View logs from all services
make logs-app           # View FastAPI application logs only
make logs-postgres      # View PostgreSQL logs only
```

### Database Operations
```bash
make db-setup           # Setup fresh database with seed data
make db-reset           # Reset database completely (drop/recreate)
make db-connect         # Connect to database with psql
make db-backup          # Create database backup
```

### Test Execution
```bash
make test               # Run all K6 tests
make test-auth          # Authentication tests only
make test-rbac          # RBAC tests only
make test-security      # Security tests (MFA, WebAuthn)
make test-features      # Feature tests (notifications, storage, etc.)
make test-compliance    # OAuth2 compliance tests
make test-load          # Load tests (20 VUs, 5 minutes)
make test-stress        # Stress tests (50 VUs, 10 minutes)
```

### Development & Debugging
```bash
make shell-app          # Access shell in FastAPI container
make shell-postgres     # Access shell in PostgreSQL container
make shell-k6           # Access shell in K6 container
make health             # Check health of all services
make wait-ready         # Wait for all services to be ready
```

### Maintenance
```bash
make clean              # Clean up containers and volumes
make clean-data         # Remove all persistent data volumes
make rebuild            # Rebuild all images and restart
make info               # Show environment information
```

## 🔧 Configuration

### Environment File (.env.k6)

The K6 testing environment uses a dedicated `.env.k6` file for configuration. This provides complete isolation from your main application environment.

#### Setup Environment File
```bash
# Copy the example file
cp .env.k6.example .env.k6

# The example file contains sensible defaults that work out of the box
# Customize as needed for your testing requirements
```

#### Key Environment Variables
The `.env.k6` file contains over 200 configuration options organized by category:

```bash
# Application Configuration (K6 Testing Instance)
APP_NAME="FastAPI Laravel K6 Tests"
APP_URL="http://localhost:8001" 
APP_ENV="testing"
APP_SECRET_KEY="k6-test-secret-key-change-in-production-must-be-32-chars"

# Database Configuration (Isolated PostgreSQL)
DB_CONNECTION="postgresql"
DB_HOST="postgres-k6"
DB_DATABASE="test_k6_db"
DB_USERNAME="postgres" 
DB_PASSWORD="k6_test_password"
K6_POSTGRES_EXTERNAL_PORT="5433"

# Redis Configuration (Isolated Cache/Queue)
REDIS_HOST="redis-k6"
CACHE_DRIVER="redis"
QUEUE_CONNECTION="redis"
K6_REDIS_EXTERNAL_PORT="6380"

# K6 Test Configuration
K6_BASE_URL="http://localhost:8001"
K6_TEST_DB_URL="postgresql://postgres:k6_test_password@localhost:5433/test_k6_db"
K6_TEST_USER_EMAIL="test@example.com"
K6_ADMIN_USER_EMAIL="admin@example.com"
K6_OAUTH2_CLIENT_ID="test-client-id"

# Load Testing Settings
K6_VUS_LIGHT="5"
K6_VUS_NORMAL="20"
K6_VUS_STRESS="50"
RATE_LIMIT_ENABLED="false"  # Disabled for load testing

# Feature Flags (All Enabled for Testing)
FEATURE_REGISTRATION_ENABLED="true"
FEATURE_OAUTH2_ENABLED="true"
FEATURE_ANALYTICS_ENABLED="true"
```

#### Environment Variable Categories

The `.env.k6` file organizes 200+ variables into these categories:

- **Application Configuration**: Basic app settings, URLs, secrets
- **Database Configuration**: PostgreSQL settings with custom ports
- **Redis Configuration**: Cache and queue configuration
- **Authentication & Security**: JWT, OAuth2, MFA settings
- **K6 Test Configuration**: Test-specific settings and credentials
- **Load Testing Configuration**: VUs, durations, scenarios
- **Feature Flags**: Enable/disable features for testing
- **Docker Configuration**: Container images, networks, volumes
- **Monitoring & Health**: Health check settings

### Custom Configuration

You have several options to customize the K6 testing environment:

#### 1. Environment File (.env.k6) - Recommended
```bash
# Copy and edit the environment file
cp .env.k6.example .env.k6
nano .env.k6

# Modify any settings you need:
# - Change database passwords
# - Adjust load testing parameters  
# - Configure OAuth2 clients
# - Enable/disable features
```

#### 2. Environment Variables (Override)
```bash
# Set environment variables before running
export K6_VUS_STRESS=100
export K6_TEST_USER_EMAIL=mytest@example.com
make test-stress
```

#### 3. Docker Compose Override
```yaml
# docker-compose.override.yml
services:
  app-k6:
    environment:
      - LOG_LEVEL=debug
      - FEATURE_CUSTOM_SETTING=true
```

#### 4. Custom Docker Compose (Advanced)
```bash
# Copy and modify the compose file
cp docker-compose.k6.yml docker-compose.custom.yml
# Edit as needed
docker compose -f docker-compose.custom.yml --env-file .env.k6 up
```

## 🔍 Monitoring & Debugging

### Health Checks
All services include health checks:

```bash
# Check overall health
make health

# Individual service health
docker-compose -f docker-compose.k6.yml exec postgres-k6 pg_isready -U postgres -d test_k6_db
curl -f http://localhost:8001/monitoring/health
docker-compose -f docker-compose.k6.yml exec redis-k6 redis-cli ping
```

### Logs
```bash
# All service logs
make logs

# Specific service logs
docker-compose -f docker-compose.k6.yml logs postgres-k6
docker-compose -f docker-compose.k6.yml logs app-k6
docker-compose -f docker-compose.k6.yml logs redis-k6

# Follow logs in real-time
docker-compose -f docker-compose.k6.yml logs -f app-k6
```

### Database Access
```bash
# Connect to PostgreSQL
make db-connect

# Or directly
docker-compose -f docker-compose.k6.yml exec postgres-k6 psql -U postgres -d test_k6_db

# Run queries
psql -h localhost -p 5433 -U postgres -d test_k6_db -c "SELECT COUNT(*) FROM users;"
```

### Application Access
```bash
# Application shell
make shell-app

# Or directly
docker-compose -f docker-compose.k6.yml exec app-k6 /bin/bash

# API testing
curl http://localhost:8001/monitoring/health
curl http://localhost:8001/api/v1/auth/login
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check if ports are in use
netstat -tulpn | grep :5433
netstat -tulpn | grep :6380
netstat -tulpn | grep :8001

# Solution: Stop conflicting services or change ports
docker-compose -f docker-compose.k6.yml down
```

#### 2. Services Not Starting
```bash
# Check Docker daemon
sudo systemctl status docker

# Check available resources
docker system df
docker system prune -f

# Restart Docker
sudo systemctl restart docker
```

#### 3. Database Connection Issues
```bash
# Check PostgreSQL logs
make logs-postgres

# Test connection manually
docker-compose -f docker-compose.k6.yml exec postgres-k6 pg_isready -U postgres

# Reset database
make db-reset
```

#### 4. Application Not Responding
```bash
# Check application logs
make logs-app

# Check health endpoint
curl -v http://localhost:8001/monitoring/health

# Restart application
docker-compose -f docker-compose.k6.yml restart app-k6
```

#### 5. K6 Tests Failing
```bash
# Check test configuration
cat config/test-config.js

# Verify application is ready
make wait-ready

# Run tests with debug output
docker-compose -f docker-compose.k6.yml --profile testing run --rm k6-runner run --log-level=debug tests/auth/jwt-auth-test.js
```

### Performance Issues

#### 1. Slow Database Operations
```bash
# Check PostgreSQL configuration
docker-compose -f docker-compose.k6.yml exec postgres-k6 psql -U postgres -c "SHOW all;"

# Monitor database performance
docker-compose -f docker-compose.k6.yml exec postgres-k6 psql -U postgres -d test_k6_db -c "SELECT * FROM pg_stat_activity;"
```

#### 2. High Memory Usage
```bash
# Check container resources
docker stats

# Limit container memory
# Add to docker-compose.k6.yml:
# deploy:
#   resources:
#     limits:
#       memory: 512M
```

#### 3. Slow Test Execution
```bash
# Reduce VU count
make test-auth  # Uses default lower VU count

# Use faster test scenarios
docker-compose -f docker-compose.k6.yml --profile testing run --rm k6-runner run --vus 5 --duration 30s tests/auth/jwt-auth-test.js
```

## 🔒 Security Considerations

### Test Environment Security
- Use dedicated passwords for test environment
- Isolate test network from production
- Clean up test data after testing
- Don't expose test services to public networks

### Docker Security
```bash
# Run containers with non-root user
# Add to service configuration:
# user: "1001:1001"

# Use read-only filesystems where possible
# read_only: true

# Limit container capabilities
# cap_drop:
#   - ALL
# cap_add:
#   - NET_BIND_SERVICE
```

## 📈 Performance Optimization

### Database Optimization
The PostgreSQL container includes optimized settings:

```sql
-- Applied automatically via init-db.sql
max_connections = 200
shared_buffers = '256MB'
effective_cache_size = '1GB'
maintenance_work_mem = '64MB'
```

### Container Resource Limits
```yaml
# Add to services in docker-compose.k6.yml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
    reservations:
      memory: 512M
      cpus: '0.25'
```

## 🎯 Best Practices

### 1. Test Isolation
- Always use fresh database for each test run
- Clean up test data between test suites
- Use separate test credentials

### 2. Resource Management
- Monitor container resource usage
- Set appropriate resource limits
- Clean up unused volumes and networks

### 3. Development Workflow
```bash
# Start development session
make quick-start

# Run tests during development
make test-auth  # Quick feedback loop

# Clean up after development
make clean
```

### 4. CI/CD Integration
```bash
# In CI/CD pipeline
cd k6-tests
make quick-start
make test
make clean
```

This Docker setup provides a robust, isolated, and reproducible environment for K6 testing with PostgreSQL, ensuring consistent results across different environments and team members.