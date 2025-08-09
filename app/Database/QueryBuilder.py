from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, Callable, List, Union, Type, TypeVar, Tuple
from datetime import datetime
from sqlalchemy import String, DateTime, func, event, ForeignKey, and_, or_, Table, Column, desc, asc, text, select
from sqlalchemy.sql import Select
from sqlalchemy.orm import Session, selectinload, joinedload, contains_eager, Query
from sqlalchemy.ext.hybrid import hybrid_property
from functools import wraps
from enum import Enum
import json

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound='BaseModel')


class QueryBuilder:
    """Laravel-style query builder for SQLAlchemy."""
    
    def __init__(self, model: Type[T], session: Session) -> None:
        self.model = model
        self.session = session
        self._query = select(model)
        self._wheres: List[Any] = []
        self._orders: List[Any] = []
        self._limits: Optional[int] = None
        self._offsets: Optional[int] = None
        self._includes: List[str] = []
        self._group_bys: List[Any] = []
        self._havings: List[Any] = []
        self._distinct_columns: List[Any] = []
        
    def where(self, column: Union[str, Callable[..., Any]], operator: Optional[str] = None, value: Any = None) -> QueryBuilder:
        """Laravel-style where clause."""
        if callable(column):
            # Support for closure-based where
            column(self)
        elif operator is None and value is None:
            # where(column, value) - assumes equals
            self._wheres.append(getattr(self.model, column) == operator)
        elif value is None:
            # where(column, operator) - assumes value is in operator
            self._wheres.append(getattr(self.model, column) == operator)
        else:
            # where(column, operator, value)
            column_attr = getattr(self.model, column)
            if operator == '=':
                self._wheres.append(column_attr == value)
            elif operator == '!=':
                self._wheres.append(column_attr != value)
            elif operator == '>':
                self._wheres.append(column_attr > value)
            elif operator == '>=':
                self._wheres.append(column_attr >= value)
            elif operator == '<':
                self._wheres.append(column_attr < value)
            elif operator == '<=':
                self._wheres.append(column_attr <= value)
            elif operator == 'like':
                self._wheres.append(column_attr.like(value))
            elif operator == 'ilike':
                self._wheres.append(column_attr.ilike(value))
            elif operator == 'in':
                self._wheres.append(column_attr.in_(value))
            elif operator == 'not in':
                self._wheres.append(~column_attr.in_(value))
            elif operator == 'is null':
                self._wheres.append(column_attr.is_(None))
            elif operator == 'is not null':
                self._wheres.append(column_attr.is_not(None))
        
        return self
    
    def or_where(self, column: Union[str, Callable[..., Any]], operator: Optional[str] = None, value: Any = None) -> QueryBuilder:
        """Laravel-style or where clause."""
        # This would need to be implemented with proper OR logic
        return self.where(column, operator, value)
    
    def where_in(self, column: str, values: List[Any]) -> QueryBuilder:
        """Laravel-style where in clause."""
        self._wheres.append(getattr(self.model, column).in_(values))
        return self
    
    def where_not_in(self, column: str, values: List[Any]) -> QueryBuilder:
        """Laravel-style where not in clause."""
        self._wheres.append(~getattr(self.model, column).in_(values))
        return self
    
    def where_null(self, column: str) -> QueryBuilder:
        """Laravel-style where null clause."""
        self._wheres.append(getattr(self.model, column).is_(None))
        return self
    
    def where_not_null(self, column: str) -> QueryBuilder:
        """Laravel-style where not null clause."""
        self._wheres.append(getattr(self.model, column).is_not(None))
        return self
    
    def where_between(self, column: str, start: Any, end: Any) -> QueryBuilder:
        """Laravel-style where between clause."""
        self._wheres.append(getattr(self.model, column).between(start, end))
        return self
    
    def where_not_between(self, column: str, start: Any, end: Any) -> QueryBuilder:
        """Laravel-style where not between clause."""
        self._wheres.append(~getattr(self.model, column).between(start, end))
        return self
    
    def where_date(self, column: str, operator: str, value: Union[str, datetime]) -> QueryBuilder:
        """Laravel-style where date clause."""
        column_attr = getattr(self.model, column)
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        
        if operator == '=':
            # Extract date part and compare
            self._wheres.append(func.date(column_attr) == value.date())
        elif operator == '>':
            self._wheres.append(func.date(column_attr) > value.date())
        elif operator == '<':
            self._wheres.append(func.date(column_attr) < value.date())
        
        return self
    
    def where_year(self, column: str, operator: str, value: int) -> QueryBuilder:
        """Laravel-style where year clause."""
        column_attr = getattr(self.model, column)
        if operator == '=':
            self._wheres.append(func.extract('year', column_attr) == value)
        elif operator == '>':
            self._wheres.append(func.extract('year', column_attr) > value)
        elif operator == '<':
            self._wheres.append(func.extract('year', column_attr) < value)
        
        return self
    
    def where_month(self, column: str, operator: str, value: int) -> QueryBuilder:
        """Laravel-style where month clause."""
        column_attr = getattr(self.model, column)
        if operator == '=':
            self._wheres.append(func.extract('month', column_attr) == value)
        elif operator == '>':
            self._wheres.append(func.extract('month', column_attr) > value)
        elif operator == '<':
            self._wheres.append(func.extract('month', column_attr) < value)
        
        return self
    
    def where_day(self, column: str, operator: str, value: int) -> QueryBuilder:
        """Laravel-style where day clause."""
        column_attr = getattr(self.model, column)
        if operator == '=':
            self._wheres.append(func.extract('day', column_attr) == value)
        elif operator == '>':
            self._wheres.append(func.extract('day', column_attr) > value)
        elif operator == '<':
            self._wheres.append(func.extract('day', column_attr) < value)
        
        return self
    
    def order_by(self, column: str, direction: str = 'asc') -> QueryBuilder:
        """Laravel-style order by clause."""
        column_attr = getattr(self.model, column)
        if direction.lower() == 'desc':
            self._orders.append(desc(column_attr))
        else:
            self._orders.append(asc(column_attr))
        return self
    
    def latest(self, column: str = 'created_at') -> QueryBuilder:
        """Laravel-style latest method."""
        return self.order_by(column, 'desc')
    
    def oldest(self, column: str = 'created_at') -> QueryBuilder:
        """Laravel-style oldest method."""
        return self.order_by(column, 'asc')
    
    def limit(self, count: int) -> QueryBuilder:
        """Laravel-style limit clause."""
        self._limits = count
        return self
    
    def take(self, count: int) -> QueryBuilder:
        """Laravel-style take method (alias for limit)."""
        return self.limit(count)
    
    def offset(self, count: int) -> QueryBuilder:
        """Laravel-style offset clause."""
        self._offsets = count
        return self
    
    def skip(self, count: int) -> QueryBuilder:
        """Laravel-style skip method (alias for offset)."""
        return self.offset(count)
    
    def with_(self, *relations: str) -> QueryBuilder:
        """Laravel-style eager loading."""
        self._includes.extend(relations)
        return self
    
    def with_count(self, *relations: str) -> QueryBuilder:
        """Laravel-style with count."""
        # This would add count columns for relationships
        return self
    
    def group_by(self, *columns: str) -> QueryBuilder:
        """Laravel-style group by clause."""
        for column in columns:
            self._group_bys.append(getattr(self.model, column))
        return self
    
    def having(self, column: str, operator: str, value: Any) -> QueryBuilder:
        """Laravel-style having clause."""
        column_attr = getattr(self.model, column)
        if operator == '=':
            self._havings.append(column_attr == value)
        elif operator == '>':
            self._havings.append(column_attr > value)
        elif operator == '<':
            self._havings.append(column_attr < value)
        # Add more operators as needed
        return self
    
    def distinct(self, *columns: str) -> QueryBuilder:
        """Laravel-style distinct clause."""
        if columns:
            for column in columns:
                self._distinct_columns.append(getattr(self.model, column))
        else:
            self._query = self._query.distinct()
        return self
    
    def _build_query(self) -> Select[Tuple[T]]:
        """Build the final SQLAlchemy query."""
        query = self._query
        
        # Apply where clauses
        if self._wheres:
            query = query.where(and_(*self._wheres))
        
        # Apply group by
        if self._group_bys:
            query = query.group_by(*self._group_bys)
        
        # Apply having clauses
        if self._havings:
            query = query.having(and_(*self._havings))
        
        # Apply order by
        if self._orders:
            query = query.order_by(*self._orders)
        
        # Apply limit
        if self._limits is not None:
            query = query.limit(self._limits)
        
        # Apply offset
        if self._offsets is not None:
            query = query.offset(self._offsets)
        
        # Apply distinct columns
        if self._distinct_columns:
            query = query.distinct(*self._distinct_columns)
        
        # Apply eager loading
        for include in self._includes:
            # This would need proper relationship handling
            pass
        
        return query
    
    def get(self) -> List[T]:
        """Execute query and return all results."""
        query: Any = self._build_query()
        return list(self.session.execute(query).scalars().all())
    
    def all(self) -> List[T]:
        """Laravel-style all method (alias for get)."""
        return self.get()
    
    def first(self) -> Optional[T]:
        """Execute query and return first result."""
        query: Any = self._build_query().limit(1)
        result = self.session.execute(query).scalar()
        return result
    
    def first_or_fail(self) -> T:
        """Execute query and return first result or raise exception."""
        result = self.first()
        if result is None:
            raise ValueError(f"No {self.model.__name__} found")
        return result
    
    def find(self, id_value: Any) -> Optional[T]:
        """Find by ID."""
        return self.where('id', id_value).first()
    
    def find_or_fail(self, id_value: Any) -> T:
        """Find by ID or raise exception."""
        result = self.find(id_value)
        if result is None:
            raise ValueError(f"{self.model.__name__} with id {id_value} not found")
        return result
    
    def paginate(self, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Laravel-style pagination."""
        total_query = select(func.count()).select_from(self.model)
        if self._wheres:
            total_query = total_query.where(and_(*self._wheres))
        
        total = self.session.execute(total_query).scalar() or 0
        
        # Calculate pagination values
        offset_val = (page - 1) * per_page
        last_page = (total + per_page - 1) // per_page
        
        # Get the data
        data: List[T] = self.offset(offset_val).limit(per_page).get()
        
        return {
            'data': data,
            'current_page': page,
            'per_page': per_page,
            'total': total,
            'last_page': last_page,
            'from': offset_val + 1 if data else 0,
            'to': min(offset_val + per_page, total) if data else 0,
            'has_more': page < last_page
        }
    
    def count(self) -> int:
        """Get count of records."""
        query = select(func.count()).select_from(self.model)
        if self._wheres:
            query = query.where(and_(*self._wheres))
        return self.session.execute(query).scalar() or 0
    
    def exists(self) -> bool:
        """Check if any records exist."""
        return self.count() > 0
    
    def doesnt_exist(self) -> bool:
        """Check if no records exist."""
        return not self.exists()
    
    def max(self, column: str) -> Any:
        """Get maximum value of column."""
        query = select(func.max(getattr(self.model, column)))
        if self._wheres:
            query = query.where(and_(*self._wheres))
        return self.session.execute(query).scalar()
    
    def min(self, column: str) -> Any:
        """Get minimum value of column."""
        query = select(func.min(getattr(self.model, column)))
        if self._wheres:
            query = query.where(and_(*self._wheres))
        return self.session.execute(query).scalar()
    
    def avg(self, column: str) -> Any:
        """Get average value of column."""
        query = select(func.avg(getattr(self.model, column)))
        if self._wheres:
            query = query.where(and_(*self._wheres))
        return self.session.execute(query).scalar()
    
    def sum(self, column: str) -> Any:
        """Get sum of column values."""
        query = select(func.sum(getattr(self.model, column)))
        if self._wheres:
            query = query.where(and_(*self._wheres))
        return self.session.execute(query).scalar() or 0
    
    def pluck(self, column: str, key_column: Optional[str] = None) -> Union[List[Any], Dict[Any, Any]]:
        """Laravel-style pluck method."""
        if key_column:
            # Return as dictionary
            query = select(getattr(self.model, key_column), getattr(self.model, column))
        else:
            # Return as list
            query = select(getattr(self.model, column))
        
        if self._wheres:
            query = query.where(and_(*self._wheres))
        
        results = self.session.execute(query).all()
        
        if key_column:
            return {row[0]: row[1] for row in results}
        else:
            return [row[0] for row in results]
    
    def chunk(self, size: int, callback: Callable[[List[T]], bool]) -> bool:
        """Laravel-style chunk processing."""
        offset_val = 0
        while True:
            chunk_data: List[T] = self.offset(offset_val).limit(size).get()
            if not chunk_data:
                break
            
            # Call the callback
            if callback(chunk_data) is False:
                return False
            
            offset_val += size
        
        return True
    
    def each(self, callback: Callable[[T], bool]) -> bool:
        """Laravel-style each processing."""
        item: T
        for item in self.get():
            if callback(item) is False:
                return False
        return True
    
    def update(self, values: Dict[str, Any]) -> int:
        """Bulk update records."""
        # This would need to be implemented with proper update query
        # For now, just return 0
        return 0
    
    def delete(self) -> int:
        """Bulk delete records."""
        # This would need to be implemented with proper delete query
        # For now, just return 0
        return 0


__all__ = ['QueryBuilder']