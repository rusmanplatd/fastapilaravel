from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Generic, TypeVar, Iterator
from dataclasses import dataclass
import math
from urllib.parse import urlencode, urlparse, parse_qs

from fastapi import Request
from sqlalchemy.orm import Query
from sqlalchemy import func, select

from .Paginator import PaginationLink, Paginator

T = TypeVar('T')


@dataclass
class PaginationMeta:
    """Pagination metadata for API responses."""
    
    current_page: int
    from_item: Optional[int]
    last_page: int
    links: List[Dict[str, Any]]
    path: str
    per_page: int
    to_item: Optional[int]
    total: int


class LengthAwarePaginator(Paginator[T]):
    """
    Laravel-style Length-Aware Paginator with enhanced features.
    
    This paginator knows the total number of items and can provide
    complete pagination information including total pages, item counts,
    and sophisticated link generation.
    """
    
    def __init__(
        self,
        items: List[T],
        total: int,
        per_page: int,
        current_page: int = 1,
        path: str = "",
        page_name: str = "page",
        query_params: Optional[Dict[str, Any]] = None,
        fragment: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            items=items,
            total=total,
            per_page=per_page,
            current_page=current_page,
            path=path,
            page_name=page_name,
            query_params=query_params,
            fragment=fragment
        )
        
        self.options = options or {}
        self._resolver: Optional[Callable] = None
    
    def with_query_string(self, params: Dict[str, Any]) -> 'LengthAwarePaginator[T]':
        """Add query parameters to pagination URLs."""
        self.query_params.update(params)
        return self
    
    def append_query_string(self, key: str, value: Any) -> 'LengthAwarePaginator[T]':
        """Append a single query parameter."""
        self.query_params[key] = value
        return self
    
    def with_path(self, path: str) -> 'LengthAwarePaginator[T]':
        """Set the base path for pagination URLs."""
        self.path = path
        return self
    
    def get_options(self) -> Dict[str, Any]:
        """Get pagination options."""
        return self.options
    
    def has_pages(self) -> bool:
        """Determine if there are enough items to split across multiple pages."""
        return self.per_page < self.total
    
    def count(self) -> int:
        """Get the number of items on the current page."""
        return len(self.items)
    
    def is_empty(self) -> bool:
        """Determine if the paginator has no items."""
        return len(self.items) == 0
    
    def is_not_empty(self) -> bool:
        """Determine if the paginator has items."""
        return len(self.items) > 0
    
    def get_collection(self) -> List[T]:
        """Get the items being paginated."""
        return self.items
    
    def set_collection(self, items: List[T]) -> 'LengthAwarePaginator[T]':
        """Set the items being paginated."""
        self.items = items
        return self
    
    def transform(self, callback: Callable[[T], Any]) -> 'LengthAwarePaginator[Any]':
        """Transform each item using the given callback."""
        transformed_items = [callback(item) for item in self.items]
        
        return LengthAwarePaginator(
            items=transformed_items,
            total=self.total,
            per_page=self.per_page,
            current_page=self.current_page,
            path=self.path,
            page_name=self.page_name,
            query_params=self.query_params.copy(),
            fragment=self.fragment,
            options=self.options.copy()
        )
    
    def map(self, callback: Callable[[T], Any]) -> 'LengthAwarePaginator[Any]':
        """Map each item using the given callback (alias for transform)."""
        return self.transform(callback)
    
    def filter(self, callback: Callable[[T], bool]) -> 'LengthAwarePaginator[T]':
        """Filter items using the given callback."""
        filtered_items = [item for item in self.items if callback(item)]
        
        return LengthAwarePaginator(
            items=filtered_items,
            total=len(filtered_items),  # Note: This changes the total
            per_page=self.per_page,
            current_page=1,  # Reset to first page
            path=self.path,
            page_name=self.page_name,
            query_params=self.query_params.copy(),
            fragment=self.fragment,
            options=self.options.copy()
        )
    
    def through(self, callback: Callable[['LengthAwarePaginator[T]'], 'LengthAwarePaginator[T]']) -> 'LengthAwarePaginator[T]':
        """Pass the paginator through the given callback."""
        return callback(self)
    
    def when(self, condition: bool, callback: Callable[['LengthAwarePaginator[T]'], 'LengthAwarePaginator[T]']) -> 'LengthAwarePaginator[T]':
        """Apply the callback if the condition is true."""
        if condition:
            return callback(self)
        return self
    
    def unless(self, condition: bool, callback: Callable[['LengthAwarePaginator[T]'], 'LengthAwarePaginator[T]']) -> 'LengthAwarePaginator[T]':
        """Apply the callback if the condition is false."""
        if not condition:
            return callback(self)
        return self
    
    def range(self, start: int, end: int) -> List[int]:
        """Get a range of page numbers."""
        start = max(1, start)
        end = min(self.last_page, end)
        return list(range(start, end + 1))
    
    def get_url_range(self, start: int, end: int) -> Dict[int, str]:
        """Get URLs for a range of pages."""
        urls = {}
        for page in self.range(start, end):
            urls[page] = self.url(page)
        return urls
    
    def links(
        self, 
        view: Optional[str] = None, 
        data: Optional[Dict[str, Any]] = None,
        on_each_side: int = 3,
        on_ends: int = 1
    ) -> List[PaginationLink]:
        """Generate pagination links with customizable view and data."""
        if not self.has_pages():
            return []
        
        # Use the parent class implementation
        return super().links(on_each_side, on_ends)
    
    def simple_links(self, view: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> List[PaginationLink]:
        """Generate simple previous/next links."""
        return super().simple_links()
    
    def render(self, view: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """Render the paginator as HTML."""
        # This would typically integrate with a template engine
        # For now, return a simple HTML representation
        
        if not self.has_pages():
            return ""
        
        links = self.links()
        html_parts = ['<nav aria-label="Pagination">']
        html_parts.append('<ul class="pagination">')
        
        for link in links:
            if link.url is None:
                # Disabled link (dots)
                html_parts.append(f'<li class="page-item disabled"><span class="page-link">{link.label}</span></li>')
            elif link.active:
                # Active page
                html_parts.append(f'<li class="page-item active"><span class="page-link">{link.label}</span></li>')
            else:
                # Regular link
                html_parts.append(f'<li class="page-item"><a class="page-link" href="{link.url}">{link.label}</a></li>')
        
        html_parts.append('</ul>')
        html_parts.append('</nav>')
        
        return '\n'.join(html_parts)
    
    def simple_render(self, view: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """Render simple pagination as HTML."""
        if not self.has_pages():
            return ""
        
        links = self.simple_links()
        html_parts = ['<nav aria-label="Simple Pagination">']
        html_parts.append('<ul class="pagination pagination-simple">')
        
        for link in links:
            html_parts.append(f'<li class="page-item"><a class="page-link" href="{link.url}">{link.label}</a></li>')
        
        html_parts.append('</ul>')
        html_parts.append('</nav>')
        
        return '\n'.join(html_parts)
    
    def get_meta(self) -> PaginationMeta:
        """Get pagination metadata."""
        return PaginationMeta(
            current_page=self.current_page,
            from_item=self.first_item,
            last_page=self.last_page,
            links=[
                {
                    'url': link.url,
                    'label': link.label,
                    'active': link.active
                }
                for link in self.links()
            ],
            path=self.path,
            per_page=self.per_page,
            to_item=self.last_item,
            total=self.total
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paginator to dictionary with Laravel-style structure."""
        return {
            'current_page': self.current_page,
            'data': self.items,
            'first_page_url': self.url(1),
            'from': self.first_item,
            'last_page': self.last_page,
            'last_page_url': self.url(self.last_page),
            'links': [
                {
                    'url': link.url,
                    'label': link.label,
                    'active': link.active
                }
                for link in self.links()
            ],
            'next_page_url': self.next_page_url,
            'path': self.path,
            'per_page': self.per_page,
            'prev_page_url': self.previous_page_url,
            'to': self.last_item,
            'total': self.total
        }
    
    def to_json(self) -> str:
        """Convert paginator to JSON string."""
        import json
        return json.dumps(self.to_dict(), default=str)
    
    def __iter__(self) -> Iterator[T]:
        """Make the paginator iterable."""
        return iter(self.items)
    
    def __len__(self) -> int:
        """Get the number of items on the current page."""
        return len(self.items)
    
    def __getitem__(self, key: int) -> T:
        """Get an item by index."""
        return self.items[key]
    
    def __bool__(self) -> bool:
        """Check if the paginator has items."""
        return len(self.items) > 0
    
    def __repr__(self) -> str:
        """String representation of the paginator."""
        return f'<LengthAwarePaginator: {len(self.items)} items, page {self.current_page} of {self.last_page}>'


class CursorPaginator(Generic[T]):
    """
    Cursor-based paginator for efficient pagination of large datasets.
    
    This is useful for APIs where consistent pagination is required
    even when the underlying data changes.
    """
    
    def __init__(
        self,
        items: List[T],
        per_page: int,
        cursor: Optional[str] = None,
        cursor_name: str = "cursor",
        path: str = "",
        query_params: Optional[Dict[str, Any]] = None,
        has_more: bool = False,
        previous_cursor: Optional[str] = None,
        next_cursor: Optional[str] = None
    ):
        self.items = items
        self.per_page = per_page
        self.cursor = cursor
        self.cursor_name = cursor_name
        self.path = path
        self.query_params = query_params or {}
        self.has_more = has_more
        self.previous_cursor = previous_cursor
        self.next_cursor = next_cursor
        
        # Remove cursor parameter from query params
        self.query_params = {k: v for k, v in self.query_params.items() if k != self.cursor_name}
    
    @property
    def has_pages(self) -> bool:
        """Check if there are more pages available."""
        return self.has_more or self.previous_cursor is not None
    
    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages after this one."""
        return self.has_more
    
    @property
    def has_previous_pages(self) -> bool:
        """Check if there are previous pages."""
        return self.previous_cursor is not None
    
    def url(self, cursor: Optional[str]) -> str:
        """Generate URL for a specific cursor."""
        params = self.query_params.copy()
        
        if cursor:
            params[self.cursor_name] = cursor
        elif self.cursor_name in params:
            del params[self.cursor_name]
        
        query_string = urlencode(params)
        url = self.path
        
        if query_string:
            url += "?" + query_string
        
        return url
    
    @property
    def previous_page_url(self) -> Optional[str]:
        """Get URL for the previous page."""
        if not self.has_previous_pages:
            return None
        return self.url(self.previous_cursor)
    
    @property
    def next_page_url(self) -> Optional[str]:
        """Get URL for the next page."""
        if not self.has_more_pages:
            return None
        return self.url(self.next_cursor)
    
    def links(self) -> List[PaginationLink]:
        """Generate simple previous/next links for cursor pagination."""
        links = []
        
        if self.has_previous_pages:
            links.append(PaginationLink(
                url=self.previous_page_url,
                label="« Previous"
            ))
        
        if self.has_more_pages:
            links.append(PaginationLink(
                url=self.next_page_url,
                label="Next »"
            ))
        
        return links
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cursor paginator to dictionary."""
        return {
            'data': self.items,
            'per_page': self.per_page,
            'path': self.path,
            'next_cursor': self.next_cursor,
            'next_page_url': self.next_page_url,
            'prev_cursor': self.previous_cursor,
            'prev_page_url': self.previous_page_url,
            'links': [
                {
                    'url': link.url,
                    'label': link.label,
                    'active': link.active
                }
                for link in self.links()
            ]
        }
    
    def __iter__(self) -> Iterator[T]:
        """Make the paginator iterable."""
        return iter(self.items)
    
    def __len__(self) -> int:
        """Get the number of items on the current page."""
        return len(self.items)
    
    def __getitem__(self, key: int) -> T:
        """Get an item by index."""
        return self.items[key]
    
    def __bool__(self) -> bool:
        """Check if the paginator has items."""
        return len(self.items) > 0