from __future__ import annotations

from typing import Dict, Any, List, Optional, Callable
from fastapi import Request
from pydantic import EmailStr, validator

from .BaseFormRequest import BaseFormRequest


class CreateUserRequest(BaseFormRequest):
    """Enhanced Form request for creating a new user with comprehensive validation."""
    
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    password_confirmation: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    role: Optional[str] = None
    terms_accepted: Optional[bool] = None
    
    def authorize(self) -> bool:
        """Check if user can create users."""
        # Here you would check permissions
        # user = self.request.state.user
        # return user.can('create_users')
        return True
    
    def rules(self) -> Dict[str, Any]:
        """Enhanced validation rules for user creation."""
        return {
            "name": "required|alpha_dash|min:2|max:255",
            "email": "required|email|unique:users,email",
            "password": "required|min:8|regex:^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).*$",
            "password_confirmation": "required|confirmed",
            "phone": "nullable|regex:^\\+?[1-9]\\d{1,14}$",
            "birth_date": "nullable|date|before:today",
            "role": "required|in:admin,user,moderator",
            "terms_accepted": "accepted"
        }
    
    def sometimes_rules(self) -> Dict[str, Any]:
        """Rules that are only applied when the field is present."""
        return {
            "middle_name": "alpha|min:1|max:100",  # Only validate if provided
            "website": "url|active_url",  # Only validate if provided
            "bio": "string|max:1000"  # Only validate if provided
        }
    
    def when_rules(self, condition_field: str, condition_value: Any) -> Dict[str, Any]:
        """Conditional validation rules based on other field values."""
        if condition_field == "role" and condition_value == "admin":
            return {
                "admin_code": "required|alpha_num|size:8",
                "department": "required|in:IT,HR,Finance"
            }
        
        if condition_field == "phone" and condition_value:
            return {
                "phone_verified": "required|boolean"
            }
        
        return {}
    
    def custom_rules(self) -> Dict[str, Callable[[str, Any, Optional[List[str]]], bool]]:
        """Custom validation rules defined as lambda functions."""
        return {
            "strong_password": lambda attr, value, params: (
                len(str(value)) >= 8 and
                any(c.isupper() for c in str(value)) and
                any(c.islower() for c in str(value)) and
                any(c.isdigit() for c in str(value)) and
                any(c in "!@#$%^&*()" for c in str(value))
            ),
            "no_profanity": lambda attr, value, params: (
                not any(word in str(value).lower() for word in ["badword1", "badword2"])
            ),
            "valid_username": lambda attr, value, params: (
                isinstance(value, str) and
                len(value) >= 3 and
                value.replace('_', '').replace('.', '').isalnum() and
                not value.startswith('_') and
                not value.endswith('_')
            )
        }
    
    def messages(self) -> Dict[str, str]:
        """Enhanced custom validation messages."""
        return {
            "name.required": "Please provide your full name.",
            "name.alpha_dash": "Name can only contain letters, numbers, dashes, and underscores.",
            "name.min": "Name must be at least 2 characters long.",
            "name.max": "Name cannot exceed 255 characters.",
            
            "email.required": "Email address is required.",
            "email.email": "Please provide a valid email address.",
            "email.unique": "This email address is already registered.",
            
            "password.required": "Password is required.",
            "password.min": "Password must be at least 8 characters long.",
            "password.regex": "Password must contain uppercase, lowercase, and number.",
            
            "password_confirmation.required": "Please confirm your password.",
            "password_confirmation.confirmed": "Password confirmation does not match.",
            
            "phone.regex": "Please provide a valid phone number in international format.",
            "birth_date.date": "Please provide a valid birth date.",
            "birth_date.before": "Birth date must be in the past.",
            
            "role.required": "Please select a role.",
            "role.in": "Selected role is invalid. Choose from: admin, user, moderator.",
            
            "terms_accepted.accepted": "You must accept the terms and conditions.",
            
            # Custom rule messages
            "password.strong_password": "Password must contain uppercase, lowercase, number, and special character.",
            "name.no_profanity": "Name contains inappropriate language.",
            "name.valid_username": "Username must be at least 3 characters and contain only letters, numbers, dots, and underscores."
        }
    
    def attributes(self) -> Dict[str, str]:
        """Custom attribute names for better error messages."""
        return {
            "password_confirmation": "password confirmation",
            "birth_date": "date of birth",
            "terms_accepted": "terms and conditions",
            "admin_code": "administrator code"
        }
    
    def bail_on_first_failure(self) -> bool:
        """Stop validation on first failure for each field."""
        return False  # Continue validation to show all errors
    
    def stop_on_first_failure(self) -> bool:
        """Stop all validation on first failure."""
        return False  # Show all validation errors
    
    def prepare_for_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data before validation."""
        # Normalize email
        if 'email' in data and data['email']:
            data['email'] = data['email'].lower().strip()
        
        # Normalize name
        if 'name' in data and data['name']:
            data['name'] = ' '.join(data['name'].strip().split())  # Remove extra whitespace
        
        return data
    
    def after_validation(self, data: Dict[str, Any]) -> None:
        """Perform additional validation after basic validation passes."""
        # Additional business logic validation
        if data.get('email') and data['email'].endswith('@tempmail.com'):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Validation failed.",
                    "errors": {"email": ["Temporary email addresses are not allowed."]}
                }
            )
        
        # Check password strength using custom rule
        if data.get('password'):
            custom_rules = self.custom_rules()
            if not custom_rules["strong_password"]("password", data['password'], None):
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "message": "Validation failed.",
                        "errors": {"password": ["Password does not meet security requirements."]}
                    }
                )


class UpdateUserRequest(BaseFormRequest):
    """Form request for updating user information with conditional validation."""
    
    name: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    new_password_confirmation: Optional[str] = None
    
    def authorize(self) -> bool:
        """Check if user can update this profile."""
        return True  # Implement authorization logic
    
    def rules(self) -> Dict[str, Any]:
        """Validation rules that depend on what fields are being updated."""
        base_rules: Dict[str, Any] = {}
        
        # Only validate fields that are present in the request
        return base_rules
    
    def sometimes_rules(self) -> Dict[str, Any]:
        """Rules that apply only when fields are present."""
        return {
            "name": "alpha_dash|min:2|max:255",
            "email": "email|unique:users,email",
        }
    
    def when_rules(self, condition_field: str, condition_value: Any) -> Dict[str, Any]:
        """Conditional rules based on field presence."""
        # If new_password is provided, require current_password and confirmation
        if condition_field == "new_password" and condition_value:
            return {
                "current_password": "required",
                "new_password_confirmation": "required|same:new_password",
                "new_password": "min:8|different:current_password"
            }
        
        return {}
    
    def messages(self) -> Dict[str, str]:
        """Custom messages for update validation."""
        return {
            "current_password.required": "Current password is required to change password.",
            "new_password_confirmation.required": "Please confirm your new password.",
            "new_password_confirmation.same": "New password confirmation does not match.",
            "new_password.different": "New password must be different from current password.",
            "email.unique": "This email address is already in use by another account."
        }