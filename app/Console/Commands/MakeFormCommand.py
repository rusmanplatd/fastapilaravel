from __future__ import annotations

from pathlib import Path
from typing import Optional
from ..Command import Command


class MakeFormCommand(Command):
    """Generate a new form class."""
    
    signature = "make:form {name : The name of the form} {--model= : The model to bind to the form}"
    description = "Create a new form class"
    help = "Generate a new form class for handling form data, validation, and rendering"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        model_name = self.option("model")
        
        if not name:
            self.error("Form name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Form"):
            name += "Form"
        
        form_path = Path(f"app/Forms/{name}.py")
        form_path.parent.mkdir(parents=True, exist_ok=True)
        
        if form_path.exists():
            if not self.confirm(f"Form {name} already exists. Overwrite?"):
                self.info("Form creation cancelled.")
                return
        
        content = self._generate_form_content(name, model_name)
        form_path.write_text(content)
        
        self.info(f"✅ Form created: {form_path}")
        self.comment("Update the form fields, validation rules, and rendering methods")
        if model_name:
            self.comment(f"Form configured for {model_name} model")
    
    def _generate_form_content(self, form_name: str, model_name: Optional[str] = None) -> str:
        """Generate form content."""
        model_import = ""
        model_hint = "Any"
        
        if model_name:
            model_import = f"from app.Models.{model_name} import {model_name}"
            model_hint = model_name
        
        return f'''from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Type
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, validator, ValidationError
from fastapi import Form, File, UploadFile
{model_import}


class {form_name}:
    """Form class for handling form data, validation, and rendering."""
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, instance: Optional[{model_hint}] = None):
        """Initialize the form."""
        self.data = data or {{}}
        self.instance = instance
        self.errors: Dict[str, List[str]] = {{}}
        self.cleaned_data: Dict[str, Any] = {{}}
        self.is_bound = bool(data)
        self.is_valid_cached: Optional[bool] = None
        
        # Form configuration
        self.fields = self._get_fields()
        self.field_order = self._get_field_order()
        self.css_classes = self._get_css_classes()
        
        # Initialize form with instance data if provided
        if instance and not self.is_bound:
            self._populate_from_instance()
    
    def _get_fields(self) -> Dict[str, Dict[str, Any]]:
        """Define form fields and their configurations."""
        return {{
            # Example field definitions:
            # "name": {{
            #     "type": "text",
            #     "required": True,
            #     "max_length": 100,
            #     "label": "Full Name",
            #     "help_text": "Enter your full name",
            #     "placeholder": "John Doe"
            # }},
            # "email": {{
            #     "type": "email",
            #     "required": True,
            #     "label": "Email Address",
            #     "validators": [self._validate_email_domain]
            # }},
            # "age": {{
            #     "type": "number",
            #     "required": False,
            #     "min_value": 18,
            #     "max_value": 120,
            #     "label": "Age"
            # }},
            # "bio": {{
            #     "type": "textarea",
            #     "required": False,
            #     "max_length": 500,
            #     "label": "Biography",
            #     "rows": 4
            # }},
            # "is_active": {{
            #     "type": "checkbox",
            #     "required": False,
            #     "label": "Active Status",
            #     "default": True
            # }},
            # "category": {{
            #     "type": "select",
            #     "required": True,
            #     "choices": [
            #         ("personal", "Personal"),
            #         ("business", "Business"),
            #         ("other", "Other")
            #     ],
            #     "label": "Category"
            # }},
            # "avatar": {{
            #     "type": "file",
            #     "required": False,
            #     "accept": "image/*",
            #     "label": "Avatar Image"
            # }}
        }}
    
    def _get_field_order(self) -> List[str]:
        """Define the order of fields for rendering."""
        return list(self.fields.keys())
    
    def _get_css_classes(self) -> Dict[str, str]:
        """Define CSS classes for form elements."""
        return {{
            "form": "form",
            "field": "field",
            "label": "field-label",
            "input": "field-input",
            "error": "field-error",
            "help": "field-help"
        }}
    
    def _populate_from_instance(self) -> None:
        """Populate form data from model instance."""
        if not self.instance:
            return
        
        for field_name in self.fields.keys():
            if hasattr(self.instance, field_name):
                value = getattr(self.instance, field_name)
                self.data[field_name] = self._serialize_value(value)
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for form input."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, Enum):
            return value.value
        else:
            return value
    
    def is_valid(self) -> bool:
        """Check if form data is valid."""
        if not self.is_bound:
            return False
        
        if self.is_valid_cached is not None:
            return self.is_valid_cached
        
        self.errors.clear()
        self.cleaned_data.clear()
        
        # Validate each field
        for field_name, field_config in self.fields.items():
            try:
                value = self._validate_field(field_name, field_config)
                self.cleaned_data[field_name] = value
            except ValidationError as e:
                self._add_field_error(field_name, str(e))
        
        # Run form-level validation
        try:
            self._clean()
        except ValidationError as e:
            self._add_form_error(str(e))
        
        self.is_valid_cached = len(self.errors) == 0
        return self.is_valid_cached
    
    def _validate_field(self, field_name: str, field_config: Dict[str, Any]) -> Any:
        """Validate a single field."""
        value = self.data.get(field_name)
        field_type = field_config.get("type", "text")
        required = field_config.get("required", False)
        
        # Check required fields
        if required and (value is None or value == ""):
            raise ValidationError(f"{{field_config.get('label', field_name)}} is required")
        
        # Skip validation for empty optional fields
        if not required and (value is None or value == ""):
            return None
        
        # Type-specific validation
        if field_type == "email":
            return self._validate_email(value, field_config)
        elif field_type == "number":
            return self._validate_number(value, field_config)
        elif field_type == "text" or field_type == "textarea":
            return self._validate_text(value, field_config)
        elif field_type == "checkbox":
            return self._validate_boolean(value, field_config)
        elif field_type == "select":
            return self._validate_choice(value, field_config)
        elif field_type == "file":
            return self._validate_file(value, field_config)
        else:
            return value
    
    def _validate_email(self, value: str, config: Dict[str, Any]) -> str:
        """Validate email field."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
        
        if not re.match(email_pattern, str(value)):
            raise ValidationError("Enter a valid email address")
        
        # Custom validators
        validators = config.get("validators", [])
        for validator in validators:
            validator(value)
        
        return str(value).lower()
    
    def _validate_number(self, value: Any, config: Dict[str, Any]) -> Union[int, float]:
        """Validate number field."""
        try:
            if isinstance(value, str) and '.' in value:
                num_value = float(value)
            else:
                num_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError("Enter a valid number")
        
        min_value = config.get("min_value")
        max_value = config.get("max_value")
        
        if min_value is not None and num_value < min_value:
            raise ValidationError(f"Value must be at least {{min_value}}")
        
        if max_value is not None and num_value > max_value:
            raise ValidationError(f"Value must be no more than {{max_value}}")
        
        return num_value
    
    def _validate_text(self, value: str, config: Dict[str, Any]) -> str:
        """Validate text field."""
        text_value = str(value).strip()
        
        min_length = config.get("min_length", 0)
        max_length = config.get("max_length")
        
        if len(text_value) < min_length:
            raise ValidationError(f"Text must be at least {{min_length}} characters")
        
        if max_length and len(text_value) > max_length:
            raise ValidationError(f"Text must be no more than {{max_length}} characters")
        
        return text_value
    
    def _validate_boolean(self, value: Any, config: Dict[str, Any]) -> bool:
        """Validate boolean/checkbox field."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        else:
            return bool(value)
    
    def _validate_choice(self, value: str, config: Dict[str, Any]) -> str:
        """Validate select/choice field."""
        choices = config.get("choices", [])
        valid_choices = [choice[0] for choice in choices]
        
        if value not in valid_choices:
            raise ValidationError(f"Select a valid choice. {{value}} is not one of the available choices.")
        
        return value
    
    def _validate_file(self, value: Any, config: Dict[str, Any]) -> Any:
        """Validate file field."""
        if isinstance(value, UploadFile):
            # Validate file type if specified
            accept = config.get("accept")
            if accept and value.content_type:
                # Simple content type validation
                if not any(value.content_type.startswith(t.strip().replace("*", "")) 
                          for t in accept.split(",")):
                    raise ValidationError(f"Invalid file type. Accepted types: {{accept}}")
            
            # Validate file size if specified
            max_size = config.get("max_size")  # in bytes
            if max_size and hasattr(value, "size") and value.size > max_size:
                raise ValidationError(f"File size exceeds maximum allowed size")
        
        return value
    
    def _clean(self) -> None:
        """Perform form-level validation."""
        # Override this method for custom form validation
        # Example:
        # if self.cleaned_data.get("password") != self.cleaned_data.get("confirm_password"):
        #     raise ValidationError("Passwords do not match")
        pass
    
    def _add_field_error(self, field_name: str, error: str) -> None:
        """Add error to a specific field."""
        if field_name not in self.errors:
            self.errors[field_name] = []
        self.errors[field_name].append(error)
    
    def _add_form_error(self, error: str) -> None:
        """Add form-level error."""
        self._add_field_error("__all__", error)
    
    def save(self, commit: bool = True) -> Optional[{model_hint}]:
        """Save form data to model instance."""
        if not self.is_valid():
            raise ValueError("Form data is invalid")
        
        if self.instance is None:
            # Create new instance
            if "{model_name}" != "Any":
                self.instance = {model_name}()
            else:
                raise ValueError("Cannot save form without model class or instance")
        
        # Update instance with cleaned data
        for field_name, value in self.cleaned_data.items():
            if hasattr(self.instance, field_name):
                setattr(self.instance, field_name, value)
        
        if commit:
            # Save to database (implement based on your ORM)
            # self.instance.save()
            pass
        
        return self.instance
    
    def render(self) -> str:
        """Render form as HTML."""
        html_parts = [f'<form class="{{self.css_classes["form"]}}">']
        
        for field_name in self.field_order:
            if field_name in self.fields:
                field_html = self._render_field(field_name, self.fields[field_name])
                html_parts.append(field_html)
        
        html_parts.append('</form>')
        return '\\n'.join(html_parts)
    
    def _render_field(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Render a single form field."""
        field_type = field_config.get("type", "text")
        label = field_config.get("label", field_name.replace("_", " ").title())
        help_text = field_config.get("help_text", "")
        value = self.data.get(field_name, field_config.get("default", ""))
        
        # Field wrapper
        field_html = [f'<div class="{{self.css_classes["field"]}}">']
        
        # Label
        required = field_config.get("required", False)
        required_marker = " *" if required else ""
        field_html.append(f'<label class="{{self.css_classes["label"]}}" for="{{field_name}}">{{label}}{{required_marker}}</label>')
        
        # Input
        if field_type == "textarea":
            rows = field_config.get("rows", 3)
            field_html.append(f'<textarea class="{{self.css_classes["input"]}}" id="{{field_name}}" name="{{field_name}}" rows="{{rows}}">{{value}}</textarea>')
        elif field_type == "select":
            field_html.append(f'<select class="{{self.css_classes["input"]}}" id="{{field_name}}" name="{{field_name}}">')
            choices = field_config.get("choices", [])
            for choice_value, choice_label in choices:
                selected = 'selected' if str(value) == str(choice_value) else ''
                field_html.append(f'<option value="{{choice_value}}" {{selected}}>{{choice_label}}</option>')
            field_html.append('</select>')
        elif field_type == "checkbox":
            checked = 'checked' if value else ''
            field_html.append(f'<input type="checkbox" class="{{self.css_classes["input"]}}" id="{{field_name}}" name="{{field_name}}" {{checked}}>')
        else:
            input_type = field_type
            placeholder = field_config.get("placeholder", "")
            field_html.append(f'<input type="{{input_type}}" class="{{self.css_classes["input"]}}" id="{{field_name}}" name="{{field_name}}" value="{{value}}" placeholder="{{placeholder}}">')
        
        # Errors
        if field_name in self.errors:
            for error in self.errors[field_name]:
                field_html.append(f'<div class="{{self.css_classes["error"]}}">{{error}}</div>')
        
        # Help text
        if help_text:
            field_html.append(f'<div class="{{self.css_classes["help"]}}">{{help_text}}</div>')
        
        field_html.append('</div>')
        return '\\n'.join(field_html)
    
    def as_dict(self) -> Dict[str, Any]:
        """Return form data as dictionary."""
        return {{
            "data": self.data,
            "errors": self.errors,
            "is_valid": self.is_valid() if self.is_bound else None,
            "cleaned_data": self.cleaned_data if self.is_bound else {{}}
        }}


# Usage examples:
#
# # Create form with data
# form = {form_name}(data=request_data)
# if form.is_valid():
#     instance = form.save()
#     return {{"success": True, "id": instance.id}}
# else:
#     return {{"errors": form.errors}}
#
# # Create form with existing instance
# form = {form_name}(instance=user)
# html = form.render()
#
# # FastAPI integration
# @app.post("/submit-form")
# async def submit_form(
#     name: str = Form(...),
#     email: str = Form(...),
#     age: Optional[int] = Form(None)
# ):
#     form_data = {{"name": name, "email": email, "age": age}}
#     form = {form_name}(data=form_data)
#     
#     if form.is_valid():
#         return form.save()
#     else:
#         return {{"errors": form.errors}}, 400
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeFormCommand)
