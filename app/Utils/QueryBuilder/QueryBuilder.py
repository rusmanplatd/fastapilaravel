from __future__ import annotations

from typing import List, Optional, Union, Dict, Type, TypeVar, Generic, Callable, Generator, Set, Tuple, Any
from app.Types import JsonObject, JsonValue, FilterCriteria
from sqlalchemy.orm import Query as SQLQuery, Session
from sqlalchemy import func, text, and_, or_
from sqlalchemy.sql import not_
from sqlalchemy.sql import distinct, select, Select
from starlette.requests import Request
from dataclasses import dataclass, field
import json
from datetime import datetime
import logging
from contextlib import contextmanager

from .QueryBuilderRequest import QueryBuilderRequest
from .AllowedFilter import AllowedFilter
from .AllowedSort import AllowedSort, SortDirection
from .AllowedInclude import AllowedInclude
from .AllowedField import AllowedField, FieldSelector
from .FilterOperators import FilterOperator
from .Filters import (
    FilterInterface,
    DateRangeFilter,
    JsonPathFilter,
    FullTextSearchFilter,
    GeographicFilter,
    RelationshipCountFilter,
    TextFilter,
    NumericRangeFilter
)
from .Exceptions import (
    InvalidFilterQueryException,
    InvalidSortQueryException, 
    InvalidIncludeQueryException,
    InvalidFieldQueryException
)

T = TypeVar('T')


@dataclass
class QueryMetrics:
    """Query performance and debugging metrics"""
    execution_time: float = 0.0
    sql_query: Optional[str] = None
    query_plan: Optional[str] = None
    filters_applied: List[str] = field(default_factory=list)
    sorts_applied: List[str] = field(default_factory=list)
    includes_applied: List[str] = field(default_factory=list)
    cache_hit: bool = False
    total_rows_examined: Optional[int] = None
    index_usage: List[str] = field(default_factory=list)


@dataclass
class PaginationResult(Generic[T]):
    """Comprehensive pagination result with enhanced metadata"""
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
    metrics: Optional[QueryMetrics] = None
    facets: Optional[Dict[str, Dict[str, int]]] = None
    aggregations: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
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
        
        if self.metrics:
            result['meta']['metrics'] = {
                'execution_time': self.metrics.execution_time,
                'filters_applied': self.metrics.filters_applied,
                'sorts_applied': self.metrics.sorts_applied,
                'includes_applied': self.metrics.includes_applied,
                'cache_hit': self.metrics.cache_hit
            }
        
        if self.facets:
            result['facets'] = self.facets
            
        if self.aggregations:
            result['aggregations'] = self.aggregations
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class QueryBuilder(Generic[T]):
    """
    FastAPI Query Builder with comprehensive filtering, analytics, and performance optimization
    
    Provides comprehensive filtering, sorting, includes, field selection, faceting,
    aggregation, and performance monitoring capabilities for SQLAlchemy queries.
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
        
        # Custom filtering
        self._custom_filters: Dict[str, FilterInterface] = {}
        self._filter_groups: Dict[str, List[str]] = {}
        self._conditional_filters: List[Callable[[SQLQuery[T]], SQLQuery[T]]] = []
        
        # Analytics and performance
        self._enable_metrics: bool = False
        self._enable_faceting: bool = False
        self._enable_aggregations: bool = False
        self._cache_enabled: bool = False
        self._cache_ttl: int = 300  # 5 minutes
        self._query_timeout: Optional[int] = None
        
        # Faceting configuration
        self._facet_fields: List[str] = []
        self._facet_limit: int = 10
        
        # Aggregation configuration
        self._aggregation_fields: Dict[str, List[str]] = {}
        
        # Performance optimization
        self._optimize_queries: bool = True
        self._auto_index_suggestions: bool = False
        self._explain_queries: bool = False
        
        # Settings
        self._disable_invalid_filter_exception = False
        self._disable_invalid_sort_exception = False
        self._disable_invalid_include_exception = False
        self._disable_invalid_field_exception = False
        
        # Metrics tracking
        self._metrics = QueryMetrics()
        self._logger = logging.getLogger(__name__)
    
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
        """Set allowed filters with support for custom filters"""
        self._allowed_filters = []
        
        for filter_item in filters:
            if isinstance(filter_item, str):
                self._allowed_filters.append(AllowedFilter.partial(filter_item))
            else:
                self._allowed_filters.append(filter_item)
        
        return self
    
    def add_custom_filter(self, name: str, filter_impl: FilterInterface) -> QueryBuilder[T]:
        """Add a custom filter implementation"""
        self._custom_filters[name] = filter_impl
        return self
    
    def add_date_range_filter(self, name: str, **kwargs: Any) -> QueryBuilder[T]:
        """Add a date range filter"""
        self._custom_filters[name] = DateRangeFilter(**kwargs)
        return self
    
    def add_json_path_filter(self, name: str, path_prefix: str = '$') -> QueryBuilder[T]:
        """Add a JSON path filter"""
        self._custom_filters[name] = JsonPathFilter(path_prefix)
        return self
    
    def add_fulltext_filter(self, name: str, search_type: str = 'natural', **kwargs: Any) -> QueryBuilder[T]:
        """Add a full-text search filter"""
        self._custom_filters[name] = FullTextSearchFilter(search_type, **kwargs)
        return self
    
    def add_geographic_filter(self, name: str, srid: int = 4326) -> QueryBuilder[T]:
        """Add a geographic filter"""
        self._custom_filters[name] = GeographicFilter(srid)
        return self
    
    def add_relationship_count_filter(self, name: str, relationship_name: str, operator: str = '>=') -> QueryBuilder[T]:
        """Add a relationship count filter"""
        self._custom_filters[name] = RelationshipCountFilter(relationship_name, operator)
        return self
    
    def add_text_filter(self, name: str, **kwargs: Any) -> QueryBuilder[T]:
        """Add a text filter"""
        self._custom_filters[name] = TextFilter(**kwargs)
        return self
    
    def add_numeric_range_filter(self, name: str, **kwargs: Any) -> QueryBuilder[T]:
        """Add a numeric range filter"""
        self._custom_filters[name] = NumericRangeFilter(**kwargs)
        return self
    
    def filter_group(self, group_name: str, filters: List[str]) -> QueryBuilder[T]:
        """Define a group of filters that work together"""
        self._filter_groups[group_name] = filters
        return self
    
    def conditional_filter(self, condition_func: Callable[[SQLQuery[T]], SQLQuery[T]]) -> QueryBuilder[T]:
        """Add a conditional filter function"""
        self._conditional_filters.append(condition_func)
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
        """Apply filters from request with support for custom filters"""
        if not self.request:
            return self
        
        requested_filters = self.request.filters()
        
        if not requested_filters:
            return self
        
        # Validate requested filters
        allowed_filter_names = [f.name for f in self._allowed_filters]
        custom_filter_names = list(self._custom_filters.keys())
        all_allowed_names = allowed_filter_names + custom_filter_names
        
        unknown_filters = [name for name in requested_filters.keys() if name not in all_allowed_names]
        
        if unknown_filters and not self._disable_invalid_filter_exception:
            raise InvalidFilterQueryException(unknown_filters, all_allowed_names)
        
        # Apply standard filters
        for filter_name, filter_value in requested_filters.items():
            if filter_name in allowed_filter_names and self.model_class is not None:
                allowed_filter = next(f for f in self._allowed_filters if f.name == filter_name)
                self.query = allowed_filter.apply(self.query, filter_value, self.model_class)
                self._metrics.filters_applied.append(f"{filter_name}:{filter_value}")
            
            # Apply custom filters
            elif filter_name in custom_filter_names:
                custom_filter = self._custom_filters[filter_name]
                self.query = custom_filter(self.query, filter_value, filter_name)
                self._metrics.filters_applied.append(f"custom:{filter_name}:{filter_value}")
        
        # Apply conditional filters
        for condition_func in self._conditional_filters:
            self.query = condition_func(self.query)
        
        return self
    
    def apply_filter_groups(self) -> QueryBuilder[T]:
        """Apply filter groups with AND/OR logic"""
        if not self.request:
            return self
        
        group_filters = self.request.filter_groups()
        
        for group_name, group_logic in group_filters.items():
            if group_name in self._filter_groups:
                group_filter_names = self._filter_groups[group_name]
                requested_filters = self.request.filters()
                
                # Collect conditions for this group
                conditions = []
                for filter_name in group_filter_names:
                    if filter_name in requested_filters:
                        filter_value = requested_filters[filter_name]
                        
                        if filter_name in [f.name for f in self._allowed_filters]:
                            allowed_filter = next(f for f in self._allowed_filters if f.name == filter_name)
                            # Create condition without applying to query yet
                            column = self._get_column_for_filter(filter_name)
                            if column is not None:
                                # This is simplified - in practice you'd extract the condition logic
                                conditions.append(column == filter_value)
                
                # Apply group logic (AND/OR)
                if conditions:
                    if group_logic == 'OR':
                        self.query = self.query.filter(or_(*conditions))
                    else:  # Default to AND
                        self.query = self.query.filter(and_(*conditions))
        
        return self
    
    def _get_column_for_filter(self, filter_name: str) -> Optional[Any]:
        """Get column for filter name"""
        if self.model_class and hasattr(self.model_class, filter_name):
            return getattr(self.model_class, filter_name)
        return None
    
    def apply_sorts(self) -> QueryBuilder[T]:
        """Apply sorts from request with metrics tracking"""
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
                self._metrics.sorts_applied.append(sort)
        
        return self
    
    def apply_includes(self) -> QueryBuilder[T]:
        """Apply includes from request with metrics tracking"""
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
                self._metrics.includes_applied.append(include_name)
        
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
    
    def pluck(self, column_name: str) -> List[Union[str, int, float, bool, None]]:
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
    
    def find(self, id_value: Union[str, int]) -> Optional[T]:
        """Find by ID"""
        if not self.model_class:
            return None
            
        # Assume 'id' is the primary key column
        id_column = getattr(self.model_class, 'id', None)
        if id_column is None:
            return None
            
        return self.build().filter(id_column == id_value).first()
    
    def find_or_fail(self, id_value: Union[str, int]) -> T:
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
        error_out: bool = False,
        include_metrics: bool = None,
        include_facets: bool = None,
        include_aggregations: bool = None
    ) -> PaginationResult[T]:
        """Paginate results with comprehensive pagination data and analytics"""
        # Use instance settings if not explicitly provided
        if include_metrics is None:
            include_metrics = self._enable_metrics
        if include_facets is None:
            include_facets = self._enable_faceting
        if include_aggregations is None:
            include_aggregations = self._enable_aggregations
        
        # Validate pagination parameters
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        
        with self.measure_execution_time():
            # Build the query first to apply all filters, sorts, includes
            query = self.build()
            
            # Store SQL for metrics
            if include_metrics:
                self._metrics.sql_query = self.to_sql()
            
            # Get total count before applying pagination
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
        
        # Generate facets if enabled
        facets = None
        if include_facets:
            facets = self.get_facets()
        
        # Generate aggregations if enabled
        aggregations = None
        if include_aggregations:
            aggregations = self.get_aggregations()
        
        # Include metrics if enabled
        metrics = None
        if include_metrics:
            if self._explain_queries:
                try:
                    self._metrics.query_plan = self.explain()
                except Exception:
                    pass
            metrics = self._metrics
        
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
            showing_to=offset + len(items) if items else 0,
            metrics=metrics,
            facets=facets,
            aggregations=aggregations
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
    
    # Analytics and performance methods
    def enable_metrics(self, enabled: bool = True) -> QueryBuilder[T]:
        """Enable query performance metrics"""
        self._enable_metrics = enabled
        return self
    
    def enable_faceting(self, fields: List[str], limit: int = 10) -> QueryBuilder[T]:
        """Enable faceting for specified fields"""
        self._enable_faceting = True
        self._facet_fields = fields
        self._facet_limit = limit
        return self
    
    def enable_aggregations(self, field_aggregations: Dict[str, List[str]]) -> QueryBuilder[T]:
        """Enable aggregations (count, sum, avg, min, max) for specified fields"""
        self._enable_aggregations = True
        self._aggregation_fields = field_aggregations
        return self
    
    def enable_caching(self, ttl: int = 300) -> QueryBuilder[T]:
        """Enable query result caching"""
        self._cache_enabled = True
        self._cache_ttl = ttl
        return self
    
    def set_query_timeout(self, timeout_seconds: int) -> QueryBuilder[T]:
        """Set query execution timeout"""
        self._query_timeout = timeout_seconds
        return self
    
    def enable_query_optimization(self, enabled: bool = True) -> QueryBuilder[T]:
        """Enable automatic query optimization"""
        self._optimize_queries = enabled
        return self
    
    def enable_index_suggestions(self, enabled: bool = True) -> QueryBuilder[T]:
        """Enable automatic index suggestions"""
        self._auto_index_suggestions = enabled
        return self
    
    def enable_query_explanation(self, enabled: bool = True) -> QueryBuilder[T]:
        """Enable query plan explanation"""
        self._explain_queries = enabled
        return self
    
    @contextmanager
    def measure_execution_time(self) -> Generator[None, None, None]:
        """Context manager to measure query execution time"""
        start_time = datetime.now()
        try:
            yield
        finally:
            end_time = datetime.now()
            self._metrics.execution_time = (end_time - start_time).total_seconds()
    
    def get_facets(self) -> Dict[str, Dict[str, int]]:
        """Generate facets for configured fields"""
        if not self._enable_faceting or not self._facet_fields:
            return {}
        
        facets = {}
        
        for field_name in self._facet_fields:
            if self.model_class and hasattr(self.model_class, field_name):
                column = getattr(self.model_class, field_name)
                
                # Create facet query
                facet_query = self.base_query.with_entities(
                    column,
                    func.count().label('count')
                ).group_by(column).order_by(func.count().desc()).limit(self._facet_limit)
                
                try:
                    results = facet_query.all()
                    facets[field_name] = {str(value): count for value, count in results if value is not None}
                except Exception as e:
                    self._logger.warning(f"Failed to generate facets for {field_name}: {e}")
                    facets[field_name] = {}
        
        return facets
    
    def get_aggregations(self) -> Dict[str, Any]:
        """Generate aggregations for configured fields"""
        if not self._enable_aggregations or not self._aggregation_fields:
            return {}
        
        aggregations = {}
        
        for field_name, agg_functions in self._aggregation_fields.items():
            if self.model_class and hasattr(self.model_class, field_name):
                column = getattr(self.model_class, field_name)
                field_aggs = {}
                
                try:
                    for agg_func in agg_functions:
                        if agg_func == 'count':
                            field_aggs['count'] = self.base_query.with_entities(func.count(column)).scalar()
                        elif agg_func == 'sum':
                            field_aggs['sum'] = self.base_query.with_entities(func.sum(column)).scalar()
                        elif agg_func == 'avg':
                            field_aggs['avg'] = self.base_query.with_entities(func.avg(column)).scalar()
                        elif agg_func == 'min':
                            field_aggs['min'] = self.base_query.with_entities(func.min(column)).scalar()
                        elif agg_func == 'max':
                            field_aggs['max'] = self.base_query.with_entities(func.max(column)).scalar()
                        elif agg_func == 'stddev':
                            field_aggs['stddev'] = self.base_query.with_entities(func.stddev(column)).scalar()
                        elif agg_func == 'variance':
                            field_aggs['variance'] = self.base_query.with_entities(func.variance(column)).scalar()
                    
                    aggregations[field_name] = field_aggs
                    
                except Exception as e:
                    self._logger.warning(f"Failed to generate aggregations for {field_name}: {e}")
                    aggregations[field_name] = {}
        
        return aggregations
    
    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze query performance and suggest optimizations"""
        analysis: Dict[str, Any] = {
            'sql_query': self.to_sql(),
            'estimated_cost': None,
            'index_suggestions': [],
            'optimization_hints': []
        }
        
        if self._explain_queries:
            try:
                query_plan = self.explain()
                analysis['query_plan'] = query_plan
                self._metrics.query_plan = query_plan
            except Exception as e:
                self._logger.warning(f"Failed to get query plan: {e}")
        
        if self._auto_index_suggestions:
            # Analyze filters and sorts for index suggestions
            suggested_indexes = self._suggest_indexes()
            analysis['index_suggestions'] = suggested_indexes
            self._metrics.index_usage = suggested_indexes
        
        return analysis
    
    def _suggest_indexes(self) -> List[str]:
        """Suggest database indexes based on applied filters and sorts"""
        suggestions = []
        
        # Suggest indexes for filtered columns
        if self._metrics.filters_applied:
            for filter_applied in self._metrics.filters_applied:
                if ':' in filter_applied:
                    field_name = filter_applied.split(':', 1)[0]
                    if field_name not in ['custom']:  # Skip custom filters
                        suggestions.append(f"CREATE INDEX idx_{self.model_class.__tablename__ if self.model_class else 'table'}_{field_name} ON {self.model_class.__tablename__ if self.model_class else 'table'} ({field_name});")
        
        # Suggest indexes for sorted columns
        if self._metrics.sorts_applied:
            for sort_applied in self._metrics.sorts_applied:
                field_name = sort_applied.lstrip('-')
                suggestions.append(f"CREATE INDEX idx_{self.model_class.__tablename__ if self.model_class else 'table'}_{field_name}_sort ON {self.model_class.__tablename__ if self.model_class else 'table'} ({field_name});")
        
        # Suggest composite indexes for multiple filters
        if len(self._metrics.filters_applied) > 1:
            filter_fields = []
            for filter_applied in self._metrics.filters_applied:
                if ':' in filter_applied:
                    field_name = filter_applied.split(':', 1)[0]
                    if field_name not in ['custom']:
                        filter_fields.append(field_name)
            
            if len(filter_fields) > 1:
                composite_index = f"CREATE INDEX idx_{self.model_class.__tablename__ if self.model_class else 'table'}_composite ON {self.model_class.__tablename__ if self.model_class else 'table'} ({', '.join(filter_fields)});"
                suggestions.append(composite_index)
        
        return list(set(suggestions))  # Remove duplicates
    
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
    def filter(self, *args: Union[str, int, bool, None], **kwargs: Union[str, int, bool, None]) -> QueryBuilder[T]:
        """Chain SQLAlchemy filter"""
        self.query = self.query.filter(*args, **kwargs)
        return self
    
    def join(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy join"""
        self.query = self.query.join(*args, **kwargs)
        return self
    
    def where(self, *args: Union[str, int, bool, None], **kwargs: Union[str, int, bool, None]) -> QueryBuilder[T]:
        """Alias for filter"""
        return self.filter(*args, **kwargs)
    
    def order_by(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy order_by"""
        self.query = self.query.order_by(*args, **kwargs)
        return self
    
    def group_by(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy group_by"""
        self.query = self.query.group_by(*args, **kwargs)
        return self
    
    def having(self, *args: Union[str, int, bool, None], **kwargs: Union[str, int, bool, None]) -> QueryBuilder[T]:
        """Chain SQLAlchemy having"""
        self.query = self.query.having(*args, **kwargs)
        return self
    
    def limit(self, *args: Union[int, None], **kwargs: Union[int, None]) -> QueryBuilder[T]:
        """Chain SQLAlchemy limit"""
        self.query = self.query.limit(*args, **kwargs)
        return self
    
    def offset(self, *args: Union[int, None], **kwargs: Union[int, None]) -> QueryBuilder[T]:
        """Chain SQLAlchemy offset"""
        self.query = self.query.offset(*args, **kwargs)
        return self
    
    def distinct(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy distinct"""
        self.query = self.query.distinct(*args, **kwargs)
        return self
    
    def union(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy union"""
        self.query = self.query.union(*args, **kwargs)
        return self
    
    def union_all(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy union_all"""
        self.query = self.query.union_all(*args, **kwargs)
        return self
    
    def with_entities(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy with_entities"""
        self.query = self.query.with_entities(*args, **kwargs)
        return self
    
    def options(self, *args: Union[str, object], **kwargs: Union[str, object]) -> QueryBuilder[T]:
        """Chain SQLAlchemy options"""
        self.query = self.query.options(*args, **kwargs)
        return self