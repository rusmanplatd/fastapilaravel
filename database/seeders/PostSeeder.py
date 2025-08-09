from __future__ import annotations

import os
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from database.seeders.SeederManager import Seeder
from database.factories.PostFactory import PostFactory
from app.Models.User import User
from app.Models.Post import Post


class PostSeeder(Seeder):
    """
    Laravel-style Post Seeder.
    
    Seeds the database with sample blog posts using factories.
    """
    
    def run(self) -> None:
        """Run the post seeder."""
        
        # Get seeding mode
        mode = os.getenv('SEEDER_MODE', 'normal')
        
        if mode == 'demo':
            self.seed_demo_posts()
        elif mode == 'test':
            self.seed_test_posts()
        else:
            self.seed_normal_posts()
    
    def seed_demo_posts(self) -> None:
        """Seed comprehensive demo posts."""
        self.console.info("Creating demo blog posts...")
        
        # Get some users to assign as authors
        users = self.session.query(User).limit(5).all()
        if not users:
            self.console.warning("No users found, creating posts without authors")
            users = [None]
        
        # Create featured posts with specific content
        featured_posts = [
            {
                'title': 'Welcome to FastAPI Laravel - A New Era of Web Development',
                'content': self._get_welcome_post_content(),
                'category': 'technology',
                'tags': ['fastapi', 'laravel', 'python', 'web-development'],
                'is_published': True,
                'is_featured': True,
                'meta_description': 'Discover how FastAPI Laravel combines the best of both worlds - Python performance with Laravel elegance.',
            },
            {
                'title': 'Building Scalable APIs with FastAPI and Laravel Patterns',
                'content': self._get_api_development_content(),
                'category': 'tutorial',
                'tags': ['api', 'scalability', 'architecture', 'best-practices'],
                'is_published': True,
                'is_featured': True,
                'meta_description': 'Learn how to build scalable, maintainable APIs using Laravel architectural patterns in FastAPI.',
            },
            {
                'title': 'OAuth2 Authentication: A Complete Guide',
                'content': self._get_oauth_guide_content(),
                'category': 'security',
                'tags': ['oauth2', 'authentication', 'security', 'jwt'],
                'is_published': True,
                'is_featured': False,
                'meta_description': 'Complete guide to implementing OAuth2 authentication with JWT tokens and security best practices.',
            },
        ]
        
        # Create featured posts
        for post_data in featured_posts:
            author = random.choice(users) if users[0] else None
            
            post = PostFactory.create_post({
                **post_data,
                'author_id': author.id if author else None,
                'published_at': datetime.now() - timedelta(days=random.randint(1, 30)),
                'views_count': random.randint(100, 1000),
                'likes_count': random.randint(10, 100),
            })
            
            self.session.add(post)
        
        # Create additional random posts
        additional_posts = PostFactory.create_many(
            count=25,
            attributes={
                'author_id': lambda: random.choice(users).id if users[0] else None,
                'is_published': lambda: random.choice([True, True, True, False]),  # 75% published
                'published_at': lambda: datetime.now() - timedelta(days=random.randint(1, 90)),
                'views_count': lambda: random.randint(0, 500),
                'likes_count': lambda: random.randint(0, 50),
            }
        )
        
        for post in additional_posts:
            self.session.add(post)
        
        self.session.commit()
        self.console.success(f"Created {len(featured_posts) + len(additional_posts)} demo posts")
    
    def seed_test_posts(self) -> None:
        """Seed minimal test posts."""
        self.console.info("Creating test blog posts...")
        
        # Get a test user
        user = self.session.query(User).first()
        
        # Create minimal posts for testing
        test_posts = PostFactory.create_many(
            count=5,
            attributes={
                'author_id': user.id if user else None,
                'is_published': True,
                'published_at': datetime.now() - timedelta(days=1),
            }
        )
        
        for post in test_posts:
            self.session.add(post)
        
        self.session.commit()
        self.console.success(f"Created {len(test_posts)} test posts")
    
    def seed_normal_posts(self) -> None:
        """Seed normal amount of posts."""
        self.console.info("Creating blog posts...")
        
        # Get users for authors
        users = self.session.query(User).all()
        if not users:
            self.console.warning("No users found, skipping post seeding")
            return
        
        # Create posts
        posts = PostFactory.create_many(
            count=15,
            attributes={
                'author_id': lambda: random.choice(users).id,
                'is_published': lambda: random.choice([True, True, False]),  # 66% published
                'published_at': lambda: datetime.now() - timedelta(days=random.randint(1, 60)),
            }
        )
        
        for post in posts:
            self.session.add(post)
        
        self.session.commit()
        self.console.success(f"Created {len(posts)} blog posts")
    
    def _get_welcome_post_content(self) -> str:
        """Get content for the welcome post."""
        return """
# Welcome to FastAPI Laravel

We're excited to introduce **FastAPI Laravel** - a revolutionary approach to web development that combines the blazing-fast performance of FastAPI with the elegant architectural patterns of Laravel.

## Why FastAPI Laravel?

### 🚀 **Performance Meets Elegance**
- FastAPI's async performance with Laravel's developer experience
- Type-safe code with comprehensive validation
- Automatic API documentation generation

### 🏗️ **Familiar Architecture**
- Laravel-style MVC patterns
- Service providers and dependency injection
- Eloquent-like ORM with relationships
- Middleware pipeline for request processing

### 🔒 **Enterprise Security**
- Complete OAuth2 implementation
- Role-based access control
- JWT authentication
- CSRF protection

## Getting Started

```python
from fastapi import FastAPI
from app.Http.Controllers.HomeController import HomeController

app = FastAPI()

@app.get("/")
async def home():
    return HomeController().index()
```

## What's Next?

Explore our comprehensive features:
- **API Documentation**: Interactive docs at `/docs`
- **Authentication**: OAuth2 with multiple grant types  
- **Background Jobs**: Laravel-style queue processing
- **Real-time Features**: WebSocket broadcasting
- **Monitoring**: Built-in performance monitoring

Ready to build something amazing? Let's get started!
"""

    def _get_api_development_content(self) -> str:
        """Get content for the API development tutorial."""
        return """
# Building Scalable APIs with FastAPI Laravel

Creating scalable, maintainable APIs requires more than just fast code - it requires thoughtful architecture. FastAPI Laravel brings Laravel's proven patterns to the Python ecosystem.

## The Laravel Way in Python

### Controllers
```python
class UserController(BaseController):
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    async def index(self) -> List[UserResource]:
        users = await self.user_service.get_all()
        return UserResource.collection(users)
```

### Form Requests
```python  
class CreateUserRequest(FormRequest):
    def rules(self) -> Dict[str, str]:
        return {
            'name': 'required|string|max:100',
            'email': 'required|email|unique:users',
            'password': 'required|string|min:8'
        }
```

### Service Layers
```python
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository
    
    async def create_user(self, data: Dict) -> User:
        # Business logic here
        return await self.repository.create(data)
```

## Key Benefits

1. **Separation of Concerns**: Clear boundaries between layers
2. **Testability**: Easy to mock and test individual components  
3. **Reusability**: Services can be used across multiple controllers
4. **Maintainability**: Laravel patterns are well-understood

## Best Practices

- Use dependency injection for loose coupling
- Validate early with Form Requests
- Keep controllers thin, services fat
- Use resource transformers for consistent output
- Implement proper error handling

This architecture scales from small projects to enterprise applications.
"""

    def _get_oauth_guide_content(self) -> str:
        """Get content for the OAuth2 guide."""
        return """
# OAuth2 Authentication: A Complete Guide

OAuth2 is the gold standard for API authentication. FastAPI Laravel includes a complete OAuth2 server implementation with all major grant types.

## Supported Grant Types

### Authorization Code Flow (with PKCE)
Perfect for web applications and SPAs:
```
GET /oauth/authorize?response_type=code&client_id=123&redirect_uri=...
```

### Client Credentials Flow  
For server-to-server communication:
```python
import httpx

response = httpx.post('/oauth/token', data={
    'grant_type': 'client_credentials',
    'client_id': 'your-client-id', 
    'client_secret': 'your-secret',
    'scope': 'read write'
})
```

### Password Grant
For trusted first-party applications:
```python
response = httpx.post('/oauth/token', data={
    'grant_type': 'password',
    'username': 'user@example.com',
    'password': 'password',
    'client_id': 'client-id',
    'scope': 'user'
})
```

## Token Management

### JWT Tokens
All access tokens are JWT tokens containing:
- User information
- Scopes and permissions
- Expiration time
- Token type

### Refresh Tokens
Long-lived tokens for getting new access tokens:
```python
response = httpx.post('/oauth/token', data={
    'grant_type': 'refresh_token',
    'refresh_token': 'your-refresh-token',
    'client_id': 'client-id'
})
```

## Security Features

- **PKCE**: Required for authorization code flow
- **Rate Limiting**: Prevent brute force attacks
- **Scope Validation**: Fine-grained permissions
- **Token Introspection**: Validate tokens server-side

## Best Practices

1. Always use HTTPS in production
2. Store client secrets securely
3. Implement proper scope validation
4. Use short-lived access tokens
5. Rotate refresh tokens regularly

OAuth2 provides the foundation for secure, scalable authentication in modern applications.
"""

    def should_run(self) -> bool:
        """Check if this seeder should run."""
        # Only run if we have the Post model available
        try:
            from app.Models.Post import Post
            return True
        except ImportError:
            self.console.warning("Post model not available, skipping PostSeeder")
            return False