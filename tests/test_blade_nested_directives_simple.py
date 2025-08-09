"""
Simple Nested Directive Test Suite for Blade Engine
Tests working nested directive scenarios without complex syntax issues
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
    
    def can(self, permission: str) -> bool:
        return permission in self._data.get('permissions', [])


class TestBladeNestedDirectivesSimple:
    """Test simple nested Blade directives that work correctly"""
    
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
    
    def test_nested_auth_and_permission_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test nested authentication and permission directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="auth-nested">
    @auth
        <div class="user-area">
            <h1>Welcome, {{ current_user.name }}!</h1>
            
            @hasrole('admin')
                <div class="admin-panel">
                    <h2>Admin Panel</h2>
                    
                    @can('manage-users')
                        <div class="user-management">
                            <h3>User Management</h3>
                            <p>You can manage users</p>
                            
                            @can('create-users')
                                <button class="btn-create">Create User</button>
                            @endcan
                            
                            @can('delete-users')
                                <button class="btn-delete">Delete Users</button>
                            @endcan
                        </div>
                    @else
                        <p>No user management access</p>
                    @endcan
                    
                    @hasrole('super-admin')
                        <div class="super-admin-section">
                            <h3>Super Admin Tools</h3>
                            
                            @can('system-settings')
                                <p>System Settings Available</p>
                            @endcan
                            
                            @can('view-logs')
                                <div class="logs-section">
                                    <h4>System Logs</h4>
                                    <p>Log access granted</p>
                                </div>
                            @endcan
                        </div>
                    @endhasrole
                </div>
            @endhasrole
            
            @hasrole('editor')
                @unless(current_user.is_admin)
                    <div class="editor-panel">
                        <h2>Content Editor</h2>
                        
                        @can('edit-posts')
                            <div class="post-editor">
                                <h3>Post Editor</h3>
                                
                                @can('publish-posts')
                                    <button class="btn-publish">Publish</button>
                                @else
                                    <button class="btn-draft">Save Draft</button>
                                @endcan
                            </div>
                        @endcan
                    </div>
                @endunless
            @endhasrole
            
            @hasrole('moderator')
                <div class="moderator-panel">
                    <h2>Moderation Panel</h2>
                    
                    @can('moderate-comments')
                        <div class="comment-moderation">
                            <h3>Comment Moderation</h3>
                            
                            @can('ban-users')
                                <button class="btn-ban">Ban Users</button>
                            @endcan
                        </div>
                    @endcan
                </div>
            @endhasrole
        </div>
    @else
        <div class="login-required">
            <h2>Please Log In</h2>
            <p>You must be authenticated to access this area.</p>
        </div>
    @endauth
</div>
        """.strip()
        self.create_template(temp_dir, "nested_auth_simple.blade.html", template_content)
        
        # Create admin user with multiple roles
        admin_user = MockUser({
            'id': 1,
            'name': 'Admin User',
            'email': 'admin@example.com',
            'is_admin': True,
            'roles': ['admin', 'super-admin'],
            'permissions': ['manage-users', 'create-users', 'delete-users', 'system-settings', 'view-logs']
        })
        
        context: Dict[str, Any] = {
            'current_user': admin_user
        }
        
        result = engine.render("nested_auth_simple.blade.html", context)
        
        # Verify nested authentication works
        assert "Welcome, Admin User!" in result
        assert "Admin Panel" in result
        assert "User Management" in result
        assert "You can manage users" in result
        assert "Create User" in result
        assert "Delete Users" in result
        
        # Verify super admin section
        assert "Super Admin Tools" in result
        assert "System Settings Available" in result
        assert "System Logs" in result
        assert "Log access granted" in result
        
        # Verify editor section not shown (user has admin role)
        assert "Content Editor" not in result
        
        # Verify no login prompt
        assert "Please Log In" not in result
    
    def test_nested_loops_with_simple_conditionals(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test nested loops with simple conditional logic"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="nested-loops">
    <h1>Team Structure</h1>
    
    @foreach(teams as team)
        <div class="team">
            <h2>{{ team.name }}</h2>
            
            @if(team.active)
                <div class="team-details">
                    <p>Team Leader: {{ team.leader }}</p>
                    
                    @if(team.members)
                        <div class="members-list">
                            <h3>Team Members</h3>
                            
                            @foreach(team.members as member)
                                <div class="member">
                                    <h4>{{ member.name }}</h4>
                                    <p>Role: {{ member.role }}</p>
                                    
                                    @if(member.active)
                                        <span class="status-active">Active</span>
                                        
                                        @if(member.skills)
                                            <div class="skills">
                                                <strong>Skills:</strong>
                                                @foreach(member.skills as skill)
                                                    <span class="skill skill-{{ skill.level }}">
                                                        {{ skill.name }}
                                                        @if(skill.certified)
                                                            ✓
                                                        @endif
                                                    </span>
                                                @endforeach
                                            </div>
                                        @endif
                                        
                                        @if(member.projects)
                                            <div class="projects">
                                                <strong>Projects:</strong>
                                                @foreach(member.projects as project)
                                                    @if(project.active)
                                                        <div class="project">
                                                            <span>{{ project.name }}</span>
                                                            
                                                            @if(project.priority == 'high')
                                                                <span class="priority-high">High Priority</span>
                                                            @elseif(project.priority == 'medium')
                                                                <span class="priority-medium">Medium</span>
                                                            @else
                                                                <span class="priority-low">Low</span>
                                                            @endif
                                                            
                                                            @if(project.overdue)
                                                                <span class="overdue">Overdue</span>
                                                            @endif
                                                        </div>
                                                    @endif
                                                @endforeach
                                            </div>
                                        @endif
                                    @else
                                        <span class="status-inactive">Inactive</span>
                                    @endif
                                </div>
                            @endforeach
                        </div>
                    @else
                        <p class="no-members">No members assigned</p>
                    @endif
                </div>
            @else
                <div class="team-inactive">
                    <p>This team is currently inactive</p>
                </div>
            @endif
        </div>
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "nested_loops_simple.blade.html", template_content)
        
        context: Dict[str, Any] = {
            'teams': [
                {
                    'name': 'Development Team',
                    'active': True,
                    'leader': 'Alice Johnson',
                    'members': [
                        {
                            'name': 'John Developer',
                            'role': 'Senior Developer',
                            'active': True,
                            'skills': [
                                {'name': 'Python', 'level': 'expert', 'certified': True},
                                {'name': 'JavaScript', 'level': 'intermediate', 'certified': False}
                            ],
                            'projects': [
                                {
                                    'name': 'API Development',
                                    'active': True,
                                    'priority': 'high',
                                    'overdue': False
                                },
                                {
                                    'name': 'Database Migration',
                                    'active': True,
                                    'priority': 'medium',
                                    'overdue': True
                                }
                            ]
                        },
                        {
                            'name': 'Sarah Tester',
                            'role': 'QA Engineer',
                            'active': False,
                            'skills': [],
                            'projects': []
                        }
                    ]
                },
                {
                    'name': 'Marketing Team',
                    'active': False,
                    'leader': 'Bob Wilson',
                    'members': []
                },
                {
                    'name': 'Design Team',
                    'active': True,
                    'leader': 'Carol Smith',
                    'members': []
                }
            ]
        }
        
        result = engine.render("nested_loops_simple.blade.html", context)
        
        # Verify basic structure
        assert "Team Structure" in result
        assert "Development Team" in result
        assert "Alice Johnson" in result
        
        # Verify nested member details
        assert "John Developer" in result
        assert "Senior Developer" in result
        assert "Active" in result
        
        # Verify skills nested loop
        assert "Python" in result
        assert "skill-expert" in result
        assert "✓" in result  # Certified marker
        assert "JavaScript" in result
        assert "skill-intermediate" in result
        
        # Verify projects nested loop
        assert "API Development" in result
        assert "priority-high" in result
        assert "Database Migration" in result
        assert "priority-medium" in result
        assert "Overdue" in result
        
        # Verify inactive member handling
        assert "Sarah Tester" in result
        assert "status-inactive" in result
        
        # Verify inactive team
        assert "Marketing Team" in result
        assert "This team is currently inactive" in result
        
        # Verify team with no members
        assert "Design Team" in result
        assert "No members assigned" in result
    
    def test_nested_conditionals_with_complex_logic(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test nested conditionals with complex logic"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="conditional-nesting">
    <h1>Product Catalog</h1>
    
    @foreach(products as product)
        <div class="product">
            <h2>{{ product.name }}</h2>
            <p>Price: ${{ product.price }}</p>
            
            @if(product.in_stock)
                <div class="stock-available">
                    <span class="stock-status">In Stock ({{ product.stock_count }})</span>
                    
                    @if(product.on_sale)
                        <div class="sale-section">
                            <span class="sale-badge">ON SALE!</span>
                            <p>Original Price: ${{ product.original_price }}</p>
                            <p>Discount: {{ product.discount_percent }}%</p>
                            
                            @if(product.sale_ends_soon)
                                <div class="urgency">
                                    <span class="urgent">Sale ends soon!</span>
                                    
                                    @if(product.hours_left < 24)
                                        <span class="very-urgent">Only {{ product.hours_left }} hours left!</span>
                                    @endif
                                </div>
                            @endif
                        </div>
                    @endif
                    
                    @if(product.stock_count < 5)
                        <div class="low-stock-warning">
                            <span class="warning">Low Stock!</span>
                            
                            @if(product.stock_count <= 1)
                                <span class="critical">Only {{ product.stock_count }} left!</span>
                            @else
                                <span class="caution">Only {{ product.stock_count }} items remaining</span>
                            @endif
                        </div>
                    @endif
                    
                    @if(product.features)
                        <div class="features">
                            <h3>Features</h3>
                            
                            @foreach(product.features as feature)
                                <div class="feature">
                                    <span class="feature-name">{{ feature.name }}</span>
                                    
                                    @if(feature.premium)
                                        <span class="premium-feature">Premium</span>
                                        
                                        @if(feature.new)
                                            <span class="new-feature">NEW!</span>
                                        @endif
                                    @endif
                                    
                                    @if(feature.description)
                                        <p class="feature-desc">{{ feature.description }}</p>
                                    @endif
                                </div>
                            @endforeach
                        </div>
                    @endif
                </div>
            @else
                <div class="out-of-stock">
                    <span class="stock-status">Out of Stock</span>
                    
                    @if(product.restock_date)
                        <p class="restock-info">
                            Expected back in stock: {{ product.restock_date }}
                            
                            @if(product.notify_available)
                                <button class="btn-notify">Notify When Available</button>
                            @endif
                        </p>
                    @else
                        <p class="no-restock">Currently unavailable</p>
                    @endif
                </div>
            @endif
            
            @if(product.reviews)
                <div class="reviews-section">
                    <h3>Customer Reviews</h3>
                    
                    @foreach(product.reviews as review)
                        <div class="review">
                            <div class="review-header">
                                <span class="reviewer">{{ review.author }}</span>
                                <div class="rating">
                                    @if(review.rating >= 4)
                                        <span class="rating-high">{{ review.rating }}/5 ⭐⭐⭐⭐⭐</span>
                                    @elseif(review.rating >= 3)
                                        <span class="rating-medium">{{ review.rating }}/5 ⭐⭐⭐</span>
                                    @else
                                        <span class="rating-low">{{ review.rating }}/5 ⭐⭐</span>
                                    @endif
                                </div>
                            </div>
                            
                            <p class="review-text">{{ review.text }}</p>
                            
                            @if(review.verified_purchase)
                                <span class="verified">Verified Purchase</span>
                            @endif
                            
                            @if(review.helpful_count > 0)
                                <div class="helpful">
                                    <span>{{ review.helpful_count }} people found this helpful</span>
                                </div>
                            @endif
                        </div>
                    @endforeach
                </div>
            @endif
        </div>
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "nested_conditionals.blade.html", template_content)
        
        context: Dict[str, Any] = {
            'products': [
                {
                    'name': 'Premium Headphones',
                    'price': 299.99,
                    'original_price': 399.99,
                    'in_stock': True,
                    'stock_count': 3,
                    'on_sale': True,
                    'discount_percent': 25,
                    'sale_ends_soon': True,
                    'hours_left': 12,
                    'features': [
                        {
                            'name': 'Noise Cancellation',
                            'premium': True,
                            'new': True,
                            'description': 'Advanced active noise cancellation'
                        },
                        {
                            'name': 'Wireless',
                            'premium': False,
                            'new': False,
                            'description': 'Bluetooth 5.0 connectivity'
                        }
                    ],
                    'reviews': [
                        {
                            'author': 'John D.',
                            'rating': 5,
                            'text': 'Excellent sound quality!',
                            'verified_purchase': True,
                            'helpful_count': 15
                        },
                        {
                            'author': 'Sarah M.',
                            'rating': 4,
                            'text': 'Great headphones, worth the price.',
                            'verified_purchase': True,
                            'helpful_count': 8
                        }
                    ]
                },
                {
                    'name': 'Budget Speakers',
                    'price': 49.99,
                    'in_stock': False,
                    'restock_date': '2025-02-01',
                    'notify_available': True,
                    'features': [],
                    'reviews': [
                        {
                            'author': 'Mike R.',
                            'rating': 2,
                            'text': 'Not great quality for the price.',
                            'verified_purchase': False,
                            'helpful_count': 3
                        }
                    ]
                }
            ]
        }
        
        result = engine.render("nested_conditionals.blade.html", context)
        
        # Verify basic product structure
        assert "Product Catalog" in result
        assert "Premium Headphones" in result
        assert "$299.99" in result
        
        # Verify nested stock and sale logic
        assert "In Stock (3)" in result
        assert "ON SALE!" in result
        assert "$399.99" in result
        assert "25%" in result
        assert "Sale ends soon!" in result
        assert "Only 12 hours left!" in result
        
        # Verify low stock warning
        assert "Low Stock!" in result
        assert "Only 3 items remaining" in result
        
        # Verify nested features
        assert "Noise Cancellation" in result
        assert "Premium" in result
        assert "NEW!" in result
        assert "Advanced active noise cancellation" in result
        assert "Wireless" in result
        assert "Bluetooth 5.0 connectivity" in result
        
        # Verify nested reviews
        assert "Customer Reviews" in result
        assert "John D." in result
        assert "5/5 ⭐⭐⭐⭐⭐" in result
        assert "Excellent sound quality!" in result
        assert "Verified Purchase" in result
        assert "15 people found this helpful" in result
        
        # Verify out of stock product
        assert "Budget Speakers" in result
        assert "Out of Stock" in result
        assert "Expected back in stock: 2025-02-01" in result
        assert "Notify When Available" in result
        
        # Verify low rating review
        assert "Mike R." in result
        assert "2/5 ⭐⭐" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])