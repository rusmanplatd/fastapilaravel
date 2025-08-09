"""
Nested Template Inheritance Test Suite for Blade Engine
Tests complex nested template inheritance scenarios
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple

from app.View.BladeEngine import BladeEngine


class TestBladeNestedInheritance:
    """Test complex nested template inheritance"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        """Create BladeEngine instance with temp directory"""
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
    
    def test_multi_level_template_inheritance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test multi-level template inheritance with nested sections"""
        engine, temp_dir = blade_engine
        
        # Base layout (Level 1)
        base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'My App')</title>
    <meta charset="utf-8">
    @stack('meta')
    
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
        @stack('styles')
    </style>
</head>
<body class="@yield('body-class')">
    @yield('header')
    
    <main class="content">
        @yield('content')
    </main>
    
    @yield('footer')
    
    <script>
        @stack('scripts')
    </script>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", base_layout)
        
        # App layout extending base (Level 2)
        app_layout = """
@extends('layouts/base')

@section('header')
    <header class="app-header">
        <div class="container">
            <h1 class="logo">@yield('app-name', 'My Application')</h1>
            
            <nav class="main-nav">
                @yield('navigation')
            </nav>
            
            <div class="user-section">
                @yield('user-info')
            </div>
        </div>
        
        @hasSection('breadcrumbs')
            <div class="breadcrumbs">
                @yield('breadcrumbs')
            </div>
        @endif
    </header>
@endsection

@section('footer')
    <footer class="app-footer">
        <div class="container">
            @yield('footer-content')
            
            <div class="footer-links">
                @yield('footer-links')
            </div>
            
            <div class="copyright">
                @yield('copyright', '&copy; 2025 My Application')
            </div>
        </div>
    </footer>
@endsection

@push('styles')
    .app-header { background: #2c3e50; color: white; padding: 1rem 0; }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }
    .main-nav { display: flex; gap: 2rem; }
    .app-footer { background: #34495e; color: white; padding: 2rem 0; margin-top: 2rem; }
@endpush
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", app_layout)
        
        # Admin layout extending app (Level 3)
        admin_layout = """
@extends('layouts/app')

@section('body-class', 'admin-interface')

@section('app-name', 'Admin Dashboard')

@section('navigation')
    <div class="admin-nav">
        <a href="/admin" class="nav-item @if(current_page == 'dashboard') active @endif">Dashboard</a>
        
        @can('manage-users')
            <div class="nav-dropdown">
                <span class="nav-item">Users</span>
                <div class="dropdown-menu">
                    <a href="/admin/users">All Users</a>
                    @can('create-users')
                        <a href="/admin/users/create">Create User</a>
                    @endcan
                    <a href="/admin/roles">Roles & Permissions</a>
                </div>
            </div>
        @endcan
        
        @can('view-reports')
            <div class="nav-dropdown">
                <span class="nav-item">Reports</span>
                <div class="dropdown-menu">
                    @foreach(report_types as report)
                        <a href="/admin/reports/{{ report.slug }}">{{ report.name }}</a>
                    @endforeach
                </div>
            </div>
        @endcan
    </div>
@endsection

@section('user-info')
    <div class="admin-user-info">
        @if(current_user)
            <div class="user-dropdown">
                <span class="user-name">{{ current_user.name }}</span>
                <div class="dropdown-menu">
                    <a href="/admin/profile">Profile Settings</a>
                    @hasrole('super-admin')
                        <a href="/admin/system">System Settings</a>
                    @endhasrole
                    <a href="/logout">Logout</a>
                </div>
            </div>
        @endif
    </div>
@endsection

@push('styles')
    .admin-interface { background: #ecf0f1; }
    .admin-nav { display: flex; align-items: center; gap: 2rem; }
    .nav-item { color: white; text-decoration: none; padding: 0.5rem 1rem; }
    .nav-item.active { background: rgba(255,255,255,0.2); border-radius: 4px; }
    .nav-dropdown { position: relative; }
    .dropdown-menu { 
        position: absolute; background: white; color: black; 
        min-width: 200px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        display: none; 
    }
    .nav-dropdown:hover .dropdown-menu { display: block; }
    .admin-user-info .user-name { font-weight: bold; }
@endpush

@push('scripts')
    // Admin interface JavaScript
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Admin interface loaded');
    });
@endpush
        """.strip()
        self.create_template(temp_dir, "layouts/admin.blade.html", admin_layout)
        
        # User management page extending admin (Level 4)
        user_management_page = """
@extends('layouts/admin')

@section('title', 'User Management - Admin Dashboard')

@push('meta')
    <meta name="description" content="Manage system users and permissions">
@endpush

@section('breadcrumbs')
    <ol class="breadcrumb">
        <li><a href="/admin">Dashboard</a></li>
        <li><a href="/admin/users">Users</a></li>
        <li class="active">Management</li>
    </ol>
@endsection

@section('content')
    <div class="user-management-page">
        <div class="page-header">
            <div class="header-content">
                <h2>User Management</h2>
                <p class="page-description">Manage system users, roles, and permissions</p>
            </div>
            
            @can('create-users')
                <div class="header-actions">
                    <a href="/admin/users/create" class="btn btn-primary">
                        <i class="icon-plus"></i> Create User
                    </a>
                    
                    @can('bulk-import')
                        <a href="/admin/users/import" class="btn btn-secondary">
                            <i class="icon-upload"></i> Import Users
                        </a>
                    @endcan
                </div>
            @endcan
        </div>
        
        <div class="filters-section">
            <div class="filter-row">
                @foreach(user_filters as filter)
                    <div class="filter-group">
                        <label>{{ filter.label }}</label>
                        
                        @if(filter.type == 'select')
                            <select name="{{ filter.name }}" class="form-control">
                                @foreach(filter.options as option)
                                    <option value="{{ option.value }}" 
                                            @if(option.selected) selected @endif>
                                        {{ option.label }}
                                    </option>
                                @endforeach
                            </select>
                        @elseif(filter.type == 'text')
                            <input type="text" name="{{ filter.name }}" 
                                   value="{{ filter.value }}" 
                                   placeholder="{{ filter.placeholder }}"
                                   class="form-control">
                        @endif
                    </div>
                @endforeach
                
                <div class="filter-actions">
                    <button type="button" class="btn btn-outline" onclick="applyFilters()">
                        Apply Filters
                    </button>
                    <button type="button" class="btn btn-link" onclick="clearFilters()">
                        Clear
                    </button>
                </div>
            </div>
        </div>
        
        <div class="users-table-section">
            @if(users)
                <div class="table-header">
                    <div class="table-info">
                        <span class="results-count">Showing {{ users | length }} of {{ total_users }} users</span>
                    </div>
                    
                    @can('bulk-actions')
                        <div class="bulk-actions">
                            <select class="bulk-action-select">
                                <option value="">Bulk Actions</option>
                                <option value="activate">Activate Selected</option>
                                <option value="deactivate">Deactivate Selected</option>
                                <option value="delete">Delete Selected</option>
                            </select>
                            <button type="button" class="btn btn-outline" onclick="performBulkAction()">
                                Apply
                            </button>
                        </div>
                    @endcan
                </div>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            @can('bulk-actions')
                                <th class="select-column">
                                    <input type="checkbox" id="select-all">
                                </th>
                            @endcan
                            <th>User</th>
                            <th>Email</th>
                            <th>Roles</th>
                            <th>Status</th>
                            <th>Last Login</th>
                            <th class="actions-column">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach(users as user)
                            <tr class="user-row @if(not user.active) inactive @endif">
                                @can('bulk-actions')
                                    <td class="select-column">
                                        @unless(user.is_protected)
                                            <input type="checkbox" name="user_ids[]" value="{{ user.id }}">
                                        @endunless
                                    </td>
                                @endcan
                                
                                <td class="user-cell">
                                    <div class="user-info">
                                        @if(user.avatar)
                                            <img src="{{ user.avatar }}" alt="{{ user.name }}" class="user-avatar">
                                        @else
                                            <div class="avatar-placeholder">
                                                {{ user.name | slice(0, 1) | upper }}
                                            </div>
                                        @endif
                                        
                                        <div class="user-details">
                                            <div class="user-name">
                                                {{ user.name }}
                                                @if(user.is_verified)
                                                    <i class="icon-verified" title="Verified Account"></i>
                                                @endif
                                            </div>
                                            <div class="user-meta">
                                                ID: {{ user.id }}
                                                @if(user.is_online)
                                                    <span class="online-indicator">Online</span>
                                                @endif
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                
                                <td class="email-cell">{{ user.email }}</td>
                                
                                <td class="roles-cell">
                                    @if(user.roles)
                                        <div class="role-badges">
                                            @foreach(user.roles as role)
                                                <span class="role-badge role-{{ role.slug }}">
                                                    {{ role.name }}
                                                </span>
                                            @endforeach
                                        </div>
                                    @else
                                        <span class="no-roles">No roles assigned</span>
                                    @endif
                                </td>
                                
                                <td class="status-cell">
                                    @if(user.active)
                                        <span class="status-badge status-active">Active</span>
                                    @else
                                        <span class="status-badge status-inactive">Inactive</span>
                                    @endif
                                    
                                    @if(user.suspended)
                                        <span class="status-badge status-suspended">Suspended</span>
                                    @endif
                                </td>
                                
                                <td class="last-login-cell">
                                    @if(user.last_login)
                                        <div class="login-info">
                                            <div class="login-date">{{ user.last_login.date }}</div>
                                            <div class="login-time">{{ user.last_login.time }}</div>
                                        </div>
                                    @else
                                        <span class="never-logged-in">Never</span>
                                    @endif
                                </td>
                                
                                <td class="actions-cell">
                                    <div class="action-buttons">
                                        @can('view-users')
                                            <a href="/admin/users/{{ user.id }}" 
                                               class="btn btn-sm btn-outline" 
                                               title="View User">
                                                <i class="icon-eye"></i>
                                            </a>
                                        @endcan
                                        
                                        @can('edit-users')
                                            @unless(user.is_protected and not current_user.is_super_admin)
                                                <a href="/admin/users/{{ user.id }}/edit" 
                                                   class="btn btn-sm btn-primary" 
                                                   title="Edit User">
                                                    <i class="icon-edit"></i>
                                                </a>
                                            @endunless
                                        @endcan
                                        
                                        @can('impersonate-users')
                                            @unless(user.is_protected or user.id == current_user.id)
                                                <button class="btn btn-sm btn-warning" 
                                                        onclick="impersonateUser({{ user.id }})"
                                                        title="Impersonate User">
                                                    <i class="icon-user-switch"></i>
                                                </button>
                                            @endunless
                                        @endcan
                                        
                                        @can('delete-users')
                                            @unless(user.is_protected or user.id == current_user.id)
                                                <button class="btn btn-sm btn-danger" 
                                                        onclick="deleteUser({{ user.id }}, '{{ user.name }}')"
                                                        title="Delete User">
                                                    <i class="icon-trash"></i>
                                                </button>
                                            @endunless
                                        @endcan
                                    </div>
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
                
                @if(pagination)
                    <div class="pagination-wrapper">
                        <div class="pagination-info">
                            Page {{ pagination.current }} of {{ pagination.total_pages }}
                        </div>
                        
                        <nav class="pagination">
                            @if(pagination.has_prev)
                                <a href="{{ pagination.prev_url }}" class="page-link">Previous</a>
                            @endif
                            
                            @foreach(pagination.pages as page)
                                @if(page.type == 'page')
                                    <a href="{{ page.url }}" 
                                       class="page-link @if(page.current) active @endif">
                                        {{ page.number }}
                                    </a>
                                @elseif(page.type == 'dots')
                                    <span class="page-dots">...</span>
                                @endif
                            @endforeach
                            
                            @if(pagination.has_next)
                                <a href="{{ pagination.next_url }}" class="page-link">Next</a>
                            @endif
                        </nav>
                    </div>
                @endif
            @else
                <div class="empty-state">
                    <div class="empty-icon">
                        <i class="icon-users"></i>
                    </div>
                    <h3>No Users Found</h3>
                    <p>No users match your current filter criteria.</p>
                    
                    @can('create-users')
                        <div class="empty-actions">
                            <a href="/admin/users/create" class="btn btn-primary">
                                Create First User
                            </a>
                        </div>
                    @endcan
                </div>
            @endif
        </div>
    </div>
@endsection

@section('footer-content')
    <div class="admin-footer">
        <p>Admin Dashboard - User Management System</p>
    </div>
@endsection

@section('footer-links')
    <div class="admin-links">
        <a href="/admin/help">Help</a>
        <a href="/admin/docs">Documentation</a>
        <a href="/admin/support">Support</a>
    </div>
@endsection

@push('styles')
    .user-management-page { padding: 2rem; }
    .page-header { 
        display: flex; justify-content: space-between; align-items: flex-start; 
        margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #ddd;
    }
    .filters-section { background: white; padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px; }
    .filter-row { display: flex; align-items: end; gap: 1rem; }
    .filter-group { display: flex; flex-direction: column; gap: 0.5rem; }
    .data-table { width: 100%; border-collapse: collapse; background: white; }
    .data-table th, .data-table td { padding: 1rem; border-bottom: 1px solid #eee; text-align: left; }
    .user-row.inactive { opacity: 0.6; }
    .user-info { display: flex; align-items: center; gap: 1rem; }
    .user-avatar { width: 40px; height: 40px; border-radius: 50%; }
    .avatar-placeholder { 
        width: 40px; height: 40px; border-radius: 50%; 
        background: #007bff; color: white; display: flex; 
        align-items: center; justify-content: center; font-weight: bold;
    }
    .role-badge { 
        padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem; 
        margin-right: 0.25rem; color: white;
    }
    .role-badge.role-admin { background: #dc3545; }
    .role-badge.role-editor { background: #28a745; }
    .role-badge.role-user { background: #6c757d; }
    .status-badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem; }
    .status-active { background: #d4edda; color: #155724; }
    .status-inactive { background: #f8d7da; color: #721c24; }
    .status-suspended { background: #fff3cd; color: #856404; }
    .action-buttons { display: flex; gap: 0.5rem; }
    .empty-state { text-align: center; padding: 4rem 2rem; background: white; border-radius: 8px; }
    .pagination-wrapper { display: flex; justify-content: space-between; align-items: center; margin-top: 2rem; }
    .pagination { display: flex; gap: 0.5rem; }
    .page-link { padding: 0.5rem 1rem; border: 1px solid #ddd; text-decoration: none; }
    .page-link.active { background: #007bff; color: white; }
@endpush

@push('scripts')
    function applyFilters() {
        // Collect filter values and update URL
        console.log('Applying filters...');
    }
    
    function clearFilters() {
        // Clear all filter inputs
        console.log('Clearing filters...');
    }
    
    function performBulkAction() {
        const action = document.querySelector('.bulk-action-select').value;
        const selected = document.querySelectorAll('input[name="user_ids[]"]:checked');
        
        if (!action || selected.length === 0) {
            alert('Please select an action and at least one user.');
            return;
        }
        
        console.log(`Performing ${action} on ${selected.length} users`);
    }
    
    function impersonateUser(userId) {
        if (confirm('Are you sure you want to impersonate this user?')) {
            console.log(`Impersonating user ${userId}`);
        }
    }
    
    function deleteUser(userId, userName) {
        if (confirm(`Are you sure you want to delete user "${userName}"? This action cannot be undone.`)) {
            console.log(`Deleting user ${userId}`);
        }
    }
    
    // Select all functionality
    document.addEventListener('DOMContentLoaded', function() {
        const selectAll = document.getElementById('select-all');
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                const checkboxes = document.querySelectorAll('input[name="user_ids[]"]');
                checkboxes.forEach(cb => cb.checked = this.checked);
            });
        }
    });
@endpush
        """.strip()
        self.create_template(temp_dir, "admin/users/management.blade.html", user_management_page)
        
        # Create mock user and context
        from .test_blade_nested_directives_simple import MockUser
        
        admin_user = MockUser({
            'id': 1,
            'name': 'Super Admin',
            'email': 'admin@example.com',
            'is_super_admin': True,
            'roles': ['admin', 'super-admin'],
            'permissions': [
                'manage-users', 'create-users', 'edit-users', 'view-users', 'delete-users',
                'bulk-actions', 'bulk-import', 'impersonate-users'
            ]
        })
        
        context: Dict[str, Any] = {
            'current_user': admin_user,
            'current_page': 'users',
            'report_types': [
                {'name': 'User Activity', 'slug': 'user-activity'},
                {'name': 'System Logs', 'slug': 'system-logs'}
            ],
            'user_filters': [
                {
                    'label': 'Role',
                    'name': 'role',
                    'type': 'select',
                    'options': [
                        {'value': '', 'label': 'All Roles', 'selected': True},
                        {'value': 'admin', 'label': 'Administrator', 'selected': False}
                    ]
                },
                {
                    'label': 'Search',
                    'name': 'search',
                    'type': 'text',
                    'value': '',
                    'placeholder': 'Search users...'
                }
            ],
            'total_users': 150,
            'users': [
                {
                    'id': 2,
                    'name': 'John Editor',
                    'email': 'john@example.com',
                    'avatar': '/avatars/john.jpg',
                    'is_verified': True,
                    'is_online': True,
                    'active': True,
                    'suspended': False,
                    'is_protected': False,
                    'roles': [
                        {'name': 'Editor', 'slug': 'editor'}
                    ],
                    'last_login': {
                        'date': '2025-01-15',
                        'time': '14:30'
                    }
                },
                {
                    'id': 3,
                    'name': 'Jane User',
                    'email': 'jane@example.com',
                    'avatar': None,
                    'is_verified': False,
                    'is_online': False,
                    'active': False,
                    'suspended': True,
                    'is_protected': False,
                    'roles': [
                        {'name': 'User', 'slug': 'user'}
                    ],
                    'last_login': None
                }
            ],
            'pagination': {
                'current': 1,
                'total_pages': 8,
                'has_prev': False,
                'has_next': True,
                'prev_url': None,
                'next_url': '/admin/users?page=2',
                'pages': [
                    {'type': 'page', 'number': 1, 'url': '/admin/users?page=1', 'current': True},
                    {'type': 'page', 'number': 2, 'url': '/admin/users?page=2', 'current': False},
                    {'type': 'dots'},
                    {'type': 'page', 'number': 8, 'url': '/admin/users?page=8', 'current': False}
                ]
            }
        }
        
        # Add slice filter
        engine.env.filters['slice'] = lambda s, start, end=None: s[start:end] if s else ''
        
        # Render the complex nested inheritance
        result = engine.render("admin/users/management.blade.html", context)
        
        # Verify 4-level inheritance works
        assert "<!DOCTYPE html>" in result  # Base layout
        assert "My Application" in result   # App layout (overridden by admin)
        assert "Admin Dashboard" in result  # Admin layout override
        assert "User Management - Admin Dashboard" in result  # Page title
        
        # Verify nested navigation
        assert "admin-nav" in result
        assert "Dashboard" in result
        assert "nav-item active" in result
        assert "All Users" in result
        assert "Create User" in result
        
        # Verify user info section
        assert "Super Admin" in result
        assert "System Settings" in result
        
        # Verify breadcrumbs from page level
        assert "breadcrumb" in result
        assert "Management" in result
        
        # Verify complex nested content
        assert "User Management" in result
        assert "Showing 2 of 150 users" in result
        assert "John Editor" in result
        assert "john@example.com" in result
        assert "Editor" in result
        assert "role-editor" in result
        
        # Verify inactive user handling
        assert "Jane User" in result
        assert "user-row inactive" in result
        assert "status-suspended" in result
        assert "Never" in result  # Never logged in
        
        # Verify action buttons with permissions
        assert "icon-eye" in result
        assert "icon-edit" in result
        assert "icon-user-switch" in result
        assert "icon-trash" in result
        
        # Verify pagination
        assert "pagination" in result
        assert "Next" in result
        
        # Verify stacked styles from all levels
        assert "body { font-family: Arial" in result  # Base
        assert ".app-header { background: #2c3e50" in result  # App
        assert ".admin-interface { background: #ecf0f1" in result  # Admin
        assert ".user-management-page { padding: 2rem" in result  # Page
        
        # Verify stacked scripts from all levels
        assert "Admin interface loaded" in result  # Admin layout script
        assert "applyFilters" in result  # Page script
        assert "performBulkAction" in result  # Page script
        
        # Verify footer inheritance
        assert "Admin Dashboard - User Management System" in result
        assert "Help" in result
        assert "Documentation" in result
        assert "&copy; 2025 My Application" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])