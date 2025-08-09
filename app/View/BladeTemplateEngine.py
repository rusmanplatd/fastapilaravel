from __future__ import annotations

import re
import os
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound


class BladeDirective:
    """Represents a Blade directive."""
    
    def __init__(self, name: str, handler: Callable[[str], str], is_block: bool = False):
        self.name = name
        self.handler = handler
        self.is_block = is_block


class BladeTemplateEngine:
    """
    Laravel-style Blade Template Engine.
    
    Provides Laravel Blade-like templating functionality using Jinja2 as the base,
    with custom directives and syntax similar to Laravel Blade.
    """
    
    def __init__(self, template_paths: Optional[List[str]] = None, cache_path: Optional[str] = None):
        self.template_paths = template_paths or ['resources/views']
        self.cache_path = cache_path or 'storage/framework/views'
        self.directives: Dict[str, BladeDirective] = {}
        self.components: Dict[str, str] = {}
        self.globals: Dict[str, Any] = {}
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_paths),
            autoescape=select_autoescape(['html', 'xml']),
            cache_size=0 if cache_path else -1
        )
        
        # Register default Blade directives
        self._register_default_directives()
        self._register_default_filters()
        self._register_default_globals()
    
    def _register_default_directives(self) -> None:
        """Register default Laravel Blade directives."""
        
        # @if directive
        self.directive('if', lambda expr: f"{{% if {expr} %}}")
        self.directive('elseif', lambda expr: f"{{% elif {expr} %}}")
        self.directive('else', lambda expr: "{% else %}")
        self.directive('endif', lambda expr: "{% endif %}")
        
        # @unless directive (opposite of @if)
        self.directive('unless', lambda expr: f"{{% if not ({expr}) %}}")
        self.directive('endunless', lambda expr: "{% endif %}")
        
        # @for directive
        self.directive('for', lambda expr: f"{{% for {expr} %}}")
        self.directive('endfor', lambda expr: "{% endfor %}")
        
        # @foreach directive
        self.directive('foreach', lambda expr: self._foreach_directive(expr))
        self.directive('endforeach', lambda expr: "{% endfor %}")
        
        # @while directive
        self.directive('while', lambda expr: f"{{% while {expr} %}}")
        self.directive('endwhile', lambda expr: "{% endwhile %}")
        
        # @forelse directive (for with else)
        self.directive('forelse', lambda expr: self._forelse_directive(expr))
        self.directive('empty', lambda expr: "{% else %}")
        self.directive('endforelse', lambda expr: "{% endfor %}")
        
        # @switch directive
        self.directive('switch', lambda expr: f"{{% set _switch_var = {expr} %}}")
        self.directive('case', lambda expr: f"{{% if _switch_var == {expr} %}}")
        self.directive('default', lambda expr: "{% else %}")
        self.directive('break', lambda expr: "{% endif %}")
        self.directive('endswitch', lambda expr: "")
        
        # @isset and @empty directives
        self.directive('isset', lambda expr: f"{{% if {expr} is defined and {expr} is not none %}}")
        self.directive('endisset', lambda expr: "{% endif %}")
        self.directive('empty', lambda expr: f"{{% if not {expr} %}}")
        self.directive('endempty', lambda expr: "{% endif %}")
        
        # @auth and @guest directives
        self.directive('auth', lambda expr: "{% if current_user %}")
        self.directive('endauth', lambda expr: "{% endif %}")
        self.directive('guest', lambda expr: "{% if not current_user %}")
        self.directive('endguest', lambda expr: "{% endif %}")
        
        # @can directive (authorization)
        self.directive('can', lambda expr: f"{{% if can({expr}) %}}")
        self.directive('cannot', lambda expr: f"{{% if not can({expr}) %}}")
        self.directive('endcan', lambda expr: "{% endif %}")
        self.directive('endcannot', lambda expr: "{% endif %}")
        
        # @hasSection directive
        self.directive('hasSection', lambda expr: f"{{% if has_section({expr}) %}}")
        self.directive('endHasSection', lambda expr: "{% endif %}")
        
        # @section and @yield directives
        self.directive('section', lambda expr: self._section_directive(expr))
        self.directive('endsection', lambda expr: "{% endblock %}")
        self.directive('yield', lambda expr: f"{{{{ {expr} | default('') }}}}")
        self.directive('show', lambda expr: "{% endblock %}")
        
        # @extends directive
        self.directive('extends', lambda expr: f"{{% extends {expr} %}}")
        
        # @include directive
        self.directive('include', lambda expr: f"{{% include {expr} %}}")
        
        # @includeIf directive
        self.directive('includeIf', lambda expr: self._include_if_directive(expr))
        
        # @includeWhen directive
        self.directive('includeWhen', lambda expr: self._include_when_directive(expr))
        
        # @includeFirst directive
        self.directive('includeFirst', lambda expr: self._include_first_directive(expr))
        
        # @component directive
        self.directive('component', lambda expr: self._component_directive(expr))
        self.directive('endcomponent', lambda expr: "{% endcall %}")
        
        # @slot directive
        self.directive('slot', lambda expr: self._slot_directive(expr))
        self.directive('endslot', lambda expr: "")
        
        # @push and @stack directives (for stacking content)
        self.directive('push', lambda expr: self._push_directive(expr))
        self.directive('endpush', lambda expr: "")
        self.directive('stack', lambda expr: f"{{{{ get_stack({expr}) | safe }}}}")
        
        # @once directive (render only once)
        self.directive('once', lambda expr: "{% if not _once_rendered %}")
        self.directive('endonce', lambda expr: "{% set _once_rendered = true %}{% endif %}")
        
        # @verbatim directive (raw content)
        self.directive('verbatim', lambda expr: "{% raw %}")
        self.directive('endverbatim', lambda expr: "{% endraw %}")
        
        # @php directive (for PHP-like code, converted to Python)
        self.directive('php', lambda expr: "{% set _php_start = true %}")
        self.directive('endphp', lambda expr: "")
        
        # @json directive
        self.directive('json', lambda expr: f"{{{{ {expr} | tojson | safe }}}}")
        
        # @csrf directive
        self.directive('csrf', lambda expr: "{{ csrf_token() | safe }}")
        
        # @method directive (for HTTP method spoofing)
        self.directive('method', lambda expr: f'<input type="hidden" name="_method" value="{expr.strip("\'\"")}">')
        
        # @error directive
        self.directive('error', lambda expr: self._error_directive(expr))
        self.directive('enderror', lambda expr: "{% endif %}")
        
        # @env directive
        self.directive('env', lambda expr: self._env_directive(expr))
        self.directive('endenv', lambda expr: "{% endif %}")
        
        # @production directive
        self.directive('production', lambda expr: "{% if app.is_production() %}")
        self.directive('endproduction', lambda expr: "{% endif %}")
        
        # @dd and @dump directives (debug)
        self.directive('dd', lambda expr: f"{{{{ dd({expr}) }}}}")
        self.directive('dump', lambda expr: f"{{{{ dump({expr}) }}}}")
    
    def _foreach_directive(self, expr: str) -> str:
        """Convert @foreach to Jinja2 for loop."""
        # Parse: $items as $item or $items as $key => $value
        match = re.match(r'\$(\w+)\s+as\s+\$(\w+)(?:\s*=>\s*\$(\w+))?', expr)
        if match:
            items, key, value = match.groups()
            if value:
                return f"{{% for {key}, {value} in {items}.items() %}}"
            else:
                return f"{{% for {key} in {items} %}}"
        return f"{{% for item in {expr} %}}"
    
    def _forelse_directive(self, expr: str) -> str:
        """Convert @forelse to Jinja2 for-else loop."""
        foreach_result = self._foreach_directive(expr)
        return foreach_result
    
    def _section_directive(self, expr: str) -> str:
        """Convert @section to Jinja2 block."""
        section_name = expr.strip('"\'')
        return f"{{% block {section_name} %}}"
    
    def _include_if_directive(self, expr: str) -> str:
        """Convert @includeIf to conditional include."""
        parts = [part.strip() for part in expr.split(',', 1)]
        if len(parts) == 2:
            condition, template = parts
            return f"{{% if {condition} %}}{{% include {template} %}}{{% endif %}}"
        return f"{{% include {expr} %}}"
    
    def _include_when_directive(self, expr: str) -> str:
        """Convert @includeWhen to conditional include."""
        parts = [part.strip() for part in expr.split(',', 1)]
        if len(parts) == 2:
            condition, template = parts
            return f"{{% if {condition} %}}{{% include {template} %}}{{% endif %}}"
        return f"{{% include {expr} %}}"
    
    def _include_first_directive(self, expr: str) -> str:
        """Convert @includeFirst to include first existing template."""
        # This would need more complex logic to check template existence
        return f"{{% include {expr} %}}"
    
    def _component_directive(self, expr: str) -> str:
        """Convert @component to Jinja2 macro call."""
        return f"{{% call component({expr}) %}}"
    
    def _slot_directive(self, expr: str) -> str:
        """Convert @slot to Jinja2 variable assignment."""
        slot_name = expr.strip('"\'')
        return f"{{% set {slot_name}_slot %}}"
    
    def _push_directive(self, expr: str) -> str:
        """Convert @push to stack assignment."""
        stack_name = expr.strip('"\'')
        return f"{{% set {stack_name}_stack = {stack_name}_stack + [' %}}"
    
    def _error_directive(self, expr: str) -> str:
        """Convert @error to error check."""
        field_name = expr.strip('"\'')
        return f"{{% if errors and errors.get('{field_name}') %}}"
    
    def _env_directive(self, expr: str) -> str:
        """Convert @env to environment check."""
        environments = [env.strip().strip('"\'') for env in expr.split(',')]
        env_check = " or ".join([f"app.environment() == '{env}'" for env in environments])
        return f"{{% if {env_check} %}}"
    
    def directive(self, name: str, handler: Callable[[str], str], is_block: bool = False) -> None:
        """Register a custom Blade directive."""
        self.directives[name] = BladeDirective(name, handler, is_block)
    
    def _register_default_filters(self) -> None:
        """Register default Jinja2 filters for Blade compatibility."""
        
        def str_limit(text: str, limit: int = 100, end: str = '...') -> str:
            """Laravel-style str_limit filter."""
            if len(text) <= limit:
                return text
            return text[:limit] + end
        
        def str_slug(text: str, separator: str = '-') -> str:
            """Laravel-style str_slug filter."""
            import re
            # Convert to lowercase and replace spaces/special chars with separator
            slug = re.sub(r'[^\w\s-]', '', text.lower())
            slug = re.sub(r'[\s_-]+', separator, slug)
            return slug.strip(separator)
        
        def str_plural(text: str, count: int = 2) -> str:
            """Laravel-style str_plural filter."""
            if count == 1:
                return text
            # Simple pluralization (would need proper inflector in real implementation)
            if text.endswith(('s', 'sh', 'ch', 'x', 'z')):
                return text + 'es'
            elif text.endswith('y') and text[-2] not in 'aeiou':
                return text[:-1] + 'ies'
            else:
                return text + 's'
        
        def str_singular(text: str) -> str:
            """Laravel-style str_singular filter."""
            # Simple singularization (would need proper inflector in real implementation)
            if text.endswith('ies'):
                return text[:-3] + 'y'
            elif text.endswith('es') and text[-3] in 'shcxz':
                return text[:-2]
            elif text.endswith('s') and not text.endswith('ss'):
                return text[:-1]
            return text
        
        def money_format(amount: float, currency: str = '$') -> str:
            """Format money with currency symbol."""
            return f"{currency}{amount:,.2f}"
        
        def file_size(bytes_size: int) -> str:
            """Convert bytes to human readable format."""
            size_float = float(bytes_size)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_float < 1024.0:
                    return f"{size_float:.1f} {unit}"
                size_float /= 1024.0
            return f"{size_float:.1f} PB"
        
        # Register filters
        self.jinja_env.filters['limit'] = str_limit
        self.jinja_env.filters['slug'] = str_slug
        self.jinja_env.filters['plural'] = str_plural
        self.jinja_env.filters['singular'] = str_singular
        self.jinja_env.filters['money'] = money_format
        self.jinja_env.filters['filesize'] = file_size
    
    def _register_default_globals(self) -> None:
        """Register default global functions for Blade templates."""
        
        def old(key: str, default: Any = None) -> Any:
            """Get old input value (for form persistence)."""
            # This would get old input from session/flash data
            return default
        
        def csrf_token() -> str:
            """Generate CSRF token."""
            # This would generate actual CSRF token
            return '<input type="hidden" name="_token" value="csrf_token_here">'
        
        def route(name: str, **params: Any) -> str:
            """Generate URL for named route."""
            # This would use the route manager to generate URLs
            return f"/route/{name}"
        
        def url(path: str) -> str:
            """Generate full URL for path."""
            return f"http://localhost:8000{path}"
        
        def asset(path: str) -> str:
            """Generate URL for asset."""
            return f"/assets/{path}"
        
        def config(key: str, default: Any = None) -> Any:
            """Get configuration value."""
            # This would get from config repository
            return default
        
        def session(key: Optional[str] = None, default: Any = None) -> Any:
            """Get session value."""
            # This would get from session
            return default
        
        def auth() -> Dict[str, Any]:
            """Get authentication information."""
            return {'user': None, 'check': False}
        
        def can(ability: str, *args: Any) -> bool:
            """Check authorization."""
            # This would check with gate/policy system
            return True
        
        def has_section(name: str) -> bool:
            """Check if section exists."""
            return False
        
        def get_stack(name: str) -> str:
            """Get stacked content."""
            return ""
        
        def dd(*args: Any) -> str:
            """Dump and die (for debugging)."""
            import json
            return f"<pre>{json.dumps(args, indent=2, default=str)}</pre>"
        
        def dump(*args: Any) -> str:
            """Dump variables (for debugging)."""
            import json
            return f"<pre>{json.dumps(args, indent=2, default=str)}</pre>"
        
        # Register globals
        self.jinja_env.globals.update({
            'old': old,
            'csrf_token': csrf_token,
            'route': route,
            'url': url,
            'asset': asset,
            'config': config,
            'session': session,
            'auth': auth,
            'can': can,
            'has_section': has_section,
            'get_stack': get_stack,
            'dd': dd,
            'dump': dump,
        })
    
    def compile_template(self, template_content: str) -> str:
        """Compile Blade template to Jinja2."""
        compiled = template_content
        
        # Convert Blade syntax to Jinja2
        compiled = self._convert_blade_syntax(compiled)
        compiled = self._convert_blade_directives(compiled)
        compiled = self._convert_blade_comments(compiled)
        compiled = self._convert_blade_echo(compiled)
        
        return compiled
    
    def _convert_blade_syntax(self, content: str) -> str:
        """Convert basic Blade syntax to Jinja2."""
        
        # Convert {{ $var }} to {{ var }}
        content = re.sub(r'{{\s*\$(\w+)', r'{{ \1', content)
        
        # Convert {!! $var !!} to {{ var | safe }}
        content = re.sub(r'{\!!\s*\$(\w+)\s*\!\!}', r'{{ \1 | safe }}', content)
        content = re.sub(r'{\!!\s*([^!]+)\s*\!\!}', r'{{ \1 | safe }}', content)
        
        # Convert @{{ to {{ (escaped)
        content = re.sub(r'@{{', r'{{ ', content)
        
        return content
    
    def _convert_blade_directives(self, content: str) -> str:
        """Convert Blade directives to Jinja2."""
        
        # Match @directive or @directive(args)
        directive_pattern = r'@(\w+)(?:\s*\(\s*([^)]*)\s*\))?'
        
        def replace_directive(match: re.Match[str]) -> str:
            directive_name = match.group(1)
            directive_args = match.group(2) or ''
            
            if directive_name in self.directives:
                directive = self.directives[directive_name]
                return directive.handler(directive_args)
            
            # Unknown directive - leave as is or convert to comment
            return f"<!-- Unknown directive: @{directive_name} -->"
        
        content = re.sub(directive_pattern, replace_directive, content)
        return content
    
    def _convert_blade_comments(self, content: str) -> str:
        """Convert Blade comments to Jinja2."""
        # Convert {{-- comment --}} to {# comment #}
        content = re.sub(r'{{--\s*(.*?)\s*--}}', r'{# \1 #}', content, flags=re.DOTALL)
        return content
    
    def _convert_blade_echo(self, content: str) -> str:
        """Convert Blade echo statements."""
        # Convert remaining {{ }} that weren't converted
        # This handles complex expressions
        return content
    
    def render(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a Blade template."""
        context = context or {}
        
        try:
            # Load template content
            template_path = self._find_template(template_name)
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Compile Blade to Jinja2
            compiled_content = self.compile_template(template_content)
            
            # Create Jinja2 template
            template = self.jinja_env.from_string(compiled_content)
            
            # Add default context variables
            default_context = {
                'app': self._get_app_context(),
                'current_user': context.get('user'),
                'errors': context.get('errors', {}),
            }
            
            context.update(default_context)
            
            # Render template
            return template.render(context)
            
        except TemplateNotFound:
            raise FileNotFoundError(f"Template not found: {template_name}")
        except Exception as e:
            raise RuntimeError(f"Error rendering template {template_name}: {str(e)}")
    
    def _find_template(self, template_name: str) -> str:
        """Find template file path."""
        # Convert dot notation to path (e.g., 'auth.login' -> 'auth/login.blade.html')
        template_path = template_name.replace('.', '/')
        
        # Try different extensions
        extensions = ['.blade.html', '.blade.php', '.html', '.htm']
        
        for base_path in self.template_paths:
            for ext in extensions:
                full_path = Path(base_path) / f"{template_path}{ext}"
                if full_path.exists():
                    return str(full_path)
        
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    def _get_app_context(self) -> Dict[str, Any]:
        """Get application context for templates."""
        return {
            'name': 'FastAPI Laravel',
            'version': '1.0.0',
            'environment': lambda: 'production',
            'is_production': lambda: True,
            'is_local': lambda: False,
            'is_debug': lambda: False,
        }
    
    def add_global(self, name: str, value: Any) -> None:
        """Add global variable to template context."""
        self.jinja_env.globals[name] = value
    
    def add_filter(self, name: str, filter_func: Callable[..., Any]) -> None:
        """Add custom filter."""
        self.jinja_env.filters[name] = filter_func
    
    def extend_with_globals(self, globals_dict: Dict[str, Any]) -> None:
        """Extend template globals."""
        self.jinja_env.globals.update(globals_dict)
    
    def component(self, name: str, template_path: str) -> None:
        """Register a Blade component."""
        self.components[name] = template_path
    
    def clear_cache(self) -> None:
        """Clear template cache."""
        if hasattr(self.jinja_env, 'cache') and self.jinja_env.cache is not None:
            self.jinja_env.cache.clear()


# Global Blade engine instance
blade = BladeTemplateEngine()


def view(template: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Laravel-style view helper function."""
    return blade.render(template, context or {})