# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- dont use name "advanced", "comprehensive", "enhanced", "enhancements", "improved", "enhancement", "laravel" on code
- dont create legacy/backward compatible code when updating/improving

## Database Setup

### PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql
brew services start postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE fastapilaravel;
CREATE USER postgres WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE fastapilaravel TO postgres;
\q
```

### Environment Configuration
Copy `.env.example` to `.env` and configure PostgreSQL connection:
```bash
DB_CONNECTION="postgresql"
DB_HOST="localhost"
DB_PORT=5432
DB_DATABASE="fastapilaravel"
DB_USERNAME="postgres"
DB_PASSWORD="password"
DATABASE_URL="postgresql://postgres:password@localhost:5432/fastapilaravel"
```

### Docker Development Setup (Recommended)
Use Docker Compose for easy PostgreSQL setup:
```bash
# Start PostgreSQL containers (dev + test databases)
docker-compose -f docker-compose.dev.yml up -d

# Check container status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs postgres

# Stop containers
docker-compose -f docker-compose.dev.yml down
```

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
make db-reset         # Reset PostgreSQL database (drop and recreate tables)
make db-migrate       # Run database migrations
make db-status        # Show database connection status
```

### Job Scheduling & Cron
```bash
make schedule-run           # Run scheduled commands that are due
make schedule-list          # List all scheduled commands
make schedule-work          # Start the schedule worker
make schedule-install       # Install scheduler in system cron
make schedule-uninstall     # Remove scheduler from system cron
make schedule-status        # Show scheduler status and health
make schedule-report        # Generate comprehensive schedule report
make schedule-discover      # Auto-discover scheduled events
make schedule-logs          # View recent schedule execution logs
make schedule-cleanup       # Clean up old schedule logs
make schedule-test CMD=name # Test a specific scheduled command
```

### Project Management
```bash
make install          # Install production dependencies
make install-dev      # Install dev dependencies (black, isort, pre-commit)
make clean            # Remove cache, build artifacts
make help             # Show all available commands
```

## Architecture Overview

This is a **FastAPI application with complete Laravel 12-style architecture** and **comprehensive enterprise features** updated for 2025 using **PostgreSQL** as the primary database.

### Core Structure
- **Laravel Application Foundation**: Full Laravel-style Application class with service container, providers, and dependency injection
- **Laravel MVC Pattern**: Controllers handle requests, Services contain business logic, Models define data
- **Service Container**: Laravel-style dependency injection with singleton bindings and auto-resolution
- **Service Providers**: Modular service registration and bootstrapping
- **Configuration Management**: Laravel-style config repository with dot notation access
- **Logging System**: Multi-channel logging with Laravel-style formatters
- **Hash Manager**: Multiple hashing drivers (bcrypt, argon2, pbkdf2) with auto-rehashing
- **Filesystem Manager**: Multi-disk file operations with Laravel-style API
- **Helper Functions**: 100+ Laravel-style global helper functions
- **Strict Type Safety**: All code must pass `mypy --strict` checks
- **OAuth2 Server**: Full RFC-compliant implementation with 21+ RFC standards including all grant types, security extensions, and modern OAuth2 features
- **Role-Based Access Control**: Spatie Laravel Permission-style system

### Directory Layout
```
app/Broadcasting/         # Real-time event broadcasting (Pusher, WebSocket)
app/Cache/                # Multi-driver caching system (Array, File, Redis)
app/Config/               # Configuration repository with dot notation access
app/Console/              # Artisan-style commands and code generation
app/Events/               # Event classes and dispatcher
app/Filesystem/           # Multi-disk filesystem management (Local, S3, FTP)
app/Foundation/           # Laravel-style Application class and core foundation
app/Hash/                 # Password hashing with multiple drivers
app/Helpers/              # 100+ Laravel-style global helper functions
app/Http/Controllers/     # Request handlers (AuthController, OAuth2*Controller)
app/Http/Middleware/      # Auth, CORS, OAuth2, Permission middleware
app/Http/Requests/        # Laravel-style Form Request validation
app/Http/Resources/       # API resource transformers
app/Http/Schemas/         # Pydantic request/response models
app/Listeners/            # Event listeners
app/Log/                  # Multi-channel logging system
app/Mail/                 # Mailable classes for emails
app/Models/               # SQLAlchemy models with observers and scopes
app/Observers/            # Model observers for lifecycle events
app/Policies/             # Authorization policies and gates
app/Providers/            # Service providers for dependency injection
app/RateLimiting/         # Rate limiting with multiple stores
app/Routing/              # Advanced routing and middleware groups
app/Services/             # Business logic (AuthService, OAuth2*Service)
app/Storage/              # File storage abstraction (Local, S3)
app/Support/              # Core support classes (Container, Facades, Collections)
app/Testing/              # Laravel-style testing utilities
app/Utils/                # JWT, OAuth2, Password utilities
app/Validation/           # Custom validation rules
config/                   # Configuration files (database, logging, filesystems, etc.)
database/factories/       # Model factories with Faker integration
database/migrations/      # Table creation scripts
database/Schema/          # Schema builder for migrations
database/seeders/         # Data seeding scripts
resources/views/emails/   # Email templates (HTML)
```

### Key Components

**Laravel Application Foundation**: Complete Laravel-style Application class with service container, provider registration, and bootstrapping lifecycle.

**Service Container**: Powerful dependency injection container with automatic resolution, singleton bindings, and contextual binding support.

**Configuration System**: Laravel-style configuration repository with support for environment variables, dot notation access, and multiple file formats.

**Logging System**: Multi-channel logging with support for single files, daily rotation, syslog, stderr, and custom formatters (Laravel and JSON).

**Hash Manager**: Multiple password hashing drivers including bcrypt, argon2, pbkdf2, with automatic rehashing and password strength validation.

**Filesystem Manager**: Multi-disk file operations supporting local, S3, FTP with Laravel-style API for file manipulation, streaming, and metadata.

**Helper Functions**: Comprehensive set of 100+ Laravel-style global helper functions for strings, arrays, paths, encryption, validation, and more.

**PostgreSQL Database**: Production-ready PostgreSQL database with connection pooling, migrations, and optimized queries.

**OAuth2 Implementation**: Complete server with Authorization Code (+ PKCE), Client Credentials, Password, and Refresh Token grants. Metadata available at `/.well-known/oauth-authorization-server`.

**Authentication Flow**: JWT-based auth + OAuth2. Use `/api/v1/auth/login` for JWT or `/oauth/token` for OAuth2 tokens.

**Permission System**: Spatie-like roles and permissions with methods like `user.can()`, `user.has_role()`, `user.has_any_permission()`.

## Laravel 12 Type Safety Requirements

### Laravel 12 Enhanced Type System
1. **Strict Type Checking**: All functions must have complete type annotations (return types and parameters)
2. **Future Annotations**: Uses `from __future__ import annotations` for forward compatibility
3. **Generic Types**: Properly typed `List`, `Dict`, `Optional`, `TypeVar`, `final` decorators
4. **Strict Mypy Mode**: Code must pass `mypy --strict` checks with zero tolerance for `Any` types
5. **Type Stubs**: Available in `stubs/` for external libraries
6. **Laravel 12 Features**: Enhanced service container, routing, and ORM with strict typing

### Type Checking Integration
- Enhanced type checking scripts: `scripts/type_check.py`, `scripts/add_strict_typing.py`
- Laravel 12 compatible configuration in both `mypy.ini` and `pyproject.toml`
- Automated type annotation addition for legacy code
- Pre-commit hooks enforce strict type checking
- CI/CD runs ultra-strict type validation with Laravel 12 standards

## Laravel 12 Development Workflow

1. **Enhanced Type Checking**: Use `make type-check-strict` for Laravel 12 compliance
2. **Automatic Type Addition**: Run `python3 scripts/add_strict_typing.py` for new files
3. **Follow Laravel 12 Patterns**: Check neighboring files for modern conventions
4. **Use Enhanced Services**: Keep Controllers thin with Laravel 12 service patterns
5. **Zero-Any Policy**: Strictly no `Any` types - use proper type annotations
6. **Laravel 12 Features**: Utilize enhanced container, routing, and ORM features
7. **Test Comprehensive Flows**: OAuth2, MFA, and all enterprise features

## OAuth2 Specific Notes

- **Clients**: Seeded via `database/seeders/oauth2_seeder.py`
- **Scopes**: Defined in `config/oauth2.py` settings
- **Grant Types**: All major OAuth2 flows implemented
- **PKCE**: Required by default for Authorization Code flow
- **Token Storage**: SQLAlchemy models for all token types
- **Introspection**: RFC 7662 compliant token introspection endpoint

### Complete RFC Standards Implementation

This OAuth2 server implements **21+ RFC standards** for maximum compliance and interoperability:

**Core OAuth2 Standards:**
- **RFC 6749**: OAuth 2.0 Authorization Framework (all grant types)
- **RFC 6750**: Bearer Token Usage
- **RFC 7009**: Token Revocation
- **RFC 7662**: Token Introspection

**Security & PKCE:**
- **RFC 7636**: Proof Key for Code Exchange (PKCE)
- **RFC 8725**: OAuth 2.0 Security Best Practices
- **RFC 8705**: Mutual-TLS Client Authentication
- **RFC 9449**: Demonstrating Proof-of-Possession (DPoP)

**Discovery & Metadata:**
- **RFC 8414**: Authorization Server Metadata
- **RFC 9207**: Authorization Server Issuer Identification

**Grant Extensions:**
- **RFC 8628**: Device Authorization Grant
- **RFC 8693**: Token Exchange
- **RFC 7523**: JWT Bearer Token Grant

**Client Management:**
- **RFC 7591**: Dynamic Client Registration
- **RFC 7592**: Dynamic Client Registration Management

**Resource & Authorization:**
- **RFC 8707**: Resource Indicators
- **RFC 9126**: Pushed Authorization Requests (PAR)
- **RFC 9396**: Rich Authorization Requests

**JWT & Token Profiles:**
- **RFC 9068**: JWT Access Token Profile

**Security Events:**
- **RFC 8417**: Security Event Tokens (SET)

**Mobile & Native:**
- **RFC 8252**: OAuth2 for Native Apps

### RFC Compliance Validation

Access comprehensive RFC compliance validation via these endpoints:

```bash
# Get overall compliance report
curl http://localhost:8000/oauth/compliance/report

# Get compliance summary with scores
curl http://localhost:8000/oauth/compliance/summary

# Validate specific RFC (e.g., RFC 6749)
curl http://localhost:8000/oauth/compliance/validate/RFC%206749

# Get list of all implemented RFCs
curl http://localhost:8000/oauth/compliance/rfcs

# Get compliance score and recommendations
curl http://localhost:8000/oauth/compliance/score
curl http://localhost:8000/oauth/compliance/recommendations

# Get detailed metrics and analytics
curl http://localhost:8000/oauth/compliance/metrics
```

### Security Event Token Endpoints (RFC 8417)

Access Security Event Token functionality for security incident communication:

```bash
# Get security event capabilities
curl http://localhost:8000/oauth/security-events/capabilities

# Get supported event types
curl http://localhost:8000/oauth/security-events/event-types

# Create a token revocation event
curl -X POST http://localhost:8000/oauth/security-events/token-revoked \
  -d "client_id=your_client_id" \
  -d "token_id=token_123" \
  -d "token_type=access_token" \
  -d "reason=user_action"

# Create a credential compromise event
curl -X POST http://localhost:8000/oauth/security-events/credential-compromise \
  -d "client_id=your_client_id" \
  -d "compromise_type=leaked"

# Create a suspicious login event
curl -X POST http://localhost:8000/oauth/security-events/suspicious-login \
  -d "user_id=user_123" \
  -d "client_id=your_client_id" \
  -d "suspicious_indicators=unusual_location,new_device"

# Subscribe to security events
curl -X POST http://localhost:8000/oauth/security-events/subscribe \
  -d "client_id=your_client_id" \
  -d "webhook_url=https://your-app.com/security-events" \
  -d "event_types=token_revoked,credential_compromise"

# Validate a Security Event Token
curl -X POST http://localhost:8000/oauth/security-events/validate \
  -d "set_token=your_set_token"
```

### Dynamic Client Registration Endpoints (RFC 7591/7592)

Manage OAuth2 clients dynamically:

```bash
# Register a new client
curl -X POST http://localhost:8000/oauth/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "My App",
    "client_uri": "https://myapp.com",
    "redirect_uris": ["https://myapp.com/callback"],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "scope": "read write"
  }'

# Get client configuration
curl -H "Authorization: Bearer registration_access_token" \
  http://localhost:8000/oauth/register/client_id

# Update client configuration
curl -X PUT http://localhost:8000/oauth/register/client_id \
  -H "Authorization: Bearer registration_access_token" \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Updated App Name"}'

# Delete client registration
curl -X DELETE http://localhost:8000/oauth/register/client_id \
  -H "Authorization: Bearer registration_access_token"
```

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

### Laravel-Style Pagination System

Complete pagination implementation with multiple pagination strategies:

```python
from app.Pagination import (
    LengthAwarePaginator, CursorPaginator, SimplePaginator,
    PaginationDep, create_model_pagination_dependency,
    PaginationMiddleware, PaginationResponse
)

# FastAPI route with automatic pagination
@app.get("/posts")
async def get_posts(
    request: Request,
    pagination: PaginationDep = Depends(BasicPagination),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    query = db.query(Post).order_by(Post.created_at.desc())
    paginator = query_paginator.paginate(query, pagination.page, pagination.per_page, request)
    
    return PaginationResponse.create([...], paginator)

# Model-specific pagination dependency
PostPagination = create_model_pagination_dependency(
    model_class=Post,
    searchable_fields=['title', 'content'],
    filterable_fields=['author', 'published'],
    sortable_fields=['id', 'title', 'created_at']
)

@app.get("/posts/auto")
async def get_posts_auto(paginated_posts: LengthAwarePaginator = Depends(PostPagination)):
    return PaginationResponse.create([...], paginated_posts)
```

**Pagination Features:**
- **Length-Aware Pagination**: Full pagination with total counts and page navigation
- **Simple Pagination**: Performance-optimized pagination without total counts
- **Cursor Pagination**: Efficient pagination for large datasets
- **Auto-Discovery**: Model-specific dependencies with search, filter, and sort
- **Multiple Formats**: Laravel, JSON:API, and custom response formats
- **Middleware Support**: Automatic headers, caching, and logging
- **FastAPI Integration**: Dependencies, type hints, and async support

### Laravel-Style File Storage and Uploads

Complete file storage system with multiple drivers and comprehensive upload handling:

```python
from app.Storage import (
    Storage, StorageDisk, UploadHandler, UploadConfig,
    ImageUploadDep, DocumentUploadDep, FileManagerDep,
    storage_exists, storage_get, storage_put, storage_url
)

# Configure storage disks
Storage.configure_disk("s3", "s3", bucket="my-bucket", region="us-east-1")
Storage.configure_disk("gcs", "gcs", bucket="my-gcs-bucket", project_id="my-project")
Storage.configure_disk("azure", "azure", account="myaccount", container="files")

# File upload endpoint
@app.post("/upload")
async def upload_file(result: UploadResult = Depends(ImageUploadDep)):
    return {"url": result.url, "path": result.file_path}

# Storage operations
@app.get("/files/{path:path}")
async def download_file(path: str, storage: StorageDisk = Depends()):
    return storage.download_response(path)

# Advanced upload with validation
custom_upload = create_upload_dependency(
    allowed_extensions=[".pdf", ".docx"],
    max_file_size=20 * 1024 * 1024,  # 20MB
    disk="s3"
)
```

**Storage Features:**
- **Multiple Drivers**: Local, S3, Google Cloud, Azure, DigitalOcean, MinIO, FTP
- **Upload Handling**: File validation, processing, and organization
- **Image Processing**: Auto-resize, thumbnail generation, metadata extraction
- **Security**: File type validation, virus scanning, sanitization
- **Laravel Facade**: Unified interface for all storage operations
- **FastAPI Integration**: Dependencies, type hints, and streaming responses
- **Cloud Features**: Presigned URLs, direct uploads, CDN integration

### Storage Commands
```bash
# Storage operations
make storage-link         # Create symbolic link for public storage
make storage-test         # Test storage connections
make storage-cleanup      # Clean up temporary files
make storage-info         # Show storage disk information
make storage-usage        # Show storage usage statistics
make storage-backup       # Backup storage directory
make storage-example      # Run storage example server
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