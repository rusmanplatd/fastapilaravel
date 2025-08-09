from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeDTOCommand(Command):
    """Generate a new Data Transfer Object (DTO) class."""
    
    signature = "make:dto {name : The name of the DTO} {--immutable : Create an immutable DTO} {--validation : Add validation to the DTO}"
    description = "Create a new Data Transfer Object (DTO) class"
    help = "Generate a new DTO class for structured data transfer between application layers"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        immutable = self.option("immutable", False)
        validation = self.option("validation", False)
        
        if not name:
            self.error("DTO name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("DTO"):
            name += "DTO"
        
        dto_path = Path(f"app/DTOs/{name}.py")
        dto_path.parent.mkdir(parents=True, exist_ok=True)
        
        if dto_path.exists():
            if not self.confirm(f"DTO {name} already exists. Overwrite?"):
                self.info("DTO creation cancelled.")
                return
        
        content = self._generate_dto_content(name, immutable, validation)
        dto_path.write_text(content)
        
        self.info(f"✅ DTO created: {dto_path}")
        self.comment("Update the DTO with your data fields and methods")
        
        if immutable:
            self.comment("DTO created as immutable (frozen dataclass)")
        if validation:
            self.comment("DTO includes Pydantic validation")
    
    def _generate_dto_content(self, dto_name: str, immutable: bool = False, validation: bool = False) -> str:
        """Generate DTO content."""
        if validation:
            return self._generate_pydantic_dto(dto_name, immutable)
        else:
            return self._generate_dataclass_dto(dto_name, immutable)
    
    def _generate_pydantic_dto(self, dto_name: str, immutable: bool = False) -> str:
        """Generate a Pydantic-based DTO."""
        config_class = ""
        if immutable:
            config_class = '''
    class Config:
        """Pydantic configuration."""
        frozen = True  # Makes the DTO immutable
        validate_assignment = True
        use_enum_values = True'''
        
        return f'''from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator


class {dto_name}(BaseModel):
    """Data Transfer Object for structured data transfer."""
    {config_class}
    
    # Define your DTO fields here
    # Example fields:
    # id: Optional[int] = Field(None, description="Unique identifier")
    # name: str = Field(..., min_length=1, max_length=100, description="Name field")
    # email: Optional[str] = Field(None, regex=r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$', description="Email address")
    # age: Optional[int] = Field(None, ge=0, le=150, description="Age in years")
    # is_active: bool = Field(True, description="Active status")
    # created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    # metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('name', pre=True)
    def validate_name(cls, v: Any) -> str:
        """Validate and clean name field."""
        if isinstance(v, str):
            return v.strip().title()
        return str(v) if v is not None else ""
    
    @validator('email', pre=True)
    def validate_email(cls, v: Any) -> Optional[str]:
        """Validate email field."""
        if v is None or v == "":
            return None
        
        email = str(v).lower().strip()
        if '@' not in email:
            raise ValueError('Invalid email format')
        
        return email
    
    @root_validator
    def validate_dto(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Perform cross-field validation."""
        # Example cross-field validation
        # if values.get('is_active') and not values.get('email'):
        #     raise ValueError('Active users must have an email address')
        
        return values
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return self.dict(exclude_none=True)
    
    def to_json(self) -> str:
        """Convert DTO to JSON string."""
        return self.json(exclude_none=True, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> '{dto_name}':
        """Create DTO instance from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_model(cls, model: Any) -> '{dto_name}':
        """Create DTO instance from model."""
        if hasattr(model, '__dict__'):
            model_data = {{k: v for k, v in model.__dict__.items() if not k.startswith('_')}}
            return cls(**model_data)
        else:
            raise ValueError("Model must have __dict__ attribute")
    
    def update(self, **kwargs: Any) -> '{dto_name}':
        """Create a new DTO instance with updated values."""
        {"# Note: For immutable DTOs, this creates a new instance" if immutable else ""}
        update_data = self.dict()
        update_data.update(kwargs)
        return self.__class__(**update_data)
    
    def merge(self, other: '{dto_name}') -> '{dto_name}':
        """Merge with another DTO instance."""
        merged_data = self.dict()
        merged_data.update(other.dict(exclude_none=True))
        return self.__class__(**merged_data)
    
    def is_empty(self) -> bool:
        """Check if DTO contains any meaningful data."""
        data = self.dict(exclude_none=True)
        return len(data) == 0
    
    def has_field(self, field_name: str) -> bool:
        """Check if DTO has a specific field."""
        return hasattr(self, field_name)
    
    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get field value with default."""
        return getattr(self, field_name, default)
    
    def get_changed_fields(self, other: '{dto_name}') -> Dict[str, tuple[Any, Any]]:
        """Get fields that are different between two DTOs."""
        changes = {{}}
        
        self_data = self.dict()
        other_data = other.dict()
        
        all_fields = set(self_data.keys()) | set(other_data.keys())
        
        for field in all_fields:
            self_value = self_data.get(field)
            other_value = other_data.get(field)
            
            if self_value != other_value:
                changes[field] = (self_value, other_value)
        
        return changes


# Specialized DTO classes:

class PaginatedResponseDTO(BaseModel):
    """DTO for paginated responses."""
    
    data: List[{dto_name}] = Field(default_factory=list, description="Data items")
    total: int = Field(0, ge=0, description="Total number of items")
    page: int = Field(1, ge=1, description="Current page number")
    per_page: int = Field(15, ge=1, le=100, description="Items per page")
    
    @property
    def total_pages(self) -> int:
        """Calculate total pages."""
        return (self.total + self.per_page - 1) // self.per_page if self.total > 0 else 0
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


class ApiResponseDTO(BaseModel):
    """DTO for API responses."""
    
    success: bool = Field(True, description="Success status")
    message: str = Field("", description="Response message")
    data: Optional[Union[{dto_name}, List[{dto_name}], Dict[str, Any]]] = Field(None, description="Response data")
    errors: Optional[List[str]] = Field(default_factory=list, description="Error messages")
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response metadata")
    
    @validator('errors', pre=True)
    def ensure_errors_list(cls, v: Any) -> List[str]:
        """Ensure errors is always a list."""
        if v is None:
            return []
        elif isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            return v
        else:
            return [str(v)]


# Usage examples:
#
# # Basic usage
# dto = {dto_name}(
#     name="John Doe",
#     email="john@example.com",
#     age=30,
#     is_active=True
# )
#
# # From dictionary
# data = {{"name": "Jane", "email": "jane@example.com"}}
# dto = {dto_name}.from_dict(data)
#
# # From model
# user = User.query.first()
# dto = {dto_name}.from_model(user)
#
# # Update (creates new instance if immutable)
# updated_dto = dto.update(age=31, is_active=False)
#
# # Convert to formats
# dict_data = dto.to_dict()
# json_data = dto.to_json()
#
# # API Response
# response = ApiResponseDTO(
#     success=True,
#     message="User retrieved successfully",
#     data=dto
# )
#
# # Paginated response
# users_dto = [UserDTO.from_model(user) for user in users]
# paginated = PaginatedResponseDTO(
#     data=users_dto,
#     total=total_count,
#     page=page,
#     per_page=per_page
# )
'''
    
    def _generate_dataclass_dto(self, dto_name: str, immutable: bool = False) -> str:
        """Generate a dataclass-based DTO."""
        frozen_param = ", frozen=True" if immutable else ""
        
        return f'''from __future__ import annotations

from dataclasses import dataclass, field, asdict, astuple
from typing import Any, Dict, List, Optional, Union, TypeVar, Type
from datetime import datetime, date
from decimal import Decimal
import json

T = TypeVar('T', bound='{dto_name}')


@dataclass{frozen_param}
class {dto_name}:
    """Data Transfer Object for structured data transfer."""
    
    # Define your DTO fields here
    # Example fields:
    # id: Optional[int] = None
    # name: str = ""
    # email: Optional[str] = None
    # age: Optional[int] = None
    # is_active: bool = True
    # created_at: Optional[datetime] = None
    # metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return asdict(self)
    
    def to_tuple(self) -> tuple:
        """Convert DTO to tuple."""
        return astuple(self)
    
    def to_json(self) -> str:
        """Convert DTO to JSON string."""
        return json.dumps(self.to_dict(), default=self._json_serializer, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create DTO instance from dictionary."""
        # Filter out keys that don't exist in the dataclass
        valid_keys = {{f.name for f in cls.__dataclass_fields__.values()}}
        filtered_data = {{k: v for k, v in data.items() if k in valid_keys}}
        return cls(**filtered_data)
    
    @classmethod
    def from_model(cls: Type[T], model: Any) -> T:
        """Create DTO instance from model."""
        if hasattr(model, '__dict__'):
            model_data = {{k: v for k, v in model.__dict__.items() if not k.startswith('_')}}
            return cls.from_dict(model_data)
        else:
            raise ValueError("Model must have __dict__ attribute")
    
    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """Create DTO instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update(self: T, **kwargs: Any) -> T:
        """Create a new DTO instance with updated values."""
        {"# Note: For immutable DTOs, this creates a new instance" if immutable else ""}
        current_data = self.to_dict()
        current_data.update(kwargs)
        return self.__class__.from_dict(current_data)
    
    def merge(self: T, other: T) -> T:
        """Merge with another DTO instance."""
        current_data = self.to_dict()
        other_data = other.to_dict()
        
        # Only update with non-None values from other
        for key, value in other_data.items():
            if value is not None:
                current_data[key] = value
        
        return self.__class__.from_dict(current_data)
    
    def is_empty(self) -> bool:
        """Check if DTO contains any meaningful data."""
        data = self.to_dict()
        return all(
            value is None or 
            value == "" or 
            (isinstance(value, (list, dict)) and len(value) == 0)
            for value in data.values()
        )
    
    def has_field(self, field_name: str) -> bool:
        """Check if DTO has a specific field."""
        return field_name in self.__dataclass_fields__
    
    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get field value with default."""
        return getattr(self, field_name, default)
    
    def get_field_names(self) -> List[str]:
        """Get all field names."""
        return list(self.__dataclass_fields__.keys())
    
    def get_changed_fields(self, other: {dto_name}) -> Dict[str, tuple[Any, Any]]:
        """Get fields that are different between two DTOs."""
        changes = {{}}
        
        for field_name in self.get_field_names():
            self_value = getattr(self, field_name)
            other_value = getattr(other, field_name, None)
            
            if self_value != other_value:
                changes[field_name] = (self_value, other_value)
        
        return changes
    
    def validate(self) -> List[str]:
        """Validate DTO data and return list of errors."""
        errors = []
        
        # Add your validation logic here
        # Example validations:
        # if hasattr(self, 'email') and self.email:
        #     if '@' not in self.email:
        #         errors.append("Invalid email format")
        # 
        # if hasattr(self, 'age') and self.age is not None:
        #     if self.age < 0 or self.age > 150:
        #         errors.append("Age must be between 0 and 150")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if DTO data is valid."""
        return len(self.validate()) == 0
    
    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """Custom JSON serializer for special types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            raise TypeError(f"Object of type {{type(obj).__name__}} is not JSON serializable")
    
    def __str__(self) -> str:
        """String representation of DTO."""
        fields = [f"{{k}}={{v!r}}" for k, v in self.to_dict().items()]
        return f"{self.__class__.__name__}({{', '.join(fields)}})"
    
    def __repr__(self) -> str:
        """Detailed representation of DTO."""
        return self.__str__()


# Utility functions for working with DTOs:

def convert_models_to_dtos(models: List[Any], dto_class: Type[T]) -> List[T]:
    """Convert a list of models to DTOs."""
    return [dto_class.from_model(model) for model in models if model is not None]


def merge_dtos(*dtos: {dto_name}) -> {dto_name}:
    """Merge multiple DTOs into one."""
    if not dtos:
        return {dto_name}()
    
    result = dtos[0]
    for dto in dtos[1:]:
        result = result.merge(dto)
    
    return result


def filter_dtos(dtos: List[{dto_name}], **criteria: Any) -> List[{dto_name}]:
    """Filter DTOs based on criteria."""
    filtered = []
    
    for dto in dtos:
        matches = True
        for field, expected_value in criteria.items():
            if dto.get_field_value(field) != expected_value:
                matches = False
                break
        
        if matches:
            filtered.append(dto)
    
    return filtered


# Usage examples:
#
# # Basic usage
# dto = {dto_name}(
#     name="John Doe",
#     email="john@example.com", 
#     age=30,
#     is_active=True
# )
#
# # Validation
# if dto.is_valid():
#     print("DTO is valid")
# else:
#     print("Validation errors:", dto.validate())
#
# # From model
# user = User.query.first()
# dto = {dto_name}.from_model(user)
#
# # Update (creates new instance)
# updated_dto = dto.update(age=31)
#
# # Merge DTOs
# merged_dto = dto.merge(other_dto)
#
# # Serialization
# dict_data = dto.to_dict()
# json_data = dto.to_json()
# 
# # Bulk operations
# user_dtos = convert_models_to_dtos(users, {dto_name})
# active_dtos = filter_dtos(user_dtos, is_active=True)
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeDTOCommand)
