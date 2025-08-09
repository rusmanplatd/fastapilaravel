from __future__ import annotations

from typing import Optional, List


class QueryBuilderException(Exception):
    """Base exception for QueryBuilder"""
    pass


class InvalidFilterQueryException(QueryBuilderException):
    """Exception raised when an invalid filter is used"""
    
    def __init__(self, unknown_filters: List[str], allowed_filters: List[str]) -> None:
        self.unknown_filters = unknown_filters
        self.allowed_filters = allowed_filters
        
        filters_str = ", ".join(unknown_filters)
        allowed_str = ", ".join(allowed_filters)
        
        super().__init__(
            f"Requested filter(s) `{filters_str}` are not allowed. "
            f"Allowed filter(s) are `{allowed_str}`."
        )


class InvalidSortQueryException(QueryBuilderException):
    """Exception raised when an invalid sort is used"""
    
    def __init__(self, unknown_sorts: List[str], allowed_sorts: List[str]) -> None:
        self.unknown_sorts = unknown_sorts
        self.allowed_sorts = allowed_sorts
        
        sorts_str = ", ".join(unknown_sorts)
        allowed_str = ", ".join(allowed_sorts)
        
        super().__init__(
            f"Requested sort(s) `{sorts_str}` are not allowed. "
            f"Allowed sort(s) are `{allowed_str}`."
        )


class InvalidIncludeQueryException(QueryBuilderException):
    """Exception raised when an invalid include is used"""
    
    def __init__(self, unknown_includes: List[str], allowed_includes: List[str]) -> None:
        self.unknown_includes = unknown_includes
        self.allowed_includes = allowed_includes
        
        includes_str = ", ".join(unknown_includes)
        allowed_str = ", ".join(allowed_includes)
        
        super().__init__(
            f"Requested include(s) `{includes_str}` are not allowed. "
            f"Allowed include(s) are `{allowed_str}`."
        )


class InvalidFieldQueryException(QueryBuilderException):
    """Exception raised when an invalid field is used"""
    
    def __init__(self, unknown_fields: List[str], allowed_fields: List[str]) -> None:
        self.unknown_fields = unknown_fields
        self.allowed_fields = allowed_fields
        
        fields_str = ", ".join(unknown_fields)
        allowed_str = ", ".join(allowed_fields)
        
        super().__init__(
            f"Requested field(s) `{fields_str}` are not allowed. "
            f"Allowed field(s) are `{allowed_str}`."
        )