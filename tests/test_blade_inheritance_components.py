"""
Comprehensive Blade Template Inheritance and Component Test Suite
Tests template inheritance, component system, slots, and advanced composition patterns
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List, Optional
import json

from app.View.BladeEngine import BladeEngine


class TestBladeInheritanceAndComponents:
    """Test template inheritance and component system comprehensively"""
    
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
    
    def test_complex_template_inheritance_hierarchy(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex multi-level template inheritance with section management"""
        engine, temp_dir = blade_engine
        
        # Base layout - top level
        base_layout = """
<!DOCTYPE html>
<html lang="{{ app_locale | default('en') }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'Default Title') - {{ app_name }}</title>
    
    <!-- Meta sections -->
    @hasSection('meta')
        @yield('meta')
    @else
        <meta name="description" content="Default description">
        <meta name="keywords" content="default, keywords">
    @endhasSection
    
    <!-- Favicon -->
    <link rel="icon" href="{{ asset('favicon.ico') }}">
    
    <!-- CSS Stack with base styles -->
    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
    @stack('css')
    
    <!-- Custom head content -->
    @yield('head')
    
    @production
        <!-- Production analytics -->
        <script async src="https://analytics.example.com/track.js"></script>
    @endproduction
</head>
<body class="@yield('body-class', 'default-layout')">
    <!-- Skip to content for accessibility -->
    <a href="#main-content" class="skip-to-content">Skip to main content</a>
    
    <!-- Header section -->
    <header class="site-header">
        @hasSection('header')
            @yield('header')
        @else
            <div class="default-header">
                <h1>{{ app_name }}</h1>
                <nav>@yield('navigation', '<p>No navigation provided</p>')</nav>
            </div>
        @endhasSection
    </header>
    
    <!-- Breadcrumbs -->
    @hasSection('breadcrumbs')
        <nav class="breadcrumbs" aria-label="Breadcrumb">
            @yield('breadcrumbs')
        </nav>
    @endhasSection
    
    <!-- Flash messages -->
    @if(flash_messages)
        <div class="flash-messages">
            @foreach(flash_messages as type, messages)
                @foreach(messages as message)
                    <div class="alert alert-{{ type }}" role="alert">
                        {{ message }}
                    </div>
                @endforeach
            @endforeach
        </div>
    @endif
    
    <!-- Main content wrapper -->
    <div class="content-wrapper">
        <!-- Sidebar (optional) -->
        @hasSection('sidebar')
            <aside class="sidebar" role="complementary">
                @yield('sidebar')
            </aside>
        @endhasSection
        
        <!-- Main content area -->
        <main id="main-content" class="main-content @hasSection('sidebar') ? 'has-sidebar' : 'no-sidebar' @endhasSection">
            <!-- Content header with actions -->
            @hasSection('content-header')
                <div class="content-header">
                    @yield('content-header')
                    
                    @hasSection('page-actions')
                        <div class="page-actions">
                            @yield('page-actions')
                        </div>
                    @endhasSection
                </div>
            @endhasSection
            
            <!-- Main content -->
            @yield('content')
            
            <!-- Additional content sections -->
            @hasSection('after-content')
                <div class="after-content">
                    @yield('after-content')
                </div>
            @endhasSection
        </main>
    </div>
    
    <!-- Footer -->
    <footer class="site-footer">
        @hasSection('footer')
            @yield('footer')
        @else
            <p>&copy; {{ date('Y') }} {{ app_name }}. All rights reserved.</p>
        @endhasSection
        
        @hasSection('footer-scripts')
            @yield('footer-scripts')
        @endhasSection
    </footer>
    
    <!-- JavaScript -->
    <script src="{{ asset('js/app.js') }}"></script>
    @stack('scripts')
    
    <!-- Page-specific JavaScript -->
    @hasSection('scripts')
        <script>
            @yield('scripts')
        </script>
    @endhasSection
</body>
</html>
        """.strip()
        
        # Admin layout - extends base
        admin_layout = """
@extends('base-layout')

@section('body-class', 'admin-layout')

@push('css')
    <link rel="stylesheet" href="{{ asset('css/admin.css') }}">
    <link rel="stylesheet" href="{{ asset('css/admin-components.css') }}">
@endpush

@section('header')
    <div class="admin-header">
        <div class="admin-brand">
            <img src="{{ asset('images/admin-logo.png') }}" alt="{{ app_name }} Admin">
            <h1>{{ app_name }} Administration</h1>
        </div>
        
        <div class="admin-user-menu">
            @auth
                <div class="user-info">
                    <img src="{{ current_user.avatar }}" alt="{{ current_user.name }}" class="user-avatar">
                    <span class="user-name">{{ current_user.name }}</span>
                    
                    @hasrole('super-admin')
                        <span class="role-badge super-admin">Super Admin</span>
                    @elseif(current_user.has_role('admin'))
                        <span class="role-badge admin">Admin</span>
                    @endhasrole
                </div>
                
                <div class="admin-actions">
                    <a href="{{ route('admin.profile') }}">Profile</a>
                    <a href="{{ route('admin.settings') }}">Settings</a>
                    <form method="POST" action="{{ route('logout') }}" style="display: inline;">
                        @csrf
                        <button type="submit">Logout</button>
                    </form>
                </div>
            @endauth
        </div>
    </div>
@endsection

@section('navigation')
    <nav class="admin-navigation">
        <ul class="nav-menu">
            <li class="{{ request.is('admin/dashboard') ? 'active' : '' }}">
                <a href="{{ route('admin.dashboard') }}">
                    <i class="icon-dashboard"></i> Dashboard
                </a>
            </li>
            
            @can('manage_users')
                <li class="{{ request.is('admin/users*') ? 'active' : '' }}">
                    <a href="{{ route('admin.users.index') }}">
                        <i class="icon-users"></i> Users
                    </a>
                </li>
            @endcan
            
            @can('manage_content')
                <li class="has-submenu {{ request.is('admin/content*') ? 'active' : '' }}">
                    <a href="#" class="submenu-toggle">
                        <i class="icon-content"></i> Content <i class="icon-chevron-down"></i>
                    </a>
                    <ul class="submenu">
                        <li><a href="{{ route('admin.posts.index') }}">Posts</a></li>
                        <li><a href="{{ route('admin.pages.index') }}">Pages</a></li>
                        <li><a href="{{ route('admin.media.index') }}">Media</a></li>
                    </ul>
                </li>
            @endcan
            
            @can('view_analytics')
                <li class="{{ request.is('admin/analytics*') ? 'active' : '' }}">
                    <a href="{{ route('admin.analytics') }}">
                        <i class="icon-chart"></i> Analytics
                    </a>
                </li>
            @endcan
            
            <li class="{{ request.is('admin/settings*') ? 'active' : '' }}">
                <a href="{{ route('admin.settings') }}">
                    <i class="icon-settings"></i> Settings
                </a>
            </li>
        </ul>
    </nav>
@endsection

@section('sidebar')
    <div class="admin-sidebar">
        <!-- Quick stats -->
        <div class="sidebar-widget stats-widget">
            <h3>Quick Stats</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-number">{{ stats.users | number_format }}</span>
                    <span class="stat-label">Users</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{{ stats.posts | number_format }}</span>
                    <span class="stat-label">Posts</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{{ stats.pages | number_format }}</span>
                    <span class="stat-label">Pages</span>
                </div>
            </div>
        </div>
        
        <!-- Recent activity -->
        <div class="sidebar-widget activity-widget">
            <h3>Recent Activity</h3>
            @forelse(recent_activity as activity)
                <div class="activity-item">
                    <div class="activity-icon {{ activity.type }}">
                        <i class="icon-{{ activity.type }}"></i>
                    </div>
                    <div class="activity-content">
                        <p>{{ activity.description }}</p>
                        <small>{{ activity.created_at | time_ago }}</small>
                    </div>
                </div>
            @empty
                <p>No recent activity</p>
            @endforelse
        </div>
        
        <!-- System info -->
        @hasrole('super-admin')
            <div class="sidebar-widget system-widget">
                <h3>System Information</h3>
                <ul class="system-info">
                    <li>Version: {{ app_version }}</li>
                    <li>Environment: {{ app_env }}</li>
                    <li>Uptime: {{ system_uptime }}</li>
                    <li>Memory: {{ memory_usage }}</li>
                </ul>
            </div>
        @endhasrole
        
        @yield('admin-sidebar-extra')
    </div>
@endsection

@push('scripts')
    <script src="{{ asset('js/admin.js') }}"></script>
    <script>
        // Admin-specific JavaScript
        window.adminConfig = @json(admin_config);
    </script>
@endpush
        """.strip()
        
        # User dashboard - extends admin layout
        user_dashboard = """
@extends('admin-layout')

@section('title', 'User Management Dashboard')

@section('meta')
    <meta name="description" content="Manage users, roles, and permissions">
    <meta name="keywords" content="users, management, admin, roles, permissions">
@endsection

@push('css')
    <link rel="stylesheet" href="{{ asset('css/user-management.css') }}">
@endpush

@section('breadcrumbs')
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">Dashboard</a></li>
        <li class="breadcrumb-item active" aria-current="page">User Management</li>
    </ol>
@endsection

@section('content-header')
    <div class="content-header-main">
        <h1>User Management</h1>
        <p class="content-subtitle">Manage system users, their roles, and permissions</p>
    </div>
@endsection

@section('page-actions')
    <div class="btn-group">
        @can('create_users')
            <a href="{{ route('admin.users.create') }}" class="btn btn-primary">
                <i class="icon-plus"></i> Create User
            </a>
        @endcan
        
        @can('import_users')
            <button class="btn btn-secondary" id="import-users">
                <i class="icon-upload"></i> Import Users
            </button>
        @endcan
        
        @can('export_users')
            <a href="{{ route('admin.users.export') }}" class="btn btn-outline">
                <i class="icon-download"></i> Export Users
            </a>
        @endcan
    </div>
@endsection

@section('content')
    <!-- Filter and search section -->
    <div class="filters-section">
        <form method="GET" action="{{ route('admin.users.index') }}" class="filters-form">
            <div class="filter-row">
                <div class="filter-group">
                    <label for="search">Search Users</label>
                    <input type="text" id="search" name="search" value="{{ request.get('search') }}" 
                           placeholder="Search by name, email, or username">
                </div>
                
                <div class="filter-group">
                    <label for="role">Filter by Role</label>
                    <select id="role" name="role">
                        <option value="">All Roles</option>
                        @foreach(available_roles as role)
                            <option value="{{ role.name }}" {{ request.get('role') == role.name ? 'selected' : '' }}>
                                {{ role.display_name }}
                            </option>
                        @endforeach
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="status">Filter by Status</label>
                    <select id="status" name="status">
                        <option value="">All Statuses</option>
                        <option value="active" {{ request.get('status') == 'active' ? 'selected' : '' }}>Active</option>
                        <option value="inactive" {{ request.get('status') == 'inactive' ? 'selected' : '' }}>Inactive</option>
                        <option value="pending" {{ request.get('status') == 'pending' ? 'selected' : '' }}>Pending</option>
                        <option value="suspended" {{ request.get('status') == 'suspended' ? 'selected' : '' }}>Suspended</option>
                    </select>
                </div>
                
                <div class="filter-actions">
                    <button type="submit" class="btn btn-primary">Filter</button>
                    <a href="{{ route('admin.users.index') }}" class="btn btn-outline">Clear</a>
                </div>
            </div>
        </form>
    </div>
    
    <!-- Users table -->
    <div class="users-table-container">
        <table class="users-table">
            <thead>
                <tr>
                    <th>
                        <input type="checkbox" id="select-all">
                    </th>
                    <th>User</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                @forelse(users as user)
                    <tr class="user-row {{ user.status }}">
                        <td>
                            <input type="checkbox" name="selected_users[]" value="{{ user.id }}">
                        </td>
                        <td class="user-info">
                            <div class="user-avatar-container">
                                @if(user.avatar)
                                    <img src="{{ user.avatar }}" alt="{{ user.name }}" class="user-avatar">
                                @else
                                    <div class="user-avatar-placeholder">{{ user.name | first }}</div>
                                @endif
                            </div>
                            <div class="user-details">
                                <strong class="user-name">{{ user.name }}</strong>
                                @if(user.username)
                                    <span class="username">@{{ user.username }}</span>
                                @endif
                            </div>
                        </td>
                        <td class="user-email">
                            {{ user.email }}
                            @unless(user.email_verified_at)
                                <span class="unverified-badge">Unverified</span>
                            @endunless
                        </td>
                        <td class="user-role">
                            @foreach(user.roles as role)
                                <span class="role-badge {{ role.name }}">{{ role.display_name }}</span>
                            @endforeach
                        </td>
                        <td class="user-status">
                            <span class="status-indicator {{ user.status }}">{{ user.status | title }}</span>
                        </td>
                        <td class="last-login">
                            @if(user.last_login_at)
                                {{ user.last_login_at | time_ago }}
                            @else
                                <span class="never">Never</span>
                            @endif
                        </td>
                        <td class="user-actions">
                            <div class="action-buttons">
                                @can('view_users')
                                    <a href="{{ route('admin.users.show', user.id) }}" class="btn btn-sm btn-outline" title="View">
                                        <i class="icon-eye"></i>
                                    </a>
                                @endcan
                                
                                @can('edit_users')
                                    <a href="{{ route('admin.users.edit', user.id) }}" class="btn btn-sm btn-primary" title="Edit">
                                        <i class="icon-edit"></i>
                                    </a>
                                @endcan
                                
                                @can('delete_users')
                                    @unless(user.id == current_user.id)
                                        <button class="btn btn-sm btn-danger delete-user" data-user-id="{{ user.id }}" title="Delete">
                                            <i class="icon-trash"></i>
                                        </button>
                                    @endunless
                                @endcan
                                
                                <div class="dropdown">
                                    <button class="btn btn-sm btn-outline dropdown-toggle" data-toggle="dropdown">
                                        <i class="icon-more"></i>
                                    </button>
                                    <ul class="dropdown-menu">
                                        @can('impersonate_users')
                                            @unless(user.id == current_user.id)
                                                <li><a href="{{ route('admin.users.impersonate', user.id) }}">Login as User</a></li>
                                            @endunless
                                        @endcan
                                        
                                        @if(user.status == 'active')
                                            @can('suspend_users')
                                                <li><a href="#" class="suspend-user" data-user-id="{{ user.id }}">Suspend User</a></li>
                                            @endcan
                                        @else
                                            @can('activate_users')
                                                <li><a href="#" class="activate-user" data-user-id="{{ user.id }}">Activate User</a></li>
                                            @endcan
                                        @endif
                                        
                                        @can('reset_passwords')
                                            <li><a href="#" class="reset-password" data-user-id="{{ user.id }}">Reset Password</a></li>
                                        @endcan
                                    </ul>
                                </div>
                            </div>
                        </td>
                    </tr>
                @empty
                    <tr>
                        <td colspan="7" class="no-users">
                            <div class="empty-state">
                                <i class="icon-users-empty"></i>
                                <h3>No users found</h3>
                                <p>No users match your current filters.</p>
                                @can('create_users')
                                    <a href="{{ route('admin.users.create') }}" class="btn btn-primary">Create First User</a>
                                @endcan
                            </div>
                        </td>
                    </tr>
                @endforelse
            </tbody>
        </table>
    </div>
    
    <!-- Pagination -->
    @if(users.hasPages())
        <div class="pagination-container">
            {{ users.links() }}
        </div>
    @endif
    
    <!-- Bulk actions -->
    <div class="bulk-actions" style="display: none;">
        <div class="bulk-actions-bar">
            <span class="selected-count">0 users selected</span>
            <div class="bulk-actions-buttons">
                @can('delete_users')
                    <button class="btn btn-danger bulk-delete">Delete Selected</button>
                @endcan
                
                @can('export_users')
                    <button class="btn btn-secondary bulk-export">Export Selected</button>
                @endcan
                
                @can('edit_users')
                    <select class="bulk-role-change">
                        <option value="">Change Role...</option>
                        @foreach(available_roles as role)
                            <option value="{{ role.name }}">{{ role.display_name }}</option>
                        @endforeach
                    </select>
                @endcan
            </div>
        </div>
    </div>
@endsection

@section('admin-sidebar-extra')
    <!-- User statistics -->
    <div class="sidebar-widget user-stats-widget">
        <h3>User Statistics</h3>
        <div class="stats-list">
            <div class="stat-item">
                <span class="stat-label">Total Users:</span>
                <span class="stat-value">{{ user_stats.total | number_format }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Active Users:</span>
                <span class="stat-value">{{ user_stats.active | number_format }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">New This Month:</span>
                <span class="stat-value">{{ user_stats.new_this_month | number_format }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Online Now:</span>
                <span class="stat-value">{{ user_stats.online_now | number_format }}</span>
            </div>
        </div>
    </div>
    
    <!-- Role distribution -->
    <div class="sidebar-widget role-distribution-widget">
        <h3>Role Distribution</h3>
        <div class="role-chart">
            @foreach(role_distribution as role_name, count)
                <div class="role-bar">
                    <span class="role-name">{{ role_name | title }}</span>
                    <div class="role-bar-container">
                        <div class="role-bar-fill {{ role_name }}" style="width: {{ (count / user_stats.total * 100) }}%"></div>
                    </div>
                    <span class="role-count">{{ count }}</span>
                </div>
            @endforeach
        </div>
    </div>
@endsection

@section('footer-scripts')
    @parent
    
    <script>
        // User management specific scripts
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize user management functionality
            initUserManagement();
        });
    </script>
@endsection

@push('scripts')
    <script src="{{ asset('js/user-management.js') }}"></script>
    <script>
        // Page configuration
        window.userManagementConfig = {
            deleteConfirmMessage: 'Are you sure you want to delete this user?',
            bulkDeleteConfirmMessage: 'Are you sure you want to delete the selected users?',
            routes: {
                delete: '{{ route("admin.users.destroy", ":id") }}',
                bulkDelete: '{{ route("admin.users.bulk-delete") }}',
                suspend: '{{ route("admin.users.suspend", ":id") }}',
                activate: '{{ route("admin.users.activate", ":id") }}',
                resetPassword: '{{ route("admin.users.reset-password", ":id") }}'
            }
        };
    </script>
@endpush
        """.strip()
        
        # Create all templates
        self.create_template(temp_dir, "base-layout.blade.html", base_layout)
        self.create_template(temp_dir, "admin-layout.blade.html", admin_layout)
        self.create_template(temp_dir, "user-dashboard.blade.html", user_dashboard)
        
        context = {
            "app_name": "Advanced App",
            "app_locale": "en",
            "app_version": "1.2.3",
            "app_env": "testing",
            "flash_messages": {
                "success": ["User created successfully!"],
                "info": ["Welcome to the admin panel"]
            },
            "current_user": {
                "id": 1,
                "name": "Admin User",
                "email": "admin@example.com",
                "avatar": "/avatars/admin.jpg",
                "roles": [{"name": "super-admin", "display_name": "Super Administrator"}],
                "has_role": lambda role: role == "super-admin"
            },
            "stats": {
                "users": 1250,
                "posts": 3400,
                "pages": 150
            },
            "recent_activity": [
                {"type": "user", "description": "New user registered", "created_at": "2024-01-15T10:30:00"},
                {"type": "post", "description": "New post published", "created_at": "2024-01-15T09:15:00"}
            ],
            "system_uptime": "15 days, 3 hours",
            "memory_usage": "512MB / 2GB",
            "admin_config": {"theme": "dark", "sidebar_collapsed": False},
            "request": {
                "is": lambda path: path == "admin/users",
                "get": lambda key: {"search": "john", "role": "admin"}.get(key, "")
            },
            "available_roles": [
                {"name": "admin", "display_name": "Administrator"},
                {"name": "moderator", "display_name": "Moderator"},
                {"name": "user", "display_name": "Regular User"}
            ],
            "users": [
                {
                    "id": 2,
                    "name": "John Smith", 
                    "username": "johnsmith",
                    "email": "john@example.com",
                    "avatar": "/avatars/john.jpg",
                    "email_verified_at": "2024-01-01T00:00:00",
                    "roles": [{"name": "admin", "display_name": "Administrator"}],
                    "status": "active",
                    "last_login_at": "2024-01-15T08:30:00"
                },
                {
                    "id": 3,
                    "name": "Jane Doe",
                    "username": None,
                    "email": "jane@example.com", 
                    "avatar": None,
                    "email_verified_at": None,
                    "roles": [{"name": "user", "display_name": "Regular User"}],
                    "status": "pending",
                    "last_login_at": None
                }
            ],
            "user_stats": {
                "total": 1250,
                "active": 1100,
                "new_this_month": 150,
                "online_now": 45
            },
            "role_distribution": {
                "admin": 50,
                "moderator": 100,
                "user": 1100
            },
            "route": lambda name, *args: f"/{name.replace('.', '/')}" + (f"/{args[0]}" if args else ""),
            "asset": lambda path: f"/assets/{path.lstrip('/')}",
            "date": lambda format_str: "2024"
        }
        
        result = engine.render("user-dashboard.blade.html", context)
        
        # Verify inheritance chain
        assert "Advanced App" in result  # App name from base
        assert "User Management Dashboard" in result  # Title from user dashboard
        assert "admin-layout" in result  # Body class from admin layout
        
        # Verify section inheritance and overrides
        assert "Manage users, roles, and permissions" in result  # Meta description override
        assert "User Management" in result  # Content header
        assert "Create User" in result  # Page actions
        
        # Verify nested sections and conditions
        assert "Super Administrator" in result  # Role badge
        assert "John Smith" in result and "Jane Doe" in result  # Users table
        assert "Administrator" in result  # Role display
        assert "Unverified" in result  # Email verification status
        
        # Verify sidebar content from admin layout
        assert "Quick Stats" in result  # Sidebar widget
        assert "1,250" in result  # Formatted user count
        assert "Role Distribution" in result  # Additional sidebar content
        
        # Verify script and CSS stacks
        assert "user-management.css" in result  # Pushed CSS
        assert "admin.js" in result  # Admin layout script
        assert "user-management.js" in result  # Page-specific script
        
        # Verify complex conditional logic
        assert "Login as User" in result  # Impersonation option
        assert "Reset Password" in result  # Password reset option
        
        # Verify flash messages from base layout
        assert "User created successfully!" in result
        assert "Welcome to the admin panel" in result
    
    def test_advanced_component_system_with_slots(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test advanced component system with slots, props, and composition"""
        engine, temp_dir = blade_engine
        
        # Base card component
        card_component = """
<div class="card {{ $variant ?? 'default' }} {{ $size ?? 'medium' }} {{ $class ?? '' }}">
    @isset($header)
        <div class="card-header {{ $headerClass ?? '' }}">
            {{ $header }}
            
            @isset($actions)
                <div class="card-actions">
                    {{ $actions }}
                </div>
            @endisset
        </div>
    @endisset
    
    <div class="card-body {{ $bodyClass ?? '' }}">
        {{ $slot }}
        
        @isset($aside)
            <aside class="card-aside">
                {{ $aside }}
            </aside>
        @endisset
    </div>
    
    @isset($footer)
        <div class="card-footer {{ $footerClass ?? '' }}">
            {{ $footer }}
            
            @isset($footerActions)
                <div class="footer-actions">
                    {{ $footerActions }}
                </div>
            @endisset
        </div>
    @endisset
</div>
        """.strip()
        
        # Modal component with complex slots
        modal_component = """
<div class="modal {{ $show ? 'show' : '' }}" id="{{ $id ?? 'modal' }}" tabindex="-1">
    <div class="modal-dialog {{ $size ?? 'medium' }} {{ $centered ? 'modal-dialog-centered' : '' }}">
        <div class="modal-content">
            @isset($header)
                <div class="modal-header">
                    <h5 class="modal-title">{{ $header }}</h5>
                    
                    @unless($hideClose ?? false)
                        <button type="button" class="btn-close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    @endunless
                </div>
            @endisset
            
            <div class="modal-body">
                {{ $slot }}
            </div>
            
            @isset($footer)
                <div class="modal-footer">
                    {{ $footer }}
                </div>
            @else
                @if($showDefaultFooter ?? true)
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        @isset($primaryAction)
                            {{ $primaryAction }}
                        @else
                            <button type="button" class="btn btn-primary">{{ $primaryActionText ?? 'Save' }}</button>
                        @endisset
                    </div>
                @endif
            @endisset
        </div>
    </div>
</div>

@push('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            @if($autoShow ?? false)
                new Modal('#{{ $id ?? "modal" }}').show();
            @endif
        });
    </script>
@endpush
        """.strip()
        
        # Form component with validation
        form_component = """
<form {{ $attributes->merge(['class' => 'form ' . ($variant ?? 'default')]) }} 
      method="{{ $method ?? 'POST' }}" 
      action="{{ $action }}"
      @if($enctype ?? false) enctype="{{ $enctype }}" @endif>
    
    @if($method && strtoupper($method) != 'GET' && strtoupper($method) != 'POST')
        @method($method)
    @endif
    
    @if(($csrf ?? true) && strtoupper($method ?? 'POST') != 'GET')
        @csrf
    @endif
    
    @isset($header)
        <div class="form-header">
            {{ $header }}
        </div>
    @endisset
    
    <div class="form-body">
        @if($errors ?? false)
            @if($errors->any())
                <div class="alert alert-danger">
                    <h6>Please correct the following errors:</h6>
                    <ul>
                        @foreach($errors->all() as $error)
                            <li>{{ $error }}</li>
                        @endforeach
                    </ul>
                </div>
            @endif
        @endif
        
        {{ $slot }}
    </div>
    
    @isset($footer)
        <div class="form-footer">
            {{ $footer }}
        </div>
    @else
        @if($showDefaultFooter ?? true)
            <div class="form-footer">
                <button type="submit" class="btn btn-primary {{ $submitClass ?? '' }}" 
                        @if($submitDisabled ?? false) disabled @endif>
                    {{ $submitText ?? 'Submit' }}
                </button>
                
                @if($showCancel ?? true)
                    <a href="{{ $cancelUrl ?? '#' }}" class="btn btn-secondary">
                        {{ $cancelText ?? 'Cancel' }}
                    </a>
                @endif
                
                @isset($additionalActions)
                    {{ $additionalActions }}
                @endisset
            </div>
        @endif
    @endisset
</form>
        """.strip()
        
        # Input field component
        input_component = """
@props(['name', 'type' => 'text', 'label', 'value' => null, 'placeholder' => null, 'required' => false, 'disabled' => false])

<div class="form-group {{ $errors->has($name) ? 'has-error' : '' }}">
    @if($label ?? false)
        <label for="{{ $id ?? $name }}" class="form-label {{ $required ? 'required' : '' }}">
            {{ $label }}
            @if($required)
                <span class="required-indicator">*</span>
            @endif
        </label>
    @endif
    
    @switch($type)
        @case('textarea')
            <textarea name="{{ $name }}" 
                      id="{{ $id ?? $name }}"
                      class="form-control {{ $class ?? '' }}"
                      @if($placeholder) placeholder="{{ $placeholder }}" @endif
                      @if($required) required @endif
                      @if($disabled) disabled @endif
                      @if($rows ?? false) rows="{{ $rows }}" @endif
                      {{ $attributes ?? '' }}>{{ old($name, $value) }}</textarea>
        @break
        
        @case('select')
            <select name="{{ $name }}" 
                    id="{{ $id ?? $name }}"
                    class="form-control {{ $class ?? '' }}"
                    @if($required) required @endif
                    @if($disabled) disabled @endif
                    @if($multiple ?? false) multiple @endif
                    {{ $attributes ?? '' }}>
                
                @if($placeholder && !($multiple ?? false))
                    <option value="">{{ $placeholder }}</option>
                @endif
                
                @isset($options)
                    @foreach($options as $optionValue => $optionLabel)
                        <option value="{{ $optionValue }}" 
                                @if(old($name, $value) == $optionValue) selected @endif>
                            {{ $optionLabel }}
                        </option>
                    @endforeach
                @endisset
                
                {{ $slot }}
            </select>
        @break
        
        @case('checkbox')
        @case('radio')
            <div class="form-check {{ $inline ?? false ? 'form-check-inline' : '' }}">
                <input type="{{ $type }}" 
                       name="{{ $name }}" 
                       id="{{ $id ?? $name }}"
                       value="{{ $checkValue ?? '1' }}"
                       class="form-check-input {{ $class ?? '' }}"
                       @if(old($name, $value)) checked @endif
                       @if($required) required @endif
                       @if($disabled) disabled @endif
                       {{ $attributes ?? '' }}>
                
                @if($label ?? false)
                    <label for="{{ $id ?? $name }}" class="form-check-label">
                        {{ $label }}
                    </label>
                @endif
            </div>
        @break
        
        @default
            <input type="{{ $type }}" 
                   name="{{ $name }}" 
                   id="{{ $id ?? $name }}"
                   value="{{ old($name, $value) }}"
                   class="form-control {{ $class ?? '' }}"
                   @if($placeholder) placeholder="{{ $placeholder }}" @endif
                   @if($required) required @endif
                   @if($disabled) disabled @endif
                   @if($min ?? false) min="{{ $min }}" @endif
                   @if($max ?? false) max="{{ $max }}" @endif
                   @if($step ?? false) step="{{ $step }}" @endif
                   {{ $attributes ?? '' }}>
    @endswitch
    
    @if($help ?? false)
        <small class="form-text text-muted">{{ $help }}</small>
    @endif
    
    @error($name)
        <div class="invalid-feedback">{{ $message }}</div>
    @enderror
    
    @isset($append)
        <div class="input-group-append">
            {{ $append }}
        </div>
    @endisset
</div>
        """.strip()
        
        # Data table component
        data_table_component = """
@props(['data', 'columns', 'paginated' => false, 'sortable' => false, 'searchable' => false])

<div class="data-table-container">
    @if($searchable)
        <div class="table-search">
            <input type="text" class="form-control" placeholder="Search..." id="table-search">
        </div>
    @endif
    
    <div class="table-responsive">
        <table class="table data-table {{ $class ?? '' }}">
            <thead>
                <tr>
                    @foreach($columns as $key => $column)
                        <th @if($sortable) class="sortable" data-column="{{ $key }}" @endif>
                            {{ is_array($column) ? $column['label'] : $column }}
                            @if($sortable)
                                <i class="sort-icon"></i>
                            @endif
                        </th>
                    @endforeach
                    
                    @isset($actions)
                        <th class="actions-column">Actions</th>
                    @endisset
                </tr>
            </thead>
            <tbody>
                @forelse($data as $row)
                    <tr>
                        @foreach($columns as $key => $column)
                            <td>
                                @if(is_array($column) && isset($column['render']))
                                    {!! $column['render']($row) !!}
                                @else
                                    {{ data_get($row, $key, '-') }}
                                @endif
                            </td>
                        @endforeach
                        
                        @isset($actions)
                            <td class="actions">
                                {!! $actions($row) !!}
                            </td>
                        @endisset
                    </tr>
                @empty
                    <tr>
                        <td colspan="{{ count($columns) + (isset($actions) ? 1 : 0) }}" class="text-center">
                            @isset($empty)
                                {{ $empty }}
                            @else
                                <div class="empty-state">
                                    <p>No data available</p>
                                </div>
                            @endisset
                        </td>
                    </tr>
                @endforelse
            </tbody>
        </table>
    </div>
    
    @if($paginated && method_exists($data, 'links'))
        <div class="table-pagination">
            {{ $data->links() }}
        </div>
    @endif
</div>

@push('scripts')
    @if($searchable || $sortable)
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                @if($searchable)
                    initTableSearch('#table-search', '.data-table');
                @endif
                
                @if($sortable)
                    initTableSorting('.data-table');
                @endif
            });
        </script>
    @endif
@endpush
        """.strip()
        
        # Page template using components
        component_demo_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Component Demo</title>
    <link rel="stylesheet" href="/css/components.css">
</head>
<body>
    <!-- Card components with various slots -->
    <div class="components-demo">
        <h1>Component System Demo</h1>
        
        <!-- Basic card -->
        <x-card variant="primary" size="large">
            <x-slot:header>
                <h2>User Profile</h2>
            </x-slot>
            
            <div class="profile-content">
                <p>This is the main card content showing user profile information.</p>
                <p>Name: John Doe</p>
                <p>Email: john@example.com</p>
            </div>
            
            <x-slot:aside>
                <div class="profile-stats">
                    <h4>Quick Stats</h4>
                    <ul>
                        <li>Posts: 42</li>
                        <li>Followers: 1.2K</li>
                        <li>Following: 234</li>
                    </ul>
                </div>
            </x-slot>
            
            <x-slot:footer>
                <p class="last-active">Last active: 2 hours ago</p>
            </x-slot>
            
            <x-slot:actions>
                <button class="btn btn-primary">Edit Profile</button>
                <button class="btn btn-secondary">Message</button>
            </x-slot>
        </x-card>
        
        <!-- Modal component -->
        <x-modal id="confirm-modal" size="small" centered="true" autoShow="false">
            <x-slot:header>
                Confirm Action
            </x-slot>
            
            <p>Are you sure you want to delete this item? This action cannot be undone.</p>
            
            <x-slot:footer>
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-danger">Delete</button>
            </x-slot>
        </x-modal>
        
        <!-- Complex form with input components -->
        <x-form action="/users" method="POST" enctype="multipart/form-data" variant="bordered">
            <x-slot:header>
                <h2>Create New User</h2>
                <p>Fill out the form below to create a new user account.</p>
            </x-slot>
            
            <div class="form-row">
                <div class="col-md-6">
                    <x-input name="first_name" 
                             type="text"
                             label="First Name"
                             placeholder="Enter first name"
                             required="true"
                             value="{{ $user->first_name ?? '' }}" />
                </div>
                
                <div class="col-md-6">
                    <x-input name="last_name"
                             type="text" 
                             label="Last Name"
                             placeholder="Enter last name"
                             required="true"
                             value="{{ $user->last_name ?? '' }}" />
                </div>
            </div>
            
            <x-input name="email"
                     type="email"
                     label="Email Address"
                     placeholder="user@example.com"
                     required="true"
                     help="We'll never share your email with anyone else."
                     value="{{ $user->email ?? '' }}" />
            
            <x-input name="password"
                     type="password"
                     label="Password"
                     required="true"
                     min="8"
                     help="Password must be at least 8 characters long." />
            
            <x-input name="role"
                     type="select"
                     label="User Role"
                     required="true"
                     placeholder="Select a role"
                     :options="$roles" />
            
            <x-input name="bio"
                     type="textarea"
                     label="Biography"
                     placeholder="Tell us about yourself..."
                     rows="4"
                     help="Optional: Brief description about the user." />
            
            <x-input name="avatar"
                     type="file"
                     label="Profile Avatar"
                     accept="image/*"
                     help="Upload a profile picture (optional)." />
            
            <div class="form-row">
                <div class="col-md-6">
                    <x-input name="notifications"
                             type="checkbox"
                             label="Email Notifications"
                             checkValue="1"
                             help="Receive email notifications for important updates." />
                </div>
                
                <div class="col-md-6">
                    <x-input name="terms"
                             type="checkbox"
                             label="I agree to the Terms of Service"
                             required="true" />
                </div>
            </div>
            
            <x-slot:additionalActions>
                <button type="button" class="btn btn-outline">Save as Draft</button>
            </x-slot>
        </x-form>
        
        <!-- Data table component -->
        <x-data-table 
            :data="$users" 
            :columns="$userColumns"
            :paginated="true"
            :sortable="true"
            :searchable="true"
            class="users-table">
            
            <x-slot:empty>
                <div class="empty-users">
                    <h3>No Users Found</h3>
                    <p>There are no users to display.</p>
                    <a href="/users/create" class="btn btn-primary">Create First User</a>
                </div>
            </x-slot>
        </x-data-table>
        
        <!-- Nested components -->
        <x-card variant="info" class="nested-demo">
            <x-slot:header>
                <h2>Nested Components Demo</h2>
            </x-slot>
            
            <div class="nested-content">
                <p>This card contains other components:</p>
                
                <x-form action="/nested-form" method="POST" :showDefaultFooter="false">
                    <x-input name="nested_input"
                             type="text"
                             label="Nested Input"
                             placeholder="Input inside a card" />
                    
                    <x-slot:footer>
                        <button type="submit" class="btn btn-sm btn-primary">Submit Nested Form</button>
                    </x-slot>
                </x-form>
            </div>
            
            <x-slot:footer>
                <small>This demonstrates component composition and nesting.</small>
            </x-slot>
        </x-card>
    </div>
</body>
</html>
        """.strip()
        
        # Create all component templates
        self.create_template(temp_dir, "components/card.blade.html", card_component)
        self.create_template(temp_dir, "components/modal.blade.html", modal_component)
        self.create_template(temp_dir, "components/form.blade.html", form_component)
        self.create_template(temp_dir, "components/input.blade.html", input_component)
        self.create_template(temp_dir, "components/data-table.blade.html", data_table_component)
        self.create_template(temp_dir, "component-demo.blade.html", component_demo_page)
        
        context = {
            "user": {
                "first_name": "John",
                "last_name": "Doe", 
                "email": "john@example.com"
            },
            "roles": {
                "admin": "Administrator",
                "moderator": "Moderator",
                "user": "Regular User"
            },
            "users": [
                {"id": 1, "name": "John Doe", "email": "john@example.com", "role": "admin"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "role": "user"}
            ],
            "userColumns": {
                "id": "ID",
                "name": "Name", 
                "email": "Email",
                "role": {"label": "Role", "render": lambda row: f"<span class='badge'>{row['role']}</span>"}
            },
            "old": lambda field, default=None: default,
            "errors": {"has": lambda field: False, "all": lambda: []},
            "data_get": lambda obj, key, default: obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
        }
        
        result = engine.render("component-demo.blade.html", context)
        
        # Verify component rendering
        assert "User Profile" in result  # Card header slot
        assert "This is the main card content" in result  # Main slot
        assert "Quick Stats" in result  # Aside slot
        assert "Last active: 2 hours ago" in result  # Footer slot
        assert "Edit Profile" in result  # Actions slot
        
        # Verify modal component
        assert "Confirm Action" in result  # Modal header
        assert "Are you sure you want to delete" in result  # Modal content
        assert "data-dismiss=\"modal\"" in result  # Modal functionality
        
        # Verify form component with inputs
        assert "Create New User" in result  # Form header
        assert "First Name" in result  # Input label
        assert "required" in result  # Required attribute
        assert "placeholder=\"Enter first name\"" in result  # Input placeholder
        assert "form-control" in result  # CSS classes
        
        # Verify input types
        assert "type=\"email\"" in result  # Email input
        assert "type=\"password\"" in result  # Password input
        assert "<textarea" in result  # Textarea input
        assert "<select" in result  # Select input
        assert "type=\"file\"" in result  # File input
        assert "type=\"checkbox\"" in result  # Checkbox input
        
        # Verify data table
        assert "users-table" in result  # Table class
        assert "John Doe" in result  # Table data
        assert "sortable" in result  # Sortable functionality
        
        # Verify nested components
        assert "Nested Components Demo" in result  # Nested card header
        assert "Input inside a card" in result  # Nested input placeholder
        
        # Verify component props and attributes
        assert "card primary large" in result  # Card variant and size
        assert "form bordered" in result  # Form variant
    
    def test_template_composition_and_advanced_patterns(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test advanced template composition patterns and edge cases"""
        engine, temp_dir = blade_engine
        
        # Trait-like template with common functionality
        common_traits = """
{{-- Common traits that can be included in multiple templates --}}

@php
    // Common helper functions (would be in PHP context)
@endphp

@macro('render_user_badge')
    <span class="user-badge {{ $user->status ?? 'active' }} {{ $user->role ?? 'user' }}">
        @if($user->avatar ?? false)
            <img src="{{ $user->avatar }}" alt="{{ $user->name }}" class="badge-avatar">
        @else
            <span class="badge-initials">{{ $user->name | first | upper }}</span>
        @endif
        
        <span class="badge-info">
            <strong>{{ $user->name }}</strong>
            @if($user->title ?? false)
                <small>{{ $user->title }}</small>
            @endif
        </span>
        
        @hasrole('admin')
            <i class="badge-icon admin" title="Administrator"></i>
        @endhasrole
    </span>
@endmacro

@macro('render_status_indicator')
    @switch($status ?? 'unknown')
        @case('active')
            <span class="status-indicator active">
                <i class="icon-check-circle"></i> Active
            </span>
        @break
        
        @case('inactive')
            <span class="status-indicator inactive">
                <i class="icon-pause-circle"></i> Inactive
            </span>
        @break
        
        @case('pending')
            <span class="status-indicator pending">
                <i class="icon-clock"></i> Pending
            </span>
        @break
        
        @case('suspended')
            <span class="status-indicator suspended">
                <i class="icon-x-circle"></i> Suspended
            </span>
        @break
        
        @default
            <span class="status-indicator unknown">
                <i class="icon-help-circle"></i> Unknown
            </span>
    @endswitch
@endmacro

@macro('render_pagination')
    @if($paginator->hasPages())
        <nav class="pagination-nav" aria-label="Pagination Navigation">
            <ul class="pagination">
                {{-- Previous Page Link --}}
                @if($paginator->onFirstPage())
                    <li class="page-item disabled"><span class="page-link">Previous</span></li>
                @else
                    <li class="page-item">
                        <a class="page-link" href="{{ $paginator->previousPageUrl() }}">Previous</a>
                    </li>
                @endif
                
                {{-- Pagination Elements --}}
                @foreach($paginator->getUrlRange(1, $paginator->lastPage()) as $page => $url)
                    @if($page == $paginator->currentPage())
                        <li class="page-item active">
                            <span class="page-link">{{ $page }}</span>
                        </li>
                    @else
                        <li class="page-item">
                            <a class="page-link" href="{{ $url }}">{{ $page }}</a>
                        </li>
                    @endif
                @endforeach
                
                {{-- Next Page Link --}}
                @if($paginator->hasMorePages())
                    <li class="page-item">
                        <a class="page-link" href="{{ $paginator->nextPageUrl() }}">Next</a>
                    </li>
                @else
                    <li class="page-item disabled"><span class="page-link">Next</span></li>
                @endif
            </ul>
        </nav>
    @endif
@endmacro

{{-- Conditional macros based on user permissions --}}
@can('view_admin_tools')
    @macro('render_admin_actions')
        <div class="admin-actions">
            @can('edit_users')
                <button class="btn btn-sm btn-primary edit-user" data-user-id="{{ $user->id ?? '' }}">
                    <i class="icon-edit"></i> Edit
                </button>
            @endcan
            
            @can('delete_users')
                <button class="btn btn-sm btn-danger delete-user" data-user-id="{{ $user->id ?? '' }}">
                    <i class="icon-trash"></i> Delete
                </button>
            @endcan
            
            @can('impersonate_users')
                <a href="{{ route('admin.impersonate', $user->id ?? '#') }}" class="btn btn-sm btn-outline">
                    <i class="icon-user"></i> Login As
                </a>
            @endcan
        </div>
    @endmacro
@endcan
        """.strip()
        
        # Layout with complex conditional sections
        dynamic_layout = """
@include('common-traits')

<!DOCTYPE html>
<html lang="{{ app()->getLocale() }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    
    <title>@yield('title', config('app.name', 'Laravel'))</title>
    
    {{-- Conditional meta tags based on page type --}}
    @hasSection('seo-meta')
        @yield('seo-meta')
    @else
        @switch($pageType ?? 'default')
            @case('blog')
                <meta name="description" content="@yield('meta-description', 'Latest blog posts and articles')">
                <meta property="og:type" content="article">
                @if($post ?? false)
                    <meta property="article:published_time" content="{{ $post->created_at->toISOString() }}">
                    <meta property="article:author" content="{{ $post->author->name }}">
                    @foreach($post->tags as $tag)
                        <meta property="article:tag" content="{{ $tag->name }}">
                    @endforeach
                @endif
            @break
            
            @case('profile')
                <meta name="description" content="User profile for @yield('profile-name', 'User')">
                <meta property="og:type" content="profile">
                @if($profileUser ?? false)
                    <meta property="profile:first_name" content="{{ $profileUser->first_name }}">
                    <meta property="profile:last_name" content="{{ $profileUser->last_name }}">
                @endif
            @break
            
            @default
                <meta name="description" content="@yield('meta-description', config('app.description', 'Web application'))">
                <meta property="og:type" content="website">
        @endswitch
        
        <meta property="og:title" content="@yield('title', config('app.name'))">
        <meta property="og:description" content="@yield('meta-description', config('app.description'))">
        <meta property="og:image" content="@yield('og-image', asset('images/og-default.jpg'))">
        <meta property="og:url" content="{{ request()->url() }}">
    @endhasSection
    
    {{-- Dynamic CSS loading based on features --}}
    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
    
    @if(isset($features) && is_array($features))
        @foreach($features as $feature)
            @if(file_exists(public_path("css/features/{$feature}.css")))
                <link rel="stylesheet" href="{{ asset("css/features/{$feature}.css") }}">
            @endif
        @endforeach
    @endif
    
    @hasSection('custom-css')
        <style>
            @yield('custom-css')
        </style>
    @endhasSection
    
    @stack('head-styles')
</head>
<body class="@yield('body-class') {{ $theme ?? 'default' }}-theme {{ $layout ?? 'standard' }}-layout">
    {{-- Accessibility skip links --}}
    <div class="skip-links">
        <a href="#main-content">Skip to main content</a>
        @hasSection('sidebar')
            <a href="#sidebar">Skip to sidebar</a>
        @endhasSection
        <a href="#footer">Skip to footer</a>
    </div>
    
    {{-- Dynamic header based on user type and permissions --}}
    <header class="site-header" role="banner">
        @switch($userType ?? 'guest')
            @case('admin')
                @include('headers.admin-header')
            @break
            
            @case('member')
                @include('headers.member-header')  
            @break
            
            @case('moderator')
                @include('headers.moderator-header')
            @break
            
            @default
                @include('headers.public-header')
        @endswitch
        
        @hasSection('header-extra')
            <div class="header-extra">
                @yield('header-extra')
            </div>
        @endhasSection
    </header>
    
    {{-- Conditional announcement bar --}}
    @if($announcements ?? false)
        <div class="announcement-bar">
            @foreach($announcements as $announcement)
                @if($announcement->is_active && $announcement->shouldShowToUser(auth()->user()))
                    <div class="announcement {{ $announcement->type }}" data-announcement-id="{{ $announcement->id }}">
                        <div class="announcement-content">
                            {!! $announcement->content !!}
                        </div>
                        @if($announcement->dismissible)
                            <button class="announcement-dismiss" aria-label="Dismiss announcement">
                                <i class="icon-x"></i>
                            </button>
                        @endif
                    </div>
                @endif
            @endforeach
        </div>
    @endif
    
    {{-- Main content area with flexible layout --}}
    <div class="main-wrapper">
        @hasSection('sidebar')
            <aside class="sidebar {{ $sidebarPosition ?? 'left' }}" id="sidebar" role="complementary">
                @yield('sidebar')
            </aside>
        @endhasSection
        
        <main id="main-content" class="main-content" role="main">
            {{-- Breadcrumbs with automatic generation --}}
            @if($showBreadcrumbs ?? true)
                @hasSection('breadcrumbs')
                    @yield('breadcrumbs')
                @else
                    @if(isset($breadcrumbs) && count($breadcrumbs) > 0)
                        <nav class="breadcrumbs" aria-label="Breadcrumb">
                            <ol>
                                @foreach($breadcrumbs as $crumb)
                                    @if($loop->last)
                                        <li class="active" aria-current="page">{{ $crumb['title'] }}</li>
                                    @else
                                        <li><a href="{{ $crumb['url'] }}">{{ $crumb['title'] }}</a></li>
                                    @endif
                                @endforeach
                            </ol>
                        </nav>
                    @endif
                @endhasSection
            @endif
            
            {{-- Flash messages with different types --}}
            @if(session()->has('flash_notification'))
                <div class="flash-messages">
                    @foreach(session('flash_notification') as $message)
                        <div class="alert alert-{{ $message['level'] }} {{ $message['important'] ? 'alert-important' : '' }}"
                             role="alert" 
                             @if(!$message['important']) data-auto-dismiss="5000" @endif>
                            
                            @switch($message['level'])
                                @case('success')
                                    <i class="alert-icon icon-check-circle"></i>
                                @break
                                @case('error')
                                @case('danger')
                                    <i class="alert-icon icon-alert-circle"></i>
                                @break
                                @case('warning')
                                    <i class="alert-icon icon-alert-triangle"></i>
                                @break
                                @case('info')
                                    <i class="alert-icon icon-info"></i>
                                @break
                            @endswitch
                            
                            <div class="alert-content">
                                @if($message['title'] ?? false)
                                    <strong>{{ $message['title'] }}</strong>
                                @endif
                                <p>{!! $message['message'] !!}</p>
                            </div>
                            
                            <button type="button" class="alert-close" data-dismiss="alert" aria-label="Close">
                                <i class="icon-x"></i>
                            </button>
                        </div>
                    @endforeach
                </div>
            @endif
            
            {{-- Page title with actions --}}
            @hasSection('page-header')
                <div class="page-header">
                    @yield('page-header')
                </div>
            @else
                @if($pageTitle ?? false)
                    <div class="page-header">
                        <div class="page-title-wrapper">
                            <h1 class="page-title">{{ $pageTitle }}</h1>
                            @if($pageSubtitle ?? false)
                                <p class="page-subtitle">{{ $pageSubtitle }}</p>
                            @endif
                        </div>
                        
                        @hasSection('page-actions')
                            <div class="page-actions">
                                @yield('page-actions')
                            </div>
                        @endhasSection
                    </div>
                @endif
            @endhasSection
            
            {{-- Main content --}}
            @yield('content')
        </main>
    </div>
    
    {{-- Footer with dynamic content --}}
    <footer class="site-footer" id="footer" role="contentinfo">
        @hasSection('footer')
            @yield('footer')
        @else
            <div class="footer-content">
                <div class="footer-section">
                    <h3>{{ config('app.name') }}</h3>
                    <p>{{ config('app.description', 'Web application powered by Laravel') }}</p>
                </div>
                
                @if($footerLinks ?? false)
                    <div class="footer-section">
                        <h4>Quick Links</h4>
                        <ul>
                            @foreach($footerLinks as $link)
                                <li><a href="{{ $link['url'] }}">{{ $link['title'] }}</a></li>
                            @endforeach
                        </ul>
                    </div>
                @endif
                
                <div class="footer-section">
                    <p>&copy; {{ date('Y') }} {{ config('app.name') }}. All rights reserved.</p>
                </div>
            </div>
        @endhasSection
    </footer>
    
    {{-- Dynamic JavaScript loading --}}
    <script src="{{ asset('js/app.js') }}"></script>
    
    @if(isset($features) && is_array($features))
        @foreach($features as $feature)
            @if(file_exists(public_path("js/features/{$feature}.js")))
                <script src="{{ asset("js/features/{$feature}.js") }}"></script>
            @endif
        @endforeach
    @endif
    
    @stack('scripts')
    
    @hasSection('inline-scripts')
        <script>
            @yield('inline-scripts')
        </script>
    @endhasSection
</body>
</html>
        """.strip()
        
        # Complex page using the dynamic layout
        complex_page = """
@extends('dynamic-layout', ['pageType' => 'profile', 'userType' => 'admin'])

@section('title', 'Advanced User Profile - ' . ($user->name ?? 'User'))

@section('seo-meta')
    <meta name="description" content="Profile page for {{ $user->name ?? 'User' }}, {{ $user->title ?? 'Member' }}">
    <meta property="og:type" content="profile">
    <meta property="profile:first_name" content="{{ $user->first_name ?? '' }}">
    <meta property="profile:last_name" content="{{ $user->last_name ?? '' }}">
    <meta property="og:image" content="{{ $user->avatar ?? asset('images/default-avatar.jpg') }}">
@endsection

@php
    $features = ['user-profile', 'activity-feed', 'messaging'];
    $theme = 'admin';
    $layout = 'sidebar';
    $sidebarPosition = 'right';
@endphp

@section('breadcrumbs')
    <nav class="breadcrumbs" aria-label="Breadcrumb">
        <ol>
            <li><a href="{{ route('admin.dashboard') }}">Dashboard</a></li>
            <li><a href="{{ route('admin.users.index') }}">Users</a></li>
            <li class="active" aria-current="page">{{ $user->name ?? 'User Profile' }}</li>
        </ol>
    </nav>
@endsection

@section('page-header')
    <div class="profile-header">
        <div class="profile-basic-info">
            @include('render_user_badge', ['user' => $user])
            
            <div class="profile-details">
                <h1>{{ $user->name ?? 'Unknown User' }}</h1>
                @if($user->title ?? false)
                    <p class="user-title">{{ $user->title }}</p>
                @endif
                
                <div class="profile-meta">
                    @include('render_status_indicator', ['status' => $user->status ?? 'active'])
                    
                    <span class="join-date">
                        Member since {{ $user->created_at->format('F Y') ?? 'Unknown' }}
                    </span>
                    
                    @if($user->last_login_at ?? false)
                        <span class="last-seen">
                            Last seen {{ $user->last_login_at->diffForHumans() }}
                        </span>
                    @endif
                </div>
            </div>
        </div>
        
        <div class="profile-stats">
            <div class="stat-item">
                <span class="stat-number">{{ $user->posts_count ?? 0 }}</span>
                <span class="stat-label">Posts</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">{{ $user->comments_count ?? 0 }}</span>
                <span class="stat-label">Comments</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">{{ $user->followers_count ?? 0 }}</span>
                <span class="stat-label">Followers</span>
            </div>
        </div>
    </div>
@endsection

@section('page-actions')
    <div class="profile-actions">
        @can('edit_users')
            <a href="{{ route('admin.users.edit', $user->id ?? '#') }}" class="btn btn-primary">
                <i class="icon-edit"></i> Edit Profile
            </a>
        @endcan
        
        @can('message_users')
            <button class="btn btn-secondary" data-toggle="modal" data-target="#message-modal">
                <i class="icon-mail"></i> Send Message
            </button>
        @endcan
        
        @include('render_admin_actions', ['user' => $user])
    </div>
@endsection

@section('content')
    <div class="profile-content">
        {{-- Profile sections with conditional content --}}
        @if($user->bio ?? false)
            <section class="profile-section bio-section">
                <h2>About</h2>
                <div class="bio-content">
                    {!! nl2br(e($user->bio)) !!}
                </div>
            </section>
        @endif
        
        {{-- Dynamic sections based on user permissions and data --}}
        @if($user->permissions->isNotEmpty())
            <section class="profile-section permissions-section">
                <h2>Permissions & Roles</h2>
                
                <div class="roles-list">
                    <h3>Roles</h3>
                    @forelse($user->roles as $role)
                        <span class="role-badge {{ $role->name }}">
                            <i class="role-icon icon-{{ $role->icon ?? 'user' }}"></i>
                            {{ $role->display_name }}
                        </span>
                    @empty
                        <p>No roles assigned</p>
                    @endforelse
                </div>
                
                <div class="permissions-list">
                    <h3>Direct Permissions</h3>
                    @forelse($user->permissions as $permission)
                        <div class="permission-item">
                            <strong>{{ $permission->display_name }}</strong>
                            @if($permission->description)
                                <p>{{ $permission->description }}</p>
                            @endif
                        </div>
                    @empty
                        <p>No direct permissions assigned</p>
                    @endforelse
                </div>
            </section>
        @endif
        
        {{-- Activity timeline --}}
        @if($activities ?? false)
            <section class="profile-section activity-section">
                <h2>Recent Activity</h2>
                
                <div class="activity-timeline">
                    @foreach($activities->take(10) as $activity)
                        <div class="activity-item {{ $activity->type }}">
                            <div class="activity-icon">
                                <i class="icon-{{ $activity->icon ?? 'activity' }}"></i>
                            </div>
                            
                            <div class="activity-content">
                                <div class="activity-header">
                                    <strong>{{ $activity->title }}</strong>
                                    <time datetime="{{ $activity->created_at->toISOString() }}">
                                        {{ $activity->created_at->diffForHumans() }}
                                    </time>
                                </div>
                                
                                @if($activity->description)
                                    <p class="activity-description">{{ $activity->description }}</p>
                                @endif
                                
                                @if($activity->metadata ?? false)
                                    <div class="activity-metadata">
                                        @foreach($activity->metadata as $key => $value)
                                            <span class="metadata-item">
                                                <strong>{{ ucfirst($key) }}:</strong> {{ $value }}
                                            </span>
                                        @endforeach
                                    </div>
                                @endif
                            </div>
                        </div>
                    @endforeach
                    
                    @if($activities->count() > 10)
                        <div class="activity-load-more">
                            <button class="btn btn-outline load-more-activities" 
                                    data-user-id="{{ $user->id }}" 
                                    data-offset="10">
                                Load More Activities
                            </button>
                        </div>
                    @endif
                </div>
            </section>
        @endif
        
        {{-- User content (posts, comments, etc.) --}}
        @if($userContent ?? false)
            <section class="profile-section content-section">
                <div class="content-tabs">
                    <nav class="tab-nav">
                        <button class="tab-button active" data-tab="posts">
                            Posts ({{ $userContent['posts']->count() }})
                        </button>
                        <button class="tab-button" data-tab="comments">
                            Comments ({{ $userContent['comments']->count() }})
                        </button>
                        @if($userContent['media'] ?? false)
                            <button class="tab-button" data-tab="media">
                                Media ({{ $userContent['media']->count() }})
                            </button>
                        @endif
                    </nav>
                    
                    <div class="tab-content">
                        {{-- Posts tab --}}
                        <div class="tab-pane active" id="posts-tab">
                            @forelse($userContent['posts'] as $post)
                                <article class="content-item post-item">
                                    <header class="content-header">
                                        <h3><a href="{{ route('posts.show', $post->id) }}">{{ $post->title }}</a></h3>
                                        <div class="content-meta">
                                            <time datetime="{{ $post->published_at->toISOString() }}">
                                                {{ $post->published_at->format('M j, Y') }}
                                            </time>
                                            <span class="content-stats">
                                                {{ $post->views_count }} views, 
                                                {{ $post->comments_count }} comments
                                            </span>
                                        </div>
                                    </header>
                                    
                                    <div class="content-excerpt">
                                        {{ Str::limit($post->excerpt, 200) }}
                                    </div>
                                    
                                    @if($post->tags->isNotEmpty())
                                        <div class="content-tags">
                                            @foreach($post->tags as $tag)
                                                <span class="tag">{{ $tag->name }}</span>
                                            @endforeach
                                        </div>
                                    @endif
                                </article>
                            @empty
                                <div class="empty-content">
                                    <p>No posts yet</p>
                                </div>
                            @endforelse
                            
                            @if($userContent['posts']->hasMorePages())
                                @include('render_pagination', ['paginator' => $userContent['posts']])
                            @endif
                        </div>
                        
                        {{-- Comments tab --}}
                        <div class="tab-pane" id="comments-tab">
                            @forelse($userContent['comments'] as $comment)
                                <div class="content-item comment-item">
                                    <div class="comment-context">
                                        On <a href="{{ route('posts.show', $comment->post->id) }}#comment-{{ $comment->id }}">
                                            {{ $comment->post->title }}
                                        </a>
                                    </div>
                                    
                                    <div class="comment-content">
                                        {{ Str::limit($comment->content, 300) }}
                                    </div>
                                    
                                    <div class="comment-meta">
                                        <time datetime="{{ $comment->created_at->toISOString() }}">
                                            {{ $comment->created_at->diffForHumans() }}
                                        </time>
                                        @if($comment->likes_count > 0)
                                            <span class="comment-likes">{{ $comment->likes_count }} likes</span>
                                        @endif
                                    </div>
                                </div>
                            @empty
                                <div class="empty-content">
                                    <p>No comments yet</p>
                                </div>
                            @endforelse
                        </div>
                        
                        {{-- Media tab --}}
                        @if($userContent['media'] ?? false)
                            <div class="tab-pane" id="media-tab">
                                <div class="media-grid">
                                    @foreach($userContent['media'] as $media)
                                        <div class="media-item">
                                            @if($media->type === 'image')
                                                <img src="{{ $media->thumbnail_url }}" alt="{{ $media->alt_text }}">
                                            @elseif($media->type === 'video')
                                                <video poster="{{ $media->thumbnail_url }}">
                                                    <source src="{{ $media->url }}" type="{{ $media->mime_type }}">
                                                </video>
                                            @else
                                                <div class="file-preview">
                                                    <i class="file-icon icon-file-{{ $media->extension }}"></i>
                                                    <span class="file-name">{{ $media->filename }}</span>
                                                </div>
                                            @endif
                                            
                                            <div class="media-overlay">
                                                <a href="{{ $media->url }}" class="media-view">View</a>
                                            </div>
                                        </div>
                                    @endforeach
                                </div>
                            </div>
                        @endif
                    </div>
                </div>
            </section>
        @endif
    </div>
@endsection

@section('sidebar')
    <div class="profile-sidebar">
        {{-- Contact information --}}
        @if($user->contact_info ?? false)
            <div class="sidebar-section contact-section">
                <h3>Contact Information</h3>
                <ul class="contact-list">
                    @if($user->email ?? false)
                        <li class="contact-item email">
                            <i class="contact-icon icon-mail"></i>
                            <a href="mailto:{{ $user->email }}">{{ $user->email }}</a>
                        </li>
                    @endif
                    
                    @if($user->phone ?? false)
                        <li class="contact-item phone">
                            <i class="contact-icon icon-phone"></i>
                            <a href="tel:{{ $user->phone }}">{{ $user->phone }}</a>
                        </li>
                    @endif
                    
                    @if($user->website ?? false)
                        <li class="contact-item website">
                            <i class="contact-icon icon-globe"></i>
                            <a href="{{ $user->website }}" target="_blank">{{ $user->website }}</a>
                        </li>
                    @endif
                    
                    @if($user->location ?? false)
                        <li class="contact-item location">
                            <i class="contact-icon icon-map-pin"></i>
                            <span>{{ $user->location }}</span>
                        </li>
                    @endif
                </ul>
            </div>
        @endif
        
        {{-- Social links --}}
        @if($user->social_links ?? false)
            <div class="sidebar-section social-section">
                <h3>Social Media</h3>
                <div class="social-links">
                    @foreach($user->social_links as $platform => $url)
                        @if($url)
                            <a href="{{ $url }}" class="social-link {{ $platform }}" target="_blank" 
                               title="{{ ucfirst($platform) }}">
                                <i class="social-icon icon-{{ $platform }}"></i>
                            </a>
                        @endif
                    @endforeach
                </div>
            </div>
        @endif
        
        {{-- Quick actions --}}
        <div class="sidebar-section actions-section">
            <h3>Quick Actions</h3>
            <div class="quick-actions">
                @can('message_users')
                    <button class="quick-action message-action" data-user-id="{{ $user->id }}">
                        <i class="action-icon icon-mail"></i>
                        Send Message
                    </button>
                @endcan
                
                @can('follow_users')
                    @if($user->isFollowedBy(auth()->user()))
                        <button class="quick-action unfollow-action" data-user-id="{{ $user->id }}">
                            <i class="action-icon icon-user-minus"></i>
                            Unfollow
                        </button>
                    @else
                        <button class="quick-action follow-action" data-user-id="{{ $user->id }}">
                            <i class="action-icon icon-user-plus"></i>
                            Follow
                        </button>
                    @endif
                @endcan
                
                @can('block_users')
                    <button class="quick-action block-action danger" data-user-id="{{ $user->id }}">
                        <i class="action-icon icon-user-x"></i>
                        Block User
                    </button>
                @endcan
            </div>
        </div>
        
        {{-- Related users --}}
        @if($relatedUsers ?? false)
            <div class="sidebar-section related-section">
                <h3>Similar Users</h3>
                <div class="related-users">
                    @foreach($relatedUsers->take(5) as $relatedUser)
                        <div class="related-user-item">
                            @include('render_user_badge', ['user' => $relatedUser])
                        </div>
                    @endforeach
                </div>
            </div>
        @endif
    </div>
@endsection

@push('head-styles')
    <link rel="stylesheet" href="{{ asset('css/profile.css') }}">
@endpush

@section('custom-css')
    .profile-header {
        background: linear-gradient(135deg, {{ $user->theme_color ?? '#6366f1' }} 0%, {{ $user->secondary_color ?? '#8b5cf6' }} 100%);
    }
    
    .user-badge.{{ $user->role ?? 'user' }} {
        border-color: {{ $user->theme_color ?? '#6366f1' }};
    }
@endsection

@push('scripts')
    <script src="{{ asset('js/profile.js') }}"></script>
@endpush

@section('inline-scripts')
    window.profileConfig = {
        userId: {{ $user->id ?? 0 }},
        canMessage: @can('message_users') true @else false @endcan,
        canFollow: @can('follow_users') true @else false @endcan,
        isFollowing: {{ $user->isFollowedBy(auth()->user()) ? 'true' : 'false' }},
        routes: {
            message: '{{ route("messages.create", ":userId") }}',
            follow: '{{ route("users.follow", ":userId") }}',
            unfollow: '{{ route("users.unfollow", ":userId") }}',
            block: '{{ route("users.block", ":userId") }}'
        }
    };
@endsection
        """.strip()
        
        # Create header partials
        admin_header = """
<div class="admin-header-content">
    <h1>Admin Panel</h1>
    <nav class="admin-nav">
        <a href="/admin/dashboard">Dashboard</a>
        <a href="/admin/users">Users</a>
        <a href="/admin/settings">Settings</a>
    </nav>
</div>
        """.strip()
        
        # Create all templates
        self.create_template(temp_dir, "common-traits.blade.html", common_traits)
        self.create_template(temp_dir, "dynamic-layout.blade.html", dynamic_layout)
        self.create_template(temp_dir, "complex-profile.blade.html", complex_page)
        self.create_template(temp_dir, "headers/admin-header.blade.html", admin_header)
        
        context = {
            "user": {
                "id": 1,
                "name": "John Administrator",
                "first_name": "John",
                "last_name": "Administrator", 
                "title": "System Administrator",
                "email": "john@example.com",
                "bio": "Experienced system administrator with over 10 years in the field.",
                "avatar": "/avatars/john.jpg",
                "status": "active",
                "theme_color": "#6366f1",
                "secondary_color": "#8b5cf6",
                "role": "admin",
                "posts_count": 45,
                "comments_count": 128,
                "followers_count": 234,
                "created_at": {"format": lambda fmt: "January 2020"},
                "last_login_at": {"diffForHumans": lambda: "2 hours ago"},
                "roles": [
                    {"name": "super-admin", "display_name": "Super Administrator", "icon": "shield"}
                ],
                "permissions": [
                    {"display_name": "Manage Users", "description": "Can create, edit, and delete users"},
                    {"display_name": "System Settings", "description": "Can modify system configuration"}
                ],
                "contact_info": {
                    "phone": "+1-555-123-4567",
                    "website": "https://johndoe.dev",
                    "location": "New York, NY"
                },
                "social_links": {
                    "twitter": "https://twitter.com/johnadmin",
                    "linkedin": "https://linkedin.com/in/johnadmin",
                    "github": "https://github.com/johnadmin"
                },
                "isFollowedBy": lambda u: False
            },
            "activities": [
                {
                    "type": "login",
                    "title": "User Login",
                    "description": "Logged into admin panel",
                    "icon": "log-in",
                    "created_at": {"toISOString": lambda: "2024-01-15T10:30:00Z", "diffForHumans": lambda: "2 hours ago"},
                    "metadata": {"ip": "192.168.1.100", "browser": "Chrome"}
                }
            ],
            "userContent": {
                "posts": [
                    {
                        "id": 1,
                        "title": "System Maintenance Guide",
                        "excerpt": "A comprehensive guide to maintaining system performance...",
                        "published_at": {"toISOString": lambda: "2024-01-10T00:00:00Z", "format": lambda fmt: "Jan 10, 2024"},
                        "views_count": 1250,
                        "comments_count": 23,
                        "tags": [{"name": "maintenance"}, {"name": "system"}]
                    }
                ],
                "comments": [
                    {
                        "id": 1,
                        "content": "Great point about system optimization...",
                        "post": {"id": 2, "title": "Performance Tuning"},
                        "created_at": {"toISOString": lambda: "2024-01-12T00:00:00Z", "diffForHumans": lambda: "3 days ago"},
                        "likes_count": 5
                    }
                ]
            },
            "relatedUsers": [
                {"name": "Jane Admin", "avatar": "/avatars/jane.jpg", "role": "admin", "status": "active"}
            ],
            "route": lambda name, *args: f"/{name.replace('.', '/')}" + (f"/{args[0]}" if args else ""),
            "asset": lambda path: f"/assets/{path.lstrip('/')}",
            "config": lambda key, default=None: {"app.name": "Advanced App"}.get(key, default),
            "auth": lambda: type('User', (), {"user": lambda: context["user"]}),
            "request": lambda: type('Request', (), {"url": lambda: "https://example.com/profile/1"}),
            "csrf_token": lambda: "csrf_token_123",
            "session": lambda: type('Session', (), {"has": lambda key: key == "flash_notification"}),
            "file_exists": lambda path: True,
            "public_path": lambda path: f"/public/{path}",
            "nl2br": lambda text: text.replace('\n', '<br>'),
            "e": lambda text: text,  # HTML escape function
            "Str": type('Str', (), {"limit": lambda text, length: text[:length] + "..." if len(text) > length else text})
        }
        
        result = engine.render("complex-profile.blade.html", context)
        
        # Verify complex inheritance and composition
        assert "John Administrator" in result  # User name
        assert "System Administrator" in result  # User title
        assert "Admin Panel" in result  # Header from admin layout
        assert "Profile page for John Administrator" in result  # SEO meta
        
        # Verify macro usage
        assert "user-badge" in result  # User badge macro
        assert "status-indicator active" in result  # Status indicator macro
        
        # Verify conditional sections
        assert "Experienced system administrator" in result  # Bio section
        assert "Permissions & Roles" in result  # Permissions section
        assert "Recent Activity" in result  # Activity section
        
        # Verify tab content
        assert "System Maintenance Guide" in result  # Post content
        assert "Great point about system optimization" in result  # Comment content
        
        # Verify sidebar content
        assert "john@example.com" in result  # Contact info
        assert "https://twitter.com/johnadmin" in result  # Social links
        assert "Jane Admin" in result  # Related users
        
        # Verify dynamic CSS and JavaScript
        assert "#6366f1" in result  # Theme color
        assert "profile.js" in result  # JavaScript file
        assert "profileConfig" in result  # Inline script configuration
        
        # Verify permission-based content
        assert "Edit Profile" in result  # Admin can edit
        assert "Send Message" in result  # Can message users
        
        # Verify complex conditional logic
        assert "Super Administrator" in result  # Role badge
        assert "Manage Users" in result  # Permission display


if __name__ == "__main__":
    pytest.main([__file__, "-v"])