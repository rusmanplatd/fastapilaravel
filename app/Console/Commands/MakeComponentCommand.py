from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeComponentCommand(Command):
    """Generate a new component class."""
    
    signature = "make:component {name : The name of the component} {--inline : Create an inline component} {--view : Create a view component}"
    description = "Create a new reusable component class"
    help = "Generate a new component class for reusable functionality"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        inline = self.option("inline", False)
        view = self.option("view", False)
        
        if not name:
            self.error("Component name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Component"):
            name += "Component"
        
        component_path = Path(f"app/View/Components/{name}.py")
        component_path.parent.mkdir(parents=True, exist_ok=True)
        
        if component_path.exists():
            if not self.confirm(f"Component {name} already exists. Overwrite?"):
                self.info("Component creation cancelled.")
                return
        
        content = self._generate_component_content(name, inline, view)
        component_path.write_text(content)
        
        # Create template file if not inline
        if not inline and view:
            await self._create_template_file(name)
        
        self.info(f"✅ Component created: {component_path}")
        
        if view and not inline:
            template_name = self._get_template_name(name)
            self.comment(f"Template created: resources/views/components/{template_name}.html")
        
        self.comment("Update the component with your custom logic")
        self.comment(f"Usage: <x-{self._get_component_tag(name)} />")
    
    def _generate_component_content(self, component_name: str, inline: bool = False, view: bool = False) -> str:
        """Generate component content."""
        if view:
            return self._generate_view_component(component_name, inline)
        else:
            return self._generate_api_component(component_name)
    
    def _generate_view_component(self, component_name: str, inline: bool = False) -> str:
        """Generate a view component."""
        template_method = ""
        if not inline:
            template_name = self._get_template_name(component_name)
            template_method = f'''
    def template(self) -> str:
        """Get the component template path."""
        return "components/{template_name}.html"'''
        else:
            template_method = '''
    def render(self) -> str:
        """Render the inline component."""
        return f"""
        <div class="component {self.css_class}">
            <h3>{self.title}</h3>
            <p>{self.content}</p>
        </div>
        """'''
        
        return f'''from __future__ import annotations

from typing import Any, Dict, Optional, List
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


class {component_name}:
    """Reusable view component."""
    
    def __init__(
        self, 
        title: str = "",
        content: str = "",
        css_class: str = "",
        **attributes: Any
    ) -> None:
        """Initialize the component."""
        self.title = title
        self.content = content
        self.css_class = css_class
        self.attributes = attributes
        
        # Set up template environment
        template_dir = Path("resources/views")
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )
    {template_method}
    
    def with_data(self, **data: Any) -> '{component_name}':
        """Add data to the component."""
        for key, value in data.items():
            setattr(self, key, value)
        return self
    
    def with_attributes(self, **attributes: Any) -> '{component_name}':
        """Add HTML attributes to the component."""
        self.attributes.update(attributes)
        return self
    
    def get_attributes(self) -> Dict[str, Any]:
        """Get component attributes."""
        return {{
            "title": self.title,
            "content": self.content,
            "css_class": self.css_class,
            **self.attributes
        }}
    
    def should_render(self) -> bool:
        """Determine if the component should render."""
        # Add your conditional rendering logic here
        return True
    
    def before_render(self) -> None:
        """Hook called before rendering."""
        # Add pre-render logic here
        pass
    
    def after_render(self, rendered_content: str) -> str:
        """Hook called after rendering."""
        # Add post-render logic here
        return rendered_content
    
    def render_html(self, **extra_data: Any) -> str:
        """Render the component to HTML."""
        if not self.should_render():
            return ""
        
        self.before_render()
        
        # Merge component data with extra data
        data = {{
            **self.get_attributes(),
            **extra_data
        }}
        
        try:
            {"template = self.template_env.get_template(self.template())" if not inline else ""}
            {"rendered = template.render(**data)" if not inline else "rendered = self.render()"}
            return self.after_render(rendered)
        except Exception as e:
            # Handle rendering errors gracefully
            return f'<div class="component-error">Error rendering {component_name}: {{e}}</div>'


# Usage examples:
#
# # Basic usage
# component = {component_name}(
#     title="Welcome",
#     content="Hello, World!",
#     css_class="welcome-component"
# )
# html = component.render_html()
#
# # With additional data
# html = component.with_data(
#     user_name="John Doe",
#     show_avatar=True
# ).render_html()
#
# # In FastAPI template
# @app.get("/")
# async def home(request: Request):
#     component = {component_name}("Page Title", "Welcome content")
#     return templates.TemplateResponse("home.html", {{
#         "request": request,
#         "welcome_component": component.render_html()
#     }})
'''
    
    def _generate_api_component(self, component_name: str) -> str:
        """Generate an API component."""
        return f'''from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, validator


class {component_name}:
    """Reusable API component for data processing and response formatting."""
    
    def __init__(self, **config: Any) -> None:
        """Initialize the component."""
        self.config = config
        self.data: Dict[str, Any] = {{}}
        self.errors: List[str] = []
        self.metadata: Dict[str, Any] = {{}}
    
    def process(self, input_data: Any) -> '{component_name}':
        """Process input data."""
        try:
            # Add your data processing logic here
            # Example:
            # if isinstance(input_data, dict):
            #     self.data = self.transform_data(input_data)
            # elif isinstance(input_data, list):
            #     self.data = self.process_list(input_data)
            
            self.data = input_data if input_data else {{}}
            self.add_metadata("processed_at", datetime.now().isoformat())
            
        except Exception as e:
            self.add_error(f"Processing failed: {{str(e)}}")
        
        return self
    
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform input data."""
        # Add your transformation logic here
        # Example transformations:
        transformed = {{}}
        
        for key, value in data.items():
            # Convert snake_case to camelCase
            camel_key = self.to_camel_case(key)
            
            # Apply value transformations
            if isinstance(value, datetime):
                transformed[camel_key] = value.isoformat()
            elif isinstance(value, (int, float)) and key.endswith('_id'):
                # Transform ID fields
                transformed[camel_key] = str(value)
            else:
                transformed[camel_key] = value
        
        return transformed
    
    def validate_data(self) -> bool:
        """Validate the processed data."""
        # Add your validation logic here
        # Example validations:
        
        if not self.data:
            self.add_error("No data to validate")
            return False
        
        # Required fields validation
        required_fields = self.config.get("required_fields", [])
        for field in required_fields:
            if field not in self.data or not self.data[field]:
                self.add_error(f"Required field '{{field}}' is missing")
        
        # Type validation
        field_types = self.config.get("field_types", {{}})
        for field, expected_type in field_types.items():
            if field in self.data and not isinstance(self.data[field], expected_type):
                self.add_error(f"Field '{{field}}' must be of type {{expected_type.__name__}}")
        
        return len(self.errors) == 0
    
    def format_response(self) -> Dict[str, Any]:
        """Format the component data for API response."""
        response = {{
            "data": self.data,
            "component": {{
                "name": "{component_name}",
                "version": self.config.get("version", "1.0.0"),
                "processed_at": datetime.now().isoformat()
            }}
        }}
        
        if self.metadata:
            response["meta"] = self.metadata
        
        if self.errors:
            response["errors"] = self.errors
            response["success"] = False
        else:
            response["success"] = True
        
        return response
    
    def add_error(self, error: str) -> '{component_name}':
        """Add an error message."""
        self.errors.append(error)
        return self
    
    def add_metadata(self, key: str, value: Any) -> '{component_name}':
        """Add metadata."""
        self.metadata[key] = value
        return self
    
    def to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    def to_snake_case(self, camel_str: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
    
    def has_errors(self) -> bool:
        """Check if component has errors."""
        return len(self.errors) > 0
    
    def clear_errors(self) -> '{component_name}':
        """Clear all errors."""
        self.errors = []
        return self
    
    def get_summary(self) -> Dict[str, Any]:
        """Get component processing summary."""
        return {{
            "component": "{component_name}",
            "data_count": len(self.data) if isinstance(self.data, (dict, list)) else 1,
            "error_count": len(self.errors),
            "metadata_count": len(self.metadata),
            "has_errors": self.has_errors(),
            "config": self.config
        }}


# Usage examples:
#
# # Basic usage
# component = {component_name}(
#     required_fields=["name", "email"],
#     field_types={{"age": int, "active": bool}}
# )
#
# # Process and validate data
# result = component.process(input_data).validate_data()
# if component.has_errors():
#     return {{"errors": component.errors}}
#
# # Get formatted response
# response = component.format_response()
#
# # In FastAPI endpoint
# @app.post("/api/process")
# async def process_data(data: dict):
#     component = {component_name}(version="2.0.0")
#     component.process(data)
#     
#     if component.validate_data():
#         return component.format_response()
#     else:
#         return {{"errors": component.errors}}, 400
'''
    
    async def _create_template_file(self, component_name: str) -> None:
        """Create template file for view component."""
        template_name = self._get_template_name(component_name)
        template_path = Path(f"resources/views/components/{template_name}.html")
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not template_path.exists():
            content = f'''<!-- {component_name} Template -->
<div class="component component-{template_name} {{{{ css_class }}}}">
    {{% if title %}}
    <div class="component-header">
        <h3 class="component-title">{{{{ title }}}}</h3>
    </div>
    {{% endif %}}
    
    <div class="component-body">
        {{% if content %}}
        <div class="component-content">
            {{{{ content }}}}
        </div>
        {{% endif %}}
        
        <!-- Add your custom template content here -->
        {{% block component_content %}}
        <p>Default {component_name.replace("Component", "")} content</p>
        {{% endblock %}}
    </div>
    
    {{% if attributes %}}
    <div class="component-footer" data-attributes="{{{{ attributes | tojson }}}}">
        <!-- Additional content based on attributes -->
    </div>
    {{% endif %}}
</div>

<style>
.component-{template_name} {{
    border: 1px solid #e1e5e9;
    border-radius: 6px;
    padding: 1rem;
    margin: 0.5rem 0;
    background-color: #ffffff;
}}

.component-{template_name} .component-header {{
    border-bottom: 1px solid #e1e5e9;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}}

.component-{template_name} .component-title {{
    margin: 0;
    color: #24292e;
    font-size: 1.1rem;
    font-weight: 600;
}}

.component-{template_name} .component-body {{
    line-height: 1.6;
}}

.component-{template_name} .component-content {{
    color: #586069;
}}

.component-{template_name} .component-footer {{
    border-top: 1px solid #e1e5e9;
    padding-top: 0.5rem;
    margin-top: 1rem;
    font-size: 0.9rem;
    color: #6a737d;
}}
</style>'''
            template_path.write_text(content)
    
    def _get_template_name(self, component_name: str) -> str:
        """Get template name from component name."""
        # Convert ComponentName to component-name
        name = component_name.replace("Component", "")
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
    
    def _get_component_tag(self, component_name: str) -> str:
        """Get component tag name."""
        return self._get_template_name(component_name)
# Register command
from app.Console.Artisan import register_command
register_command(MakeComponentCommand)
