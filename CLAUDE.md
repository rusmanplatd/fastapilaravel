# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Development Server
```bash
make dev              # Start development server with auto-reload
make dev-debug        # Start with debug logging
```

### Type Checking (CRITICAL)
This project enforces strict type checking with mypy. Always run type checks before committing:
```bash
make type-check       # Basic type checking using scripts/type_check.py
make type-check-strict # Strict mypy checking (CI mode)
make type-coverage    # Generate HTML type coverage report
```

### Code Quality
```bash
make format           # Format with black and isort (line-length 100)
make format-check     # Check formatting without changes
make lint             # Run format-check + type-check
make ci               # Full CI pipeline (format-check + type-check + test)
```

### Database Operations
```bash
make db-seed          # Seed all default data (users, permissions, oauth2)
make db-seed-oauth2   # Seed only OAuth2 clients and scopes
make db-reset         # Delete SQLite database file
```

### Project Management
```bash
make install          # Install production dependencies
make install-dev      # Install dev dependencies (black, isort, pre-commit)
make clean            # Remove cache, build artifacts
make help             # Show all available commands
```

## Architecture Overview

This is a **FastAPI application with Laravel-style architecture** and **complete OAuth2 implementation**.

### Core Structure
- **Laravel MVC Pattern**: Controllers handle requests, Services contain business logic, Models define data
- **Strict Type Safety**: All code must pass `mypy --strict` checks
- **OAuth2 Server**: Full RFC-compliant implementation with all grant types
- **Role-Based Access Control**: Spatie Laravel Permission-style system

### Directory Layout
```
app/Http/Controllers/     # Request handlers (AuthController, OAuth2*Controller)
app/Http/Middleware/      # Auth, CORS, OAuth2, Permission middleware  
app/Http/Schemas/         # Pydantic request/response models
app/Models/               # SQLAlchemy models with relationships
app/Services/             # Business logic (AuthService, OAuth2*Service)
app/Utils/                # JWT, OAuth2, Password utilities
routes/                   # Router definitions (api.py, oauth2.py, etc)
config/                   # Settings, database config, oauth2 config
database/migrations/      # Table creation scripts
database/seeders/         # Data seeding scripts
```

### Key Components

**OAuth2 Implementation**: Complete server with Authorization Code (+ PKCE), Client Credentials, Password, and Refresh Token grants. Metadata available at `/.well-known/oauth-authorization-server`.

**Authentication Flow**: JWT-based auth + OAuth2. Use `/api/v1/auth/login` for JWT or `/oauth/token` for OAuth2 tokens.

**Permission System**: Spatie-like roles and permissions with methods like `user.can()`, `user.has_role()`, `user.has_any_permission()`.

## Type Safety Requirements

### Critical Rules
1. **All functions must have type annotations** - return types and parameters
2. **Use forward references**: `from __future__ import annotations` 
3. **Generic types**: Properly type `List`, `Dict`, `Optional`, `TypeVar`
4. **Strict mypy**: Code must pass `mypy --strict` checks
5. **Type stubs**: Available in `stubs/` for external libraries

### Type Checking Integration
- Custom type checking script: `scripts/type_check.py`
- Configuration in both `mypy.ini` and `pyproject.toml`
- Pre-commit hooks enforce type checking
- CI/CD runs strict type validation

## Development Workflow

1. **Always run type checks**: Use `make type-check` before any commit
2. **Follow existing patterns**: Check neighboring files for conventions
3. **Use Services for business logic**: Keep Controllers thin
4. **Maintain strict types**: No `Any` types without justification
5. **Test OAuth2 flows**: Use `/docs` for interactive API testing

## OAuth2 Specific Notes

- **Clients**: Seeded via `database/seeders/oauth2_seeder.py`
- **Scopes**: Defined in `config/oauth2.py` settings
- **Grant Types**: All major OAuth2 flows implemented
- **PKCE**: Required by default for Authorization Code flow
- **Token Storage**: SQLAlchemy models for all token types
- **Introspection**: RFC 7662 compliant token introspection endpoint

## Queue System

Complete Laravel-style queue implementation for background job processing.

### Queue Commands
```bash
# Basic Operations
make queue-work                 # Start default queue worker
make queue-work-emails          # Start worker for emails queue
make queue-work-notifications   # Start worker for notifications queue
make queue-stats               # Show queue statistics
make queue-failed              # List failed jobs
make queue-retry-failed        # Retry all failed jobs
make queue-clear               # Clear queue (with confirmation)

# Advanced Monitoring & Management
make queue-dashboard           # Real-time monitoring dashboard
make queue-metrics            # Detailed analytics & performance
make queue-health             # Health check & diagnostics  
make queue-top                # htop-style process monitor

# Examples & Demos
make queue-example            # Basic queue usage examples
make queue-advanced-example   # Advanced features demonstration
```

### Job Creation
Create jobs by inheriting from `app.Jobs.Job`:
```python
from app.Jobs.Job import Job

class SendEmailJob(Job):
    def __init__(self, to_email: str, subject: str, body: str):
        super().__init__()
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.options.queue = "emails"
    
    def handle(self) -> None:
        # Job logic here
        pass
    
    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()
        data["data"] = {"to_email": self.to_email, ...}
        return data
```

### Job Dispatching
```python
# Basic dispatch
job_id = SendEmailJob.dispatch("user@example.com", "Subject", "Body")

# With options
job_id = SendEmailJob("user@example.com", "Subject", "Body") \
    .on_queue("high-priority") \
    .delay_until(60) \
    .with_priority(10) \
    .dispatch()

# Conditional dispatch
SendEmailJob.dispatch_if(condition, ...)
SendEmailJob.dispatch_unless(condition, ...)

# Immediate execution (no queue)
SendEmailJob.dispatch_now(...)
```

### Advanced Features

#### Job Batching
```python
from app.Jobs.Batch import batch, BatchableJob

# Create batchable job
class ProcessDataJob(BatchableJob):
    def _handle(self): # Use _handle instead of handle
        # Job logic here
        pass

# Dispatch batch
batch_id = batch([
    ProcessDataJob("data1"),
    ProcessDataJob("data2"),
    ProcessDataJob("data3")
]).name("Data Processing").allow_failures(1).dispatch()
```

#### Job Chaining
```python
from app.Jobs.Chain import chain, ChainableJob

# Sequential job execution
chain_id = chain([
    ExtractDataJob(),
    TransformDataJob(), 
    LoadDataJob(),
    NotifyCompletionJob()
]).name("ETL Pipeline").dispatch()
```

#### Rate Limiting
```python
from app.Jobs.RateLimiter import RateLimit, RateLimited

class EmailJob(Job, RateLimited):
    def get_rate_limits(self):
        return [RateLimit(max_attempts=100, per_seconds=3600)] # 100/hour
```

#### Job Middleware
```python
from app.Jobs.Middleware import MiddlewareStack, LoggingMiddleware

# Apply middleware to jobs
middleware = MiddlewareStack()
middleware.add(LoggingMiddleware())
middleware.add(ThrottleMiddleware())
```

#### Security & Encryption
```python
from app.Jobs.Security import SecureJob

class SecureDataJob(SecureJob):
    def __init__(self, sensitive_data):
        super().__init__()
        self.set_sensitive_fields(["sensitive_data"])
        self.set_required_permissions(["process_data"])
```

#### Queue Configurations
```python
from app.Queue.QueueManager import define_queue

# Define specialized queues
define_queue("high-priority", 
    connection="redis",
    max_jobs=1000,
    rate_limit_enabled=True)
```

### Queue Architecture
- **Models**: `jobs`, `failed_jobs`, `job_batches`, `job_metrics` tables
- **Worker**: `app.Queue.Worker.QueueWorker` with middleware support
- **Service**: `app.Services.QueueService` with advanced management
- **Drivers**: Database and Redis queue drivers
- **Security**: Job encryption, signing, and access control
- **Monitoring**: Real-time metrics, performance tracking
- **Batching**: Bulk job processing with progress tracking
- **Chaining**: Sequential job workflows
- **Events**: Lifecycle hooks and event system

## Testing

Currently tests are not implemented (placeholders in Makefile). When adding tests:
- Use pytest (already in type stub dependencies)
- Test OAuth2 flows comprehensively
- Maintain type annotations in test files
- Run `make ci` for full validation pipeline