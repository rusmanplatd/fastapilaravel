"""
Enhanced Laravel-style Validation Rules
"""
from __future__ import annotations

import re
import json
import uuid
from typing import Any, List, Optional, Dict, Union
from datetime import datetime
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation

from app.Validation.Validator import ValidationRule


class AlphaRule(ValidationRule):
    """Validate that a field contains only alphabetic characters"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        return value.isalpha()
    
    def message(self) -> str:
        return "The {attribute} field must contain only letters."


class AlphaNumRule(ValidationRule):
    """Validate that a field contains only alphanumeric characters"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        return value.isalnum()
    
    def message(self) -> str:
        return "The {attribute} field must contain only letters and numbers."


class AlphaDashRule(ValidationRule):
    """Validate that a field contains only alphanumeric characters, dashes, and underscores"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        return re.match(r'^[a-zA-Z0-9_-]+$', value) is not None
    
    def message(self) -> str:
        return "The {attribute} field must contain only letters, numbers, dashes, and underscores."


class NumericRule(ValidationRule):
    """Validate that a field is numeric"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if isinstance(value, (int, float)):
            return True
        
        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be numeric."


class IntegerRule(ValidationRule):
    """Validate that a field is an integer"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if isinstance(value, int):
            return True
        
        if isinstance(value, str):
            try:
                int(value)
                return True
            except ValueError:
                return False
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be an integer."


class BooleanRule(ValidationRule):
    """Validate that a field is a boolean"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if isinstance(value, bool):
            return True
        
        if isinstance(value, str):
            return value.lower() in ['true', 'false', '1', '0', 'yes', 'no']
        
        if isinstance(value, int):
            return value in [0, 1]
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be true or false."


class UrlRule(ValidationRule):
    """Validate that a field is a valid URL"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        
        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def message(self) -> str:
        return "The {attribute} field must be a valid URL."


class DateRule(ValidationRule):
    """Validate that a field is a valid date"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if isinstance(value, datetime):
            return True
        
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                # Try common date formats
                formats = [
                    '%Y-%m-%d',
                    '%Y-%m-%d %H:%M:%S',
                    '%m/%d/%Y',
                    '%d/%m/%Y',
                    '%Y/%m/%d'
                ]
                
                for fmt in formats:
                    try:
                        datetime.strptime(value, fmt)
                        return True
                    except ValueError:
                        continue
                
                return False
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be a valid date."


class InRule(ValidationRule):
    """Validate that a field is in a given list of values"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return False
        
        return str(value) in parameters
    
    def message(self) -> str:
        return "The selected {attribute} is invalid."


class NotInRule(ValidationRule):
    """Validate that a field is not in a given list of values"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return True
        
        return str(value) not in parameters
    
    def message(self) -> str:
        return "The selected {attribute} is invalid."


class RegexRule(ValidationRule):
    """Validate that a field matches a regular expression"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or not isinstance(value, str):
            return False
        
        pattern = parameters[0]
        try:
            return re.match(pattern, value) is not None
        except re.error:
            return False
    
    def message(self) -> str:
        return "The {attribute} field format is invalid."


class JsonRule(ValidationRule):
    """Validate that a field is valid JSON"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if isinstance(value, (dict, list)):
            return True
        
        if isinstance(value, str):
            try:
                json.loads(value)
                return True
            except json.JSONDecodeError:
                return False
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be a valid JSON string."


class UuidRule(ValidationRule):
    """Validate that a field is a valid UUID"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def message(self) -> str:
        return "The {attribute} field must be a valid UUID."


class IpRule(ValidationRule):
    """Validate that a field is a valid IP address"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        
        import ipaddress
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
    
    def message(self) -> str:
        return "The {attribute} field must be a valid IP address."


class BetweenRule(ValidationRule):
    """Validate that a field value is between two values"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or len(parameters) < 2:
            return False
        
        try:
            min_val = float(parameters[0])
            max_val = float(parameters[1])
            
            if isinstance(value, str):
                # For strings, check length
                return min_val <= len(value) <= max_val
            elif isinstance(value, (int, float)):
                # For numbers, check value
                return min_val <= value <= max_val
            elif isinstance(value, (list, dict)):
                # For collections, check size
                return min_val <= len(value) <= max_val
            
        except ValueError:
            pass
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be between {min} and {max}."


class SizeRule(ValidationRule):
    """Validate that a field has an exact size"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return False
        
        try:
            size = int(parameters[0])
            
            if isinstance(value, str):
                return len(value) == size
            elif isinstance(value, (int, float)):
                return value == size
            elif isinstance(value, (list, dict)):
                return len(value) == size
            
        except ValueError:
            pass
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be {size}."


class DigitsRule(ValidationRule):
    """Validate that a field has an exact number of digits"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return False
        
        try:
            digits = int(parameters[0])
            value_str = str(value)
            
            if not value_str.isdigit():
                return False
            
            return len(value_str) == digits
            
        except ValueError:
            pass
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must be {digits} digits."


class DigitsBetweenRule(ValidationRule):
    """Validate that a field has a number of digits between two values"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or len(parameters) < 2:
            return False
        
        try:
            min_digits = int(parameters[0])
            max_digits = int(parameters[1])
            value_str = str(value)
            
            if not value_str.isdigit():
                return False
            
            digit_count = len(value_str)
            return min_digits <= digit_count <= max_digits
            
        except ValueError:
            pass
        
        return False
    
    def message(self) -> str:
        return "The {attribute} field must have between {min} and {max} digits."


class DecimalRule(ValidationRule):
    """Validate that a field has at most X digits in total and Y digits after decimal point"""
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters:
            return False
        
        try:
            max_digits = int(parameters[0])
            decimal_places = int(parameters[1]) if len(parameters) > 1 else 0
            
            decimal_value = Decimal(str(value))
            sign, digits, exponent = decimal_value.as_tuple()
            
            # Total digits
            total_digits = len(digits)
            if total_digits > max_digits:
                return False
            
            # Decimal places
            decimal_places_count = max(0, -exponent)
            return decimal_places_count <= decimal_places
            
        except (ValueError, InvalidOperation):
            return False
    
    def message(self) -> str:
        return "The {attribute} field must be a decimal with at most {max_digits} total digits and {decimal_places} decimal places."


class ConfirmedRule(ValidationRule):
    """Validate that a field has a matching confirmation field"""
    
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set validation data"""
        self.data = data
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not self.data:
            return False
        
        confirmation_field = f"{attribute}_confirmation"
        confirmation_value = self.data.get(confirmation_field)
        
        return value == confirmation_value
    
    def message(self) -> str:
        return "The {attribute} confirmation does not match."


class DifferentRule(ValidationRule):
    """Validate that a field has a different value from another field"""
    
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set validation data"""
        self.data = data
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or not self.data:
            return False
        
        other_field = parameters[0]
        other_value = self.data.get(other_field)
        
        return value != other_value
    
    def message(self) -> str:
        return "The {attribute} and {other} must be different."


class SameRule(ValidationRule):
    """Validate that a field has the same value as another field"""
    
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set validation data"""
        self.data = data
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or not self.data:
            return False
        
        other_field = parameters[0]
        other_value = self.data.get(other_field)
        
        return value == other_value
    
    def message(self) -> str:
        return "The {attribute} and {other} must match."


class RequiredIfRule(ValidationRule):
    """Validate that a field is required if another field has a specific value"""
    
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set validation data"""
        self.data = data
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or len(parameters) < 2 or not self.data:
            return True  # No validation if parameters are missing
        
        other_field = parameters[0]
        other_value = parameters[1]
        actual_other_value = self.data.get(other_field)
        
        # If the condition is not met, validation passes
        if str(actual_other_value) != other_value:
            return True
        
        # If condition is met, field is required
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        
        return True
    
    def message(self) -> str:
        return "The {attribute} field is required when {other} is {value}."


class RequiredUnlessRule(ValidationRule):
    """Validate that a field is required unless another field has a specific value"""
    
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set validation data"""
        self.data = data
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not parameters or len(parameters) < 2 or not self.data:
            return True
        
        other_field = parameters[0]
        other_value = parameters[1]
        actual_other_value = self.data.get(other_field)
        
        # If the condition is met, validation passes (field not required)
        if str(actual_other_value) == other_value:
            return True
        
        # If condition is not met, field is required
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        
        return True
    
    def message(self) -> str:
        return "The {attribute} field is required unless {other} is {value}."