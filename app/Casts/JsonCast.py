from __future__ import annotations

import json
from typing import Any, Union, Optional


class JsonCast:
    """Cast for JSON serialization and deserialization."""
    
    def get(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Union[dict[str, Any], list[Any], None]:
        """Transform JSON string to Python object."""
        if value is None:
            return None
        
        if isinstance(value, str):
            try:
                return json.loads(value)  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                return None
        
        return value  # type: ignore[no-any-return]
    
    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Optional[str]:
        """Transform Python object to JSON string."""
        if value is None:
            return None
        
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        
        return str(value)