#!/usr/bin/env python3
"""
Laravel-style Global Scopes Usage Examples

This script demonstrates comprehensive usage of the Global Scopes system,
showing how to implement automatic query filtering across all model queries.

Run with: python3 examples/global_scopes_usage.py
Or: make scope-example
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta
from typing import Optional, List, Any, Type

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Import our Global Scopes system
from app.Scopes import (
    Scope, ActiveScope, PublishedScope, VerifiedScope, TenantScope,
    ArchiveScope, DateRangeScope, OwnerScope, VisibilityScope, StatusScope,
    create_scope, conditional_scope, combine_scopes,
    GlobalScopeManager, ScopeRegistry
)


# Test Models
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    status = Column(String(20), default='active')
    email_verified_at = Column(DateTime, nullable=True)
    tenant_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    
    @classmethod
    def get_scope_manager(cls) -> GlobalScopeManager:
        """Get the scope manager for this model."""
        return ScopeRegistry.get_manager(cls)
    
    @classmethod
    def add_global_scope(cls, name: str, scope: Scope) -> None:
        """Add a global scope to this model."""
        cls.get_scope_manager().add_scope(name, scope)
    
    @classmethod
    def remove_global_scope(cls, name: str) -> None:
        """Remove a global scope from this model."""
        cls.get_scope_manager().remove_scope(name)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', status='{self.status}')>"


class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(String(1000), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), default='draft')
    visibility = Column(String(20), default='public')
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    
    @classmethod
    def get_scope_manager(cls) -> GlobalScopeManager:
        """Get the scope manager for this model."""
        return ScopeRegistry.get_manager(cls)
    
    @classmethod
    def add_global_scope(cls, name: str, scope: Scope) -> None:
        """Add a global scope to this model."""
        cls.get_scope_manager().add_scope(name, scope)
    
    @classmethod
    def remove_global_scope(cls, name: str) -> None:
        """Remove a global scope from this model."""
        cls.get_scope_manager().remove_scope(name)
    
    def __repr__(self) -> str:
        return f"<Post(id={self.id}, title='{self.title}', status='{self.status}')>"


# Custom Scopes

class CompanyScope(Scope):
    """Custom scope for company-specific filtering."""
    
    def __init__(self, company_id: str):
        super().__init__('CompanyScope')
        self.company_id = company_id
    
    def apply(self, builder, model: Type[Any]):
        """Apply company filter to queries."""
        if hasattr(model, 'company_id'):
            return builder.filter(getattr(model, 'company_id') == self.company_id)
        return builder


class RecentScope(Scope):
    """Custom scope for recent records (last 30 days)."""
    
    def apply(self, builder, model: Type[Any]):
        """Apply recent filter to queries."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        if hasattr(model, 'created_at'):
            return builder.filter(getattr(model, 'created_at') >= thirty_days_ago)
        return builder


# Global state for examples
current_user_id = 1
current_tenant_id = "tenant_123"
current_company_id = "company_456"

def get_current_user_id() -> int:
    """Mock function to get current user ID."""
    return current_user_id

def get_current_tenant_id() -> str:
    """Mock function to get current tenant ID."""
    return current_tenant_id

def get_current_company_id() -> str:
    """Mock function to get current company ID."""
    return current_company_id

def is_admin_user() -> bool:
    """Mock function to check if current user is admin."""
    return current_user_id == 1


def setup_database():
    """Set up in-memory SQLite database for examples."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create test data
    users = [
        User(id=1, name="John Admin", email="john@example.com", status="active", 
             email_verified_at=datetime.utcnow(), tenant_id="tenant_123"),
        User(id=2, name="Jane User", email="jane@example.com", status="active", 
             email_verified_at=datetime.utcnow(), tenant_id="tenant_123"),
        User(id=3, name="Bob Inactive", email="bob@example.com", status="inactive", 
             tenant_id="tenant_456"),
        User(id=4, name="Alice Unverified", email="alice@example.com", status="active", 
             email_verified_at=None, tenant_id="tenant_123"),
        User(id=5, name="Carol Archived", email="carol@example.com", status="active", 
             email_verified_at=datetime.utcnow(), tenant_id="tenant_123",
             archived_at=datetime.utcnow() - timedelta(days=5)),
    ]
    
    posts = [
        Post(id=1, title="Active Post", content="Content 1", user_id=1, status="published", 
             published_at=datetime.utcnow() - timedelta(days=1)),
        Post(id=2, title="Draft Post", content="Content 2", user_id=1, status="draft"),
        Post(id=3, title="Published Post", content="Content 3", user_id=2, status="published", 
             published_at=datetime.utcnow() - timedelta(days=2)),
        Post(id=4, title="Private Post", content="Content 4", user_id=2, status="published", 
             visibility="private", published_at=datetime.utcnow() - timedelta(days=3)),
        Post(id=5, title="Archived Post", content="Content 5", user_id=1, status="published", 
             published_at=datetime.utcnow() - timedelta(days=4),
             archived_at=datetime.utcnow() - timedelta(days=1)),
    ]
    
    for user in users:
        session.add(user)
    for post in posts:
        session.add(post)
    
    session.commit()
    return session


def example_basic_scopes(session: Session):
    """Demonstrate basic scope functionality."""
    print("\n" + "="*60)
    print("BASIC SCOPES EXAMPLE")
    print("="*60)
    
    # Add basic scopes to User model
    User.add_global_scope('active', ActiveScope())
    User.add_global_scope('verified', VerifiedScope())
    
    print("\n1. Without scopes - All users:")
    # Get scope manager and bypass scopes
    manager = User.get_scope_manager()
    query = session.query(User)
    unscoped_query = manager.without_scopes(query)
    for user in unscoped_query.all():
        verified = "✓" if user.email_verified_at else "✗"
        print(f"   {user.name} - {user.status} - Verified: {verified}")
    
    print("\n2. With active scope - Only active users:")
    query = session.query(User)
    scoped_query = manager.apply_scopes(query, except_scopes=['verified'])
    for user in scoped_query.all():
        verified = "✓" if user.email_verified_at else "✗"
        print(f"   {user.name} - {user.status} - Verified: {verified}")
    
    print("\n3. With both scopes - Only active AND verified users:")
    query = session.query(User)
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        verified = "✓" if user.email_verified_at else "✗"
        print(f"   {user.name} - {user.status} - Verified: {verified}")
    
    # Clean up for next example
    User.remove_global_scope('active')
    User.remove_global_scope('verified')


def example_tenant_scope(session: Session):
    """Demonstrate tenant-based multi-tenancy."""
    print("\n" + "="*60)
    print("TENANT SCOPE EXAMPLE")
    print("="*60)
    
    # Add tenant scope
    User.add_global_scope('tenant', TenantScope(get_current_tenant_id))
    
    print(f"\nCurrent tenant: {get_current_tenant_id()}")
    
    print("\n1. Without tenant scope - All users:")
    manager = User.get_scope_manager()
    query = session.query(User)
    unscoped_query = manager.without_scopes(query, ['tenant'])
    for user in unscoped_query.all():
        print(f"   {user.name} - Tenant: {user.tenant_id}")
    
    print("\n2. With tenant scope - Only current tenant's users:")
    query = session.query(User)
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        print(f"   {user.name} - Tenant: {user.tenant_id}")
    
    # Switch tenant
    global current_tenant_id
    original_tenant = current_tenant_id
    current_tenant_id = "tenant_456"
    
    print(f"\n3. After switching to tenant: {get_current_tenant_id()}")
    query = session.query(User)
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        print(f"   {user.name} - Tenant: {user.tenant_id}")
    
    # Restore original tenant
    current_tenant_id = original_tenant
    User.remove_global_scope('tenant')


def example_composite_scopes(session: Session):
    """Demonstrate composite and conditional scopes."""
    print("\n" + "="*60)
    print("COMPOSITE AND CONDITIONAL SCOPES EXAMPLE")
    print("="*60)
    
    # Create individual scopes
    active_scope = ActiveScope()
    verified_scope = VerifiedScope()
    archive_scope = ArchiveScope()
    
    # Create composite scope
    composite = combine_scopes(active_scope, verified_scope, archive_scope, 
                              name='active_verified_unarchived')
    User.add_global_scope('composite', composite)
    
    print("\n1. Composite scope (active + verified + unarchived):")
    manager = User.get_scope_manager()
    query = session.query(User)
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        verified = "✓" if user.email_verified_at else "✗"
        archived = "✓" if user.archived_at else "✗"
        print(f"   {user.name} - {user.status} - Verified: {verified} - Archived: {archived}")
    
    # Create conditional scope
    admin_only_scope = conditional_scope(
        condition=is_admin_user,
        apply_func=lambda builder, model: builder.filter(model.id == get_current_user_id()),
        name='admin_only'
    )
    User.add_global_scope('admin_only', admin_only_scope)
    
    print(f"\n2. With admin conditional scope (current user: {get_current_user_id()}):")
    query = session.query(User)
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        print(f"   {user.name} - ID: {user.id}")
    
    # Switch to non-admin user
    global current_user_id
    original_user = current_user_id
    current_user_id = 2
    
    print(f"\n3. Non-admin user (current user: {get_current_user_id()}):")
    query = session.query(User)
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        verified = "✓" if user.email_verified_at else "✗"
        archived = "✓" if user.archived_at else "✗"
        print(f"   {user.name} - {user.status} - Verified: {verified} - Archived: {archived}")
    
    # Restore original user
    current_user_id = original_user
    User.remove_global_scope('composite')
    User.remove_global_scope('admin_only')


def example_post_scopes(session: Session):
    """Demonstrate scopes with Post model."""
    print("\n" + "="*60)
    print("POST SCOPES EXAMPLE")
    print("="*60)
    
    # Add scopes to Post model
    Post.add_global_scope('published', PublishedScope())
    Post.add_global_scope('public', VisibilityScope(['public']))
    Post.add_global_scope('unarchived', ArchiveScope())
    
    print("\n1. All posts (without scopes):")
    manager = Post.get_scope_manager()
    query = session.query(Post)
    unscoped_query = manager.without_scopes(query)
    for post in unscoped_query.all():
        pub_status = "✓" if post.published_at else "✗"
        arch_status = "✓" if post.archived_at else "✗"
        print(f"   {post.title} - {post.status} - {post.visibility} - Published: {pub_status} - Archived: {arch_status}")
    
    print("\n2. With all scopes (published + public + unarchived):")
    query = session.query(Post)
    scoped_query = manager.apply_scopes(query)
    for post in scoped_query.all():
        pub_status = "✓" if post.published_at else "✗"
        print(f"   {post.title} - {post.status} - {post.visibility} - Published: {pub_status}")
    
    print("\n3. Only published scope (include private posts):")
    query = session.query(Post)
    scoped_query = manager.apply_scopes(query, except_scopes=['public', 'unarchived'])
    for post in scoped_query.all():
        pub_status = "✓" if post.published_at else "✗"
        arch_status = "✓" if post.archived_at else "✗"
        print(f"   {post.title} - {post.visibility} - Published: {pub_status} - Archived: {arch_status}")
    
    # Clean up
    Post.remove_global_scope('published')
    Post.remove_global_scope('public')
    Post.remove_global_scope('unarchived')


def example_anonymous_scopes(session: Session):
    """Demonstrate anonymous and factory-created scopes."""
    print("\n" + "="*60)
    print("ANONYMOUS SCOPES EXAMPLE")
    print("="*60)
    
    # Create anonymous scope using factory function
    recent_posts_scope = create_scope(
        apply_func=lambda builder, model: builder.filter(
            model.created_at >= datetime.utcnow() - timedelta(days=7)
        ),
        name='recent_posts'
    )
    Post.add_global_scope('recent', recent_posts_scope)
    
    # Create another anonymous scope for specific user
    owner_posts_scope = create_scope(
        apply_func=lambda builder, model: builder.filter(model.user_id == get_current_user_id()),
        name='owner_posts'
    )
    Post.add_global_scope('owner', owner_posts_scope)
    
    print(f"\n1. Recent posts by current user (User ID: {get_current_user_id()}):")
    manager = Post.get_scope_manager()
    query = session.query(Post)
    scoped_query = manager.apply_scopes(query)
    for post in scoped_query.all():
        days_old = (datetime.utcnow() - post.created_at).days
        print(f"   {post.title} - User: {post.user_id} - Age: {days_old} days")
    
    # Switch user
    global current_user_id
    original_user = current_user_id
    current_user_id = 2
    
    print(f"\n2. After switching to User ID: {get_current_user_id()}")
    query = session.query(Post)
    scoped_query = manager.apply_scopes(query)
    for post in scoped_query.all():
        days_old = (datetime.utcnow() - post.created_at).days
        print(f"   {post.title} - User: {post.user_id} - Age: {days_old} days")
    
    # Restore original user
    current_user_id = original_user
    Post.remove_global_scope('recent')
    Post.remove_global_scope('owner')


def example_scope_management(session: Session):
    """Demonstrate scope management and debugging."""
    print("\n" + "="*60)
    print("SCOPE MANAGEMENT EXAMPLE")
    print("="*60)
    
    # Add multiple scopes with different priorities
    active_scope = ActiveScope().set_priority(1)
    verified_scope = VerifiedScope().set_priority(2)
    tenant_scope = TenantScope(get_current_tenant_id).set_priority(0)  # Highest priority
    
    User.add_global_scope('active', active_scope)
    User.add_global_scope('verified', verified_scope)
    User.add_global_scope('tenant', tenant_scope)
    
    manager = User.get_scope_manager()
    
    print("\n1. Scope Manager Information:")
    print(f"   {manager}")
    print(f"   Total scopes: {manager.get_scope_count()}")
    print(f"   Enabled scopes: {manager.get_enabled_scopes()}")
    print(f"   Disabled scopes: {manager.get_disabled_scopes()}")
    
    print("\n2. Performance Statistics:")
    stats = manager.get_performance_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n3. Debug Information:")
    debug_info = manager.debug_info()
    print(f"   Model: {debug_info['model']}")
    print(f"   Total scopes: {debug_info['total_scopes']}")
    print(f"   Enabled count: {debug_info['enabled_count']}")
    
    for name, details in debug_info['scopes'].items():
        print(f"   Scope '{name}':")
        for key, value in details.items():
            print(f"     {key}: {value}")
    
    print("\n4. Global Registry Statistics:")
    global_stats = ScopeRegistry.get_global_stats()
    for key, value in global_stats.items():
        print(f"   {key}: {value}")
    
    # Demonstrate scope enabling/disabling
    print("\n5. Disabling 'verified' scope:")
    manager.disable_scope('verified')
    print(f"   Enabled scopes: {manager.get_enabled_scopes()}")
    
    print("\n6. Re-enabling 'verified' scope:")
    manager.enable_scope('verified')
    print(f"   Enabled scopes: {manager.get_enabled_scopes()}")
    
    # Clean up
    User.remove_global_scope('active')
    User.remove_global_scope('verified')
    User.remove_global_scope('tenant')


def example_custom_scopes(session: Session):
    """Demonstrate custom scope implementations."""
    print("\n" + "="*60)
    print("CUSTOM SCOPES EXAMPLE")
    print("="*60)
    
    # Use custom scopes
    User.add_global_scope('company', CompanyScope(get_current_company_id()))
    User.add_global_scope('recent', RecentScope())
    
    print("\n1. Custom company and recent scopes:")
    print(f"   Company ID: {get_current_company_id()}")
    
    manager = User.get_scope_manager()
    query = session.query(User)
    
    # Note: Our test data doesn't have company_id, so this will show all users
    # In a real scenario, users would be filtered by company_id
    scoped_query = manager.apply_scopes(query)
    for user in scoped_query.all():
        days_old = (datetime.utcnow() - user.created_at).days
        print(f"   {user.name} - Age: {days_old} days")
    
    # Show scope details
    print("\n2. Custom scope details:")
    for name, scope in manager.get_scopes().items():
        print(f"   {name}: {scope}")
        if hasattr(scope, 'company_id'):
            print(f"     Company ID: {scope.company_id}")
    
    # Clean up
    User.remove_global_scope('company')
    User.remove_global_scope('recent')


def main():
    """Run all Global Scopes examples."""
    print("Laravel-Style Global Scopes Examples")
    print("====================================")
    
    # Set up database
    session = setup_database()
    
    try:
        # Run examples
        example_basic_scopes(session)
        example_tenant_scope(session)
        example_composite_scopes(session)
        example_post_scopes(session)
        example_anonymous_scopes(session)
        example_scope_management(session)
        example_custom_scopes(session)
        
        print("\n" + "="*60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nGlobal Scopes provide automatic query filtering across all model queries.")
        print("Key features demonstrated:")
        print("• Basic scope filtering (Active, Verified, Published)")
        print("• Multi-tenant support with dynamic tenant resolution")
        print("• Composite scopes combining multiple filters")
        print("• Conditional scopes based on runtime conditions")
        print("• Anonymous scopes created with factory functions")
        print("• Scope management (enable/disable, priorities, debugging)")
        print("• Custom scope implementations")
        print("\nGlobal Scopes are essential for features like:")
        print("• Soft deletes")
        print("• Multi-tenancy")
        print("• Role-based access control")
        print("• Content visibility")
        print("• Data archiving")
        
    finally:
        session.close()
        # Clear all global scopes
        ScopeRegistry.clear_all_scopes()


if __name__ == "__main__":
    main()