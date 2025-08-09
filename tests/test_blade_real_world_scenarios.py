"""
Test Suite for Real-World Blade Engine Scenarios
Tests practical use cases, integration patterns, and production scenarios
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator, Tuple
import os
from datetime import datetime, timedelta
import json

from app.View.BladeEngine import BladeEngine


class TestBladeWebApplicationScenarios:
    """Test real-world web application scenarios"""
    
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
    
    def test_complete_blog_layout(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test a complete blog application layout"""
        engine, temp_dir = blade_engine
        
        # Master layout template
        master_layout = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'My Blog')</title>
    <meta name="description" content="@yield('description', 'A Laravel-style blog')">
    
    @push('meta')
        <meta name="author" content="{{ config.site.author }}">
    @endpush
    
    @stack('meta')
    
    <link href="/css/app.css" rel="stylesheet">
    @stack('styles')
</head>
<body class="@yield('body_class', '')">
    <nav class="navbar">
        <div class="container">
            <a href="/" class="brand">{{ config.site.name }}</a>
            <ul class="nav-links">
                <li><a href="/">Home</a></li>
                <li><a href="/about">About</a></li>
                
                @auth
                    <li><a href="/dashboard">Dashboard</a></li>
                    <li><a href="/logout">Logout ({{ current_user.name }})</a></li>
                @else
                    <li><a href="/login">Login</a></li>
                    <li><a href="/register">Register</a></li>
                @endauth
            </ul>
        </div>
    </nav>
    
    <main class="main-content">
        @yield('breadcrumbs')
        
        @if(session.flash_message)
            <div class="alert alert-{{ session.flash_type or 'info' }}">
                {{ session.flash_message }}
            </div>
        @endif
        
        @yield('content')
    </main>
    
    <footer class="footer">
        <div class="container">
            <p>&copy; {{ "now"|date("Y") }} {{ config.site.name }}. All rights reserved.</p>
        </div>
    </footer>
    
    <script src="/js/app.js"></script>
    @stack('scripts')
</body>
</html>
        """.strip()
        
        # Blog post template  
        blog_post_template = """
@extends('master')

@section('title', post.title + ' - My Blog')
@section('description', post.excerpt)

@push('meta')
    <meta property="og:title" content="{{ post.title }}">
    <meta property="og:description" content="{{ post.excerpt }}">
    <meta property="og:image" content="{{ post.featured_image }}">
@endpush

@section('breadcrumbs')
    <nav class="breadcrumbs">
        <a href="/">Home</a> >
        <a href="/blog">Blog</a> >
        <span>{{ post.title }}</span>
    </nav>
@endsection

@section('content')
<article class="blog-post">
    <header class="post-header">
        @if(post.featured_image)
            <img src="{{ post.featured_image }}" alt="{{ post.title }}" class="featured-image">
        @endif
        
        <h1>{{ post.title }}</h1>
        
        <div class="post-meta">
            <span class="author">By {{ post.author.name }}</span>
            <span class="date">{{ post.published_at | date('F j, Y') }}</span>
            <span class="read-time">{{ post.read_time }} min read</span>
            
            @if(post.tags)
                <div class="tags">
                @foreach(post.tags as tag)
                    <span class="tag">{{ tag.name }}</span>
                @endforeach
                </div>
            @endif
        </div>
    </header>
    
    <div class="post-content">
        {!! post.content !!}
    </div>
    
    <footer class="post-footer">
        @if(post.categories)
            <div class="categories">
                <strong>Categories:</strong>
                @foreach(post.categories as category)
                    <a href="/category/{{ category.slug }}">{{ category.name }}</a>{{ not loop.last ? ', ' : '' }}
                @endforeach
            </div>
        @endif
        
        <div class="social-share">
            <a href="https://twitter.com/share?url={{ request.url }}&text={{ post.title }}" class="twitter-share">Share on Twitter</a>
            <a href="https://facebook.com/sharer/sharer.php?u={{ request.url }}" class="facebook-share">Share on Facebook</a>
        </div>
    </footer>
</article>

@if(related_posts)
    <section class="related-posts">
        <h3>Related Posts</h3>
        <div class="post-grid">
        @foreach(related_posts as related)
            <article class="post-card">
                <a href="/blog/{{ related.slug }}">
                    @if(related.featured_image)
                        <img src="{{ related.featured_image }}" alt="{{ related.title }}">
                    @endif
                    <h4>{{ related.title }}</h4>
                    <p>{{ related.excerpt | truncate_words(15) }}</p>
                </a>
            </article>
        @endforeach
        </div>
    </section>
@endif

@can('edit-posts')
    <div class="admin-actions">
        <a href="/admin/posts/{{ post.id }}/edit" class="btn btn-primary">Edit Post</a>
        <a href="/admin/posts/{{ post.id }}/delete" class="btn btn-danger">Delete Post</a>
    </div>
@endcan
@endsection

@push('scripts')
    <script src="/js/social-share.js"></script>
    <script>
        // Post-specific JavaScript
        document.addEventListener('DOMContentLoaded', function() {
            hljs.highlightAll(); // Syntax highlighting
        });
    </script>
@endpush
        """.strip()
        
        self.create_template(temp_dir, "master.blade.html", master_layout)
        self.create_template(temp_dir, "blog_post.blade.html", blog_post_template)
        
        # Mock data
        context = {
            'config': {
                'site': {
                    'name': 'Tech Blog',
                    'author': 'John Doe'
                }
            },
            'current_user': {'name': 'Admin User'},
            'session': {
                'flash_message': 'Welcome back!',
                'flash_type': 'success'
            },
            'post': {
                'id': 1,
                'title': 'Getting Started with FastAPI and Blade Templates',
                'slug': 'getting-started-fastapi-blade',
                'excerpt': 'Learn how to build modern web applications...',
                'content': '<p>This is the post content with <strong>HTML</strong>.</p>',
                'featured_image': '/images/fastapi-blog.jpg',
                'author': {'name': 'Jane Smith'},
                'published_at': datetime.now() - timedelta(days=2),
                'read_time': 5,
                'tags': [
                    {'name': 'FastAPI'},
                    {'name': 'Python'},
                    {'name': 'Templates'}
                ],
                'categories': [
                    {'name': 'Web Development', 'slug': 'web-development'},
                    {'name': 'Python', 'slug': 'python'}
                ]
            },
            'related_posts': [
                {
                    'title': 'Advanced FastAPI Patterns',
                    'slug': 'advanced-fastapi-patterns',
                    'excerpt': 'Explore advanced patterns for FastAPI applications...',
                    'featured_image': '/images/advanced-fastapi.jpg'
                }
            ],
            'request': {'url': 'https://myblog.com/blog/getting-started-fastapi-blade'}
        }
        
        # Mock user permissions
        class MockUser:
            def can(self, permission: str) -> bool:
                return permission == 'edit-posts'
        
        context['current_user'] = MockUser()
        
        result = engine.render("blog_post.blade.html", context)
        
        # Verify key elements are present
        assert 'Getting Started with FastAPI and Blade Templates' in result
        assert 'Jane Smith' in result
        assert 'Tech Blog' in result
        assert 'Welcome back!' in result
        assert 'This is the post content' in result
        assert 'Related Posts' in result
        assert 'Edit Post' in result  # User has permission
        assert 'FastAPI' in result  # Tags
        assert 'Web Development' in result  # Categories
    
    def test_e_commerce_product_listing(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test e-commerce product listing with filters and pagination"""
        engine, temp_dir = blade_engine
        
        product_listing_template = """
@extends('master')

@section('title', 'Products - ' + category.name if category else 'All Products')

@section('content')
<div class="product-listing">
    <div class="listing-header">
        <h1>
            @if(category)
                {{ category.name }}
            @else
                All Products
            @endif
            <span class="count">({{ products.total }} items)</span>
        </h1>
        
        @if(search_query)
            <div class="search-results">
                Search results for: "<strong>{{ search_query }}</strong>"
                <a href="{{ request.url_without('search') }}" class="clear-search">&times;</a>
            </div>
        @endif
    </div>
    
    <div class="listing-controls">
        <div class="filters">
            <form method="GET" class="filter-form">
                <select name="sort" onchange="this.form.submit()">
                    <option value="name" {{ request.get('sort') == 'name' ? 'selected' : '' }}>Name</option>
                    <option value="price_asc" {{ request.get('sort') == 'price_asc' ? 'selected' : '' }}>Price: Low to High</option>
                    <option value="price_desc" {{ request.get('sort') == 'price_desc' ? 'selected' : '' }}>Price: High to Low</option>
                    <option value="newest" {{ request.get('sort') == 'newest' ? 'selected' : '' }}>Newest</option>
                </select>
                
                <div class="price-range">
                    <label>Price Range:</label>
                    <input type="number" name="min_price" placeholder="Min" value="{{ request.get('min_price') }}">
                    <input type="number" name="max_price" placeholder="Max" value="{{ request.get('max_price') }}">
                </div>
                
                @if(available_brands)
                    <div class="brand-filter">
                        <label>Brand:</label>
                        <select name="brand">
                            <option value="">All Brands</option>
                            @foreach(available_brands as brand)
                                <option value="{{ brand.id }}" {{ request.get('brand') == brand.id|string ? 'selected' : '' }}>
                                    {{ brand.name }}
                                </option>
                            @endforeach
                        </select>
                    </div>
                @endif
                
                <button type="submit" class="btn btn-primary">Filter</button>
            </form>
        </div>
        
        <div class="view-toggle">
            <button class="grid-view {{ view_mode != 'list' ? 'active' : '' }}" data-view="grid">Grid</button>
            <button class="list-view {{ view_mode == 'list' ? 'active' : '' }}" data-view="list">List</button>
        </div>
    </div>
    
    @if(products.data)
        <div class="product-grid {{ view_mode == 'list' ? 'list-view' : 'grid-view' }}">
        @foreach(products.data as product)
            <div class="product-card">
                <div class="product-image">
                    <a href="/products/{{ product.slug }}">
                        <img src="{{ product.image or '/images/no-image.jpg' }}" alt="{{ product.name }}">
                    </a>
                    
                    @if(product.discount_percentage)
                        <span class="discount-badge">-{{ product.discount_percentage }}%</span>
                    @endif
                    
                    @if(product.is_new)
                        <span class="new-badge">New</span>
                    @endif
                </div>
                
                <div class="product-info">
                    <h3><a href="/products/{{ product.slug }}">{{ product.name }}</a></h3>
                    
                    @if(product.brand)
                        <p class="brand">{{ product.brand.name }}</p>
                    @endif
                    
                    <div class="price">
                        @if(product.sale_price and product.sale_price < product.price)
                            <span class="sale-price">{{ product.sale_price | money }}</span>
                            <span class="original-price">{{ product.price | money }}</span>
                        @else
                            <span class="price">{{ product.price | money }}</span>
                        @endif
                    </div>
                    
                    @if(product.rating)
                        <div class="rating">
                            @for(i in range(1, 6))
                                <span class="star {{ i <= product.rating ? 'filled' : '' }}">★</span>
                            @endfor
                            <span class="rating-count">({{ product.review_count }})</span>
                        </div>
                    @endif
                    
                    <div class="product-actions">
                        @if(product.in_stock)
                            <button class="btn btn-primary add-to-cart" data-product="{{ product.id }}">
                                Add to Cart
                            </button>
                            <button class="btn btn-secondary add-to-wishlist" data-product="{{ product.id }}">
                                ❤
                            </button>
                        @else
                            <button class="btn btn-disabled" disabled>Out of Stock</button>
                        @endif
                    </div>
                </div>
            </div>
        @endforeach
        </div>
        
        <!-- Pagination -->
        @if(products.total > products.per_page)
            <div class="pagination">
                @if(products.current_page > 1)
                    <a href="?page={{ products.current_page - 1 }}" class="prev">Previous</a>
                @endif
                
                @for(page in range(max(1, products.current_page - 2), min(products.last_page + 1, products.current_page + 3)))
                    @if(page == products.current_page)
                        <span class="current">{{ page }}</span>
                    @else
                        <a href="?page={{ page }}">{{ page }}</a>
                    @endif
                @endfor
                
                @if(products.current_page < products.last_page)
                    <a href="?page={{ products.current_page + 1 }}" class="next">Next</a>
                @endif
            </div>
        @endif
    @else
        <div class="no-products">
            <h3>No products found</h3>
            <p>Try adjusting your filters or search terms.</p>
        </div>
    @endif
</div>
@endsection

@push('scripts')
<script>
    // Add to cart functionality
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.product;
            // AJAX call to add product to cart
            fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': '{{ csrf_token() }}'
                },
                body: JSON.stringify({ product_id: productId, quantity: 1 })
            });
        });
    });
</script>
@endpush
        """.strip()
        
        self.create_template(temp_dir, "master.blade.html", "<html><body>@yield('content')</body></html>")
        self.create_template(temp_dir, "product_listing.blade.html", product_listing_template)
        
        # Mock e-commerce data
        products_data = []
        for i in range(5):
            products_data.append({
                'id': i + 1,
                'name': f'Product {i + 1}',
                'slug': f'product-{i + 1}',
                'price': 99.99 + (i * 10),
                'sale_price': 89.99 + (i * 10) if i % 2 == 0 else None,
                'image': f'/images/product-{i + 1}.jpg',
                'brand': {'name': f'Brand {i % 3 + 1}'},
                'rating': 4 + (i % 2),
                'review_count': 20 + (i * 5),
                'in_stock': i != 2,  # Product 3 out of stock
                'is_new': i < 2,
                'discount_percentage': 10 if i % 2 == 0 else None
            })
        
        context = {
            'category': {'name': 'Electronics'},
            'search_query': '',
            'products': {
                'data': products_data,
                'total': 25,
                'per_page': 12,
                'current_page': 1,
                'last_page': 3
            },
            'available_brands': [
                {'id': 1, 'name': 'Brand 1'},
                {'id': 2, 'name': 'Brand 2'},
                {'id': 3, 'name': 'Brand 3'}
            ],
            'view_mode': 'grid',
            'request': {
                'get': lambda key: None,
                'url_without': lambda key: '/products'
            }
        }
        
        result = engine.render("product_listing.blade.html", context)
        
        # Verify key e-commerce elements
        assert 'Electronics' in result
        assert 'Product 1' in result
        assert '$99.99' in result
        assert 'Add to Cart' in result
        assert 'Out of Stock' in result  # Product 3
        assert 'Brand 1' in result
        assert 'Previous' not in result  # First page
        assert 'rating' in result
    
    def test_user_dashboard_with_widgets(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test a complex user dashboard with multiple widgets"""
        engine, temp_dir = blade_engine
        
        dashboard_template = """
@extends('master')

@section('title', 'Dashboard - ' + current_user.name)

@push('styles')
    <link href="/css/dashboard.css" rel="stylesheet">
@endpush

@section('content')
<div class="dashboard">
    <div class="dashboard-header">
        <h1>Welcome back, {{ current_user.name }}!</h1>
        <p class="last-login">Last login: {{ current_user.last_login | timeago }}</p>
    </div>
    
    <div class="dashboard-grid">
        <!-- Stats Cards -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-content">
                    <h3>{{ stats.total_orders }}</h3>
                    <p>Total Orders</p>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">💰</div>
                <div class="stat-content">
                    <h3>{{ stats.total_spent | money }}</h3>
                    <p>Total Spent</p>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">📦</div>
                <div class="stat-content">
                    <h3>{{ stats.pending_orders }}</h3>
                    <p>Pending Orders</p>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">⭐</div>
                <div class="stat-content">
                    <h3>{{ stats.loyalty_points }}</h3>
                    <p>Loyalty Points</p>
                </div>
            </div>
        </div>
        
        <!-- Recent Orders -->
        <div class="widget">
            <div class="widget-header">
                <h2>Recent Orders</h2>
                <a href="/orders" class="view-all">View All</a>
            </div>
            <div class="widget-content">
                @if(recent_orders)
                    <table class="orders-table">
                        <thead>
                            <tr>
                                <th>Order #</th>
                                <th>Date</th>
                                <th>Items</th>
                                <th>Total</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                        @foreach(recent_orders as order)
                            <tr>
                                <td><a href="/orders/{{ order.id }}">#{{ order.id }}</a></td>
                                <td>{{ order.created_at | date('M j, Y') }}</td>
                                <td>{{ order.items|length }} items</td>
                                <td>{{ order.total | money }}</td>
                                <td>
                                    <span class="status status-{{ order.status }}">
                                        {{ order.status|title }}
                                    </span>
                                </td>
                                <td>
                                    <a href="/orders/{{ order.id }}" class="btn btn-sm">View</a>
                                    @if(order.status == 'pending')
                                        <a href="/orders/{{ order.id }}/cancel" class="btn btn-sm btn-danger">Cancel</a>
                                    @endif
                                </td>
                            </tr>
                        @endforeach
                        </tbody>
                    </table>
                @else
                    <p class="empty-state">No recent orders found.</p>
                @endif
            </div>
        </div>
        
        <!-- Wishlist -->
        <div class="widget">
            <div class="widget-header">
                <h2>Wishlist</h2>
                <span class="count">{{ wishlist_items|length }} items</span>
            </div>
            <div class="widget-content">
                @if(wishlist_items)
                    <div class="wishlist-grid">
                    @foreach(wishlist_items|slice(0, 4) as item)
                        <div class="wishlist-item">
                            <img src="{{ item.product.image }}" alt="{{ item.product.name }}">
                            <h4>{{ item.product.name }}</h4>
                            <p class="price">{{ item.product.price | money }}</p>
                            <div class="actions">
                                <button class="btn btn-sm btn-primary">Add to Cart</button>
                                <button class="btn btn-sm btn-danger">Remove</button>
                            </div>
                        </div>
                    @endforeach
                    </div>
                    @if(wishlist_items|length > 4)
                        <p class="view-more"><a href="/wishlist">View {{ wishlist_items|length - 4 }} more items</a></p>
                    @endif
                @else
                    <p class="empty-state">Your wishlist is empty.</p>
                @endif
            </div>
        </div>
        
        <!-- Account Actions -->
        <div class="widget">
            <div class="widget-header">
                <h2>Quick Actions</h2>
            </div>
            <div class="widget-content">
                <div class="action-grid">
                    <a href="/profile/edit" class="action-card">
                        <div class="action-icon">👤</div>
                        <div class="action-text">
                            <h4>Edit Profile</h4>
                            <p>Update your personal information</p>
                        </div>
                    </a>
                    
                    <a href="/addresses" class="action-card">
                        <div class="action-icon">📍</div>
                        <div class="action-text">
                            <h4>Manage Addresses</h4>
                            <p>Update shipping & billing addresses</p>
                        </div>
                    </a>
                    
                    <a href="/payment-methods" class="action-card">
                        <div class="action-icon">💳</div>
                        <div class="action-text">
                            <h4>Payment Methods</h4>
                            <p>Manage your payment options</p>
                        </div>
                    </a>
                    
                    <a href="/security" class="action-card">
                        <div class="action-icon">🔒</div>
                        <div class="action-text">
                            <h4>Security Settings</h4>
                            <p>Change password & 2FA</p>
                        </div>
                    </a>
                </div>
            </div>
        </div>
        
        <!-- Notifications -->
        @if(notifications)
        <div class="widget">
            <div class="widget-header">
                <h2>Recent Notifications</h2>
                <button class="mark-all-read">Mark All Read</button>
            </div>
            <div class="widget-content">
                <div class="notifications-list">
                @foreach(notifications|slice(0, 5) as notification)
                    <div class="notification {{ not notification.read_at ? 'unread' : '' }}">
                        <div class="notification-icon">
                            @if(notification.type == 'order')
                                📦
                            @elseif(notification.type == 'promotion')
                                🎉
                            @elseif(notification.type == 'system')
                                ⚙️
                            @else
                                📢
                            @endif
                        </div>
                        <div class="notification-content">
                            <p>{{ notification.message }}</p>
                            <small>{{ notification.created_at | timeago }}</small>
                        </div>
                    </div>
                @endforeach
                </div>
                @if(notifications|length > 5)
                    <a href="/notifications" class="view-all-notifications">View All Notifications</a>
                @endif
            </div>
        </div>
        @endif
    </div>
</div>
@endsection

@push('scripts')
<script src="/js/dashboard.js"></script>
@endpush
        """.strip()
        
        self.create_template(temp_dir, "master.blade.html", "<html><body>@yield('content')</body></html>")
        self.create_template(temp_dir, "dashboard.blade.html", dashboard_template)
        
        # Mock dashboard data
        context = {
            'current_user': {
                'name': 'John Doe',
                'last_login': datetime.now() - timedelta(hours=8)
            },
            'stats': {
                'total_orders': 23,
                'total_spent': 1247.50,
                'pending_orders': 2,
                'loyalty_points': 450
            },
            'recent_orders': [
                {
                    'id': 1001,
                    'created_at': datetime.now() - timedelta(days=3),
                    'items': [{'name': 'Product 1'}, {'name': 'Product 2'}],
                    'total': 129.99,
                    'status': 'shipped'
                },
                {
                    'id': 1002,
                    'created_at': datetime.now() - timedelta(days=1),
                    'items': [{'name': 'Product 3'}],
                    'total': 79.99,
                    'status': 'pending'
                }
            ],
            'wishlist_items': [
                {
                    'product': {
                        'name': 'Wishlist Item 1',
                        'image': '/images/wish1.jpg',
                        'price': 49.99
                    }
                },
                {
                    'product': {
                        'name': 'Wishlist Item 2', 
                        'image': '/images/wish2.jpg',
                        'price': 89.99
                    }
                }
            ],
            'notifications': [
                {
                    'type': 'order',
                    'message': 'Your order #1002 has been shipped!',
                    'created_at': datetime.now() - timedelta(hours=2),
                    'read_at': None
                },
                {
                    'type': 'promotion',
                    'message': 'New sale: 20% off electronics!',
                    'created_at': datetime.now() - timedelta(days=1),
                    'read_at': datetime.now() - timedelta(hours=12)
                }
            ]
        }
        
        result = engine.render("dashboard.blade.html", context)
        
        # Verify dashboard elements
        assert 'Welcome back, John Doe!' in result
        assert 'Total Orders' in result
        assert '23' in result  # Total orders stat
        assert '$1,247.50' in result  # Total spent
        assert 'Recent Orders' in result
        assert '#1001' in result  # Order number
        assert 'Wishlist Item 1' in result
        assert '$49.99' in result
        assert 'Your order #1002 has been shipped!' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])