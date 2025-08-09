# Type Checking Guide

This document describes the enhanced type checking implementation for the FastAPI Laravel project.

## Overview

This project enforces strict type checking using mypy with enhanced rules to ensure code quality and reliability.

## Configuration

### mypy.ini Configuration

The project uses a strict mypy configuration with enhanced rules:

- **Strict Mode**: Enabled for maximum type safety
- **Enhanced Strictness**: Additional rules like `strict_equality`, `strict_concatenate`
- **No Implicit Optional**: All optional parameters must be explicitly typed
- **Disallow Any**: Restricted use of `Any` type in most contexts
- **Progressive Enforcement**: Core modules have stricter rules than legacy modules

### Module-Specific Rules

Different modules have different strictness levels:

#### Strict Modules (Full Type Safety)
- `app/Services/*` - Business logic services
- `app/Models/*` - Data models
- `app/Http/Controllers/*` - HTTP controllers
- `app/Http/Requests/*` - Request validation
- `app/Http/Resources/*` - API resources
- `app/Http/Schemas/*` - Pydantic schemas
- `app/Utils/*` - Utility functions
- `app/Cache/*` - Caching layer
- `app/Queue/*` - Queue system
- `app/Jobs/*` - Background jobs

#### Relaxed Modules (Legacy Support)
- `app/Horizon/*` - Dashboard components
- `app/Telescope/*` - Debug tools
- `app/Socialite/*` - OAuth providers
- `database/migrations/*` - Database migrations

## Type Checking Commands

### Basic Commands

```bash
# Standard type checking
make type-check

# Strict type checking on entire codebase
make type-check-strict

# Enhanced modular type checking
make type-check-enhanced

# Generate type coverage report
make type-coverage

# Clean unused type: ignore comments
make clean-type-ignores
```

### Advanced Commands

```bash
# Check specific module
mypy --strict --config-file=mypy.ini app/Services/

# Check with error codes
mypy --show-error-codes --config-file=mypy.ini app/Services/

# Generate HTML coverage report
mypy --html-report=type_coverage --config-file=mypy.ini app/
```

## Type Safety Best Practices

### 1. Function Signatures

Always provide complete type annotations:

```python
# ✅ Good
def process_data(data: List[Dict[str, Any]], timeout: Optional[int] = None) -> Tuple[bool, str]:
    return True, "Success"

# ❌ Bad
def process_data(data, timeout=None):
    return True, "Success"
```

### 2. Generic Types

Use specific generic types instead of `Any`:

```python
# ✅ Good
from typing import List, Dict, Optional

def get_users() -> List[Dict[str, Union[str, int]]]:
    return [{"id": 1, "name": "John"}]

# ❌ Bad
def get_users() -> List[Dict[str, Any]]:
    return [{"id": 1, "name": "John"}]
```

### 3. Forward References

Use `from __future__ import annotations` for forward references:

```python
from __future__ import annotations

class UserService:
    def get_user(self, user_id: str) -> User:  # Forward reference
        pass
```

### 4. Union Types

Use `Union` or `|` (Python 3.10+) for multiple types:

```python
from typing import Union

def process_id(user_id: Union[str, int]) -> str:
    return str(user_id)

# Python 3.10+
def process_id(user_id: str | int) -> str:
    return str(user_id)
```

### 5. Optional Values

Always use `Optional` for nullable values:

```python
from typing import Optional

# ✅ Good
def find_user(email: str) -> Optional[User]:
    return user or None

# ❌ Bad (with no_implicit_optional=True)
def find_user(email: str) -> User:
    return user or None  # Type error!
```

## Handling Type Errors

### Common Error Types

#### 1. `[no-untyped-def]`
```python
# Error
def process_data(data):
    pass

# Fix
def process_data(data: List[Any]) -> None:
    pass
```

#### 2. `[arg-type]`
```python
# Error
user_id: int = "123"  # String assigned to int

# Fix
user_id: Union[int, str] = "123"
# or
user_id: int = int("123")
```

#### 3. `[return-value]`
```python
# Error
def get_name() -> str:
    return None  # None returned when str expected

# Fix
def get_name() -> Optional[str]:
    return None
```

#### 4. `[attr-defined]`
```python
# Error
request.nonexistent_attr

# Fix - Check if attribute exists or use proper typing
if hasattr(request, 'attr_name'):
    value = request.attr_name
```

### Using Type Ignores (Sparingly)

Only use `# type: ignore` for legitimate cases:

```python
# External library without stubs
import some_external_lib  # type: ignore

# Complex dynamic attribute access
value = getattr(obj, dynamic_attr, None)  # type: ignore[attr-defined]

# Temporary workaround (add TODO)
result = complex_legacy_function()  # type: ignore  # TODO: Fix legacy function typing
```

## Migration Strategy

### Phase 1: Core Services ✅
- Services layer fully typed
- Models with complete annotations
- HTTP layer with proper schemas

### Phase 2: Business Logic (Current)
- Controllers with request/response types
- Middleware with proper signatures
- Queue jobs with typed payloads

### Phase 3: Infrastructure
- Database layer improvements
- Cache layer enhancements
- Logging and monitoring

### Phase 4: Legacy Cleanup
- Horizon dashboard typing
- Telescope debug tools
- Socialite providers

## Tools and Scripts

### Enhanced Type Checker (`scripts/strict_type_check.py`)
- Modular type checking
- Better error reporting
- Progress tracking

### Cleanup Script (`scripts/clean_unused_ignores.py`)
- Removes unused `# type: ignore` comments
- Keeps codebase clean

### Coverage Analysis
- HTML reports with `make type-coverage`
- Identifies untyped code sections

## Integration with Development Workflow

### Pre-commit Hooks
Type checking is enforced via pre-commit hooks:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: mypy
      name: mypy
      entry: make type-check
      language: system
      pass_filenames: false
```

### CI/CD Pipeline
Continuous integration runs strict type checking:

```bash
# In CI pipeline
make type-check-strict
```

### IDE Integration
Configure your IDE for real-time type checking:

- **VS Code**: Python extension with mypy
- **PyCharm**: Built-in type checking
- **Vim/Neovim**: LSP with mypy

## Troubleshooting

### Performance Issues
If type checking is slow:
1. Use `--cache-dir` for mypy cache
2. Run modular checks with `make type-check-enhanced`
3. Exclude problematic directories

### False Positives
For legitimate false positives:
1. Check mypy configuration
2. Update type stubs
3. Use targeted `# type: ignore` with explanation

### Missing Stubs
For missing library stubs:
1. Install from `types-*` packages
2. Add to `[mypy-library.*]` ignore section
3. Contribute stubs to typeshed

## Resources

- [mypy documentation](https://mypy.readthedocs.io/)
- [Typing module documentation](https://docs.python.org/3/library/typing.html)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [FastAPI typing guide](https://fastapi.tiangolo.com/python-types/)