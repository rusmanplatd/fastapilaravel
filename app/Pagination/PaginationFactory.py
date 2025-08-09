from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type, Protocol
import math
import base64
import json
from urllib.parse import urlencode

from fastapi import Request, Depends
from sqlalchemy.orm import Query, Session
from sqlalchemy import func, select, text, desc, asc
from sqlalchemy.sql.expression import BinaryExpression

from .Paginator import Paginator, SimplePaginator
from .LengthAwarePaginator import LengthAwarePaginator, CursorPaginator

T = TypeVar('T')


class PaginationProtocol(Protocol):
    """Protocol for pagination objects."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        ...


class PaginationFactory:
    """
    Factory class for creating various types of paginators.
    
    This provides a centralized way to create paginators with
    consistent configuration and behavior.
    """
    
    def __init__(
        self,
        default_per_page: int = 15,
        max_per_page: int = 100,
        page_name: str = "page",
        per_page_name: str = "per_page"
    ):
        self.default_per_page = default_per_page
        self.max_per_page = max_per_page
        self.page_name = page_name
        self.per_page_name = per_page_name
        self.resolvers: Dict[str, Callable] = {}
    
    def set_default_per_page(self, per_page: int) -> 'PaginationFactory':
        """Set the default items per page."""
        self.default_per_page = per_page
        return self
    
    def set_max_per_page(self, max_per_page: int) -> 'PaginationFactory':
        """Set the maximum items per page."""
        self.max_per_page = max_per_page
        return self
    
    def set_page_name(self, page_name: str) -> 'PaginationFactory':
        """Set the page parameter name."""
        self.page_name = page_name
        return self
    
    def set_per_page_name(self, per_page_name: str) -> 'PaginationFactory':
        """Set the per_page parameter name."""
        self.per_page_name = per_page_name
        return self
    
    def resolve_current_page(self, request: Optional[Request] = None, page_name: Optional[str] = None) -> int:
        """Resolve the current page from the request."""
        if not request:
            return 1
        
        page_param = page_name or self.page_name
        
        try:
            page = int(request.query_params.get(page_param, 1))
            return max(1, page)
        except (ValueError, TypeError):
            return 1
    
    def resolve_per_page(self, request: Optional[Request] = None, per_page_name: Optional[str] = None) -> int:
        """Resolve the per_page from the request."""
        if not request:
            return self.default_per_page
        
        per_page_param = per_page_name or self.per_page_name
        
        try:
            per_page = int(request.query_params.get(per_page_param, self.default_per_page))
            return min(max(1, per_page), self.max_per_page)
        except (ValueError, TypeError):
            return self.default_per_page
    
    def make(
        self,
        items: List[T],
        total: int,
        per_page: Optional[int] = None,
        current_page: Optional[int] = None,
        request: Optional[Request] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> LengthAwarePaginator[T]:
        """Create a length-aware paginator."""
        per_page = per_page or self.resolve_per_page(request)
        current_page = current_page or self.resolve_current_page(request)
        
        path = ""
        query_params = {}
        
        if request:
            path = str(request.url).split('?')[0]  # type: ignore[attr-defined]
            query_params = dict(request.query_params)
        
        return LengthAwarePaginator(
            items=items,
            total=total,
            per_page=per_page,
            current_page=current_page,
            path=path,
            page_name=self.page_name,
            query_params=query_params,
            options=options or {}
        )
    
    def simple(
        self,
        items: List[T],
        per_page: Optional[int] = None,
        current_page: Optional[int] = None,
        request: Optional[Request] = None,
        has_more: bool = False
    ) -> SimplePaginator[T]:
        """Create a simple paginator."""
        per_page = per_page or self.resolve_per_page(request)
        current_page = current_page or self.resolve_current_page(request)
        
        path = ""
        query_params = {}
        
        if request:
            path = str(request.url).split('?')[0]  # type: ignore[attr-defined]
            query_params = dict(request.query_params)
        
        return SimplePaginator(
            items=items,
            per_page=per_page,
            current_page=current_page,
            path=path,
            page_name=self.page_name,
            query_params=query_params,
            has_more=has_more
        )
    
    def cursor(
        self,
        items: List[T],
        per_page: Optional[int] = None,
        cursor: Optional[str] = None,
        request: Optional[Request] = None,
        has_more: bool = False,
        previous_cursor: Optional[str] = None,
        next_cursor: Optional[str] = None,
        cursor_name: str = "cursor"
    ) -> CursorPaginator[T]:
        """Create a cursor paginator."""
        per_page = per_page or self.resolve_per_page(request)
        
        if request and cursor is None:
            cursor = request.query_params.get(cursor_name)
        
        path = ""
        query_params = {}
        
        if request:
            path = str(request.url).split('?')[0]  # type: ignore[attr-defined]
            query_params = dict(request.query_params)
        
        return CursorPaginator(
            items=items,
            per_page=per_page,
            cursor=cursor,
            cursor_name=cursor_name,
            path=path,
            query_params=query_params,
            has_more=has_more,
            previous_cursor=previous_cursor,
            next_cursor=next_cursor
        )


class QueryPaginator:
    """
    Advanced query paginator with SQLAlchemy integration.
    
    Provides sophisticated pagination capabilities including
    cursor-based pagination, custom sorting, and filtering.
    """
    
    def __init__(self, factory: PaginationFactory):
        self.factory = factory
    
    def paginate(
        self,
        query: Query[T],
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        request: Optional[Request] = None,
        columns: Optional[List[str]] = None
    ) -> LengthAwarePaginator[T]:
        """Paginate a SQLAlchemy query with total count."""
        page = page or self.factory.resolve_current_page(request)
        per_page = per_page or self.factory.resolve_per_page(request)
        
        # Get total count
        count_query = query.statement.with_only_columns(func.count())
        total = query.session.execute(count_query).scalar()
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get items for current page
        if columns:
            # Select specific columns
            items = query.with_entities(*columns).offset(offset).limit(per_page).all()
        else:
            items = query.offset(offset).limit(per_page).all()
        
        return self.factory.make(
            items=items,
            total=total,
            per_page=per_page,
            current_page=page,
            request=request
        )
    
    def simple_paginate(
        self,
        query: Query[T],
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        request: Optional[Request] = None,
        columns: Optional[List[str]] = None
    ) -> SimplePaginator[T]:
        """Simple paginate a SQLAlchemy query without total count."""
        page = page or self.factory.resolve_current_page(request)
        per_page = per_page or self.factory.resolve_per_page(request)
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get items for current page + 1 to check if there are more
        if columns:
            items = query.with_entities(*columns).offset(offset).limit(per_page + 1).all()
        else:
            items = query.offset(offset).limit(per_page + 1).all()
        
        # Check if there are more items
        has_more = len(items) > per_page
        
        # Remove the extra item if it exists
        if has_more:
            items = items[:-1]
        
        return self.factory.simple(
            items=items,
            per_page=per_page,
            current_page=page,
            request=request,
            has_more=has_more
        )
    
    def cursor_paginate(
        self,
        query: Query[T],
        cursor_column: str,
        per_page: Optional[int] = None,
        cursor: Optional[str] = None,
        request: Optional[Request] = None,
        direction: str = "asc",
        cursor_name: str = "cursor"
    ) -> CursorPaginator[T]:
        """Cursor-based pagination for efficient large dataset pagination."""
        per_page = per_page or self.factory.resolve_per_page(request)
        
        if request and cursor is None:
            cursor = request.query_params.get(cursor_name)
        
        # Decode cursor if provided
        cursor_value = None
        if cursor:
            try:
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                cursor_value = cursor_data.get('value')
            except (ValueError, json.JSONDecodeError):
                cursor_value = None
        
        # Build the query with cursor condition
        if cursor_value is not None:
            column = getattr(query.column_descriptions[0]['type'], cursor_column)
            if direction.lower() == "desc":
                query = query.filter(column < cursor_value).order_by(desc(column))
            else:
                query = query.filter(column > cursor_value).order_by(asc(column))
        else:
            column = getattr(query.column_descriptions[0]['type'], cursor_column)
            if direction.lower() == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(asc(column))
        
        # Get items + 1 to check if there are more
        items = query.limit(per_page + 1).all()
        
        # Check if there are more items
        has_more = len(items) > per_page
        
        # Remove the extra item if it exists
        if has_more:
            items = items[:-1]
        
        # Generate next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            cursor_val = getattr(last_item, cursor_column)
            next_cursor_data = {'value': cursor_val, 'direction': direction}
            next_cursor = base64.b64encode(
                json.dumps(next_cursor_data, default=str).encode()
            ).decode()
        
        # Generate previous cursor (simplified - in production you'd need more logic)
        previous_cursor = None
        
        return self.factory.cursor(
            items=items,
            per_page=per_page,
            cursor=cursor,
            request=request,
            has_more=has_more,
            previous_cursor=previous_cursor,
            next_cursor=next_cursor,
            cursor_name=cursor_name
        )


class PaginationHelper:
    """
    Helper class for common pagination operations and utilities.
    """
    
    @staticmethod
    def get_pagination_info(request: Request) -> Dict[str, Any]:
        """Extract pagination information from request."""
        return {
            'page': PaginationHelper.get_page(request),
            'per_page': PaginationHelper.get_per_page(request),
            'sort': request.query_params.get('sort'),
            'order': request.query_params.get('order', 'asc'),
            'search': request.query_params.get('search'),
            'filters': {
                k: v for k, v in request.query_params.items()
                if k not in ['page', 'per_page', 'sort', 'order', 'search']
            }
        }
    
    @staticmethod
    def get_page(request: Request, default: int = 1) -> int:
        """Get page number from request."""
        try:
            return max(1, int(request.query_params.get('page', default)))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_per_page(request: Request, default: int = 15, max_per_page: int = 100) -> int:
        """Get per_page from request."""
        try:
            per_page = int(request.query_params.get('per_page', default))
            return min(max(1, per_page), max_per_page)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def create_pagination_response(
        data: List[Any],
        paginator: PaginationProtocol,
        meta_key: str = "meta",
        links_key: str = "links"
    ) -> Dict[str, Any]:
        """Create a standardized pagination response."""
        pagination_dict = paginator.to_dict()
        
        response = {
            "data": data,
            meta_key: {
                "current_page": pagination_dict.get("current_page"),
                "from": pagination_dict.get("from"),
                "last_page": pagination_dict.get("last_page"),
                "path": pagination_dict.get("path"),
                "per_page": pagination_dict.get("per_page"),
                "to": pagination_dict.get("to"),
                "total": pagination_dict.get("total")
            }
        }
        
        if "links" in pagination_dict:
            response[links_key] = pagination_dict["links"]
        
        return response
    
    @staticmethod
    def calculate_page_range(current_page: int, last_page: int, delta: int = 2) -> List[int]:
        """Calculate a range of pages around the current page."""
        start = max(1, current_page - delta)
        end = min(last_page, current_page + delta)
        return list(range(start, end + 1))
    
    @staticmethod
    def generate_page_title(current_page: int, last_page: int, base_title: str = "Page") -> str:
        """Generate a page title for SEO."""
        if current_page == 1:
            return base_title
        return f"{base_title} - Page {current_page} of {last_page}"


# Global pagination factory instance
pagination_factory = PaginationFactory()

# Convenience functions using the global factory
def paginate(
    items: List[T],
    total: int,
    per_page: Optional[int] = None,
    current_page: Optional[int] = None,
    request: Optional[Request] = None,
    options: Optional[Dict[str, Any]] = None
) -> LengthAwarePaginator[T]:
    """Create a length-aware paginator using the global factory."""
    return pagination_factory.make(items, total, per_page, current_page, request, options)


def simple_paginate(
    items: List[T],
    per_page: Optional[int] = None,
    current_page: Optional[int] = None,
    request: Optional[Request] = None,
    has_more: bool = False
) -> SimplePaginator[T]:
    """Create a simple paginator using the global factory."""
    return pagination_factory.simple(items, per_page, current_page, request, has_more)


def cursor_paginate(
    items: List[T],
    per_page: Optional[int] = None,
    cursor: Optional[str] = None,
    request: Optional[Request] = None,
    has_more: bool = False,
    previous_cursor: Optional[str] = None,
    next_cursor: Optional[str] = None,
    cursor_name: str = "cursor"
) -> CursorPaginator[T]:
    """Create a cursor paginator using the global factory."""
    return pagination_factory.cursor(
        items, per_page, cursor, request, has_more, 
        previous_cursor, next_cursor, cursor_name
    )


# Query paginator instance
query_paginator = QueryPaginator(pagination_factory)