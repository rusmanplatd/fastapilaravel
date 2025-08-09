# Blade Template Engine Documentation

## Overview

The Blade Template Engine is a powerful, Laravel-inspired templating system for FastAPI applications. It provides a clean, intuitive syntax for creating dynamic views with features like template inheritance, sections, directives, and view composition.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Template Syntax](#template-syntax)
3. [Template Inheritance](#template-inheritance)
4. [Directives](#directives)
5. [View Composition](#view-composition)
6. [Custom Directives](#custom-directives)
7. [Filters](#filters)
8. [Caching](#caching)
9. [Integration with FastAPI](#integration-with-fastapi)
10. [Testing](#testing)
11. [Performance](#performance)
12. [Examples](#examples)

## Getting Started

### Installation

The Blade engine is included in the FastAPI Laravel project. To use it:

```python
from app.View import blade, view, view_share, view_composer

# Initialize with template paths
blade_engine = blade(['resources/views'])

# Render a template
html = view('welcome', {'name': 'World'})
```

### Basic Usage

```python
# Simple template rendering
from app.View import view

def my_route():
    context = {'message': 'Hello World'}
    return view('my-template', context)
```

## Template Syntax

### Variable Output

```blade
<!-- Escaped output (safe) -->
<p>Hello, {{ name }}!</p>

<!-- Unescaped output (raw HTML) -->
<div>{!! html_content !!}</div>
```

### Comments

```blade
{{-- This is a Blade comment --}}
{{-- 
    Multi-line
    Blade comment
--}}
```

## Template Inheritance

### Creating Layouts

**resources/views/layouts/app.blade.html**
```blade
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Default Title')</title>
    @yield('head')
</head>
<body>
    <header>
        @yield('header')
    </header>
    
    <main>
        @yield('content')
    </main>
    
    <footer>
        @yield('footer', '<p>Default Footer</p>')
    </footer>
    
    @yield('scripts')
</body>
</html>
```

### Extending Layouts

**resources/views/pages/home.blade.html**
```blade
@extends('layouts.app')

@section('title', 'Home Page')

@section('head')
    <link href="/css/home.css" rel="stylesheet">
@endsection

@section('content')
    <h1>Welcome to our site!</h1>
    <p>{{ message }}</p>
@endsection

@section('scripts')
    <script src="/js/home.js"></script>
@endsection
```

### Section Inheritance

```blade
@section('content')
    @parent
    <p>Additional content appended to parent section</p>
@endsection
```

## Directives

### Conditional Directives

#### If Statements
```blade
@if(user.is_admin)
    <p>Welcome, Admin!</p>
@elseif(user.is_moderator)
    <p>Welcome, Moderator!</p>
@else
    <p>Welcome, User!</p>
@endif
```

#### Unless Statements
```blade
@unless(user.is_banned)
    <p>You can access this content</p>
@endunless
```

### Authentication Directives

```blade
@auth
    <p>You are logged in as {{ current_user.name }}</p>
@endauth

@guest
    <a href="/login">Please log in</a>
@endguest
```

### Authorization Directives

```blade
@can('edit-posts')
    <a href="/posts/edit/{{ post.id }}">Edit Post</a>
@endcan

@cannot('delete-posts')
    <p>You don't have permission to delete posts</p>
@endcannot

@hasrole('admin')
    <a href="/admin">Admin Panel</a>
@endhasrole

@hasanyrole(['admin', 'moderator'])
    <button>Moderate Content</button>
@endhasanyrole

@haspermission('manage-users')
    <a href="/users">Manage Users</a>
@endhaspermission
```

### Loop Directives

#### Foreach Loops
```blade
<ul>
@foreach(items as item)
    <li>{{ item.name }}</li>
@endforeach
</ul>
```

#### Forelse Loops
```blade
@forelse(posts as post)
    <article>
        <h3>{{ post.title }}</h3>
        <p>{{ post.excerpt }}</p>
    </article>
@empty
    <p>No posts available</p>
@endforelse
```

#### For Loops
```blade
@for(i in range(10))
    <p>Number: {{ i }}</p>
@endfor
```

### Include Directives

```blade
@include('partials.header')

@include('partials.post-card', {'post': post})

@includeIf('partials.sidebar', sidebar_exists)

@includeWhen(show_ads, 'partials.ads')

@includeFirst(['partials.custom-header', 'partials.default-header'])
```

### Form Directives

```blade
<form method="POST" action="/contact">
    @csrf
    @method('PUT')
    
    <input type="text" name="name">
    <button type="submit">Submit</button>
</form>
```

### Utility Directives

```blade
<!-- JSON output -->
<script>
    var data = @json(user_data);
</script>

<!-- Environment checks -->
@production
    <script src="/js/analytics.js"></script>
@endproduction

@env('local')
    <div class="debug-bar">Debug Mode</div>
@endenv

<!-- Error handling -->
@error('email')
    <span class="error">{{ message }}</span>
@enderror

<!-- Isset checks -->
@isset(user.profile.avatar)
    <img src="{{ user.profile.avatar }}" alt="Avatar">
@endisset

@empty(posts)
    <p>No posts to show</p>
@endempty
```

### Switch Statements

```blade
@switch(user.role)
    @case('admin')
        <p>Administrator Access</p>
        @break
    
    @case('moderator')
        <p>Moderator Access</p>
        @break
    
    @default
        <p>Regular User Access</p>
@endswitch
```

### Raw Output

```blade
@verbatim
    <div class="container">
        {{ This will not be processed by Blade }}
    </div>
@endverbatim
```

## View Composition

### Sharing Data Globally

```python
from app.View import view_share

# Share data with all views
view_share('app_name', 'My Application')
view_share('current_year', 2024)
```

### View Composers

```python
from app.View import view_composer

def header_composer(context):
    """Add navigation data to header views"""
    return {
        'navigation_items': [
            {'name': 'Home', 'url': '/'},
            {'name': 'About', 'url': '/about'},
            {'name': 'Contact', 'url': '/contact'}
        ]
    }

# Register composer for all header views
view_composer('partials.header*', header_composer)

# Register composer for specific views
view_composer('dashboard*', dashboard_composer)
```

## Custom Directives

### Creating Custom Directives

```python
from app.View import blade

# Get blade engine instance
engine = blade()

# Register custom directive
def alert_directive(content):
    alert_type = content.strip().strip("'\"")
    return f'<div class="alert alert-{alert_type}>"'

engine.directive('alert', alert_directive)
```

### Using Custom Directives

```blade
@alert('success')
    <p>Operation completed successfully!</p>
</div>

@alert('danger')
    <p>An error occurred!</p>
</div>
```

## Filters

### Built-in Filters

```blade
<!-- Text transformation -->
<p>{{ text | ucfirst }}</p>       <!-- Capitalize first letter -->
<p>{{ text | title }}</p>         <!-- Title Case -->
<p>{{ text | slug }}</p>          <!-- URL-friendly slug -->

<!-- Formatting -->
<p>{{ price | money }}</p>        <!-- $29.99 -->
<p>{{ rate | percentage }}</p>    <!-- 75.5% -->

<!-- Text manipulation -->
<p>{{ long_text | truncate_words(10) }}</p>  <!-- Truncate to 10 words -->
```

### Custom Filters

```python
# Register custom filter
blade().env.filters['custom_format'] = lambda s: s.upper().replace(' ', '-')
```

```blade
<!-- Use custom filter -->
<p>{{ text | custom_format }}</p>
```

## Caching

### Template Caching

```python
# Initialize with caching enabled (production)
blade_engine = blade(['resources/views'], cache_path='storage/views', debug=False)

# Clear template cache
blade_engine.clear_cache()
```

### Cache Control

```python
# Disable caching in development
blade_engine = blade(['resources/views'], debug=True)
```

## Integration with FastAPI

### Basic Integration

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.View import view

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    context = {
        'title': 'Welcome',
        'message': 'Hello from FastAPI!'
    }
    return HTMLResponse(view('home', context))
```

### Advanced Integration

```python
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from app.View import blade, view_share

app = FastAPI()

# Initialize Blade
blade(['resources/views'])

# Share global data
view_share('app_name', 'FastAPI Laravel')

@app.middleware("http")
async def add_template_context(request: Request, call_next):
    """Add common template variables"""
    # Add request-specific data to all views
    view_share('request_url', str(request.url))
    response = await call_next(request)
    return response

async def get_current_user():
    # Your authentication logic here
    return {'name': 'John Doe', 'role': 'admin'}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user=Depends(get_current_user)):
    context = {
        'current_user': user,
        'page_title': 'Dashboard'
    }
    return HTMLResponse(view('dashboard', context))
```

## Testing

### Unit Tests

```python
import pytest
from app.View.BladeEngine import BladeEngine

def test_blade_compilation():
    engine = BladeEngine(['tests/templates'], debug=True)
    
    # Test basic variable output
    result = engine.compile_blade("Hello, {{ name }}!")
    assert "Hello, {{ name }}!" in result
    
    # Test if directive
    template = "@if(user.active)\n<p>Active</p>\n@endif"
    result = engine.compile_blade(template)
    assert "{% if user.active %}" in result
    assert "{% endif %}" in result

def test_template_rendering(tmp_path):
    # Create test template
    template_path = tmp_path / "test.blade.html"
    template_path.write_text("<h1>{{ title }}</h1>")
    
    engine = BladeEngine([str(tmp_path)], debug=True)
    result = engine.render("test.blade.html", {"title": "Test Page"})
    
    assert "<h1>Test Page</h1>" in result
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from your_app import app

client = TestClient(app)

def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.text

def test_dashboard_with_auth():
    # Mock authentication
    response = client.get("/dashboard", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert "Dashboard" in response.text
```

## Performance

### Optimization Tips

1. **Enable Caching**: Use template caching in production
2. **Minimize Template Paths**: Keep template search paths minimal
3. **Precompile Templates**: For high-traffic applications, consider precompiling
4. **Use View Composers Sparingly**: Only when necessary
5. **Cache Static Data**: Cache data that doesn't change frequently

### Performance Monitoring

```python
import time
from functools import wraps

def time_template_render(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Template render took {end - start:.3f}s")
        return result
    return wrapper

# Monitor template performance
blade().render = time_template_render(blade().render)
```

## Examples

### Complete Example: Blog Post Template

**resources/views/blog/post.blade.html**
```blade
@extends('layouts.app')

@section('title', post.title . ' - Blog')

@section('head')
    <meta name="description" content="{{ post.excerpt | truncate_words(20) }}">
    <meta property="og:title" content="{{ post.title }}">
    <meta property="og:description" content="{{ post.excerpt }}">
@endsection

@section('content')
<article class="post">
    <header class="post-header">
        <h1>{{ post.title }}</h1>
        
        <div class="post-meta">
            <span>By {{ post.author.name }}</span>
            <time datetime="{{ post.created_at.isoformat() }}">
                {{ post.created_at.strftime('%B %d, %Y') }}
            </time>
            
            @if(post.tags)
                <div class="tags">
                    @foreach(post.tags as tag)
                        <span class="tag">{{ tag.name }}</span>
                    @endforeach
                </div>
            @endif
        </div>
    </header>
    
    @if(post.featured_image)
        <div class="featured-image">
            <img src="{{ asset(post.featured_image) }}" alt="{{ post.title }}">
        </div>
    @endif
    
    <div class="post-content">
        {!! post.content !!}
    </div>
    
    <footer class="post-footer">
        @can('edit-posts')
            <a href="{{ route('posts.edit', post.id) }}" class="btn">Edit Post</a>
        @endcan
        
        @can('delete-posts')
            <form method="POST" action="{{ route('posts.destroy', post.id) }}" style="display: inline;">
                @csrf
                @method('DELETE')
                <button type="submit" onclick="return confirm('Delete this post?')">Delete</button>
            </form>
        @endcan
    </footer>
</article>

@include('blog.comments', {'comments': post.comments})
@endsection

@section('scripts')
<script>
    // Post-specific JavaScript
    const postData = @json({
        'id': post.id,
        'title': post.title,
        'author': post.author.name
    });
</script>
@endsection
```

### Usage in FastAPI Route

```python
@app.get("/blog/{post_id}", response_class=HTMLResponse)
async def show_post(post_id: int, user=Depends(get_current_user)):
    post = await get_post_by_id(post_id)  # Your data fetching logic
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    context = {
        'post': post,
        'current_user': user
    }
    
    return HTMLResponse(view('blog.post', context))
```

This comprehensive documentation covers all aspects of the Blade Template Engine implementation. The system provides Laravel-like templating capabilities while being fully integrated with FastAPI's async architecture and Python's type system.