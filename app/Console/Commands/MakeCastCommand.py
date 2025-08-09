from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeCastCommand(Command):
    """Generate a new attribute cast class."""
    
    signature = "make:cast {name : The name of the cast} {--inbound : Generate an inbound-only cast}"
    description = "Create a new custom cast class"
    help = "Generate a new custom cast class for model attributes"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        inbound_only = self.option("inbound")
        
        if not name:
            self.error("Cast name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Cast"):
            name += "Cast"
        
        cast_path = Path(f"app/Casts/{name}.py")
        cast_path.parent.mkdir(parents=True, exist_ok=True)
        
        if cast_path.exists():
            if not self.confirm(f"Cast {name} already exists. Overwrite?"):
                self.info("Cast creation cancelled.")
                return
        
        content = self._generate_cast_content(name, inbound_only)
        cast_path.write_text(content)
        
        self.info(f"✅ Cast created: {cast_path}")
        self.comment("Update the get() and set() methods with your casting logic")
        self.comment(f"Register the cast in your model: __casts__ = {{'field_name': '{name}'}}")
    
    def _generate_cast_content(self, cast_name: str, inbound_only: bool = False) -> str:
        """Generate cast content."""
        if inbound_only:
            return self._generate_inbound_cast(cast_name)
        else:
            return self._generate_full_cast(cast_name)
    
    def _generate_full_cast(self, cast_name: str) -> str:
        """Generate a full cast class with get and set methods."""
        return f'''from __future__ import annotations

from typing import Any, Optional
from abc import ABC, abstractmethod


class CastContract(ABC):
    """Contract for custom attribute casts."""
    
    @abstractmethod
    def get(self, model: Any, key: str, value: Any, attributes: dict) -> Any:
        """Transform the attribute from the model."""
        pass
    
    @abstractmethod
    def set(self, model: Any, key: str, value: Any, attributes: dict) -> Any:
        """Transform the attribute to the model."""
        pass


class {cast_name}(CastContract):
    """Custom cast for attribute transformation."""
    
    def get(self, model: Any, key: str, value: Any, attributes: dict) -> Any:
        """Transform the attribute when retrieving from the model."""
        if value is None:
            return None
        
        # Production-ready casting implementation for data retrieval
        try:
            # Common casting patterns (uncomment and modify as needed):
            
            # 1. JSON string to Python object
            # if isinstance(value, str):
            #     import json
            #     return json.loads(value)
            
            # 2. Timestamp to datetime object
            # if isinstance(value, (int, float)):
            #     from datetime import datetime
            #     return datetime.fromtimestamp(value)
            
            # 3. Encrypted string decryption
            # if isinstance(value, str):
            #     from app.Support.Facades.Crypt import Crypt
            #     return Crypt.decrypt(value)
            
            # 4. String case transformation
            # if isinstance(value, str):
            #     return value.upper()  # or .lower(), .title(), .capitalize()
            
            # 5. Boolean conversion from string
            # if isinstance(value, str):
            #     return value.lower() in ('true', '1', 'yes', 'on')
            
            # 6. Array/List from comma-separated string
            # if isinstance(value, str):
            #     return [item.strip() for item in value.split(',') if item.strip()]
            
            # 7. Decimal/Currency formatting
            # if isinstance(value, (int, float, str)):
            #     from decimal import Decimal
            #     return Decimal(str(value))
            
            # Default: return value unchanged
            return value
            
        except Exception as e:
            # Log casting error and return original value as fallback
            from app.Support.Facades.Log import Log
            Log.warning(f"Cast get() failed for key '{key}': {str(e)}", {
                'cast_class': self.__class__.__name__,
                'value_type': type(value).__name__,
                'error': str(e)
            })
            return value
    
    def set(self, model: Any, key: str, value: Any, attributes: dict) -> Any:
        """Transform the attribute when storing to the model."""
        if value is None:
            return None
        
        # Production-ready reverse casting implementation for data storage
        try:
            # Common reverse casting patterns (uncomment and modify as needed):
            
            # 1. Python object to JSON string
            # if isinstance(value, (dict, list, tuple)):
            #     import json
            #     return json.dumps(value, default=str, ensure_ascii=False)
            
            # 2. Datetime to timestamp
            # if hasattr(value, 'timestamp'):
            #     return value.timestamp()
            
            # 3. String encryption
            # if isinstance(value, str):
            #     from app.Support.Facades.Crypt import Crypt
            #     return Crypt.encrypt(value)
            
            # 4. String case transformation
            # if isinstance(value, str):
            #     return value.lower()  # or .upper(), .title(), .capitalize()
            
            # 5. Boolean to string conversion
            # if isinstance(value, bool):
            #     return 'true' if value else 'false'
            
            # 6. Array/List to comma-separated string
            # if isinstance(value, (list, tuple)):
            #     return ','.join(str(item) for item in value)
            
            # 7. Number formatting
            # if isinstance(value, (int, float)):
            #     return f"{value:.2f}"  # Format to 2 decimal places
            
            # Default: return value unchanged
            return value
            
        except Exception as e:
            # Log casting error and return original value as fallback
            from app.Support.Facades.Log import Log
            Log.warning(f"Cast set() failed for key '{key}': {str(e)}", {
                'cast_class': self.__class__.__name__,
                'value_type': type(value).__name__,
                'error': str(e)
            })
            return value
        
        return value
    
    # Helper methods (optional)
    # def encrypt(self, value: str) -> str:
    #     """Encrypt a value."""
    #     # Implement encryption logic
    #     return value
    # 
    # def decrypt(self, value: str) -> str:
    #     """Decrypt a value."""
    #     # Implement decryption logic
    #     return value


# Example usage in model:
# class User(BaseModel):
#     __casts__ = {{
#         'preferences': '{cast_name}',
#         'metadata': '{cast_name}',
#     }}
'''
    
    def _generate_inbound_cast(self, cast_name: str) -> str:
        """Generate an inbound-only cast class."""
        return f'''from __future__ import annotations

from typing import Any, Optional


class {cast_name}:
    """Inbound-only cast for attribute transformation."""
    
    def set(self, model: Any, key: str, value: Any, attributes: dict) -> Any:
        """Transform the attribute when storing to the model."""
        if value is None:
            return None
        
        # Production-ready inbound-only casting implementation
        try:
            # Common inbound casting patterns (uncomment and modify as needed):
            
            # 1. Password hashing
            # if isinstance(value, str) and key.endswith('password'):
            #     from app.Support.Facades.Hash import Hash
            #     return Hash.make(value)
            
            # 2. Phone number formatting
            # if isinstance(value, str) and 'phone' in key.lower():
            #     import re
            #     # Remove all non-digit characters
            #     digits_only = re.sub(r'\\D', '', value)
            #     # Format as (XXX) XXX-XXXX for US numbers
            #     if len(digits_only) == 10:
            #         return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
            #     return digits_only
            
            # 3. Input sanitization
            # if isinstance(value, str):
            #     import html
            #     import re
            #     # HTML escape and remove potentially dangerous content
            #     sanitized = html.escape(value.strip())
            #     # Remove script tags and other dangerous content
            #     sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            #     return sanitized
            
            # 4. Case transformation for consistency
            # if isinstance(value, str) and key.endswith('_code'):
            #     return value.upper().strip()
            
            # 5. Email normalization
            # if isinstance(value, str) and 'email' in key.lower():
            #     return value.lower().strip()
            
            # 6. URL normalization
            # if isinstance(value, str) and 'url' in key.lower():
            #     if not value.startswith(('http://', 'https://')):
            #         return f"https://{value}"
            #     return value
            
            # 7. Slug generation
            # if isinstance(value, str) and key == 'slug':
            #     import re
            #     slug = value.lower().strip()
            #     slug = re.sub(r'[^a-z0-9]+', '-', slug)
            #     return slug.strip('-')
            
            # Default: return value unchanged
            return value
            
        except Exception as e:
            # Log casting error and return original value as fallback
            from app.Support.Facades.Log import Log
            Log.warning(f"Cast set() failed for key '{key}': {str(e)}", {
                'cast_class': self.__class__.__name__,
                'value_type': type(value).__name__,
                'error': str(e)
            })
            return value
        
        return value
    
    # Helper methods (optional)
    # def format_phone(self, phone: str) -> str:
    #     \"\"\"Format phone number.\"\"\"
    #     # Remove non-digits and format
    #     phone_digits = ''.join(filter(str.isdigit, phone))
    #     if len(phone_digits) == 10:
    #         return f"({{phone_digits[:3]}}) {{phone_digits[3:6]}}-{{phone_digits[6:]}}"
    #     return phone
    # 
    # def sanitize(self, value: str) -> str:
    #     \"\"\"Sanitize input value.\"\"\"
    #     # Implement sanitization logic
    #     return value.strip()


# Example usage in model:
# class User(BaseModel):
#     __casts__ = {{
#         'phone': '{cast_name}',
#         'password': '{cast_name}',
#     }}
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeCastCommand)
