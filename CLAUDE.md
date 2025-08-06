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

## Testing

Currently tests are not implemented (placeholders in Makefile). When adding tests:
- Use pytest (already in type stub dependencies)
- Test OAuth2 flows comprehensively
- Maintain type annotations in test files
- Run `make ci` for full validation pipeline