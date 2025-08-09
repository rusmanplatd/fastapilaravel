"""
Enhanced Blade Form Validation and CSRF System
Provides advanced form handling, validation, and security features
"""
from __future__ import annotations

import hmac
import hashlib
import secrets
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Set, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import re
from urllib.parse import parse_qs


@dataclass
class ValidationRule:
    """Represents a validation rule"""
    rule_type: str
    parameters: List[Any] = field(default_factory=list)
    message: str = ""
    condition: Optional[Callable[..., bool]] = None  # Conditional validation
    
    def __post_init__(self) -> None:
        if not self.message:
            self.message = self._default_message()
    
    def _default_message(self) -> str:
        """Get default validation message"""
        messages = {
            'required': 'The {field} field is required.',
            'email': 'The {field} must be a valid email address.',
            'min': 'The {field} must be at least {0} characters.',
            'max': 'The {field} may not be greater than {0} characters.',
            'numeric': 'The {field} must be a number.',
            'alpha': 'The {field} may only contain letters.',
            'alpha_num': 'The {field} may only contain letters and numbers.',
            'regex': 'The {field} format is invalid.',
            'in': 'The selected {field} is invalid.',
            'unique': 'The {field} has already been taken.',
            'confirmed': 'The {field} confirmation does not match.',
            'date': 'The {field} is not a valid date.',
            'url': 'The {field} format is invalid.',
            'json': 'The {field} must be valid JSON.',
            'file': 'The {field} must be a file.',
            'image': 'The {field} must be an image.',
            'size': 'The {field} must be {0} bytes.',
            'between': 'The {field} must be between {0} and {1}.',
            'different': 'The {field} and {0} must be different.',
            'same': 'The {field} and {0} must match.'
        }
        
        message = messages.get(self.rule_type, 'The {field} is invalid.')
        return message.format(*self.parameters)


class ValidationError(Exception):
    """Validation error exception"""
    
    def __init__(self, field: str, rule: str, message: str):
        self.field = field
        self.rule = rule
        self.message = message
        super().__init__(message)


class FormValidator:
    """Advanced form validation system"""
    
    def __init__(self) -> None:
        self.custom_rules: Dict[str, Callable[..., bool]] = {}
        self.custom_messages: Dict[str, str] = {}
    
    def add_rule(self, name: str, validator: Callable[..., bool], message: str = "") -> None:
        """Add custom validation rule"""
        self.custom_rules[name] = validator
        if message:
            self.custom_messages[name] = message
    
    def validate(self, data: Dict[str, Any], rules: Dict[str, Union[str, List[str], List[ValidationRule]]],
                messages: Optional[Dict[str, str]] = None) -> Tuple[bool, Dict[str, List[str]]]:
        """Validate form data against rules"""
        errors: Dict[str, List[str]] = {}
        messages = messages or {}
        
        for field, field_rules in rules.items():
            field_errors = self._validate_field(field, data.get(field), field_rules, data, messages)
            if field_errors:
                errors[field] = field_errors
        
        return len(errors) == 0, errors
    
    def _validate_field(self, field: str, value: Any, rules: Union[str, List[str], List[ValidationRule]],
                       all_data: Dict[str, Any], messages: Dict[str, str]) -> List[str]:
        """Validate a single field"""
        errors = []
        
        # Convert string rules to ValidationRule objects
        if isinstance(rules, str):
            rules = self._parse_rules_string(rules)
        elif isinstance(rules, list) and rules and isinstance(rules[0], str):
            parsed_rules = []
            for rule in rules:
                if isinstance(rule, str):
                    parsed_rule = self._parse_rule_string(rule)
                    if parsed_rule:
                        parsed_rules.append(parsed_rule)
            rules = parsed_rules
        
        for rule in rules:
            if isinstance(rule, ValidationRule):
                # Check conditional validation
                if rule.condition and not rule.condition(value, all_data):
                    continue
                
                try:
                    self._apply_rule(field, value, rule, all_data)
                except ValidationError as e:
                    # Use custom message if provided
                    custom_key = f"{field}.{rule.rule_type}"
                    message = messages.get(custom_key) or messages.get(rule.rule_type) or e.message
                    errors.append(message.format(field=field.replace('_', ' ').title()))
        
        return errors
    
    def _parse_rules_string(self, rules_string: str) -> List[ValidationRule]:
        """Parse pipe-separated rules string"""
        rules = []
        for rule_str in rules_string.split('|'):
            rule = self._parse_rule_string(rule_str.strip())
            if rule:
                rules.append(rule)
        return rules
    
    def _parse_rule_string(self, rule_string: str) -> Optional[ValidationRule]:
        """Parse single rule string"""
        if ':' in rule_string:
            rule_type, params_str = rule_string.split(':', 1)
            parameters = [p.strip() for p in params_str.split(',')]
        else:
            rule_type = rule_string
            parameters = []
        
        return ValidationRule(rule_type=rule_type, parameters=parameters)
    
    def _apply_rule(self, field: str, value: Any, rule: ValidationRule, all_data: Dict[str, Any]) -> None:
        """Apply a validation rule"""
        rule_type = rule.rule_type
        params = rule.parameters
        
        # Built-in rules
        if rule_type == 'required':
            if value is None or value == '' or (isinstance(value, (list, dict)) and len(value) == 0):
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'email':
            if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'min':
            min_val = int(params[0]) if params else 0
            if value and len(str(value)) < min_val:
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'max':
            max_val = int(params[0]) if params else 0
            if value and len(str(value)) > max_val:
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'numeric':
            if value is not None and value != '':
                try:
                    float(value)
                except (ValueError, TypeError):
                    raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'alpha':
            if value and not re.match(r'^[a-zA-Z]+$', str(value)):
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'alpha_num':
            if value and not re.match(r'^[a-zA-Z0-9]+$', str(value)):
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'regex':
            pattern = params[0] if params else ''
            if value and not re.match(pattern, str(value)):
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'in':
            allowed_values = params
            if value not in allowed_values:
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'confirmed':
            confirmation_field = f"{field}_confirmation"
            if all_data.get(confirmation_field) != value:
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'same':
            other_field = params[0] if params else ''
            if all_data.get(other_field) != value:
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'different':
            other_field = params[0] if params else ''
            if all_data.get(other_field) == value:
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'url':
            if value and not re.match(r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/[^?\s]*)?(?:\?[^#\s]*)?(?:#[^\s]*)?$', str(value)):
                raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'json':
            if value:
                try:
                    json.loads(str(value))
                except (ValueError, TypeError):
                    raise ValidationError(field, rule_type, rule.message)
        
        elif rule_type == 'between':
            if len(params) >= 2:
                between_min: float = float(params[0])
                between_max: float = float(params[1])
                if value is not None:
                    try:
                        num_value = float(value)
                        if not (between_min <= num_value <= between_max):
                            raise ValidationError(field, rule_type, rule.message)
                    except (ValueError, TypeError):
                        raise ValidationError(field, rule_type, rule.message)
        
        # Custom rules
        elif rule_type in self.custom_rules:
            if not self.custom_rules[rule_type](value, params, all_data):
                message = rule.message or self.custom_messages.get(rule_type, 'Validation failed')
                raise ValidationError(field, rule_type, message)


@dataclass
class CSRFToken:
    """CSRF token information"""
    token: str
    created_at: datetime
    expires_at: datetime
    session_id: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now() > self.expires_at
    
    def is_valid_for_session(self, session_id: Optional[str]) -> bool:
        """Check if token is valid for session"""
        return self.session_id == session_id if self.session_id else True


class CSRFProtection:
    """Enhanced CSRF protection system"""
    
    def __init__(self, secret_key: str, token_lifetime: int = 3600):
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.token_lifetime = token_lifetime  # seconds
        self.tokens: Dict[str, CSRFToken] = {}
        self.cleanup_threshold = 1000
    
    def generate_token(self, session_id: Optional[str] = None) -> str:
        """Generate CSRF token"""
        # Clean up old tokens periodically
        if len(self.tokens) > self.cleanup_threshold:
            self._cleanup_expired_tokens()
        
        # Generate random token
        token = secrets.token_urlsafe(32)
        
        # Create token info
        csrf_token = CSRFToken(
            token=token,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.token_lifetime),
            session_id=session_id
        )
        
        # Store token
        self.tokens[token] = csrf_token
        
        return token
    
    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """Validate CSRF token"""
        if not token or token not in self.tokens:
            return False
        
        csrf_token = self.tokens[token]
        
        # Check expiration
        if csrf_token.is_expired():
            del self.tokens[token]
            return False
        
        # Check session binding
        if not csrf_token.is_valid_for_session(session_id):
            return False
        
        return True
    
    def invalidate_token(self, token: str) -> None:
        """Invalidate a specific token"""
        self.tokens.pop(token, None)
    
    def invalidate_session_tokens(self, session_id: str) -> None:
        """Invalidate all tokens for a session"""
        tokens_to_remove = [
            token for token, csrf_token in self.tokens.items()
            if csrf_token.session_id == session_id
        ]
        
        for token in tokens_to_remove:
            del self.tokens[token]
    
    def _cleanup_expired_tokens(self) -> None:
        """Remove expired tokens"""
        now = datetime.now()
        expired_tokens = [
            token for token, csrf_token in self.tokens.items()
            if csrf_token.expires_at <= now
        ]
        
        for token in expired_tokens:
            del self.tokens[token]
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get CSRF token statistics"""
        now = datetime.now()
        active_tokens = sum(1 for t in self.tokens.values() if not t.is_expired())
        expired_tokens = len(self.tokens) - active_tokens
        
        return {
            'total_tokens': len(self.tokens),
            'active_tokens': active_tokens,
            'expired_tokens': expired_tokens,
            'token_lifetime': self.token_lifetime
        }


class FormField:
    """Represents a form field with validation and attributes"""
    
    def __init__(self, name: str, field_type: str = 'text', 
                 value: Any = None, attributes: Optional[Dict[str, Any]] = None,
                 validation_rules: Optional[Union[str, List[str], List[ValidationRule]]] = None,
                 label: Optional[str] = None, help_text: Optional[str] = None):
        self.name = name
        self.field_type = field_type
        self.value = value
        self.attributes = attributes or {}
        self.validation_rules = validation_rules or []
        self.label = label or name.replace('_', ' ').title()
        self.help_text = help_text
        self.errors: List[str] = []
    
    def render_input(self) -> str:
        """Render form input HTML"""
        attrs = dict(self.attributes)
        attrs['name'] = self.name
        attrs['id'] = attrs.get('id', f'field_{self.name}')
        
        if self.value is not None:
            attrs['value'] = self.value
        
        # Add validation classes
        if self.errors:
            attrs['class'] = f"{attrs.get('class', '')} is-invalid".strip()
        
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        
        if self.field_type == 'textarea':
            return f'<textarea {attr_str}>{self.value or ""}</textarea>'
        elif self.field_type == 'select':
            options = attrs.pop('options', [])
            option_html = []
            for option in options:
                if isinstance(option, dict):
                    value = option.get('value', '')
                    text = option.get('text', value)
                    selected = 'selected' if str(value) == str(self.value) else ''
                    option_html.append(f'<option value="{value}" {selected}>{text}</option>')
                else:
                    selected = 'selected' if str(option) == str(self.value) else ''
                    option_html.append(f'<option value="{option}" {selected}>{option}</option>')
            
            return f'<select {attr_str}>{"".join(option_html)}</select>'
        else:
            attrs['type'] = self.field_type
            attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
            return f'<input {attr_str}>'
    
    def render_label(self) -> str:
        """Render field label"""
        required_indicator = ' <span class="required">*</span>' if self._is_required() else ''
        return f'<label for="field_{self.name}">{self.label}{required_indicator}</label>'
    
    def render_errors(self) -> str:
        """Render field errors"""
        if not self.errors:
            return ''
        
        error_items = ''.join(f'<li>{error}</li>' for error in self.errors)
        return f'<ul class="field-errors">{error_items}</ul>'
    
    def render_help(self) -> str:
        """Render help text"""
        if not self.help_text:
            return ''
        return f'<small class="help-text">{self.help_text}</small>'
    
    def _is_required(self) -> bool:
        """Check if field is required"""
        if isinstance(self.validation_rules, str):
            return 'required' in self.validation_rules
        elif isinstance(self.validation_rules, list):
            for rule in self.validation_rules:
                if isinstance(rule, str) and 'required' in rule:
                    return True
                elif isinstance(rule, ValidationRule) and rule.rule_type == 'required':
                    return True
        return False


class BladeFormBuilder:
    """Form builder for Blade templates"""
    
    def __init__(self, csrf_protection: CSRFProtection, validator: FormValidator):
        self.csrf_protection = csrf_protection
        self.validator = validator
        self.fields: Dict[str, FormField] = {}
        self.form_errors: List[str] = []
    
    def add_field(self, field: FormField) -> 'BladeFormBuilder':
        """Add field to form"""
        self.fields[field.name] = field
        return self
    
    def field(self, name: str, field_type: str = 'text', **kwargs: Any) -> 'BladeFormBuilder':
        """Add field using fluent interface"""
        field = FormField(name, field_type, **kwargs)
        return self.add_field(field)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate form data"""
        rules = {}
        messages: Dict[str, str] = {}
        
        for name, field in self.fields.items():
            if field.validation_rules:
                rules[name] = field.validation_rules
        
        is_valid, errors = self.validator.validate(data, rules, messages)
        
        # Assign errors to fields
        for field_name, field_errors in errors.items():
            if field_name in self.fields:
                self.fields[field_name].errors = field_errors
        
        return is_valid
    
    def fill(self, data: Dict[str, Any]) -> 'BladeFormBuilder':
        """Fill form with data"""
        for name, value in data.items():
            if name in self.fields:
                self.fields[name].value = value
        return self
    
    def render_field(self, name: str) -> str:
        """Render a specific field"""
        if name not in self.fields:
            return f'<!-- Field "{name}" not found -->'
        
        field = self.fields[name]
        html_parts = [
            field.render_label(),
            field.render_input(),
            field.render_errors(),
            field.render_help()
        ]
        
        return f'<div class="form-field">{" ".join(html_parts)}</div>'
    
    def render_csrf_token(self, session_id: Optional[str] = None) -> str:
        """Render CSRF token field"""
        token = self.csrf_protection.generate_token(session_id)
        return f'<input type="hidden" name="_token" value="{token}">'
    
    def render_method_field(self, method: str) -> str:
        """Render method override field"""
        return f'<input type="hidden" name="_method" value="{method.upper()}">'


class BladeFormDirectives:
    """Form-related Blade directives"""
    
    def __init__(self, blade_engine: Any, csrf_protection: CSRFProtection, 
                 validator: FormValidator):
        self.blade_engine = blade_engine
        self.csrf_protection = csrf_protection
        self.validator = validator
    
    def register_form_directives(self) -> Dict[str, Callable[..., str]]:
        """Register form directives"""
        return {
            # CSRF directives
            'csrf': self._csrf_directive,
            'csrfToken': self._csrf_token_directive,
            
            # Method override
            'method': self._method_directive,
            
            # Form fields
            'field': self._field_directive,
            'input': self._input_directive,
            'textarea': self._textarea_directive,
            'select': self._select_directive,
            'checkbox': self._checkbox_directive,
            'radio': self._radio_directive,
            
            # Validation
            'error': self._error_directive,
            'errors': self._errors_directive,
            'enderror': self._enderror_directive,
            'old': self._old_directive,
            
            # Form structure
            'form': self._form_directive,
            'endform': self._endform_directive,
            'fieldset': self._fieldset_directive,
            'endfieldset': self._endfieldset_directive,
            
            # Validation helpers
            'validated': self._validated_directive,
            'endvalidated': self._endvalidated_directive,
            'invalid': self._invalid_directive,
            'endinvalid': self._endinvalid_directive
        }
    
    def _csrf_directive(self, content: str) -> str:
        """@csrf directive"""
        return '{{ csrf_field() | safe }}'
    
    def _csrf_token_directive(self, content: str) -> str:
        """@csrfToken directive"""
        return '{{ csrf_token() }}'
    
    def _method_directive(self, content: str) -> str:
        """@method directive"""
        method = content.strip().strip('"\'').upper()
        return f'<input type="hidden" name="_method" value="{method}">'
    
    def _field_directive(self, content: str) -> str:
        """@field directive for form fields"""
        # Parse @field('name', 'text', {'class': 'form-control'})
        parts = [p.strip().strip('"\'') for p in content.split(',')]
        field_name = parts[0] if parts else 'field'
        field_type = parts[1] if len(parts) > 1 else 'text'
        
        return f"{{{{ form_field('{field_name}', '{field_type}') | safe }}}}"
    
    def _input_directive(self, content: str) -> str:
        """@input directive"""
        # Parse @input('name', 'value', {'class': 'form-control'})
        parts = content.split(',', 2)
        name = parts[0].strip().strip('"\'') if parts else 'input'
        value = parts[1].strip().strip('"\'') if len(parts) > 1 else ''
        
        base_attrs = f'name="{name}" id="{name}"'
        if value:
            base_attrs += f' value="{value}"'
            
        return f'<input type="text" {base_attrs} class="{{{{ field_class(\'{name}\') }}}}" value="{{{{ old(\'{name}\', \'{value}\') }}}}">'
    
    def _textarea_directive(self, content: str) -> str:
        """@textarea directive"""
        parts = content.split(',', 2)
        name = parts[0].strip().strip('"\'') if parts else 'textarea'
        value = parts[1].strip().strip('"\'') if len(parts) > 1 else ''
        
        return f'<textarea name="{name}" id="{name}" class="{{{{ field_class(\'{name}\') }}}}">{{{{ old(\'{name}\', \'{value}\') }}</textarea>'
    
    def _select_directive(self, content: str) -> str:
        """@select directive"""
        parts = content.split(',', 3)
        name = parts[0].strip().strip('"\'') if parts else 'select'
        options = parts[1].strip() if len(parts) > 1 else '[]'
        selected = parts[2].strip().strip('"\'') if len(parts) > 2 else ''
        
        return f"""
        <select name="{name}" id="{name}" class="{{{{ field_class('{name}') }}}}">
        {{% for option in {options} %}}
            <option value="{{{{ option.value if option is mapping else option }}}}" 
                    {{{{ 'selected' if (option.value if option is mapping else option) == old('{name}', '{selected}') else '' }}}}>
                {{{{ option.text if option is mapping else option }}}}
            </option>
        {{% endfor %}}
        </select>
        """.strip()
    
    def _checkbox_directive(self, content: str) -> str:
        """@checkbox directive"""
        parts = content.split(',', 3)
        name = parts[0].strip().strip('"\'') if parts else 'checkbox'
        value = parts[1].strip().strip('"\'') if len(parts) > 1 else '1'
        checked = parts[2].strip() if len(parts) > 2 else 'false'
        
        return f'<input type="checkbox" name="{name}" id="{name}" value="{value}" {{{{ "checked" if old(\'{name}\', {checked}) else "" }}}} class="{{{{ field_class(\'{name}\') }}}}">'
    
    def _radio_directive(self, content: str) -> str:
        """@radio directive"""
        parts = content.split(',', 3)
        name = parts[0].strip().strip('"\'') if parts else 'radio'
        value = parts[1].strip().strip('"\'') if len(parts) > 1 else ''
        selected = parts[2].strip().strip('"\'') if len(parts) > 2 else ''
        
        return f'<input type="radio" name="{name}" value="{value}" {{{{ "checked" if old(\'{name}\', \'{selected}\') == \'{value}\' else "" }}}} class="{{{{ field_class(\'{name}\') }}}}">'
    
    def _error_directive(self, content: str) -> str:
        """@error directive"""
        field = content.strip().strip('"\'')
        return f"{{% if errors and '{field}' in errors %}}"
    
    def _errors_directive(self, content: str) -> str:
        """@errors directive to display all errors"""
        if content.strip():
            field = content.strip().strip('"\'')
            return f"{{{{ errors.get('{field}', []) | join('<br>') | safe }}}}"
        else:
            return """
            {% if errors %}
                <div class="alert alert-danger">
                    <ul>
                    {% for field, field_errors in errors.items() %}
                        {% for error in field_errors %}
                            <li>{{ error }}</li>
                        {% endfor %}
                    {% endfor %}
                    </ul>
                </div>
            {% endif %}
            """.strip()
    
    def _enderror_directive(self, content: str) -> str:
        """@enderror directive"""
        return "{% endif %}"
    
    def _old_directive(self, content: str) -> str:
        """@old directive"""
        parts = content.split(',', 2)
        field = parts[0].strip().strip('"\'') if parts else ''
        default = parts[1].strip().strip('"\'') if len(parts) > 1 else ''
        
        return f"{{{{ old('{field}', '{default}') }}}}"
    
    def _form_directive(self, content: str) -> str:
        """@form directive"""
        # Parse form attributes
        attrs = content.strip() if content else ''
        return f'<form {attrs}>'
    
    def _endform_directive(self, content: str) -> str:
        """@endform directive"""
        return '</form>'
    
    def _fieldset_directive(self, content: str) -> str:
        """@fieldset directive"""
        legend = content.strip().strip('"\'') if content else ''
        fieldset_html = '<fieldset>'
        if legend:
            fieldset_html += f'<legend>{legend}</legend>'
        return fieldset_html
    
    def _endfieldset_directive(self, content: str) -> str:
        """@endfieldset directive"""
        return '</fieldset>'
    
    def _validated_directive(self, content: str) -> str:
        """@validated directive - show content if validation passed"""
        return "{% if not errors %}"
    
    def _endvalidated_directive(self, content: str) -> str:
        """@endvalidated directive"""
        return "{% endif %}"
    
    def _invalid_directive(self, content: str) -> str:
        """@invalid directive - show content if validation failed"""
        return "{% if errors %}"
    
    def _endinvalid_directive(self, content: str) -> str:
        """@endinvalid directive"""
        return "{% endif %}"


def add_form_features_to_engine(blade_engine: Any, secret_key: Optional[str] = None) -> Dict[str, Any]:
    """Add form features to Blade engine"""
    
    # Initialize components
    secret_key = secret_key or secrets.token_urlsafe(32)
    csrf_protection = CSRFProtection(secret_key)
    validator = FormValidator()
    
    # Register form directives
    form_directives = BladeFormDirectives(blade_engine, csrf_protection, validator)
    directives = form_directives.register_form_directives()
    
    for name, callback in directives.items():
        blade_engine.directive(name, callback)
    
    # Add form helpers to global context
    def csrf_field() -> str:
        """Generate CSRF field"""
        token = csrf_protection.generate_token()
        return f'<input type="hidden" name="_token" value="{token}">'
    
    def csrf_token() -> str:
        """Generate CSRF token"""
        return csrf_protection.generate_token()
    
    def old(field: str, default: Any = '') -> Any:
        """Get old input value"""
        # This would integrate with session/request in real implementation
        return default
    
    def field_class(field: str, base_class: str = 'form-control') -> str:
        """Get CSS class for field"""
        # This would check for validation errors
        return base_class
    
    def form_field(name: str, field_type: str = 'text') -> str:
        """Render form field"""
        field = FormField(name, field_type)
        return field.render_input()
    
    # Add to engine globals
    blade_engine.env.globals.update({
        'csrf_field': csrf_field,
        'csrf_token': csrf_token,
        'old': old,
        'field_class': field_class,
        'form_field': form_field
    })
    
    # Store components on engine for external access
    blade_engine.csrf_protection = csrf_protection
    blade_engine.form_validator = validator
    
    return {
        'csrf_protection': csrf_protection,
        'validator': validator,
        'form_directives': form_directives
    }