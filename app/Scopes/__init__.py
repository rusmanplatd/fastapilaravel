from __future__ import annotations

"""
Laravel-style Global Scopes module.

This module provides complete Global Scope functionality for automatic
query modification across all model queries.

Classes:
- Scope: Abstract base class for creating custom scopes
- ScopeInterface: Protocol for scope implementations
- AnonymousScope: For inline scope definitions
- ConditionalScope: For conditional scope application
- CompositeScope: For combining multiple scopes
- GlobalScopeManager: Manages scopes for individual models
- ScopeRegistry: Global registry for all scope managers

Common Scopes:
- ActiveScope: Filter by active status
- PublishedScope: Filter by published content
- VerifiedScope: Filter by verified records
- TenantScope: Multi-tenant filtering
- ArchiveScope: Exclude archived records
- DateRangeScope: Filter by date ranges
- OwnerScope: Filter by owner/user
- VisibilityScope: Filter by visibility settings
- StatusScope: Generic status-based filtering

Usage:
    from app.Scopes import Scope, ActiveScope, TenantScope
    
    # Custom scope
    class CompanyScope(Scope):
        def apply(self, builder, model):
            return builder.filter(model.company_id == get_current_company_id())
    
    # Apply to model
    User.add_global_scope('company', CompanyScope())
    User.add_global_scope('active', ActiveScope())
    
    # All queries now automatically filtered
    users = User.all()  # Only active users from current company
    
    # Bypass scopes when needed
    all_users = User.without_global_scopes().all()
"""

# Core scope classes
from .Scope import (
    Scope,
    ScopeInterface,
    AnonymousScope,
    ConditionalScope,
    CompositeScope,
    create_scope,
    conditional_scope,
    combine_scopes
)

# Scope management
from .GlobalScopeManager import (
    GlobalScopeManager,
    ScopeRegistry
)

# Common reusable scopes
from .CommonScopes import (
    ActiveScope,
    PublishedScope,
    VerifiedScope,
    TenantScope,
    ArchiveScope,
    DateRangeScope,
    OwnerScope,
    VisibilityScope,
    StatusScope,
    # Factory functions
    active_scope,
    published_scope,
    verified_scope,
    tenant_scope,
    owner_scope,
    status_scope,
    date_range_scope
)

__all__ = [
    # Core scope classes
    'Scope',
    'ScopeInterface',
    'AnonymousScope', 
    'ConditionalScope',
    'CompositeScope',
    'create_scope',
    'conditional_scope',
    'combine_scopes',
    
    # Management classes
    'GlobalScopeManager',
    'ScopeRegistry',
    
    # Common scopes
    'ActiveScope',
    'PublishedScope',
    'VerifiedScope',
    'TenantScope',
    'ArchiveScope',
    'DateRangeScope',
    'OwnerScope',
    'VisibilityScope',
    'StatusScope',
    
    # Factory functions
    'active_scope',
    'published_scope',
    'verified_scope',
    'tenant_scope',
    'owner_scope',
    'status_scope',
    'date_range_scope'
]