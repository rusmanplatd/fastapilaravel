"""
Laravel-style Pagination System for FastAPI

This module provides comprehensive pagination capabilities including:
- Length-aware pagination with total counts
- Simple pagination for performance
- Cursor-based pagination for large datasets
- FastAPI dependencies and middleware
- Multiple response formats (Laravel, JSON:API, custom)
"""

from .Paginator import Paginator, SimplePaginator, PaginationLink, paginate, simple_paginate
from .LengthAwarePaginator import LengthAwarePaginator, CursorPaginator, PaginationMeta
from .PaginationFactory import (
    PaginationFactory, QueryPaginator, PaginationHelper,
    pagination_factory, query_paginator
)
from .Dependencies import (
    PaginationParams, PaginationDependency, QueryPaginationDependency,
    PaginationResponse, BasicPagination, SmallPagePagination, LargePagePagination,
    create_pagination_dependency, create_model_pagination_dependency,
    get_pagination_params, get_simple_pagination_params,
    PaginationDep, SimplePaginationDep
)
from .Middleware import (
    PaginationMiddleware, PaginationCacheMiddleware, PaginationLoggingMiddleware
)

__all__ = [
    # Core pagination classes
    "Paginator",
    "SimplePaginator", 
    "LengthAwarePaginator",
    "CursorPaginator",
    "PaginationLink",
    "PaginationMeta",
    
    # Factory and utilities
    "PaginationFactory",
    "QueryPaginator", 
    "PaginationHelper",
    "pagination_factory",
    "query_paginator",
    
    # Dependencies
    "PaginationParams",
    "PaginationDependency",
    "QueryPaginationDependency", 
    "PaginationResponse",
    "BasicPagination",
    "SmallPagePagination",
    "LargePagePagination",
    "create_pagination_dependency",
    "create_model_pagination_dependency",
    "get_pagination_params",
    "get_simple_pagination_params",
    "PaginationDep",
    "SimplePaginationDep",
    
    # Middleware
    "PaginationMiddleware",
    "PaginationCacheMiddleware", 
    "PaginationLoggingMiddleware",
    
    # Convenience functions
    "paginate",
    "simple_paginate",
]