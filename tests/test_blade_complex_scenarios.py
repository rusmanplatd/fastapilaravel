"""
Complex Blade Template Engine Test Scenarios
Tests real-world scenarios combining multiple Blade features and directives
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List, Optional
import os

from app.View.BladeEngine import BladeEngine


class MockUser:
    """Mock user class for authentication tests"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self._data = user_data
    
    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)
    
    def has_role(self, role: str) -> bool:
        return role in self._data.get('roles', [])
    
    def has_any_role(self, roles: List[str]) -> bool:
        user_roles = self._data.get('roles', [])
        return any(role in user_roles for role in roles)
    
    def can(self, permission: str) -> bool:
        return permission in self._data.get('permissions', [])
    
    def cannot(self, permission: str) -> bool:
        return not self.can(permission)


class TestComplexBladeScenarios:
    """Complex real-world Blade template scenarios"""
    
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
    
    def test_complex_admin_dashboard(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex admin dashboard with multiple Blade features"""
        engine, temp_dir = blade_engine
        
        # Main admin layout
        admin_layout = """
<!DOCTYPE html>
<html lang="{{ locale or 'en' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title') - Admin Panel</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
    @yield('meta')
    
    <link href="{{ asset('css/admin.css') }}" rel="stylesheet">
    @yield('styles')
</head>
<body class="admin-body @yield('body_class')">
    @include('admin/partials/header')
    
    <div class="admin-container">
        @include('admin/partials/sidebar')
        
        <main class="admin-main">
            @yield('breadcrumbs')
            
            @if(flash_message)
                <div class="alert alert-{{ flash_type or 'info' }}">
                    {!! flash_message !!}
                    <button type="button" class="close">&times;</button>
                </div>
            @endif
            
            @yield('content')
        </main>
    </div>
    
    @include('admin/partials/footer')
    
    <script src="{{ asset('js/admin.js') }}"></script>
    @yield('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/admin.blade.html", admin_layout)
        
        # Header partial
        header_content = """
<header class="admin-header">
    <div class="header-content">
        <div class="logo">
            <h1>{{ config('app.name', 'Admin Panel') }}</h1>
        </div>
        
        <nav class="header-nav">
            @auth
                <div class="user-menu">
                    <span class="user-name">Hello, {{ current_user.name }}!</span>
                    
                    @can('view-notifications')
                        <div class="notifications">
                            <i class="icon-bell"></i>
                            @if(notification_count > 0)
                                <span class="badge">{{ notification_count }}</span>
                            @endif
                        </div>
                    @endcan
                    
                    <div class="dropdown">
                        <button class="dropdown-toggle">
                            <img src="{{ current_user.avatar or asset('images/default-avatar.png') }}" 
                                 alt="Avatar" class="avatar">
                        </button>
                        <div class="dropdown-menu">
                            <a href="{{ route('profile') }}">Profile</a>
                            @can('manage-settings')
                                <a href="{{ route('admin.settings') }}">Settings</a>
                            @endcan
                            <hr>
                            <a href="{{ route('logout') }}">Logout</a>
                        </div>
                    </div>
                </div>
            @else
                <a href="{{ route('login') }}" class="login-btn">Login</a>
            @endauth
        </nav>
    </div>
</header>
        """.strip()
        self.create_template(temp_dir, "admin/partials/header.blade.html", header_content)
        
        # Sidebar partial
        sidebar_content = """
<aside class="admin-sidebar">
    <nav class="sidebar-nav">
        @foreach(menu_items as menu_item)
            @if(menu_item.get('roles') and current_user.has_any_role(menu_item.roles))
                @continue
            @endif
            
            @unless(menu_item.get('permission') and not current_user.can(menu_item.permission))
                <div class="nav-group">
                    @if(menu_item.get('children'))
                        <div class="nav-group-header">
                            <i class="icon-{{ menu_item.icon }}"></i>
                            {{ menu_item.title }}
                        </div>
                        <ul class="nav-group-items">
                            @foreach(menu_item.children as child_item)
                                @can(child_item.get('permission', 'view'))
                                    <li class="nav-item @if(child_item.route == current_route) active @endif">
                                        <a href="{{ route(child_item.route) }}">
                                            <i class="icon-{{ child_item.icon }}"></i>
                                            {{ child_item.title }}
                                            @if(child_item.get('badge'))
                                                <span class="badge">{{ child_item.badge }}</span>
                                            @endif
                                        </a>
                                    </li>
                                @endcan
                            @endforeach
                        </ul>
                    @else
                        <a href="{{ route(menu_item.route) }}" 
                           class="nav-link @if(menu_item.route == current_route) active @endif">
                            <i class="icon-{{ menu_item.icon }}"></i>
                            {{ menu_item.title }}
                        </a>
                    @endif
                </div>
            @endunless
        @endforeach
    </nav>
</aside>
        """.strip()
        self.create_template(temp_dir, "admin/partials/sidebar.blade.html", sidebar_content)
        
        # Footer partial
        footer_content = """
<footer class="admin-footer">
    <div class="footer-content">
        <div class="footer-left">
            <span>&copy; {{ date('Y') }} {{ config('app.name') }}</span>
            <span class="separator">|</span>
            <span>Version {{ config('app.version', '1.0.0') }}</span>
        </div>
        <div class="footer-right">
            @if(debug_mode)
                <span class="debug-info">
                    Debug Mode | 
                    Memory: {{ memory_usage | default('N/A') }} | 
                    Time: {{ render_time | default('N/A') }}ms
                </span>
            @endif
        </div>
    </div>
</footer>
        """.strip()
        self.create_template(temp_dir, "admin/partials/footer.blade.html", footer_content)
        
        # Dashboard page
        dashboard_content = """
@extends('layouts/admin')

@section('title', 'Dashboard')

@section('body_class', 'dashboard-page')

@section('meta')
    <meta name="description" content="Admin dashboard overview">
@endsection

@section('breadcrumbs')
    <nav class="breadcrumbs">
        <ol>
            <li><a href="{{ route('admin.dashboard') }}">Dashboard</a></li>
            <li class="active">Overview</li>
        </ol>
    </nav>
@endsection

@section('content')
    <div class="dashboard-content">
        <!-- Statistics Cards -->
        <div class="stats-grid">
            @foreach(dashboard_stats as stat)
                <div class="stat-card @if(stat.trend == 'up') trend-up @elseif(stat.trend == 'down') trend-down @endif">
                    <div class="stat-header">
                        <h3>{{ stat.title }}</h3>
                        <i class="icon-{{ stat.icon }}"></i>
                    </div>
                    <div class="stat-value">
                        {{ stat.value | number_format }}
                        @if(stat.get('change'))
                            <span class="stat-change">
                                @if(stat.change > 0)+@endif{{ stat.change }}%
                            </span>
                        @endif
                    </div>
                    @if(stat.get('subtitle'))
                        <div class="stat-subtitle">{{ stat.subtitle }}</div>
                    @endif
                </div>
            @endforeach
        </div>
        
        <!-- Quick Actions -->
        @can('perform-actions')
            <div class="quick-actions">
                <h2>Quick Actions</h2>
                <div class="action-grid">
                    @foreach(quick_actions as action)
                        @can(action.permission)
                            <a href="{{ route(action.route) }}" 
                               class="action-card @if(action.get('primary')) primary @endif">
                                <i class="icon-{{ action.icon }}"></i>
                                <h3>{{ action.title }}</h3>
                                <p>{{ action.description }}</p>
                            </a>
                        @endcan
                    @endforeach
                </div>
            </div>
        @endcan
        
        <!-- Recent Activity -->
        <div class="recent-activity">
            <div class="section-header">
                <h2>Recent Activity</h2>
                <div class="section-actions">
                    @can('view-all-activity')
                        <a href="{{ route('admin.activity') }}" class="btn btn-outline">
                            View All
                        </a>
                    @endcan
                </div>
            </div>
            
            @if(recent_activities)
                <div class="activity-list">
                    @foreach(recent_activities as activity)
                        <div class="activity-item @if(loop.last) last @endif">
                            <div class="activity-avatar">
                                <img src="{{ activity.user.avatar or asset('images/default-avatar.png') }}" 
                                     alt="{{ activity.user.name }}">
                            </div>
                            <div class="activity-content">
                                <div class="activity-text">
                                    <strong>{{ activity.user.name }}</strong>
                                    {{ activity.description }}
                                    @if(activity.get('target'))
                                        <em>"{{ activity.target | truncate(50) }}"</em>
                                    @endif
                                </div>
                                <div class="activity-meta">
                                    <time datetime="{{ activity.created_at }}">
                                        {{ activity.created_at | timeago }}
                                    </time>
                                    @if(activity.get('ip_address'))
                                        <span class="ip">{{ activity.ip_address }}</span>
                                    @endif
                                </div>
                            </div>
                            @if(activity.get('status'))
                                <div class="activity-status">
                                    <span class="status-badge status-{{ activity.status }}">
                                        {{ activity.status | title }}
                                    </span>
                                </div>
                            @endif
                        </div>
                    @endforeach
                </div>
            @else
                <div class="empty-state">
                    <i class="icon-activity"></i>
                    <h3>No recent activity</h3>
                    <p>Activity will appear here as users interact with the system.</p>
                </div>
            @endif
        </div>
        
        <!-- System Status -->
        @hasrole('super-admin')
            <div class="system-status">
                <h2>System Status</h2>
                <div class="status-grid">
                    @foreach(system_checks as check)
                        <div class="status-item">
                            <div class="status-indicator @if(check.status == 'ok') ok @elseif(check.status == 'warning') warning @else error @endif">
                                <i class="icon-{{ check.status == 'ok' ? 'check' : (check.status == 'warning' ? 'warning' : 'error') }}"></i>
                            </div>
                            <div class="status-details">
                                <h4>{{ check.name }}</h4>
                                <p>{{ check.message }}</p>
                                @if(check.get('last_checked'))
                                    <small>Last checked: {{ check.last_checked | timeago }}</small>
                                @endif
                            </div>
                        </div>
                    @endforeach
                </div>
            </div>
        @endhasrole
    </div>
@endsection

@section('styles')
    <style>
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 1rem; 
            margin-bottom: 2rem; 
        }
        .stat-card { 
            background: white; 
            padding: 1.5rem; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
        }
        .trend-up { border-left: 4px solid #10b981; }
        .trend-down { border-left: 4px solid #ef4444; }
        .activity-list { max-height: 400px; overflow-y: auto; }
        .empty-state { text-align: center; padding: 2rem; color: #6b7280; }
    </style>
@endsection

@section('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-refresh stats every 30 seconds
            @if(config('dashboard.auto_refresh', true))
                setInterval(function() {
                    fetch('{{ route("admin.dashboard.stats") }}')
                        .then(response => response.json())
                        .then(data => updateStats(data))
                        .catch(console.error);
                }, 30000);
            @endif
            
            // Initialize tooltips
            document.querySelectorAll('[data-tooltip]').forEach(function(element) {
                new Tooltip(element);
            });
            
            // Log page view
            fetch('{{ route("admin.analytics.pageview") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({
                    page: '{{ current_route }}',
                    timestamp: new Date().toISOString()
                })
            });
        });
        
        function updateStats(data) {
            // Update dashboard stats dynamically
            @json(dashboard_stats);
            console.log('Stats updated:', data);
        }
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "admin/dashboard.blade.html", dashboard_content)
        
        # Set up complex test context
        admin_user = MockUser({
            'id': 1,
            'name': 'John Admin',
            'email': 'admin@example.com',
            'avatar': '/avatars/admin.jpg',
            'roles': ['admin', 'super-admin'],
            'permissions': ['view-notifications', 'manage-settings', 'perform-actions', 'view-all-activity']
        })
        
        context: Dict[str, Any] = {
            'locale': 'en',
            'current_user': admin_user,
            'flash_message': 'Welcome back to the admin panel!',
            'flash_type': 'success',
            'notification_count': 5,
            'current_route': 'admin.dashboard',
            'debug_mode': True,
            'memory_usage': '45.2MB',
            'render_time': '127',
            'menu_items': [
                {
                    'title': 'Dashboard',
                    'route': 'admin.dashboard',
                    'icon': 'dashboard',
                    'permission': 'view-dashboard'
                },
                {
                    'title': 'User Management',
                    'icon': 'users',
                    'children': [
                        {
                            'title': 'All Users',
                            'route': 'admin.users.index',
                            'icon': 'user',
                            'permission': 'view-users'
                        },
                        {
                            'title': 'Roles',
                            'route': 'admin.roles.index',
                            'icon': 'shield',
                            'permission': 'manage-roles',
                            'badge': '3'
                        }
                    ]
                },
                {
                    'title': 'Settings',
                    'route': 'admin.settings',
                    'icon': 'settings',
                    'permission': 'manage-settings'
                }
            ],
            'dashboard_stats': [
                {
                    'title': 'Total Users',
                    'value': 15234,
                    'change': 12.5,
                    'trend': 'up',
                    'icon': 'users',
                    'subtitle': 'Active this month'
                },
                {
                    'title': 'Revenue',
                    'value': 98765,
                    'change': -2.1,
                    'trend': 'down',
                    'icon': 'dollar',
                    'subtitle': 'This quarter'
                },
                {
                    'title': 'Orders',
                    'value': 3456,
                    'change': 8.3,
                    'trend': 'up',
                    'icon': 'shopping',
                    'subtitle': 'Last 7 days'
                }
            ],
            'quick_actions': [
                {
                    'title': 'Create User',
                    'description': 'Add a new user to the system',
                    'route': 'admin.users.create',
                    'icon': 'user-plus',
                    'permission': 'create-users',
                    'primary': True
                },
                {
                    'title': 'Generate Report',
                    'description': 'Create system analytics report',
                    'route': 'admin.reports.create',
                    'icon': 'chart',
                    'permission': 'view-reports'
                }
            ],
            'recent_activities': [
                {
                    'user': {'name': 'Alice Johnson', 'avatar': '/avatars/alice.jpg'},
                    'description': 'updated user profile for',
                    'target': 'Bob Smith (bob@example.com)',
                    'created_at': '2025-01-15T10:30:00Z',
                    'ip_address': '192.168.1.100',
                    'status': 'success'
                },
                {
                    'user': {'name': 'Charlie Brown', 'avatar': None},
                    'description': 'deleted post',
                    'target': 'Introduction to FastAPI Development',
                    'created_at': '2025-01-15T09:15:00Z',
                    'ip_address': '10.0.0.1',
                    'status': 'warning'
                }
            ],
            'system_checks': [
                {
                    'name': 'Database Connection',
                    'status': 'ok',
                    'message': 'All database connections are healthy',
                    'last_checked': '2025-01-15T10:45:00Z'
                },
                {
                    'name': 'Cache System',
                    'status': 'warning',
                    'message': 'Cache hit rate below optimal (75%)',
                    'last_checked': '2025-01-15T10:44:00Z'
                },
                {
                    'name': 'Storage Space',
                    'status': 'ok',
                    'message': '45% utilized (234GB available)',
                    'last_checked': '2025-01-15T10:43:00Z'
                }
            ]
        }
        
        # Render the complex dashboard
        result = engine.render("admin/dashboard.blade.html", context)
        
        # Verify complex template features
        assert "Admin Panel" in result
        assert "Hello, John Admin!" in result
        assert "Welcome back to the admin panel!" in result
        assert "alert-success" in result
        assert '<span class="badge">5</span>' in result
        
        # Verify authorization checks
        assert "User Management" in result
        assert "All Users" in result
        assert "Settings" in result
        
        # Verify dashboard stats
        assert "15,234" in result or "15234" in result
        assert "+12.5%" in result
        assert "-2.1%" in result
        assert "trend-up" in result
        assert "trend-down" in result
        
        # Verify quick actions
        assert "Create User" in result
        assert "Generate Report" in result
        
        # Verify recent activity
        assert "Alice Johnson" in result
        assert "Charlie Brown" in result
        assert "updated user profile" in result
        assert "Bob Smith" in result
        
        # Verify system status (super-admin only)
        assert "System Status" in result
        assert "Database Connection" in result
        assert "Cache System" in result
        assert "75%" in result
        
        # Verify JavaScript integration
        assert "updateStats" in result
        assert "admin.dashboard.stats" in result
        assert "X-CSRF-TOKEN" in result
        
        # Verify CSS and styling
        assert ".stats-grid" in result
        assert "grid-template-columns" in result
        assert "border-left: 4px solid" in result
    
    def test_complex_ecommerce_product_page(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex e-commerce product page with multiple features"""
        engine, temp_dir = blade_engine
        
        # Main layout
        layout_content = """
<!DOCTYPE html>
<html lang="{{ locale or 'en' }}" data-theme="{{ theme or 'light' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', config('app.name'))</title>
    
    @yield('meta')
    
    <link href="{{ asset('css/app.css') }}" rel="stylesheet">
    @yield('styles')
    
    @if(config('analytics.gtag_id'))
        <script async src="https://www.googletagmanager.com/gtag/js?id={{ config('analytics.gtag_id') }}"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '{{ config('analytics.gtag_id') }}');
        </script>
    @endif
</head>
<body class="@yield('body_class')">
    @include('partials.header')
    
    @yield('breadcrumbs')
    
    <main class="main-content">
        @yield('content')
    </main>
    
    @include('partials.footer')
    
    <script src="{{ asset('js/app.js') }}"></script>
    @yield('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", layout_content)
        
        # Header partial
        header_content = """
<header class="site-header">
    <div class="header-top">
        <div class="container">
            <div class="header-info">
                <span>Free shipping on orders over {{ free_shipping_threshold | money }}</span>
            </div>
            <div class="header-actions">
                @auth
                    <a href="{{ route('account') }}">My Account</a>
                @else
                    <a href="{{ route('login') }}">Login</a>
                    <a href="{{ route('register') }}">Register</a>
                @endauth
            </div>
        </div>
    </div>
    
    <div class="header-main">
        <div class="container">
            <div class="header-content">
                <div class="logo">
                    <a href="{{ route('home') }}">
                        <img src="{{ asset('images/logo.png') }}" alt="{{ config('app.name') }}">
                    </a>
                </div>
                
                <div class="header-search">
                    <form action="{{ route('search') }}" method="GET" class="search-form">
                        <input type="text" name="q" placeholder="Search products..." value="{{ search_query }}">
                        <button type="submit">
                            <i class="icon-search"></i>
                        </button>
                    </form>
                </div>
                
                <div class="header-cart">
                    <a href="{{ route('cart') }}" class="cart-link">
                        <i class="icon-cart"></i>
                        <span class="cart-count">{{ cart.item_count }}</span>
                        <span class="cart-total">{{ cart.total | money }}</span>
                    </a>
                </div>
            </div>
        </div>
    </div>
</header>
        """.strip()
        self.create_template(temp_dir, "partials/header.blade.html", header_content)
        
        # Complex product page
        product_page = """
@extends('layouts/app')

@section('title', product.name ~ ' - ' ~ config('app.name'))

@section('meta')
    <meta name="description" content="{{ product.description | striptags | truncate(160) }}">
    <meta name="keywords" content="{{ product.tags | join(', ') }}">
    <meta property="og:title" content="{{ product.name }}">
    <meta property="og:description" content="{{ product.description | striptags | truncate(300) }}">
    <meta property="og:image" content="{{ asset(product.featured_image) }}">
    <meta property="og:type" content="product">
    <meta property="product:price:amount" content="{{ product.price }}">
    <meta property="product:price:currency" content="{{ currency }}">
    
    <script type="application/ld+json">
    @json({
        '@context': 'https://schema.org/',
        '@type': 'Product',
        'name': product.name,
        'description': product.description,
        'image': [asset(product.featured_image)],
        'brand': {'@type': 'Brand', 'name': product.brand.name},
        'offers': {
            '@type': 'Offer',
            'url': route('products.show', product.slug),
            'priceCurrency': currency,
            'price': product.price,
            'availability': product.in_stock ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock'
        }
    })
    </script>
@endsection

@section('breadcrumbs')
    <nav class="breadcrumbs">
        <div class="container">
            <ol itemscope itemtype="https://schema.org/BreadcrumbList">
                <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                    <a itemprop="item" href="{{ route('home') }}">
                        <span itemprop="name">Home</span>
                    </a>
                    <meta itemprop="position" content="1">
                </li>
                @foreach(product.categories as category)
                    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                        <a itemprop="item" href="{{ route('categories.show', category.slug) }}">
                            <span itemprop="name">{{ category.name }}</span>
                        </a>
                        <meta itemprop="position" content="{{ loop.index + 1 }}">
                    </li>
                @endforeach
                <li class="active" itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                    <span itemprop="name">{{ product.name }}</span>
                    <meta itemprop="position" content="{{ (product.categories | length) + 2 }}">
                </li>
            </ol>
        </div>
    </nav>
@endsection

@section('content')
    <div class="product-page">
        <div class="container">
            <!-- Product Main Section -->
            <div class="product-main">
                <div class="product-gallery">
                    <div class="gallery-main">
                        <img src="{{ asset(product.featured_image) }}" 
                             alt="{{ product.name }}" 
                             class="main-image"
                             data-zoom="{{ asset(product.featured_image_large) }}">
                    </div>
                    
                    @if(product.images)
                        <div class="gallery-thumbs">
                            @foreach(product.images as image)
                                <button type="button" 
                                        class="thumb @if(loop.first) active @endif"
                                        data-image="{{ asset(image.url) }}"
                                        data-zoom="{{ asset(image.large_url) }}">
                                    <img src="{{ asset(image.thumb_url) }}" alt="Product image {{ loop.index }}">
                                </button>
                            @endforeach
                        </div>
                    @endif
                    
                    @if(product.video_url)
                        <div class="product-video">
                            <button type="button" class="video-trigger" data-video="{{ product.video_url }}">
                                <i class="icon-play"></i>
                                Watch Video
                            </button>
                        </div>
                    @endif
                </div>
                
                <div class="product-info">
                    <div class="product-header">
                        @if(product.brand)
                            <div class="brand">
                                <a href="{{ route('brands.show', product.brand.slug) }}">
                                    {{ product.brand.name }}
                                </a>
                            </div>
                        @endif
                        
                        <h1 class="product-title">{{ product.name }}</h1>
                        
                        @if(product.rating_average > 0)
                            <div class="product-rating">
                                <div class="stars">
                                    @for(i = 1; i <= 5; i++)
                                        <i class="icon-star @if(i <= product.rating_average) filled @endif"></i>
                                    @endfor
                                </div>
                                <span class="rating-count">
                                    ({{ product.review_count }} 
                                    {{ product.review_count == 1 ? 'review' : 'reviews' }})
                                </span>
                            </div>
                        @endif
                    </div>
                    
                    <div class="product-pricing">
                        @if(product.sale_price and product.sale_price < product.price)
                            <div class="pricing-sale">
                                <span class="sale-price">{{ product.sale_price | money }}</span>
                                <span class="original-price">{{ product.price | money }}</span>
                                <span class="discount-badge">
                                    Save {{ ((product.price - product.sale_price) / product.price * 100) | round }}%
                                </span>
                            </div>
                        @else
                            <div class="pricing-regular">
                                <span class="price">{{ product.price | money }}</span>
                            </div>
                        @endif
                        
                        @if(product.price_per_unit)
                            <div class="price-per-unit">
                                {{ product.price_per_unit | money }} per {{ product.unit_type }}
                            </div>
                        @endif
                    </div>
                    
                    @if(product.description)
                        <div class="product-description">
                            {!! product.description !!}
                        </div>
                    @endif
                    
                    <!-- Product Options -->
                    @if(product.variants)
                        <div class="product-options">
                            @foreach(product.option_types as option_type)
                                <div class="option-group">
                                    <label class="option-label">{{ option_type.name }}:</label>
                                    <div class="option-values">
                                        @foreach(option_type.values as value)
                                            @php
                                                $available = product.variants->some(function($variant) use ($value) {
                                                    return $variant->options->contains('value', $value->value) && $variant->stock > 0;
                                                });
                                            @endphp
                                            
                                            <button type="button" 
                                                    class="option-value @unless(available) disabled @endunless"
                                                    data-option="{{ option_type.name }}"
                                                    data-value="{{ value.value }}"
                                                    @unless(available) disabled @endunless>
                                                @if(option_type.type == 'color')
                                                    <span class="color-swatch" 
                                                          style="background-color: {{ value.hex_color }}"></span>
                                                @endif
                                                {{ value.display_name }}
                                            </button>
                                        @endforeach
                                    </div>
                                </div>
                            @endforeach
                        </div>
                    @endif
                    
                    <!-- Add to Cart -->
                    <div class="product-actions">
                        <form action="{{ route('cart.add') }}" method="POST" class="add-to-cart-form">
                            @csrf
                            <input type="hidden" name="product_id" value="{{ product.id }}">
                            
                            <div class="quantity-selector">
                                <label for="quantity">Quantity:</label>
                                <div class="quantity-input">
                                    <button type="button" class="qty-decrease">-</button>
                                    <input type="number" 
                                           id="quantity" 
                                           name="quantity" 
                                           value="1" 
                                           min="1" 
                                           max="{{ product.max_quantity or 99 }}">
                                    <button type="button" class="qty-increase">+</button>
                                </div>
                            </div>
                            
                            <div class="action-buttons">
                                @if(product.in_stock)
                                    <button type="submit" class="btn btn-primary btn-add-cart">
                                        <i class="icon-cart"></i>
                                        Add to Cart
                                    </button>
                                    
                                    @if(config('features.buy_now'))
                                        <button type="button" class="btn btn-secondary btn-buy-now">
                                            Buy Now
                                        </button>
                                    @endif
                                @else
                                    <button type="button" class="btn btn-disabled" disabled>
                                        Out of Stock
                                    </button>
                                    
                                    @if(config('features.back_in_stock_notifications'))
                                        <button type="button" class="btn btn-outline btn-notify">
                                            Notify When Available
                                        </button>
                                    @endif
                                @endif
                            </div>
                        </form>
                        
                        <div class="product-meta">
                            @if(product.sku)
                                <div class="meta-item">
                                    <strong>SKU:</strong> {{ product.sku }}
                                </div>
                            @endif
                            
                            @if(product.categories)
                                <div class="meta-item">
                                    <strong>Categories:</strong>
                                    @foreach(product.categories as category)
                                        <a href="{{ route('categories.show', category.slug) }}">
                                            {{ category.name }}
                                        </a>@if(!loop.last), @endif
                                    @endforeach
                                </div>
                            @endif
                            
                            @if(product.tags)
                                <div class="meta-item">
                                    <strong>Tags:</strong>
                                    @foreach(product.tags as tag)
                                        <a href="{{ route('products.tagged', tag) }}" class="tag">
                                            {{ tag }}
                                        </a>
                                    @endforeach
                                </div>
                            @endif
                        </div>
                        
                        <!-- Social Sharing -->
                        <div class="social-share">
                            <span class="share-label">Share:</span>
                            <a href="https://facebook.com/sharer/sharer.php?u={{ urlencode(request.url) }}" 
                               target="_blank" class="social-link facebook">
                                <i class="icon-facebook"></i>
                            </a>
                            <a href="https://twitter.com/intent/tweet?url={{ urlencode(request.url) }}&text={{ urlencode(product.name) }}" 
                               target="_blank" class="social-link twitter">
                                <i class="icon-twitter"></i>
                            </a>
                            <a href="https://pinterest.com/pin/create/button/?url={{ urlencode(request.url) }}&media={{ urlencode(asset(product.featured_image)) }}&description={{ urlencode(product.name) }}" 
                               target="_blank" class="social-link pinterest">
                                <i class="icon-pinterest"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Product Tabs -->
            <div class="product-tabs">
                <div class="tab-nav">
                    <button class="tab-button active" data-tab="description">Description</button>
                    @if(product.specifications)
                        <button class="tab-button" data-tab="specifications">Specifications</button>
                    @endif
                    @if(product.review_count > 0)
                        <button class="tab-button" data-tab="reviews">
                            Reviews ({{ product.review_count }})
                        </button>
                    @endif
                    @if(product.shipping_info)
                        <button class="tab-button" data-tab="shipping">Shipping</button>
                    @endif
                </div>
                
                <div class="tab-content">
                    <div class="tab-pane active" id="description">
                        {!! product.full_description or product.description !!}
                    </div>
                    
                    @if(product.specifications)
                        <div class="tab-pane" id="specifications">
                            <table class="specifications-table">
                                @foreach(product.specifications as spec)
                                    <tr>
                                        <td class="spec-name">{{ spec.name }}</td>
                                        <td class="spec-value">{{ spec.value }}</td>
                                    </tr>
                                @endforeach
                            </table>
                        </div>
                    @endif
                    
                    @if(product.review_count > 0)
                        <div class="tab-pane" id="reviews">
                            @include('products.partials.reviews')
                        </div>
                    @endif
                    
                    @if(product.shipping_info)
                        <div class="tab-pane" id="shipping">
                            {!! product.shipping_info !!}
                        </div>
                    @endif
                </div>
            </div>
            
            <!-- Related Products -->
            @if(related_products)
                <div class="related-products">
                    <h2>Related Products</h2>
                    <div class="product-grid">
                        @foreach(related_products as related)
                            <div class="product-card">
                                <a href="{{ route('products.show', related.slug) }}">
                                    <img src="{{ asset(related.featured_image) }}" 
                                         alt="{{ related.name }}"
                                         loading="lazy">
                                    <h3>{{ related.name }}</h3>
                                    <div class="price">
                                        @if(related.sale_price and related.sale_price < related.price)
                                            <span class="sale-price">{{ related.sale_price | money }}</span>
                                            <span class="original-price">{{ related.price | money }}</span>
                                        @else
                                            <span class="regular-price">{{ related.price | money }}</span>
                                        @endif
                                    </div>
                                </a>
                            </div>
                        @endforeach
                    </div>
                </div>
            @endif
        </div>
    </div>
@endsection

@section('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Product gallery
            const thumbs = document.querySelectorAll('.thumb');
            const mainImage = document.querySelector('.main-image');
            
            thumbs.forEach(thumb => {
                thumb.addEventListener('click', function() {
                    thumbs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    mainImage.src = this.dataset.image;
                });
            });
            
            // Quantity controls
            const qtyDecrease = document.querySelector('.qty-decrease');
            const qtyIncrease = document.querySelector('.qty-increase');
            const qtyInput = document.querySelector('#quantity');
            
            qtyDecrease.addEventListener('click', function() {
                let value = parseInt(qtyInput.value);
                if (value > 1) {
                    qtyInput.value = value - 1;
                }
            });
            
            qtyIncrease.addEventListener('click', function() {
                let value = parseInt(qtyInput.value);
                let max = parseInt(qtyInput.max);
                if (value < max) {
                    qtyInput.value = value + 1;
                }
            });
            
            // Product tabs
            const tabButtons = document.querySelectorAll('.tab-button');
            const tabPanes = document.querySelectorAll('.tab-pane');
            
            tabButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const targetTab = this.dataset.tab;
                    
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    tabPanes.forEach(pane => pane.classList.remove('active'));
                    
                    this.classList.add('active');
                    document.getElementById(targetTab).classList.add('active');
                });
            });
            
            // Analytics tracking
            @if(config('analytics.gtag_id'))
                gtag('event', 'view_item', {
                    currency: '{{ currency }}',
                    value: {{ product.sale_price or product.price }},
                    items: [{
                        item_id: '{{ product.sku }}',
                        item_name: '{{ product.name }}',
                        category: '{{ product.categories[0].name if product.categories else '' }}',
                        quantity: 1,
                        price: {{ product.sale_price or product.price }}
                    }]
                });
            @endif
        });
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "products/show.blade.html", product_page)
        
        # Set up complex product context
        context: Dict[str, Any] = {
            'locale': 'en',
            'theme': 'light',
            'currency': 'USD',
            'free_shipping_threshold': 75,
            'search_query': '',
            'cart': {
                'item_count': 3,
                'total': 129.99
            },
            'product': {
                'id': 123,
                'name': 'Premium Wireless Headphones',
                'slug': 'premium-wireless-headphones',
                'description': 'Experience crystal-clear audio with our premium wireless headphones featuring active noise cancellation.',
                'full_description': '<p>Our premium wireless headphones deliver exceptional sound quality with deep bass and crystal-clear highs. Perfect for music lovers and professionals alike.</p>',
                'sku': 'PWH-001',
                'price': 199.99,
                'sale_price': 159.99,
                'price_per_unit': None,
                'unit_type': None,
                'in_stock': True,
                'max_quantity': 5,
                'stock': 15,
                'featured_image': 'products/headphones-main.jpg',
                'featured_image_large': 'products/headphones-main-large.jpg',
                'video_url': 'https://youtube.com/watch?v=example',
                'rating_average': 4.5,
                'review_count': 127,
                'brand': {
                    'name': 'AudioTech',
                    'slug': 'audiotech'
                },
                'categories': [
                    {'name': 'Electronics', 'slug': 'electronics'},
                    {'name': 'Audio', 'slug': 'audio'},
                    {'name': 'Headphones', 'slug': 'headphones'}
                ],
                'tags': ['wireless', 'bluetooth', 'noise-cancelling', 'premium'],
                'images': [
                    {
                        'url': 'products/headphones-1.jpg',
                        'large_url': 'products/headphones-1-large.jpg',
                        'thumb_url': 'products/headphones-1-thumb.jpg'
                    },
                    {
                        'url': 'products/headphones-2.jpg',
                        'large_url': 'products/headphones-2-large.jpg',
                        'thumb_url': 'products/headphones-2-thumb.jpg'
                    }
                ],
                'specifications': [
                    {'name': 'Driver Size', 'value': '40mm'},
                    {'name': 'Frequency Response', 'value': '20Hz - 20kHz'},
                    {'name': 'Battery Life', 'value': '30 hours'},
                    {'name': 'Charging Time', 'value': '2 hours'},
                    {'name': 'Weight', 'value': '250g'}
                ],
                'shipping_info': '<p>Free shipping on orders over $75. Express delivery available.</p>',
                'variants': [],
                'option_types': []
            },
            'related_products': [
                {
                    'name': 'Budget Wireless Earbuds',
                    'slug': 'budget-wireless-earbuds',
                    'featured_image': 'products/earbuds-main.jpg',
                    'price': 49.99,
                    'sale_price': None
                },
                {
                    'name': 'Pro Studio Headphones',
                    'slug': 'pro-studio-headphones',
                    'featured_image': 'products/studio-main.jpg',
                    'price': 299.99,
                    'sale_price': 249.99
                }
            ],
            'current_user': None,
            'request': {'url': 'https://example.com/products/premium-wireless-headphones'}
        }
        
        # Render the complex product page
        result = engine.render("products/show.blade.html", context)
        
        # Verify complex template features
        assert "Premium Wireless Headphones" in result
        assert "AudioTech" in result
        assert "$159.99" in result
        assert "$199.99" in result
        assert "Save 20%" in result
        
        # Verify breadcrumbs
        assert "Electronics" in result
        assert "Audio" in result
        assert "Headphones" in result
        
        # Verify product gallery
        assert "headphones-main.jpg" in result
        assert "headphones-1.jpg" in result
        assert "data-zoom" in result
        
        # Verify ratings
        assert "4.5" in result or "★" in result
        assert "127" in result
        assert "reviews" in result
        
        # Verify specifications
        assert "40mm" in result
        assert "20Hz - 20kHz" in result
        assert "30 hours" in result
        
        # Verify social sharing
        assert "facebook.com/sharer" in result
        assert "twitter.com/intent" in result
        assert "pinterest.com/pin" in result
        
        # Verify related products
        assert "Budget Wireless Earbuds" in result
        assert "Pro Studio Headphones" in result
        assert "$49.99" in result
        assert "$249.99" in result
        
        # Verify JavaScript functionality
        assert "view_item" in result
        assert "gtag" in result
        assert "addEventListener" in result
        
        # Verify schema markup
        assert '"@type": "Product"' in result
        assert '"availability"' in result
        
        # Verify meta tags
        assert 'property="og:title"' in result
        assert 'property="og:image"' in result
        assert 'itemscope itemtype="https://schema.org/BreadcrumbList"' in result

    def test_complex_form_with_validation(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex form with validation, conditional fields, and dynamic content"""
        engine, temp_dir = blade_engine
        
        # Complex form template
        form_content = """
@extends('layouts/app')

@section('title', 'User Registration')

@section('content')
    <div class="registration-form">
        <div class="container">
            <div class="form-header">
                <h1>Create Your Account</h1>
                <p>Join thousands of users already using our platform</p>
            </div>
            
            <form action="{{ route('register') }}" 
                  method="POST" 
                  class="multi-step-form"
                  enctype="multipart/form-data"
                  novalidate>
                @csrf
                
                <!-- Step Progress -->
                <div class="form-progress">
                    <div class="progress-steps">
                        @foreach(form_steps as step)
                            <div class="step @if(loop.index <= current_step) active @endif @if(loop.index < current_step) completed @endif">
                                <div class="step-number">{{ loop.index }}</div>
                                <div class="step-title">{{ step.title }}</div>
                            </div>
                        @endforeach
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ (current_step / (form_steps | length)) * 100 }}%"></div>
                    </div>
                </div>
                
                <!-- Step 1: Personal Information -->
                <div class="form-step @if(current_step == 1) active @endif" data-step="1">
                    <h2>Personal Information</h2>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="first_name" class="required">First Name</label>
                            <input type="text" 
                                   id="first_name" 
                                   name="first_name" 
                                   value="{{ old('first_name') }}"
                                   class="form-control @error('first_name') error @enderror"
                                   required>
                            @error('first_name')
                                <div class="error-message">{{ message }}</div>
                            @enderror
                        </div>
                        
                        <div class="form-group">
                            <label for="last_name" class="required">Last Name</label>
                            <input type="text" 
                                   id="last_name" 
                                   name="last_name" 
                                   value="{{ old('last_name') }}"
                                   class="form-control @error('last_name') error @enderror"
                                   required>
                            @error('last_name')
                                <div class="error-message">{{ message }}</div>
                            @enderror
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="email" class="required">Email Address</label>
                        <input type="email" 
                               id="email" 
                               name="email" 
                               value="{{ old('email') }}"
                               class="form-control @error('email') error @enderror"
                               required>
                        @error('email')
                            <div class="error-message">{{ message }}</div>
                        @enderror
                        <div class="field-hint">We'll use this for important account notifications</div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="phone">Phone Number</label>
                            <div class="input-group">
                                <select name="country_code" class="country-select">
                                    @foreach(countries as country)
                                        <option value="{{ country.code }}" 
                                                @if(country.code == (old('country_code') or default_country)) selected @endif>
                                            {{ country.flag }} +{{ country.dial_code }}
                                        </option>
                                    @endforeach
                                </select>
                                <input type="tel" 
                                       id="phone" 
                                       name="phone" 
                                       value="{{ old('phone') }}"
                                       class="form-control"
                                       placeholder="123 456 7890">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="birth_date">Date of Birth</label>
                            <input type="date" 
                                   id="birth_date" 
                                   name="birth_date" 
                                   value="{{ old('birth_date') }}"
                                   class="form-control"
                                   max="{{ date('Y-m-d', strtotime('-13 years')) }}">
                        </div>
                    </div>
                </div>
                
                <!-- Step 2: Account Security -->
                <div class="form-step @if(current_step == 2) active @endif" data-step="2">
                    <h2>Account Security</h2>
                    
                    <div class="form-group">
                        <label for="password" class="required">Password</label>
                        <div class="password-input">
                            <input type="password" 
                                   id="password" 
                                   name="password" 
                                   class="form-control @error('password') error @enderror"
                                   required>
                            <button type="button" class="password-toggle" data-target="password">
                                <i class="icon-eye"></i>
                            </button>
                        </div>
                        @error('password')
                            <div class="error-message">{{ message }}</div>
                        @enderror
                        
                        <div class="password-strength">
                            <div class="strength-meter">
                                <div class="strength-fill"></div>
                            </div>
                            <div class="strength-text">Password strength: <span class="strength-level">Weak</span></div>
                        </div>
                        
                        <div class="password-requirements">
                            <div class="requirement" data-requirement="length">
                                <i class="icon-check"></i> At least 8 characters
                            </div>
                            <div class="requirement" data-requirement="uppercase">
                                <i class="icon-check"></i> One uppercase letter
                            </div>
                            <div class="requirement" data-requirement="lowercase">
                                <i class="icon-check"></i> One lowercase letter
                            </div>
                            <div class="requirement" data-requirement="number">
                                <i class="icon-check"></i> One number
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="password_confirmation" class="required">Confirm Password</label>
                        <div class="password-input">
                            <input type="password" 
                                   id="password_confirmation" 
                                   name="password_confirmation" 
                                   class="form-control @error('password_confirmation') error @enderror"
                                   required>
                            <button type="button" class="password-toggle" data-target="password_confirmation">
                                <i class="icon-eye"></i>
                            </button>
                        </div>
                        @error('password_confirmation')
                            <div class="error-message">{{ message }}</div>
                        @enderror
                    </div>
                    
                    @if(config('features.two_factor_auth'))
                        <div class="form-group">
                            <label class="checkbox-label">
                                <input type="checkbox" 
                                       name="enable_2fa" 
                                       value="1" 
                                       @if(old('enable_2fa')) checked @endif>
                                <span class="checkmark"></span>
                                Enable Two-Factor Authentication
                            </label>
                            <div class="field-hint">
                                Adds an extra layer of security to your account
                            </div>
                        </div>
                    @endif
                </div>
                
                <!-- Step 3: Profile & Preferences -->
                <div class="form-step @if(current_step == 3) active @endif" data-step="3">
                    <h2>Profile & Preferences</h2>
                    
                    <div class="form-group">
                        <label for="avatar">Profile Picture</label>
                        <div class="file-upload">
                            <div class="upload-area" id="avatar-upload">
                                <div class="upload-content">
                                    <i class="icon-upload"></i>
                                    <p>Drag & drop your photo here or <button type="button" class="upload-button">browse</button></p>
                                    <small>JPG, PNG or GIF (max 5MB)</small>
                                </div>
                                <input type="file" 
                                       id="avatar" 
                                       name="avatar" 
                                       accept="image/*"
                                       class="file-input">
                            </div>
                            <div class="file-preview" style="display: none;">
                                <img class="preview-image" alt="Preview">
                                <button type="button" class="remove-file">&times;</button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="bio">Bio</label>
                        <textarea id="bio" 
                                  name="bio" 
                                  class="form-control" 
                                  rows="4" 
                                  maxlength="500" 
                                  placeholder="Tell us a little about yourself...">{{ old('bio') }}</textarea>
                        <div class="character-count">
                            <span class="current">0</span>/<span class="max">500</span> characters
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="timezone">Timezone</label>
                            <select id="timezone" name="timezone" class="form-control">
                                @foreach(timezones as timezone)
                                    <option value="{{ timezone.value }}" 
                                            @if(timezone.value == (old('timezone') or user_timezone)) selected @endif>
                                        {{ timezone.label }}
                                    </option>
                                @endforeach
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="language">Preferred Language</label>
                            <select id="language" name="language" class="form-control">
                                @foreach(languages as language)
                                    <option value="{{ language.code }}" 
                                            @if(language.code == (old('language') or default_language)) selected @endif>
                                        {{ language.flag }} {{ language.name }}
                                    </option>
                                @endforeach
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Interests</label>
                        <div class="interest-tags">
                            @foreach(interests as interest)
                                <label class="tag-label">
                                    <input type="checkbox" 
                                           name="interests[]" 
                                           value="{{ interest.id }}"
                                           @if(old('interests') and interest.id in old('interests')) checked @endif>
                                    <span class="tag">{{ interest.name }}</span>
                                </label>
                            @endforeach
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Newsletter Preferences</label>
                        <div class="newsletter-options">
                            @foreach(newsletter_types as newsletter)
                                <label class="checkbox-label">
                                    <input type="checkbox" 
                                           name="newsletters[]" 
                                           value="{{ newsletter.id }}"
                                           @if(newsletter.default or (old('newsletters') and newsletter.id in old('newsletters'))) checked @endif>
                                    <span class="checkmark"></span>
                                    <div class="newsletter-info">
                                        <strong>{{ newsletter.name }}</strong>
                                        <p>{{ newsletter.description }}</p>
                                        <small>{{ newsletter.frequency }}</small>
                                    </div>
                                </label>
                            @endforeach
                        </div>
                    </div>
                </div>
                
                <!-- Terms & Submit -->
                <div class="form-footer">
                    @if(current_step == (form_steps | length))
                        <div class="form-group">
                            <label class="checkbox-label required">
                                <input type="checkbox" 
                                       name="terms_accepted" 
                                       value="1" 
                                       required
                                       @if(old('terms_accepted')) checked @endif>
                                <span class="checkmark"></span>
                                I agree to the 
                                <a href="{{ route('terms') }}" target="_blank">Terms of Service</a> 
                                and 
                                <a href="{{ route('privacy') }}" target="_blank">Privacy Policy</a>
                            </label>
                        </div>
                        
                        @if(config('features.marketing_consent'))
                            <div class="form-group">
                                <label class="checkbox-label">
                                    <input type="checkbox" 
                                           name="marketing_consent" 
                                           value="1"
                                           @if(old('marketing_consent')) checked @endif>
                                    <span class="checkmark"></span>
                                    I consent to receive marketing communications
                                </label>
                                <div class="field-hint">
                                    You can unsubscribe at any time. See our 
                                    <a href="{{ route('privacy') }}">Privacy Policy</a> for details.
                                </div>
                            </div>
                        @endif
                    @endif
                    
                    <div class="form-actions">
                        @if(current_step > 1)
                            <button type="button" class="btn btn-outline btn-prev">
                                <i class="icon-arrow-left"></i>
                                Previous
                            </button>
                        @endif
                        
                        @if(current_step < (form_steps | length))
                            <button type="button" class="btn btn-primary btn-next">
                                Next
                                <i class="icon-arrow-right"></i>
                            </button>
                        @else
                            <button type="submit" class="btn btn-primary btn-submit">
                                <i class="icon-check"></i>
                                Create Account
                            </button>
                        @endif
                    </div>
                </div>
            </form>
            
            <div class="form-help">
                <p>Already have an account? <a href="{{ route('login') }}">Sign in</a></p>
                <p>Need help? <a href="{{ route('support') }}">Contact Support</a></p>
            </div>
        </div>
    </div>
@endsection

@section('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Multi-step form logic
            let currentStep = {{ current_step }};
            const totalSteps = {{ form_steps | length }};
            
            // Password strength checker
            const passwordInput = document.getElementById('password');
            const strengthMeter = document.querySelector('.strength-fill');
            const strengthText = document.querySelector('.strength-level');
            const requirements = document.querySelectorAll('.requirement');
            
            passwordInput.addEventListener('input', function() {
                checkPasswordStrength(this.value);
            });
            
            function checkPasswordStrength(password) {
                let score = 0;
                const checks = {
                    length: password.length >= 8,
                    uppercase: /[A-Z]/.test(password),
                    lowercase: /[a-z]/.test(password),
                    number: /\\d/.test(password)
                };
                
                Object.keys(checks).forEach(key => {
                    const requirement = document.querySelector(`[data-requirement="${key}"]`);
                    if (checks[key]) {
                        requirement.classList.add('met');
                        score++;
                    } else {
                        requirement.classList.remove('met');
                    }
                });
                
                const strength = ['Weak', 'Fair', 'Good', 'Strong'][Math.min(score, 3)];
                const colors = ['#ff4444', '#ffaa00', '#00aa00', '#006600'];
                
                strengthMeter.style.width = `${(score / 4) * 100}%`;
                strengthMeter.style.backgroundColor = colors[Math.min(score, 3)];
                strengthText.textContent = strength;
                strengthText.className = `strength-level ${strength.toLowerCase()}`;
            }
            
            // File upload handling
            const fileUpload = document.getElementById('avatar-upload');
            const fileInput = document.getElementById('avatar');
            const filePreview = document.querySelector('.file-preview');
            const previewImage = document.querySelector('.preview-image');
            
            fileUpload.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.classList.add('dragover');
            });
            
            fileUpload.addEventListener('dragleave', function() {
                this.classList.remove('dragover');
            });
            
            fileUpload.addEventListener('drop', function(e) {
                e.preventDefault();
                this.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileSelect(files[0]);
                }
            });
            
            fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    handleFileSelect(this.files[0]);
                }
            });
            
            function handleFileSelect(file) {
                if (file.type.startsWith('image/') && file.size <= 5 * 1024 * 1024) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewImage.src = e.target.result;
                        fileUpload.style.display = 'none';
                        filePreview.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                } else {
                    alert('Please select a valid image file (max 5MB)');
                }
            }
            
            // Character counter
            const bioTextarea = document.getElementById('bio');
            const charCurrent = document.querySelector('.character-count .current');
            
            bioTextarea.addEventListener('input', function() {
                charCurrent.textContent = this.value.length;
            });
            
            // Form validation
            const form = document.querySelector('.multi-step-form');
            form.addEventListener('submit', function(e) {
                if (!validateCurrentStep()) {
                    e.preventDefault();
                }
            });
            
            function validateCurrentStep() {
                const currentStepElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
                const requiredFields = currentStepElement.querySelectorAll('[required]');
                let isValid = true;
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        field.classList.add('error');
                        isValid = false;
                    } else {
                        field.classList.remove('error');
                    }
                });
                
                return isValid;
            }
            
            console.log('Registration form initialized with {{ form_steps | length }} steps');
        });
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "auth/register.blade.html", form_content)
        
        # Complex form context
        context: Dict[str, Any] = {
            'current_step': 2,
            'form_steps': [
                {'title': 'Personal Info'},
                {'title': 'Security'},
                {'title': 'Profile'}
            ],
            'countries': [
                {'code': 'US', 'dial_code': '1', 'flag': '🇺🇸'},
                {'code': 'CA', 'dial_code': '1', 'flag': '🇨🇦'},
                {'code': 'UK', 'dial_code': '44', 'flag': '🇬🇧'}
            ],
            'default_country': 'US',
            'timezones': [
                {'value': 'America/New_York', 'label': '(UTC-05:00) Eastern Time'},
                {'value': 'America/Chicago', 'label': '(UTC-06:00) Central Time'},
                {'value': 'America/Denver', 'label': '(UTC-07:00) Mountain Time'},
                {'value': 'America/Los_Angeles', 'label': '(UTC-08:00) Pacific Time'}
            ],
            'user_timezone': 'America/New_York',
            'languages': [
                {'code': 'en', 'name': 'English', 'flag': '🇺🇸'},
                {'code': 'es', 'name': 'Español', 'flag': '🇪🇸'},
                {'code': 'fr', 'name': 'Français', 'flag': '🇫🇷'}
            ],
            'default_language': 'en',
            'interests': [
                {'id': 1, 'name': 'Technology'},
                {'id': 2, 'name': 'Travel'},
                {'id': 3, 'name': 'Food'},
                {'id': 4, 'name': 'Sports'},
                {'id': 5, 'name': 'Music'}
            ],
            'newsletter_types': [
                {
                    'id': 1,
                    'name': 'Weekly Newsletter',
                    'description': 'Get the latest updates and features',
                    'frequency': 'Weekly',
                    'default': True
                },
                {
                    'id': 2,
                    'name': 'Product Updates',
                    'description': 'New features and improvements',
                    'frequency': 'Monthly',
                    'default': False
                }
            ],
            'errors': {
                'first_name': 'First name is required',
                'email': 'Email address is already taken'
            }
        }
        
        # Add old input simulation
        def old(key: str, default: Any = None) -> Any:
            old_data = {
                'first_name': 'John',
                'email': 'john@example.com',
                'country_code': 'US',
                'enable_2fa': True,
                'interests': [1, 3, 5]
            }
            return old_data.get(key, default)
        
        def error(field: str) -> bool:
            return field in context['errors']
        
        # Add template helpers
        context['old'] = old
        engine.env.globals['old'] = old
        
        # Define error helper as a function that returns a context manager-like object
        class ErrorContext:
            def __init__(self, field: str, errors: Dict[str, str]):
                self.field = field
                self.errors = errors
                
            def __bool__(self) -> bool:
                return self.field in self.errors
                
            @property  
            def message(self) -> str:
                return self.errors.get(self.field, '')
        
        def make_error_helper(errors: Dict[str, str]) -> Any:
            def error_helper(field: str) -> ErrorContext:
                return ErrorContext(field, errors)
            return error_helper
        
        engine.env.globals['error'] = make_error_helper(context['errors'])
        
        # Render complex form
        result = engine.render("auth/register.blade.html", context)
        
        # Verify complex form features
        assert "Create Your Account" in result
        assert "multi-step-form" in result
        assert "Step 2" in result or "Security" in result
        
        # Verify progress indicator
        assert "width: 66" in result  # 2/3 steps completed
        
        # Verify form fields with old values
        assert 'value="John"' in result
        assert 'value="john@example.com"' in result
        
        # Verify error handling
        assert "First name is required" in result
        assert "Email address is already taken" in result
        assert "form-control error" in result
        
        # Verify country selection
        assert "🇺🇸 +1" in result
        assert "🇨🇦 +1" in result
        assert "🇬🇧 +44" in result
        
        # Verify password requirements
        assert "At least 8 characters" in result
        assert "One uppercase letter" in result
        assert "password-strength" in result
        
        # Verify interests checkboxes
        assert "Technology" in result
        assert "Travel" in result
        assert 'name="interests[]"' in result
        
        # Verify newsletter options
        assert "Weekly Newsletter" in result
        assert "Product Updates" in result
        
        # Verify JavaScript functionality
        assert "checkPasswordStrength" in result
        assert "validateCurrentStep" in result
        assert "handleFileSelect" in result
        assert "addEventListener" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])