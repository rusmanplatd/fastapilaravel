from __future__ import annotations

from typing import Dict, Any, List, Optional, Type, Callable, Union
from abc import ABC, abstractmethod
from fastapi import HTTPException, status, Request
from pydantic import BaseModel, validator
from pydantic_core import ValidationError
from functools import wraps


class FormRequest(BaseModel, ABC):
    """Laravel-style Form Request for validation and authorization."""
    
    class Config:
        extra = "forbid"
        validate_assignment = True
    
    @abstractmethod
    def authorize(self, request: Request) -> bool:
        """Determine if the user is authorized to make this request."""
        pass
    
    @abstractmethod
    def rules(self) -> Dict[str, Any]:
        """Get the validation rules that apply to the request."""
        pass
    
    def messages(self) -> Dict[str, str]:
        """Get custom validation messages."""
        return {}
    
    def attributes(self) -> Dict[str, str]:
        """Get custom attribute names for validation."""
        return {}
    
    def prepare_for_validation(self) -> None:
        """Prepare the data for validation."""
        pass
    
    def after_validation(self) -> None:
        """Perform additional validation after basic validation passes."""
        pass
    
    def passes_authorization(self, request: Request) -> bool:
        """Check if authorization passes."""
        try:
            return self.authorize(request)
        except Exception:
            return False
    
    def validate_request(self, request: Request) -> FormRequest:
        """Validate the request and return validated instance."""
        if not self.passes_authorization(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This action is unauthorized."
            )
        
        self.prepare_for_validation()
        
        try:
            # Pydantic validation happens automatically during instantiation
            self.after_validation()
            return self
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "The given data was invalid.",
                    "errors": self._format_validation_errors(e.errors())
                }
            )
    
    def _format_validation_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Format validation errors in Laravel style."""
        formatted_errors: Dict[str, List[str]] = {}
        
        for error in errors:
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            
            # Apply custom messages if available
            custom_messages = self.messages()
            if field in custom_messages:
                message = custom_messages[field]
            
            # Apply custom attribute names
            custom_attributes = self.attributes()
            if field in custom_attributes:
                field = custom_attributes[field]
            
            if field not in formatted_errors:
                formatted_errors[field] = []
            formatted_errors[field].append(message)
        
        return formatted_errors


def validate_with_form_request(form_request_class: Type[FormRequest]) -> Callable[..., Any]:
    """Decorator to validate request using a Form Request class."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request and data from arguments
            request = None
            data = {}
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Get request data
            if request:
                if hasattr(request, 'method') and request.method in ["POST", "PUT", "PATCH"]:
                    try:
                        if hasattr(request, 'json'):
                            data = await request.json()
                    except Exception:
                        data = {}
                else:
                    if hasattr(request, 'query_params'):
                        data = dict(request.query_params)
            
            # Create and validate form request
            form_request = form_request_class(**data)
            if request:
                validated_request = form_request.validate_request(request)
            else:
                validated_request = form_request
            
            # Add validated data to kwargs
            kwargs['validated_data'] = validated_request
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class BaseFormRequest(FormRequest):
    """Base form request with common authorization logic."""
    
    def authorize(self, request: Request) -> bool:
        """Default authorization - always allow."""
        return True