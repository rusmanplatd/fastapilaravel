"""
Advanced Blade Template Engine Test Scenarios
Tests real-world complex scenarios combining multiple Blade features
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List, Optional

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


class TestAdvancedBladeScenarios:
    """Advanced real-world Blade template scenarios"""
    
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
    
    def test_dashboard_with_components_and_permissions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex dashboard with multiple components and permission checks"""
        engine, temp_dir = blade_engine
        
        # Base layout
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Dashboard')</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
    @yield('styles')
</head>
<body>
    <div class="app">
        @yield('content')
    </div>
    @yield('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", layout_content)
        
        # Dashboard template
        dashboard_content = """
@extends('layouts/app')

@section('title', 'Admin Dashboard')

@section('content')
    <div class="dashboard">
        <header class="dashboard-header">
            <h1>Welcome back, {{ current_user.name }}!</h1>
            
            @can('view-notifications')
                <div class="notifications">
                    <i class="bell"></i>
                    @if(notification_count > 0)
                        <span class="badge">{{ notification_count }}</span>
                    @endif
                </div>
            @endcan
        </header>
        
        <!-- Stats Cards -->
        <div class="stats-grid">
            @foreach(dashboard_stats as stat)
                @can(stat.permission)
                    <div class="stat-card {{ stat.type }}">
                        <div class="stat-icon">
                            <i class="icon-{{ stat.icon }}"></i>
                        </div>
                        <div class="stat-content">
                            <h3>{{ stat.title }}</h3>
                            <div class="stat-value">
                                {{ stat.value | number_format }}
                                @if(stat.change)
                                    <span class="change {{ stat.change > 0 ? 'positive' : 'negative' }}">
                                        {{ stat.change > 0 ? '+' : '' }}{{ stat.change }}%
                                    </span>
                                @endif
                            </div>
                            @if(stat.subtitle)
                                <p class="stat-subtitle">{{ stat.subtitle }}</p>
                            @endif
                        </div>
                    </div>
                @endcan
            @endforeach
        </div>
        
        <!-- Activity Feed -->
        @if(recent_activities)
            <div class="activity-section">
                <div class="section-header">
                    <h2>Recent Activity</h2>
                    @can('view-all-activity')
                        <a href="{{ route('activity.all') }}" class="view-all">View All</a>
                    @endcan
                </div>
                
                <div class="activity-feed">
                    @foreach(recent_activities as activity)
                        <div class="activity-item">
                            <div class="activity-avatar">
                                @if(activity.user.avatar)
                                    <img src="{{ activity.user.avatar }}" alt="{{ activity.user.name }}">
                                @else
                                    <div class="avatar-placeholder">
                                        {{ activity.user.name | slice(0, 1) | upper }}
                                    </div>
                                @endif
                            </div>
                            
                            <div class="activity-content">
                                <div class="activity-text">
                                    <strong>{{ activity.user.name }}</strong>
                                    {{ activity.description }}
                                    @if(activity.target)
                                        <em>"{{ activity.target | truncate(30) }}"</em>
                                    @endif
                                </div>
                                <div class="activity-meta">
                                    <time>{{ activity.created_at | date('M j, g:i A') }}</time>
                                    @if(activity.location)
                                        <span class="location">{{ activity.location }}</span>
                                    @endif
                                </div>
                            </div>
                            
                            @if(activity.status)
                                <div class="activity-status">
                                    <span class="status-{{ activity.status }}">
                                        {{ activity.status | title }}
                                    </span>
                                </div>
                            @endif
                        </div>
                    @endforeach
                </div>
            </div>
        @endif
        
        <!-- Quick Actions -->
        @hasrole('admin')
            <div class="quick-actions">
                <h2>Quick Actions</h2>
                <div class="action-grid">
                    @foreach(quick_actions as action)
                        @can(action.permission)
                            <a href="{{ route(action.route) }}" 
                               class="action-card {{ action.primary ? 'primary' : '' }}">
                                <i class="icon-{{ action.icon }}"></i>
                                <h3>{{ action.title }}</h3>
                                <p>{{ action.description }}</p>
                                @if(action.count)
                                    <div class="action-count">{{ action.count }}</div>
                                @endif
                            </a>
                        @endcan
                    @endforeach
                </div>
            </div>
        @endhasrole
        
        <!-- System Health -->
        @hasrole('super-admin')
            <div class="system-health">
                <h2>System Health</h2>
                <div class="health-checks">
                    @foreach(system_checks as check)
                        <div class="health-item {{ check.status }}">
                            <div class="health-indicator">
                                @if(check.status == 'healthy')
                                    <i class="icon-check-circle text-success"></i>
                                @elseif(check.status == 'warning')
                                    <i class="icon-warning text-warning"></i>
                                @else
                                    <i class="icon-error text-danger"></i>
                                @endif
                            </div>
                            
                            <div class="health-details">
                                <h4>{{ check.name }}</h4>
                                <p>{{ check.message }}</p>
                                @if(check.last_checked)
                                    <small>Last checked: {{ check.last_checked | timeago }}</small>
                                @endif
                            </div>
                            
                            @if(check.metrics)
                                <div class="health-metrics">
                                    @foreach(check.metrics as metric)
                                        <span class="metric">
                                            {{ metric.name }}: {{ metric.value }}
                                        </span>
                                    @endforeach
                                </div>
                            @endif
                        </div>
                    @endforeach
                </div>
            </div>
        @endhasrole
    </div>
@endsection

@section('styles')
    <style>
        .dashboard { padding: 2rem; }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
            gap: 1.5rem; 
            margin: 2rem 0; 
        }
        .stat-card { 
            background: white; 
            padding: 1.5rem; 
            border-radius: 8px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
        }
        .stat-card.revenue { border-left: 4px solid #10b981; }
        .stat-card.users { border-left: 4px solid #3b82f6; }
        .stat-card.orders { border-left: 4px solid #f59e0b; }
        .activity-feed { max-height: 400px; overflow-y: auto; }
        .action-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
        .action-card.primary { background: #3b82f6; color: white; }
    </style>
@endsection

@section('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-refresh dashboard stats
            @if(config('dashboard.auto_refresh'))
                setInterval(function() {
                    fetch('{{ route("dashboard.refresh") }}')
                        .then(response => response.json())
                        .then(data => updateDashboard(data))
                        .catch(console.error);
                }, {{ config('dashboard.refresh_interval', 30000) }});
            @endif
            
            // Initialize tooltips for health checks
            document.querySelectorAll('.health-item').forEach(function(item) {
                item.addEventListener('mouseover', function() {
                    // Show detailed health info
                });
            });
            
            // Track dashboard views
            fetch('{{ route("analytics.track") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({
                    event: 'dashboard_view',
                    user_id: {{ current_user.id }},
                    timestamp: new Date().toISOString()
                })
            });
            
            console.log('Dashboard initialized for user: {{ current_user.name }}');
        });
        
        function updateDashboard(data) {
            // Update stats dynamically
            @foreach(dashboard_stats as stat)
                const statCard{{ loop.index }} = document.querySelector('.stat-card:nth-child({{ loop.index }}) .stat-value');
                if (statCard{{ loop.index }} && data.stats[{{ loop.index - 1 }}]) {
                    statCard{{ loop.index }}.textContent = data.stats[{{ loop.index - 1 }}].value.toLocaleString();
                }
            @endforeach
        }
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "dashboard.blade.html", dashboard_content)
        
        # Create complex context
        admin_user = MockUser({
            'id': 1,
            'name': 'John Administrator',
            'email': 'admin@example.com',
            'avatar': '/avatars/admin.jpg',
            'roles': ['admin', 'super-admin'],
            'permissions': ['view-notifications', 'view-all-activity', 'create-users', 'view-reports']
        })
        
        context: Dict[str, Any] = {
            'current_user': admin_user,
            'notification_count': 7,
            'dashboard_stats': [
                {
                    'title': 'Total Revenue',
                    'value': 125340,
                    'change': 15.3,
                    'type': 'revenue',
                    'icon': 'dollar',
                    'subtitle': 'This month',
                    'permission': 'view-revenue'
                },
                {
                    'title': 'Active Users',
                    'value': 8429,
                    'change': -2.1,
                    'type': 'users',
                    'icon': 'users',
                    'subtitle': 'Last 30 days',
                    'permission': 'view-users'
                },
                {
                    'title': 'Orders',
                    'value': 1876,
                    'change': 8.7,
                    'type': 'orders',
                    'icon': 'shopping',
                    'subtitle': 'This week',
                    'permission': 'view-orders'
                }
            ],
            'recent_activities': [
                {
                    'user': {
                        'name': 'Sarah Johnson',
                        'avatar': '/avatars/sarah.jpg'
                    },
                    'description': 'created a new post',
                    'target': 'Getting Started with FastAPI and Blade Templates',
                    'created_at': '2025-01-15T14:30:00Z',
                    'location': 'New York',
                    'status': 'success'
                },
                {
                    'user': {
                        'name': 'Mike Chen',
                        'avatar': None
                    },
                    'description': 'updated user permissions for',
                    'target': 'jane.smith@example.com',
                    'created_at': '2025-01-15T13:45:00Z',
                    'location': 'San Francisco',
                    'status': 'info'
                },
                {
                    'user': {
                        'name': 'Emily Rodriguez',
                        'avatar': '/avatars/emily.jpg'
                    },
                    'description': 'deleted expired sessions',
                    'target': None,
                    'created_at': '2025-01-15T12:15:00Z',
                    'location': 'Remote',
                    'status': 'warning'
                }
            ],
            'quick_actions': [
                {
                    'title': 'Create User',
                    'description': 'Add a new user to the system',
                    'route': 'admin.users.create',
                    'icon': 'user-plus',
                    'permission': 'create-users',
                    'primary': True,
                    'count': None
                },
                {
                    'title': 'View Reports',
                    'description': 'Access analytics and reports',
                    'route': 'admin.reports.index',
                    'icon': 'chart-bar',
                    'permission': 'view-reports',
                    'primary': False,
                    'count': 23
                },
                {
                    'title': 'System Logs',
                    'description': 'Review system activity logs',
                    'route': 'admin.logs.index',
                    'icon': 'document-text',
                    'permission': 'view-logs',
                    'primary': False,
                    'count': 156
                }
            ],
            'system_checks': [
                {
                    'name': 'Database Performance',
                    'status': 'healthy',
                    'message': 'All queries executing within acceptable limits',
                    'last_checked': '2025-01-15T15:00:00Z',
                    'metrics': [
                        {'name': 'Avg Query Time', 'value': '45ms'},
                        {'name': 'Active Connections', 'value': '23/100'}
                    ]
                },
                {
                    'name': 'Cache System',
                    'status': 'warning',
                    'message': 'Hit rate below optimal threshold',
                    'last_checked': '2025-01-15T15:00:00Z',
                    'metrics': [
                        {'name': 'Hit Rate', 'value': '72%'},
                        {'name': 'Memory Usage', 'value': '256MB/512MB'}
                    ]
                },
                {
                    'name': 'Storage Space',
                    'status': 'healthy',
                    'message': 'Sufficient storage available',
                    'last_checked': '2025-01-15T15:00:00Z',
                    'metrics': [
                        {'name': 'Used', 'value': '45%'},
                        {'name': 'Available', 'value': '2.1TB'}
                    ]
                }
            ],
            'config': lambda key, default=None: {
                'dashboard.auto_refresh': True,
                'dashboard.refresh_interval': 30000
            }.get(key, default)
        }
        
        # Add necessary template globals
        engine.env.globals['config'] = context['config']
        engine.env.filters['number_format'] = lambda x: f"{x:,}" if isinstance(x, (int, float)) else x
        engine.env.filters['truncate'] = lambda s, length=50: s[:length] + '...' if len(s) > length else s
        engine.env.filters['date'] = lambda d, fmt: d  # Simplified date filter
        engine.env.filters['timeago'] = lambda d: '2 minutes ago'  # Simplified timeago
        engine.env.filters['slice'] = lambda s, start, end: s[start:end] if s else ''
        
        # Render complex dashboard
        result = engine.render("dashboard.blade.html", context)
        
        # Verify complex features
        assert "Welcome back, John Administrator!" in result
        assert '<span class="badge">7</span>' in result
        
        # Verify stats with formatting
        assert "125,340" in result
        assert "+15.3%" in result
        assert "-2.1%" in result
        assert "8,429" in result
        assert "1,876" in result
        
        # Verify activity feed
        assert "Sarah Johnson" in result
        assert "Mike Chen" in result
        assert "Emily Rodriguez" in result
        assert "Getting Started with FastAPI" in result
        assert "updated user permissions" in result
        
        # Verify quick actions (admin role)
        assert "Create User" in result
        assert "View Reports" in result
        assert "System Logs" in result
        assert "action-card primary" in result
        
        # Verify system health (super-admin role)
        assert "System Health" in result
        assert "Database Performance" in result
        assert "Cache System" in result
        assert "Storage Space" in result
        assert "Hit Rate: 72%" in result
        assert "2.1TB" in result
        
        # Verify CSS styling
        assert ".stats-grid" in result
        assert "grid-template-columns" in result
        assert ".stat-card.revenue" in result
        
        # Verify JavaScript functionality
        assert "updateDashboard" in result
        assert "dashboard_view" in result
        assert "John Administrator" in result
        assert "setInterval" in result
    
    def test_ecommerce_product_listing_with_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex e-commerce product listing with filters and sorting"""
        engine, temp_dir = blade_engine
        
        # Product listing template
        listing_content = """
<div class="product-listing">
    <div class="listing-header">
        <h1>{{ category.name or 'All Products' }}</h1>
        <div class="results-info">
            Showing {{ products | length }} of {{ total_products }} products
            @if(search_query)
                for "{{ search_query }}"
            @endif
            @if(active_filters)
                with filters: 
                @foreach(active_filters as filter)
                    <span class="filter-tag">
                        {{ filter.name }}: {{ filter.value }}
                        <a href="{{ filter.remove_url }}">&times;</a>
                    </span>
                @endforeach
            @endif
        </div>
    </div>
    
    <div class="listing-controls">
        <!-- Sorting -->
        <div class="sort-options">
            <label for="sort">Sort by:</label>
            <select id="sort" name="sort" onchange="updateSort(this.value)">
                @foreach(sort_options as option)
                    <option value="{{ option.value }}" 
                            @if(option.value == current_sort) selected @endif>
                        {{ option.label }}
                    </option>
                @endforeach
            </select>
        </div>
        
        <!-- View Toggle -->
        <div class="view-toggle">
            <button class="view-btn @if(view_mode == 'grid') active @endif" 
                    data-view="grid">
                <i class="icon-grid"></i>
            </button>
            <button class="view-btn @if(view_mode == 'list') active @endif" 
                    data-view="list">
                <i class="icon-list"></i>
            </button>
        </div>
    </div>
    
    <div class="listing-content">
        <!-- Filters Sidebar -->
        <aside class="filters-sidebar">
            <h3>Filters</h3>
            
            <!-- Price Filter -->
            <div class="filter-group">
                <h4>Price Range</h4>
                <div class="price-filter">
                    <input type="range" 
                           id="price-min" 
                           min="{{ price_range.min }}" 
                           max="{{ price_range.max }}" 
                           value="{{ price_filter.min or price_range.min }}">
                    <input type="range" 
                           id="price-max" 
                           min="{{ price_range.min }}" 
                           max="{{ price_range.max }}" 
                           value="{{ price_filter.max or price_range.max }}">
                    <div class="price-display">
                        $<span id="price-min-display">{{ price_filter.min or price_range.min }}</span>
                        -
                        $<span id="price-max-display">{{ price_filter.max or price_range.max }}</span>
                    </div>
                </div>
            </div>
            
            <!-- Category Filter -->
            @if(categories)
                <div class="filter-group">
                    <h4>Categories</h4>
                    <ul class="category-filter">
                        @foreach(categories as cat)
                            <li>
                                <label class="filter-checkbox">
                                    <input type="checkbox" 
                                           name="categories[]" 
                                           value="{{ cat.id }}"
                                           @if(cat.id in selected_categories) checked @endif
                                           onchange="updateFilters()">
                                    <span class="checkmark"></span>
                                    {{ cat.name }}
                                    <span class="count">({{ cat.product_count }})</span>
                                </label>
                            </li>
                        @endforeach
                    </ul>
                </div>
            @endif
            
            <!-- Brand Filter -->
            @if(brands)
                <div class="filter-group">
                    <h4>Brands</h4>
                    <div class="brand-filter">
                        @foreach(brands as brand)
                            <label class="filter-checkbox">
                                <input type="checkbox" 
                                       name="brands[]" 
                                       value="{{ brand.id }}"
                                       @if(brand.id in selected_brands) checked @endif
                                       onchange="updateFilters()">
                                <span class="checkmark"></span>
                                {{ brand.name }}
                                <span class="count">({{ brand.product_count }})</span>
                            </label>
                        @endforeach
                    </div>
                </div>
            @endif
            
            <!-- Rating Filter -->
            <div class="filter-group">
                <h4>Rating</h4>
                <div class="rating-filter">
                    @for(rating = 5; rating >= 1; rating--)
                        <label class="rating-option">
                            <input type="radio" 
                                   name="min_rating" 
                                   value="{{ rating }}"
                                   @if(rating == min_rating) checked @endif
                                   onchange="updateFilters()">
                            <div class="stars">
                                @for(i = 1; i <= 5; i++)
                                    <i class="icon-star @if(i <= rating) filled @endif"></i>
                                @endfor
                            </div>
                            <span>{{ rating }} stars & up</span>
                        </label>
                    @endfor
                </div>
            </div>
            
            <!-- Clear Filters -->
            @if(has_active_filters)
                <div class="filter-actions">
                    <button type="button" 
                            class="clear-filters" 
                            onclick="clearAllFilters()">
                        Clear All Filters
                    </button>
                </div>
            @endif
        </aside>
        
        <!-- Products Grid/List -->
        <main class="products-main">
            @if(products)
                <div class="products-grid view-{{ view_mode }}">
                    @foreach(products as product)
                        <div class="product-card @if(product.on_sale) on-sale @endif @if(product.featured) featured @endif">
                            <div class="product-image">
                                <a href="{{ route('products.show', product.slug) }}">
                                    <img src="{{ asset(product.image) }}" 
                                         alt="{{ product.name }}"
                                         loading="@if(loop.index <= 6) eager @else lazy @endif">
                                </a>
                                
                                @if(product.on_sale)
                                    <span class="sale-badge">
                                        {{ product.discount_percentage }}% OFF
                                    </span>
                                @endif
                                
                                @if(product.featured)
                                    <span class="featured-badge">Featured</span>
                                @endif
                                
                                <div class="product-actions">
                                    <button class="quick-view" 
                                            data-product="{{ product.id }}"
                                            onclick="showQuickView({{ product.id }})">
                                        <i class="icon-eye"></i>
                                    </button>
                                    <button class="add-wishlist @if(product.in_wishlist) active @endif"
                                            data-product="{{ product.id }}"
                                            onclick="toggleWishlist({{ product.id }})">
                                        <i class="icon-heart"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <div class="product-info">
                                @if(product.brand)
                                    <div class="product-brand">
                                        <a href="{{ route('brands.show', product.brand.slug) }}">
                                            {{ product.brand.name }}
                                        </a>
                                    </div>
                                @endif
                                
                                <h3 class="product-name">
                                    <a href="{{ route('products.show', product.slug) }}">
                                        {{ product.name | truncate(50) }}
                                    </a>
                                </h3>
                                
                                @if(product.rating_average > 0)
                                    <div class="product-rating">
                                        <div class="stars">
                                            @for(i = 1; i <= 5; i++)
                                                <i class="icon-star @if(i <= product.rating_average) filled @endif"></i>
                                            @endfor
                                        </div>
                                        <span class="rating-text">
                                            {{ product.rating_average | number_format(1) }}
                                            ({{ product.review_count }})
                                        </span>
                                    </div>
                                @endif
                                
                                <div class="product-price">
                                    @if(product.on_sale)
                                        <span class="sale-price">{{ product.sale_price | money }}</span>
                                        <span class="original-price">{{ product.price | money }}</span>
                                    @else
                                        <span class="regular-price">{{ product.price | money }}</span>
                                    @endif
                                </div>
                                
                                @if(product.short_description)
                                    <p class="product-description">
                                        {{ product.short_description | truncate(100) }}
                                    </p>
                                @endif
                                
                                <div class="product-meta">
                                    @if(product.in_stock)
                                        <span class="stock-status in-stock">In Stock</span>
                                    @else
                                        <span class="stock-status out-of-stock">Out of Stock</span>
                                    @endif
                                    
                                    @if(product.free_shipping)
                                        <span class="shipping-info">Free Shipping</span>
                                    @endif
                                </div>
                                
                                <div class="product-actions-bottom">
                                    @if(product.in_stock)
                                        <button class="btn btn-primary add-to-cart" 
                                                data-product="{{ product.id }}"
                                                onclick="addToCart({{ product.id }})">
                                            <i class="icon-cart"></i>
                                            Add to Cart
                                        </button>
                                    @else
                                        <button class="btn btn-disabled" disabled>
                                            Out of Stock
                                        </button>
                                    @endif
                                </div>
                            </div>
                        </div>
                    @endforeach
                </div>
                
                <!-- Pagination -->
                @if(pagination.total_pages > 1)
                    <div class="pagination">
                        @if(pagination.current_page > 1)
                            <a href="{{ pagination.prev_url }}" class="page-btn prev">
                                <i class="icon-arrow-left"></i> Previous
                            </a>
                        @endif
                        
                        @foreach(pagination.pages as page)
                            @if(page.type == 'page')
                                <a href="{{ page.url }}" 
                                   class="page-btn @if(page.current) active @endif">
                                    {{ page.number }}
                                </a>
                            @elseif(page.type == 'dots')
                                <span class="page-dots">...</span>
                            @endif
                        @endforeach
                        
                        @if(pagination.current_page < pagination.total_pages)
                            <a href="{{ pagination.next_url }}" class="page-btn next">
                                Next <i class="icon-arrow-right"></i>
                            </a>
                        @endif
                    </div>
                @endif
            @else
                <div class="empty-results">
                    <div class="empty-icon">
                        <i class="icon-search"></i>
                    </div>
                    <h3>No products found</h3>
                    <p>
                        @if(search_query)
                            We couldn't find any products matching "{{ search_query }}".
                        @else
                            No products match your current filters.
                        @endif
                    </p>
                    <div class="empty-actions">
                        @if(has_active_filters)
                            <button class="btn btn-outline" onclick="clearAllFilters()">
                                Clear Filters
                            </button>
                        @endif
                        <a href="{{ route('products.index') }}" class="btn btn-primary">
                            View All Products
                        </a>
                    </div>
                </div>
            @endif
        </main>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Initialize filters
    const filters = {
        sort: '{{ current_sort }}',
        view: '{{ view_mode }}',
        categories: @json(selected_categories),
        brands: @json(selected_brands),
        minRating: {{ min_rating or 0 }},
        priceMin: {{ price_filter.min or price_range.min }},
        priceMax: {{ price_filter.max or price_range.max }}
    };
    
    // View toggle functionality
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.dataset.view;
            updateView(view);
        });
    });
    
    // Price range sliders
    const priceMinSlider = document.getElementById('price-min');
    const priceMaxSlider = document.getElementById('price-max');
    
    if (priceMinSlider && priceMaxSlider) {
        priceMinSlider.addEventListener('input', updatePriceDisplay);
        priceMaxSlider.addEventListener('input', updatePriceDisplay);
    }
    
    function updatePriceDisplay() {
        document.getElementById('price-min-display').textContent = priceMinSlider.value;
        document.getElementById('price-max-display').textContent = priceMaxSlider.value;
    }
    
    console.log('Product listing initialized with {{ products | length }} products');
});

function updateSort(sortValue) {
    const url = new URL(window.location);
    url.searchParams.set('sort', sortValue);
    window.location.href = url.toString();
}

function updateView(viewMode) {
    const url = new URL(window.location);
    url.searchParams.set('view', viewMode);
    window.location.href = url.toString();
}

function updateFilters() {
    // Collect all filter values and update URL
    const form = new FormData();
    
    document.querySelectorAll('input[name="categories[]"]:checked').forEach(cb => {
        form.append('categories[]', cb.value);
    });
    
    document.querySelectorAll('input[name="brands[]"]:checked').forEach(cb => {
        form.append('brands[]', cb.value);
    });
    
    const minRating = document.querySelector('input[name="min_rating"]:checked');
    if (minRating) {
        form.append('min_rating', minRating.value);
    }
    
    // Build URL and redirect
    const url = new URL(window.location);
    for (const [key, value] of form) {
        url.searchParams.append(key, value);
    }
    window.location.href = url.toString();
}

function clearAllFilters() {
    window.location.href = '{{ route("products.index") }}';
}

function addToCart(productId) {
    fetch('{{ route("cart.add") }}', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({
            product_id: productId,
            quantity: 1
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message or update cart count
            console.log('Added to cart:', data);
        }
    })
    .catch(console.error);
}

function toggleWishlist(productId) {
    // Wishlist toggle functionality
    console.log('Toggle wishlist for product:', productId);
}

function showQuickView(productId) {
    // Quick view modal functionality
    console.log('Show quick view for product:', productId);
}
</script>
        """.strip()
        self.create_template(temp_dir, "products/index.blade.html", listing_content)
        
        # Create complex product listing context
        context: Dict[str, Any] = {
            'category': {'name': 'Electronics'},
            'search_query': 'wireless',
            'total_products': 156,
            'current_sort': 'price_asc',
            'view_mode': 'grid',
            'sort_options': [
                {'value': 'newest', 'label': 'Newest First'},
                {'value': 'price_asc', 'label': 'Price: Low to High'},
                {'value': 'price_desc', 'label': 'Price: High to Low'},
                {'value': 'rating', 'label': 'Highest Rated'},
                {'value': 'popular', 'label': 'Most Popular'}
            ],
            'active_filters': [
                {
                    'name': 'Brand',
                    'value': 'Apple',
                    'remove_url': '/products?category=electronics'
                }
            ],
            'price_range': {'min': 10, 'max': 2000},
            'price_filter': {'min': 50, 'max': 500},
            'selected_categories': [1, 3],
            'selected_brands': [2],
            'min_rating': 4,
            'has_active_filters': True,
            'categories': [
                {'id': 1, 'name': 'Smartphones', 'product_count': 45},
                {'id': 2, 'name': 'Laptops', 'product_count': 32},
                {'id': 3, 'name': 'Accessories', 'product_count': 78}
            ],
            'brands': [
                {'id': 1, 'name': 'Apple', 'product_count': 23},
                {'id': 2, 'name': 'Samsung', 'product_count': 19},
                {'id': 3, 'name': 'Sony', 'product_count': 15}
            ],
            'products': [
                {
                    'id': 1,
                    'name': 'Wireless Bluetooth Headphones Premium',
                    'slug': 'wireless-bluetooth-headphones',
                    'image': 'products/headphones.jpg',
                    'brand': {'name': 'Sony', 'slug': 'sony'},
                    'price': 199.99,
                    'sale_price': 149.99,
                    'on_sale': True,
                    'discount_percentage': 25,
                    'featured': True,
                    'rating_average': 4.5,
                    'review_count': 128,
                    'short_description': 'Premium wireless headphones with noise cancellation',
                    'in_stock': True,
                    'free_shipping': True,
                    'in_wishlist': False
                },
                {
                    'id': 2,
                    'name': 'Smartphone Case Wireless Charging',
                    'slug': 'smartphone-case-wireless',
                    'image': 'products/case.jpg',
                    'brand': {'name': 'Apple', 'slug': 'apple'},
                    'price': 79.99,
                    'sale_price': None,
                    'on_sale': False,
                    'discount_percentage': 0,
                    'featured': False,
                    'rating_average': 4.2,
                    'review_count': 56,
                    'short_description': 'Wireless charging compatible smartphone case',
                    'in_stock': True,
                    'free_shipping': False,
                    'in_wishlist': True
                },
                {
                    'id': 3,
                    'name': 'Wireless Mouse Ultra Precision',
                    'slug': 'wireless-mouse-precision',
                    'image': 'products/mouse.jpg',
                    'brand': None,
                    'price': 29.99,
                    'sale_price': None,
                    'on_sale': False,
                    'discount_percentage': 0,
                    'featured': False,
                    'rating_average': 3.8,
                    'review_count': 34,
                    'short_description': 'Precision wireless mouse for professionals',
                    'in_stock': False,
                    'free_shipping': True,
                    'in_wishlist': False
                }
            ],
            'pagination': {
                'current_page': 2,
                'total_pages': 8,
                'prev_url': '/products?page=1',
                'next_url': '/products?page=3',
                'pages': [
                    {'type': 'page', 'number': 1, 'url': '/products?page=1', 'current': False},
                    {'type': 'page', 'number': 2, 'url': '/products?page=2', 'current': True},
                    {'type': 'page', 'number': 3, 'url': '/products?page=3', 'current': False},
                    {'type': 'dots'},
                    {'type': 'page', 'number': 8, 'url': '/products?page=8', 'current': False}
                ]
            }
        }
        
        # Add template filters
        engine.env.filters['money'] = lambda x: f"${x:.2f}" if x else "$0.00"
        engine.env.filters['truncate'] = lambda s, length=50: s[:length] + '...' if len(s) > length else s
        engine.env.filters['number_format'] = lambda x, decimals=0: f"{x:.{decimals}f}" if isinstance(x, (int, float)) else x
        
        # Render complex product listing
        result = engine.render("products/index.blade.html", context)
        
        # Verify complex e-commerce features
        assert "Showing 3 of 156 products" in result
        assert 'for "wireless"' in result
        assert "Brand: Apple" in result
        
        # Verify sorting and view controls
        assert "Price: Low to High" in result
        assert "view-grid" in result
        assert "view-list" in result
        
        # Verify filters
        assert "Price Range" in result
        assert "Categories" in result
        assert "Brands" in result
        assert "Rating" in result
        assert "Clear All Filters" in result
        
        # Verify product cards
        assert "Wireless Bluetooth Headphones Premium" in result
        assert "$149.99" in result
        assert "$199.99" in result
        assert "25% OFF" in result
        assert "featured-badge" in result
        assert "Sony" in result
        
        # Verify stock status
        assert "In Stock" in result
        assert "Out of Stock" in result
        assert "Free Shipping" in result
        
        # Verify ratings
        assert "4.5" in result
        assert "(128)" in result
        assert "icon-star filled" in result
        
        # Verify pagination
        assert "Previous" in result
        assert "Next" in result
        assert "page=1" in result
        assert "page=3" in result
        
        # Verify JavaScript functionality
        assert "addToCart" in result
        assert "toggleWishlist" in result
        assert "updateFilters" in result
        assert "clearAllFilters" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])