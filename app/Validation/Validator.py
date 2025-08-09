from __future__ import annotations

from typing import Any, Dict, List, Callable, Optional, Union, Type, cast, overload, Literal
from abc import ABC, abstractmethod
import re
from datetime import datetime, date
from decimal import Decimal
from functools import wraps

from app.Support.Types import T, validate_types, TypeConstants
from app.Support.ServiceContainer import container
from app.Models.BaseModel import BaseModel


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


class ValidationException(Exception):
    """Laravel 12 validation exception."""
    
    def __init__(self, errors: Dict[str, List[str]], message: str = "The given data was invalid.") -> None:
        self.errors = errors
        self.message = message
        super().__init__(message)
    
    def get_errors(self) -> Dict[str, List[str]]:
        """Get validation errors."""
        return self.errors
    
    def get_first_error(self, field: Optional[str] = None) -> Optional[str]:
        """Get first error message."""
        if field and field in self.errors:
            return self.errors[field][0] if self.errors[field] else None
        
        for field_errors in self.errors.values():
            if field_errors:
                return field_errors[0]
        
        return None


class Validator:
    """Laravel 12 enhanced validator."""
    
    def __init__(self, data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None, attributes: Optional[Dict[str, str]] = None) -> None:
        self.data = data
        self.rules = rules
        self.custom_messages = messages or {}
        self.custom_attributes = attributes or {}
        self.errors: Dict[str, List[str]] = {}
        self.bail_on_first_failure = False
        self.stop_on_first_failure = False
        self.implicit_rules = ['required', 'accepted', 'present']
        self.dependent_rules = ['required_if', 'required_unless', 'required_with', 'required_without']
        self.exclude_rules = ['exclude', 'exclude_if', 'exclude_unless']
        self.validated_data: Dict[str, Any] = {}
        self.invalid_data: Dict[str, Any] = {}
        self.after_validation_hooks: List[Callable[[Validator], None]] = []
        
        # Built-in rules
        self.rule_classes = {
            'required': RequiredRule(),
            'email': EmailRule(),
            'min': MinRule(),
            'max': MaxRule(),
            'unique': UniqueRule(),
        }
        
        # Load enhanced rules
        self._load_enhanced_rules()
        
        # Load additional rules
        self._load_additional_rules()
    
    def validate(self) -> Dict[str, Any]:
        """Validate the data with Laravel 12 enhancements."""
        self.errors = {}
        self.validated_data = {}
        self.invalid_data = {}
        
        # First pass: handle implicit rules
        self._validate_implicit_rules()
        
        # Second pass: validate all other rules
        for field, field_rules in self.rules.items():
            if field in self.errors:
                continue  # Skip if already has errors from implicit validation
            
            value = self.data.get(field)
            field_has_error = False
            
            # Convert rules to list
            if isinstance(field_rules, str):
                rule_list = [rule.strip() for rule in field_rules.split('|')]
            else:
                rule_list = field_rules
            
            # Check for exclude rules first
            if self._should_exclude_field(field, rule_list):
                continue
            
            # Handle nullable rule specially
            is_nullable = 'nullable' in rule_list
            if is_nullable and (value is None or value == ''):
                self.validated_data[field] = value
                continue  # Skip validation for nullable empty fields
            
            # Check if field is required by other rules
            is_required = self._is_field_required(field, rule_list)
            
            # Skip non-required empty fields
            if not is_required and (value is None or (isinstance(value, str) and value.strip() == '')):
                continue
            
            for rule_str in rule_list:
                if rule_str in ['nullable'] + self.implicit_rules + self.exclude_rules:
                    continue  # Skip already handled rules
                
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
                try:
                    if not rule.passes(field, value, parameters):
                        error_message = self._get_error_message(field, rule_name, rule, parameters)
                        
                        if field not in self.errors:
                            self.errors[field] = []
                        self.errors[field].append(error_message)
                        field_has_error = True
                        
                        # Add to invalid data
                        self.invalid_data[field] = value
                        
                        # Stop on first failure for this field if bail is enabled
                        if self.bail_on_first_failure:
                            break
                        
                        # Stop all validation if stop_on_first_failure is enabled
                        if self.stop_on_first_failure:
                            break
                
                except Exception as e:
                    # Handle rule execution errors gracefully
                    error_message = f"Validation error for {field}: {str(e)}"
                    if field not in self.errors:
                        self.errors[field] = []
                    self.errors[field].append(error_message)
                    field_has_error = True
                    self.invalid_data[field] = value
                    
                    if self.bail_on_first_failure or self.stop_on_first_failure:
                        break
            
            # Add to validated data if no errors
            if not field_has_error:
                self.validated_data[field] = value
            
            # Break outer loop if stop_on_first_failure is enabled and we have an error
            if self.stop_on_first_failure and field_has_error:
                break
        
        # Run after validation hooks
        for hook in self.after_validation_hooks:
            hook(self)
        
        if self.errors:
            raise ValidationException(self.errors, "The given data was invalid.")
        
        return self.validated_data
    
    def _validate_implicit_rules(self) -> None:
        """Validate implicit rules that must run first."""
        for field, field_rules in self.rules.items():
            if isinstance(field_rules, str):
                rule_list = [rule.strip() for rule in field_rules.split('|')]
            else:
                rule_list = field_rules
            
            for rule_str in rule_list:
                if ':' in rule_str:
                    rule_name, params_str = rule_str.split(':', 1)
                    parameters = [p.strip() for p in params_str.split(',')]
                else:
                    rule_name = rule_str
                    parameters = []
                
                if rule_name in self.implicit_rules + self.dependent_rules:
                    rule = self.rule_classes.get(rule_name)
                    if rule:
                        value = self.data.get(field)
                        if not rule.passes(field, value, parameters):
                            error_message = self._get_error_message(field, rule_name, rule, parameters)
                            if field not in self.errors:
                                self.errors[field] = []
                            self.errors[field].append(error_message)
                            self.invalid_data[field] = value
    
    def _should_exclude_field(self, field: str, rule_list: List[str]) -> bool:
        """Check if field should be excluded from validation."""
        for rule_str in rule_list:
            if ':' in rule_str:
                rule_name, params_str = rule_str.split(':', 1)
                parameters = [p.strip() for p in params_str.split(',')]
            else:
                rule_name = rule_str
                parameters = []
            
            if rule_name in self.exclude_rules:
                rule = self.rule_classes.get(rule_name)
                if rule and rule.passes(field, self.data.get(field), parameters):
                    return True
        
        return False
    
    def _is_field_required(self, field: str, rule_list: List[str]) -> bool:
        """Check if field is required by any rule."""
        for rule_str in rule_list:
            rule_name = rule_str.split(':')[0]
            if rule_name in self.implicit_rules + self.dependent_rules:
                return True
        return False
    
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
        if not self.validated_data:
            self.validate()
        return self.validated_data
    
    def safe(self) -> Dict[str, Any]:
        """Get safe validated data (doesn't throw exception)."""
        try:
            return self.validated()
        except ValidationException:
            return self.validated_data
    
    def invalid(self) -> Dict[str, Any]:
        """Get invalid data."""
        return self.invalid_data
    
    def get_message_bag(self) -> Dict[str, List[str]]:
        """Get error message bag."""
        return self.errors
    
    def sometimes(self, field: str, rules: Union[str, List[str]], callback: Callable[[Dict[str, Any]], bool]) -> 'Validator':
        """Conditionally add rules."""
        if callback(self.data):
            self.rules[field] = rules
        return self
    
    def after(self, callback: Callable[['Validator'], None]) -> 'Validator':
        """Add after validation hook."""
        self.after_validation_hooks.append(callback)
        return self
    
    def stop_on_first_failure(self, stop: bool = True) -> 'Validator':
        """Stop validation on first failure."""
        self.stop_on_first_failure = stop
        return self
    
    def bail(self, bail: bool = True) -> 'Validator':
        """Bail on first failure for each field."""
        self.bail_on_first_failure = bail
        return self
    
    def get_attribute_name(self, field: str) -> str:
        """Get human-readable attribute name."""
        return self.custom_attributes.get(field, field.replace('_', ' '))
    
    def merge_rules(self, rules: Dict[str, Union[str, List[str]]]) -> 'Validator':
        """Merge additional rules."""
        for field, field_rules in rules.items():
            if field in self.rules:
                existing = self.rules[field]
                if isinstance(existing, str) and isinstance(field_rules, str):
                    self.rules[field] = f"{existing}|{field_rules}"
                elif isinstance(existing, list) and isinstance(field_rules, list):
                    self.rules[field] = existing + field_rules
                else:
                    # Convert to list and merge
                    existing_list = existing.split('|') if isinstance(existing, str) else existing
                    new_list = field_rules.split('|') if isinstance(field_rules, str) else field_rules
                    self.rules[field] = existing_list + new_list
            else:
                self.rules[field] = field_rules
        return self
    
    def replace_rules(self, rules: Dict[str, Union[str, List[str]]]) -> 'Validator':
        """Replace rules entirely."""
        self.rules.update(rules)
        return self
    
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
        
        # Replace rule-specific placeholders
        if parameters:
            # Replace common placeholders
            if rule_name in ['min', 'max', 'between', 'size', 'digits', 'digits_between']:
                if rule_name == 'min':
                    message = message.replace('{min}', parameters[0])
                elif rule_name == 'max':
                    message = message.replace('{max}', parameters[0])
                elif rule_name == 'between':
                    message = message.replace('{min}', parameters[0]).replace('{max}', parameters[1] if len(parameters) > 1 else '')
                elif rule_name == 'size':
                    message = message.replace('{size}', parameters[0])
                elif rule_name == 'digits':
                    message = message.replace('{digits}', parameters[0])
                elif rule_name == 'digits_between':
                    message = message.replace('{min}', parameters[0]).replace('{max}', parameters[1] if len(parameters) > 1 else '')
            
            # Replace parameter placeholders
            for i, param in enumerate(parameters):
                message = message.replace(f'{{param{i}}}', param)
                message = message.replace(f'{{{rule_name}}}', param)
            
            # Handle special cases for some rules
            if rule_name in ['in', 'not_in', 'ends_with', 'starts_with', 'doesnt_end_with', 'doesnt_start_with']:
                values_str = ', '.join(parameters)
                message = message.replace('{values}', values_str)
            
            if rule_name in ['required_if', 'required_unless']:
                if len(parameters) >= 2:
                    message = message.replace('{other}', parameters[0]).replace('{value}', parameters[1])
            
            if rule_name in ['required_with', 'required_without']:
                fields_str = ', '.join(parameters)
                message = message.replace('{fields}', fields_str)
            
            if rule_name in ['after', 'before']:
                message = message.replace('{date}', parameters[0])
            
            if rule_name == 'decimal':
                if len(parameters) >= 2:
                    message = message.replace('{max_digits}', parameters[0]).replace('{decimal_places}', parameters[1])
        
        return message
    
    def _load_enhanced_rules(self) -> None:
        """Load enhanced validation rules"""
        from app.Validation.Rules import (
            AlphaRule, AlphaNumRule, AlphaDashRule, NumericRule, IntegerRule,
            BooleanRule, UrlRule, DateRule, InRule, NotInRule, RegexRule,
            JsonRule, UuidRule, IpRule, BetweenRule, SizeRule, DigitsRule,
            DigitsBetweenRule, DecimalRule, ConfirmedRule, DifferentRule,
            SameRule, RequiredIfRule, RequiredUnlessRule
        )
        
        enhanced_rules = {
            'alpha': AlphaRule(),
            'alpha_num': AlphaNumRule(),
            'alpha_dash': AlphaDashRule(),
            'numeric': NumericRule(),
            'integer': IntegerRule(),
            'boolean': BooleanRule(),
            'url': UrlRule(),
            'date': DateRule(),
            'in': InRule(),
            'not_in': NotInRule(),
            'regex': RegexRule(),
            'json': JsonRule(),
            'uuid': UuidRule(),
            'ip': IpRule(),
            'between': BetweenRule(),
            'size': SizeRule(),
            'digits': DigitsRule(),
            'digits_between': DigitsBetweenRule(),
            'decimal': DecimalRule(),
            'confirmed': ConfirmedRule(),
            'different': DifferentRule(),
            'same': SameRule(),
            'required_if': RequiredIfRule(),
            'required_unless': RequiredUnlessRule(),
        }
        
        self.rule_classes.update(enhanced_rules)
        
        # Set data for rules that need it
        for rule in self.rule_classes.values():
            if hasattr(rule, 'set_data'):
                rule.set_data(self.data)
    
    def _load_additional_rules(self) -> None:
        """Load additional validation rules"""
        from app.Validation.Rules import (
            NullableRule, PresentRule, AcceptedRule, DeclinedRule, ActiveUrlRule,
            AfterDateRule, BeforeDateRule, EndsWithRule, StartsWithRule,
            DoesntEndWithRule, DoesntStartWithRule, RequiredWithRule, RequiredWithoutRule
        )
        
        additional_rules = {
            'nullable': NullableRule(),
            'present': PresentRule(),
            'accepted': AcceptedRule(),
            'declined': DeclinedRule(),
            'active_url': ActiveUrlRule(),
            'after': AfterDateRule(),
            'before': BeforeDateRule(),
            'ends_with': EndsWithRule(),
            'starts_with': StartsWithRule(),
            'doesnt_end_with': DoesntEndWithRule(),
            'doesnt_start_with': DoesntStartWithRule(),
            'required_with': RequiredWithRule(),
            'required_without': RequiredWithoutRule(),
        }
        
        self.rule_classes.update(additional_rules)
        
        # Set data for rules that need it
        for rule in self.rule_classes.values():
            if hasattr(rule, 'set_data'):
                rule.set_data(self.data)
    
    def add_custom_rule(self, name: str, rule_func: Callable[[str, Any, Optional[List[str]]], bool], message: str = "The {attribute} field is invalid.") -> None:
        """Add a custom validation rule."""
        from app.Http.Requests.FormRequest import CustomRuleWrapper  # type: ignore
        
        custom_rule = CustomRuleWrapper(rule_func, message)
        self.rule_classes[name] = custom_rule
    
    def extend_rule(self, name: str, rule: ValidationRule) -> None:
        """Extend validator with a new rule instance."""
        self.rule_classes[name] = rule
        if hasattr(rule, 'set_data'):
            rule.set_data(self.data)


def make_validator(data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None, attributes: Optional[Dict[str, str]] = None) -> Validator:
    """Create a validator instance."""
    return Validator(data, rules, messages, attributes)


@validate_types
def validate(data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None, attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Validate data and return validated data."""
    validator = Validator(data, rules, messages, attributes)
    return validator.validated()


@validate_types
def validate_or_fail(data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None, attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Validate data or raise ValidationException."""
    validator = Validator(data, rules, messages, attributes)
    return validator.validated()


def sometimes(data: Dict[str, Any], field: str, rules: Union[str, List[str]], callback: Callable[[Dict[str, Any]], bool]) -> bool:
    """Check if field should be validated based on condition."""
    return callback(data)


# Laravel 12 Validation Decorators
def validates_data(rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None, attributes: Optional[Dict[str, str]] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for validating function parameters."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract data from kwargs
            data = kwargs.get('data', {})
            if not data and args:
                # Try to extract from first argument if it's a dict
                if isinstance(args[0], dict):
                    data = args[0]
            
            # Validate data
            validator = Validator(data, rules, messages, attributes)
            validated_data = validator.validated()
            
            # Replace data with validated data
            if 'data' in kwargs:
                kwargs['data'] = validated_data
            elif args and isinstance(args[0], dict):
                args = (validated_data,) + args[1:]
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validates_request() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for validating FastAPI requests."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # This would integrate with FastAPI request validation
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def bail_on_first_failure(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to bail on first validation failure."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # This would modify validation behavior
        return func(*args, **kwargs)
    
    return wrapper


# Export Laravel 12 validation functionality
__all__ = [
    'ValidationRule',
    'RequiredRule',
    'EmailRule',
    'MinRule',
    'MaxRule',
    'UniqueRule',
    'Validator',
    'ValidationException',
    'make_validator',
    'validate',
    'validate_or_fail',
    'sometimes',
    'validates_data',
    'validates_request',
    'bail_on_first_failure',
]