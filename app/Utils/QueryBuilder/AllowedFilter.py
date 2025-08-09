from __future__ import annotations

from typing import Optional, Union, List, Callable, Dict, TYPE_CHECKING, cast
from abc import ABC, abstractmethod
import re

if TYPE_CHECKING:
    from sqlalchemy.orm import Query
    from app.Models.BaseModel import BaseModel
    SQLQuery = Query[BaseModel]
else:
    from sqlalchemy.orm import Query
    SQLQuery = Query
from sqlalchemy import Column, and_, or_, text, inspect
from sqlalchemy.orm import joinedload, selectinload, contains_eager
from .FilterOperators import FilterOperator


class FilterInterface(ABC):
    """Interface for filter implementations"""
    
    @abstractmethod
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        """Apply filter to query"""
        pass


class AllowedFilter:
    """
    Represents an allowed filter for QueryBuilder
    Inspired by Spatie Laravel Query Builder
    """
    
    def __init__(
        self,
        name: str,
        internal_name: Optional[str] = None,
        filter_class: Optional[FilterInterface] = None,
        default_value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None] = None,
        nullable: bool = False,
        ignored_values: Optional[List[Union[str, int, float, bool, None]]] = None,
        array_delimiter: str = ','
    ) -> None:
        self.name = name
        self.internal_name = internal_name or name
        self.filter_class = filter_class
        self.default_value = default_value
        self._nullable = nullable
        self.ignored_values = ignored_values or []
        self.array_delimiter = array_delimiter
    
    @classmethod
    def partial(
        cls, 
        name: str, 
        internal_name: Optional[str] = None,
        add_relation_constraint: bool = True
    ) -> AllowedFilter:
        """Create partial match filter (LIKE/ILIKE)"""
        filter_impl = PartialFilter(add_relation_constraint)
        return cls(name, internal_name, filter_impl)
    
    @classmethod
    def exact(
        cls, 
        name: str, 
        internal_name: Optional[str] = None,
        add_relation_constraint: bool = True,
        array_delimiter: Optional[str] = None
    ) -> AllowedFilter:
        """Create exact match filter"""
        filter_impl = ExactFilter(add_relation_constraint, array_delimiter)
        return cls(name, internal_name, filter_impl)
    
    @classmethod
    def operator(
        cls, 
        name: str,
        operator: FilterOperator,
        internal_name: Optional[str] = None,
        add_relation_constraint: bool = True
    ) -> AllowedFilter:
        """Create operator-based filter"""
        filter_impl = OperatorFilter(operator, add_relation_constraint)
        return cls(name, internal_name, filter_impl)
    
    @classmethod
    def scope(
        cls, 
        name: str, 
        scope_name: Optional[str] = None
    ) -> AllowedFilter:
        """Create scope filter (calls model scope method)"""
        filter_impl = ScopeFilter(scope_name or name)
        return cls(name, name, filter_impl)
    
    @classmethod
    def callback(
        cls, 
        name: str, 
        callback: Callable[[SQLQuery, Union[str, int, float, bool, List[Union[str, int, float, bool]], None], str], SQLQuery]
    ) -> AllowedFilter:
        """Create callback filter"""
        filter_impl = CallbackFilter(callback)
        return cls(name, name, filter_impl)
    
    @classmethod
    def custom(
        cls, 
        name: str, 
        filter_class: FilterInterface,
        internal_name: Optional[str] = None
    ) -> AllowedFilter:
        """Create custom filter"""
        return cls(name, internal_name, filter_class)
    
    @classmethod
    def belongs_to(
        cls, 
        name: str, 
        relationship_path: Optional[str] = None
    ) -> AllowedFilter:
        """Create belongs-to relationship filter"""
        filter_impl = BelongsToFilter(relationship_path or name)
        return cls(name, name, filter_impl)
    
    @classmethod
    def trashed(cls, name: str = "trashed") -> AllowedFilter:
        """Create trashed (soft delete) filter"""
        filter_impl = TrashedFilter()
        return cls(name, name, filter_impl)
    
    def default(self, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> AllowedFilter:
        """Set default value for filter"""
        self.default_value = value
        return self
    
    def nullable(self, nullable: bool = True) -> AllowedFilter:
        """Allow nullable values"""
        self._nullable = nullable
        return self
    
    def ignore(self, *values: Union[str, int, float, bool, None]) -> AllowedFilter:
        """Set values to ignore"""
        if len(values) == 1 and isinstance(values[0], list):
            self.ignored_values = values[0]
        else:
            self.ignored_values = list(values)
        return self
    
    def should_apply_filter(self, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> bool:
        """Check if filter should be applied based on value and settings"""
        # Parse comma-separated values if needed
        parsed_values = self._parse_array_values(value)
        
        # Check if all values should be ignored
        if isinstance(parsed_values, list):
            remaining_values = [v for v in parsed_values if v not in self.ignored_values]
            if not remaining_values:
                return False
        else:
            if parsed_values in self.ignored_values:
                return False
        
        # Check nullable
        if not self._nullable and (parsed_values is None or parsed_values == ""):
            return False
        
        return True
    
    def _parse_array_values(self, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> Union[str, int, float, bool, List[Union[str, int, float, bool]], None]:
        """Parse array values using delimiter"""
        if isinstance(value, str) and self.array_delimiter in value:
            return [v.strip() for v in value.split(self.array_delimiter) if v.strip()]
        return value
    
    def apply(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], model_class: type) -> SQLQuery:
        """Apply filter to query"""
        # Parse array values
        parsed_value = self._parse_array_values(value)
        
        # Filter out ignored values
        if isinstance(parsed_value, list):
            parsed_value = [v for v in parsed_value if v not in self.ignored_values]
            if not parsed_value and self.default_value is None:
                return query
        
        if not self.should_apply_filter(parsed_value):
            # Use default value if filter shouldn't apply normally
            if self.default_value is not None:
                parsed_value = self.default_value
            else:
                return query
        
        if self.filter_class:
            return self.filter_class(query, parsed_value, self.internal_name)
        else:
            # Default exact filter behavior
            column = self._get_column(model_class, self.internal_name)
            if column is not None:
                if isinstance(parsed_value, list):
                    return query.filter(column.in_(parsed_value))
                else:
                    return query.filter(column == parsed_value)
            return query
    
    def _get_column(self, model_class: type, property_name: str) -> Optional[Column]:
        """Get column from model class, handling relationships"""
        try:
            if '.' in property_name:
                # Handle nested relationships
                parts = property_name.split('.')
                current_model = model_class
                
                for i, part in enumerate(parts[:-1]):
                    if hasattr(current_model, part):
                        relationship = getattr(current_model, part)
                        if hasattr(relationship.property, 'mapper'):
                            current_model = relationship.property.mapper.class_
                        else:
                            return None
                    else:
                        return None
                
                # Get the final column
                final_column = parts[-1]
                if hasattr(current_model, final_column):
                    return cast(Column, getattr(current_model, final_column))
            else:
                # Simple column access
                if hasattr(model_class, property_name):
                    return cast(Column, getattr(model_class, property_name))
            
            return None
        except Exception:
            return None


class PartialFilter(FilterInterface):
    """Partial match filter using LIKE/ILIKE"""
    
    def __init__(self, add_relation_constraint: bool = True) -> None:
        self.add_relation_constraint = add_relation_constraint
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        column, query = self._resolve_column_and_query(query, property_name)
        if column is None:
            return query
        
        if isinstance(value, list):
            conditions = []
            for v in value:
                if v is not None and v != '':
                    conditions.append(column.ilike(f'%{v}%'))
            if conditions:
                return query.filter(or_(*conditions))  # type: ignore[arg-type]
        else:
            if value is not None and value != '':
                return query.filter(column.ilike(f'%{value}%'))
        
        return query
    
    def _resolve_column_and_query(self, query: SQLQuery, property_name: str) -> tuple[Optional[Column], SQLQuery]:
        """Resolve column and potentially modify query with joins"""
        if '.' in property_name and self.add_relation_constraint:
            parts = property_name.split('.')
            if len(parts) == 2:
                # Handle simple relationship.column pattern
                relationship_name, column_name = parts
                
                # Get the model from query
                model = self._get_model_from_query(query)
                if model and hasattr(model, relationship_name):
                    relationship = getattr(model, relationship_name)
                    
                    # Add join if not already present
                    if hasattr(relationship.property, 'mapper'):
                        related_model = relationship.property.mapper.class_
                        query = query.join(relationship)
                        
                        if hasattr(related_model, column_name):
                            return getattr(related_model, column_name), query
        else:
            # Simple column access
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name), query
        
        return None, query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions: List[Dict[str, Any]] = query.column_descriptions
                if descriptions and len(descriptions) > 0 and descriptions[0].get('entity'):
                    return cast(type, descriptions[0]['entity'])
            return None
        except Exception:
            return None


class ExactFilter(FilterInterface):
    """Exact match filter"""
    
    def __init__(self, add_relation_constraint: bool = True, array_delimiter: Optional[str] = None) -> None:
        self.add_relation_constraint = add_relation_constraint
        self.array_delimiter = array_delimiter or ","
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        # Handle comma-separated values
        if isinstance(value, str) and self.array_delimiter in value:
            value = [v.strip() for v in value.split(self.array_delimiter) if v.strip()]
        
        column, query = self._resolve_column_and_query(query, property_name)
        if column is None:
            return query
        
        # Handle boolean values
        if isinstance(value, str):
            if value.lower() in ('true', '1'):
                value = True
            elif value.lower() in ('false', '0'):
                value = False
        
        # Apply filter
        if isinstance(value, list):
            if value:  # Only apply if list is not empty
                return query.filter(column.in_(value))
        else:
            return query.filter(column == value)
        
        return query
    
    def _resolve_column_and_query(self, query: SQLQuery, property_name: str) -> tuple[Optional[Column], SQLQuery]:
        """Resolve column and potentially modify query with joins"""
        if '.' in property_name and self.add_relation_constraint:
            parts = property_name.split('.')
            if len(parts) == 2:
                # Handle simple relationship.column pattern
                relationship_name, column_name = parts
                
                # Get the model from query
                model = self._get_model_from_query(query)
                if model and hasattr(model, relationship_name):
                    relationship = getattr(model, relationship_name)
                    
                    # Add join if not already present
                    if hasattr(relationship.property, 'mapper'):
                        related_model = relationship.property.mapper.class_
                        query = query.join(relationship)
                        
                        if hasattr(related_model, column_name):
                            return getattr(related_model, column_name), query
        else:
            # Simple column access
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name), query
        
        return None, query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions: List[Dict[str, Any]] = query.column_descriptions
                if descriptions and len(descriptions) > 0 and descriptions[0].get('entity'):
                    return cast(type, descriptions[0]['entity'])
            return None
        except Exception:
            return None


class OperatorFilter(FilterInterface):
    """Operator-based filter with support for dynamic and static operators"""
    
    def __init__(self, operator: FilterOperator, add_relation_constraint: bool = True) -> None:
        self.operator = operator
        self.add_relation_constraint = add_relation_constraint
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        column, query = self._resolve_column_and_query(query, property_name)
        if column is None:
            return query
        
        if self.operator == FilterOperator.DYNAMIC:
            return self._apply_dynamic_operator(query, column, value)
        else:
            return self._apply_static_operator(query, column, value)
    
    def _apply_dynamic_operator(self, query: SQLQuery, column: Column, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> SQLQuery:
        """Apply dynamic operator based on value format"""
        # Support various formats for dynamic operators:
        # 1. Dict format: {'operator': '>', 'value': 100}
        # 2. String format with operator prefix: '>100', '>=100', 'like:john'
        # 3. URL parameter format: ?filter[salary]=>3000
        
        if isinstance(value, dict) and 'operator' in value and 'value' in value:
            operator = value['operator'].lower()
            filter_value = value['value']
        elif isinstance(value, str):
            operator, filter_value = self._parse_operator_string(value)
        else:
            # Default to equality
            operator, filter_value = 'eq', value
        
        return self._apply_operator(query, column, operator, filter_value)
    
    def _parse_operator_string(self, value: str) -> tuple[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Parse operator from string like '>100', '>=100', 'like:john'"""
        # Handle common operator patterns
        operator_patterns = [
            (r'^>=(.+)$', 'gte'),
            (r'^<=(.+)$', 'lte'),
            (r'^!=(.+)$', 'ne'),
            (r'^>(.+)$', 'gt'),
            (r'^<(.+)$', 'lt'),
            (r'^=(.+)$', 'eq'),
            (r'^like:(.+)$', 'like'),
            (r'^in:(.+)$', 'in'),
            (r'^not_in:(.+)$', 'not_in'),
        ]
        
        for pattern, operator in operator_patterns:
            match = re.match(pattern, value, re.IGNORECASE)
            if match:
                filter_value = match.group(1)
                # Handle array values for 'in' operators
                if operator in ('in', 'not_in') and ',' in filter_value:
                    filter_value = [v.strip() for v in filter_value.split(',')]
                return operator, filter_value
        
        # Default to equality
        return 'eq', value
    
    def _apply_static_operator(self, query: SQLQuery, column: Column, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> SQLQuery:
        """Apply static operator"""
        if self.operator == FilterOperator.EQUAL:
            return query.filter(column == value)
        elif self.operator == FilterOperator.NOT_EQUAL:
            return query.filter(column != value)
        elif self.operator == FilterOperator.GREATER_THAN:
            return query.filter(column > value)
        elif self.operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return query.filter(column >= value)
        elif self.operator == FilterOperator.LESS_THAN:
            return query.filter(column < value)
        elif self.operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return query.filter(column <= value)
        elif self.operator == FilterOperator.LIKE:
            return query.filter(column.like(f"%{value}%"))
        elif self.operator == FilterOperator.IN and isinstance(value, list):
            return query.filter(column.in_(value))
        elif self.operator == FilterOperator.NOT_IN and isinstance(value, list):
            return query.filter(~column.in_(value))
        
        return query
    
    def _apply_operator(self, query: SQLQuery, column: Column, operator: str, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> SQLQuery:
        """Apply specific operator to column"""
        if operator in ('eq', '=', 'equal'):
            return query.filter(column == value)
        elif operator in ('ne', '!=', 'not_equal'):
            return query.filter(column != value)
        elif operator in ('gt', '>', 'greater_than'):
            return query.filter(column > value)
        elif operator in ('gte', '>=', 'greater_than_or_equal'):
            return query.filter(column >= value)
        elif operator in ('lt', '<', 'less_than'):
            return query.filter(column < value)
        elif operator in ('lte', '<=', 'less_than_or_equal'):
            return query.filter(column <= value)
        elif operator in ('like', 'ilike'):
            if operator == 'ilike':
                return query.filter(column.ilike(f"%{value}%"))
            else:
                return query.filter(column.like(f"%{value}%"))
        elif operator in ('in',):
            if isinstance(value, list):
                return query.filter(column.in_(value))
            else:
                # Convert single value to list
                return query.filter(column.in_([value]))
        elif operator in ('not_in', 'nin'):
            if isinstance(value, list):
                return query.filter(~column.in_(value))
            else:
                return query.filter(~column.in_([value]))
        elif operator in ('is_null', 'null'):
            return query.filter(column.is_(None))
        elif operator in ('is_not_null', 'not_null'):
            return query.filter(column.isnot(None))
        
        # Default to equality
        return query.filter(column == value)
    
    def _resolve_column_and_query(self, query: SQLQuery, property_name: str) -> tuple[Optional[Column], SQLQuery]:
        """Resolve column and potentially modify query with joins"""
        if '.' in property_name and self.add_relation_constraint:
            parts = property_name.split('.')
            if len(parts) == 2:
                relationship_name, column_name = parts
                model = self._get_model_from_query(query)
                if model and hasattr(model, relationship_name):
                    relationship = getattr(model, relationship_name)
                    if hasattr(relationship.property, 'mapper'):
                        related_model = relationship.property.mapper.class_
                        query = query.join(relationship)
                        if hasattr(related_model, column_name):
                            return getattr(related_model, column_name), query
        else:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name), query
        
        return None, query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions: List[Dict[str, Any]] = query.column_descriptions
                if descriptions and len(descriptions) > 0 and descriptions[0].get('entity'):
                    return cast(type, descriptions[0]['entity'])
            return None
        except Exception:
            return None


class ScopeFilter(FilterInterface):
    """Scope filter that calls model scope methods"""
    
    def __init__(self, scope_name: str) -> None:
        self.scope_name = scope_name
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        # Get the model from query
        model = self._get_model_from_query(query)
        if model is None:
            return query
        
        # Try to find the scope method
        scope_method_name = f"scope_{self.scope_name.lower()}"
        
        if hasattr(model, scope_method_name):
            scope_method = getattr(model, scope_method_name)
            try:
                # Handle different scope method signatures
                if isinstance(value, str) and ',' in value:
                    # Multiple parameters separated by comma
                    params = [v.strip() for v in value.split(',')]
                    return cast(SQLQuery, scope_method(query, *params))
                elif value is not None:
                    # Single parameter
                    return cast(SQLQuery, scope_method(query, value))
                else:
                    # No parameters
                    return cast(SQLQuery, scope_method(query))
            except Exception:
                # If scope method fails, return original query
                pass
        
        # If scope method not found or failed, try alternative naming
        alternative_name = f"scope_{self.scope_name}"
        if hasattr(model, alternative_name):
            try:
                scope_method = getattr(model, alternative_name)
                if value is not None:
                    return cast(SQLQuery, scope_method(query, value))
                else:
                    return cast(SQLQuery, scope_method(query))
            except Exception:
                pass
        
        return query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions: List[Dict[str, Any]] = query.column_descriptions
                if descriptions and len(descriptions) > 0 and descriptions[0].get('entity'):
                    return cast(type, descriptions[0]['entity'])
            return None
        except Exception:
            return None


class CallbackFilter(FilterInterface):
    """Callback-based filter"""
    
    def __init__(self, callback: Callable[[SQLQuery, Union[str, int, float, bool, List[Union[str, int, float, bool]], None], str], SQLQuery]) -> None:
        self.callback = callback
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        return self.callback(query, value, property_name)


class BelongsToFilter(FilterInterface):
    """Belongs-to relationship filter"""
    
    def __init__(self, relationship_path: str) -> None:
        self.relationship_path = relationship_path
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        # Get the model from query
        model = self._get_model_from_query(query)
        if model is None:
            return query
        
        # Handle nested relationships (e.g., "post.author")
        parts = self.relationship_path.split(".")
        
        if len(parts) == 1:
            # Simple belongs-to relationship
            relationship_name = parts[0]
            
            if hasattr(model, relationship_name):
                relationship = getattr(model, relationship_name)
                
                # Use the relationship's foreign key
                if hasattr(relationship.property, 'local_columns'):
                    foreign_key_columns = list(relationship.property.local_columns)
                    if foreign_key_columns:
                        foreign_key_column = foreign_key_columns[0]
                        
                        # Handle multiple values
                        if isinstance(value, list):
                            return query.filter(foreign_key_column.in_(value))
                        else:
                            return query.filter(foreign_key_column == value)
            else:
                # Fallback: try to find foreign key column by convention
                foreign_key_name = f"{relationship_name}_id"
                if hasattr(model, foreign_key_name):
                    foreign_key_column = getattr(model, foreign_key_name)
                    if isinstance(value, list):
                        return query.filter(foreign_key_column.in_(value))
                    else:
                        return query.filter(foreign_key_column == value)
        
        elif len(parts) == 2:
            # Nested belongs-to (e.g., "post.author")
            first_relationship, second_relationship = parts
            
            if hasattr(model, first_relationship):
                first_rel = getattr(model, first_relationship)
                
                if hasattr(first_rel.property, 'mapper'):
                    intermediate_model = first_rel.property.mapper.class_
                    
                    if hasattr(intermediate_model, second_relationship):
                        second_rel = getattr(intermediate_model, second_relationship)
                        
                        # Join both relationships and filter on the final foreign key
                        query = query.join(first_rel).join(second_rel)
                        
                        if hasattr(second_rel.property, 'remote_side'):
                            remote_columns = second_rel.property.remote_side
                            if remote_columns:
                                target_column = list(remote_columns)[0]
                                if isinstance(value, list):
                                    return query.filter(target_column.in_(value))
                                else:
                                    return query.filter(target_column == value)
        
        return query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions: List[Dict[str, Any]] = query.column_descriptions
                if descriptions and len(descriptions) > 0 and descriptions[0].get('entity'):
                    return cast(type, descriptions[0]['entity'])
            return None
        except Exception:
            return None


class TrashedFilter(FilterInterface):
    """Trashed (soft delete) filter with proper model integration"""
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        # Get the model from query
        model = self._get_model_from_query(query)
        if model is None:
            return query
        
        # Look for soft delete column (deleted_at, deleted_on, is_deleted)
        deleted_column = None
        for column_name in ['deleted_at', 'deleted_on', 'is_deleted']:
            if hasattr(model, column_name):
                deleted_column = getattr(model, column_name)
                break
        
        if deleted_column is None:
            # No soft delete column found
            return query
        
        # Handle different value formats
        if isinstance(value, str):
            value = value.lower()
        
        if value in ('only', 'true', '1', True):
            # Only trashed records
            if hasattr(deleted_column.type, 'python_type') and deleted_column.type.python_type == bool:
                # Boolean column (is_deleted)
                return query.filter(deleted_column == True)
            else:
                # DateTime column (deleted_at, deleted_on)
                return query.filter(deleted_column.isnot(None))
        elif value in ('with', 'include'):
            # Include trashed records (no additional filter)
            return query
        else:
            # Default: exclude trashed (only active records)
            if hasattr(deleted_column.type, 'python_type') and deleted_column.type.python_type == bool:
                # Boolean column (is_deleted)
                return query.filter(deleted_column == False)
            else:
                # DateTime column (deleted_at, deleted_on)
                return query.filter(deleted_column.is_(None))
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions: List[Dict[str, Any]] = query.column_descriptions
                if descriptions and len(descriptions) > 0 and descriptions[0].get('entity'):
                    return cast(type, descriptions[0]['entity'])
            return None
        except Exception:
            return None