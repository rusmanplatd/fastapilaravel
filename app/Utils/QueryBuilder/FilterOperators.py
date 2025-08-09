from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, Set
from typing_extensions import TypeAlias

# Define proper type aliases for strict typing
FilterValue: TypeAlias = Union[str, int, float, bool, None]
FilterValueList: TypeAlias = List[Union[str, int, float, bool, None]]
FilterValueDict: TypeAlias = Dict[str, FilterValue]
FilterValueType: TypeAlias = Union[FilterValue, FilterValueList, FilterValueDict]
import re
from dataclasses import dataclass


@dataclass
class OperatorConfig:
    """Configuration for filter operators"""
    requires_value: bool = True
    supports_multiple_values: bool = False
    is_text_operator: bool = False
    is_date_operator: bool = False
    is_json_operator: bool = False
    is_relationship_operator: bool = False
    is_geographic_operator: bool = False
    is_numeric_operator: bool = False
    supports_negation: bool = True
    case_sensitive: bool = True
    aliases: Optional[List[str]] = None
    sql_template: Optional[str] = None
    validation_pattern: Optional[str] = None
    
    def __post_init__(self) -> None:
        if self.aliases is None:
            self.aliases = []


class FilterOperator(Enum):
    """Enhanced enumeration of filter operators for QueryBuilder with extensive capabilities"""
    
    # Basic comparison operators
    EQUAL = "="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    
    # Text search operators
    LIKE = "LIKE"
    ILIKE = "ILIKE"  # Case-insensitive LIKE
    NOT_LIKE = "NOT LIKE"
    NOT_ILIKE = "NOT ILIKE"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    REGEX = "REGEX"
    NOT_REGEX = "NOT_REGEX"
    SOUNDEX = "SOUNDEX"
    
    # Array and collection operations
    IN = "IN"
    NOT_IN = "NOT IN"
    ANY = "ANY"
    ALL = "ALL"
    OVERLAP = "OVERLAP"
    
    # Null and existence checks
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    IS_EMPTY = "IS_EMPTY"
    IS_NOT_EMPTY = "IS_NOT_EMPTY"
    
    # Range operations
    BETWEEN = "BETWEEN"
    NOT_BETWEEN = "NOT BETWEEN"
    
    # Date/time specific operators
    DATE_EQUAL = "DATE_EQUAL"
    DATE_NOT_EQUAL = "DATE_NOT_EQUAL"
    DATE_GREATER_THAN = "DATE_GT"
    DATE_LESS_THAN = "DATE_LT"
    DATE_GREATER_THAN_OR_EQUAL = "DATE_GTE"
    DATE_LESS_THAN_OR_EQUAL = "DATE_LTE"
    DATE_BETWEEN = "DATE_BETWEEN"
    TIME_EQUAL = "TIME_EQUAL"
    TIME_BETWEEN = "TIME_BETWEEN"
    YEAR_EQUAL = "YEAR_EQUAL"
    MONTH_EQUAL = "MONTH_EQUAL"
    DAY_EQUAL = "DAY_EQUAL"
    WEEKDAY_EQUAL = "WEEKDAY_EQUAL"
    QUARTER_EQUAL = "QUARTER_EQUAL"
    
    # JSON operations (PostgreSQL/MySQL specific)
    JSON_CONTAINS = "JSON_CONTAINS"
    JSON_CONTAINED_BY = "JSON_CONTAINED_BY"
    JSON_HAS_KEY = "JSON_HAS_KEY"
    JSON_HAS_ANY_KEY = "JSON_HAS_ANY_KEY"
    JSON_HAS_ALL_KEYS = "JSON_HAS_ALL_KEYS"
    JSON_PATH_EXISTS = "JSON_PATH_EXISTS"
    JSON_PATH_MATCH = "JSON_PATH_MATCH"
    JSON_EXTRACT = "JSON_EXTRACT"
    JSON_LENGTH = "JSON_LENGTH"
    JSON_TYPE = "JSON_TYPE"
    
    # Full-text search operators
    MATCH = "MATCH"
    MATCH_BOOLEAN = "MATCH_BOOLEAN"
    MATCH_NATURAL = "MATCH_NATURAL"
    MATCH_QUERY_EXPANSION = "MATCH_QUERY_EXPANSION"
    
    # Fuzzy search operators
    FUZZY = "FUZZY"
    LEVENSHTEIN = "LEVENSHTEIN"
    SIMILARITY = "SIMILARITY"
    
    # Numeric operators
    MODULO = "MODULO"
    POWER = "POWER"
    ROUND = "ROUND"
    CEIL = "CEIL"
    FLOOR = "FLOOR"
    ABS = "ABS"
    
    # Relationship operations
    HAS = "HAS"
    DOESNT_HAVE = "DOESNT_HAVE"
    WHERE_HAS = "WHERE_HAS"
    WHERE_DOESNT_HAVE = "WHERE_DOESNT_HAVE"
    WITH_COUNT = "WITH_COUNT"
    HAS_COUNT = "HAS_COUNT"
    
    # Geographic operations (PostGIS)
    ST_CONTAINS = "ST_CONTAINS"
    ST_WITHIN = "ST_WITHIN"
    ST_INTERSECTS = "ST_INTERSECTS"
    ST_TOUCHES = "ST_TOUCHES"
    ST_CROSSES = "ST_CROSSES"
    ST_OVERLAPS = "ST_OVERLAPS"
    ST_DISJOINT = "ST_DISJOINT"
    ST_DISTANCE = "ST_DISTANCE"
    ST_DISTANCE_SPHERE = "ST_DISTANCE_SPHERE"
    ST_DWITHIN = "ST_DWITHIN"
    ST_BUFFER = "ST_BUFFER"
    
    # Special operators
    DYNAMIC = "DYNAMIC"  # Determined at runtime
    CUSTOM = "CUSTOM"   # Custom callback function
    RAW = "RAW"         # Raw SQL
    SCOPE = "SCOPE"     # Model scope method
    
    # Aggregate operators
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    GROUP_CONCAT = "GROUP_CONCAT"
    
    # Window function operators
    ROW_NUMBER = "ROW_NUMBER"
    RANK = "RANK"
    DENSE_RANK = "DENSE_RANK"
    LAG = "LAG"
    LEAD = "LEAD"
    
    def get_config(self) -> OperatorConfig:
        """Get configuration for this operator"""
        configs: Dict[FilterOperator, OperatorConfig] = {
            FilterOperator.EQUAL: OperatorConfig(
                aliases=['eq', 'equal', '=='],
                sql_template="{column} = {value}",
                is_numeric_operator=True
            ),
            FilterOperator.NOT_EQUAL: OperatorConfig(
                aliases=['ne', 'not_equal', '!=', '<>'],
                sql_template="{column} != {value}",
                is_numeric_operator=True
            ),
            FilterOperator.GREATER_THAN: OperatorConfig(
                aliases=['gt', 'greater_than'],
                sql_template="{column} > {value}",
                is_numeric_operator=True
            ),
            FilterOperator.GREATER_THAN_OR_EQUAL: OperatorConfig(
                aliases=['gte', 'greater_than_or_equal', '>='],
                sql_template="{column} >= {value}",
                is_numeric_operator=True
            ),
            FilterOperator.LESS_THAN: OperatorConfig(
                aliases=['lt', 'less_than'],
                sql_template="{column} < {value}",
                is_numeric_operator=True
            ),
            FilterOperator.LESS_THAN_OR_EQUAL: OperatorConfig(
                aliases=['lte', 'less_than_or_equal', '<='],
                sql_template="{column} <= {value}",
                is_numeric_operator=True
            ),
            FilterOperator.LIKE: OperatorConfig(
                is_text_operator=True,
                aliases=['like'],
                sql_template="{column} LIKE {value}"
            ),
            FilterOperator.ILIKE: OperatorConfig(
                is_text_operator=True,
                case_sensitive=False,
                aliases=['ilike'],
                sql_template="{column} ILIKE {value}"
            ),
            FilterOperator.STARTS_WITH: OperatorConfig(
                is_text_operator=True,
                aliases=['starts_with', 'begins_with'],
                sql_template="{column} LIKE {value}%"
            ),
            FilterOperator.ENDS_WITH: OperatorConfig(
                is_text_operator=True,
                aliases=['ends_with'],
                sql_template="{column} LIKE %{value}"
            ),
            FilterOperator.CONTAINS: OperatorConfig(
                is_text_operator=True,
                aliases=['contains'],
                sql_template="{column} LIKE %{value}%"
            ),
            FilterOperator.IN: OperatorConfig(
                supports_multiple_values=True,
                aliases=['in'],
                sql_template="{column} IN ({value})"
            ),
            FilterOperator.NOT_IN: OperatorConfig(
                supports_multiple_values=True,
                aliases=['not_in', 'nin'],
                sql_template="{column} NOT IN ({value})"
            ),
            FilterOperator.IS_NULL: OperatorConfig(
                requires_value=False,
                aliases=['is_null', 'null'],
                sql_template="{column} IS NULL"
            ),
            FilterOperator.IS_NOT_NULL: OperatorConfig(
                requires_value=False,
                aliases=['is_not_null', 'not_null'],
                sql_template="{column} IS NOT NULL"
            ),
            FilterOperator.BETWEEN: OperatorConfig(
                supports_multiple_values=True,
                aliases=['between'],
                sql_template="{column} BETWEEN {value1} AND {value2}",
                validation_pattern=r'^.+,.+$'
            ),
            FilterOperator.JSON_CONTAINS: OperatorConfig(
                is_json_operator=True,
                aliases=['json_contains'],
                sql_template="JSON_CONTAINS({column}, {value})"
            ),
            FilterOperator.JSON_HAS_KEY: OperatorConfig(
                is_json_operator=True,
                aliases=['json_has_key'],
                sql_template="JSON_EXTRACT({column}, '$.{value}') IS NOT NULL"
            ),
            FilterOperator.REGEX: OperatorConfig(
                is_text_operator=True,
                aliases=['regex', 'regexp'],
                sql_template="{column} REGEXP {value}"
            ),
            FilterOperator.DATE_EQUAL: OperatorConfig(
                is_date_operator=True,
                aliases=['date_equal', 'date_eq'],
                sql_template="DATE({column}) = DATE({value})"
            ),
            FilterOperator.HAS: OperatorConfig(
                is_relationship_operator=True,
                aliases=['has'],
                requires_value=False
            ),
            FilterOperator.ST_CONTAINS: OperatorConfig(
                is_geographic_operator=True,
                aliases=['st_contains'],
                sql_template="ST_Contains({column}, {value})"
            ),
            FilterOperator.DYNAMIC: OperatorConfig(
                aliases=['dynamic']
            )
        }
        
        return configs.get(self, OperatorConfig())
    
    @classmethod
    def from_string(cls, operator_str: str) -> 'FilterOperator':
        """Enhanced string to FilterOperator conversion with alias support"""
        operator_str = operator_str.lower().strip()
        
        # Direct mapping
        for operator in cls:
            config = operator.get_config()
            if operator_str == operator.value.lower() or (config.aliases and operator_str in config.aliases):
                return operator
        
        # Fallback to exact match patterns
        operator_patterns = {
            r'^(=|eq|equal|==)$': cls.EQUAL,
            r'^(!=|ne|not_equal|<>)$': cls.NOT_EQUAL,
            r'^(>|gt|greater_than)$': cls.GREATER_THAN,
            r'^(>=|gte|greater_than_or_equal)$': cls.GREATER_THAN_OR_EQUAL,
            r'^(<|lt|less_than)$': cls.LESS_THAN,
            r'^(<=|lte|less_than_or_equal)$': cls.LESS_THAN_OR_EQUAL,
            r'^(like)$': cls.LIKE,
            r'^(ilike)$': cls.ILIKE,
            r'^(starts_with|begins_with)$': cls.STARTS_WITH,
            r'^(ends_with)$': cls.ENDS_WITH,
            r'^(contains)$': cls.CONTAINS,
            r'^(in)$': cls.IN,
            r'^(not_in|nin)$': cls.NOT_IN,
            r'^(is_null|null)$': cls.IS_NULL,
            r'^(is_not_null|not_null)$': cls.IS_NOT_NULL,
            r'^(between)$': cls.BETWEEN,
            r'^(regex|regexp)$': cls.REGEX,
            r'^(fuzzy)$': cls.FUZZY,
            r'^(match)$': cls.MATCH,
            r'^(has)$': cls.HAS,
            r'^(doesnt_have|doesnt-have)$': cls.DOESNT_HAVE,
        }
        
        for pattern, operator in operator_patterns.items():
            if re.match(pattern, operator_str, re.IGNORECASE):
                return operator
        
        # Default to EQUAL if no match found
        return cls.EQUAL
    
    @classmethod
    def get_operators_by_type(cls, operator_type: str) -> List['FilterOperator']:
        """Get operators by type (text, numeric, date, etc.)"""
        operators = []
        
        for operator in cls:
            config = operator.get_config()
            
            if operator_type == 'text' and config.is_text_operator:
                operators.append(operator)
            elif operator_type == 'numeric' and config.is_numeric_operator:
                operators.append(operator)
            elif operator_type == 'date' and config.is_date_operator:
                operators.append(operator)
            elif operator_type == 'json' and config.is_json_operator:
                operators.append(operator)
            elif operator_type == 'relationship' and config.is_relationship_operator:
                operators.append(operator)
            elif operator_type == 'geographic' and config.is_geographic_operator:
                operators.append(operator)
        
        return operators
    
    @classmethod
    def suggest_operators(cls, value_type: str, value: Optional[FilterValueType] = None) -> List['FilterOperator']:
        """Suggest appropriate operators based on value type and content"""
        suggestions = []
        
        if value_type in ('str', 'string', 'text'):
            suggestions.extend([
                cls.EQUAL, cls.NOT_EQUAL, cls.LIKE, cls.ILIKE,
                cls.STARTS_WITH, cls.ENDS_WITH, cls.CONTAINS,
                cls.IN, cls.NOT_IN, cls.IS_NULL, cls.IS_NOT_NULL
            ])
            
            if value and isinstance(value, str):
                if ',' in value:
                    suggestions.extend([cls.IN, cls.NOT_IN])
                if any(char in value for char in ['%', '_']):
                    suggestions.extend([cls.LIKE, cls.ILIKE])
                    
        elif value_type in ('int', 'float', 'number', 'numeric'):
            suggestions.extend([
                cls.EQUAL, cls.NOT_EQUAL, cls.GREATER_THAN, cls.GREATER_THAN_OR_EQUAL,
                cls.LESS_THAN, cls.LESS_THAN_OR_EQUAL, cls.BETWEEN, cls.NOT_BETWEEN,
                cls.IN, cls.NOT_IN, cls.IS_NULL, cls.IS_NOT_NULL
            ])
            
        elif value_type in ('bool', 'boolean'):
            suggestions.extend([cls.EQUAL, cls.NOT_EQUAL, cls.IS_NULL, cls.IS_NOT_NULL])
            
        elif value_type in ('date', 'datetime', 'timestamp'):
            suggestions.extend([
                cls.EQUAL, cls.NOT_EQUAL, cls.GREATER_THAN, cls.LESS_THAN,
                cls.BETWEEN, cls.DATE_EQUAL, cls.DATE_GREATER_THAN, cls.DATE_LESS_THAN,
                cls.YEAR_EQUAL, cls.MONTH_EQUAL, cls.DAY_EQUAL, cls.IS_NULL, cls.IS_NOT_NULL
            ])
            
        elif value_type in ('list', 'array'):
            suggestions.extend([cls.IN, cls.NOT_IN, cls.ANY, cls.ALL, cls.OVERLAP])
            
        elif value_type in ('dict', 'json', 'object'):
            suggestions.extend([
                cls.JSON_CONTAINS, cls.JSON_HAS_KEY, cls.JSON_HAS_ANY_KEY,
                cls.JSON_HAS_ALL_KEYS, cls.JSON_PATH_EXISTS, cls.EQUAL, cls.NOT_EQUAL
            ])
        
        return suggestions
    
    def requires_value(self) -> bool:
        """Check if operator requires a value"""
        return self.get_config().requires_value
    
    def supports_multiple_values(self) -> bool:
        """Check if operator supports multiple values"""
        return self.get_config().supports_multiple_values
    
    def is_text_operator(self) -> bool:
        """Check if operator is for text operations"""
        return self.get_config().is_text_operator
    
    def is_date_operator(self) -> bool:
        """Check if operator is for date operations"""
        return self.get_config().is_date_operator
    
    def is_json_operator(self) -> bool:
        """Check if operator is for JSON operations"""
        return self.get_config().is_json_operator
    
    def is_relationship_operator(self) -> bool:
        """Check if operator is for relationship operations"""
        return self.get_config().is_relationship_operator
    
    def is_geographic_operator(self) -> bool:
        """Check if operator is for geographic operations"""
        return self.get_config().is_geographic_operator
    
    def is_numeric_operator(self) -> bool:
        """Check if operator is for numeric operations"""
        return self.get_config().is_numeric_operator
    
    def get_aliases(self) -> List[str]:
        """Get all aliases for this operator"""
        return self.get_config().aliases or []
    
    def get_sql_template(self) -> Optional[str]:
        """Get SQL template for this operator"""
        return self.get_config().sql_template
    
    def validate_value(self, value: FilterValueType) -> bool:
        """Validate value against operator requirements"""
        config = self.get_config()
        
        if not config.requires_value and value is not None:
            return False
            
        if config.requires_value and value is None:
            return False
            
        if config.validation_pattern and isinstance(value, str):
            return bool(re.match(config.validation_pattern, value))
            
        return True
    
    def format_value(self, value: FilterValueType) -> FilterValueType:
        """Format value according to operator requirements"""
        config = self.get_config()
        
        if self == FilterOperator.BETWEEN and isinstance(value, str) and ',' in value:
            parts = [part.strip() for part in value.split(',', 1)]
            if len(parts) == 2:
                return parts  # type: ignore[return-value]
            return value
            
        if config.supports_multiple_values and isinstance(value, str) and ',' in value:
            return [part.strip() for part in value.split(',')]
            
        if config.is_text_operator and not config.case_sensitive and isinstance(value, str):
            return value.lower()
            
        return value