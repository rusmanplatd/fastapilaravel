from __future__ import annotations

from typing import List, Optional, Union, Dict, Any, Type, TypeVar, Generic, Callable, Generator
from sqlalchemy.orm import Query as SQLQuery, Session
from sqlalchemy import func, text
from sqlalchemy.sql import distinct, select, Select
from starlette.requests import Request
from dataclasses import dataclass

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


@dataclass
class PaginationResult(Generic[T]):
    """Comprehensive pagination result"""
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_prev: bool
    has_next: bool
    prev_page: Optional[int]
    next_page: Optional[int]
    showing_from: int
    showing_to: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'data': self.items,
            'meta': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages,
                'has_prev': self.has_prev,
                'has_next': self.has_next,
                'prev_page': self.prev_page,
                'next_page': self.next_page,
                'showing_from': self.showing_from,
                'showing_to': self.showing_to
            }
        }


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
    
    def chunk(self, size: int = 100) -> Generator[List[T], None, None]:
        """Chunk results for memory-efficient processing"""
        query = self.build()
        offset = 0
        
        while True:
            chunk_query = query.offset(offset).limit(size)
            chunk = chunk_query.all()
            
            if not chunk:
                break
                
            yield chunk
            
            if len(chunk) < size:
                break
                
            offset += size
    
    def each(self, callback: Callable[[T], None], chunk_size: int = 100) -> None:
        """Process each result with a callback function"""
        for chunk in self.chunk(chunk_size):
            for item in chunk:
                callback(item)
    
    def pluck(self, column_name: str) -> List[Any]:
        """Get a list of values from a specific column"""
        if not self.model_class:
            return []
            
        column = getattr(self.model_class, column_name, None)
        if column is None:
            return []
        
        query = self.build().with_entities(column)
        return [row[0] for row in query.all()]
    
    def first(self) -> Optional[T]:
        """Get first result"""
        return self.build().first()
    
    def first_or_fail(self) -> T:
        """Get first result or raise exception"""
        result = self.first()
        if result is None:
            raise ValueError("No results found")
        return result
    
    def find(self, id_value: Any) -> Optional[T]:
        """Find by ID"""
        if not self.model_class:
            return None
            
        # Assume 'id' is the primary key column
        id_column = getattr(self.model_class, 'id', None)
        if id_column is None:
            return None
            
        return self.build().filter(id_column == id_value).first()
    
    def find_or_fail(self, id_value: Any) -> T:
        """Find by ID or raise exception"""
        result = self.find(id_value)
        if result is None:
            raise ValueError(f"No result found for ID: {id_value}")
        return result
    
    def count(self) -> int:
        """Get count of results"""
        # Build query and get count more efficiently
        query = self.build()
        
        # Use a more efficient count query that doesn't load all data
        try:
            # For SQLAlchemy 2.0, use different approach
            
            # Check if statement has alias method
            if hasattr(query.statement, 'alias'):
                count_query = select(func.count()).select_from(query.statement.alias())
                return query.session.execute(count_query).scalar() or 0
            else:
                return query.count()
        except Exception:
            # Fallback to standard count if the above fails
            return query.count()
    
    def distinct_count(self, column_name: Optional[str] = None) -> int:
        """Get distinct count of results"""
        query = self.build()
        
        if column_name and self.model_class:
            column = getattr(self.model_class, column_name, None)
            if column is not None:
                count_query = query.session.query(func.count(distinct(column)))
                return count_query.scalar() or 0
        
        # Fallback to regular count
        return self.count()
    
    def exists(self) -> bool:
        """Check if any results exist"""
        query = self.build()
        return query.session.query(query.exists()).scalar() or False
    
    def paginate(
        self, 
        page: int = 1, 
        per_page: int = 15,
        max_per_page: int = 100,
        error_out: bool = False
    ) -> PaginationResult[T]:
        """Paginate results with comprehensive pagination data"""
        # Validate pagination parameters
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        
        # Build the query first to apply all filters, sorts, includes
        query = self.build()
        
        # Get total count before applying pagination
        # For SQLAlchemy 2.0 compatibility
        
        # Check if statement has alias method
        if hasattr(query.statement, 'alias'):
            count_query = select(func.count()).select_from(query.statement.alias())
            total = query.session.execute(count_query).scalar() or 0
        else:
            total = query.count()
        
        # Calculate pagination values
        total_pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Apply pagination to query
        paginated_query = query.offset(offset).limit(per_page)
        items = paginated_query.all()
        
        # Calculate additional pagination metadata
        has_prev = page > 1
        has_next = page < total_pages
        prev_page = page - 1 if has_prev else None
        next_page = page + 1 if has_next else None
        
        return PaginationResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_prev=has_prev,
            has_next=has_next,
            prev_page=prev_page,
            next_page=next_page,
            showing_from=offset + 1 if items else 0,
            showing_to=offset + len(items) if items else 0
        )
    
    def to_sql(self) -> str:
        """Get SQL string representation"""
        try:
            query = self.build()
            bind = query.session.bind
            if bind is not None:
                compiled = query.statement.compile(
                    dialect=bind.dialect,
                    compile_kwargs={"literal_binds": True}
                )
                return str(compiled)
            else:
                return str(query.statement)
        except Exception:
            # Fallback for cases where literal_binds fails
            return str(self.build().statement)
    
    def explain(self) -> str:
        """Get query execution plan"""
        query = self.build()
        try:
            # For PostgreSQL
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {self.to_sql()}"
            result = query.session.execute(text(explain_query))
            return '\n'.join([row[0] for row in result])
        except Exception:
            try:
                # Fallback for other databases
                explain_query = f"EXPLAIN {self.to_sql()}"
                result = query.session.execute(text(explain_query))
                return '\n'.join([str(row[0]) for row in result])
            except Exception:
                return "Query execution plan not available"
    
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
    
    def disable_all_exceptions(self, disable: bool = True) -> QueryBuilder[T]:
        """Disable all invalid query exceptions"""
        self._disable_invalid_filter_exception = disable
        self._disable_invalid_sort_exception = disable
        self._disable_invalid_include_exception = disable
        self._disable_invalid_field_exception = disable
        return self
    
    def clone(self) -> QueryBuilder[T]:
        """Create a copy of the QueryBuilder"""
        cloned = QueryBuilder(
            self.base_query,
            self.request,
            self.model_class
        )
        
        # Copy configuration
        cloned._allowed_filters = self._allowed_filters.copy()
        cloned._allowed_sorts = self._allowed_sorts.copy()
        cloned._allowed_includes = self._allowed_includes.copy()
        cloned._allowed_fields = self._allowed_fields.copy()
        cloned._default_sorts = self._default_sorts.copy()
        
        # Copy settings
        cloned._disable_invalid_filter_exception = self._disable_invalid_filter_exception
        cloned._disable_invalid_sort_exception = self._disable_invalid_sort_exception
        cloned._disable_invalid_include_exception = self._disable_invalid_include_exception
        cloned._disable_invalid_field_exception = self._disable_invalid_field_exception
        
        return cloned
    
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
    
    def distinct(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy distinct"""
        self.query = self.query.distinct(*args, **kwargs)
        return self
    
    def union(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy union"""
        self.query = self.query.union(*args, **kwargs)
        return self
    
    def union_all(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy union_all"""
        self.query = self.query.union_all(*args, **kwargs)
        return self
    
    def with_entities(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy with_entities"""
        self.query = self.query.with_entities(*args, **kwargs)
        return self
    
    def options(self, *args: Any, **kwargs: Any) -> QueryBuilder[T]:
        """Chain SQLAlchemy options"""
        self.query = self.query.options(*args, **kwargs)
        return self