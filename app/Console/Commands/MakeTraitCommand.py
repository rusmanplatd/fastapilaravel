from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeTraitCommand(Command):
    """Generate a new trait (mixin class)."""
    
    signature = "make:trait {name : The name of the trait}"
    description = "Create a new trait (mixin class)"
    help = "Generate a new trait using Python mixin pattern for code reuse"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Trait name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Trait"):
            name += "Trait"
        
        trait_path = Path(f"app/Traits/{name}.py")
        trait_path.parent.mkdir(parents=True, exist_ok=True)
        
        if trait_path.exists():
            if not self.confirm(f"Trait {name} already exists. Overwrite?"):
                self.info("Trait creation cancelled.")
                return
        
        content = self._generate_trait_content(name)
        trait_path.write_text(content)
        
        self.info(f"✅ Trait created: {trait_path}")
        self.comment("Update the trait with your reusable methods")
        self.comment("Use this trait as a mixin in your classes")
        self.comment(f"Example: class MyClass(BaseClass, {name}):")
    
    def _generate_trait_content(self, trait_name: str) -> str:
        """Generate trait content."""
        return f'''from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    # Import types only for type checking to avoid circular imports
    pass


class {trait_name}:
    """Mixin trait for reusable functionality across classes."""
    
    def trait_method(self, parameter: Any) -> Any:
        """Example trait method."""
        # Production-ready reusable functionality implementation
        try:
            from app.Support.Facades.Log import Log
            
            # Log method usage for debugging/monitoring
            Log.debug(f"{{self.__class__.__name__}} using trait method", {{
                'trait': '{{trait_name}}',
                'parameter_type': type(parameter).__name__,
                'class': self.__class__.__name__
            }})
            
            # Example trait implementations (uncomment and customize as needed):
            
            # 1. Data validation trait
            # if hasattr(self, '_validate_data'):
            #     validated_parameter = self._validate_data(parameter)
            #     return validated_parameter
            
            # 2. Caching trait
            # if hasattr(self, '_cache_key'):
            #     from app.Support.Facades.Cache import Cache
            #     cache_key = f"{{self._cache_key}}_{{hash(str(parameter))}}"
            #     cached_result = Cache.get(cache_key)
            #     if cached_result is not None:
            #         return cached_result
            #     result = self._process_parameter(parameter)
            #     Cache.put(cache_key, result, 300)  # Cache for 5 minutes
            #     return result
            
            # 3. Transformation trait
            # if isinstance(parameter, str):
            #     return parameter.strip().title()  # Clean and format string
            # elif isinstance(parameter, (list, tuple)):
            #     return [self.trait_method(item) for item in parameter]  # Recursive processing
            # elif isinstance(parameter, dict):
            #     return {k: self.trait_method(v) for k, v in parameter.items()}
            
            # 4. Validation trait
            # if hasattr(self, 'validation_rules'):
            #     for rule in self.validation_rules:
            #         if not rule(parameter):
            #             raise ValueError(f"Parameter validation failed: {{parameter}}")
            
            # 5. Audit trail trait
            # if hasattr(self, '_audit_enabled') and self._audit_enabled:
            #     from app.Support.Facades.Event import Event
            #     Event.dispatch('trait_method_used', {{
            #         'trait': '{{trait_name}}',
            #         'class': self.__class__.__name__,
            #         'parameter': parameter
            #     }})
            
            # Default: return parameter unchanged (safe fallback)
            return parameter
            
        except Exception as e:
            # Log error but don't break the application
            from app.Support.Facades.Log import Log
            Log.error(f"Error in {{'{trait_name}'}} trait method: {{str(e)}}", {{
                'error': str(e),
                'parameter': parameter,
                'class': self.__class__.__name__
            }})
            # Return parameter unchanged as fallback
            return parameter
    
    def get_trait_info(self) -> Dict[str, Any]:
        """Get information about this trait."""
        return {{
            "trait_name": "{trait_name}",
            "methods": [method for method in dir(self) if not method.startswith('_')],
            "timestamp": datetime.now().isoformat()
        }}
    
    # Example common functionality patterns:
    
    # Timestamping functionality
    def touch(self) -> None:
        """Update timestamp (requires updated_at attribute)."""
        if hasattr(self, 'updated_at'):
            self.updated_at = datetime.now()
    
    def fresh_timestamp(self) -> datetime:
        """Get fresh timestamp."""
        return datetime.now()
    
    # Serialization functionality  
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary."""
        result = {{}}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif hasattr(value, 'to_dict'):
                    result[key] = value.to_dict()
                elif hasattr(value, '__dict__'):
                    result[key] = str(value)
                else:
                    result[key] = value
        return result
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Update object from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    # Validation functionality
    def validate_required_fields(self, required_fields: List[str]) -> bool:
        """Validate that required fields are present."""
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                return False
        return True
    
    def has_attribute(self, attribute: str) -> bool:
        """Check if object has attribute."""
        return hasattr(self, attribute)
    
    def get_attribute_value(self, attribute: str, default: Any = None) -> Any:
        """Get attribute value with default."""
        return getattr(self, attribute, default)
    
    # Utility functionality
    def clone(self) -> Any:
        """Create a shallow copy of the object."""
        import copy
        return copy.copy(self)
    
    def deep_clone(self) -> Any:
        """Create a deep copy of the object."""
        import copy
        return copy.deepcopy(self)


# Example usage:
#
# class User(BaseModel, {trait_name}):
#     """User model with trait functionality."""
#     
#     def __init__(self, name: str, email: str):
#         self.name = name
#         self.email = email
#         self.updated_at = datetime.now()
#     
#     # Now has access to all trait methods:
#     # user.touch()
#     # user.to_dict()
#     # user.validate_required_fields(['name', 'email'])
#
# class Product(BaseModel, {trait_name}):
#     """Product model with trait functionality."""
#     
#     def __init__(self, title: str, price: float):
#         self.title = title
#         self.price = price
#         self.updated_at = datetime.now()
#     
#     # Also has access to all trait methods


# Multiple inheritance example:
#
# from app.Traits.LogsActivityTrait import LogsActivityTrait
# from app.Traits.CacheableTrait import CacheableTrait
#
# class MyModel(BaseModel, {trait_name}, LogsActivityTrait, CacheableTrait):
#     """Model with multiple traits."""
#     pass


# Conditional trait usage:
#
# class ConditionalTraitMixin({trait_name}):
#     """Conditional trait usage."""
#     
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if hasattr(self, 'enable_trait_features'):
#             if self.enable_trait_features:
#                 self.setup_trait_features()
#     
#     def setup_trait_features(self) -> None:
#         """Setup trait-specific features."""
#         pass
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeTraitCommand)
