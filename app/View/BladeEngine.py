"""
Laravel-style Blade Template Engine for FastAPI
Provides template inheritance, sections, and directives
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape


class BladeDirective:
    """Custom Blade directive implementation"""
    
    def __init__(self, name: str, callback: callable):
        self.name = name
        self.callback = callback


class BladeEngine:
    """Laravel-style Blade template engine built on Jinja2"""
    
    def __init__(self, template_paths: List[str]):
        self.template_paths = template_paths
        self.directives: Dict[str, BladeDirective] = {}
        self.sections: Dict[str, str] = {}
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_paths),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register built-in directives
        self._register_builtin_directives()
        
        # Add custom filters
        self._register_filters()
    
    def _register_builtin_directives(self) -> None:
        """Register built-in Blade directives"""
        
        # Auth directives
        self.directive('auth', self._auth_directive)
        self.directive('guest', self._guest_directive)
        self.directive('endauth', lambda content: "{% endif %}")
        self.directive('endguest', lambda content: "{% endif %}")
        
        # Can directive
        self.directive('can', self._can_directive)
        self.directive('cannot', self._cannot_directive)
        self.directive('endcan', lambda content: "{% endif %}")
        self.directive('endcannot', lambda content: "{% endif %}")
        
        # Loop directives
        self.directive('forelse', self._forelse_directive)
        self.directive('empty', lambda content: "{% else %}")
        self.directive('endforelse', lambda content: "{% endfor %}")
        
        # Conditional directives
        self.directive('unless', self._unless_directive)
        self.directive('endunless', lambda content: "{% endif %}")
        
        # Include directives
        self.directive('include', self._include_directive)
        self.directive('includeIf', self._include_if_directive)
        self.directive('includeWhen', self._include_when_directive)
        
        # CSRF directive
        self.directive('csrf', lambda content: '<input type="hidden" name="_token" value="{{ csrf_token() }}">')
        
        # Method directive
        self.directive('method', self._method_directive)
        
        # JSON directive
        self.directive('json', self._json_directive)
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters"""
        self.env.filters['ucfirst'] = lambda s: s[0].upper() + s[1:] if s else s
        self.env.filters['title'] = lambda s: s.title() if s else s
        self.env.filters['slug'] = lambda s: re.sub(r'[^\w\s-]', '', s).strip().replace(' ', '-').lower() if s else s
    
    def directive(self, name: str, callback: callable) -> None:
        """Register a custom Blade directive"""
        self.directives[name] = BladeDirective(name, callback)
    
    def _auth_directive(self, content: str) -> str:
        """Convert @auth to Jinja2"""
        return "{% if current_user %}"
    
    def _guest_directive(self, content: str) -> str:
        """Convert @guest to Jinja2"""
        return "{% if not current_user %}"
    
    def _can_directive(self, content: str) -> str:
        """Convert @can to Jinja2"""
        permission = content.strip().strip("'\"")
        return f"{{% if current_user and current_user.can('{permission}') %}}"
    
    def _cannot_directive(self, content: str) -> str:
        """Convert @cannot to Jinja2"""
        permission = content.strip().strip("'\"")
        return f"{{% if not (current_user and current_user.can('{permission}')) %}}"
    
    def _forelse_directive(self, content: str) -> str:
        """Convert @forelse to Jinja2"""
        # Parse forelse($items as $item)
        match = re.match(r'\s*\(\s*(.+?)\s+as\s+(.+?)\s*\)', content)
        if match:
            items, item = match.groups()
            return f"{{% for {item} in {items} %}}"
        return "{% for item in items %}"
    
    def _unless_directive(self, content: str) -> str:
        """Convert @unless to Jinja2"""
        condition = content.strip('()')
        return f"{{% if not ({condition}) %}}"
    
    def _include_directive(self, content: str) -> str:
        """Convert @include to Jinja2"""
        template = content.strip().strip("'\"")
        return f"{{% include '{template}' %}}"
    
    def _include_if_directive(self, content: str) -> str:
        """Convert @includeIf to Jinja2"""
        # Parse includeIf($condition, 'template')
        parts = content.split(',', 1)
        if len(parts) == 2:
            condition = parts[0].strip().strip('(')
            template = parts[1].strip().strip(')').strip("'\"")
            return f"{{% if {condition} %}}{{% include '{template}' %}}{{% endif %}}"
        return ""
    
    def _include_when_directive(self, content: str) -> str:
        """Convert @includeWhen to Jinja2"""
        return self._include_if_directive(content)
    
    def _method_directive(self, content: str) -> str:
        """Convert @method to HTML input"""
        method = content.strip().strip("'\"").upper()
        return f'<input type="hidden" name="_method" value="{method}">'
    
    def _json_directive(self, content: str) -> str:
        """Convert @json to Jinja2"""
        variable = content.strip()
        return f"{{{{ {variable} | tojson }}}}"
    
    def compile_blade(self, template_content: str) -> str:
        """Convert Blade syntax to Jinja2 syntax"""
        
        # Handle @extends
        template_content = re.sub(
            r"@extends\s*\(\s*['\"](.+?)['\"]\s*\)",
            r"{% extends '\1' %}",
            template_content
        )
        
        # Handle @section and @endsection
        template_content = re.sub(
            r"@section\s*\(\s*['\"](.+?)['\"]\s*\)",
            r"{% block \1 %}",
            template_content
        )
        template_content = re.sub(r"@endsection", "{% endblock %}", template_content)
        
        # Handle @yield
        template_content = re.sub(
            r"@yield\s*\(\s*['\"](.+?)['\"]\s*\)",
            r"{% block \1 %}{% endblock %}",
            template_content
        )
        
        # Handle @parent
        template_content = re.sub(r"@parent", "{{ super() }}", template_content)
        
        # Handle @if, @elseif, @else, @endif
        template_content = re.sub(r"@if\s*\(\s*(.+?)\s*\)", r"{% if \1 %}", template_content)
        template_content = re.sub(r"@elseif\s*\(\s*(.+?)\s*\)", r"{% elif \1 %}", template_content)
        template_content = re.sub(r"@else", "{% else %}", template_content)
        template_content = re.sub(r"@endif", "{% endif %}", template_content)
        
        # Handle @for, @endfor
        template_content = re.sub(
            r"@for\s*\(\s*(.+?)\s*\)",
            lambda m: self._convert_php_for_to_jinja(m.group(1)),
            template_content
        )
        template_content = re.sub(r"@endfor", "{% endfor %}", template_content)
        
        # Handle @foreach, @endforeach
        template_content = re.sub(
            r"@foreach\s*\(\s*(.+?)\s+as\s+(.+?)\s*\)",
            r"{% for \2 in \1 %}",
            template_content
        )
        template_content = re.sub(r"@endforeach", "{% endfor %}", template_content)
        
        # Handle @while, @endwhile
        template_content = re.sub(r"@while\s*\(\s*(.+?)\s*\)", r"{% while \1 %}", template_content)
        template_content = re.sub(r"@endwhile", "{% endwhile %}", template_content)
        
        # Handle custom directives
        for name, directive in self.directives.items():
            pattern = rf"@{name}(?:\s*\(\s*(.+?)\s*\))?"
            template_content = re.sub(
                pattern,
                lambda m: directive.callback(m.group(1) or ''),
                template_content
            )
        
        # Handle Blade comments {{-- comment --}}
        template_content = re.sub(r"\{\{--.*?--\}\}", "", template_content, flags=re.DOTALL)
        
        # Handle unescaped output {!! variable !!}
        template_content = re.sub(r"\{\!\!\s*(.+?)\s*\!\!\}", r"{{ \1 | safe }}", template_content)
        
        # Handle escaped output {{ variable }} (already Jinja2 compatible)
        
        return template_content
    
    def _convert_php_for_to_jinja(self, for_content: str) -> str:
        """Convert PHP-style for loop to Jinja2"""
        # This is a simplified conversion
        # In practice, you might want more sophisticated parsing
        return "{% for item in range(10) %}"  # Placeholder
    
    def render(self, template_name: str, context: Dict[str, Any] = None) -> str:
        """Render a Blade template"""
        if context is None:
            context = {}
        
        # Load and compile template
        try:
            with open(self._find_template(template_name), 'r') as f:
                template_content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template '{template_name}' not found")
        
        compiled_content = self.compile_blade(template_content)
        
        # Create Jinja2 template and render
        template = self.env.from_string(compiled_content)
        return template.render(**context)
    
    def _find_template(self, template_name: str) -> str:
        """Find template file in template paths"""
        for path in self.template_paths:
            template_path = Path(path) / template_name
            if template_path.exists():
                return str(template_path)
        
        # Try with .blade.html extension
        for path in self.template_paths:
            template_path = Path(path) / f"{template_name}.blade.html"
            if template_path.exists():
                return str(template_path)
        
        raise FileNotFoundError(f"Template '{template_name}' not found")


# Global Blade engine instance
_blade_engine: Optional[BladeEngine] = None


def blade(template_paths: List[str] = None) -> BladeEngine:
    """Get or create global Blade engine instance"""
    global _blade_engine
    
    if _blade_engine is None or template_paths:
        if template_paths is None:
            template_paths = ['resources/views']
        _blade_engine = BladeEngine(template_paths)
    
    return _blade_engine


def view(template_name: str, context: Dict[str, Any] = None) -> str:
    """Laravel-style view helper"""
    return blade().render(template_name, context)