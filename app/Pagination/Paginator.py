"""
Laravel-style Pagination System
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Union, Callable, Generic, TypeVar
from dataclasses import dataclass
from urllib.parse import urlencode

from fastapi import Request
from sqlalchemy.orm import Query
from sqlalchemy import func, select

T = TypeVar('T')


@dataclass
class PaginationLink:
    """Represents a pagination link"""
    url: Optional[str]
    label: str
    active: bool = False


class Paginator(Generic[T]):
    """Laravel-style paginator"""
    
    def __init__(
        self,
        items: List[T],
        total: int,
        per_page: int,
        current_page: int = 1,
        path: str = "",
        page_name: str = "page",
        query_params: Optional[Dict[str, Any]] = None,
        fragment: Optional[str] = None
    ):
        self.items = items
        self.total = total
        self.per_page = per_page
        self.current_page = max(1, current_page)
        self.path = path
        self.page_name = page_name
        self.query_params = query_params or {}
        self.fragment = fragment
        
        # Remove page parameter from query params to avoid conflicts
        self.query_params = {k: v for k, v in self.query_params.items() if k != self.page_name}
    
    @property
    def last_page(self) -> int:
        """Get the last page number"""
        return max(1, math.ceil(self.total / self.per_page))
    
    @property
    def has_pages(self) -> bool:
        """Check if there are enough items to split across multiple pages"""
        return self.total > self.per_page
    
    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages available"""
        return self.current_page < self.last_page
    
    @property
    def on_first_page(self) -> bool:
        """Check if we're on the first page"""
        return self.current_page <= 1
    
    @property
    def on_last_page(self) -> bool:
        """Check if we're on the last page"""
        return self.current_page >= self.last_page
    
    @property
    def first_item(self) -> Optional[int]:
        """Get the index of the first item on the current page"""
        if self.total == 0:
            return None
        return (self.current_page - 1) * self.per_page + 1
    
    @property
    def last_item(self) -> Optional[int]:
        """Get the index of the last item on the current page"""
        if self.total == 0:
            return None
        return min(self.current_page * self.per_page, self.total)
    
    @property
    def previous_page_url(self) -> Optional[str]:
        """Get URL for the previous page"""
        if self.current_page <= 1:
            return None
        return self.url(self.current_page - 1)
    
    @property
    def next_page_url(self) -> Optional[str]:
        """Get URL for the next page"""
        if self.current_page >= self.last_page:
            return None
        return self.url(self.current_page + 1)
    
    def url(self, page: int) -> str:
        """Generate URL for a specific page"""
        params = self.query_params.copy()
        params[self.page_name] = page
        
        query_string = urlencode(params)
        url = self.path
        
        if query_string:
            url += "?" + query_string
        
        if self.fragment:
            url += "#" + self.fragment
        
        return url
    
    def get_url_range(self, start: int, end: int) -> Dict[int, str]:
        """Get URLs for a range of pages"""
        urls = {}
        for page in range(max(1, start), min(end + 1, self.last_page + 1)):
            urls[page] = self.url(page)
        return urls
    
    def links(self, on_each_side: int = 3, on_ends: int = 1) -> List[PaginationLink]:
        """Generate pagination links with smart truncation"""
        if not self.has_pages:
            return []
        
        links = []
        
        # Previous link
        if self.current_page > 1:
            links.append(PaginationLink(
                url=self.previous_page_url,
                label="« Previous"
            ))
        
        # Generate page links
        window_start = max(1, self.current_page - on_each_side)
        window_end = min(self.last_page, self.current_page + on_each_side)
        
        # Add first pages
        if window_start > on_ends + 1:
            for page in range(1, on_ends + 1):
                links.append(PaginationLink(
                    url=self.url(page),
                    label=str(page),
                    active=(page == self.current_page)
                ))
            
            # Add dots if there's a gap
            if window_start > on_ends + 2:
                links.append(PaginationLink(
                    url=None,
                    label="..."
                ))
        
        # Add window pages
        for page in range(window_start, window_end + 1):
            links.append(PaginationLink(
                url=self.url(page),
                label=str(page),
                active=(page == self.current_page)
            ))
        
        # Add last pages
        if window_end < self.last_page - on_ends:
            # Add dots if there's a gap
            if window_end < self.last_page - on_ends - 1:
                links.append(PaginationLink(
                    url=None,
                    label="..."
                ))
            
            for page in range(self.last_page - on_ends + 1, self.last_page + 1):
                links.append(PaginationLink(
                    url=self.url(page),
                    label=str(page),
                    active=(page == self.current_page)
                ))
        
        # Next link
        if self.current_page < self.last_page:
            links.append(PaginationLink(
                url=self.next_page_url,
                label="Next »"
            ))
        
        return links
    
    def simple_links(self) -> List[PaginationLink]:
        """Generate simple previous/next links"""
        links = []
        
        if self.current_page > 1:
            links.append(PaginationLink(
                url=self.previous_page_url,
                label="« Previous"
            ))
        
        if self.current_page < self.last_page:
            links.append(PaginationLink(
                url=self.next_page_url,
                label="Next »"
            ))
        
        return links
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paginator to dictionary"""
        return {
            'data': self.items,
            'current_page': self.current_page,
            'per_page': self.per_page,
            'total': self.total,
            'last_page': self.last_page,
            'from': self.first_item,
            'to': self.last_item,
            'path': self.path,
            'first_page_url': self.url(1),
            'last_page_url': self.url(self.last_page),
            'next_page_url': self.next_page_url,
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


class SimplePaginator(Generic[T]):
    """Simple paginator that only shows previous/next links"""
    
    def __init__(
        self,
        items: List[T],
        per_page: int,
        current_page: int = 1,
        path: str = "",
        page_name: str = "page",
        query_params: Optional[Dict[str, Any]] = None,
        has_more: bool = False
    ):
        self.items = items
        self.per_page = per_page
        self.current_page = max(1, current_page)
        self.path = path
        self.page_name = page_name
        self.query_params = query_params or {}
        self.has_more = has_more
        
        # Remove page parameter from query params
        self.query_params = {k: v for k, v in self.query_params.items() if k != self.page_name}
    
    @property
    def first_item(self) -> Optional[int]:
        """Get the index of the first item on the current page"""
        if len(self.items) == 0:
            return None
        return (self.current_page - 1) * self.per_page + 1
    
    @property
    def last_item(self) -> Optional[int]:
        """Get the index of the last item on the current page"""
        if len(self.items) == 0:
            return None
        return (self.current_page - 1) * self.per_page + len(self.items)
    
    @property
    def on_first_page(self) -> bool:
        """Check if we're on the first page"""
        return self.current_page <= 1
    
    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages available"""
        return self.has_more or len(self.items) >= self.per_page
    
    @property
    def previous_page_url(self) -> Optional[str]:
        """Get URL for the previous page"""
        if self.current_page <= 1:
            return None
        return self.url(self.current_page - 1)
    
    @property
    def next_page_url(self) -> Optional[str]:
        """Get URL for the next page"""
        if not self.has_more_pages:
            return None
        return self.url(self.current_page + 1)
    
    def url(self, page: int) -> str:
        """Generate URL for a specific page"""
        params = self.query_params.copy()
        params[self.page_name] = page
        
        query_string = urlencode(params)
        url = self.path
        
        if query_string:
            url += "?" + query_string
        
        return url
    
    def links(self) -> List[PaginationLink]:
        """Generate simple previous/next links"""
        links = []
        
        if self.current_page > 1:
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
        """Convert simple paginator to dictionary"""
        return {
            'data': self.items,
            'current_page': self.current_page,
            'per_page': self.per_page,
            'from': self.first_item,
            'to': self.last_item,
            'path': self.path,
            'next_page_url': self.next_page_url,
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


class LengthAwarePaginator(Paginator[T]):
    """Length-aware paginator (knows total count)"""
    pass


def paginate(
    query: Query,
    page: int = 1,
    per_page: int = 15,
    request: Optional[Request] = None,
    page_name: str = "page"
) -> Paginator:
    """Paginate a SQLAlchemy query"""
    
    # Get total count
    total = query.count()
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get items for current page
    items = query.offset(offset).limit(per_page).all()
    
    # Build pagination info
    path = ""
    query_params = {}
    
    if request:
        path = str(request.url).split('?')[0]
        query_params = dict(request.query_params)
    
    return Paginator(
        items=items,
        total=total,
        per_page=per_page,
        current_page=page,
        path=path,
        page_name=page_name,
        query_params=query_params
    )


def simple_paginate(
    query: Query,
    page: int = 1,
    per_page: int = 15,
    request: Optional[Request] = None,
    page_name: str = "page"
) -> SimplePaginator:
    """Simple paginate a SQLAlchemy query"""
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get items for current page + 1 to check if there are more
    items = query.offset(offset).limit(per_page + 1).all()
    
    # Check if there are more items
    has_more = len(items) > per_page
    
    # Remove the extra item if it exists
    if has_more:
        items = items[:-1]
    
    # Build pagination info
    path = ""
    query_params = {}
    
    if request:
        path = str(request.url).split('?')[0]
        query_params = dict(request.query_params)
    
    return SimplePaginator(
        items=items,
        per_page=per_page,
        current_page=page,
        path=path,
        page_name=page_name,
        query_params=query_params,
        has_more=has_more
    )