# Laravel-Style Authorization

FastAPI Laravel includes a complete authorization system that closely mimics Laravel's Gates and Policies, providing fine-grained access control for your application.

## Overview

The authorization system consists of three main components:

1. **Gates** - Define authorization logic for specific abilities
2. **Policies** - Group authorization logic around models/resources  
3. **Middleware** - Automatic authorization checking for routes

## Architecture

### Core Components

```
app/
├── Auth/
│   └── Gate.py                    # Main Gate class and global functions
├── Policies/
│   ├── Policy.py                  # Base Policy class with advanced features
│   ├── PostPolicy.py              # Example policy for Post model
│   └── UserPolicy.py              # Example policy for User model
└── Http/
    └── Middleware/
        └── AuthorizationMiddleware.py  # FastAPI authorization middleware
```

## Quick Start

### 1. Define a Policy

```python
from app.Policies.Policy import Policy

class PostPolicy(Policy):
    def view(self, user, post):
        """Anyone can view published posts, authors can view their own."""
        if post.is_published:
            return True
        return user and user.id == post.author_id
    
    def update(self, user, post):
        """Authors can edit their own posts, editors can edit any."""
        if not user:
            return False
        
        if user.id == post.author_id:
            return True
        
        return user.can('edit_posts')
    
    def delete(self, user, post):
        """Only authors can delete their unpublished posts."""
        if not user or post.is_published:
            return False
        
        return user.id == post.author_id
```

### 2. Register the Policy

```python
from app.Auth.Gate import gate_instance
from app.Policies.PostPolicy import PostPolicy
from app.Models.Post import Post

# Register policy with gate
gate_instance.policy(Post, PostPolicy)
```

### 3. Use Authorization in Routes

```python
from fastapi import FastAPI, HTTPException, Depends
from app.Auth.Gate import gate_instance
from app.Http.Middleware.AuthorizationMiddleware import authorize, require_abilities

app = FastAPI()

@app.get("/posts/{post_id}")
@authorize(abilities=["view_posts"])
async def view_post(post_id: str, current_user=Depends(get_current_user)):
    post = get_post(post_id)
    
    # Additional check using gate directly
    if not gate_instance.allows('view', post, user=current_user):
        raise HTTPException(status_code=403, detail="Cannot view this post")
    
    return {"post": post}
```

## Gates

Gates provide a simple way to determine if a user is authorized to perform an action.

### Defining Abilities

```python
from app.Auth.Gate import gate_instance

# Simple ability check
gate_instance.define('update_settings', lambda user: user.is_admin)

# More complex ability with arguments
def can_edit_post(user, post):
    if not user:
        return False
    return user.id == post.author_id or user.can('edit_posts')

gate_instance.define('edit_post', can_edit_post)
```

### Using Gates

```python
from app.Auth.Gate import gate_instance, for_user

# Global gate usage
if gate_instance.allows('update_settings', user=current_user):
    # User can update settings
    pass

# User-specific gate
user_gate = for_user(current_user)
if user_gate.allows('edit_post', post):
    # User can edit this post
    pass

# Authorize or throw exception
gate_instance.authorize('edit_post', post, user=current_user)
```

### Gate Methods

- `allows(ability, arguments, user)` - Check if allowed
- `denies(ability, arguments, user)` - Check if denied
- `check(abilities, arguments, user)` - Check multiple abilities (all must pass)
- `any(abilities, arguments, user)` - Check if any ability is allowed
- `authorize(ability, arguments, user)` - Authorize or throw exception
- `inspect(ability, arguments, user)` - Get detailed authorization response

## Policies

Policies group authorization logic around a particular model or resource.

### Standard Policy Methods

Laravel convention names for CRUD operations:

- `viewAny(user)` - Can view any instances of the model
- `view(user, model)` - Can view this specific instance
- `create(user)` - Can create new instances
- `update(user, model)` - Can update this instance
- `delete(user, model)` - Can delete this instance
- `restore(user, model)` - Can restore soft-deleted instance
- `forceDelete(user, model)` - Can permanently delete instance

### Advanced Policy Features

#### Before/After Hooks

```python
class PostPolicy(Policy):
    def before(self, user, ability, *args, context=None):
        """Run before all other checks."""
        # Super admin can do anything
        if user and user.is_super_admin:
            return True
        return None  # Continue with normal checks
    
    def after(self, user, ability, result, *args, context=None):
        """Run after all other checks."""
        # Could modify result or add logging
        return None  # Keep original result
```

#### Policy Rules with Decorators

```python
from app.Policies.Policy import policy_rule

class PostPolicy(Policy):
    @policy_rule("rate_limit", allow=False, message="Rate limit exceeded")
    def _rate_limit_rule(self, user, context=None):
        """Custom rule to rate limit actions."""
        if user.actions_today > 100:
            return True  # Trigger the rule (deny)
        return False
    
    def update(self, user, post):
        # Rule will be checked automatically
        return user.id == post.author_id
```

#### Caching Results

```python
from app.Policies.Policy import cache_result
from datetime import timedelta

class PostPolicy(Policy):
    @cache_result(ttl=timedelta(minutes=10))
    def view(self, user, post):
        """Cached for 10 minutes."""
        return post.is_published or (user and user.id == post.author_id)
```

#### Context-Aware Authorization

```python
from app.Policies.Policy import PolicyContext

class PostPolicy(Policy):
    def update(self, user, post, context=None):
        if not user:
            return False
        
        # Check request context
        if context:
            # Different rules for API vs web interface
            if context.get_metadata('interface') == 'api':
                return user.can('api_edit_posts')
        
        return user.id == post.author_id
```

## Middleware Integration

### Authorization Middleware

The authorization middleware automatically checks route permissions:

```python
from fastapi import FastAPI
from app.Http.Middleware.AuthorizationMiddleware import AuthorizationMiddleware

app = FastAPI()
app.add_middleware(AuthorizationMiddleware)
```

### Route Decorators

```python
from app.Http.Middleware.AuthorizationMiddleware import (
    authorize, require_abilities, require_roles, admin_only, authorize_resource
)

# Require specific abilities
@app.get("/admin/dashboard")
@require_abilities("view_dashboard", "manage_users")
async def admin_dashboard():
    return {"message": "Admin dashboard"}

# Require specific roles
@app.get("/moderator/panel")
@require_roles("moderator", "admin")
async def moderator_panel():
    return {"message": "Moderator panel"}

# Admin only
@app.get("/super-admin")
@admin_only()
async def super_admin_area():
    return {"message": "Super admin area"}

# Resource-based authorization
@app.put("/posts/{post_id}")
@authorize_resource(Post, ability="update", param="post_id")
async def update_post(post_id: str):
    return {"message": "Post updated"}

# Custom authorization
@authorize(custom=lambda req, user: user and user.is_verified)
@app.get("/verified-only")
async def verified_users_only():
    return {"message": "Verified users only"}
```

## Resource Authorization

### Model-Based Policies

```python
# Register policies for automatic resolution
gate_instance.policy(Post, PostPolicy)
gate_instance.policy(User, UserPolicy)

# Now you can use model instances directly
post = Post.find(1)
if gate_instance.allows('update', post, user=current_user):
    # User can update this post
    pass
```

### Resource Loading

```python
@app.get("/posts/{post_id}/edit")
@authorize_resource(Post, ability="update", param="post_id")
async def edit_post(post_id: str):
    # Middleware automatically:
    # 1. Loads the post using post_id
    # 2. Checks the 'update' ability
    # 3. Raises 403 if not authorized
    # 4. Raises 404 if post not found
    return {"message": "Edit form"}
```

## Error Handling

### Authorization Exceptions

```python
from app.Auth.Gate import AuthorizationException

try:
    gate_instance.authorize('delete', post, user=current_user)
except AuthorizationException as e:
    # Handle authorization failure
    return {"error": e.detail, "status_code": e.status_code}
```

### Custom Error Responses

```python
@app.exception_handler(AuthorizationException)
async def authorization_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": "AUTHORIZATION_FAILED",
            "timestamp": time.time()
        }
    )
```

## Advanced Usage

### User-Specific Gates

```python
from app.Auth.Gate import for_user

# Create gate for specific user
user_gate = for_user(current_user)

# Check multiple abilities
content_abilities = ['create_posts', 'edit_posts', 'delete_posts']
if user_gate.any(content_abilities):
    # User has at least one content management ability
    pass

# Check that user has none of the admin abilities
admin_abilities = ['manage_users', 'view_logs', 'change_settings']
if user_gate.none(admin_abilities):
    # User is not an admin
    pass
```

### Conditional Authorization

```python
# Gates support conditional logic
def can_publish_post(user, post):
    if not user:
        return False
    
    # Authors can publish their own posts
    if user.id == post.author_id:
        return user.can('publish_own_posts')
    
    # Editors can publish any post
    return user.can('publish_any_post')

gate_instance.define('publish_post', can_publish_post)
```

### Policy Inspection

```python
# Get detailed authorization information
response = gate_instance.inspect('update', post, user=current_user)

if response.allowed:
    print("Authorization granted")
    if response.message:
        print(f"Reason: {response.message}")
else:
    print("Authorization denied")
    print(f"Reason: {response.message}")
    print(f"Status: {response.code}")
```

### Dynamic Abilities

```python
# Define abilities based on user attributes
for role in ['admin', 'moderator', 'user']:
    gate_instance.define(
        f'access_{role}_panel',
        lambda user, r=role: user and user.has_role(r)
    )

# Use dynamic abilities
if gate_instance.allows('access_admin_panel', user=current_user):
    # User can access admin panel
    pass
```

## Testing Authorization

### Unit Testing Policies

```python
import pytest
from app.Policies.PostPolicy import PostPolicy
from app.Models.User import User
from app.Models.Post import Post

def test_post_policy_view():
    policy = PostPolicy()
    
    # Test published post (anyone can view)
    published_post = Post(is_published=True)
    assert policy.view(None, published_post) == True
    
    # Test unpublished post (only author can view)
    author = User(id=1)
    unpublished_post = Post(is_published=False, author_id=1)
    
    assert policy.view(author, unpublished_post) == True
    assert policy.view(None, unpublished_post) == False

def test_post_policy_update():
    policy = PostPolicy()
    author = User(id=1)
    other_user = User(id=2)
    post = Post(author_id=1)
    
    # Author can update their own post
    assert policy.update(author, post) == True
    
    # Other users cannot
    assert policy.update(other_user, post) == False
    assert policy.update(None, post) == False
```

### Integration Testing

```python
from fastapi.testclient import TestClient

def test_post_authorization(client: TestClient):
    # Test unauthorized access
    response = client.get("/posts/1")
    assert response.status_code == 403
    
    # Test authorized access
    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/posts/1", headers=headers)
    assert response.status_code == 200
```

## Performance Considerations

### Caching

- Policy results are automatically cached based on user, ability, and resource
- Cache TTL is configurable per policy method
- Cache is automatically invalidated when appropriate

### Lazy Loading

- Policies are only instantiated when needed
- Resource loading is deferred until authorization check
- Database queries are minimized through intelligent caching

### Batch Authorization

```python
# Check authorization for multiple resources efficiently
posts = [post1, post2, post3]
authorized_posts = []

for post in posts:
    if gate_instance.allows('view', post, user=current_user):
        authorized_posts.append(post)
```

## Best Practices

1. **Keep Policies Simple** - Each method should have a single responsibility
2. **Use Before Hooks Sparingly** - Only for admin overrides or special cases
3. **Cache Expensive Checks** - Use `@cache_result` for database-heavy authorization
4. **Test Thoroughly** - Authorization bugs can be security vulnerabilities
5. **Log Authorization Failures** - For security monitoring and debugging
6. **Use Resource Policies** - Group related authorization logic together
7. **Fail Secure** - Default to denying access when in doubt

## Security Considerations

- Never trust client-side authorization checks
- Always re-check authorization on the server side
- Log authorization failures for security monitoring
- Use principle of least privilege
- Regularly audit and review authorization logic
- Consider rate limiting for authorization-sensitive endpoints

## Laravel Compatibility

This authorization system maintains compatibility with Laravel's Gates and Policies:

- Same method names and conventions
- Compatible policy method signatures
- Similar gate functionality and API
- Equivalent authorization patterns and best practices

This makes it easy to port authorization logic from Laravel applications or follow Laravel documentation and tutorials.