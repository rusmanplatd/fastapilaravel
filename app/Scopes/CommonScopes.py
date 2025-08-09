from __future__ import annotations

from typing import Any, Type, Optional, List, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Query
from sqlalchemy.sql import Select
from sqlalchemy import func, and_, or_, text

from .Scope import Scope


class ActiveScope(Scope):
    """
    Global scope to only include active records.
    
    Automatically filters queries to only return records where
    the status column equals 'active' or is_active is True.
    
    Usage:
        class User(BaseModel):
            status = Column(String(20), default='active')
        
        # Apply scope
        User.add_global_scope(ActiveScope())
        
        # All queries now filter active records
        active_users = User.all()  # Only active users
        
        # Bypass when needed
        all_users = User.without_global_scope('ActiveScope').all()
    """
    
    def __init__(self, column: str = 'status', value: str = 'active', name: Optional[str] = None):
        """
        Initialize the active scope.
        
        @param column: Column name to check (default: 'status')
        @param value: Value that indicates active (default: 'active')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'ActiveScope')
        self.column = column
        self.value = value
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply active filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            return builder.filter(column_attr == self.value)
        return builder
    
    def remove(self, builder: Query, model: Type[Any]) -> Query:
        """Remove active filter from the query."""
        # This is complex to implement generically for SQLAlchemy
        # In practice, we'd need to analyze and remove the specific filter
        return builder


class PublishedScope(Scope):
    """
    Global scope to only include published content.
    
    Automatically filters queries to only return records that have
    been published based on published_at timestamp.
    
    Usage:
        class Post(BaseModel):
            published_at = Column(DateTime, nullable=True)
        
        Post.add_global_scope(PublishedScope())
        published_posts = Post.all()  # Only published posts
    """
    
    def __init__(self, column: str = 'published_at', name: Optional[str] = None):
        """
        Initialize the published scope.
        
        @param column: Column name to check (default: 'published_at')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'PublishedScope')
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply published filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            now = datetime.now(timezone.utc)
            return builder.filter(
                and_(
                    column_attr.is_not(None),
                    column_attr <= now
                )
            )
        return builder


class VerifiedScope(Scope):
    """
    Global scope to only include verified records.
    
    Filters queries to only return records where verification
    status indicates the record has been verified.
    
    Usage:
        class User(BaseModel):
            email_verified_at = Column(DateTime, nullable=True)
        
        User.add_global_scope(VerifiedScope())
        verified_users = User.all()  # Only verified users
    """
    
    def __init__(self, column: str = 'email_verified_at', name: Optional[str] = None):
        """
        Initialize the verified scope.
        
        @param column: Column name to check (default: 'email_verified_at')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'VerifiedScope')
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply verified filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            return builder.filter(column_attr.is_not(None))
        return builder


class TenantScope(Scope):
    """
    Global scope for multi-tenant applications.
    
    Automatically filters queries to only return records
    belonging to the current tenant.
    
    Usage:
        class Order(BaseModel):
            tenant_id = Column(String(50), nullable=False)
        
        def get_current_tenant_id():
            return current_user.tenant_id
        
        Order.add_global_scope(TenantScope(get_current_tenant_id))
        orders = Order.all()  # Only current tenant's orders
    """
    
    def __init__(
        self, 
        tenant_resolver: callable, 
        column: str = 'tenant_id', 
        name: Optional[str] = None
    ):
        """
        Initialize the tenant scope.
        
        @param tenant_resolver: Function that returns current tenant ID
        @param column: Column name for tenant ID (default: 'tenant_id')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'TenantScope')
        self.tenant_resolver = tenant_resolver
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply tenant filter to the query."""
        if hasattr(model, self.column):
            try:
                current_tenant = self.tenant_resolver()
                if current_tenant:
                    column_attr = getattr(model, self.column)
                    return builder.filter(column_attr == current_tenant)
            except Exception as e:
                import logging
                logging.warning(f"Error getting current tenant: {e}")
        return builder
    
    def can_apply(self, model: Type[Any]) -> bool:
        """Check if tenant scope can apply."""
        if not super().can_apply(model):
            return False
        try:
            return self.tenant_resolver() is not None
        except Exception:
            return False


class ArchiveScope(Scope):
    """
    Global scope to exclude archived records.
    
    Automatically filters queries to exclude records that
    have been marked as archived.
    
    Usage:
        class Document(BaseModel):
            archived_at = Column(DateTime, nullable=True)
        
        Document.add_global_scope(ArchiveScope())
        active_docs = Document.all()  # Only non-archived documents
    """
    
    def __init__(self, column: str = 'archived_at', name: Optional[str] = None):
        """
        Initialize the archive scope.
        
        @param column: Column name to check (default: 'archived_at')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'ArchiveScope')
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply non-archived filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            return builder.filter(column_attr.is_(None))
        return builder


class DateRangeScope(Scope):
    """
    Global scope to filter records by date range.
    
    Automatically filters queries to only return records
    within a specified date range.
    
    Usage:
        # Only show posts from last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        Post.add_global_scope(
            DateRangeScope(start_date=thirty_days_ago, column='created_at')
        )
        recent_posts = Post.all()
    """
    
    def __init__(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        column: str = 'created_at',
        name: Optional[str] = None
    ):
        """
        Initialize the date range scope.
        
        @param start_date: Start date for range (inclusive)
        @param end_date: End date for range (inclusive)
        @param column: Column name to check (default: 'created_at')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'DateRangeScope')
        self.start_date = start_date
        self.end_date = end_date
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply date range filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            conditions = []
            
            if self.start_date:
                conditions.append(column_attr >= self.start_date)
            
            if self.end_date:
                conditions.append(column_attr <= self.end_date)
            
            if conditions:
                return builder.filter(and_(*conditions))
        
        return builder


class OwnerScope(Scope):
    """
    Global scope to filter records by owner.
    
    Automatically filters queries to only return records
    belonging to the current user or specified owner.
    
    Usage:
        def get_current_user_id():
            return current_user.id
        
        class Task(BaseModel):
            user_id = Column(Integer, ForeignKey('users.id'))
        
        Task.add_global_scope(OwnerScope(get_current_user_id))
        my_tasks = Task.all()  # Only current user's tasks
    """
    
    def __init__(
        self, 
        owner_resolver: callable, 
        column: str = 'user_id', 
        name: Optional[str] = None
    ):
        """
        Initialize the owner scope.
        
        @param owner_resolver: Function that returns current owner ID
        @param column: Column name for owner ID (default: 'user_id')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'OwnerScope')
        self.owner_resolver = owner_resolver
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply owner filter to the query."""
        if hasattr(model, self.column):
            try:
                current_owner = self.owner_resolver()
                if current_owner:
                    column_attr = getattr(model, self.column)
                    return builder.filter(column_attr == current_owner)
            except Exception as e:
                import logging
                logging.warning(f"Error getting current owner: {e}")
        return builder
    
    def can_apply(self, model: Type[Any]) -> bool:
        """Check if owner scope can apply."""
        if not super().can_apply(model):
            return False
        try:
            return self.owner_resolver() is not None
        except Exception:
            return False


class VisibilityScope(Scope):
    """
    Global scope for content visibility (public/private).
    
    Automatically filters queries based on visibility settings,
    useful for content management systems or user-generated content.
    
    Usage:
        class Article(BaseModel):
            visibility = Column(String(20), default='public')
        
        Article.add_global_scope(VisibilityScope())
        public_articles = Article.all()  # Only public articles
    """
    
    def __init__(
        self, 
        allowed_values: List[str] = None,
        column: str = 'visibility',
        name: Optional[str] = None
    ):
        """
        Initialize the visibility scope.
        
        @param allowed_values: List of allowed visibility values (default: ['public'])
        @param column: Column name to check (default: 'visibility')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'VisibilityScope')
        self.allowed_values = allowed_values or ['public']
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply visibility filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            if len(self.allowed_values) == 1:
                return builder.filter(column_attr == self.allowed_values[0])
            else:
                return builder.filter(column_attr.in_(self.allowed_values))
        return builder


class StatusScope(Scope):
    """
    Generic status-based scope with multiple allowed values.
    
    More flexible than ActiveScope, allows filtering by multiple
    status values and custom status columns.
    
    Usage:
        # Allow both 'active' and 'pending' statuses
        User.add_global_scope(
            StatusScope(['active', 'pending'], column='account_status')
        )
        active_users = User.all()
    """
    
    def __init__(
        self, 
        allowed_statuses: List[str],
        column: str = 'status',
        name: Optional[str] = None
    ):
        """
        Initialize the status scope.
        
        @param allowed_statuses: List of allowed status values
        @param column: Column name to check (default: 'status')
        @param name: Optional name for the scope
        """
        super().__init__(name or 'StatusScope')
        self.allowed_statuses = allowed_statuses
        self.column = column
    
    def apply(self, builder: Query, model: Type[Any]) -> Query:
        """Apply status filter to the query."""
        if hasattr(model, self.column):
            column_attr = getattr(model, self.column)
            if len(self.allowed_statuses) == 1:
                return builder.filter(column_attr == self.allowed_statuses[0])
            else:
                return builder.filter(column_attr.in_(self.allowed_statuses))
        return builder


# Factory functions for quick scope creation

def active_scope(column: str = 'status', value: str = 'active') -> ActiveScope:
    """Create an ActiveScope with custom parameters."""
    return ActiveScope(column, value)


def published_scope(column: str = 'published_at') -> PublishedScope:
    """Create a PublishedScope with custom column."""
    return PublishedScope(column)


def verified_scope(column: str = 'email_verified_at') -> VerifiedScope:
    """Create a VerifiedScope with custom column."""
    return VerifiedScope(column)


def tenant_scope(tenant_resolver: callable, column: str = 'tenant_id') -> TenantScope:
    """Create a TenantScope with custom parameters."""
    return TenantScope(tenant_resolver, column)


def owner_scope(owner_resolver: callable, column: str = 'user_id') -> OwnerScope:
    """Create an OwnerScope with custom parameters."""
    return OwnerScope(owner_resolver, column)


def status_scope(allowed_statuses: List[str], column: str = 'status') -> StatusScope:
    """Create a StatusScope with custom parameters."""
    return StatusScope(allowed_statuses, column)


def date_range_scope(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    column: str = 'created_at'
) -> DateRangeScope:
    """Create a DateRangeScope with custom parameters."""
    return DateRangeScope(start_date, end_date, column)