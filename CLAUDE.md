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
app/Broadcasting/         # Real-time event broadcasting (Pusher, WebSocket)
app/Cache/                # Multi-driver caching system (Array, File, Redis)
app/Console/              # Artisan-style commands and code generation
app/Events/               # Event classes and dispatcher
app/Http/Controllers/     # Request handlers (AuthController, OAuth2*Controller)
app/Http/Middleware/      # Auth, CORS, OAuth2, Permission middleware
app/Http/Requests/        # Laravel-style Form Request validation
app/Http/Resources/       # API resource transformers
app/Http/Schemas/         # Pydantic request/response models
app/Listeners/            # Event listeners
app/Mail/                 # Mailable classes for emails
app/Models/               # SQLAlchemy models with observers and scopes
app/Observers/            # Model observers for lifecycle events
app/Policies/             # Authorization policies and gates
app/RateLimiting/         # Rate limiting with multiple stores
app/Routing/              # Advanced routing and middleware groups
app/Services/             # Business logic (AuthService, OAuth2*Service)
app/Storage/              # File storage abstraction (Local, S3)
app/Support/              # Core support classes (Container, Facades, Collections)
app/Testing/              # Laravel-style testing utilities
app/Utils/                # JWT, OAuth2, Password utilities
app/Validation/           # Custom validation rules
database/factories/       # Model factories with Faker integration
database/migrations/      # Table creation scripts
database/Schema/          # Schema builder for migrations
database/seeders/         # Data seeding scripts
resources/views/emails/   # Email templates (HTML)
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

## Laravel-Style Features

This codebase now includes **ALL major Laravel features** implemented in FastAPI:

### 🏗️ **Enhanced Eloquent ORM**
- **Model Scopes**: `scope_latest()`, `scope_where_not_null()`, `scope_where_in()`, etc.
- **Model Observers**: Lifecycle event handling (creating, created, updating, updated, etc.)
- **Mass Assignment**: Fillable/guarded protection with `fill()` method
- **Attribute Casting**: Hidden/visible attributes for serialization
- **Query Builder**: Advanced filtering with relationships and includes

### 📝 **Form Requests & Validation**
- **Form Request Classes**: Laravel-style validation with authorization
- **Custom Validation Rules**: Extensible rule system (required, email, min, max, unique)
- **Error Formatting**: Laravel-style validation error responses
- **Request Decorators**: Easy controller integration

### 🎯 **Events & Broadcasting**
- **Event Dispatcher**: Async event handling with listeners
- **Real-time Broadcasting**: WebSocket, Pusher integration
- **Event Queuing**: Background event processing
- **Private/Presence Channels**: Authorized real-time channels

### 📧 **Mail System**
- **Mailable Classes**: Fluent email composition
- **Template System**: Jinja2 templates with layouts
- **Queue Integration**: Background email sending
- **Attachments**: File and data attachment support

### 🏗️ **Service Container & Facades**
- **Dependency Injection**: Auto-resolution with constructor injection
- **Service Binding**: Singleton and instance binding
- **Facades**: Static-like access (Auth, Queue, Event, Cache, Storage)
- **Service Providers**: Modular service registration

### 📊 **API Resources**
- **Resource Transformers**: Laravel-style data transformation
- **Resource Collections**: Pagination and meta data support
- **Conditional Loading**: `when()`, `when_loaded()` methods
- **Custom Serialization**: Hidden/visible attribute control

### 💾 **Storage & Caching**
- **Storage Abstraction**: Multi-driver filesystem (Local, S3)
- **Cache System**: Multiple drivers (Array, File, Redis) with tagging
- **File Operations**: Full CRUD with copy, move, metadata
- **Cache Utilities**: `remember()`, `forever()`, tagged caching

### 🛡️ **Authorization & Security**
- **Policy Classes**: Model-specific authorization logic
- **Gate System**: Global authorization with before/after hooks
- **Rate Limiting**: Multi-store rate limiting with decorators
- **Throttle Middleware**: Request-level rate limiting

### 🧪 **Testing & Development**
- **Database Factories**: Faker-based test data generation
- **Test Utilities**: Laravel-style assertions and helpers
- **Artisan Commands**: Code generation and management commands
- **Collections**: 50+ methods for data manipulation

### 📈 **Advanced Features**
- **Pipeline Processing**: Multi-stage data transformation
- **Configuration Management**: Dot notation config access
- **Middleware Groups**: Organized middleware application
- **Route Caching**: Performance optimization
- **Error Handling**: Comprehensive exception management

## Additional Features

### Activity Logging (Spatie-style)

Laravel-style activity logging with the `LogsActivity` trait for automatic change tracking:

```python
from app.Traits.LogsActivity import LogsActivity, LogOptions

class MyModel(BaseModel, LogsActivity):
    __log_options__ = LogOptions(
        log_name="my_model",
        log_only_changed=True,
        log_attributes=["name", "status"]
    )
```

### Notifications System

Multi-channel notification system supporting Database, Email, SMS, Discord, Slack, Push, and Webhook channels:

```python
from app.Notifications import Notification
from app.Notifications.Channels import DatabaseChannel, MailChannel

class WelcomeNotification(Notification):
    def __init__(self, user_name: str):
        self.user_name = user_name
    
    def via(self, notifiable) -> List[str]:
        return ["database", "mail"]
    
    def to_database(self, notifiable) -> Dict[str, Any]:
        return {"message": f"Welcome {self.user_name}!"}
```

### Multi-Factor Authentication (MFA) & WebAuthn

Complete MFA implementation with TOTP, WebAuthn, SMS, and recovery codes:

- **MFA Services**: `MFAService`, `TOTPService`, `WebAuthnService`, `SMSService`
- **Analytics**: `MFAAnalyticsService` for usage tracking
- **Policy Management**: `MFAPolicyService` for security policies
- **Audit Logging**: `MFAAuditService` for security events

### Query Builder (Spatie-style)

Laravel Query Builder-inspired filtering and querying for FastAPI endpoints:

```python
from app.Utils.QueryBuilder import QueryBuilder, AllowedFilter, AllowedSort

# URL: /users?filter[name]=john&sort=-created_at&include=roles
QueryBuilder.for_model(User, db, request) \
    .allowed_filters([AllowedFilter.partial('name')]) \
    .allowed_sorts(['created_at', 'name']) \
    .allowed_includes(['roles', 'rolesCount']) \
    .get()
```

## Testing

Currently tests are not implemented (placeholders in Makefile). When adding tests:

- Use pytest (already in type stub dependencies)
- Test OAuth2 flows comprehensively
- Test MFA flows and WebAuthn registration/authentication
- Test queue job processing and batching
- Test permission system with all grant types
- Maintain type annotations in test files
- Run `make ci` for full validation pipeline