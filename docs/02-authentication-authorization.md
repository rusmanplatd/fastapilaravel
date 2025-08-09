# Authentication & Authorization System

## Authentication Manager

### Current Implementation
Located in `app/Auth/AuthManager.py`, provides Laravel-style multi-guard authentication:

**Guard Types:**
- **Session Guard**: Traditional web authentication with cookies
- **Token Guard**: API authentication with bearer tokens
- **JWT Guard**: JSON Web Token authentication
- **OAuth2 Guard**: OAuth2 bearer token authentication

**Usage:**
```python
from app.Support.Facades import Auth

# Default guard (web)
user = Auth.user()
is_authenticated = Auth.check()

# Specific guard
api_user = Auth.guard('api').user()
jwt_user = Auth.guard('jwt').user()

# Login/logout
Auth.login(user)
Auth.logout()
```

**Guard Configuration:**
```python
guards = {
    "web": {"driver": "session", "provider": "users"},
    "api": {"driver": "token", "provider": "users"}, 
    "jwt": {"driver": "jwt", "provider": "users"},
    "oauth2": {"driver": "oauth2", "provider": "users"}
}
```

### Improvements
1. **Multi-factor authentication integration**: Seamless MFA workflow
2. **Social authentication**: Direct integration with Socialite providers
3. **Remember me functionality**: Persistent login tokens
4. **Session management**: Active session tracking and invalidation
5. **Guard middleware chains**: Composed authentication flows

## Gate System (Authorization)

### Current Implementation
Located in `app/Auth/Gate.py`, implements Laravel's authorization pattern:

**Gate Definition:**
```python
from app.Auth.Gate import Gate

gate = Gate()

# Define abilities
@gate.define('update-post')
def can_update_post(user, post):
    return user.id == post.author_id

# Check abilities
gate.allows('update-post', user, post)
gate.denies('update-post', user, post)

# Before/after callbacks
@gate.before
def super_admin_check(user, ability):
    if user.role == 'super_admin':
        return True
    return None
```

**Response System:**
```python
from app.Auth.Gate import Response

# Allow with message
return Response.allow("User owns this resource")

# Deny with message and code
return Response.deny("Insufficient permissions", 403)
```

### Improvements
1. **Policy auto-discovery**: Automatic policy registration based on model classes
2. **Resource-based policies**: Simplified CRUD authorization
3. **Role-based shortcuts**: Quick role checking without custom gates
4. **Permission inheritance**: Hierarchical permission structures

## Policy System

### Current Implementation
Located in `app/Policies/`, provides model-specific authorization:

**Policy Structure:**
```python
from app.Policies.Policy import Policy

class PostPolicy(Policy):
    def view(self, user, post):
        return post.published or user.id == post.author_id
    
    def create(self, user):
        return user.is_verified
    
    def update(self, user, post):
        return user.id == post.author_id
    
    def delete(self, user, post):
        return user.id == post.author_id or user.is_admin
```

**Advanced Features:**
```python
class Policy:
    # Before hook - runs before all policy methods
    def before(self, user, ability):
        if user.is_super_admin:
            return True
        return None
    
    # Rule-based policies
    def __init__(self):
        self.add_rule('owner', lambda u, resource: u.id == resource.owner_id)
        self.add_rule('admin', lambda u: u.is_admin)
```

### Current Policies:
- `PostPolicy` - Blog post authorization
- `UserPolicy` - User management authorization
- Generic `Policy` base class with rule system

### Improvements
1. **Dynamic policy loading**: Runtime policy registration
2. **Policy caching**: Cache policy results for performance
3. **Audit logging**: Track authorization decisions
4. **Policy testing utilities**: Isolated policy testing tools

## Middleware Integration

### Current Implementation
Located in `app/Http/Middleware/`, provides request-level authorization:

**Authentication Middleware:**
```python
from app.Http.Middleware.AuthMiddleware import AuthMiddleware

# Require authentication
@app.middleware("http")
async def auth_required(request, call_next):
    return await AuthMiddleware.handle(request, call_next)
```

**Permission Middleware:**
```python
from app.Http.Middleware.PermissionMiddleware import PermissionMiddleware

# Require specific permission
@PermissionMiddleware.require('edit-posts')
async def edit_post(request):
    # Only users with 'edit-posts' permission can access
    pass
```

**Available Middleware:**
- `AuthMiddleware` - Authentication checking
- `PermissionMiddleware` - Permission validation
- `AuthorizationMiddleware` - Policy-based authorization
- `MFAMiddleware` - Multi-factor authentication
- `OAuth2Middleware` - OAuth2 token validation

### Improvements
1. **Middleware stacking**: Combine multiple auth middleware
2. **Context-aware middleware**: Dynamic middleware based on route
3. **Performance optimization**: Middleware result caching
4. **Debugging tools**: Authorization decision tracing

## Permission System (Spatie-style)

### Current Implementation
Located in `app/Models/Permission.py` and `app/Models/Role.py`, provides:

**Role-Based Access Control:**
```python
# User model with permissions
class User(BaseModel):
    def has_permission(self, permission):
        return permission in self.get_permissions()
    
    def has_role(self, role):
        return role in self.get_roles()
    
    def can(self, permission):
        return self.has_permission(permission)

# Usage in controllers
if not user.can('edit-posts'):
    raise PermissionDenied("Cannot edit posts")
```

**Role Assignment:**
```python
# Assign roles
user.assign_role('editor')
user.assign_role(['writer', 'reviewer'])

# Remove roles  
user.remove_role('editor')

# Sync roles
user.sync_roles(['admin', 'editor'])
```

**Permission Assignment:**
```python
# Direct permissions
user.give_permission('delete-users')
user.revoke_permission('delete-users')

# Role permissions
role = Role.find_by_name('editor')
role.give_permission('edit-posts')
role.revoke_permission('edit-posts')
```

### Current Models:
- `User` - User with roles and permissions
- `Role` - Role with permissions
- `Permission` - Individual permission

### Improvements
1. **Permission inheritance**: Child permissions from parent permissions
2. **Wildcard permissions**: Pattern-based permission matching  
3. **Time-based permissions**: Temporary permission grants
4. **Permission templates**: Predefined permission sets
5. **Multi-tenancy support**: Scoped permissions per tenant

## Form Request Validation

### Current Implementation
Located in `app/Http/Requests/`, provides Laravel-style request validation:

**Form Request Classes:**
```python
from app.Http.Requests.FormRequest import FormRequest

class CreateUserRequest(FormRequest):
    def authorize(self):
        """Authorization logic"""
        return self.user().can('create-users')
    
    def rules(self):
        """Validation rules"""
        return {
            'name': ['required', 'string', 'max:255'],
            'email': ['required', 'email', 'unique:users'],
            'password': ['required', 'min:8', 'confirmed']
        }
    
    def messages(self):
        """Custom error messages"""
        return {
            'email.unique': 'This email is already taken.'
        }
```

**Usage in Controllers:**
```python
from fastapi import Depends

async def create_user(request: CreateUserRequest = Depends()):
    # Request is automatically validated and authorized
    user_data = request.validated_data
    return UserService.create(user_data)
```

### Improvements
1. **Async validation**: Background validation for heavy rules
2. **Conditional rules**: Rules based on other field values
3. **File validation**: Enhanced file upload validation
4. **Custom rule classes**: Reusable validation logic
5. **Validation caching**: Cache expensive validation results

## Session Management

### Current Implementation
Located in `app/Session/SessionManager.py`, provides:
- Session storage and retrieval
- CSRF protection
- Session regeneration
- Flash data support

### Improvements
1. **Distributed sessions**: Redis/database session storage
2. **Session analytics**: Track user session patterns
3. **Security features**: Session hijacking detection
4. **Multi-device support**: Track sessions per device

## Social Authentication (Socialite)

### Current Implementation
Located in `app/Socialite/`, provides OAuth integration with:

**Supported Providers:**
- GitHub
- Google
- Facebook
- Twitter
- Discord
- LinkedIn

**Usage:**
```python
from app.Socialite import Socialite

# Redirect to provider
redirect_url = Socialite.driver('github').redirect()

# Handle callback
user = Socialite.driver('github').user()
```

### Improvements
1. **More providers**: Add additional OAuth providers
2. **Custom providers**: Easy custom provider creation
3. **Account linking**: Link social accounts to existing users
4. **Provider-specific features**: Leverage unique provider capabilities