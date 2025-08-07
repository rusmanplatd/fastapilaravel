from __future__ import annotations

from typing import Dict, List, Any, Optional, Union
from starlette.requests import Request
from urllib.parse import parse_qs
import re


class QueryBuilderRequest:
    """
    Handles parsing of query parameters for QueryBuilder
    Inspired by Spatie Laravel Query Builder
    """
    
    # Default parameter names
    INCLUDE_PARAMETER = "include"
    FILTER_PARAMETER = "filter"
    SORT_PARAMETER = "sort"
    FIELDS_PARAMETER = "fields"
    APPEND_PARAMETER = "append"
    
    # Default array value delimiter
    _array_delimiter = ","
    _includes_delimiter: Optional[str] = None
    _filters_delimiter: Optional[str] = None
    _sorts_delimiter: Optional[str] = None
    _fields_delimiter: Optional[str] = None
    _appends_delimiter: Optional[str] = None
    
    def __init__(self, request: Request) -> None:
        self.request = request
        self._query_params = dict(request.query_params)
        self._parsed_filters: Optional[Dict[str, Any]] = None
        self._parsed_includes: Optional[List[str]] = None
        self._parsed_sorts: Optional[List[str]] = None
        self._parsed_fields: Optional[Dict[str, List[str]]] = None
        self._parsed_appends: Optional[List[str]] = None
    
    @classmethod
    def from_request(cls, request: Request) -> QueryBuilderRequest:
        """Create instance from FastAPI Request"""
        return cls(request)
    
    @classmethod
    def set_array_value_delimiter(cls, delimiter: str) -> None:
        """Set global array value delimiter"""
        cls._array_delimiter = delimiter
    
    @classmethod
    def set_includes_array_value_delimiter(cls, delimiter: str) -> None:
        """Set includes-specific array value delimiter"""
        cls._includes_delimiter = delimiter
    
    @classmethod
    def set_filters_array_value_delimiter(cls, delimiter: str) -> None:
        """Set filters-specific array value delimiter"""
        cls._filters_delimiter = delimiter
    
    @classmethod
    def set_sorts_array_value_delimiter(cls, delimiter: str) -> None:
        """Set sorts-specific array value delimiter"""
        cls._sorts_delimiter = delimiter
    
    @classmethod
    def set_fields_array_value_delimiter(cls, delimiter: str) -> None:
        """Set fields-specific array value delimiter"""
        cls._fields_delimiter = delimiter
    
    @classmethod
    def set_appends_array_value_delimiter(cls, delimiter: str) -> None:
        """Set appends-specific array value delimiter"""
        cls._appends_delimiter = delimiter
    
    def includes(self) -> List[str]:
        """Get parsed includes"""
        if self._parsed_includes is None:
            self._parsed_includes = self._parse_includes()
        return self._parsed_includes
    
    def filters(self) -> Dict[str, Any]:
        """Get parsed filters"""
        if self._parsed_filters is None:
            self._parsed_filters = self._parse_filters()
        return self._parsed_filters
    
    def sorts(self) -> List[str]:
        """Get parsed sorts"""
        if self._parsed_sorts is None:
            self._parsed_sorts = self._parse_sorts()
        return self._parsed_sorts
    
    def fields(self) -> Dict[str, List[str]]:
        """Get parsed fields"""
        if self._parsed_fields is None:
            self._parsed_fields = self._parse_fields()
        return self._parsed_fields
    
    def appends(self) -> List[str]:
        """Get parsed appends"""
        if self._parsed_appends is None:
            self._parsed_appends = self._parse_appends()
        return self._parsed_appends
    
    def has_include(self, include: str) -> bool:
        """Check if specific include is requested"""
        return include in self.includes()
    
    def has_filter(self, filter_name: str) -> bool:
        """Check if specific filter is requested"""
        return filter_name in self.filters()
    
    def has_sort(self, sort: str) -> bool:
        """Check if specific sort is requested"""
        requested_sorts = [s.lstrip('-') for s in self.sorts()]
        return sort in requested_sorts
    
    def has_field(self, table: str, field: str) -> bool:
        """Check if specific field is requested"""
        fields = self.fields()
        return table in fields and field in fields[table]
    
    def _parse_includes(self) -> List[str]:
        """Parse include parameter"""
        include_value = self._query_params.get(self.INCLUDE_PARAMETER)
        if not include_value:
            return []
        
        delimiter = self._includes_delimiter or self._array_delimiter
        return [inc.strip() for inc in include_value.split(delimiter) if inc.strip()]
    
    def _parse_filters(self) -> Dict[str, Any]:
        """Parse filter parameters"""
        filters = {}
        
        for param_name, param_value in self._query_params.items():
            # Handle filter[key] syntax
            filter_match = re.match(rf'{self.FILTER_PARAMETER}\\[(.+?)\\]', param_name)
            if filter_match:
                filter_name = filter_match.group(1)
                filters[filter_name] = self._parse_filter_value(param_value)
            # Handle direct filter parameter (simple filter=value)
            elif param_name == self.FILTER_PARAMETER:
                filters['_simple'] = self._parse_filter_value(param_value)
        
        return filters
    
    def _parse_filter_value(self, value: str) -> Union[str, List[str]]:
        """Parse individual filter value"""
        delimiter = self._filters_delimiter or self._array_delimiter
        
        # Check if value contains the delimiter
        if delimiter in value:
            return [v.strip() for v in value.split(delimiter) if v.strip()]
        
        # Check for dynamic operators (e.g., ">100", "<=50")
        dynamic_operator_match = re.match(r'^([><=!]+)(.+)$', value)
        if dynamic_operator_match:
            operator = dynamic_operator_match.group(1)
            val = dynamic_operator_match.group(2)
            return {'operator': operator, 'value': val}  # type: ignore[return-value]
        
        return value
    
    def _parse_sorts(self) -> List[str]:
        """Parse sort parameter"""
        sort_value = self._query_params.get(self.SORT_PARAMETER)
        if not sort_value:
            return []
        
        delimiter = self._sorts_delimiter or self._array_delimiter
        return [sort.strip() for sort in sort_value.split(delimiter) if sort.strip()]
    
    def _parse_fields(self) -> Dict[str, List[str]]:
        """Parse fields parameters"""
        fields = {}
        
        for param_name, param_value in self._query_params.items():
            # Handle fields[table] syntax
            fields_match = re.match(rf'{self.FIELDS_PARAMETER}\\[(.+?)\\]', param_name)
            if fields_match:
                table_name = fields_match.group(1)
                delimiter = self._fields_delimiter or self._array_delimiter
                field_list = [f.strip() for f in param_value.split(delimiter) if f.strip()]
                fields[table_name] = field_list
        
        return fields
    
    def _parse_appends(self) -> List[str]:
        """Parse append parameter"""
        append_value = self._query_params.get(self.APPEND_PARAMETER)
        if not append_value:
            return []
        
        delimiter = self._appends_delimiter or self._array_delimiter
        return [app.strip() for app in append_value.split(delimiter) if app.strip()]
    
    def get_raw_query_params(self) -> Dict[str, Any]:
        """Get raw query parameters"""
        return self._query_params
    
    def contains(self, parameter_type: str, value: str) -> bool:
        """Check if parameter type contains specific value"""
        if parameter_type == 'includes':
            return value in self.includes()
        elif parameter_type == 'filters':
            return value in self.filters()
        elif parameter_type == 'sorts':
            return value in [s.lstrip('-') for s in self.sorts()]
        elif parameter_type == 'appends':
            return value in self.appends()
        elif parameter_type == 'fields':
            for table_fields in self.fields().values():
                if value in table_fields:
                    return True
            return False
        
        return False