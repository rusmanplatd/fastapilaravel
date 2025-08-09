from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Callable, Union
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from jinja2.exceptions import TemplateNotFound
from fastapi.responses import HTMLResponse


class ViewManager:
    """Laravel-style view manager."""
    
    def __init__(
        self,
        template_paths: Optional[List[str]] = None,
        cache_path: Optional[str] = None,
        auto_reload: bool = True,
        autoescape: bool = True
    ) -> None:
        self.template_paths = template_paths or ['resources/views']
        self.cache_path = cache_path
        self.auto_reload = auto_reload
        self.autoescape = autoescape
        
        # Global view data
        self._shared_data: Dict[str, Any] = {}
        
        # View composers
        self._composers: Dict[str, List[Callable[..., Any]]] = {}
        
        # Template extensions
        self._extensions: List[str] = ['.html.j2', '.html', '.jinja2']
        
        # Initialize Jinja2 environment
        self._init_environment()
    
    def _init_environment(self) -> None:
        """Initialize Jinja2 environment."""
        # Ensure template directories exist
        for path in self.template_paths:
            Path(path).mkdir(parents=True, exist_ok=True)
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_paths),
            autoescape=select_autoescape(['html', 'xml']) if self.autoescape else False,
            auto_reload=self.auto_reload,
            cache_size=400 if not self.cache_path else 0,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters and globals
        self._register_filters()
        self._register_globals()
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters."""
        
        def json_filter(value: Any) -> str:
            """Convert value to JSON."""
            return json.dumps(value)
        
        def upper_filter(value: Any) -> str:
            """Convert to uppercase."""
            return str(value).upper()
        
        def lower_filter(value: Any) -> str:
            """Convert to lowercase."""
            return str(value).lower()
        
        def title_filter(value: Any) -> str:
            """Convert to title case."""
            return str(value).title()
        
        def slug_filter(value: Any) -> str:
            """Convert to URL slug."""
            import re
            value = str(value).lower()
            value = re.sub(r'[^a-z0-9]+', '-', value)
            return str(value.strip('-'))
        
        def truncate_filter(value: Any, length: int = 100, suffix: str = '...') -> str:
            """Truncate string."""
            value = str(value)
            if len(value) <= length:
                return str(value)
            return str(value[:length]) + suffix
        
        # Register filters
        self.env.filters['json'] = json_filter
        self.env.filters['upper'] = upper_filter
        self.env.filters['lower'] = lower_filter
        self.env.filters['title'] = title_filter
        self.env.filters['slug'] = slug_filter
        self.env.filters['truncate'] = truncate_filter
    
    def _register_globals(self) -> None:
        """Register global template functions."""
        
        def url(path: str = '/', **params: Any) -> str:
            """Generate URL."""
            # Simple URL generation - could be enhanced with routing
            if params:
                query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                return f"{path}?{query_string}"
            return path
        
        def asset(path: str) -> str:
            """Generate asset URL."""
            return f"/static/{path}"
        
        def route(name: str, **params: Any) -> str:
            """Generate named route URL."""
            # This would integrate with your routing system
            return f"/{name}"
        
        def old(key: str, default: str = '') -> str:
            """Get old input value (for form repopulation)."""
            # This would integrate with session/request handling
            return default
        
        def csrf_token() -> str:
            """Generate CSRF token."""
            # This would integrate with your CSRF protection
            return 'csrf-token-placeholder'
        
        def csrf_field() -> str:
            """Generate CSRF field HTML."""
            token = csrf_token()
            return f'<input type="hidden" name="_token" value="{token}">'
        
        def method_field(method: str) -> str:
            """Generate method field for form method spoofing."""
            return f'<input type="hidden" name="_method" value="{method.upper()}">'
        
        # Register globals
        self.env.globals.update({
            'url': url,
            'asset': asset,
            'route': route,
            'old': old,
            'csrf_token': csrf_token,
            'csrf_field': csrf_field,
            'method_field': method_field,
        })
    
    def make(self, view: str, data: Optional[Dict[str, Any]] = None, merge_data: Optional[Dict[str, Any]] = None) -> 'View':
        """Create a view instance."""
        return View(self, view, data or {}, merge_data or {})
    
    def exists(self, view: str) -> bool:
        """Check if view exists."""
        template_name = self._resolve_template_name(view)
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False
    
    def share(self, key: Union[str, Dict[str, Any]], value: Optional[Any] = None) -> None:
        """Share data with all views."""
        if isinstance(key, dict):
            self._shared_data.update(key)
        else:
            self._shared_data[key] = value
    
    def composer(self, views: Union[str, List[str]], callback: Callable[..., Any]) -> None:
        """Register view composer."""
        if isinstance(views, str):
            views = [views]
        
        for view in views:
            if view not in self._composers:
                self._composers[view] = []
            self._composers[view].append(callback)
    
    def _resolve_template_name(self, view: str) -> str:
        """Resolve template name with extensions."""
        # Convert dot notation to path
        template_path = view.replace('.', '/')
        
        # Try with each extension
        for ext in self._extensions:
            template_name = f"{template_path}{ext}"
            try:
                self.env.get_template(template_name)
                return template_name
            except TemplateNotFound:
                continue
        
        # Fallback to original name
        return f"{template_path}.html"
    
    def _call_composers(self, view_name: str, view_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call view composers for a view."""
        # Check exact match
        if view_name in self._composers:
            for composer in self._composers[view_name]:
                composer_data = composer(view_data.copy())
                if composer_data:
                    view_data.update(composer_data)
        
        # Check wildcard matches
        for pattern, composers in self._composers.items():
            if '*' in pattern:
                pattern_regex = pattern.replace('*', '.*')
                import re
                if re.match(pattern_regex, view_name):
                    for composer in composers:
                        composer_data = composer(view_data.copy())
                        if composer_data:
                            view_data.update(composer_data)
        
        return view_data
    
    def render(self, view: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Render view to string."""
        view_instance = self.make(view, data)
        return view_instance.render()
    
    def add_extension(self, extension: str) -> None:
        """Add template file extension."""
        if extension not in self._extensions:
            self._extensions.append(extension)
    
    def add_path(self, path: str) -> None:
        """Add template search path."""
        if path not in self.template_paths:
            self.template_paths.append(path)
            # Recreate loader with new paths
            self.env.loader = FileSystemLoader(self.template_paths)


class View:
    """Laravel-style view instance."""
    
    def __init__(
        self,
        manager: ViewManager,
        view: str,
        data: Dict[str, Any],
        merge_data: Optional[Dict[str, Any]] = None
    ) -> None:
        self.manager = manager
        self.view = view
        self.data = data
        self.merge_data = merge_data or {}
    
    def with_data(self, key: Union[str, Dict[str, Any]], value: Optional[Any] = None) -> 'View':
        """Add data to view."""
        if isinstance(key, dict):
            self.data.update(key)
        else:
            self.data[key] = value
        return self
    
    def with_(self, key: Union[str, Dict[str, Any]], value: Optional[Any] = None) -> 'View':
        """Alias for with_data."""
        return self.with_data(key, value)
    
    def nest(self, key: str, view: str, data: Optional[Dict[str, Any]] = None) -> 'View':
        """Nest a sub-view."""
        sub_view = self.manager.make(view, data or {})
        self.data[key] = sub_view
        return self
    
    def render(self) -> str:
        """Render view to string."""
        # Prepare data
        view_data = {}
        view_data.update(self.manager._shared_data)
        view_data.update(self.merge_data)
        view_data.update(self.data)
        
        # Call view composers
        view_data = self.manager._call_composers(self.view, view_data)
        
        # Resolve template name
        template_name = self.manager._resolve_template_name(self.view)
        
        # Render nested views
        for key, value in view_data.items():
            if isinstance(value, View):
                view_data[key] = value.render()
        
        # Get template and render
        try:
            template = self.manager.env.get_template(template_name)
            return template.render(**view_data)
        except TemplateNotFound:
            raise TemplateNotFound(f"View '{self.view}' not found. Tried: {template_name}")
    
    def to_response(self, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> HTMLResponse:
        """Convert view to FastAPI response."""
        content = self.render()
        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers=headers
        )
    
    def __str__(self) -> str:
        """Render view when converted to string."""
        return self.render()


# Global view manager
view_manager = ViewManager()


def view(template: str, data: Optional[Dict[str, Any]] = None, merge_data: Optional[Dict[str, Any]] = None) -> View:
    """Create a view instance."""
    return view_manager.make(template, data, merge_data)


def view_exists(template: str) -> bool:
    """Check if view exists."""
    return view_manager.exists(template)


def share(key: Union[str, Dict[str, Any]], value: Optional[Any] = None) -> None:
    """Share data with all views."""
    view_manager.share(key, value)


def composer(views: Union[str, List[str]], callback: Callable[..., Any]) -> None:
    """Register view composer."""
    view_manager.composer(views, callback)


def render_template(template: str, data: Optional[Dict[str, Any]] = None) -> str:
    """Render template to string."""
    return view_manager.render(template, data)


class ViewComposer:
    """Base class for view composers."""
    
    def compose(self, view_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compose view data."""
        return {}
    
    def __call__(self, view_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make composer callable."""
        return self.compose(view_data)