from __future__ import annotations

from enum import Enum
from typing import Any
from sqlalchemy import Column
from sqlalchemy.orm import Query as SQLQuery


class FilterOperator(Enum):
    """Filter operators for QueryBuilder"""
    
    # Comparison operators
    EQUAL = "="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    
    # Text operators
    LIKE = "like"
    NOT_LIKE = "not_like"
    ILIKE = "ilike"  # Case insensitive like
    NOT_ILIKE = "not_ilike"
    
    # Array operators
    IN = "in"
    NOT_IN = "not_in"
    
    # Null operators
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    
    # Range operators
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    
    # Dynamic operator (allows user to specify operator in query)
    DYNAMIC = "dynamic"
    
    def apply_to_query(self, query: SQLQuery, column: Column, value: Any) -> SQLQuery:
        """Apply the operator to a query"""
        
        if self == FilterOperator.EQUAL:
            return query.filter(column == value)
        elif self == FilterOperator.NOT_EQUAL:
            return query.filter(column != value)
        elif self == FilterOperator.GREATER_THAN:
            return query.filter(column > value)
        elif self == FilterOperator.GREATER_THAN_OR_EQUAL:
            return query.filter(column >= value)
        elif self == FilterOperator.LESS_THAN:
            return query.filter(column < value)
        elif self == FilterOperator.LESS_THAN_OR_EQUAL:
            return query.filter(column <= value)
        elif self == FilterOperator.LIKE:
            return query.filter(column.like(f"%{value}%"))
        elif self == FilterOperator.NOT_LIKE:
            return query.filter(~column.like(f"%{value}%"))
        elif self == FilterOperator.ILIKE:
            return query.filter(column.ilike(f"%{value}%"))
        elif self == FilterOperator.NOT_ILIKE:
            return query.filter(~column.ilike(f"%{value}%"))
        elif self == FilterOperator.IN:
            if isinstance(value, str):
                value = [v.strip() for v in value.split(",")]
            return query.filter(column.in_(value))
        elif self == FilterOperator.NOT_IN:
            if isinstance(value, str):
                value = [v.strip() for v in value.split(",")]
            return query.filter(~column.in_(value))
        elif self == FilterOperator.IS_NULL:
            return query.filter(column.is_(None))
        elif self == FilterOperator.IS_NOT_NULL:
            return query.filter(column.isnot(None))
        elif self == FilterOperator.BETWEEN:
            if isinstance(value, str):
                values = [v.strip() for v in value.split(",")]
                if len(values) == 2:
                    return query.filter(column.between(values[0], values[1]))
            elif isinstance(value, list) and len(value) == 2:
                return query.filter(column.between(value[0], value[1]))
            return query
        elif self == FilterOperator.NOT_BETWEEN:
            if isinstance(value, str):
                values = [v.strip() for v in value.split(",")]
                if len(values) == 2:
                    return query.filter(~column.between(values[0], values[1]))
            elif isinstance(value, list) and len(value) == 2:
                return query.filter(~column.between(value[0], value[1]))
            return query
        else:
            return query
    
    @classmethod
    def from_string(cls, operator: str) -> FilterOperator:
        """Convert string operator to FilterOperator enum"""
        operator_map = {
            "=": cls.EQUAL,
            "==": cls.EQUAL,
            "!=": cls.NOT_EQUAL,
            "<>": cls.NOT_EQUAL,
            ">": cls.GREATER_THAN,
            ">=": cls.GREATER_THAN_OR_EQUAL,
            "<": cls.LESS_THAN,
            "<=": cls.LESS_THAN_OR_EQUAL,
            "like": cls.LIKE,
            "not_like": cls.NOT_LIKE,
            "ilike": cls.ILIKE,
            "not_ilike": cls.NOT_ILIKE,
            "in": cls.IN,
            "not_in": cls.NOT_IN,
            "is_null": cls.IS_NULL,
            "is_not_null": cls.IS_NOT_NULL,
            "between": cls.BETWEEN,
            "not_between": cls.NOT_BETWEEN
        }
        
        return operator_map.get(operator.lower(), cls.EQUAL)
    
    def is_dynamic(self) -> bool:
        """Check if this is a dynamic operator"""
        return self == FilterOperator.DYNAMIC