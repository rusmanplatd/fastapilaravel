from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeEnumCommand(Command):
    """Generate a new enum class."""
    
    signature = "make:enum {name : The name of the enum} {--string : Generate a string-backed enum} {--int : Generate an integer-backed enum}"
    description = "Create a new enum class"
    help = "Generate a new enum class with values and helper methods"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        is_string = self.option("string", False)
        is_int = self.option("int", False)
        
        if not name:
            self.error("Enum name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Enum"):
            name += "Enum"
        
        enum_path = Path(f"app/Enums/{name}.py")
        enum_path.parent.mkdir(parents=True, exist_ok=True)
        
        if enum_path.exists():
            if not self.confirm(f"Enum {name} already exists. Overwrite?"):
                self.info("Enum creation cancelled.")
                return
        
        content = self._generate_enum_content(name, is_string, is_int)
        enum_path.write_text(content)
        
        self.info(f"✅ Enum created: {enum_path}")
        self.comment("Update the enum with your values and add any custom methods")
        self.comment("Import and use: from app.Enums.{name} import {name}")
    
    def _generate_enum_content(self, enum_name: str, is_string: bool = False, is_int: bool = False) -> str:
        """Generate enum content."""
        if is_string:
            return self._generate_string_enum(enum_name)
        elif is_int:
            return self._generate_int_enum(enum_name)
        else:
            return self._generate_auto_enum(enum_name)
    
    def _generate_string_enum(self, enum_name: str) -> str:
        """Generate a string-backed enum."""
        return f'''from __future__ import annotations

from enum import Enum
from typing import List, Optional


class {enum_name}(str, Enum):
    """String-backed enum for type-safe string constants."""
    
    # Define your enum values here
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    CANCELLED = "cancelled"
    
    # Example status enum values:
    # DRAFT = "draft"
    # PUBLISHED = "published" 
    # ARCHIVED = "archived"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all enum values."""
        return [member.value for member in cls]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names."""
        return [member.name for member in cls]
    
    @classmethod
    def choices(cls) -> List[tuple[str, str]]:
        """Get choices for forms (value, label)."""
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]
    
    @classmethod
    def from_string(cls, value: str) -> Optional['{enum_name}']:
        """Create enum from string value."""
        try:
            return cls(value)
        except ValueError:
            return None
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.value
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{self.__class__.__name__}.{self.name}"
    
    @property
    def label(self) -> str:
        """Get human-readable label."""
        return self.name.replace('_', ' ').title()
    
    def is_active(self) -> bool:
        """Check if status is active (example helper method)."""
        return self == self.ACTIVE
    
    def is_final(self) -> bool:
        """Check if status is final (example helper method)."""
        return self in [self.CANCELLED]


# Usage examples:
#
# # Basic usage
# status = {enum_name}.ACTIVE
# print(status)  # "active"
# print(status.label)  # "Active"
#
# # In database models
# class MyModel(BaseModel):
#     status: str = {enum_name}.PENDING.value
#     
#     @property 
#     def status_enum(self) -> {enum_name}:
#         return {enum_name}(self.status)
#
# # Validation
# def validate_status(status: str) -> bool:
#     return status in {enum_name}.values()
#
# # Form choices
# choices = {enum_name}.choices()
# # [('active', 'Active'), ('inactive', 'Inactive'), ...]
'''
    
    def _generate_int_enum(self, enum_name: str) -> str:
        """Generate an integer-backed enum."""
        return f'''from __future__ import annotations

from enum import IntEnum
from typing import List, Optional


class {enum_name}(IntEnum):
    """Integer-backed enum for numeric constants."""
    
    # Define your enum values here
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    
    # Example priority levels:
    # NONE = 0
    # BASIC = 1
    # STANDARD = 2
    # PREMIUM = 3
    # ENTERPRISE = 4
    
    @classmethod
    def values(cls) -> List[int]:
        """Get all enum values."""
        return [member.value for member in cls]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names."""
        return [member.name for member in cls]
    
    @classmethod
    def choices(cls) -> List[tuple[int, str]]:
        """Get choices for forms (value, label)."""
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]
    
    @classmethod
    def from_int(cls, value: int) -> Optional['{enum_name}']:
        """Create enum from integer value."""
        try:
            return cls(value)
        except ValueError:
            return None
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.name.replace('_', ' ').title()
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{self.__class__.__name__}.{self.name}"
    
    @property
    def label(self) -> str:
        """Get human-readable label."""
        return self.name.replace('_', ' ').title()
    
    def is_high_priority(self) -> bool:
        """Check if priority is high (example helper method)."""
        return self.value >= self.HIGH.value
    
    def is_critical(self) -> bool:
        """Check if priority is critical (example helper method)."""
        return self == self.CRITICAL
    
    def compare(self, other: '{enum_name}') -> int:
        """Compare priority levels."""
        return self.value - other.value


# Usage examples:
#
# # Basic usage
# priority = {enum_name}.HIGH
# print(priority)  # "High"
# print(priority.value)  # 3
# print(priority.label)  # "High"
#
# # Comparisons
# if {enum_name}.HIGH > {enum_name}.LOW:
#     print("High priority is greater than low")
#
# # In database models
# class Task(BaseModel):
#     priority: int = {enum_name}.MEDIUM.value
#     
#     @property
#     def priority_enum(self) -> {enum_name}:
#         return {enum_name}(self.priority)
#
# # Sorting
# priorities = [{enum_name}.LOW, {enum_name}.CRITICAL, {enum_name}.MEDIUM]
# sorted_priorities = sorted(priorities)
# # [{enum_name}.LOW, {enum_name}.MEDIUM, {enum_name}.CRITICAL]
'''
    
    def _generate_auto_enum(self, enum_name: str) -> str:
        """Generate an auto-value enum."""
        return f'''from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional


class {enum_name}(Enum):
    """Auto-value enum for type-safe constants."""
    
    # Define your enum values here (auto() assigns unique values)
    OPTION_A = auto()
    OPTION_B = auto()
    OPTION_C = auto()
    OPTION_D = auto()
    
    # Example user types:
    # ADMIN = auto()
    # EDITOR = auto()
    # VIEWER = auto()
    # GUEST = auto()
    
    @classmethod
    def values(cls) -> List[int]:
        """Get all enum values."""
        return [member.value for member in cls]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names."""
        return [member.name for member in cls]
    
    @classmethod
    def choices(cls) -> List[tuple[int, str]]:
        """Get choices for forms (value, label)."""
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]
    
    @classmethod
    def from_value(cls, value: int) -> Optional['{enum_name}']:
        """Create enum from value."""
        for member in cls:
            if member.value == value:
                return member
        return None
    
    @classmethod
    def from_name(cls, name: str) -> Optional['{enum_name}']:
        """Create enum from name."""
        try:
            return cls[name.upper()]
        except KeyError:
            return None
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.name.replace('_', ' ').title()
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{self.__class__.__name__}.{self.name}"
    
    @property
    def label(self) -> str:
        """Get human-readable label."""
        return self.name.replace('_', ' ').title()
    
    @property
    def slug(self) -> str:
        """Get URL-friendly slug."""
        return self.name.lower().replace('_', '-')


# Usage examples:
#
# # Basic usage
# option = {enum_name}.OPTION_A
# print(option)  # "Option A"
# print(option.value)  # 1 (auto-assigned)
# print(option.label)  # "Option A"
# print(option.slug)  # "option-a"
#
# # Create from name
# option = {enum_name}.from_name("OPTION_B")
#
# # In database models  
# class Settings(BaseModel):
#     option: int = {enum_name}.OPTION_A.value
#     
#     @property
#     def option_enum(self) -> {enum_name}:
#         return {enum_name}.from_value(self.option)
#
# # Validation
# def validate_option(value: int) -> bool:
#     return value in {enum_name}.values()
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeEnumCommand)
