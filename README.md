# FastAPI Laravel-Style Project with Strict Type Checking

A FastAPI application built with Laravel-style project structure and comprehensive type safety using mypy.

## 🎯 Features

- **Laravel-style architecture**: Controllers, Services, Models, Middleware
- **PostgreSQL Database**: Production-ready database with connection pooling
- **Strict Type Checking**: Complete mypy coverage with `--strict` mode
- **Authentication System**: JWT-based auth with roles and permissions (Spatie-like)
- **Permission System**: Role-based access control similar to Laravel Spatie
- **Type Safety**: Comprehensive type hints throughout the codebase
- **Code Quality**: Pre-commit hooks, formatting, and linting
- **CI/CD Ready**: GitHub Actions for type checking and quality assurance

## 📁 Project Structure

```
fastapilaravel/
├── app/
│   ├── Http/
│   │   ├── Controllers/       # Request handlers
│   │   ├── Middleware/        # Authentication & permissions
│   │   └── Schemas/           # Pydantic models
│   ├── Models/                # SQLAlchemy models
│   ├── Services/              # Business logic layer
│   └── Utils/                 # Utility functions
├── routes/                    # API route definitions
├── config/                    # Configuration files
├── database/
│   ├── migrations/            # Database models
│   └── seeders/              # Database seeders
├── storage/                   # File storage
├── scripts/                   # Utility scripts
├── stubs/                     # Type stubs for external libraries
└── .github/workflows/         # CI/CD pipelines
```

## 🗄️ Database Setup

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

## 🚀 Quick Start

### Prerequisites

- Python 3.9+ (recommended: Python 3.12)
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd fastapilaravel

# Install dependencies
make install
# or
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Create database tables and seed data
make db-seed

# Start development server
make dev
# or
uvicorn main:app --reload
```

## 🔍 Type Checking

This project uses strict type checking with mypy. All code must pass type checks.

### Run Type Checking

```bash
# Basic type checking
make type-check

# Strict type checking (CI mode)
make type-check-strict

# Generate type coverage report
make type-coverage
```

### Type Checking Features

- **Strict mode enabled**: `--strict` flag for maximum type safety
- **Generic types**: Proper use of `TypeVar`, `Generic`, and `Mapping`
- **Forward references**: Using `from __future__ import annotations`
- **TYPE_CHECKING imports**: Avoiding circular imports
- **Comprehensive stubs**: Type stubs for external dependencies

## 🛡️ Authentication & Permissions

### User Management

```python
# Register user
POST /api/v1/auth/register
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123"
}

# Login
POST /api/v1/auth/login
{
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

### Role & Permission System

```python
# Check user permissions (like Spatie Laravel Permission)
user.can("create-posts")                    # Check single permission
user.has_role("admin")                      # Check single role
user.has_any_permission(["create", "edit"]) # Check multiple permissions
user.has_all_roles(["admin", "editor"])     # Check multiple roles

# Assign roles and permissions
user.assign_role(admin_role)
user.give_permission_to(create_permission)
role.give_permission_to(permission)
```

### Middleware Protection

```python
# Using dependencies
@app.get("/admin", dependencies=[Depends(can("view-dashboard"))])
async def admin_only(): ...

@app.get("/super", dependencies=[Depends(is_role("super-admin"))])
async def super_admin_only(): ...

# Multiple permissions
@app.get("/content", dependencies=[Depends(has_any_permission(["create-posts", "edit-posts"]))])
async def content_manager(): ...
```

## 🛠️ Development

### Code Quality

```bash
# Format code
make format

# Check formatting
make format-check

# Run all linting
make lint

# Install pre-commit hooks
make install-hooks
```

### Type Safety Examples

```python
# Proper type annotations
from typing import List, Optional, Dict, Any, TypeVar, Generic

T = TypeVar('T', bound=BaseModel)

class BaseService:
    def create(self, model_class: Type[T], data: Dict[str, Any]) -> T:
        instance = model_class(**data)
        # ...
        return instance

# Forward references
from __future__ import annotations

class User(BaseModel):
    roles: Mapped[List[Role]] = relationship(...)  # Forward reference

# Strict return types
def get_user(user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
```

### API Endpoints

**Authentication:**
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/profile` - Get user profile
- `POST /api/v1/auth/logout` - Logout user

**Permissions:**
- `GET /api/v1/permissions/` - List permissions
- `POST /api/v1/permissions/` - Create permission
- `PUT /api/v1/permissions/{id}` - Update permission
- `DELETE /api/v1/permissions/{id}` - Delete permission

**Roles:**
- `GET /api/v1/roles/` - List roles
- `POST /api/v1/roles/` - Create role
- `POST /api/v1/roles/{id}/permissions` - Assign permissions to role
- `POST /api/v1/roles/assign-to-user` - Assign roles to user

## 📊 Type Coverage

The project maintains high type coverage:

```bash
# Generate detailed coverage report
make type-coverage

# View report in type_coverage/index.html
```

## 🔧 Configuration

### MyPy Configuration (`mypy.ini`)

```ini
[mypy]
python_version = 3.12
strict = True
warn_return_any = True
disallow_any_generics = True
disallow_untyped_defs = True
# ... more strict settings
```

### Environment Variables

See `.env.example` for all configuration options:

```bash
APP_NAME="FastAPI Laravel"
DEBUG=true
DATABASE_URL="postgresql://postgres:password@localhost:5432/fastapilaravel"
SECRET_KEY="your-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES=30
# ... more settings
```

## 📝 Available Commands

```bash
make help              # Show all available commands
make install           # Install dependencies
make type-check        # Run type checking
make format            # Format code
make dev               # Start development server
make db-seed           # Seed database
make clean             # Clean generated files
```

## 🔬 CI/CD

GitHub Actions automatically:
- ✅ Runs type checking on multiple Python versions
- ✅ Validates strict type compliance
- ✅ Checks code formatting
- ✅ Generates type coverage reports
- ✅ Runs security checks

## 📚 Type Safety Benefits

1. **Catch Errors Early**: Type errors caught at development time
2. **Better IDE Support**: Enhanced autocomplete and refactoring
3. **Self-Documenting**: Types serve as documentation
4. **Easier Maintenance**: Safer refactoring and changes
5. **Team Collaboration**: Clear interfaces and contracts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with proper type annotations
4. Run `make ci` to ensure all checks pass
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.