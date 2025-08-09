"""
Comprehensive Blade Engine Features Test Suite
Tests all template features, directives, filters, and complex rendering scenarios
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Generator, Tuple, Optional, Callable
import json
import datetime

from app.View.BladeEngine import BladeEngine


class TestBladeCompleteFeatures:
    """Test all Blade engine features comprehensively"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_all_control_flow_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test all control flow directives and their combinations"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Control Flow Test</title>
</head>
<body>
    <!-- Basic conditionals -->
    @if(show_header)
        <header>Header Content</header>
    @elseif(show_alt_header)
        <header>Alternative Header</header>
    @else
        <header>Default Header</header>
    @endif
    
    <!-- Unless directive -->
    @unless(hide_navigation)
        <nav>
            <ul>
                @foreach(nav_items as item)
                    @if(item.visible)
                        <li><a href="{{ item.url }}">{{ item.title }}</a></li>
                    @endif
                @endforeach
            </ul>
        </nav>
    @endunless
    
    <!-- Switch statement with complex cases -->
    @switch(user.role)
        @case('admin')
            <div class="admin-panel">
                <h1>Administrator Dashboard</h1>
                @forelse(admin_actions as action)
                    @can(action.permission)
                        <button data-action="{{ action.key }}">{{ action.label }}</button>
                    @endcan
                @empty
                    <p>No actions available</p>
                @endforelse
            </div>
        @break
        
        @case('moderator')
            <div class="moderator-panel">
                <h1>Moderator Dashboard</h1>
                @for(i = 0; i < moderation_limits; i++)
                    @if(pending_items[i])
                        <div class="pending-item">{{ pending_items[i].title }}</div>
                    @endif
                @endfor
            </div>
        @break
        
        @case('user')
        @case('member')
            <div class="user-panel">
                <h1>User Dashboard</h1>
                @isset(user.profile)
                    <p>Welcome, {{ user.profile.name }}!</p>
                    
                    @empty(user.notifications)
                        <p>No new notifications</p>
                    @else
                        <div class="notifications">
                            @foreach(user.notifications as notification)
                                <div class="notification {{ notification.type }}">
                                    <span class="time">{{ notification.created_at }}</span>
                                    <p>{{ notification.message }}</p>
                                </div>
                            @endforeach
                        </div>
                    @endempty
                @endisset
            </div>
        @break
        
        @default
            <div class="guest-panel">
                <h1>Welcome, Guest!</h1>
                <p>Please <a href="/login">login</a> or <a href="/register">register</a>.</p>
            </div>
    @endswitch
    
    <!-- Nested loops with break and continue -->
    <section class="data-grid">
        @foreach(categories as category)
            @unless(category.hidden)
                <div class="category">
                    <h2>{{ category.name }}</h2>
                    
                    @forelse(category.items as item)
                        @if(item.status === 'draft')
                            @continue
                        @endif
                        
                        @if(loop.index > max_items_per_category)
                            @break
                        @endif
                        
                        <div class="item {{ loop.first ? 'first' : '' }} {{ loop.last ? 'last' : '' }}">
                            <h3>{{ item.title }}</h3>
                            <p>Item {{ loop.index }} of {{ loop.count }}</p>
                            
                            @switch(item.type)
                                @case('image')
                                    <img src="{{ item.url }}" alt="{{ item.alt }}">
                                @break
                                
                                @case('video')
                                    <video controls>
                                        <source src="{{ item.url }}" type="video/{{ item.format }}">
                                    </video>
                                @break
                                
                                @case('document')
                                    <a href="{{ item.url }}" download>{{ item.filename }}</a>
                                @break
                                
                                @default
                                    <p>{{ item.content }}</p>
                            @endswitch
                        </div>
                    @empty
                        <p>No items in this category</p>
                    @endforelse
                </div>
            @endunless
        @endforeach
    </section>
    
    <!-- Complex authentication and authorization -->
    @auth
        <div class="authenticated-content">
            @hasrole('admin')
                <div class="admin-tools">
                    @can('manage_users')
                        <a href="/admin/users">Manage Users</a>
                    @endcan
                    
                    @can('system_settings')
                        <a href="/admin/settings">System Settings</a>
                    @endcan
                </div>
            @endhasrole
            
            @hasanyrole(['moderator', 'admin'])
                <div class="moderation-tools">
                    <a href="/moderate">Moderation Panel</a>
                </div>
            @endhasanyrole
            
            @haspermission('edit_posts')
                <div class="editor-tools">
                    <a href="/posts/create">Create Post</a>
                </div>
            @endhaspermission
        </div>
    @else
        @guest
            <div class="guest-content">
                <p>Please log in to access full features</p>
            </div>
        @endguest
    @endauth
    
    <!-- Environment and configuration based rendering -->
    @production
        <!-- Production analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id={{ ga_id }}"></script>
    @endproduction
    
    @env('local', 'development')
        <div class="debug-toolbar">
            <h3>Debug Information</h3>
            @dump(request, user, session)
        </div>
    @endenv
    
    @debug
        <div class="debug-panel">
            <h3>Debug Panel</h3>
            <pre>@dd(debug_data)</pre>
        </div>
    @enddebug
    
    <!-- Error handling -->
    @error('name')
        <div class="field-error">{{ $message }}</div>
    @enderror
    
    @error('email')
        <div class="field-error">{{ $message }}</div>
    @enderror
</body>
</html>
        """.strip()
        
        self.create_template(temp_dir, "control_flow.blade.html", template_content)
        
        context = {
            "show_header": True,
            "show_alt_header": False,
            "hide_navigation": False,
            "nav_items": [
                {"title": "Home", "url": "/", "visible": True},
                {"title": "About", "url": "/about", "visible": True},
                {"title": "Hidden", "url": "/hidden", "visible": False},
                {"title": "Contact", "url": "/contact", "visible": True}
            ],
            "user": {
                "role": "admin",
                "profile": {"name": "Admin User"},
                "notifications": [
                    {"type": "info", "message": "Welcome back!", "created_at": "2024-01-01"},
                    {"type": "warning", "message": "System maintenance scheduled", "created_at": "2024-01-02"}
                ]
            },
            "admin_actions": [
                {"key": "manage_users", "label": "Manage Users", "permission": "manage_users"},
                {"key": "system_config", "label": "System Config", "permission": "system_settings"}
            ],
            "moderation_limits": 3,
            "pending_items": [
                {"title": "Pending Review 1"},
                {"title": "Pending Review 2"},
                {"title": "Pending Review 3"}
            ],
            "categories": [
                {
                    "name": "Images",
                    "hidden": False,
                    "items": [
                        {"title": "Image 1", "status": "published", "type": "image", "url": "/image1.jpg", "alt": "Image 1"},
                        {"title": "Image 2", "status": "draft", "type": "image", "url": "/image2.jpg", "alt": "Image 2"},
                        {"title": "Image 3", "status": "published", "type": "image", "url": "/image3.jpg", "alt": "Image 3"}
                    ]
                },
                {
                    "name": "Videos", 
                    "hidden": False,
                    "items": [
                        {"title": "Video 1", "status": "published", "type": "video", "url": "/video1.mp4", "format": "mp4"}
                    ]
                },
                {
                    "name": "Hidden Category",
                    "hidden": True,
                    "items": []
                }
            ],
            "max_items_per_category": 5,
            "ga_id": "GA-123456789",
            "request": {"method": "GET", "path": "/test"},
            "session": {"id": "session123"},
            "debug_data": {"version": "1.0", "environment": "test"},
            "errors": {
                "name": "Name is required",
                "email": "Invalid email format"
            }
        }
        
        result = engine.render("control_flow.blade.html", context)
        
        # Verify control flow logic
        assert "Header Content" in result  # show_header is True
        assert "Alternative Header" not in result  # show_alt_header is False
        
        # Verify navigation rendering
        assert "Home" in result and "About" in result and "Contact" in result
        assert "Hidden" not in result  # visible is False
        
        # Verify switch statement
        assert "Administrator Dashboard" in result  # user.role is admin
        assert "Moderator Dashboard" not in result
        assert "User Dashboard" not in result
        
        # Verify nested loops and conditions
        assert "Images" in result  # Category not hidden
        assert "Image 1" in result  # Status published
        assert "Image 2" not in result  # Status draft, should be skipped
        assert "Image 3" in result  # Status published
        assert "Hidden Category" not in result  # Category hidden
        
        # Verify authentication blocks (current_user context would be needed for full test)
        # For now, just verify the template compiles correctly
        
        # Verify error handling
        assert "Name is required" in result
        assert "Invalid email format" in result
    
    def test_advanced_template_features(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test advanced template features like stacks, fragments, macros, etc."""
        engine, temp_dir = blade_engine
        
        # Create base layout
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Default Title')</title>
    
    <!-- CSS Stack -->
    @stack('styles')
    
    <!-- Meta Stack -->
    @stack('meta')
    
    <style>
        @stack('inline-styles')
    </style>
</head>
<body>
    <div class="layout">
        @yield('content')
        
        @hasSection('sidebar')
            <aside class="sidebar">
                @yield('sidebar')
            </aside>
        @endhasSection
        
        @sectionMissing('footer')
            <footer class="default-footer">
                <p>Default Footer Content</p>
            </footer>
        @endsectionMissing
        
        @yield('footer')
    </div>
    
    <!-- JavaScript Stack -->
    @stack('scripts')
    
    <!-- Once blocks for one-time initialization -->
    @once('page-init')
        <script>
            window.appInitialized = true;
            console.log('App initialized once');
        </script>
    @endonce
    
    @once('analytics')
        <script>
            // Analytics code should only load once
            gtag('config', '{{ ga_id }}');
        </script>
    @endonce
</body>
</html>
        """.strip()
        
        # Create page template that extends layout
        page_content = """
@extends('layout')

@section('title', 'Advanced Features Demo')

@push('meta')
    <meta name="description" content="Demo of advanced Blade features">
    <meta name="keywords" content="blade, templates, laravel">
@endpush

@push('styles')
    <link rel="stylesheet" href="/css/demo.css">
    <link rel="stylesheet" href="/css/components.css">
@endpush

@prepend('styles')
    <link rel="stylesheet" href="/css/critical.css">
@endprepend

@push('inline-styles')
    .demo-section { margin-bottom: 2rem; }
    .highlight { background: yellow; }
@endpush

@section('content')
    <main class="main-content">
        <h1>Advanced Features Demo</h1>
        
        <!-- Fragments -->
        @fragment('user-card')
            <div class="user-card">
                <img src="{{ user.avatar }}" alt="{{ user.name }}">
                <h3>{{ user.name }}</h3>
                <p>{{ user.bio }}</p>
            </div>
        @endfragment
        
        <!-- Display fragment multiple times -->
        <section class="users">
            @foreach(users as user)
                {{ get_fragment('user-card') }}
            @endforeach
        </section>
        
        <!-- Macros -->
        @macro('alert')
            <div class="alert alert-{{ type ?? 'info' }}">
                <strong>{{ title ?? 'Notice' }}:</strong>
                {{ message }}
            </div>
        @endmacro
        
        <!-- Use macros with different parameters -->
        <section class="alerts">
            @include('alert', ['type' => 'success', 'title' => 'Success', 'message' => 'Operation completed!'])
            @include('alert', ['type' => 'warning', 'message' => 'Please check your settings'])
            @include('alert', ['type' => 'error', 'title' => 'Error', 'message' => 'Something went wrong'])
        </section>
        
        <!-- Conditional includes -->
        @includeIf(show_stats, 'partials/stats')
        @includeWhen(user.is_premium, 'partials/premium-features')
        @includeUnless(user.is_banned, 'partials/user-actions')
        @includeFirst(['custom-header', 'partials/header', 'default-header'])
        
        <!-- Each directive for collection rendering -->
        @each('partials/product-card', products, 'product', 'partials/no-products')
        
        <!-- Complex data manipulation with filters -->
        <section class="filtered-data">
            @foreach(posts.where('published', true).sortBy('created_at').take(5) as post)
                <article>
                    <h2>{{ post.title | ucfirst }}</h2>
                    <p>{{ post.content | truncate_words(20) }}</p>
                    <small>{{ post.created_at | date('F j, Y') }}</small>
                    <div class="meta">
                        Views: {{ post.views | number_format }}
                        Price: {{ post.price | money }}
                    </div>
                </article>
            @endforeach
        </section>
        
        <!-- Loop information -->
        <section class="loop-info">
            @foreach(items as item)
                <div class="item-{{ loop.index }} {{ loop.first ? 'first-item' : '' }} {{ loop.last ? 'last-item' : '' }}">
                    <p>Item {{ loop.index }} of {{ loop.count }}</p>
                    <p>Remaining: {{ loop.remaining }}</p>
                    <p>Even/Odd: {{ loop.even ? 'even' : 'odd' }}</p>
                    
                    @if(item.children)
                        <div class="children">
                            @foreach(item.children as child)
                                <div class="child-item depth-{{ loop.depth }}">
                                    <p>Child {{ loop.parent.index }}.{{ loop.index }}</p>
                                    <p>{{ child.name }}</p>
                                </div>
                            @endforeach
                        </div>
                    @endif
                </div>
            @endforeach
        </section>
        
        <!-- JSON and data handling -->
        <section class="data-section">
            <h2>JSON Data</h2>
            <pre>@json(complex_data, JSON_PRETTY_PRINT)</pre>
            
            <!-- Class and style helpers -->
            <div class="{{ class_names('base-class', condition_class, ['conditional-class' => show_conditional]) }}">
                Dynamic classes applied
            </div>
            
            <div style="{{ styles('color' => text_color, 'background_color' => bg_color, 'font_size' => font_size) }}">
                Dynamic styles applied
            </div>
        </section>
        
        <!-- Form helpers -->
        <section class="forms">
            <form method="POST" action="/submit">
                @csrf
                @method('PUT')
                
                <input type="text" name="name" value="{{ old('name', user.name) }}" 
                       class="{{ class_names('form-control', ['is-invalid' => $errors.has('name')]) }}">
                @error('name')
                    <div class="invalid-feedback">{{ $message }}</div>
                @enderror
                
                <textarea name="bio" class="form-control">{{ old('bio', user.bio) }}</textarea>
                
                <button type="submit">Update Profile</button>
            </form>
        </section>
    </main>
@endsection

@section('sidebar')
    <div class="sidebar-content">
        <h3>Navigation</h3>
        <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/profile">Profile</a></li>
            <li><a href="/settings">Settings</a></li>
        </ul>
        
        @parent
        
        <div class="sidebar-extra">
            <p>Additional sidebar content</p>
        </div>
    </div>
@endsection

@section('footer')
    <footer class="custom-footer">
        <p>© 2024 Advanced Features Demo</p>
        <p>Powered by Blade Engine</p>
    </footer>
@endsection

@push('scripts')
    <script src="/js/demo.js"></script>
@endpush

@push('scripts')
    <script>
        console.log('Page-specific JavaScript');
        
        // Use JSON data in JavaScript
        const pageData = @json($page_data);
        console.log(pageData);
    </script>
@endpush
        """.strip()
        
        # Create partial templates
        stats_partial = """
<div class="stats-widget">
    <h3>Site Statistics</h3>
    <ul>
        <li>Users: {{ stats.users | number_format }}</li>
        <li>Posts: {{ stats.posts | number_format }}</li>
        <li>Views: {{ stats.views | number_format }}</li>
    </ul>
</div>
        """.strip()
        
        premium_partial = """
<div class="premium-features">
    <h3>Premium Features</h3>
    <ul>
        <li>Advanced Analytics</li>
        <li>Priority Support</li>
        <li>Custom Themes</li>
    </ul>
</div>
        """.strip()
        
        user_actions_partial = """
<div class="user-actions">
    <button class="btn btn-primary">Edit Profile</button>
    <button class="btn btn-secondary">View Posts</button>
    <button class="btn btn-danger">Delete Account</button>
</div>
        """.strip()
        
        product_card_partial = """
<div class="product-card">
    <h4>{{ product.name }}</h4>
    <p>{{ product.description }}</p>
    <span class="price">{{ product.price | money }}</span>
</div>
        """.strip()
        
        no_products_partial = """
<div class="no-products">
    <p>No products available at this time.</p>
</div>
        """.strip()
        
        # Create all templates
        self.create_template(temp_dir, "layout.blade.html", layout_content)
        self.create_template(temp_dir, "advanced_page.blade.html", page_content)
        self.create_template(temp_dir, "partials/stats.blade.html", stats_partial)
        self.create_template(temp_dir, "partials/premium-features.blade.html", premium_partial)
        self.create_template(temp_dir, "partials/user-actions.blade.html", user_actions_partial)
        self.create_template(temp_dir, "partials/product-card.blade.html", product_card_partial)
        self.create_template(temp_dir, "partials/no-products.blade.html", no_products_partial)
        
        context = {
            "ga_id": "GA-123456789",
            "user": {
                "name": "John Doe",
                "bio": "Full-stack developer",
                "avatar": "/avatars/john.jpg",
                "is_premium": True,
                "is_banned": False
            },
            "users": [
                {"name": "Alice", "bio": "Designer", "avatar": "/avatars/alice.jpg"},
                {"name": "Bob", "bio": "Developer", "avatar": "/avatars/bob.jpg"}
            ],
            "show_stats": True,
            "stats": {
                "users": 1250,
                "posts": 3400,
                "views": 125000
            },
            "products": [
                {"name": "Product 1", "description": "Description 1", "price": 29.99},
                {"name": "Product 2", "description": "Description 2", "price": 49.99}
            ],
            "posts": [
                {
                    "title": "first post",
                    "content": "This is the content of the first post with many words to test truncation.",
                    "created_at": datetime.datetime(2024, 1, 15),
                    "views": 1234,
                    "price": 19.99,
                    "published": True
                },
                {
                    "title": "second post",
                    "content": "This is the second post content.",
                    "created_at": datetime.datetime(2024, 1, 20),
                    "views": 5678,
                    "price": 39.99,
                    "published": True
                }
            ],
            "items": [
                {
                    "name": "Item 1",
                    "children": [
                        {"name": "Child 1.1"},
                        {"name": "Child 1.2"}
                    ]
                },
                {"name": "Item 2", "children": None},
                {
                    "name": "Item 3", 
                    "children": [
                        {"name": "Child 3.1"}
                    ]
                }
            ],
            "complex_data": {
                "array": [1, 2, 3, 4, 5],
                "object": {"key": "value", "nested": {"deep": True}},
                "boolean": True,
                "null_value": None
            },
            "condition_class": "active",
            "show_conditional": True,
            "text_color": "#333333",
            "bg_color": "#ffffff",
            "font_size": "16px",
            "errors": {},
            "page_data": {
                "title": "Advanced Features Demo",
                "timestamp": datetime.datetime.now().isoformat()
            },
            "old": lambda field, default=None: default  # Mock old input helper
        }
        
        result = engine.render("advanced_page.blade.html", context)
        
        # Verify advanced features
        assert "Advanced Features Demo" in result  # Title
        assert "Demo of advanced Blade features" in result  # Meta description
        assert "/css/critical.css" in result  # Prepended style
        assert "/css/demo.css" in result  # Pushed style
        assert "margin-bottom: 2rem" in result  # Inline style
        
        # Verify users section with fragments
        assert "Alice" in result and "Bob" in result
        
        # Verify conditional includes
        assert "Site Statistics" in result  # stats included
        assert "Premium Features" in result  # premium features included
        assert "Delete Account" in result  # user actions included (not banned)
        
        # Verify products rendering
        assert "Product 1" in result and "Product 2" in result
        
        # Verify posts with filters
        assert "First post" in result  # ucfirst filter
        assert "$19.99" in result and "$39.99" in result  # money filter
        assert "1,234" in result and "5,678" in result  # number_format filter
        
        # Verify loop information
        assert "Item 1 of 3" in result  # loop.index and loop.count
        assert "first-item" in result  # loop.first
        assert "last-item" in result  # loop.last
        assert "Child 1.1" in result  # nested loops
        
        # Verify JSON output
        assert '"array":[1,2,3,4,5]' in result or '"array": [1, 2, 3, 4, 5]' in result
        
        # Verify class and style helpers
        assert 'class="base-class active conditional-class"' in result
        assert 'color: #333333' in result
        assert 'background-color: #ffffff' in result
        
        # Verify form helpers
        assert 'name="_token"' in result  # CSRF token
        assert 'name="_method" value="PUT"' in result  # Method spoofing
        
        # Verify sidebar and footer sections
        assert "Navigation" in result  # sidebar content
        assert "© 2024 Advanced Features Demo" in result  # custom footer
        assert "Default Footer Content" not in result  # should be overridden
        
        # Verify JavaScript stack
        assert "/js/demo.js" in result  # pushed script
        assert "Page-specific JavaScript" in result  # inline script
    
    def test_complex_data_manipulation_and_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex data manipulation, custom filters, and edge cases"""
        engine, temp_dir = blade_engine
        
        # Register additional custom filters
        engine.env.filters['reverse'] = lambda s: s[::-1] if isinstance(s, str) else list(reversed(s))
        engine.env.filters['chunk'] = lambda items, size: [items[i:i + size] for i in range(0, len(items), size)]
        engine.env.filters['pluck'] = lambda items, key: [item.get(key) for item in items if isinstance(item, dict)]
        engine.env.filters['group_by'] = lambda items, key: {getattr(item, key, item.get(key)): [i for i in items if getattr(i, key, i.get(key)) == getattr(item, key, item.get(key))] for item in items}
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Complex Data Manipulation</title>
</head>
<body>
    <!-- String manipulation -->
    <section class="strings">
        <h2>String Filters</h2>
        <p>Original: "{{ sample_text }}"</p>
        <p>Title Case: "{{ sample_text | title }}"</p>
        <p>Upper Case: "{{ sample_text | upper }}"</p>
        <p>Lower Case: "{{ sample_text | lower }}"</p>
        <p>Slug: "{{ sample_text | slug }}"</p>
        <p>Truncate: "{{ long_text | truncate_words(5) }}"</p>
        <p>Reversed: "{{ sample_text | reverse }}"</p>
        <p>Length: {{ sample_text | length }}</p>
    </section>
    
    <!-- Number formatting -->
    <section class="numbers">
        <h2>Number Filters</h2>
        <p>Large Number: {{ large_number | number_format }}</p>
        <p>Money: {{ price | money }}</p>
        <p>Percentage: {{ percentage | percentage }}</p>
        <p>Round: {{ decimal_number | round(2) }}</p>
        <p>Absolute: {{ negative_number | abs }}</p>
    </section>
    
    <!-- Date/Time manipulation -->
    <section class="dates">
        <h2>Date Filters</h2>
        <p>Current Time: {{ now() | strftime('%Y-%m-%d %H:%M:%S') }}</p>
        <p>Custom Date: {{ custom_date | strftime('%B %d, %Y') }}</p>
        <p>Relative: {{ past_date | strftime('%Y-%m-%d') }}</p>
    </section>
    
    <!-- Array/Collection manipulation -->
    <section class="arrays">
        <h2>Array Manipulation</h2>
        
        <!-- Basic array operations -->
        <div class="basic-arrays">
            <h3>Basic Operations</h3>
            <p>First Item: {{ items | first }}</p>
            <p>Last Item: {{ items | last }}</p>
            <p>Length: {{ items | length }}</p>
            <p>Random: {{ items | random }}</p>
            <p>Unique: {{ duplicate_items | unique | join(', ') }}</p>
            <p>Sorted: {{ unsorted_numbers | sort | join(', ') }}</p>
            <p>Reversed: {{ items | reverse | join(', ') }}</p>
        </div>
        
        <!-- Advanced array operations -->
        <div class="advanced-arrays">
            <h3>Advanced Operations</h3>
            <p>Chunked (groups of 3):</p>
            @foreach(items | chunk(3) as chunk)
                <div class="chunk">{{ chunk | join(', ') }}</div>
            @endforeach
            
            <p>Plucked names: {{ people | pluck('name') | join(', ') }}</p>
            
            <p>Filtered adults:</p>
            @foreach(people | selectattr('age', '>', 17) | list as person)
                <div>{{ person.name }} ({{ person.age }})</div>
            @endforeach
        </div>
        
        <!-- Grouped data -->
        <div class="grouped-data">
            <h3>Grouped by Category</h3>
            @foreach(products | groupby('category') as category, product_group)
                <div class="category-group">
                    <h4>{{ category | title }}</h4>
                    @foreach(product_group as product)
                        <div class="product">
                            {{ product.name }} - {{ product.price | money }}
                        </div>
                    @endforeach
                </div>
            @endforeach
        </div>
    </section>
    
    <!-- Complex nested data structures -->
    <section class="nested-data">
        <h2>Nested Data Structures</h2>
        
        @foreach(nested_structure as section)
            <div class="section">
                <h3>{{ section.title }}</h3>
                
                @if(section.subsections)
                    @foreach(section.subsections as subsection)
                        <div class="subsection">
                            <h4>{{ subsection.title }}</h4>
                            
                            @if(subsection.items)
                                <ul>
                                    @foreach(subsection.items as item)
                                        <li>
                                            {{ item.name }} 
                                            @if(item.metadata)
                                                <small>({{ item.metadata.type }})</small>
                                            @endif
                                            
                                            @if(item.tags)
                                                <div class="tags">
                                                    @foreach(item.tags as tag)
                                                        <span class="tag">{{ tag }}</span>
                                                    @endforeach
                                                </div>
                                            @endif
                                            
                                            @if(item.nested_items)
                                                <ul class="nested-list">
                                                    @foreach(item.nested_items as nested_item)
                                                        <li>{{ nested_item.title }} - {{ nested_item.value }}</li>
                                                    @endforeach
                                                </ul>
                                            @endif
                                        </li>
                                    @endforeach
                                </ul>
                            @endif
                        </div>
                    @endforeach
                @endif
            </div>
        @endforeach
    </section>
    
    <!-- Conditional data display with complex logic -->
    <section class="conditional-complex">
        <h2>Complex Conditional Logic</h2>
        
        @foreach(users as user)
            <div class="user-card {{ user.status }} {{ user.role }}">
                <h4>{{ user.name }}</h4>
                
                @if(user.status == 'active' and user.role in ['admin', 'moderator'])
                    <div class="admin-badge">Admin User</div>
                @elseif(user.status == 'active' and user.posts_count > 10)
                    <div class="contributor-badge">Active Contributor</div>
                @elseif(user.status == 'pending')
                    <div class="pending-badge">Pending Approval</div>
                @else
                    <div class="regular-badge">Regular User</div>
                @endif
                
                <!-- Nested conditions with multiple criteria -->
                @if(user.profile and user.profile.visible)
                    @if(user.profile.avatar)
                        <img src="{{ user.profile.avatar }}" alt="{{ user.name }}">
                    @else
                        <div class="avatar-placeholder">{{ user.name | first }}</div>
                    @endif
                    
                    @if(user.profile.bio and user.profile.bio | length > 10)
                        <p class="bio">{{ user.profile.bio | truncate_words(20) }}</p>
                    @endif
                    
                    @if(user.profile.social_links)
                        <div class="social-links">
                            @foreach(user.profile.social_links as platform, url)
                                @if(url and url | length > 0)
                                    <a href="{{ url }}" target="_blank">{{ platform | title }}</a>
                                @endif
                            @endforeach
                        </div>
                    @endif
                @endif
                
                <!-- Activity indicators -->
                @switch(user.last_activity_days)
                    @case(0)
                        <span class="activity-indicator online">Online</span>
                    @break
                    
                    @case(1)
                        <span class="activity-indicator recent">Yesterday</span>
                    @break
                    
                    @default
                        @if(user.last_activity_days <= 7)
                            <span class="activity-indicator week">This week</span>
                        @elseif(user.last_activity_days <= 30)
                            <span class="activity-indicator month">This month</span>
                        @else
                            <span class="activity-indicator inactive">Inactive</span>
                        @endif
                @endswitch
            </div>
        @endforeach
    </section>
    
    <!-- Edge cases and error handling -->
    <section class="edge-cases">
        <h2>Edge Cases</h2>
        
        <!-- Null/undefined handling -->
        <div class="null-handling">
            <p>Null value: "{{ null_value | default('N/A') }}"</p>
            <p>Empty string: "{{ empty_string | default('Empty') }}"</p>
            <p>Zero: "{{ zero_value | default('Zero') }}"</p>
            <p>False: "{{ false_value | default('False') }}"</p>
        </div>
        
        <!-- Empty collections -->
        <div class="empty-collections">
            <h3>Empty Collections</h3>
            @forelse(empty_array as item)
                <p>Item: {{ item }}</p>
            @empty
                <p>No items in empty array</p>
            @endforelse
            
            @foreach(maybe_empty_array as item)
                <p>Maybe item: {{ item }}</p>
            @else
                <p>Maybe array is empty</p>
            @endforeach
        </div>
        
        <!-- Deep nesting safety -->
        <div class="deep-nesting">
            <p>Deep property: {{ deep_object.level1.level2.level3.level4.value | default('Not found') }}</p>
            <p>Missing deep property: {{ deep_object.level1.missing.deep | default('Missing') }}</p>
        </div>
    </section>
</body>
</html>
        """.strip()
        
        self.create_template(temp_dir, "complex_data.blade.html", template_content)
        
        context = {
            # String data
            "sample_text": "hello world test",
            "long_text": "This is a very long text that should be truncated when using the truncate_words filter to show only the first few words",
            
            # Number data
            "large_number": 1234567.89,
            "price": 199.99,
            "percentage": 0.756,
            "decimal_number": 3.14159,
            "negative_number": -42,
            
            # Date data
            "custom_date": datetime.datetime(2024, 3, 15, 14, 30, 0),
            "past_date": datetime.datetime(2024, 1, 1, 0, 0, 0),
            
            # Array data
            "items": ["apple", "banana", "cherry", "date"],
            "duplicate_items": ["apple", "banana", "apple", "cherry", "banana", "date"],
            "unsorted_numbers": [5, 2, 8, 1, 9, 3],
            
            # People data
            "people": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 17},
                {"name": "Charlie", "age": 30},
                {"name": "Diana", "age": 16}
            ],
            
            # Product data
            "products": [
                {"name": "Laptop", "price": 999.99, "category": "electronics"},
                {"name": "Phone", "price": 599.99, "category": "electronics"},
                {"name": "Book", "price": 19.99, "category": "books"},
                {"name": "Pen", "price": 2.99, "category": "stationery"}
            ],
            
            # Complex nested structure
            "nested_structure": [
                {
                    "title": "Technology",
                    "subsections": [
                        {
                            "title": "Programming",
                            "items": [
                                {
                                    "name": "Python",
                                    "metadata": {"type": "language"},
                                    "tags": ["backend", "ai", "data"],
                                    "nested_items": [
                                        {"title": "Django", "value": "web framework"},
                                        {"title": "NumPy", "value": "scientific computing"}
                                    ]
                                },
                                {
                                    "name": "JavaScript",
                                    "metadata": {"type": "language"},
                                    "tags": ["frontend", "backend", "web"],
                                    "nested_items": [
                                        {"title": "React", "value": "UI library"},
                                        {"title": "Node.js", "value": "runtime"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            
            # User data with complex profiles
            "users": [
                {
                    "name": "John Admin",
                    "status": "active",
                    "role": "admin",
                    "posts_count": 15,
                    "last_activity_days": 0,
                    "profile": {
                        "visible": True,
                        "avatar": "/avatars/john.jpg",
                        "bio": "System administrator with over 10 years of experience in managing complex systems",
                        "social_links": {
                            "twitter": "https://twitter.com/johnadmin",
                            "linkedin": "https://linkedin.com/in/johnadmin",
                            "github": ""
                        }
                    }
                },
                {
                    "name": "Jane Contributor",
                    "status": "active", 
                    "role": "user",
                    "posts_count": 25,
                    "last_activity_days": 2,
                    "profile": {
                        "visible": True,
                        "avatar": None,
                        "bio": "Active community member",
                        "social_links": {
                            "github": "https://github.com/janecontrib"
                        }
                    }
                },
                {
                    "name": "Bob Pending",
                    "status": "pending",
                    "role": "user",
                    "posts_count": 0,
                    "last_activity_days": 45,
                    "profile": None
                }
            ],
            
            # Edge case values
            "null_value": None,
            "empty_string": "",
            "zero_value": 0,
            "false_value": False,
            "empty_array": [],
            "maybe_empty_array": [] if True else ["item1", "item2"],
            "deep_object": {
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "value": "deep value found"
                            }
                        }
                    }
                }
            }
        }
        
        result = engine.render("complex_data.blade.html", context)
        
        # Verify string filters
        assert "Hello World Test" in result  # title case
        assert "HELLO WORLD TEST" in result  # upper case
        assert "hello-world-test" in result  # slug
        assert "tset dlrow olleh" in result  # reversed
        
        # Verify number formatting
        assert "1,234,567.89" in result or "1234567.89" in result  # number format
        assert "$199.99" in result  # money format
        assert "75.6%" in result  # percentage format
        
        # Verify array operations
        assert "apple" in result and "banana" in result  # basic arrays
        assert "Charlie (30)" in result  # filtered adults
        assert "Alice, Bob, Charlie, Diana" in result  # plucked names
        
        # Verify grouped products
        assert "Electronics" in result  # category title case
        assert "Laptop" in result and "Phone" in result  # electronics products
        assert "Books" in result and "Book" in result  # books category and product
        
        # Verify nested structure rendering
        assert "Technology" in result
        assert "Programming" in result  
        assert "Python" in result and "JavaScript" in result
        assert "Django" in result and "React" in result
        
        # Verify complex user logic
        assert "Admin User" in result  # John is admin
        assert "Active Contributor" in result  # Jane has >10 posts
        assert "Pending Approval" in result  # Bob is pending
        assert "Online" in result  # John's activity
        
        # Verify edge cases
        assert "N/A" in result  # null value default
        assert "Empty" in result  # empty string default
        assert "No items in empty array" in result  # empty forelse
        assert "deep value found" in result  # deep object access
        assert "Missing" in result  # missing deep property default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])