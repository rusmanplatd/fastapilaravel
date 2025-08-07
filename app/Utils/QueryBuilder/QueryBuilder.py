from __future__ import annotations

from typing import List, Optional, Union, Dict, Any, Type, TypeVar, Generic
from sqlalchemy.orm import Query as SQLQuery, Session
# from sqlalchemy import inspect as sqlalchemy_inspect  # type: ignore[attr-defined]
from starlette.requests import Request

from .QueryBuilderRequest import QueryBuilderRequest
from .AllowedFilter import AllowedFilter
from .AllowedSort import AllowedSort, SortDirection
from .AllowedInclude import AllowedInclude
from .AllowedField import AllowedField, FieldSelector
from .Exceptions import (
    InvalidFilterQueryException,
    InvalidSortQueryException, 
    InvalidIncludeQueryException,
    InvalidFieldQueryException
)

T = TypeVar('T')


class QueryBuilder(Generic[T]):
    """
    FastAPI Query Builder inspired by Spatie Laravel Query Builder
    
    Provides filtering, sorting, includes, and field selection capabilities
    for SQLAlchemy queries through URL parameters.
    """
    
    def __init__(
        self, 
        query: SQLQuery[T],
        request: Optional[QueryBuilderRequest] = None,
        model_class: Optional[Type[T]] = None
    ) -> None:
        self.base_query = query
        self.query = query
        self.request = request
        self.model_class = model_class
        
        # Configuration
        self._allowed_filters: List[AllowedFilter] = []
        self._allowed_sorts: List[AllowedSort] = []
        self._allowed_includes: List[AllowedInclude] = []
        self._allowed_fields: List[AllowedField] = []
        self._default_sorts: List[str] = []
        
        # Settings
        self._disable_invalid_filter_exception = False
        self._disable_invalid_sort_exception = False
        self._disable_invalid_include_exception = False
        self._disable_invalid_field_exception = False
    
    @classmethod
    def for_model(
        cls, 
        model_class: Type[T], 
        session: Session,
        request: Optional[QueryBuilderRequest] = None
    ) -> QueryBuilder[T]:
        """Create QueryBuilder for a model class"""
        query = session.query(model_class)
        return cls(query, request, model_class)
    
    @classmethod
    def for_query(
        cls, 
        query: SQLQuery[T],
        request: Optional[QueryBuilderRequest] = None,
        model_class: Optional[Type[T]] = None
    ) -> QueryBuilder[T]:
        """Create QueryBuilder from existing query"""
        return cls(query, request, model_class)
    
    def set_request(self, request: QueryBuilderRequest) -> QueryBuilder[T]:
        """Set the request object"""
        self.request = request
        return self
    
    def allowed_filters(self, filters: List[Union[str, AllowedFilter]]) -> QueryBuilder[T]:
        """Set allowed filters"""
        self._allowed_filters = []
        
        for filter_item in filters:
            if isinstance(filter_item, str):
                self._allowed_filters.append(AllowedFilter.partial(filter_item))
            else:
                self._allowed_filters.append(filter_item)
        
        return self
    
    def allowed_sorts(self, sorts: List[Union[str, AllowedSort]]) -> QueryBuilder[T]:
        """Set allowed sorts"""
        self._allowed_sorts = []
        
        for sort_item in sorts:
            if isinstance(sort_item, str):
                self._allowed_sorts.append(AllowedSort.field(sort_item))
            else:
                self._allowed_sorts.append(sort_item)
        
        return self
    
    def allowed_includes(self, includes: List[Union[str, AllowedInclude]]) -> QueryBuilder[T]:
        """Set allowed includes"""
        self._allowed_includes = []
        
        for include_item in includes:
            if isinstance(include_item, str):
                # Check if it's a count or exists include
                if include_item.endswith('Count'):
                    self._allowed_includes.append(AllowedInclude.count(include_item))
                elif include_item.endswith('Exists'):
                    self._allowed_includes.append(AllowedInclude.exists(include_item))
                else:
                    self._allowed_includes.append(AllowedInclude.relationship(include_item))
            else:
                self._allowed_includes.append(include_item)
        
        return self
    
    def allowed_fields(self, fields: List[Union[str, AllowedField]]) -> QueryBuilder[T]:
        """Set allowed fields"""
        self._allowed_fields = []
        
        for field_item in fields:
            if isinstance(field_item, str):
                self._allowed_fields.append(AllowedField.field(field_item))
            else:
                self._allowed_fields.append(field_item)
        
        return self
    
    def default_sort(self, *sorts: Union[str, AllowedSort]) -> QueryBuilder[T]:
        """Set default sorts"""
        self._default_sorts = []
        
        for sort_item in sorts:
            if isinstance(sort_item, str):
                self._default_sorts.append(sort_item)
            else:
                self._default_sorts.append(sort_item.name)
        
        return self
    
    def apply_filters(self) -> QueryBuilder[T]:
        """Apply filters from request"""
        if not self.request:
            return self
        
        requested_filters = self.request.filters()
        
        if not requested_filters:
            return self
        
        # Validate requested filters
        allowed_filter_names = [f.name for f in self._allowed_filters]
        unknown_filters = [name for name in requested_filters.keys() if name not in allowed_filter_names]
        
        if unknown_filters and not self._disable_invalid_filter_exception:
            raise InvalidFilterQueryException(unknown_filters, allowed_filter_names)
        
        # Apply each filter
        for filter_name, filter_value in requested_filters.items():
            if filter_name in allowed_filter_names and self.model_class is not None:
                allowed_filter = next(f for f in self._allowed_filters if f.name == filter_name)
                self.query = allowed_filter.apply(self.query, filter_value, self.model_class)
        
        return self
    
    def apply_sorts(self) -> QueryBuilder[T]:
        """Apply sorts from request"""
        if not self.request:
            # Apply default sorts if no request
            return self._apply_default_sorts()
        
        requested_sorts = self.request.sorts()
        
        if not requested_sorts:
            return self._apply_default_sorts()
        
        # Validate requested sorts
        allowed_sort_names = [s.name for s in self._allowed_sorts]
        unknown_sorts = []
        
        for sort in requested_sorts:
            sort_name = sort.lstrip('-')  # Remove descending prefix
            if sort_name not in allowed_sort_names:
                unknown_sorts.append(sort_name)
        
        if unknown_sorts and not self._disable_invalid_sort_exception:
            raise InvalidSortQueryException(unknown_sorts, allowed_sort_names)
        
        # Apply each sort
        for sort in requested_sorts:
            descending = sort.startswith('-')
            sort_name = sort.lstrip('-')
            
            if sort_name in allowed_sort_names and self.model_class is not None:
                allowed_sort = next(s for s in self._allowed_sorts if s.name == sort_name)
                self.query = allowed_sort.apply(self.query, descending, self.model_class)
        
        return self
    
    def apply_includes(self) -> QueryBuilder[T]:
        """Apply includes from request"""
        if not self.request:
            return self
        
        requested_includes = self.request.includes()
        
        if not requested_includes:
            return self
        
        # Validate requested includes
        allowed_include_names = [i.name for i in self._allowed_includes]
        unknown_includes = [name for name in requested_includes if name not in allowed_include_names]
        
        if unknown_includes and not self._disable_invalid_include_exception:
            raise InvalidIncludeQueryException(unknown_includes, allowed_include_names)
        
        # Apply each include
        for include_name in requested_includes:
            if include_name in allowed_include_names and self.model_class is not None:
                allowed_include = next(i for i in self._allowed_includes if i.name == include_name)
                self.query = allowed_include.apply(self.query, self.model_class)
        
        return self
    
    def apply_fields(self) -> QueryBuilder[T]:
        """Apply field selection from request"""
        if not self.request or not self.model_class:
            return self
        
        requested_fields = self.request.fields()
        
        if not requested_fields:
            return self
        
        # Get table name for the model
        table_name = getattr(self.model_class, '__tablename__', None)
        if not table_name:
            return self
        
        # Validate requested fields
        allowed_field_names = [f.name for f in self._allowed_fields]
        all_requested_fields = []
        
        for table, fields in requested_fields.items():
            all_requested_fields.extend(fields)
        
        unknown_fields = [name for name in all_requested_fields if name not in allowed_field_names]
        
        if unknown_fields and not self._disable_invalid_field_exception:
            raise InvalidFieldQueryException(unknown_fields, allowed_field_names)
        
        # Apply field selection
        field_selector = FieldSelector(self.model_class, table_name)
        self.query = field_selector.select_fields(self.query, self._allowed_fields, requested_fields)
        
        return self
    
    def _apply_default_sorts(self) -> QueryBuilder[T]:
        """Apply default sorts"""
        for sort in self._default_sorts:
            descending = sort.startswith('-')
            sort_name = sort.lstrip('-')
            
            # Find the allowed sort
            allowed_sort = next((s for s in self._allowed_sorts if s.name == sort_name), None)
            
            if allowed_sort:
                # Check if sort has a default direction
                if allowed_sort.is_descending_by_default():
                    descending = not descending  # Flip if default is descending
                
                if self.model_class is not None:
                    self.query = allowed_sort.apply(self.query, descending, self.model_class)
        
        return self
    
    def build(self) -> SQLQuery[T]:
        """Build and return the final query"""
        if self.request:
            self.apply_filters()
            self.apply_sorts()
            self.apply_includes()
            self.apply_fields()
        else:
            self._apply_default_sorts()
        
        return self.query
    
    def get(self) -> List[T]:
        """Execute query and return results"""
        return self.build().all()
    
    def first(self) -> Optional[T]:
        """Get first result"""
        return self.build().first()
    
    def count(self) -> int:
        """Get count of results"""
        return self.build().count()
    
    def paginate(
        self, 
        page: int = 1, 
        per_page: int = 15,
        error_out: bool = False
    ) -> Any:
        """Paginate results"""
        # This would need to be implemented with your preferred pagination library
        # For now, return a simple offset/limit implementation
        offset = (page - 1) * per_page
        results = self.build().offset(offset).limit(per_page).all()
        total = self.count()
        
        return {
            'items': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total
        }
    
    def to_sql(self) -> str:
        """Get SQL string representation"""
        return str(self.build().statement.compile(compile_kwargs={"literal_binds": True}))
    
    # Configuration methods
    def disable_invalid_filter_exception(self, disable: bool = True) -> QueryBuilder[T]:
        """Disable invalid filter exceptions"""
        self._disable_invalid_filter_exception = disable
        return self
    
    def disable_invalid_sort_exception(self, disable: bool = True) -> QueryBuilder[T]:
        """Disable invalid sort exceptions"""
        self._disable_invalid_sort_exception = disable
        return self
    
    def disable_invalid_include_exception(self, disable: bool = True) -> QueryBuilder[T]:
        """Disable invalid include exceptions"""
        self._disable_invalid_include_exception = disable
        return self
    
    def disable_invalid_field_exception(self, disable: bool = True) -> QueryBuilder[T]:
        """Disable invalid field exceptions"""
        self._disable_invalid_field_exception = disable
        return self
    
    # Chaining methods for SQLAlchemy compatibility
    def filter(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy filter"""
        self.query = self.query.filter(*args, **kwargs)
        return self
    
    def join(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy join"""
        self.query = self.query.join(*args, **kwargs)
        return self
    
    def where(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Alias for filter"""
        return self.filter(*args, **kwargs)
    
    def order_by(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy order_by"""
        self.query = self.query.order_by(*args, **kwargs)
        return self
    
    def group_by(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy group_by"""
        self.query = self.query.group_by(*args, **kwargs)
        return self
    
    def having(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy having"""
        self.query = self.query.having(*args, **kwargs)
        return self
    
    def limit(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy limit"""
        self.query = self.query.limit(*args, **kwargs)
        return self
    
    def offset(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy offset"""
        self.query = self.query.offset(*args, **kwargs)
        return self