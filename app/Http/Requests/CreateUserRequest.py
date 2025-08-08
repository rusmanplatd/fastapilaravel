from __future__ import annotations

from typing import Dict, Any
from fastapi import Request
from pydantic import EmailStr, validator

from .FormRequest import BaseFormRequest


class CreateUserRequest(BaseFormRequest):
    """Form request for creating a new user."""
    
    name: str
    email: EmailStr
    password: str
    password_confirmation: str
    
    def authorize(self, request: Request) -> bool:
        """Check if user can create users."""
        # Here you would check permissions
        # user = request.state.user
        # return user.can('create_users')
        return True
    
    def rules(self) -> Dict[str, Any]:
        """Validation rules for user creation."""
        return {
            "name": {"min_length": 2, "max_length": 255},
            "email": {"format": "email"},
            "password": {"min_length": 8},
            "password_confirmation": {"must_match": "password"}
        }
    
    def messages(self) -> Dict[str, str]:
        """Custom validation messages."""
        return {
            "name.min_length": "The name must be at least 2 characters.",
            "name.max_length": "The name may not be greater than 255 characters.",
            "email.format": "The email must be a valid email address.",
            "password.min_length": "The password must be at least 8 characters.",
            "password_confirmation.must_match": "The password confirmation does not match."
        }
    
    def attributes(self) -> Dict[str, str]:
        """Custom attribute names."""
        return {
            "password_confirmation": "password confirmation"
        }
    
    @validator('password_confirmation')
    def passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """Ensure password confirmation matches password."""
        if 'password' in values and v != values['password']:
            raise ValueError('Password confirmation does not match')
        return v
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate name field."""
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()