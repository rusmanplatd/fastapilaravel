from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Type, Annotated
from dataclasses import dataclass

from fastapi import Request, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query as SQLQuery

from .PaginationFactory import pagination_factory, query_paginator, PaginationHelper
from .LengthAwarePaginator import LengthAwarePaginator
from .Paginator import SimplePaginator
# from .CursorPaginator import CursorPaginator  # TODO: Implement CursorPaginator


@dataclass
class PaginationParams:
    """Data class for pagination parameters."""
    page: int
    per_page: int
    sort: Optional[str] = None
    order: str = "asc"
    search: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        if self.filters is None:
            self.filters = {}


class PaginationDependency:
    """
    FastAPI dependency for automatic pagination parameter extraction.
    
    This can be used as a dependency in FastAPI routes to automatically
    extract and validate pagination parameters from the request.
    """
    
    def __init__(
        self,
        default_per_page: int = 15,
        max_per_page: int = 100,
        default_sort: Optional[str] = None,
        allowed_sorts: Optional[List[str]] = None,
        default_order: str = "asc"
    ):
        self.default_per_page = default_per_page
        self.max_per_page = max_per_page
        self.default_sort = default_sort
        self.allowed_sorts = allowed_sorts or []
        self.default_order = default_order
    
    def __call__(
        self,
        request: Request,
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        per_page: Annotated[Optional[int], Query(ge=1, le=100, description="Items per page")] = None,
        sort: Annotated[Optional[str], Query(description="Sort field")] = None,
        order: Annotated[str, Query(regex="^(asc|desc)$", description="Sort order")] = "asc",
        search: Annotated[Optional[str], Query(description="Search query")] = None
    ) -> PaginationParams:
        """Extract pagination parameters from request."""
        
        # Validate per_page
        if per_page is None:
            per_page = self.default_per_page
        else:
            per_page = min(max(1, per_page), self.max_per_page)
        
        # Validate sort field
        if sort and self.allowed_sorts and sort not in self.allowed_sorts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort field. Allowed: {', '.join(self.allowed_sorts)}"
            )
        
        if not sort:
            sort = self.default_sort
        
        # Extract additional filters
        filters = {}
        for key, value in request.query_params.items():
            if key not in ['page', 'per_page', 'sort', 'order', 'search']:
                filters[key] = value
        
        return PaginationParams(
            page=page,
            per_page=per_page,
            sort=sort,
            order=order,
            search=search,
            filters=filters
        )


class QueryPaginationDependency:
    """
    FastAPI dependency for automatic query pagination.
    
    This dependency automatically paginates SQLAlchemy queries
    and returns paginated results.
    """
    
    def __init__(
        self,
        query_builder: Callable[[Session, PaginationParams], SQLQuery],
        session_dependency: Callable = Depends,
        pagination_dependency: Optional[PaginationDependency] = None
    ):
        self.query_builder = query_builder
        self.session_dependency = session_dependency
        self.pagination_dependency = pagination_dependency or PaginationDependency()
    
    def __call__(
        self,
        request: Request,
        pagination_params: PaginationParams,
        db: Session
    ) -> Any:
        """Build and paginate query."""
        
        # Build the query using the provided builder
        query = self.query_builder(db, pagination_params)
        
        # Apply sorting if specified
        if pagination_params.sort:
            try:
                sort_column = getattr(query.column_descriptions[0]['type'], pagination_params.sort)
                if pagination_params.order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            except AttributeError:
                # Sort column doesn't exist, ignore
                pass
        
        # Apply search if specified
        if pagination_params.search:
            # This is a simplified search implementation
            # In practice, you'd want more sophisticated search logic
            pass
        
        # Paginate the query
        return query_paginator.paginate(
            query=query,
            page=pagination_params.page,
            per_page=pagination_params.per_page,
            request=request
        )


def create_pagination_dependency(
    default_per_page: int = 15,
    max_per_page: int = 100,
    default_sort: Optional[str] = None,
    allowed_sorts: Optional[List[str]] = None,
    default_order: str = "asc"
) -> PaginationDependency:
    """Factory function to create pagination dependencies with custom settings."""
    return PaginationDependency(
        default_per_page=default_per_page,
        max_per_page=max_per_page,
        default_sort=default_sort,
        allowed_sorts=allowed_sorts,
        default_order=default_order
    )


def create_model_pagination_dependency(
    model_class: Type[Any],
    default_per_page: int = 15,
    max_per_page: int = 100,
    searchable_fields: Optional[List[str]] = None,
    filterable_fields: Optional[List[str]] = None,
    sortable_fields: Optional[List[str]] = None
) -> Any:
    """
    Create a model-specific pagination dependency.
    
    This creates a dependency that automatically handles pagination,
    searching, filtering, and sorting for a specific model.
    """
    
    def query_builder(db: Session, params: PaginationParams) -> Any:
        """Build query for the model with filtering and searching."""
        query = db.query(model_class)
        
        # Apply search
        if params.search and searchable_fields:
            search_conditions = []
            for field in searchable_fields:
                if hasattr(model_class, field):
                    column = getattr(model_class, field)
                    search_conditions.append(column.ilike(f"%{params.search}%"))
            
            if search_conditions:
                from sqlalchemy import or_
                # Type ignore for SQLAlchemy compatibility
                query = query.filter(or_(*search_conditions))  # type: ignore
        
        # Apply filters
        if params.filters and filterable_fields:
            for field, value in params.filters.items():
                if field in filterable_fields and hasattr(model_class, field):
                    column = getattr(model_class, field)
                    query = query.filter(column == value)
        
        return query
    
    pagination_dep = create_pagination_dependency(
        default_per_page=default_per_page,
        max_per_page=max_per_page,
        allowed_sorts=sortable_fields
    )
    
    return QueryPaginationDependency(
        query_builder=query_builder,
        pagination_dependency=pagination_dep
    )


# Pre-configured dependencies for common use cases
BasicPagination = PaginationDependency()

SmallPagePagination = create_pagination_dependency(
    default_per_page=10,
    max_per_page=50
)

LargePagePagination = create_pagination_dependency(
    default_per_page=50,
    max_per_page=500
)


class PaginationResponse:
    """
    Helper class for creating standardized pagination responses.
    """
    
    @staticmethod
    def create(
        data: List[Any],
        paginator: Union[LengthAwarePaginator[Any], SimplePaginator[Any]],
        meta_key: str = "meta",
        links_key: str = "links"
    ) -> Dict[str, Any]:
        """Create a standardized pagination response."""
        return PaginationHelper.create_pagination_response(
            data=data,
            paginator=paginator,
            meta_key=meta_key,
            links_key=links_key
        )
    
    @staticmethod
    def json_api(
        data: List[Any],
        paginator: LengthAwarePaginator[Any],
        included: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Create a JSON:API compliant pagination response."""
        pagination_dict = paginator.to_dict()
        
        response = {
            "data": data,
            "meta": {
                "pagination": {
                    "current_page": pagination_dict["current_page"],
                    "from": pagination_dict["from"],
                    "last_page": pagination_dict["last_page"],
                    "per_page": pagination_dict["per_page"],
                    "to": pagination_dict["to"],
                    "total": pagination_dict["total"]
                }
            },
            "links": {
                "first": pagination_dict["first_page_url"],
                "last": pagination_dict["last_page_url"],
                "prev": pagination_dict["prev_page_url"],
                "next": pagination_dict["next_page_url"],
                "self": pagination_dict["path"]
            }
        }
        
        if included:
            response["included"] = included
        
        return response
    
    @staticmethod
    def cursor(
        data: List[Any],
        paginator: Any,  # CursorPaginator - TODO: Implement CursorPaginator
        meta_key: str = "meta"
    ) -> Dict[str, Any]:
        """Create a cursor pagination response."""
        pagination_dict = paginator.to_dict()
        
        return {
            "data": data,
            meta_key: {
                "per_page": pagination_dict["per_page"],
                "path": pagination_dict["path"],
                "next_cursor": pagination_dict["next_cursor"],
                "prev_cursor": pagination_dict["prev_cursor"],
                "has_more": paginator.has_more_pages,
                "has_previous": paginator.has_previous_pages
            },
            "links": {
                "next": pagination_dict["next_page_url"],
                "prev": pagination_dict["prev_page_url"]
            }
        }


# Convenience functions that can be used as dependencies
def get_pagination_params(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 15,
    sort: Annotated[Optional[str], Query()] = None,
    order: Annotated[str, Query(regex="^(asc|desc)$")] = "asc",
    search: Annotated[Optional[str], Query()] = None
) -> PaginationParams:
    """Simple pagination parameters dependency."""
    filters = {}
    for key, value in request.query_params.items():
        if key not in ['page', 'per_page', 'sort', 'order', 'search']:
            filters[key] = value
    
    return PaginationParams(
        page=page,
        per_page=min(per_page, 100),  # Enforce max
        sort=sort,
        order=order,
        search=search,
        filters=filters
    )


def get_simple_pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 15
) -> Dict[str, int]:
    """Minimal pagination parameters dependency."""
    return {
        "page": page,
        "per_page": min(per_page, 100)
    }


# Type aliases for common dependency patterns
PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]
SimplePaginationDep = Annotated[Dict[str, int], Depends(get_simple_pagination_params)]