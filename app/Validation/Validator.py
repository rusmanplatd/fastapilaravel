from __future__ import annotations

from typing import Any, Dict, List, Callable, Optional, Union
from abc import ABC, abstractmethod
import re
from datetime import datetime


class ValidationRule(ABC):
    """Base validation rule."""
    
    @abstractmethod
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        """Determine if the validation rule passes."""
        pass
    
    @abstractmethod
    def message(self) -> str:
        """Get the validation error message."""
        pass


class RequiredRule(ValidationRule):
    """Required validation rule."""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True
    
    def message(self) -> str:
        return "The {attribute} field is required."


class EmailRule(ValidationRule):
    """Email validation rule."""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, value) is not None
    
    def message(self) -> str:
        return "The {attribute} must be a valid email address."


class MinRule(ValidationRule):
    """Minimum length/value validation rule."""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return False
        
        min_value = int(parameters[0])
        
        if isinstance(value, str):
            return len(value) >= min_value
        elif isinstance(value, (int, float)):
            return value >= min_value
        elif isinstance(value, (list, dict)):
            return len(value) >= min_value
        
        return False
    
    def message(self) -> str:
        return "The {attribute} must be at least {min} characters."


class MaxRule(ValidationRule):
    """Maximum length/value validation rule."""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return False
        
        max_value = int(parameters[0])
        
        if isinstance(value, str):
            return len(value) <= max_value
        elif isinstance(value, (int, float)):
            return value <= max_value
        elif isinstance(value, (list, dict)):
            return len(value) <= max_value
        
        return False
    
    def message(self) -> str:
        return "The {attribute} may not be greater than {max} characters."


class UniqueRule(ValidationRule):
    """Unique validation rule (simplified)."""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        # This would need database integration to check uniqueness
        # For now, just return True
        return True
    
    def message(self) -> str:
        return "The {attribute} has already been taken."


class Validator:
    """Laravel-style validator."""
    
    def __init__(self, data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None) -> None:
        self.data = data
        self.rules = rules
        self.custom_messages = messages or {}
        self.errors: Dict[str, List[str]] = {}
        
        # Built-in rules
        self.rule_classes = {
            'required': RequiredRule(),
            'email': EmailRule(),
            'min': MinRule(),
            'max': MaxRule(),
            'unique': UniqueRule(),
        }
    
    def validate(self) -> Dict[str, Any]:
        """Validate the data."""
        self.errors = {}
        
        for field, field_rules in self.rules.items():
            value = self.data.get(field)
            
            # Convert rules to list
            if isinstance(field_rules, str):
                rule_list = [rule.strip() for rule in field_rules.split('|')]
            else:
                rule_list = field_rules
            
            for rule_str in rule_list:
                # Parse rule and parameters
                if ':' in rule_str:
                    rule_name, params_str = rule_str.split(':', 1)
                    parameters = [p.strip() for p in params_str.split(',')]
                else:
                    rule_name = rule_str
                    parameters = []
                
                # Get rule instance
                rule = self.rule_classes.get(rule_name)
                if not rule:
                    continue
                
                # Validate
                if not rule.passes(field, value, parameters):
                    error_message = self._get_error_message(field, rule_name, rule, parameters)
                    
                    if field not in self.errors:
                        self.errors[field] = []
                    self.errors[field].append(error_message)
        
        if self.errors:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "The given data was invalid.",
                    "errors": self.errors
                }
            )
        
        return self.data
    
    def fails(self) -> bool:
        """Check if validation fails."""
        try:
            self.validate()
            return False
        except Exception:
            return True
    
    def passes(self) -> bool:
        """Check if validation passes."""
        return not self.fails()
    
    def validated(self) -> Dict[str, Any]:
        """Get validated data."""
        self.validate()
        return {k: v for k, v in self.data.items() if k in self.rules}
    
    def _get_error_message(self, field: str, rule_name: str, rule: ValidationRule, parameters: List[str]) -> str:
        """Get error message for a failed rule."""
        # Check for custom message
        custom_key = f"{field}.{rule_name}"
        if custom_key in self.custom_messages:
            message = self.custom_messages[custom_key]
        else:
            message = rule.message()
        
        # Replace placeholders
        message = message.replace('{attribute}', field)
        if parameters:
            for i, param in enumerate(parameters):
                message = message.replace(f'{{{rule_name}}}', param)
                message = message.replace(f'{{param{i}}}', param)
        
        return message


def make_validator(data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None) -> Validator:
    """Create a validator instance."""
    return Validator(data, rules, messages)