from __future__ import annotations

from typing import (
    Any, Dict, List, Optional, Union, Type, Generic, TypeVar, Callable, 
    Iterator, Tuple, Protocol, runtime_checkable, overload, Self, final,
    TYPE_CHECKING, Literal, Awaitable
)
from datetime import datetime, date, time, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    select, Select, insert, Insert, update, Update, delete, Delete,
    func, desc, asc, and_, or_, not_, exists, text, literal_column,
    case, cast, extract, between, nullsfirst, nullslast
)
from sqlalchemy.orm import (
    Session, Query, selectinload, joinedload, contains_eager, 
    load_only, defer, undefer, raiseload, subqueryload
)
from sqlalchemy.sql import Select as SQLSelect, operators
from sqlalchemy.sql.elements import BinaryExpression
from contextlib import contextmanager
import json
import re
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel
    from app.Support.Collection import Collection
    from app.Pagination import LengthAwarePaginator, CursorPaginator

T = TypeVar('T', bound='BaseModel')


# Laravel 12 Query Builder Contracts
@runtime_checkable
class QueryBuilderContract(Protocol[T]):
    """Contract for Laravel 12 query builders with strict typing."""
    
    def where(self, column: str, operator: str = '=', value: Any = None) -> Self:
        """Add a basic where clause."""
        ...
    
    def get(self) -> List[T]:
        """Execute the query and get all results."""
        ...
    
    def first(self) -> Optional[T]:
        """Execute the query and get the first result."""
        ...
    
    def find(self, id_value: Any) -> Optional[T]:
        """Find a record by its primary key."""
        ...


@runtime_checkable
class RelationshipQueryBuilder(Protocol[T]):
    """Contract for relationship query building (Laravel 12)."""
    
    def with_relations(self, *relations: str) -> Self:
        """Eager load relationships."""
        ...
    
    def without_relations(self, *relations: str) -> Self:
        """Remove eager loaded relationships."""
        ...
    
    def with_count(self, *relations: str) -> Self:
        """Include relationship counts."""
        ...


class QueryBuilderException(Exception):
    """Base exception for query builder errors."""
    pass


class InvalidOperatorException(QueryBuilderException):
    """Exception for invalid SQL operators."""
    pass


class RelationshipNotFoundException(QueryBuilderException):
    """Exception for missing relationships."""
    pass


# Laravel 12 Enhanced Query Builder
@final
class EnhancedQueryBuilder(Generic[T]):
    """Laravel 12 enhanced query builder with strict typing and advanced features."""
    
    # Supported operators
    OPERATORS = {
        '=', '!=', '<>', '<', '>', '<=', '>=',
        'like', 'ilike', 'not like', 'not ilike',
        'in', 'not in', 'between', 'not between',
        'is', 'is not', 'regexp', 'not regexp',
        'rlike', 'not rlike', 'sounds like'
    }
    
    # Aggregate functions
    AGGREGATES = {'count', 'max', 'min', 'avg', 'sum'}
    
    def __init__(self, model: Type[T], session: Session) -> None:
        """Initialize the query builder."""
        self.model = model
        self.session = session
        self._query: Select[Tuple[T]] = select(model)
        self._relationships: Dict[str, Any] = {}
        self._relationship_counts: List[str] = []
        self._scopes: List[Callable[[Select[Tuple[T]]], Select[Tuple[T]]]] = []
        self._global_scopes_applied = False
        self._without_global_scopes: List[str] = []
        self._orders: List[Any] = []
        self._limit_value: Optional[int] = None
        self._offset_value: Optional[int] = None
        self._distinct_value: bool = False
        self._group_by_columns: List[Any] = []
        self._having_conditions: List[Any] = []
        self._unions: List[Select[Tuple[T]]] = []
        self._lock_mode: Optional[str] = None
        self._from_raw: Optional[str] = None
        
    def __repr__(self) -> str:
        """String representation of the query builder."""
        return f"<EnhancedQueryBuilder({self.model.__name__})>"
    
    def __str__(self) -> str:
        """String representation of the SQL query."""
        return str(self._query.compile(compile_kwargs={"literal_binds": True}))
    
    # Laravel 12 Core Query Methods
    def where(self, column: Union[str, Callable], operator: str = '=', value: Any = None) -> Self:
        """Add a basic where clause with Laravel 12 enhancements."""
        if callable(column):
            # Closure-based where
            nested_query = EnhancedQueryBuilder(self.model, self.session)
            column(nested_query)
            conditions = nested_query._extract_where_conditions()
            if conditions:
                self._query = self._query.where(and_(*conditions))
            return self
        
        # Validate operator
        if operator.lower() not in self.OPERATORS:
            raise InvalidOperatorException(f"Invalid operator: {operator}")
        
        # Handle different operators
        column_attr = self._get_column_attribute(column)
        condition = self._build_condition(column_attr, operator, value)
        self._query = self._query.where(condition)
        
        return self
    
    def or_where(self, column: Union[str, Callable], operator: str = '=', value: Any = None) -> Self:
        """Add an or where clause (Laravel 12)."""
        if callable(column):
            nested_query = EnhancedQueryBuilder(self.model, self.session)
            column(nested_query)
            conditions = nested_query._extract_where_conditions()
            if conditions:
                self._query = self._query.where(or_(*conditions))
            return self
        
        column_attr = self._get_column_attribute(column)
        condition = self._build_condition(column_attr, operator, value)
        
        # Extract existing where clause and combine with OR
        existing_where = self._query.whereclause
        if existing_where is not None:
            self._query = self._query.where(or_(existing_where, condition))
        else:
            self._query = self._query.where(condition)
        
        return self
    
    def where_in(self, column: str, values: List[Any]) -> Self:
        """Add a where in clause (Laravel 12)."""
        if not values:
            # Empty values should match nothing
            self._query = self._query.where(literal_column('1=0'))
            return self
        
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.in_(values))
        return self
    
    def where_not_in(self, column: str, values: List[Any]) -> Self:
        """Add a where not in clause (Laravel 12)."""
        if not values:
            return self  # No restriction if empty
        
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(~column_attr.in_(values))
        return self
    
    def where_null(self, column: str) -> Self:
        """Add a where null clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.is_(None))
        return self
    
    def where_not_null(self, column: str) -> Self:
        """Add a where not null clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.is_not(None))
        return self
    
    def where_between(self, column: str, start: Any, end: Any) -> Self:
        """Add a where between clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.between(start, end))
        return self
    
    def where_not_between(self, column: str, start: Any, end: Any) -> Self:
        """Add a where not between clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(~column_attr.between(start, end))
        return self
    
    def where_like(self, column: str, pattern: str) -> Self:
        """Add a where like clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.like(pattern))
        return self
    
    def where_ilike(self, column: str, pattern: str) -> Self:
        """Add a case-insensitive where like clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.ilike(pattern))
        return self
    
    def where_regexp(self, column: str, pattern: str) -> Self:
        """Add a where regexp clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(column_attr.op('REGEXP')(pattern))
        return self
    
    # Laravel 12 Date Query Methods
    def where_date(self, column: str, operator: str, value: Union[str, date]) -> Self:
        """Add a where date clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        date_part = func.date(column_attr)
        
        if isinstance(value, str):
            value = datetime.fromisoformat(value).date()
        
        condition = self._build_condition(date_part, operator, value)
        self._query = self._query.where(condition)
        return self
    
    def where_time(self, column: str, operator: str, value: Union[str, time]) -> Self:
        """Add a where time clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        time_part = func.time(column_attr)
        
        if isinstance(value, str):
            value = datetime.fromisoformat(f"2000-01-01T{value}").time()
        
        condition = self._build_condition(time_part, operator, value)
        self._query = self._query.where(condition)
        return self
    
    def where_year(self, column: str, value: int) -> Self:
        """Add a where year clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(extract('year', column_attr) == value)
        return self
    
    def where_month(self, column: str, value: int) -> Self:
        """Add a where month clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(extract('month', column_attr) == value)
        return self
    
    def where_day(self, column: str, value: int) -> Self:
        """Add a where day clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        self._query = self._query.where(extract('day', column_attr) == value)
        return self
    
    # Laravel 12 JSON Query Methods
    def where_json(self, column: str, path: str, operator: str = '=', value: Any = None) -> Self:
        """Add a where JSON clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        json_extract = column_attr[path].as_string()
        condition = self._build_condition(json_extract, operator, str(value))
        self._query = self._query.where(condition)
        return self
    
    def where_json_contains(self, column: str, value: Any) -> Self:
        """Add a where JSON contains clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        json_value = json.dumps(value) if not isinstance(value, str) else value
        self._query = self._query.where(column_attr.contains(json_value))
        return self
    
    def where_json_length(self, column: str, operator: str, length: int, path: Optional[str] = None) -> Self:
        """Add a where JSON length clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        
        if path:
            json_path = column_attr[path]
            length_expr = func.json_array_length(json_path)
        else:
            length_expr = func.json_array_length(column_attr)
        
        condition = self._build_condition(length_expr, operator, length)
        self._query = self._query.where(condition)
        return self
    
    # Laravel 12 Ordering Methods
    def order_by(self, column: str, direction: str = 'asc') -> Self:
        """Add an order by clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        
        if direction.lower() == 'desc':
            order_expr = desc(column_attr)
        else:
            order_expr = asc(column_attr)
        
        self._orders.append(order_expr)
        self._query = self._query.order_by(order_expr)
        return self
    
    def latest(self, column: str = 'created_at') -> Self:
        """Order by column descending (Laravel 12)."""
        return self.order_by(column, 'desc')
    
    def oldest(self, column: str = 'created_at') -> Self:
        """Order by column ascending (Laravel 12)."""
        return self.order_by(column, 'asc')
    
    def reorder(self, column: Optional[str] = None, direction: str = 'asc') -> Self:
        """Remove existing orders and add new one (Laravel 12)."""
        # Clear existing orders
        self._orders.clear()
        # Rebuild query without orders
        self._query = self._query.order_by(None)
        
        if column:
            return self.order_by(column, direction)
        return self
    
    def inRandomOrder(self, seed: Optional[int] = None) -> Self:
        """Order results randomly (Laravel 12)."""
        if seed is not None:
            # Use seeded random for reproducible results
            random_expr = func.random(seed)
        else:
            random_expr = func.random()
        
        self._query = self._query.order_by(random_expr)
        return self
    
    # Laravel 12 Grouping and Aggregation
    def group_by(self, *columns: str) -> Self:
        """Add group by clause (Laravel 12)."""
        group_columns = [self._get_column_attribute(col) for col in columns]
        self._group_by_columns.extend(group_columns)
        self._query = self._query.group_by(*group_columns)
        return self
    
    def having(self, column: str, operator: str = '=', value: Any = None) -> Self:
        """Add having clause (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        condition = self._build_condition(column_attr, operator, value)
        self._having_conditions.append(condition)
        self._query = self._query.having(condition)
        return self
    
    def having_raw(self, sql: str, bindings: Optional[List[Any]] = None) -> Self:
        """Add raw having clause (Laravel 12)."""
        if bindings:
            condition = text(sql).bindparams(*bindings)
        else:
            condition = text(sql)
        
        self._having_conditions.append(condition)
        self._query = self._query.having(condition)
        return self
    
    # Laravel 12 Limit and Offset
    def limit(self, value: int) -> Self:
        """Add limit clause (Laravel 12)."""
        self._limit_value = value
        self._query = self._query.limit(value)
        return self
    
    def take(self, value: int) -> Self:
        """Alias for limit (Laravel 12)."""
        return self.limit(value)
    
    def offset(self, value: int) -> Self:
        """Add offset clause (Laravel 12)."""
        self._offset_value = value
        self._query = self._query.offset(value)
        return self
    
    def skip(self, value: int) -> Self:
        """Alias for offset (Laravel 12)."""
        return self.offset(value)
    
    def for_page(self, page: int, per_page: int = 15) -> Self:
        """Paginate results (Laravel 12)."""
        offset_value = (page - 1) * per_page
        return self.offset(offset_value).limit(per_page)
    
    # Laravel 12 Selection Methods
    def select(self, *columns: str) -> Self:
        """Select specific columns (Laravel 12)."""
        if not columns:
            return self
        
        selected_columns = [self._get_column_attribute(col) for col in columns]
        self._query = select(*selected_columns).select_from(self.model)
        return self
    
    def add_select(self, *columns: str) -> Self:
        """Add columns to existing selection (Laravel 12)."""
        if not columns:
            return self
        
        additional_columns = [self._get_column_attribute(col) for col in columns]
        self._query = self._query.add_columns(*additional_columns)
        return self
    
    def distinct(self, *columns: str) -> Self:
        """Add distinct clause (Laravel 12)."""
        if columns:
            distinct_columns = [self._get_column_attribute(col) for col in columns]
            self._query = self._query.distinct(*distinct_columns)
        else:
            self._query = self._query.distinct()
        
        self._distinct_value = True
        return self
    
    # Laravel 12 Relationship Loading
    def with_relations(self, *relations: str) -> Self:
        """Eager load relationships (Laravel 12)."""
        for relation in relations:
            if not hasattr(self.model, relation):
                raise RelationshipNotFoundException(f"Relationship '{relation}' not found on {self.model.__name__}")
            
            # Configure eager loading strategy
            self._relationships[relation] = selectinload(getattr(self.model, relation))
        
        return self
    
    def with_joined(self, *relations: str) -> Self:
        """Eager load relationships using JOIN (Laravel 12)."""
        for relation in relations:
            if not hasattr(self.model, relation):
                raise RelationshipNotFoundException(f"Relationship '{relation}' not found on {self.model.__name__}")
            
            self._relationships[relation] = joinedload(getattr(self.model, relation))
        
        return self
    
    def without_relations(self, *relations: str) -> Self:
        """Remove eager loaded relationships (Laravel 12)."""
        for relation in relations:
            self._relationships.pop(relation, None)
        return self
    
    def with_count(self, *relations: str) -> Self:
        """Include relationship counts (Laravel 12)."""
        for relation in relations:
            if not hasattr(self.model, relation):
                raise RelationshipNotFoundException(f"Relationship '{relation}' not found on {self.model.__name__}")
            
            self._relationship_counts.append(relation)
            
            # Add count subquery
            relation_attr = getattr(self.model, relation)
            count_subquery = select(func.count()).select_from(
                relation_attr.property.mapper.class_
            ).scalar_subquery()
            
            self._query = self._query.add_columns(
                count_subquery.label(f"{relation}_count")
            )
        
        return self
    
    # Laravel 12 Execution Methods
    def get(self) -> List[T]:
        """Execute query and get all results (Laravel 12)."""
        self._apply_global_scopes()
        self._apply_eager_loading()
        
        result = self.session.execute(self._query)
        models = result.scalars().all()
        
        # Fire retrieved events
        for model in models:
            if hasattr(model, 'fire_retrieved_event'):
                model.fire_retrieved_event()
        
        return models
    
    def first(self) -> Optional[T]:
        """Execute query and get first result (Laravel 12)."""
        result = self.limit(1).get()
        return result[0] if result else None
    
    def first_or_fail(self) -> T:
        """Execute query and get first result or raise exception (Laravel 12)."""
        result = self.first()
        if result is None:
            raise QueryBuilderException(f"No {self.model.__name__} found")
        return result
    
    def find(self, id_value: Any) -> Optional[T]:
        """Find record by primary key (Laravel 12)."""
        primary_key = getattr(self.model, self.model.__primary_key__)
        return self.where(self.model.__primary_key__, '=', id_value).first()
    
    def find_or_fail(self, id_value: Any) -> T:
        """Find record by primary key or raise exception (Laravel 12)."""
        result = self.find(id_value)
        if result is None:
            raise QueryBuilderException(f"No {self.model.__name__} found with id {id_value}")
        return result
    
    def find_many(self, ids: List[Any]) -> List[T]:
        """Find multiple records by primary keys (Laravel 12)."""
        return self.where_in(self.model.__primary_key__, ids).get()
    
    def all(self) -> List[T]:
        """Get all records (Laravel 12)."""
        return self.get()
    
    def chunk(self, size: int, callback: Callable[[List[T]], bool]) -> int:
        """Process results in chunks (Laravel 12)."""
        processed = 0
        offset = 0
        
        while True:
            chunk_query = self._clone()
            chunk_results = chunk_query.offset(offset).limit(size).get()
            
            if not chunk_results:
                break
            
            processed += len(chunk_results)
            
            # Call the callback with the chunk
            should_continue = callback(chunk_results)
            if should_continue is False:
                break
            
            offset += size
        
        return processed
    
    def chunk_by_id(self, size: int, callback: Callable[[List[T]], bool], column: str = 'id') -> int:
        """Process results in chunks by ID (Laravel 12)."""
        processed = 0
        last_id = None
        
        while True:
            chunk_query = self._clone()
            
            if last_id is not None:
                chunk_query = chunk_query.where(column, '>', last_id)
            
            chunk_query = chunk_query.order_by(column).limit(size)
            chunk_results = chunk_query.get()
            
            if not chunk_results:
                break
            
            processed += len(chunk_results)
            last_id = getattr(chunk_results[-1], column)
            
            # Call the callback with the chunk
            should_continue = callback(chunk_results)
            if should_continue is False:
                break
        
        return processed
    
    # Laravel 12 Aggregation Methods
    def count(self, column: str = '*') -> int:
        """Get count of records (Laravel 12)."""
        self._apply_global_scopes()
        
        if column == '*':
            count_query = select(func.count()).select_from(self._query.subquery())
        else:
            column_attr = self._get_column_attribute(column)
            count_query = select(func.count(column_attr)).select_from(self._query.subquery())
        
        result = self.session.execute(count_query)
        return result.scalar() or 0
    
    def max(self, column: str) -> Any:
        """Get maximum value (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        max_query = select(func.max(column_attr)).select_from(self._query.subquery())
        result = self.session.execute(max_query)
        return result.scalar()
    
    def min(self, column: str) -> Any:
        """Get minimum value (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        min_query = select(func.min(column_attr)).select_from(self._query.subquery())
        result = self.session.execute(min_query)
        return result.scalar()
    
    def avg(self, column: str) -> Optional[float]:
        """Get average value (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        avg_query = select(func.avg(column_attr)).select_from(self._query.subquery())
        result = self.session.execute(avg_query)
        value = result.scalar()
        return float(value) if value is not None else None
    
    def sum(self, column: str) -> Any:
        """Get sum of values (Laravel 12)."""
        column_attr = self._get_column_attribute(column)
        sum_query = select(func.sum(column_attr)).select_from(self._query.subquery())
        result = self.session.execute(sum_query)
        return result.scalar()
    
    # Laravel 12 Existence Methods
    def exists(self) -> bool:
        """Check if any records exist (Laravel 12)."""
        self._apply_global_scopes()
        exists_query = select(exists(self._query))
        result = self.session.execute(exists_query)
        return result.scalar() or False
    
    def doesnt_exist(self) -> bool:
        """Check if no records exist (Laravel 12)."""
        return not self.exists()
    
    # Laravel 12 Utility Methods
    def _get_column_attribute(self, column: str) -> Any:
        """Get SQLAlchemy column attribute."""
        if hasattr(self.model, column):
            return getattr(self.model, column)
        else:
            raise AttributeError(f"Column '{column}' not found on {self.model.__name__}")
    
    def _build_condition(self, column_attr: Any, operator: str, value: Any) -> Any:
        """Build SQLAlchemy condition based on operator."""
        op = operator.lower().strip()
        
        if op in ('=', '=='):
            return column_attr == value
        elif op in ('!=', '<>', 'ne'):
            return column_attr != value
        elif op == '<':
            return column_attr < value
        elif op == '>':
            return column_attr > value
        elif op == '<=':
            return column_attr <= value
        elif op == '>=':
            return column_attr >= value
        elif op == 'like':
            return column_attr.like(value)
        elif op == 'ilike':
            return column_attr.ilike(value)
        elif op == 'not like':
            return ~column_attr.like(value)
        elif op == 'not ilike':
            return ~column_attr.ilike(value)
        elif op == 'in':
            return column_attr.in_(value if isinstance(value, (list, tuple)) else [value])
        elif op == 'not in':
            return ~column_attr.in_(value if isinstance(value, (list, tuple)) else [value])
        elif op == 'between':
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return column_attr.between(value[0], value[1])
            else:
                raise ValueError("Between operator requires a list/tuple of 2 values")
        elif op == 'not between':
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return ~column_attr.between(value[0], value[1])
            else:
                raise ValueError("Not between operator requires a list/tuple of 2 values")
        elif op == 'is':
            return column_attr.is_(value)
        elif op == 'is not':
            return column_attr.is_not(value)
        elif op in ('regexp', 'rlike'):
            return column_attr.op('REGEXP')(value)
        elif op in ('not regexp', 'not rlike'):
            return ~column_attr.op('REGEXP')(value)
        else:
            raise InvalidOperatorException(f"Unsupported operator: {operator}")
    
    def _apply_global_scopes(self) -> None:
        """Apply global scopes to the query."""
        if self._global_scopes_applied:
            return
        
        # Apply model's global scopes
        for scope_name, scope in self.model.__global_scopes__.items():
            if scope_name not in self._without_global_scopes:
                self._query = scope(self._query)
        
        self._global_scopes_applied = True
    
    def _apply_eager_loading(self) -> None:
        """Apply eager loading options to the query."""
        if self._relationships:
            options = list(self._relationships.values())
            self._query = self._query.options(*options)
    
    def _extract_where_conditions(self) -> List[Any]:
        """Extract where conditions from the current query."""
        conditions = []
        if self._query.whereclause is not None:
            conditions.append(self._query.whereclause)
        return conditions
    
    def _clone(self) -> 'EnhancedQueryBuilder[T]':
        """Create a copy of this query builder."""
        clone = EnhancedQueryBuilder(self.model, self.session)
        clone._query = self._query
        clone._relationships = self._relationships.copy()
        clone._relationship_counts = self._relationship_counts.copy()
        clone._scopes = self._scopes.copy()
        clone._global_scopes_applied = self._global_scopes_applied
        clone._without_global_scopes = self._without_global_scopes.copy()
        clone._orders = self._orders.copy()
        clone._limit_value = self._limit_value
        clone._offset_value = self._offset_value
        clone._distinct_value = self._distinct_value
        clone._group_by_columns = self._group_by_columns.copy()
        clone._having_conditions = self._having_conditions.copy()
        clone._unions = self._unions.copy()
        clone._lock_mode = self._lock_mode
        clone._from_raw = self._from_raw
        return clone


# Backward compatibility alias
QueryBuilder = EnhancedQueryBuilder


# Export Laravel 12 query builder functionality
__all__ = [
    'EnhancedQueryBuilder',
    'QueryBuilder',  # For backward compatibility
    'QueryBuilderContract',
    'RelationshipQueryBuilder',
    'QueryBuilderException',
    'InvalidOperatorException',
    'RelationshipNotFoundException',
]