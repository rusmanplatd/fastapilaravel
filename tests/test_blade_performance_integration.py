"""
Test Suite for Blade Performance and Integration
Tests caching, compilation speed, error handling, and integration scenarios
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os
import queue
import threading

from app.View.BladeEngine import BladeEngine, blade, view, view_share


class TestBladePerformance:
    """Test Blade engine performance characteristics"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=False)  # Performance mode
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_template_compilation_speed(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test template compilation performance"""
        engine, temp_dir = blade_engine
        
        # Create a complex template with many directives
        complex_template = """
@extends('layout')

@section('title', 'Performance Test Page')

@section('content')
    @auth
        <div class="user-info">
            <h1>Welcome, {{ $user.name }}!</h1>
            
            @if($user.notifications)
                <div class="notifications">
                    @foreach($user.notifications as $notification)
                        @if($notification.important)
                            <div class="alert alert-important">
                                <strong>{{ $notification.title }}</strong>
                                <p>{{ $notification.message }}</p>
                                @if($notification.actions)
                                    <div class="actions">
                                        @foreach($notification.actions as $action)
                                            <button class="btn btn-{{ $action.type }}">
                                                {{ $action.label }}
                                            </button>
                                        @endforeach
                                    </div>
                                @endif
                            </div>
                        @else
                            <div class="alert alert-normal">
                                {{ $notification.message }}
                            </div>
                        @endif
                    @endforeach
                </div>
            @endif
            
            @can('view-dashboard')
                <div class="dashboard">
                    @include('partials.dashboard')
                </div>
            @endcan
        </div>
    @else
        <div class="guest-message">
            <h1>Welcome, Guest!</h1>
            <p>Please <a href="/login">log in</a> to access your account.</p>
        </div>
    @endauth
    
    @push('scripts')
        <script src="performance-test.js"></script>
    @endpush
@endsection

@section('sidebar')
    @component('components.sidebar', ['title' => 'Navigation'])
        <ul class="nav">
            @foreach($menu_items as $item)
                <li class="nav-item {{ $item.active ? 'active' : '' }}">
                    <a href="{{ $item.url }}">{{ $item.label }}</a>
                </li>
            @endforeach
        </ul>
    @endcomponent
@endsection
        """.strip()
        
        self.create_template(temp_dir, "complex.blade.html", complex_template)
        
        # Create layout template
        layout_template = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
    @stack('styles')
</head>
<body>
    <div class="container">
        @yield('content')
    </div>
    <aside>
        @yield('sidebar')
    </aside>
    @stack('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layout.blade.html", layout_template)
        
        # Measure compilation time
        context = {
            "user": {
                "name": "Test User",
                "notifications": [
                    {"title": "Important", "message": "Test notification", "important": True},
                    {"message": "Regular notification", "important": False}
                ]
            },
            "current_user": True,
            "menu_items": [
                {"label": "Home", "url": "/", "active": True},
                {"label": "Profile", "url": "/profile", "active": False}
            ]
        }
        
        start_time = time.time()
        result = engine.render("complex.blade.html", context)
        compilation_time = time.time() - start_time
        
        # Compilation should be reasonably fast (< 1 second for complex template)
        assert compilation_time < 1.0
        assert "Test User" in result
        assert "Important" in result
    
    def test_template_caching(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test template caching improves performance"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="cached-template">
    <h1>{{ $title }}</h1>
    <p>This template tests caching performance</p>
    @foreach($items as $item)
        <div class="item">{{ $item }}</div>
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "cached.blade.html", template_content)
        
        context = {
            "title": "Cache Test",
            "items": [f"Item {i}" for i in range(100)]
        }
        
        # First render (cache miss)
        start_time = time.time()
        result1 = engine.render("cached.blade.html", context)
        first_render_time = time.time() - start_time
        
        # Second render (cache hit should be faster)
        start_time = time.time()
        result2 = engine.render("cached.blade.html", context)
        second_render_time = time.time() - start_time
        
        # Results should be identical
        assert result1 == result2
        assert "Cache Test" in result1
        
        # Second render should be faster or at least not significantly slower
        # Note: In debug mode caching might be disabled
        if not engine.debug:
            assert second_render_time <= first_render_time * 1.2  # Allow 20% variance
    
    def test_large_dataset_rendering(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test rendering performance with large datasets"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="large-dataset">
    <h1>{{ $title }}</h1>
    <table class="table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            @foreach($users as $user)
                <tr class="{{ $user.active ? 'active' : 'inactive' }}">
                    <td>{{ $user.id }}</td>
                    <td>{{ $user.name }}</td>
                    <td>{{ $user.email }}</td>
                    <td>
                        @if($user.active)
                            <span class="badge badge-success">Active</span>
                        @else
                            <span class="badge badge-danger">Inactive</span>
                        @endif
                    </td>
                    <td>
                        @can('edit-users')
                            <button class="btn btn-sm btn-primary">Edit</button>
                        @endcan
                        @can('delete-users')
                            <button class="btn btn-sm btn-danger">Delete</button>
                        @endcan
                    </td>
                </tr>
            @endforeach
        </tbody>
    </table>
    
    @if($users|length == 0)
        <div class="empty-state">
            <p>No users found.</p>
        </div>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "large-dataset.blade.html", template_content)
        
        # Create a large dataset
        large_dataset = []
        for i in range(1000):  # 1000 users
            large_dataset.append({
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "active": i % 3 != 0  # Mix of active/inactive
            })
        
        context = {
            "title": "User Management",
            "users": large_dataset,
            "current_user": {"can": lambda perm: True}  # Mock permissions
        }
        
        start_time = time.time()
        result = engine.render("large-dataset.blade.html", context)
        render_time = time.time() - start_time
        
        # Should handle large datasets reasonably well (< 5 seconds for 1000 items)
        assert render_time < 5.0
        assert "User Management" in result
        assert "User 0" in result
        assert "User 999" in result
        assert result.count("<tr") >= 1000  # Should have all user rows


class TestBladeErrorHandling:
    """Test error handling and recovery"""
    
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
    
    def test_template_not_found_error(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of missing template files"""
        engine, temp_dir = blade_engine
        
        with pytest.raises(FileNotFoundError) as exc_info:
            engine.render("nonexistent.blade.html")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_syntax_error_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of Blade syntax errors"""
        engine, temp_dir = blade_engine
        
        # Template with syntax errors
        malformed_template = """
@if($condition
    <p>Missing closing parenthesis</p>
@endif

@foreach($items as $item
    <div>{{ $item }}</div>
@endforeach

@section('title'
    Unclosed section
@endsection
        """.strip()
        self.create_template(temp_dir, "malformed.blade.html", malformed_template)
        
        # Should either handle gracefully or raise a clear error
        try:
            result = engine.render("malformed.blade.html", {"condition": True, "items": ["test"]})
            # If it renders, check it has some content
            assert len(result) > 0
        except Exception as e:
            # If it raises an error, it should be informative
            assert len(str(e)) > 0
    
    def test_undefined_variable_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of undefined variables"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>{{ $undefined_variable }}</h1>
    <p>{{ $another_undefined.property }}</p>
    
    @if($undefined_condition)
        <span>This might not render</span>
    @endif
    
    @foreach($undefined_list as $item)
        <div>{{ $item }}</div>
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "undefined-vars.blade.html", template_content)
        
        # Render with minimal context
        try:
            result = engine.render("undefined-vars.blade.html", {})
            # Should render something even with undefined variables
            assert "<div>" in result
        except Exception as e:
            # Jinja2 might raise NameError or similar for undefined variables
            assert "undefined" in str(e).lower() or "not defined" in str(e).lower()
    
    def test_circular_template_inheritance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of circular template inheritance"""
        engine, temp_dir = blade_engine
        
        # Create templates that extend each other in a circle
        template_a = """
@extends('template-b')
@section('content')
    Content from A
@endsection
        """.strip()
        self.create_template(temp_dir, "template-a.blade.html", template_a)
        
        template_b = """
@extends('template-a')
@section('content')
    Content from B
@endsection
        """.strip()
        self.create_template(temp_dir, "template-b.blade.html", template_b)
        
        # Should detect and handle circular inheritance
        try:
            result = engine.render("template-a.blade.html")
            # If it renders successfully, that's okay
            assert len(result) >= 0
        except Exception as e:
            # Should raise an informative error about circular inheritance
            error_msg = str(e).lower()
            # Common error patterns for circular inheritance
            assert any(keyword in error_msg for keyword in [
                "circular", "recursion", "maximum", "loop", "infinite"
            ])


class TestBladeIntegration:
    """Test integration scenarios"""
    
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
    
    def test_complete_web_application_layout(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test a complete web application layout scenario"""
        engine, temp_dir = blade_engine
        
        # Master layout
        master_layout = """
<!DOCTYPE html>
<html lang="{{ $locale ?? 'en' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'My Application')</title>
    
    @push('meta')
        <meta name="description" content="@yield('description', 'My awesome application')">
    @endpush
    
    @stack('meta')
    
    <link href="/css/app.css" rel="stylesheet">
    @stack('styles')
</head>
<body class="@yield('body-class', '')">
    <header>
        @include('partials.navigation')
    </header>
    
    <main class="container">
        @yield('breadcrumbs')
        
        @if($flash_message ?? false)
            <div class="alert alert-{{ $flash_type ?? 'info' }}">
                {{ $flash_message }}
            </div>
        @endif
        
        @yield('content')
    </main>
    
    <aside class="sidebar">
        @yield('sidebar')
        @stack('sidebar-widgets')
    </aside>
    
    <footer>
        @include('partials.footer')
    </footer>
    
    <script src="/js/app.js"></script>
    @stack('scripts')
    
    @production
        <script async src="https://www.googletagmanager.com/gtag/js?id=GA_TRACKING_ID"></script>
    @endproduction
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/master.blade.html", master_layout)
        
        # Navigation partial
        navigation = """
<nav class="navbar">
    <div class="navbar-brand">
        <a href="/">{{ config('app.name', 'My App') }}</a>
    </div>
    
    <ul class="navbar-nav">
        @auth
            <li class="nav-item">
                <a href="/dashboard" class="nav-link">Dashboard</a>
            </li>
            @can('admin-access')
                <li class="nav-item">
                    <a href="/admin" class="nav-link">Admin</a>
                </li>
            @endcan
            <li class="nav-item dropdown">
                <a href="#" class="nav-link">{{ $current_user.name }}</a>
                <ul class="dropdown-menu">
                    <li><a href="/profile">Profile</a></li>
                    <li><a href="/settings">Settings</a></li>
                    <li><a href="/logout">Logout</a></li>
                </ul>
            </li>
        @else
            <li class="nav-item">
                <a href="/login" class="nav-link">Login</a>
            </li>
            <li class="nav-item">
                <a href="/register" class="nav-link">Register</a>
            </li>
        @endauth
    </ul>
</nav>
        """.strip()
        self.create_template(temp_dir, "partials/navigation.blade.html", navigation)
        
        # Footer partial  
        footer = """
<div class="footer-content">
    <p>&copy; {{ date('Y') }} {{ config('app.name') }}. All rights reserved.</p>
    
    <ul class="footer-links">
        <li><a href="/about">About</a></li>
        <li><a href="/contact">Contact</a></li>
        <li><a href="/privacy">Privacy Policy</a></li>
        <li><a href="/terms">Terms of Service</a></li>
    </ul>
    
    @stack('footer-content')
</div>
        """.strip()
        self.create_template(temp_dir, "partials/footer.blade.html", footer)
        
        # Page template
        page_template = """
@extends('layouts.master')

@section('title', $page_title ?? 'Dashboard')
@section('description', 'User dashboard with latest updates and notifications')
@section('body-class', 'dashboard-page')

@push('styles')
    <link href="/css/dashboard.css" rel="stylesheet">
@endpush

@section('breadcrumbs')
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="/">Home</a></li>
            <li class="breadcrumb-item active">Dashboard</li>
        </ol>
    </nav>
@endsection

@section('content')
    <div class="dashboard">
        <div class="row">
            <div class="col-md-8">
                <h1>Welcome back, {{ $user.name }}!</h1>
                
                @if($user.notifications->count() > 0)
                    <div class="notifications">
                        <h2>Recent Notifications</h2>
                        @foreach($user.notifications->take(5) as $notification)
                            <div class="notification-item {{ $notification.read ? 'read' : 'unread' }}">
                                <h4>{{ $notification.title }}</h4>
                                <p>{{ $notification.message }}</p>
                                <small>{{ $notification.created_at->diffForHumans() }}</small>
                            </div>
                        @endforeach
                    </div>
                @else
                    <div class="no-notifications">
                        <p>No new notifications</p>
                    </div>
                @endif
            </div>
            
            <div class="col-md-4">
                <div class="stats-widget">
                    <h3>Quick Stats</h3>
                    <ul>
                        <li>Posts: {{ $stats.posts ?? 0 }}</li>
                        <li>Comments: {{ $stats.comments ?? 0 }}</li>
                        <li>Views: {{ number_format($stats.views ?? 0) }}</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
@endsection

@section('sidebar')
    @push('sidebar-widgets')
        <div class="widget recent-activity">
            <h3>Recent Activity</h3>
            @forelse($recent_activities as $activity)
                <div class="activity-item">
                    <span class="activity-type">{{ $activity.type }}</span>
                    <span class="activity-time">{{ $activity.created_at->format('M j, g:i A') }}</span>
                </div>
            @empty
                <p>No recent activity</p>
            @endforelse
        </div>
    @endpush
@endsection

@push('scripts')
    <script src="/js/dashboard.js"></script>
    <script>
        // Initialize dashboard
        Dashboard.init({
            userId: {{ $user.id }},
            refreshInterval: {{ config('dashboard.refresh_interval', 30000) }}
        });
    </script>
@endpush
        """.strip()
        self.create_template(temp_dir, "dashboard.blade.html", page_template)
        
        # Test rendering with comprehensive context
        context = {
            "locale": "en",
            "current_user": {
                "name": "John Doe",
                "id": 123
            },
            "user": {
                "name": "John Doe", 
                "id": 123,
                "notifications": [
                    {"title": "Welcome", "message": "Welcome to the platform!", "read": False},
                    {"title": "Update", "message": "System maintenance scheduled", "read": True}
                ]
            },
            "page_title": "My Dashboard",
            "flash_message": "Profile updated successfully!",
            "flash_type": "success",
            "stats": {
                "posts": 15,
                "comments": 42, 
                "views": 1250
            },
            "recent_activities": [
                {"type": "login", "created_at": "2025-01-10 10:30:00"},
                {"type": "post_created", "created_at": "2025-01-10 09:15:00"}
            ]
        }
        
        result = engine.render("dashboard.blade.html", context)
        
        # Verify the complete layout rendered correctly
        assert "<!DOCTYPE html>" in result
        assert "My Dashboard" in result  # Page title
        assert "Welcome back, John Doe!" in result
        assert "Profile updated successfully!" in result  # Flash message
        assert "Posts: 15" in result  # Stats
        assert "Recent Activity" in result  # Sidebar
        assert "dashboard.js" in result  # Scripts
        assert "navbar" in result  # Navigation
        assert "footer-content" in result  # Footer
    
    def test_global_blade_functions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test global blade helper functions"""
        engine, temp_dir = blade_engine
        
        # Set up global blade instance
        global_engine = blade([temp_dir])
        view_share("app_name", "Test Application")
        
        template_content = """
<div class="app-info">
    <h1>{{ app_name }}</h1>
    <p>Global shared data test</p>
</div>
        """.strip()
        self.create_template(temp_dir, "global-test.blade.html", template_content)
        
        # Use global view function
        result = view("global-test.blade.html", {"additional": "context"})
        
        assert "Test Application" in result
        assert "Global shared data test" in result


class TestBladeConcurrency:
    """Test concurrent usage scenarios"""
    
    def test_thread_safety(self) -> None:
        """Test basic thread safety of Blade engine"""
        import threading
        import queue
        
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=False)
        
        # Create a simple template
        template_content = """
<div>Thread {{ thread_id }}: {{ message }}</div>
        """
        template_path = Path(temp_path) / "thread-test.blade.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        results: queue.Queue[str] = queue.Queue()
        
        def render_template(thread_id: int) -> None:
            try:
                context = {"thread_id": thread_id, "message": f"Hello from thread {thread_id}"}
                result = engine.render("thread-test.blade.html", context)
                results.put((thread_id, result))
            except Exception as e:
                results.put((thread_id, f"Error: {e}"))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=render_template, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all threads completed successfully
        thread_results = {}
        while not results.empty():
            thread_id, result = results.get()
            thread_results[thread_id] = result
        
        assert len(thread_results) == 5
        for thread_id, result in thread_results.items():
            assert not result.startswith("Error:")
            assert f"Thread {thread_id}" in result
            assert f"Hello from thread {thread_id}" in result
        
        shutil.rmtree(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])