# K6 Load Testing Suite for FastAPI Laravel

Comprehensive k6 test suite for the FastAPI Laravel application with complete feature coverage and fresh database setup for each test run.

## 🧪 Test Coverage

### Authentication & Authorization
- **JWT Authentication** (`tests/auth/jwt-auth-test.js`)
  - Login/logout flows
  - Token refresh
  - Protected route access
  - Rate limiting

- **OAuth2 Authentication** (`tests/auth/oauth2-auth-test.js`)
  - Client credentials flow
  - Authorization code flow (PKCE)
  - Token introspection & revocation
  - Multiple client types

- **RFC Compliance** (`tests/oauth2/rfc-compliance-test.js`)
  - RFC 6749 (OAuth 2.0 Core)
  - RFC 7662 (Token Introspection)
  - RFC 7636 (PKCE)
  - RFC 8414 (Server Metadata)
  - Security best practices (RFC 8725)

### Role-Based Access Control (RBAC)
- **User Management** (`tests/rbac/user-management-test.js`)
  - CRUD operations
  - Role assignment
  - Permission checking
  - Bulk operations

- **Permissions System** (`tests/rbac/permissions-test.js`)
  - Permission hierarchy
  - Resource-specific permissions
  - Dynamic permission assignment
  - Access control validation

### Security Features
- **Multi-Factor Authentication** (`tests/security/mfa-test.js`)
  - TOTP setup and verification
  - SMS MFA flows
  - Recovery codes
  - MFA security policies

- **WebAuthn** (`tests/security/webauthn-test.js`)
  - Registration flows
  - Authentication challenges
  - Credential management
  - Security validations

### Core Features
- **Notification System** (`tests/features/notifications-test.js`)
  - Multi-channel notifications (Email, SMS, Slack, Discord, Push, Webhook)
  - Template-based notifications
  - Bulk and scheduled notifications
  - User preferences

- **File Storage & Upload** (`tests/features/storage-upload-test.js`)
  - Single and multiple file uploads
  - Multi-driver storage (Local, S3, GCS, Azure)
  - Image processing and optimization
  - Security validation and virus scanning

- **Queue System** (`tests/features/queue-system-test.js`)
  - Job dispatch and processing
  - Batch job operations
  - Job chains and dependencies
  - Queue management and monitoring

- **Pagination & Query Builder** (`tests/features/pagination-querybuilder-test.js`)
  - Standard and cursor pagination
  - Advanced filtering and sorting
  - Relationship includes
  - Search functionality

- **Activity Logging** (`tests/features/activity-logging-test.js`)
  - Automatic and manual logging
  - Audit trails and compliance
  - Activity analytics
  - Performance monitoring

## 🏗️ Test Architecture

### Database Setup
- **Fresh PostgreSQL Database**: Each test uses a clean PostgreSQL database `test_k6_db`
- **Comprehensive Seeding**: Pre-populated with users, roles, permissions, OAuth2 clients
- **Test Isolation**: Setup and teardown for each test file
- **Database Recreation**: Full database drop/create for complete isolation

### Configuration
- **Centralized Config** (`config/test-config.js`): Base URLs, credentials, rate limits
- **Utility Helpers** (`utils/helpers.js`): Authentication, validation, test data generation
- **Database Helpers** (`setup/test-db-setup.py`): Python script for database initialization

### Test Organization
```
k6-tests/
├── config/                 # Test configuration
├── utils/                  # Helper functions
├── setup/                  # Database setup scripts
├── tests/
│   ├── auth/              # Authentication tests
│   ├── rbac/              # Role-based access control
│   ├── security/          # Security features (MFA, WebAuthn)
│   ├── oauth2/            # OAuth2 compliance tests
│   └── features/          # Core application features
├── results/               # Test output and reports
└── run-all-tests.js       # Main test runner
```

## 🚀 Running Tests

### Prerequisites
1. **Install k6**: https://k6.io/docs/getting-started/installation/
2. **Docker & Docker Compose**: For containerized testing environment
3. **Environment Configuration**: Copy `.env.k6.example` to `.env.k6` and customize if needed
4. **Python Environment** (if running locally): Ensure Python dependencies are installed (including `psycopg2`)

### Docker Setup (Recommended)

The easiest way to run K6 tests is using the dedicated Docker Compose setup:

```bash
# Navigate to k6-tests directory
cd k6-tests

# Setup environment file (optional - defaults work)
cp .env.k6.example .env.k6

# Quick start: Setup and run all infrastructure
make quick-start

# Run all tests
make test

# Run specific test categories
make test-auth          # Authentication tests
make test-rbac         # Role-based access control
make test-security     # MFA and WebAuthn tests
make test-features     # Core feature tests

# Stop infrastructure
make stop
```

### Local Setup (Alternative)

If you prefer to run tests locally without Docker:

#### PostgreSQL Setup
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Install PostgreSQL (macOS with Homebrew)
brew install postgresql
brew services start postgresql

# Create test database user (if not exists)
sudo -u postgres createuser --interactive --pwprompt postgres

# Install Python PostgreSQL adapter
pip install psycopg2-binary

# Verify connection
psql -h localhost -U postgres -c "SELECT version();"
```

#### Individual Test Files
```bash
# Start your FastAPI application first
cd .. && make dev

# In another terminal, run individual tests
cd k6-tests

# Authentication tests
k6 run tests/auth/jwt-auth-test.js
k6 run tests/auth/oauth2-auth-test.js

# RBAC tests
k6 run tests/rbac/user-management-test.js
k6 run tests/rbac/permissions-test.js

# Security tests
k6 run tests/security/mfa-test.js
k6 run tests/security/webauthn-test.js

# Feature tests
k6 run tests/features/notifications-test.js
k6 run tests/features/storage-upload-test.js
k6 run tests/features/queue-system-test.js
k6 run tests/features/pagination-querybuilder-test.js
k6 run tests/features/activity-logging-test.js

# Compliance tests
k6 run tests/oauth2/rfc-compliance-test.js
```

#### Complete Test Suite (Local)
```bash
# Run all tests sequentially (requires local FastAPI server running)
k6 run run-all-tests.js

# Run with custom environment
BASE_URL=http://localhost:8000 TEST_DB_URL=postgresql://postgres:password@localhost:5432/test_k6_db k6 run run-all-tests.js
```

### Docker Infrastructure Details

The Docker Compose setup includes:

- **PostgreSQL 17**: Isolated test database on port `5433`
- **Redis**: Cache and queue backend on port `6380` 
- **FastAPI App**: Test application instance on port `8001`
- **K6 Runner**: Containerized K6 for isolated test execution
- **Database Setup**: Automated seeding and schema management

#### Available Make Commands

```bash
# Infrastructure Management
make start              # Start PostgreSQL, Redis, and FastAPI
make stop              # Stop all services
make restart           # Restart all services
make status            # Show service status
make logs              # View all service logs

# Database Operations
make db-setup          # Initialize database with seed data
make db-reset          # Reset database completely
make db-connect        # Connect to database with psql

# Test Execution  
make test              # Run all K6 tests
make test-auth         # Run authentication tests
make test-rbac         # Run RBAC tests
make test-security     # Run security tests
make test-features     # Run feature tests
make test-load         # Run load tests (20 VUs)
make test-stress       # Run stress tests (50 VUs)

# Utilities
make health            # Check service health
make clean             # Clean up containers and volumes
make rebuild           # Rebuild and restart everything
```

### PostgreSQL Migration Notes

This test suite has been **fully migrated from SQLite to PostgreSQL** for enterprise-grade testing. Key changes include:

- **Fresh Database Creation**: Each test run creates a completely fresh PostgreSQL database
- **Docker-First Approach**: Containerized PostgreSQL with isolated test environment
- **Automatic Database Management**: Database creation, seeding, and cleanup are fully automated
- **PostgreSQL-Specific Features**: Sequence resets, transaction handling, and connection pooling
- **Comprehensive Documentation**: Complete setup guide available in `POSTGRESQL_SETUP.md`
- **Backward Compatibility**: SQLite support maintained for development environments

### Load Testing Scenarios
```bash
# Light load testing
k6 run --vus 5 --duration 30s k6-tests/tests/auth/jwt-auth-test.js

# Normal load testing
k6 run --vus 20 --duration 2m k6-tests/tests/features/notifications-test.js

# Stress testing
k6 run --vus 50 --duration 5m k6-tests/tests/rbac/user-management-test.js
```

## 📊 Test Scenarios & Thresholds

### Default Thresholds
- **Response Time**: 95th percentile < 2-3s (varies by endpoint complexity)
- **Error Rate**: < 5% for standard operations
- **Authentication**: 95th percentile < 1s
- **File Operations**: 95th percentile < 5s

### Load Testing Stages
1. **Ramp Up**: Gradually increase users
2. **Sustained Load**: Maintain target user count
3. **Ramp Down**: Graceful test completion

## 🎯 Test Data & Authentication

### Test Users
- **Regular User**: `test@example.com` / `password123`
- **Admin User**: `admin@example.com` / `admin123`
- **Generated Users**: 100 test users with various roles

### OAuth2 Clients
- **Test Client**: `test-client-id` / `test-client-secret`
- **Confidential Client**: `confidential-client` / `confidential-secret`
- **Public Client**: `public-client` (no secret)

### Test Data
- **Posts**: 500 test posts with various categories
- **Organizations**: 20 test organizations
- **Notifications**: 200 test notifications
- **Complete RBAC**: Roles, permissions, and assignments

## 📈 Reports & Results

### Output Formats
- **HTML Reports**: Detailed visual reports in `results/`
- **JSON Data**: Machine-readable results for CI/CD
- **Text Summary**: Console output with key metrics

### Key Metrics
- **Total Requests**: Number of HTTP requests made
- **Error Rate**: Percentage of failed requests
- **Response Times**: Average, median, 95th percentile
- **Throughput**: Requests per second
- **Test Coverage**: Endpoints and scenarios tested

## 🔧 Configuration Options

### Environment Variables

#### Docker Environment (Default)
```bash
BASE_URL=http://localhost:8001                                                    # Application base URL (Docker)
TEST_DB_URL=postgresql://postgres:k6_test_password@localhost:5433/test_k6_db     # Test database URL (Docker)
POSTGRES_USER=postgres                                                            # PostgreSQL username
POSTGRES_PASSWORD=k6_test_password                                                # PostgreSQL password
POSTGRES_HOST=localhost                                                           # PostgreSQL host
POSTGRES_PORT=5433                                                               # PostgreSQL port (Docker)
```

#### Local Environment
```bash
BASE_URL=http://localhost:8000                                                    # Application base URL (Local)
TEST_DB_URL=postgresql://postgres:password@localhost:5432/test_k6_db             # Test database URL (Local)
POSTGRES_USER=postgres                                                            # PostgreSQL username
POSTGRES_PASSWORD=password                                                        # PostgreSQL password
POSTGRES_HOST=localhost                                                           # PostgreSQL host
POSTGRES_PORT=5432                                                               # PostgreSQL port (Local)
```

### Test Configuration (`config/test-config.js`)
- **Authentication**: JWT and OAuth2 credentials
- **Rate Limits**: API rate limiting thresholds  
- **Test Data**: User counts, post categories, etc.
- **Scenarios**: Load testing configurations

## 🛠️ Extending Tests

### Adding New Tests
1. Create test file in appropriate directory (`tests/feature/`)
2. Import utilities and configuration
3. Define test scenarios with proper tags
4. Include setup/teardown for database state
5. Add validation checks for responses
6. Update main runner if needed

### Custom Validation
```javascript
import { validators } from '../../utils/helpers.js';

// Use built-in validators
validators.apiResponse(response, 200);
validators.paginatedResponse(response);
validators.oauth2TokenResponse(response);

// Custom validation
check(response, {
  'custom validation': (r) => r.json().hasOwnProperty('specific_field'),
});
```

### Database State Management
```javascript
// Setup fresh database
dbHelpers.setupTestDb(baseUrl);

// Clean database after tests
dbHelpers.cleanTestDb(baseUrl);
```

## 🚨 Troubleshooting

### Common Issues
1. **PostgreSQL Connection**: Ensure PostgreSQL server is running and accessible
2. **Database Permissions**: Ensure PostgreSQL user has CREATE DATABASE privileges
3. **Authentication Failures**: Verify test user credentials exist
4. **Rate Limiting**: Tests may trigger rate limits - adjust VU count
5. **Endpoint Availability**: Some endpoints may not be implemented
6. **Connection Pooling**: PostgreSQL may limit connections under high load

### Debug Mode
```bash
# Enable debug logging
k6 run --log-level=debug k6-tests/tests/auth/jwt-auth-test.js

# Save detailed results
k6 run --out json=results/detailed-results.json k6-tests/run-all-tests.js
```

## 🎉 Success Criteria

### Performance Benchmarks
- ✅ 95% of requests complete under target thresholds
- ✅ Error rate below 5%
- ✅ Authentication flows complete under 1 second
- ✅ All endpoints respond correctly under load

### Feature Coverage
- ✅ All authentication methods tested
- ✅ Complete RBAC functionality validated
- ✅ Security features (MFA, WebAuthn) working
- ✅ Core features (notifications, storage, queues) functional
- ✅ OAuth2 RFC compliance verified

This comprehensive test suite ensures your FastAPI Laravel application can handle production loads while maintaining functionality and security across all features.