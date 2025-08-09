from __future__ import annotations

from pathlib import Path
from typing import Optional
from ..Command import Command


class MakeTransformerCommand(Command):
    """Generate a new data transformer class."""
    
    signature = "make:transformer {name : The name of the transformer} {--model= : The model to transform}"
    description = "Create a new data transformer class"
    help = "Generate a new transformer class for data transformation and serialization"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        model_name = self.option("model")
        
        if not name:
            self.error("Transformer name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Transformer"):
            name += "Transformer"
        
        transformer_path = Path(f"app/Transformers/{name}.py")
        transformer_path.parent.mkdir(parents=True, exist_ok=True)
        
        if transformer_path.exists():
            if not self.confirm(f"Transformer {name} already exists. Overwrite?"):
                self.info("Transformer creation cancelled.")
                return
        
        content = self._generate_transformer_content(name, model_name)
        transformer_path.write_text(content)
        
        self.info(f"✅ Transformer created: {transformer_path}")
        self.comment("Update the transform methods with your data transformation logic")
        if model_name:
            self.comment(f"Transformer configured for {model_name} model")
    
    def _generate_transformer_content(self, transformer_name: str, model_name: Optional[str] = None) -> str:
        """Generate transformer content."""
        model_import = ""
        model_hint = "Any"
        
        if model_name:
            model_import = f"from app.Models.{model_name} import {model_name}"
            model_hint = model_name
        
        return f'''from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
from decimal import Decimal
{model_import}


class {transformer_name}:
    """Data transformer for formatting and serializing data."""
    
    def __init__(self, **config: Any) -> None:
        """Initialize the transformer."""
        self.config = config
        self.included_relationships: List[str] = []
        self.excluded_fields: List[str] = []
        self.field_aliases: Dict[str, str] = {{}}
        self.custom_transformers: Dict[str, Callable] = {{}}
    
    def transform(self, data: {model_hint}) -> Dict[str, Any]:
        """Transform a single item."""
        if data is None:
            return {{}}
        
        # Base transformation
        transformed = self._apply_base_transformation(data)
        
        # Apply field aliases
        transformed = self._apply_field_aliases(transformed)
        
        # Apply custom field transformers
        transformed = self._apply_custom_transformers(transformed, data)
        
        # Include relationships if specified
        transformed = self._include_relationships(transformed, data)
        
        # Exclude specified fields
        transformed = self._exclude_fields(transformed)
        
        return transformed
    
    def transform_collection(self, data: List[{model_hint}]) -> List[Dict[str, Any]]:
        """Transform a collection of items."""
        return [self.transform(item) for item in data if item is not None]
    
    def _apply_base_transformation(self, data: {model_hint}) -> Dict[str, Any]:
        """Apply base data transformation."""
        if hasattr(data, '__dict__'):
            # Transform model/object
            transformed = {{}}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):
                    transformed[key] = self._transform_value(value)
            return transformed
        elif isinstance(data, dict):
            # Transform dictionary
            return {{key: self._transform_value(value) for key, value in data.items()}}
        else:
            # Transform primitive value
            return {{"value": self._transform_value(data)}}
    
    def _transform_value(self, value: Any) -> Any:
        """Transform individual values."""
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (list, tuple)):
            return [self._transform_value(item) for item in value]
        elif isinstance(value, dict):
            return {{k: self._transform_value(v) for k, v in value.items()}}
        elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool)):
            # Transform nested objects
            return self._apply_base_transformation(value)
        else:
            return value
    
    def _apply_field_aliases(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field name aliases."""
        if not self.field_aliases:
            return data
        
        transformed = {{}}
        for key, value in data.items():
            new_key = self.field_aliases.get(key, key)
            transformed[new_key] = value
        
        return transformed
    
    def _apply_custom_transformers(self, data: Dict[str, Any], original: {model_hint}) -> Dict[str, Any]:
        """Apply custom field transformers."""
        for field, transformer in self.custom_transformers.items():
            if field in data:
                try:
                    data[field] = transformer(data[field], original)
                except Exception as e:
                    # Log error and keep original value
                    print(f"Transformer error for field '{{field}}': {{e}}")
        
        return data
    
    def _include_relationships(self, data: Dict[str, Any], original: {model_hint}) -> Dict[str, Any]:
        """Include specified relationships."""
        if not self.included_relationships:
            return data
        
        for relationship in self.included_relationships:
            if hasattr(original, relationship):
                related_data = getattr(original, relationship)
                
                if related_data is not None:
                    if isinstance(related_data, list):
                        # Collection relationship
                        data[relationship] = [
                            self._apply_base_transformation(item) 
                            for item in related_data
                        ]
                    else:
                        # Single relationship
                        data[relationship] = self._apply_base_transformation(related_data)
        
        return data
    
    def _exclude_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Exclude specified fields."""
        if not self.excluded_fields:
            return data
        
        return {{key: value for key, value in data.items() 
                if key not in self.excluded_fields}}
    
    def include(self, *relationships: str) -> '{transformer_name}':
        """Specify relationships to include."""
        self.included_relationships.extend(relationships)
        return self
    
    def exclude(self, *fields: str) -> '{transformer_name}':
        """Specify fields to exclude."""
        self.excluded_fields.extend(fields)
        return self
    
    def alias(self, **aliases: str) -> '{transformer_name}':
        """Set field aliases."""
        self.field_aliases.update(aliases)
        return self
    
    def custom(self, field: str, transformer: Callable) -> '{transformer_name}':
        """Add custom transformer for a field."""
        self.custom_transformers[field] = transformer
        return self
    
    def with_meta(self, data: Dict[str, Any], **meta: Any) -> Dict[str, Any]:
        """Add metadata to transformed data."""
        return {{
            "data": data,
            "meta": {{
                "transformer": "{transformer_name}",
                "transformed_at": datetime.now().isoformat(),
                **meta
            }}
        }}
    
    def paginate(
        self, 
        data: List[Dict[str, Any]], 
        page: int = 1, 
        per_page: int = 15,
        total: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add pagination metadata."""
        total = total or len(data)
        last_page = (total + per_page - 1) // per_page
        
        return {{
            "data": data,
            "pagination": {{
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "last_page": last_page,
                "from": ((page - 1) * per_page) + 1 if data else None,
                "to": min(page * per_page, total) if data else None,
                "has_more": page < last_page
            }}
        }}


# Specialized transformer classes:

class CollectionTransformer({transformer_name}):
    """Transformer for collections with enhanced pagination support."""
    
    def transform_with_pagination(
        self, 
        data: List[{model_hint}], 
        page: int = 1, 
        per_page: int = 15,
        total: Optional[int] = None
    ) -> Dict[str, Any]:
        """Transform collection with pagination."""
        transformed_data = self.transform_collection(data)
        return self.paginate(transformed_data, page, per_page, total)


class APITransformer({transformer_name}):
    """API-specific transformer with response formatting."""
    
    def success_response(
        self, 
        data: Union[{model_hint}, List[{model_hint}]], 
        message: str = "Success",
        status_code: int = 200
    ) -> Dict[str, Any]:
        """Format successful API response."""
        if isinstance(data, list):
            transformed = self.transform_collection(data)
        else:
            transformed = self.transform(data)
        
        return {{
            "success": True,
            "message": message,
            "status_code": status_code,
            "data": transformed,
            "timestamp": datetime.now().isoformat()
        }}
    
    def error_response(
        self, 
        error: str, 
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format error API response."""
        return {{
            "success": False,
            "error": error,
            "status_code": status_code,
            "details": details or {{}},
            "timestamp": datetime.now().isoformat()
        }}


# Usage examples:
#
# # Basic transformation
# transformer = {transformer_name}()
# result = transformer.transform(model_instance)
#
# # With relationships and field customization
# result = transformer.include("posts", "comments") \\
#     .exclude("password", "api_key") \\
#     .alias(created_at="createdAt", updated_at="updatedAt") \\
#     .custom("price", lambda x, obj: f"${{x:.2f}}") \\
#     .transform(user)
#
# # Collection transformation
# users = transformer.transform_collection(user_list)
#
# # API response
# api_transformer = APITransformer()
# response = api_transformer.success_response(user, "User retrieved successfully")
#
# # In FastAPI endpoint
# @app.get("/users/{{user_id}}")
# async def get_user(user_id: int):
#     user = get_user_by_id(user_id)
#     transformer = {transformer_name}().include("profile", "posts")
#     return transformer.transform(user)
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeTransformerCommand)
