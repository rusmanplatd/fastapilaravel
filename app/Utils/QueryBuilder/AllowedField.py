from __future__ import annotations

from typing import Optional, List, Dict, Any, Union, cast
from abc import ABC, abstractmethod
from sqlalchemy.orm import Query
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    SQLQuery = Query[Any]
else:
    SQLQuery = Query
from sqlalchemy import Column
from typing import Any as ColumnAny


class AllowedField:
    """
    Represents an allowed field for QueryBuilder field selection
    Inspired by Spatie Laravel Query Builder
    """
    
    def __init__(
        self,
        name: str,
        internal_name: Optional[str] = None,
        table_name: Optional[str] = None
    ) -> None:
        self.name = name
        self.internal_name = internal_name or name
        self.table_name = table_name
    
    @classmethod
    def field(
        cls, 
        name: str, 
        internal_name: Optional[str] = None,
        table_name: Optional[str] = None
    ) -> AllowedField:
        """Create field selection"""
        return cls(name, internal_name, table_name)
    
    def get_qualified_name(self) -> str:
        """Get fully qualified field name"""
        if self.table_name:
            return f"{self.table_name}.{self.internal_name}"
        return self.internal_name
    
    def matches_request(self, table_name: str, field_name: str) -> bool:
        """Check if this field matches a requested field"""
        # Check if table matches (if specified)
        if self.table_name and self.table_name != table_name:
            return False
        
        # Check if field name matches
        return self.name == field_name or self.internal_name == field_name


class FieldSelector:
    """
    Handles field selection for QueryBuilder
    """
    
    def __init__(self, model_class: type, table_name: Optional[str] = None) -> None:
        self.model_class = model_class
        self.table_name = table_name or getattr(model_class, '__tablename__', None)
        self.selected_fields: List[str] = []
        self.relationship_fields: Dict[str, List[str]] = {}
    
    def select_fields(self, query: SQLQuery, allowed_fields: List[AllowedField], requested_fields: Dict[str, List[str]]) -> SQLQuery:
        """Apply field selection to query"""
        
        # Handle main model fields
        if self.table_name in requested_fields:
            main_fields = requested_fields[self.table_name]
            validated_fields = self._validate_fields(main_fields, allowed_fields, self.table_name)
            
            if validated_fields:
                # Select only the requested fields
                columns = []
                for field_name in validated_fields:
                    column = self._get_column_for_field(field_name, allowed_fields)
                    if column:
                        columns.append(column)
                
                if columns:
                    # Type ignore for SQLAlchemy overload issue
                    query = query.with_entities(*columns)  # type: ignore[call-overload]
        
        # Handle relationship fields
        for table_name, fields in requested_fields.items():
            if table_name != self.table_name:
                # This is a relationship field selection
                validated_fields = self._validate_fields(fields, allowed_fields, table_name)
                if validated_fields:
                    self.relationship_fields[table_name] = validated_fields
        
        return query
    
    def _validate_fields(self, requested_fields: List[str], allowed_fields: List[AllowedField], table_name: str) -> List[str]:
        """Validate that requested fields are allowed"""
        validated = []
        
        for field_name in requested_fields:
            # Check if field is allowed
            is_allowed = False
            actual_field_name = field_name
            
            for allowed_field in allowed_fields:
                if allowed_field.matches_request(table_name, field_name):
                    is_allowed = True
                    actual_field_name = allowed_field.internal_name
                    break
            
            if is_allowed:
                validated.append(actual_field_name)
        
        return validated
    
    def _get_column_for_field(self, field_name: str, allowed_fields: List[AllowedField]) -> Optional[Column]:
        """Get SQLAlchemy column for field name"""
        # Find the allowed field configuration
        for allowed_field in allowed_fields:
            if allowed_field.internal_name == field_name:
                # Get the column from the model
                column = getattr(self.model_class, field_name, None)
                if column is not None:
                    return cast(Column, column)
                break
        
        # Fallback: try to get column directly from model
        column = getattr(self.model_class, field_name, None)
        return cast(Column, column) if column is not None else None
    
    def get_selected_fields(self) -> List[str]:
        """Get list of selected fields"""
        return self.selected_fields
    
    def get_relationship_fields(self) -> Dict[str, List[str]]:
        """Get relationship field selections"""
        return self.relationship_fields
    
    def has_field_selection(self) -> bool:
        """Check if any fields are selected"""
        return bool(self.selected_fields or self.relationship_fields)


class FieldParser:
    """
    Parses and handles field selection requests
    """
    
    @staticmethod
    def parse_field_name(field_name: str) -> tuple[Optional[str], str]:
        """Parse field name to extract table and field components"""
        # Handle relationship field syntax (e.g., "users.name", "posts.title")
        if "." in field_name:
            parts = field_name.split(".", 1)
            return parts[0], parts[1]
        
        return None, field_name
    
    @staticmethod
    def normalize_table_name(table_name: str, convert_to_snake_case: bool = True) -> str:
        """Normalize table name based on configuration"""
        if convert_to_snake_case:
            # Convert camelCase to snake_case
            import re
            return re.sub(r'(?<!^)(?=[A-Z])', '_', table_name).lower()
        
        return table_name
    
    @staticmethod
    def convert_field_names_to_snake_case(field_names: List[str]) -> List[str]:
        """Convert field names to snake_case if needed"""
        import re
        converted = []
        
        for field_name in field_names:
            # Convert camelCase to snake_case
            snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', field_name).lower()
            converted.append(snake_case)
        
        return converted
    
    @staticmethod
    def validate_field_request(
        table_name: str, 
        field_names: List[str], 
        allowed_fields: List[AllowedField]
    ) -> tuple[bool, List[str], List[str]]:
        """
        Validate field request
        Returns: (is_valid, valid_fields, invalid_fields)
        """
        valid_fields = []
        invalid_fields = []
        
        for field_name in field_names:
            is_valid = False
            
            for allowed_field in allowed_fields:
                if allowed_field.matches_request(table_name, field_name):
                    is_valid = True
                    valid_fields.append(allowed_field.internal_name)
                    break
            
            if not is_valid:
                invalid_fields.append(field_name)
        
        return len(invalid_fields) == 0, valid_fields, invalid_fields


class SparseFieldset:
    """
    Implements sparse fieldsets functionality
    Based on JSON API specification
    """
    
    def __init__(self) -> None:
        self.fieldsets: Dict[str, List[str]] = {}
    
    def add_fieldset(self, resource_type: str, fields: List[str]) -> None:
        """Add fieldset for resource type"""
        self.fieldsets[resource_type] = fields
    
    def get_fieldset(self, resource_type: str) -> Optional[List[str]]:
        """Get fieldset for resource type"""
        return self.fieldsets.get(resource_type)
    
    def has_fieldset(self, resource_type: str) -> bool:
        """Check if fieldset exists for resource type"""
        return resource_type in self.fieldsets
    
    def apply_to_query(self, query: SQLQuery, model_class: type, resource_type: str) -> SQLQuery:
        """Apply fieldset to query"""
        if not self.has_fieldset(resource_type):
            return query
        
        fields = self.get_fieldset(resource_type)
        if not fields:
            return query
        
        # Get columns for the specified fields
        columns = []
        for field_name in fields:
            column = getattr(model_class, field_name, None)
            if column is not None:
                columns.append(column)
        
        if columns:
            # Type ignore for SQLAlchemy overload issue
            return query.with_entities(*columns)  # type: ignore[no-any-return]
        
        return query
    
    def get_all_fieldsets(self) -> Dict[str, List[str]]:
        """Get all fieldsets"""
        return self.fieldsets.copy()