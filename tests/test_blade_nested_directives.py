"""
Comprehensive Test Suite for Blade Engine Nested Directives
Tests complex nested directive scenarios and deep nesting combinations
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List, Optional

from app.View.BladeEngine import BladeEngine


class MockUser:
    """Enhanced mock user class for complex permission testing"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self._data = user_data
    
    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)
    
    def has_role(self, role: str) -> bool:
        return role in self._data.get('roles', [])
    
    def has_any_role(self, roles: List[str]) -> bool:
        user_roles = self._data.get('roles', [])
        return any(role in user_roles for role in roles)
    
    def has_all_roles(self, roles: List[str]) -> bool:
        user_roles = self._data.get('roles', [])
        return all(role in user_roles for role in roles)
    
    def can(self, permission: str) -> bool:
        return permission in self._data.get('permissions', [])
    
    def cannot(self, permission: str) -> bool:
        return not self.can(permission)
    
    def owns(self, resource: Dict[str, Any]) -> bool:
        return resource.get('user_id') == self._data.get('id')


class TestBladeNestedDirectives:
    """Test complex nested Blade directives"""
    
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
    
    def test_deeply_nested_authentication_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test deeply nested authentication and permission directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="complex-auth">
    @auth
        <div class="user-dashboard">
            <h1>Welcome, {{ current_user.name }}!</h1>
            
            @hasrole('admin')
                <div class="admin-section">
                    <h2>Admin Panel</h2>
                    
                    @can('manage-users')
                        <div class="user-management">
                            <h3>User Management</h3>
                            
                            @foreach(users as user)
                                <div class="user-item">
                                    <span>{{ user.name }}</span>
                                    
                                    @if(current_user.id != user.id)
                                        @can('edit-users')
                                            @unless(user.is_super_admin)
                                                <div class="user-actions">
                                                    @if(user.is_active)
                                                        @can('deactivate-users')
                                                            <button class="btn-deactivate" 
                                                                    data-user="{{ user.id }}">
                                                                Deactivate
                                                            </button>
                                                        @endcan
                                                    @else
                                                        @can('activate-users')
                                                            <button class="btn-activate" 
                                                                    data-user="{{ user.id }}">
                                                                Activate
                                                            </button>
                                                        @endcan
                                                    @endif
                                                    
                                                    @hasrole('super-admin')
                                                        @can('delete-users')
                                                            @if(not user.is_admin)
                                                                <button class="btn-delete" 
                                                                        data-user="{{ user.id }}">
                                                                    Delete
                                                                </button>
                                                            @endif
                                                        @endcan
                                                    @endhasrole
                                                </div>
                                            @endunless
                                        @endcan
                                    @endif
                                </div>
                            @endforeach
                        </div>
                    @endcan
                    
                    @can('view-reports')
                        <div class="reports-section">
                            <h3>Reports</h3>
                            
                            @foreach(report_categories as category)
                                @if(category.reports)
                                    <div class="report-category">
                                        <h4>{{ category.name }}</h4>
                                        
                                        @foreach(category.reports as report)
                                            @can(report.permission)
                                                <div class="report-item">
                                                    <span>{{ report.title }}</span>
                                                    
                                                    @if(report.requires_approval)
                                                        @hasrole('super-admin')
                                                            <span class="approved">Auto-Approved</span>
                                                        @else
                                                            @can('approve-reports')
                                                                <button class="btn-approve">
                                                                    Request Approval
                                                                </button>
                                                            @else
                                                                <span class="pending">Requires Approval</span>
                                                            @endcan
                                                        @endhasrole
                                                    @endif
                                                </div>
                                            @endcan
                                        @endforeach
                                    </div>
                                @endif
                            @endforeach
                        </div>
                    @endcan
                </div>
            @endhasrole
            
            @hasrole('editor')
                @unless(current_user.has_role('admin'))
                    <div class="editor-section">
                        <h2>Content Management</h2>
                        
                        @foreach(content_items as item)
                            @if(current_user.owns(item) or current_user.can('edit-all-content'))
                                <div class="content-item">
                                    <h4>{{ item.title }}</h4>
                                    
                                    @if(item.status == 'draft')
                                        @can('publish-content')
                                            <button class="btn-publish">Publish</button>
                                        @else
                                            <span class="status-draft">Draft</span>
                                        @endcan
                                    @elseif(item.status == 'published')
                                        @can('unpublish-content')
                                            <button class="btn-unpublish">Unpublish</button>
                                        @endcan
                                        
                                        @if(item.featured)
                                            @can('unfeature-content')
                                                <button class="btn-unfeature">Remove Feature</button>
                                            @endcan
                                        @else
                                            @can('feature-content')
                                                <button class="btn-feature">Feature</button>
                                            @endcan
                                        @endif
                                    @endif
                                </div>
                            @endif
                        @endforeach
                    </div>
                @endunless
            @endhasrole
            
            @hasrole('moderator')
                <div class="moderation-section">
                    <h2>Content Moderation</h2>
                    
                    @foreach(pending_items as item)
                        <div class="moderation-item">
                            <h4>{{ item.title }}</h4>
                            <p>By: {{ item.author.name }}</p>
                            
                            @if(item.flags_count > 0)
                                <div class="flags-section">
                                    <h5>Flags ({{ item.flags_count }})</h5>
                                    
                                    @foreach(item.flags as flag)
                                        <div class="flag-item">
                                            <span>{{ flag.reason }}</span>
                                            <span>by {{ flag.reporter.name }}</span>
                                            
                                            @if(flag.is_serious)
                                                @can('handle-serious-flags')
                                                    <button class="btn-escalate">Escalate</button>
                                                @else
                                                    <span class="needs-admin">Needs Admin Review</span>
                                                @endcan
                                            @else
                                                @can('dismiss-flags')
                                                    <button class="btn-dismiss">Dismiss</button>
                                                @endcan
                                            @endif
                                        </div>
                                    @endforeach
                                </div>
                            @endif
                            
                            @can('approve-content')
                                <button class="btn-approve">Approve</button>
                            @endcan
                            
                            @can('reject-content')
                                <button class="btn-reject">Reject</button>
                            @endcan
                        </div>
                    @endforeach
                </div>
            @endhasrole
        </div>
    @else
        <div class="login-prompt">
            <h2>Please Log In</h2>
            <p>You need to be logged in to access this area.</p>
        </div>
    @endauth
</div>
        """.strip()
        self.create_template(temp_dir, "nested_auth.blade.html", template_content)
        
        # Create super admin user
        super_admin = MockUser({
            'id': 1,
            'name': 'Super Admin',
            'email': 'admin@example.com',
            'roles': ['admin', 'super-admin', 'moderator'],
            'permissions': [
                'manage-users', 'edit-users', 'delete-users', 'activate-users', 'deactivate-users',
                'view-reports', 'approve-reports', 'publish-content', 'unpublish-content',
                'feature-content', 'unfeature-content', 'handle-serious-flags', 'dismiss-flags',
                'approve-content', 'reject-content'
            ]
        })
        
        context: Dict[str, Any] = {
            'current_user': super_admin,
            'users': [
                {
                    'id': 2,
                    'name': 'John Editor',
                    'is_active': True,
                    'is_super_admin': False,
                    'is_admin': False,
                    'has_role': lambda role: role in ['editor']
                },
                {
                    'id': 3,
                    'name': 'Jane Moderator',
                    'is_active': False,
                    'is_super_admin': False,
                    'is_admin': False,
                    'has_role': lambda role: role in ['moderator']
                },
                {
                    'id': 4,
                    'name': 'Bob Admin',
                    'is_active': True,
                    'is_super_admin': False,
                    'is_admin': True,
                    'has_role': lambda role: role in ['admin']
                }
            ],
            'report_categories': [
                {
                    'name': 'User Analytics',
                    'reports': [
                        {
                            'title': 'User Activity Report',
                            'permission': 'view-user-analytics',
                            'requires_approval': False
                        },
                        {
                            'title': 'Sensitive Data Report',
                            'permission': 'view-sensitive-data',
                            'requires_approval': True
                        }
                    ]
                }
            ],
            'content_items': [
                {
                    'id': 1,
                    'title': 'Sample Article',
                    'status': 'draft',
                    'featured': False,
                    'user_id': 1
                },
                {
                    'id': 2,
                    'title': 'Published Post',
                    'status': 'published',
                    'featured': True,
                    'user_id': 2
                }
            ],
            'pending_items': [
                {
                    'id': 1,
                    'title': 'Pending Article',
                    'author': {'name': 'Content Creator'},
                    'flags_count': 2,
                    'flags': [
                        {
                            'reason': 'Inappropriate content',
                            'reporter': {'name': 'User Reporter'},
                            'is_serious': False
                        },
                        {
                            'reason': 'Spam content',
                            'reporter': {'name': 'Another User'},
                            'is_serious': True
                        }
                    ]
                }
            ]
        }
        
        # Add current_user to context and make owns method work
        super_admin._data['owns'] = lambda item: item.get('user_id') == 1
        
        result = engine.render("nested_auth.blade.html", context)
        
        # Verify deeply nested authentication works
        assert "Welcome, Super Admin!" in result
        assert "Admin Panel" in result
        assert "User Management" in result
        assert "John Editor" in result
        assert "Jane Moderator" in result
        assert "Bob Admin" in result
        
        # Verify nested permissions work
        assert "btn-deactivate" in result  # For John (active user)
        assert "btn-activate" in result    # For Jane (inactive user)
        assert "btn-delete" in result      # Super admin can delete non-admins
        
        # Verify complex nested conditions
        assert "Reports" in result
        assert "Content Management" not in result  # Super admin has admin role
        assert "Content Moderation" in result
        assert "Pending Article" in result
        assert "btn-escalate" in result    # Can handle serious flags
        assert "btn-dismiss" in result     # Can dismiss flags
    
    def test_nested_loops_with_complex_conditionals(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test nested loops with complex conditional logic"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="nested-loops-complex">
    <h1>Organization Structure</h1>
    
    @foreach(departments as department)
        <div class="department">
            <h2>{{ department.name }}</h2>
            
            @if(department.teams)
                <div class="teams-section">
                    @foreach(department.teams as team)
                        @if(team.active)
                            <div class="team">
                                <h3>{{ team.name }}</h3>
                                <p>Manager: {{ team.manager.name }}</p>
                                
                                @if(team.members)
                                    <div class="team-members">
                                        @foreach(team.members as member)
                                            @unless(member.on_leave)
                                                <div class="member @if(member.is_lead) team-lead @endif">
                                                    <div class="member-info">
                                                        <h4>{{ member.name }}</h4>
                                                        <p>{{ member.position }}</p>
                                                        
                                                        @if(member.skills)
                                                            <div class="skills">
                                                                <strong>Skills:</strong>
                                                                @foreach(member.skills as skill)
                                                                    <span class="skill {{ skill.level }}">
                                                                        {{ skill.name }}
                                                                        @if(skill.certified)
                                                                            <i class="icon-certified"></i>
                                                                        @endif
                                                                    </span>
                                                                    @unless(loop.last), @endunless
                                                                @endforeach
                                                            </div>
                                                        @endif
                                                        
                                                        @if(member.projects)
                                                            <div class="projects">
                                                                <strong>Current Projects:</strong>
                                                                @foreach(member.projects as project)
                                                                    @if(project.active)
                                                                        <div class="project">
                                                                            <span class="project-name">{{ project.name }}</span>
                                                                            
                                                                            @if(project.priority)
                                                                                @if(project.priority == 'high')
                                                                                    <span class="priority-high">High Priority</span>
                                                                                @elseif(project.priority == 'medium')
                                                                                    <span class="priority-medium">Medium</span>
                                                                                @else
                                                                                    <span class="priority-low">Low</span>
                                                                                @endif
                                                                            @endif
                                                                            
                                                                            @if(project.deadline_approaching)
                                                                                @if(project.completion_percentage < 50)
                                                                                    <span class="warning">Behind Schedule</span>
                                                                                @elseif(project.completion_percentage < 80)
                                                                                    <span class="caution">On Track</span>
                                                                                @else
                                                                                    <span class="success">Ahead of Schedule</span>
                                                                                @endif
                                                                            @endif
                                                                            
                                                                            @if(project.collaborators)
                                                                                <div class="collaborators">
                                                                                    <small>With: 
                                                                                        @foreach(project.collaborators as collab)
                                                                                            @if(collab.id != member.id)
                                                                                                {{ collab.name }}
                                                                                                @unless(loop.last), @endunless
                                                                                            @endif
                                                                                        @endforeach
                                                                                    </small>
                                                                                </div>
                                                                            @endif
                                                                        </div>
                                                                    @endif
                                                                @endforeach
                                                            </div>
                                                        @endif
                                                    </div>
                                                    
                                                    @if(member.performance_metrics)
                                                        <div class="performance">
                                                            @foreach(member.performance_metrics as metric)
                                                                @if(metric.visible_to_team)
                                                                    <div class="metric">
                                                                        <span>{{ metric.name }}: </span>
                                                                        @if(metric.score >= 90)
                                                                            <span class="excellent">{{ metric.score }}%</span>
                                                                        @elseif(metric.score >= 80)
                                                                            <span class="good">{{ metric.score }}%</span>
                                                                        @elseif(metric.score >= 70)
                                                                            <span class="average">{{ metric.score }}%</span>
                                                                        @else
                                                                            <span class="needs-improvement">{{ metric.score }}%</span>
                                                                        @endif
                                                                        
                                                                        @if(metric.trend)
                                                                            @if(metric.trend == 'up')
                                                                                <i class="icon-trend-up"></i>
                                                                            @elseif(metric.trend == 'down')
                                                                                <i class="icon-trend-down"></i>
                                                                            @else
                                                                                <i class="icon-trend-stable"></i>
                                                                            @endif
                                                                        @endif
                                                                    </div>
                                                                @endif
                                                            @endforeach
                                                        </div>
                                                    @endif
                                                </div>
                                            @endunless
                                        @endforeach
                                    </div>
                                @else
                                    <p class="no-members">No active members in this team.</p>
                                @endif
                                
                                @if(team.budget_info)
                                    <div class="budget-summary">
                                        <h4>Budget Status</h4>
                                        @if(team.budget_info.utilization > 90)
                                            <div class="budget-critical">
                                                <span>Critical: {{ team.budget_info.utilization }}% utilized</span>
                                                @if(team.budget_info.overrun_risk)
                                                    <span class="risk-warning">Overrun Risk!</span>
                                                @endif
                                            </div>
                                        @elseif(team.budget_info.utilization > 75)
                                            <div class="budget-warning">
                                                <span>Warning: {{ team.budget_info.utilization }}% utilized</span>
                                            </div>
                                        @else
                                            <div class="budget-good">
                                                <span>Good: {{ team.budget_info.utilization }}% utilized</span>
                                            </div>
                                        @endif
                                    </div>
                                @endif
                            </div>
                        @else
                            <div class="team-inactive">
                                <h3>{{ team.name }} (Inactive)</h3>
                                <p>This team is currently inactive.</p>
                            </div>
                        @endif
                    @endforeach
                </div>
            @else
                <p class="no-teams">No teams in this department.</p>
            @endif
        </div>
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "nested_loops.blade.html", template_content)
        
        context: Dict[str, Any] = {
            'departments': [
                {
                    'name': 'Engineering',
                    'teams': [
                        {
                            'name': 'Backend Team',
                            'active': True,
                            'manager': {'name': 'Alice Johnson'},
                            'budget_info': {
                                'utilization': 85,
                                'overrun_risk': False
                            },
                            'members': [
                                {
                                    'id': 1,
                                    'name': 'John Developer',
                                    'position': 'Senior Developer',
                                    'is_lead': True,
                                    'on_leave': False,
                                    'skills': [
                                        {'name': 'Python', 'level': 'expert', 'certified': True},
                                        {'name': 'FastAPI', 'level': 'advanced', 'certified': False},
                                        {'name': 'PostgreSQL', 'level': 'intermediate', 'certified': True}
                                    ],
                                    'projects': [
                                        {
                                            'name': 'API Redesign',
                                            'active': True,
                                            'priority': 'high',
                                            'deadline_approaching': True,
                                            'completion_percentage': 75,
                                            'collaborators': [
                                                {'id': 2, 'name': 'Sarah Tester'}
                                            ]
                                        }
                                    ],
                                    'performance_metrics': [
                                        {
                                            'name': 'Code Quality',
                                            'score': 92,
                                            'trend': 'up',
                                            'visible_to_team': True
                                        },
                                        {
                                            'name': 'Delivery Speed',
                                            'score': 88,
                                            'trend': 'stable',
                                            'visible_to_team': True
                                        }
                                    ]
                                },
                                {
                                    'id': 2,
                                    'name': 'Sarah Tester',
                                    'position': 'QA Engineer',
                                    'is_lead': False,
                                    'on_leave': True,
                                    'skills': [
                                        {'name': 'Testing', 'level': 'expert', 'certified': True}
                                    ],
                                    'projects': [],
                                    'performance_metrics': []
                                }
                            ]
                        },
                        {
                            'name': 'Frontend Team',
                            'active': False,
                            'manager': {'name': 'Bob Wilson'},
                            'members': []
                        }
                    ]
                },
                {
                    'name': 'Marketing',
                    'teams': []
                }
            ]
        }
        
        result = engine.render("nested_loops.blade.html", context)
        
        # Verify nested loop structure
        assert "Organization Structure" in result
        assert "Engineering" in result
        assert "Backend Team" in result
        assert "Alice Johnson" in result
        
        # Verify deep nesting works
        assert "John Developer" in result
        assert "Senior Developer" in result
        assert "team-lead" in result
        assert "Sarah Tester" not in result  # Should be filtered out (on_leave)
        
        # Verify nested skills loop
        assert "Python" in result
        assert "expert" in result
        assert "icon-certified" in result
        
        # Verify nested projects
        assert "API Redesign" in result
        assert "High Priority" in result
        assert "On Track" in result
        
        # Verify performance metrics
        assert "Code Quality" in result
        assert "92%" in result
        assert "excellent" in result
        assert "icon-trend-up" in result
        
        # Verify budget status
        assert "Budget Status" in result
        assert "Warning: 85% utilized" in result
        
        # Verify inactive team handling
        assert "Frontend Team (Inactive)" in result
        assert "No teams in this department" in result  # Marketing dept
    
    def test_nested_template_inheritance_with_complex_sections(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex nested template inheritance with multiple section levels"""
        engine, temp_dir = blade_engine
        
        # Base layout
        base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Application')</title>
    <meta charset="utf-8">
    @stack('meta')
    
    <style>
        @yield('critical-css')
        @stack('styles')
    </style>
</head>
<body class="@yield('body-class')">
    @yield('header')
    
    <main class="main-content">
        @yield('content')
        
        @hasSection('sidebar')
            <aside class="sidebar">
                @yield('sidebar')
            </aside>
        @endif
    </main>
    
    @yield('footer')
    
    <script>
        @stack('head-scripts')
    </script>
    
    @yield('scripts')
    
    <script>
        @stack('footer-scripts')
    </script>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", base_layout)
        
        # App layout extending base
        app_layout = """
@extends('layouts/base')

@section('header')
    <header class="app-header">
        <nav class="navbar">
            @yield('navbar')
            
            <div class="nav-user">
                @auth
                    <span>Welcome, {{ current_user.name }}</span>
                    @yield('user-menu')
                @else
                    @yield('guest-menu')
                @endauth
            </div>
        </nav>
        
        @hasSection('breadcrumbs')
            <nav class="breadcrumbs">
                @yield('breadcrumbs')
            </nav>
        @endif
    </header>
@endsection

@section('footer')
    <footer class="app-footer">
        @yield('footer-content', '<p>&copy; 2025 My Application</p>')
    </footer>
@endsection

@push('styles')
    .app-header { background: #f8f9fa; padding: 1rem; }
    .navbar { display: flex; justify-content: space-between; }
    .sidebar { width: 250px; background: #e9ecef; }
@endpush
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", app_layout)
        
        # Admin layout extending app
        admin_layout = """
@extends('layouts/app')

@section('body-class', 'admin-layout')

@section('navbar')
    <div class="admin-nav">
        <a href="/admin">Dashboard</a>
        
        @can('manage-users')
            <div class="nav-group">
                <span class="nav-label">Users</span>
                <div class="nav-dropdown">
                    @can('create-users')
                        <a href="/admin/users/create">Create User</a>
                    @endcan
                    @can('view-users')
                        <a href="/admin/users">View All</a>
                    @endcan
                    @can('manage-roles')
                        <a href="/admin/roles">Manage Roles</a>
                    @endcan
                </div>
            </div>
        @endcan
        
        @can('view-reports')
            <div class="nav-group">
                <span class="nav-label">Reports</span>
                <div class="nav-dropdown">
                    @foreach(available_reports as report)
                        @can(report.permission)
                            <a href="{{ report.url }}">{{ report.name }}</a>
                        @endcan
                    @endforeach
                </div>
            </div>
        @endcan
    </div>
@endsection

@section('user-menu')
    <div class="admin-user-menu">
        <a href="/admin/profile">Profile</a>
        @hasrole('super-admin')
            <a href="/admin/system">System Settings</a>
        @endhasrole
        <a href="/logout">Logout</a>
    </div>
@endsection

@section('sidebar')
    <div class="admin-sidebar">
        <h3>Quick Actions</h3>
        <ul class="quick-actions">
            @foreach(quick_actions as action)
                @can(action.permission)
                    <li>
                        <a href="{{ action.url }}" class="action-item">
                            <i class="icon-{{ action.icon }}"></i>
                            {{ action.name }}
                            @if(action.count)
                                <span class="count">{{ action.count }}</span>
                            @endif
                        </a>
                    </li>
                @endcan
            @endforeach
        </ul>
        
        @hasrole('admin')
            <div class="system-status">
                <h4>System Status</h4>
                @foreach(system_checks as check)
                    <div class="status-item {{ check.status }}">
                        <span class="status-name">{{ check.name }}</span>
                        @if(check.status == 'error')
                            <span class="status-error">{{ check.message }}</span>
                        @elseif(check.status == 'warning')
                            <span class="status-warning">{{ check.message }}</span>
                        @else
                            <span class="status-ok">OK</span>
                        @endif
                    </div>
                @endforeach
            </div>
        @endhasrole
    </div>
@endsection

@push('styles')
    .admin-layout { background: #f1f3f4; }
    .admin-nav { display: flex; gap: 2rem; }
    .nav-group { position: relative; }
    .nav-dropdown { position: absolute; background: white; }
    .admin-sidebar { padding: 1rem; }
    .quick-actions { list-style: none; padding: 0; }
    .action-item { display: flex; align-items: center; padding: 0.5rem; }
    .count { background: #dc3545; color: white; border-radius: 50%; }
    .system-status { margin-top: 2rem; }
    .status-item { display: flex; justify-content: space-between; padding: 0.25rem 0; }
    .status-error { color: #dc3545; }
    .status-warning { color: #ffc107; }
    .status-ok { color: #28a745; }
@endpush
        """.strip()
        self.create_template(temp_dir, "layouts/admin.blade.html", admin_layout)
        
        # Final page template
        page_template = """
@extends('layouts/admin')

@section('title', 'User Management - Admin')

@section('critical-css')
    .user-management { min-height: 500px; }
    .loading { display: none; }
@endsection

@push('meta')
    <meta name="description" content="User management interface">
    <meta name="keywords" content="admin, users, management">
@endpush

@section('breadcrumbs')
    <ol class="breadcrumb">
        <li><a href="/admin">Dashboard</a></li>
        <li><a href="/admin/users">Users</a></li>
        <li class="active">Management</li>
    </ol>
@endsection

@section('content')
    <div class="user-management">
        <div class="page-header">
            <h1>User Management</h1>
            
            @can('create-users')
                <div class="header-actions">
                    <a href="/admin/users/create" class="btn btn-primary">Create User</a>
                    @can('bulk-import-users')
                        <a href="/admin/users/import" class="btn btn-secondary">Bulk Import</a>
                    @endcan
                </div>
            @endcan
        </div>
        
        <div class="filters-section">
            @foreach(user_filters as filter)
                @if(filter.visible)
                    <div class="filter-group">
                        <label>{{ filter.label }}</label>
                        @if(filter.type == 'select')
                            <select name="{{ filter.name }}">
                                @foreach(filter.options as option)
                                    <option value="{{ option.value }}" 
                                            @if(option.selected) selected @endif>
                                        {{ option.label }}
                                    </option>
                                @endforeach
                            </select>
                        @elseif(filter.type == 'checkbox')
                            @foreach(filter.options as option)
                                <label class="checkbox">
                                    <input type="checkbox" 
                                           name="{{ filter.name }}[]" 
                                           value="{{ option.value }}"
                                           @if(option.checked) checked @endif>
                                    {{ option.label }}
                                </label>
                            @endforeach
                        @endif
                    </div>
                @endif
            @endforeach
        </div>
        
        <div class="users-table">
            @if(users)
                <table class="data-table">
                    <thead>
                        <tr>
                            @can('bulk-actions')
                                <th><input type="checkbox" id="select-all"></th>
                            @endcan
                            <th>Name</th>
                            <th>Email</th>
                            <th>Roles</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach(users as user)
                            <tr class="user-row @if(user.is_suspended) suspended @endif">
                                @can('bulk-actions')
                                    <td>
                                        @unless(user.is_super_admin)
                                            <input type="checkbox" name="user_ids[]" value="{{ user.id }}">
                                        @endunless
                                    </td>
                                @endcan
                                
                                <td>
                                    <div class="user-info">
                                        @if(user.avatar)
                                            <img src="{{ user.avatar }}" alt="{{ user.name }}" class="avatar">
                                        @endif
                                        <span class="user-name">{{ user.name }}</span>
                                        @if(user.is_verified)
                                            <i class="icon-verified" title="Verified"></i>
                                        @endif
                                    </div>
                                </td>
                                
                                <td>{{ user.email }}</td>
                                
                                <td>
                                    <div class="user-roles">
                                        @foreach(user.roles as role)
                                            <span class="role-badge {{ role.slug }}">
                                                {{ role.name }}
                                            </span>
                                        @endforeach
                                    </div>
                                </td>
                                
                                <td>
                                    @if(user.is_active)
                                        @if(user.is_online)
                                            <span class="status online">Online</span>
                                        @else
                                            <span class="status active">Active</span>
                                        @endif
                                    @else
                                        <span class="status inactive">Inactive</span>
                                    @endif
                                    
                                    @if(user.is_suspended)
                                        <span class="status suspended">Suspended</span>
                                    @endif
                                </td>
                                
                                <td>
                                    <div class="action-buttons">
                                        @can('view-users')
                                            <a href="/admin/users/{{ user.id }}" class="btn-view">View</a>
                                        @endcan
                                        
                                        @can('edit-users')
                                            @unless(user.is_super_admin and not current_user.is_super_admin)
                                                <a href="/admin/users/{{ user.id }}/edit" class="btn-edit">Edit</a>
                                            @endunless
                                        @endcan
                                        
                                        @can('suspend-users')
                                            @unless(user.is_super_admin)
                                                @if(user.is_suspended)
                                                    <button class="btn-unsuspend" data-user="{{ user.id }}">
                                                        Unsuspend
                                                    </button>
                                                @else
                                                    <button class="btn-suspend" data-user="{{ user.id }}">
                                                        Suspend
                                                    </button>
                                                @endif
                                            @endunless
                                        @endcan
                                        
                                        @can('delete-users')
                                            @unless(user.is_super_admin or user.id == current_user.id)
                                                <button class="btn-delete" data-user="{{ user.id }}">
                                                    Delete
                                                </button>
                                            @endunless
                                        @endcan
                                    </div>
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            @else
                <div class="empty-state">
                    <p>No users found matching your criteria.</p>
                </div>
            @endif
        </div>
    </div>
@endsection

@push('styles')
    .user-management .page-header { display: flex; justify-content: space-between; margin-bottom: 2rem; }
    .filters-section { background: white; padding: 1rem; margin-bottom: 1rem; }
    .filter-group { display: inline-block; margin-right: 1rem; }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th, .data-table td { padding: 0.75rem; border-bottom: 1px solid #dee2e6; }
    .user-row.suspended { opacity: 0.6; }
    .user-info { display: flex; align-items: center; gap: 0.5rem; }
    .avatar { width: 32px; height: 32px; border-radius: 50%; }
    .role-badge { padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.875rem; }
    .role-badge.admin { background: #dc3545; color: white; }
    .role-badge.editor { background: #28a745; color: white; }
    .role-badge.user { background: #6c757d; color: white; }
    .status { padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.875rem; }
    .status.online { background: #28a745; color: white; }
    .status.active { background: #17a2b8; color: white; }
    .status.inactive { background: #6c757d; color: white; }
    .status.suspended { background: #dc3545; color: white; }
    .action-buttons { display: flex; gap: 0.5rem; }
    .empty-state { text-align: center; padding: 2rem; }
@endpush

@push('head-scripts')
    window.userManagement = {
        deleteUrl: '/admin/users/delete',
        suspendUrl: '/admin/users/suspend',
        csrfToken: '{{ csrf_token() }}'
    };
@endpush

@section('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Select all functionality
            const selectAllCheckbox = document.getElementById('select-all');
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', function() {
                    const checkboxes = document.querySelectorAll('input[name="user_ids[]"]');
                    checkboxes.forEach(cb => cb.checked = this.checked);
                });
            }
            
            // Suspend/Unsuspend functionality
            document.querySelectorAll('.btn-suspend, .btn-unsuspend').forEach(btn => {
                btn.addEventListener('click', function() {
                    const userId = this.dataset.user;
                    const action = this.classList.contains('btn-suspend') ? 'suspend' : 'unsuspend';
                    
                    if (confirm(`Are you sure you want to ${action} this user?`)) {
                        fetch(window.userManagement.suspendUrl, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRF-TOKEN': window.userManagement.csrfToken
                            },
                            body: JSON.stringify({
                                user_id: userId,
                                action: action
                            })
                        }).then(response => {
                            if (response.ok) {
                                location.reload();
                            }
                        });
                    }
                });
            });
            
            // Delete functionality
            document.querySelectorAll('.btn-delete').forEach(btn => {
                btn.addEventListener('click', function() {
                    const userId = this.dataset.user;
                    
                    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
                        fetch(window.userManagement.deleteUrl, {
                            method: 'DELETE',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRF-TOKEN': window.userManagement.csrfToken
                            },
                            body: JSON.stringify({
                                user_id: userId
                            })
                        }).then(response => {
                            if (response.ok) {
                                location.reload();
                            }
                        });
                    }
                });
            });
        });
    </script>
@endsection

@push('footer-scripts')
    // Track page view
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            page: 'admin.users.management',
            user_id: {{ current_user.id }}
        })
    });
@endpush
        """.strip()
        self.create_template(temp_dir, "admin/users/management.blade.html", page_template)
        
        # Create admin user
        admin_user = MockUser({
            'id': 1,
            'name': 'Super Admin',
            'email': 'admin@example.com',
            'is_super_admin': True,
            'roles': ['admin', 'super-admin'],
            'permissions': [
                'manage-users', 'create-users', 'edit-users', 'view-users', 'delete-users',
                'suspend-users', 'bulk-actions', 'bulk-import-users', 'manage-roles',
                'view-reports'
            ]
        })
        
        context: Dict[str, Any] = {
            'current_user': admin_user,
            'available_reports': [
                {'name': 'User Activity', 'url': '/admin/reports/activity', 'permission': 'view-reports'},
                {'name': 'System Logs', 'url': '/admin/reports/logs', 'permission': 'view-reports'}
            ],
            'quick_actions': [
                {'name': 'Create User', 'url': '/admin/users/create', 'icon': 'user-plus', 'permission': 'create-users', 'count': None},
                {'name': 'Pending Approvals', 'url': '/admin/approvals', 'icon': 'clock', 'permission': 'view-reports', 'count': 5}
            ],
            'system_checks': [
                {'name': 'Database', 'status': 'ok', 'message': 'Connected'},
                {'name': 'Cache', 'status': 'warning', 'message': 'High memory usage'},
                {'name': 'Storage', 'status': 'ok', 'message': '45% used'}
            ],
            'user_filters': [
                {
                    'label': 'Role',
                    'name': 'role',
                    'type': 'select',
                    'visible': True,
                    'options': [
                        {'value': '', 'label': 'All Roles', 'selected': True},
                        {'value': 'admin', 'label': 'Admin', 'selected': False},
                        {'value': 'editor', 'label': 'Editor', 'selected': False}
                    ]
                },
                {
                    'label': 'Status',
                    'name': 'status',
                    'type': 'checkbox',
                    'visible': True,
                    'options': [
                        {'value': 'active', 'label': 'Active', 'checked': True},
                        {'value': 'inactive', 'label': 'Inactive', 'checked': False}
                    ]
                }
            ],
            'users': [
                {
                    'id': 2,
                    'name': 'John Editor',
                    'email': 'john@example.com',
                    'avatar': '/avatars/john.jpg',
                    'is_verified': True,
                    'is_active': True,
                    'is_online': True,
                    'is_suspended': False,
                    'is_super_admin': False,
                    'roles': [
                        {'name': 'Editor', 'slug': 'editor'}
                    ]
                },
                {
                    'id': 3,
                    'name': 'Jane User',
                    'email': 'jane@example.com',
                    'avatar': None,
                    'is_verified': False,
                    'is_active': False,
                    'is_online': False,
                    'is_suspended': True,
                    'is_super_admin': False,
                    'roles': [
                        {'name': 'User', 'slug': 'user'}
                    ]
                }
            ]
        }
        
        # Add template globals
        engine.env.globals['csrf_token'] = lambda: 'test-csrf-token'
        
        result = engine.render("admin/users/management.blade.html", context)
        
        # Verify complex template inheritance
        assert "<!DOCTYPE html>" in result
        assert "User Management - Admin" in result
        assert "admin-layout" in result
        
        # Verify nested sections work
        assert "Welcome, Super Admin" in result
        assert "Dashboard" in result
        assert "Create User" in result
        assert "View All" in result
        assert "Manage Roles" in result
        
        # Verify stacked content
        assert ".admin-layout" in result
        assert ".user-management" in result
        assert "window.userManagement" in result
        
        # Verify deep conditional nesting in table
        assert "John Editor" in result
        assert "john@example.com" in result
        assert "icon-verified" in result
        assert "Online" in result
        assert "Editor" in result
        
        # Verify complex action buttons
        assert "btn-edit" in result
        assert "btn-suspend" in result
        assert "btn-delete" in result
        
        # Verify suspended user handling
        assert "Jane User" in result
        assert "suspended" in result
        assert "btn-unsuspend" in result
        
        # Verify sidebar content
        assert "Quick Actions" in result
        assert "Pending Approvals" in result
        assert "System Status" in result
        assert "Database" in result
        assert "Cache" in result
        assert "High memory usage" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])