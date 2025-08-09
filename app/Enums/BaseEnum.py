from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, StrEnum, IntEnum
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union, ClassVar
import json

E = TypeVar('E', bound='BaseEnum')


class BaseEnum(ABC):
    """
    Base class for Laravel-style enums with enhanced functionality.
    
    Provides common enum operations, serialization, and value object behavior
    similar to Laravel's backed enums and value objects.
    """
    
    def __init__(self, value: Any) -> None:
        self._value = value
    
    @property
    def value(self) -> Any:
        """Get the enum value."""
        return self._value
    
    @property 
    def name(self) -> str:
        """Get the enum name."""
        return self.__class__.__name__
    
    @classmethod
    @abstractmethod
    def cases(cls) -> List['BaseEnum']:
        """Get all enum cases."""
        pass
    
    @classmethod
    @abstractmethod
    def from_value(cls, value: Any) -> 'BaseEnum':
        """Create enum instance from value."""
        pass
    
    @classmethod
    def try_from(cls, value: Any) -> Optional['BaseEnum']:
        """Try to create enum instance from value, return None if invalid."""
        try:
            return cls.from_value(value)
        except (ValueError, KeyError):
            return None
    
    @classmethod
    def values(cls) -> List[Any]:
        """Get all enum values."""
        return [case.value for case in cls.cases()]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names."""
        return [case.name for case in cls.cases()]
    
    def equals(self, other: Any) -> bool:
        """Check if this enum equals another value."""
        if isinstance(other, BaseEnum):
            return self.value == other.value and type(self) == type(other)
        return bool(self.value == other)
    
    def is_one_of(self, *values: Any) -> bool:
        """Check if this enum is one of the given values."""
        return any(self.equals(value) for value in values)
    
    def to_array(self) -> Dict[str, Any]:
        """Convert enum to array representation."""
        return {
            'name': self.name,
            'value': self.value,
            'description': getattr(self, 'description', None),
            'color': getattr(self, 'color', None),
            'icon': getattr(self, 'icon', None)
        }
    
    def to_json(self) -> str:
        """Convert enum to JSON string."""
        return json.dumps(self.to_array())
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"
    
    def __eq__(self, other: Any) -> bool:
        return self.equals(other)
    
    def __hash__(self) -> int:
        return hash((self.__class__, self.value))


class StringEnum(StrEnum):
    """
    String-backed enum similar to Laravel's string backed enums.
    """
    
    @property
    def name(self) -> str:
        """Get the enum name."""
        return super().name
    
    @classmethod
    def cases(cls) -> List['StringEnum']:
        """Get all enum cases."""
        return list(cls.__members__.values())
    
    @classmethod
    def from_value(cls, value: Any) -> 'StringEnum':
        """Create enum instance from value."""
        if isinstance(value, str):
            for member in cls.__members__.values():
                if member.value == value:
                    return member
        raise ValueError(f"Invalid value '{value}' for enum {cls.__name__}")
    
    @classmethod
    def try_from(cls, value: Any) -> Optional['StringEnum']:
        """Try to create enum instance from value, return None if invalid."""
        try:
            return cls.from_value(value)
        except (ValueError, KeyError):
            return None
    
    @classmethod
    def values(cls) -> List[Any]:
        """Get all enum values."""
        return [member.value for member in cls.__members__.values()]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names."""
        return list(cls.__members__.keys())
    
    def equals(self, other: Any) -> bool:
        """Check if this enum equals another value."""
        if isinstance(other, StringEnum):
            return self.value == other.value and type(self) == type(other)
        return bool(self.value == other)
    
    def is_one_of(self, *values: Any) -> bool:
        """Check if this enum is one of the given values."""
        return any(self.equals(value) for value in values)
    
    def to_array(self) -> Dict[str, Any]:
        """Convert enum to array representation."""
        return {
            'name': self.name,
            'value': self.value,
            'description': getattr(self, 'description', None),
            'color': getattr(self, 'color', None),
            'icon': getattr(self, 'icon', None)
        }
    
    def to_json(self) -> str:
        """Convert enum to JSON string."""
        return json.dumps(self.to_array())


class IntegerEnum(IntEnum):
    """
    Integer-backed enum similar to Laravel's integer backed enums.
    """
    
    @property
    def name(self) -> str:
        """Get the enum name."""
        return super().name
    
    @classmethod
    def cases(cls) -> List['IntegerEnum']:
        """Get all enum cases."""
        return list(cls.__members__.values())
    
    @classmethod
    def from_value(cls, value: Any) -> 'IntegerEnum':
        """Create enum instance from value."""
        if isinstance(value, int):
            for member in cls.__members__.values():
                if member.value == value:
                    return member
        raise ValueError(f"Invalid value '{value}' for enum {cls.__name__}")
    
    @classmethod
    def try_from(cls, value: Any) -> Optional['IntegerEnum']:
        """Try to create enum instance from value, return None if invalid."""
        try:
            return cls.from_value(value)
        except (ValueError, KeyError):
            return None
    
    @classmethod
    def values(cls) -> List[Any]:
        """Get all enum values."""
        return [member.value for member in cls.__members__.values()]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names."""
        return list(cls.__members__.keys())
    
    def equals(self, other: Any) -> bool:
        """Check if this enum equals another value."""
        if isinstance(other, IntegerEnum):
            return self.value == other.value and type(self) == type(other)
        return bool(self.value == other)
    
    def is_one_of(self, *values: Any) -> bool:
        """Check if this enum is one of the given values."""
        return any(self.equals(value) for value in values)
    
    def to_array(self) -> Dict[str, Any]:
        """Convert enum to array representation."""
        return {
            'name': self.name,
            'value': self.value,
            'description': getattr(self, 'description', None),
            'color': getattr(self, 'color', None),
            'icon': getattr(self, 'icon', None)
        }
    
    def to_json(self) -> str:
        """Convert enum to JSON string."""
        return json.dumps(self.to_array())


class MetadataEnum(BaseEnum):
    """
    Enum with additional metadata like descriptions, colors, icons.
    Similar to Laravel enums with custom methods.
    """
    
    _registry: ClassVar[Dict[str, 'MetadataEnum']] = {}
    
    def __init__(self, value: Any, description: Optional[str] = None, 
                 color: Optional[str] = None, icon: Optional[str] = None) -> None:
        super().__init__(value)
        self.description = description
        self.color = color
        self.icon = icon
        
        # Register this enum instance
        key = f"{self.__class__.__name__}_{value}"
        MetadataEnum._registry[key] = self
    
    @classmethod
    def cases(cls) -> List['BaseEnum']:
        """Get all enum cases for this class."""
        return [enum for key, enum in MetadataEnum._registry.items() 
                if key.startswith(f"{cls.__name__}_")]
    
    @classmethod
    def from_value(cls, value: Any) -> 'MetadataEnum':
        """Create enum instance from value."""
        for enum_item in cls.cases():
            if isinstance(enum_item, MetadataEnum) and enum_item.value == value:
                return enum_item
        raise ValueError(f"Invalid value '{value}' for enum {cls.__name__}")
    
    def label(self) -> str:
        """Get human-readable label."""
        return self.description or str(self.value).replace('_', ' ').title()
    
    def badge_class(self) -> str:
        """Get CSS class for badge display."""
        if self.color:
            return f"badge-{self.color}"
        return "badge-secondary"
    
    def has_icon(self) -> bool:
        """Check if enum has an icon."""
        return self.icon is not None
    
    def icon_html(self) -> str:
        """Get HTML for icon display."""
        if self.icon:
            return f'<i class="{self.icon}"></i>'
        return ""


class SelectableEnum(MetadataEnum):
    """
    Enum designed for form selects and dropdowns.
    Provides Laravel-like select options functionality.
    """
    
    @classmethod
    def options(cls) -> Dict[Any, str]:
        """Get options for form selects."""
        return {
            enum_item.value: enum_item.label() 
            for enum_item in cls.cases() 
            if isinstance(enum_item, MetadataEnum)
        }
    
    @classmethod
    def options_with_colors(cls) -> Dict[Any, Dict[str, str]]:
        """Get options with additional metadata."""
        return {
            enum_item.value: {
                'label': enum_item.label(),
                'color': enum_item.color or 'secondary',
                'icon': enum_item.icon or '',
                'description': enum_item.description or ''
            }
            for enum_item in cls.cases()
            if isinstance(enum_item, MetadataEnum)
        }
    
    @classmethod
    def grouped_options(cls, group_key: str = 'category') -> Dict[str, Dict[Any, str]]:
        """Get options grouped by a metadata key."""
        groups: Dict[str, Dict[Any, str]] = {}
        
        for enum_item in cls.cases():
            if isinstance(enum_item, MetadataEnum):
                group = getattr(enum_item, group_key, 'Other')
                if group not in groups:
                    groups[group] = {}
                groups[group][enum_item.value] = enum_item.label()
        
        return groups


class StatusEnum(MetadataEnum):
    """
    Common status enum for models and entities.
    """
    
    # Define status instances
    DRAFT: Optional['StatusEnum'] = None
    PENDING: Optional['StatusEnum'] = None  
    ACTIVE: Optional['StatusEnum'] = None
    INACTIVE: Optional['StatusEnum'] = None
    SUSPENDED: Optional['StatusEnum'] = None
    ARCHIVED: Optional['StatusEnum'] = None
    DELETED: Optional['StatusEnum'] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.DRAFT is None:
            cls.DRAFT = cls('draft', 'Draft', 'secondary', 'fas fa-edit')
            cls.PENDING = cls('pending', 'Pending Review', 'warning', 'fas fa-clock')
            cls.ACTIVE = cls('active', 'Active', 'success', 'fas fa-check-circle')
            cls.INACTIVE = cls('inactive', 'Inactive', 'secondary', 'fas fa-pause-circle')
            cls.SUSPENDED = cls('suspended', 'Suspended', 'danger', 'fas fa-ban')
            cls.ARCHIVED = cls('archived', 'Archived', 'info', 'fas fa-archive')
            cls.DELETED = cls('deleted', 'Deleted', 'dark', 'fas fa-trash')
    
    @classmethod
    def cases(cls) -> List['BaseEnum']:
        cls._initialize_cases()
        cases_list: List['BaseEnum'] = super().cases()
        return cases_list
    
    def is_active(self) -> bool:
        """Check if status is active."""
        return bool(self.value == 'active')
    
    def is_inactive(self) -> bool:
        """Check if status is inactive or disabled."""
        return self.value in ['inactive', 'suspended', 'deleted']
    
    def is_pending(self) -> bool:
        """Check if status is pending."""
        return self.value in ['draft', 'pending']
    
    def can_activate(self) -> bool:
        """Check if status can be activated."""
        return self.value in ['draft', 'pending', 'inactive']
    
    def can_deactivate(self) -> bool:
        """Check if status can be deactivated."""
        return bool(self.value == 'active')


class PriorityEnum(SelectableEnum):
    """
    Priority enum for tasks, tickets, etc.
    """
    
    LOW: Optional['PriorityEnum'] = None
    NORMAL: Optional['PriorityEnum'] = None
    HIGH: Optional['PriorityEnum'] = None
    URGENT: Optional['PriorityEnum'] = None
    CRITICAL: Optional['PriorityEnum'] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.LOW is None:
            cls.LOW = cls(1, 'Low Priority', 'success', 'fas fa-arrow-down')
            cls.NORMAL = cls(2, 'Normal Priority', 'info', 'fas fa-minus')
            cls.HIGH = cls(3, 'High Priority', 'warning', 'fas fa-arrow-up')
            cls.URGENT = cls(4, 'Urgent Priority', 'danger', 'fas fa-exclamation')
            cls.CRITICAL = cls(5, 'Critical Priority', 'dark', 'fas fa-exclamation-triangle')
    
    @classmethod
    def cases(cls) -> List['BaseEnum']:
        cls._initialize_cases()
        cases_list: List['BaseEnum'] = super().cases()
        return cases_list
    
    def sort_order(self) -> int:
        """Get sort order (higher values = higher priority)."""
        return int(self.value)
    
    def is_high_priority(self) -> bool:
        """Check if this is high priority or above."""
        return bool(self.value >= 3)
    
    def is_urgent(self) -> bool:
        """Check if this is urgent or critical."""
        return bool(self.value >= 4)


class UserTypeEnum(StringEnum):
    """
    User type enum using string values.
    """
    
    ADMIN = 'admin'
    MODERATOR = 'moderator'  
    USER = 'user'
    GUEST = 'guest'
    
    def permissions_level(self) -> int:
        """Get permissions level (higher = more permissions)."""
        levels = {
            'guest': 0,
            'user': 1,
            'moderator': 2,
            'admin': 3
        }
        return levels.get(self.value, 0)
    
    def can_moderate(self) -> bool:
        """Check if user type can moderate."""
        return self.value in ['moderator', 'admin']
    
    def is_admin(self) -> bool:
        """Check if user type is admin."""
        return self.value == 'admin'