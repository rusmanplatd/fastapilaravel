from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Callable, 
    Dict, 
    List, 
    Optional, 
    Type, 
    Union,
    final,
    ClassVar,
    Any,
    Protocol
)

from fastapi import HTTPException, Request
from pydantic import BaseModel
from pydantic_core import ValidationError

from app.Support.Arr import Arr
from app.Validation.Validator import ValidationRule, make_validator

if TYPE_CHECKING:
    from app.Models.User import User


# Laravel 12 Conditional Rules
@dataclass
class ConditionalRules:
    """Laravel 12 conditional validation rules."""
    
    condition: bool
    rules: Dict[str, Union[str, List[str]]]
    
    def apply(self, base_rules: Dict[str, Union[str, List[str]]]) -> Dict[str, Union[str, List[str]]]:
        """Apply conditional rules to base rules."""
        if self.condition:
            base_rules.update(self.rules)
        return base_rules


class FormRequestRule:
    """Custom validation rule for form requests."""
    
    def __init__(self, rule: str, message: Optional[str] = None):
        self.rule = rule
        self.message = message
    
    def validate(self, field: str, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> bool:
        """Validate the field value."""
        # Implementation would parse the rule string and validate
        return True
    
    def get_message(self, field: str) -> str:
        """Get the validation error message."""
        return self.message or f"The {field} field is invalid."


class ValidationMessages:
    """Custom validation messages for form requests."""
    
    def __init__(self, messages: Dict[str, str]):
        self.messages = messages
    
    def get(self, field: str, rule: str) -> Optional[str]:
        """Get a custom message for a field and rule."""
        # Try field.rule first
        key = f"{field}.{rule}"
        if key in self.messages:
            return self.messages[key]
        
        # Then try just the rule
        if rule in self.messages:
            return self.messages[rule]
        
        return None


class FormRequestValidator:
    """Validator for form requests."""
    
    def __init__(self, rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None):
        self.rules = rules
        self.custom_messages = ValidationMessages(messages or {})
        self.errors: Dict[str, List[str]] = {}
    
    def validate(self, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> bool:
        """Validate the data against the rules."""
        self.errors = {}
        
        for field, field_rules in self.rules.items():
            if isinstance(field_rules, str):
                field_rules = [field_rules]
            
            value = Arr.get(data, field)
            
            for rule_str in field_rules:
                if not self._validate_rule(field, value, rule_str, data):
                    if field not in self.errors:
                        self.errors[field] = []
                    
                    message = self._get_error_message(field, rule_str, value)
                    self.errors[field].append(message)
        
        return len(self.errors) == 0
    
    def _validate_rule(self, field: str, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], rule_str: str, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> bool:
        """Validate a single rule."""
        # Parse rule (e.g., "required", "min:5", "max:10")
        if ':' in rule_str:
            rule_name, rule_param = rule_str.split(':', 1)
        else:
            rule_name = rule_str
            rule_param = None
        
        # Apply validation logic
        if rule_name == 'required':
            return value is not None and value != ''
        elif rule_name == 'string':
            return isinstance(value, str)
        elif rule_name == 'integer':
            return isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        elif rule_name == 'email':
            return isinstance(value, str) and '@' in value  # Simplified
        elif rule_name == 'min':
            min_val = int(rule_param) if rule_param else 0
            if isinstance(value, str):
                return len(value) >= min_val
            elif isinstance(value, (int, float)):
                return value >= min_val
        elif rule_name == 'max':
            max_val = int(rule_param) if rule_param else 0
            if isinstance(value, str):
                return len(value) <= max_val
            elif isinstance(value, (int, float)):
                return value <= max_val
        elif rule_name == 'in':
            allowed_values = rule_param.split(',') if rule_param else []
            return str(value) in allowed_values
        elif rule_name == 'unique':
            # This would check database uniqueness
            return True  # Simplified
        elif rule_name == 'exists':
            # This would check if value exists in database
            return True  # Simplified
        
        return True
    
    def _get_error_message(self, field: str, rule: str, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None]) -> str:
        """Get the error message for a validation failure."""
        rule_name = rule.split(':')[0]
        
        # Check for custom message
        custom_message = self.custom_messages.get(field, rule_name)
        if custom_message:
            return custom_message.replace(':attribute', field).replace(':value', str(value))
        
        # Default messages
        messages = {
            'required': f'The {field} field is required.',
            'string': f'The {field} must be a string.',
            'integer': f'The {field} must be an integer.',
            'email': f'The {field} must be a valid email address.',
            'min': f'The {field} must be at least {rule.split(":")[1] if ":" in rule else "0"} characters.',
            'max': f'The {field} may not be greater than {rule.split(":")[1] if ":" in rule else "0"} characters.',
            'in': f'The selected {field} is invalid.',
            'unique': f'The {field} has already been taken.',
            'exists': f'The selected {field} is invalid.'
        }
        
        return messages.get(rule_name, f'The {field} field is invalid.')
    
    def get_errors(self) -> Dict[str, List[str]]:
        """Get validation errors."""
        return self.errors
    
    def get_first_error(self, field: Optional[str] = None) -> Optional[str]:
        """Get the first error for a field or overall."""
        if field:
            return self.errors.get(field, [None])[0]
        
        for field_errors in self.errors.values():
            if field_errors:
                return field_errors[0]
        
        return None


class FormRequestInterface(Protocol):
    """Laravel 12 Form Request interface."""
    
    def authorize(self) -> bool:
        """Determine if the user is authorized to make this request."""
        ...
    
    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """Get the validation rules that apply to the request."""
        ...
    
    def messages(self) -> Dict[str, str]:
        """Get custom validation messages."""
        ...
    
    def attributes(self) -> Dict[str, str]:
        """Get custom attribute names for validation errors."""
        ...


class FormRequest(ABC):
    """
    Laravel 12 Enhanced Form Request.
    
    Provides comprehensive validation, authorization, and data handling
    with strict type safety and Laravel 12 patterns.
    """
    
    # Laravel 12 class-level configuration
    _redirect_route: ClassVar[Optional[str]] = None
    _error_bag: ClassVar[str] = "default"
    _stop_on_first_failure: ClassVar[bool] = False
    
    def __init__(self, request: Request) -> None:
        """Initialize form request with Laravel 12 enhancements."""
        self.request: Request = request
        self._validated_data: Optional[Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]] = None
        self._errors: Dict[str, List[str]] = {}
        self._container: Optional[object] = None
        self._user: Optional['User'] = None
        self._route_resolver: Optional[Callable[[], str]] = None
    
    @abstractmethod
    def authorize(self) -> bool:
        """Determine if the user is authorized to make this request."""
        return True
    
    @abstractmethod
    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """Get the validation rules that apply to the request."""
        return {}
    
    def messages(self) -> Dict[str, str]:
        """Get custom validation messages."""
        return {}
    
    def attributes(self) -> Dict[str, str]:
        """Get custom attribute names for validation errors."""
        return {}
    
    # Laravel 12 enhanced methods
    def user(self) -> Optional['User']:
        """Get the authenticated user (Laravel 12)."""
        if self._user is None:
            # Integration point for authentication
            self._user = getattr(self.request.state, 'user', None)
        return self._user
    
    def route(self, param: Optional[str] = None) -> Union[str, object]:
        """Get route information (Laravel 12)."""
        if param is None:
            return getattr(self.request, 'url', {}).path or ""
        return getattr(self.request, 'path_params', {}).get(param)
    
    def authorize_resource(self, model_class: Type[Any], parameter: Optional[str] = None) -> bool:
        """Laravel 12 resource authorization."""
        # Integration point for resource-based authorization
        return True
    
    def when(self, condition: bool, rules: Dict[str, Union[str, List[str]]]) -> 'ConditionalRules':
        """Laravel 12 conditional validation rules."""
        return ConditionalRules(condition, rules)
    
    def unless(self, condition: bool, rules: Dict[str, Union[str, List[str]]]) -> 'ConditionalRules':
        """Laravel 12 conditional validation rules (unless)."""
        return ConditionalRules(not condition, rules)
    
    def sometimes(self, attribute: str, rules: Union[str, List[str]], callback: Callable[..., bool]) -> None:
        """Laravel 12 sometimes validation."""
        # Implementation would be handled by validator
        pass
    
    def passesAuthorization(self) -> bool:
        """Check if request passes authorization (Laravel 12)."""
        try:
            return self.authorize()
        except Exception:
            return False
    
    def forbiddenResponse(self) -> None:
        """Handle forbidden response (Laravel 12)."""
        raise HTTPException(
            status_code=403,
            detail={
                "message": "This action is unauthorized.",
                "error_bag": self._error_bag
            }
        )
    
    def validated(self, key: Optional[str] = None, default: Union[str, int, float, bool, List[Union[str, int, float, bool]], None] = None) -> Union[Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]], Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Get validated data (Laravel 12)."""
        if self._validated_data is None:
            raise RuntimeError("Validation has not been performed yet.")
        
        if key is not None:
            return self._validated_data.get(key, default)
        
        return self._validated_data
    
    def safe(self, keys: Optional[List[str]] = None) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Get safe validated data (Laravel 12)."""
        validated_data = self.validated()
        if keys is None:
            return validated_data
        return {key: validated_data.get(key) for key in keys if key in validated_data}
    
    async def validate(self) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Validate the request."""
        # Check authorization
        if not self.authorize():
            raise HTTPException(status_code=403, detail="This action is unauthorized.")
        
        # Get request data
        data = await self._get_request_data()
        
        # Prepare data
        data = self.prepare_for_validation(data)
        
        # Validate data
        validator = FormRequestValidator(self.rules(), self.messages())
        
        if not validator.validate(data):
            self._errors = validator.get_errors()
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "The given data was invalid.",
                    "errors": self._errors
                }
            )
        
        # Store validated data
        self._validated_data = data
        
        # After validation hook
        self.after_validation(data)
        
        return data
    
    async def _get_request_data(self) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Get data from the request."""
        data = {}
        
        # Get query parameters
        if self.request.query_params:
            data.update(dict(self.request.query_params))
        
        # Get form data or JSON data
        content_type = self.request.headers.get('content-type', '')
        
        if 'application/json' in content_type:
            try:
                body = await self.request.body()  # type: ignore[attr-defined]
                if body:
                    data.update(json.loads(body))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            try:
                form_data = await self.request.form()  # type: ignore[attr-defined]
                # Convert FormData to dict, handling UploadFile objects
                for key, value in form_data.items():
                    if hasattr(value, 'filename'):  # UploadFile object
                        data[key] = value
                    else:
                        data[key] = str(value)
            except Exception:
                pass
        
        # Get path parameters
        if hasattr(self.request, 'path_params') and self.request.path_params:
            data.update(self.request.path_params)
        
        return data
    
    def prepare_for_validation(self, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Prepare the data for validation."""
        return data
    
    def after_validation(self, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> None:
        """Hook called after successful validation."""
        pass
    
    def only(self, *keys: str) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Get only the specified keys from validated data."""
        return self.safe(list(keys))
    
    def except_keys(self, *keys: str) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Get all validated data except the specified keys."""
        validated = self.validated()
        return {k: v for k, v in validated.items() if k not in keys}
    
    def has(self, key: str) -> bool:
        """Check if the validated data has a key."""
        return key in self.validated()
    
    def get(self, key: str, default: Union[str, int, float, bool, List[Union[str, int, float, bool]], None] = None) -> Union[str, int, float, bool, List[Union[str, int, float, bool]], None]:
        """Get a value from validated data."""
        return self.validated().get(key, default)


# Dependency for FastAPI
async def form_request_validator(form_request_class: Type[FormRequest]) -> Callable[..., object]:
    """FastAPI dependency for form request validation."""
    def validator(request: Request) -> Callable[..., object]:
        async def validate() -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
            form_request = form_request_class(request)
            return await form_request.validate()
        return validate
    return validator


# Example form requests
class CreateUserRequest(FormRequest):
    """Form request for creating a user."""
    
    def authorize(self) -> bool:
        """Check if user can create users."""
        # In a real app, you'd check user permissions
        return True
    
    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """Validation rules for creating a user."""
        return {
            'name': ['required', 'string', 'min:2', 'max:100'],
            'email': ['required', 'email', 'unique:users,email'],
            'password': ['required', 'string', 'min:8'],
            'password_confirmation': ['required', 'string'],
            'age': ['integer', 'min:18', 'max:120']
        }
    
    def messages(self) -> Dict[str, str]:
        """Custom validation messages."""
        return {
            'name.required': 'Please provide your name.',
            'email.unique': 'This email address is already registered.',
            'password.min': 'Password must be at least 8 characters long.',
            'age.min': 'You must be at least 18 years old.'
        }
    
    def prepare_for_validation(self, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Prepare data before validation."""
        # Trim whitespace from strings
        if 'name' in data and isinstance(data['name'], str):
            data['name'] = data['name'].strip()
        
        if 'email' in data and isinstance(data['email'], str):
            data['email'] = data['email'].lower().strip()
        
        return data
    
    def after_validation(self, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> None:
        """Check password confirmation after validation."""
        if data.get('password') != data.get('password_confirmation'):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "The given data was invalid.",
                    "errors": {
                        "password_confirmation": ["The password confirmation does not match."]
                    }
                }
            )


class UpdateUserRequest(FormRequest):
    """Form request for updating a user."""
    
    def authorize(self) -> bool:
        """Check if user can update this user."""
        # In a real app, you'd check if user owns the resource or has permission
        return True
    
    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """Validation rules for updating a user."""
        # Get user ID from path parameters for unique validation
        user_id = getattr(self.request, 'path_params', {}).get('user_id')
        
        return {
            'name': ['string', 'min:2', 'max:100'],
            'email': [f'email', f'unique:users,email,{user_id}'],
            'age': ['integer', 'min:18', 'max:120']
        }
    
    def messages(self) -> Dict[str, str]:
        """Custom validation messages."""
        return {
            'email.unique': 'This email address is already taken by another user.',
            'age.min': 'You must be at least 18 years old.'
        }


class CreatePostRequest(FormRequest):
    """Form request for creating a post."""
    
    def authorize(self) -> bool:
        """Check if user can create posts."""
        return True
    
    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """Validation rules for creating a post."""
        return {
            'title': ['required', 'string', 'min:5', 'max:200'],
            'content': ['required', 'string', 'min:10'],
            'category': ['required', 'string', 'in:tech,lifestyle,business,other'],
            'tags': ['string'],  # Comma-separated tags
            'published': ['in:true,false,1,0']
        }
    
    def messages(self) -> Dict[str, str]:
        """Custom validation messages."""
        return {
            'title.required': 'Please provide a title for your post.',
            'title.min': 'The title must be at least 5 characters long.',
            'content.required': 'Please provide content for your post.',
            'content.min': 'The content must be at least 10 characters long.',
            'category.in': 'Please select a valid category.'
        }
    
    def prepare_for_validation(self, data: Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        """Prepare data before validation."""
        # Convert published to boolean
        if 'published' in data:
            published = data['published']
            if isinstance(published, str):
                data['published'] = published.lower() in ['true', '1']
            else:
                data['published'] = bool(published)
        
        # Process tags
        if 'tags' in data and isinstance(data['tags'], str):
            tags = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
            data['tags'] = tags
        
        return data


# Helper functions for creating form request dependencies
def create_form_request_dependency(form_request_class: Type[FormRequest]) -> Callable[..., object]:
    """Create a FastAPI dependency for a form request."""
    async def dependency(request: Request) -> Dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]:
        form_request = form_request_class(request)
        return await form_request.validate()
    
    return dependency


# Usage examples:
# CreateUserData = create_form_request_dependency(CreateUserRequest)
# UpdateUserData = create_form_request_dependency(UpdateUserRequest)
# CreatePostData = create_form_request_dependency(CreatePostRequest)