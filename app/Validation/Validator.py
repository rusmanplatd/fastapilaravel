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
        self.bail_on_first_failure = False
        self.stop_on_first_failure = False
        
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
        """Validate the data."""
        self.errors = {}
        
        for field, field_rules in self.rules.items():
            value = self.data.get(field)
            field_has_error = False
            
            # Convert rules to list
            if isinstance(field_rules, str):
                rule_list = [rule.strip() for rule in field_rules.split('|')]
            else:
                rule_list = field_rules
            
            # Handle nullable rule specially
            is_nullable = 'nullable' in rule_list
            if is_nullable and (value is None or value == ''):
                continue  # Skip validation for nullable empty fields
            
            for rule_str in rule_list:
                if rule_str == 'nullable':
                    continue  # Skip nullable rule, already handled
                
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
                    
                    if self.bail_on_first_failure or self.stop_on_first_failure:
                        break
            
            # Break outer loop if stop_on_first_failure is enabled and we have an error
            if self.stop_on_first_failure and field_has_error:
                break
        
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


def make_validator(data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]], messages: Optional[Dict[str, str]] = None) -> Validator:
    """Create a validator instance."""
    return Validator(data, rules, messages)