"""
Laravel-style Blade Template Engine for FastAPI
Provides template inheritance, sections, and directives
"""
from __future__ import annotations

import re
import hashlib
import pickle
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from pathlib import Path
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.loaders import BaseLoader
from .BladeComponent import ComponentRegistry, ComponentCompiler, component_registry
from .BladeServiceProvider import blade_service_provider
import os
from datetime import datetime, timedelta
import threading


class BladeDirective:
    """Custom Blade directive implementation"""
    
    def __init__(self, name: str, callback: Callable[[str], str]):
        self.name = name
        self.callback = callback


class BladeEngine:
    """Laravel-style Blade template engine built on Jinja2"""
    
    def __init__(self, template_paths: List[str], cache_path: Optional[str] = None, debug: bool = False):
        self.template_paths = template_paths
        self.directives: Dict[str, BladeDirective] = {}
        self.sections: Dict[str, str] = {}
        self.shared_data: Dict[str, Any] = {}
        self.view_composers: Dict[str, List[Callable[..., Any]]] = {}
        self.cache_path = cache_path or 'storage/framework/views'
        self.debug = debug
        self._template_cache: Dict[str, Tuple[Template, float]] = {}
        self._lock = threading.Lock()
        
        # Initialize stacks, once blocks, and fragments
        self.stacks: Dict[str, List[str]] = {}
        self.once_blocks: set[str] = set()
        self.fragments: Dict[str, str] = {}
        self.section_stacks: Dict[str, List[str]] = {}
        self.macros: Dict[str, str] = {}
        self.current_sections: Dict[str, str] = {}
        self.translations: Dict[str, Dict[str, str]] = {}
        
        # Ensure cache directory exists
        os.makedirs(self.cache_path, exist_ok=True)
        
        # Initialize Jinja2 environment with custom loader
        self.env = Environment(
            loader=self._create_blade_loader(template_paths),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            cache_size=400 if not debug else 0
        )
        
        # Register built-in directives
        self._register_builtin_directives()
        
        # Add custom filters
        self._register_filters()
        
        # Add global functions
        self._register_globals()
        
        # Initialize component system
        self.component_registry = component_registry
        self.component_compiler = ComponentCompiler(self.component_registry, self)
        
        # Initialize service provider
        self.service_provider = blade_service_provider
        
        # Register service injection directives
        service_directives = self.service_provider.create_service_directives()
        for name, callback in service_directives.items():
            self.directive(name, callback)
    
    def _register_builtin_directives(self) -> None:
        """Register built-in Blade directives"""
        
        # Define common template strings as constants
        ENDIF = "{% endif %}"
        ENDFOR = "{% endfor %}"
        
        # Auth directives
        self.directive('auth', self._auth_directive)
        self.directive('guest', self._guest_directive)
        self.directive('endauth', lambda content: ENDIF)
        self.directive('endguest', lambda content: ENDIF)
        
        # Can directive
        self.directive('can', self._can_directive)
        self.directive('cannot', self._cannot_directive)
        self.directive('endcan', lambda content: ENDIF)
        self.directive('endcannot', lambda content: ENDIF)
        
        # Loop directives
        self.directive('forelse', self._forelse_directive)
        self.directive('empty', lambda content: "{% else %}")
        self.directive('endforelse', lambda content: ENDFOR)
        
        # Conditional directives
        self.directive('unless', self._unless_directive)
        self.directive('endunless', lambda content: ENDIF)
        
        # Include directives
        self.directive('include', self._include_directive)
        self.directive('includeIf', self._include_if_directive)
        self.directive('includeWhen', self._include_when_directive)
        self.directive('includeUnless', self._include_unless_directive)
        self.directive('includeFirst', self._include_first_directive)
        
        # Each directive
        self.directive('each', self._each_directive)
        
        # CSRF directive
        self.directive('csrf', lambda content: '<input type="hidden" name="_token" value="{{ csrf_token() }}">')
        
        # Method directive
        self.directive('method', self._method_directive)
        
        # JSON directive
        self.directive('json', self._json_directive)
        
        # Error handling directives
        self.directive('error', self._error_directive)
        self.directive('enderror', lambda content: ENDIF)
        
        # Isset/empty directives
        self.directive('isset', self._isset_directive)
        self.directive('endisset', lambda content: ENDIF)
        self.directive('empty_directive', self._empty_directive)  # Renamed to avoid conflict
        self.directive('endempty', lambda content: ENDIF)
        
        # Switch directives
        self.directive('switch', self._switch_directive)
        self.directive('case', self._case_directive)
        self.directive('default', lambda content: "{% else %}")
        self.directive('endswitch', lambda content: ENDIF)
        
        # Raw directives
        self.directive('verbatim', lambda content: "{% raw %}")
        self.directive('endverbatim', lambda content: "{% endraw %}")
        
        # Production directives
        self.directive('production', self._production_directive)
        self.directive('endproduction', lambda content: ENDIF)
        
        # Advanced directives
        self.directive('dd', self._dd_directive)
        self.directive('dump', self._dump_directive)
        self.directive('livewire', self._livewire_directive)
        self.directive('entangle', self._entangle_directive)
        
        # Environment directives
        self.directive('env', self._env_directive)
        self.directive('endenv', lambda content: ENDIF)
        
        # Hasrole/haspermission directives (Laravel Permission)
        self.directive('hasrole', self._hasrole_directive)
        self.directive('endhasrole', lambda content: ENDIF)
        self.directive('hasanyrole', self._hasanyrole_directive)
        self.directive('endhasanyrole', lambda content: ENDIF)
        self.directive('haspermission', self._haspermission_directive)
        self.directive('endhaspermission', lambda content: ENDIF)
        
        # Stack management directives
        self.directive('once', self._once_directive)
        self.directive('endonce', lambda content: ENDIF)
        self.directive('prepend', self._prepend_directive)
        self.directive('endprepend', lambda content: "")
        
        # Fragment directives
        self.directive('fragment', self._fragment_directive)
        self.directive('endfragment', lambda content: "")
        
        # Additional section directives
        self.directive('overwrite', lambda content: "{% set _overwrite = true %}")
        self.directive('append', lambda content: "{% set _append = true %}")
        self.directive('show', self._show_directive)
        
        # Component directives
        self.directive('slot', self._slot_directive)
        self.directive('endslot', lambda content: "")
        self.directive('props', self._props_directive)
        
        # Conditional class and style directives
        self.directive('class', self._class_directive)
        self.directive('style', self._style_directive)
        
        # Form and validation directives
        self.directive('old', self._old_directive)
        self.directive('errors', self._errors_directive)
        
        # Debug directives
        self.directive('debug', self._debug_directive)
        self.directive('enddebug', lambda content: ENDIF)
        
        # PHP blocks
        self.directive('php', self._php_directive)
        self.directive('endphp', lambda content: "")
        
        # Template macros
        self.directive('macro', self._macro_directive)
        self.directive('endmacro', lambda content: "")
        
        # Section conditionals
        self.directive('hasSection', self._has_section_directive)
        self.directive('endhasSection', lambda content: ENDIF)
        self.directive('sectionMissing', self._section_missing_directive)
        self.directive('endsectionMissing', lambda content: ENDIF)
        
        # Localization
        self.directive('lang', self._lang_directive)
        self.directive('choice', self._choice_directive)
        
        # Component advanced features
        self.directive('componentFirst', self._component_first_directive)
        self.directive('aware', self._aware_directive)
        self.directive('attributes', self._attributes_directive)
        
        # Asset management
        self.directive('vite', self._vite_directive)
        self.directive('livewireStyles', self._livewire_styles_directive)
        self.directive('livewireScripts', self._livewire_scripts_directive)
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters"""
        self.env.filters['ucfirst'] = lambda s: s[0].upper() + s[1:] if s else s
        self.env.filters['title'] = lambda s: s.title() if s else s
        self.env.filters['slug'] = lambda s: re.sub(r'[^\w\s-]', '', s).strip().replace(' ', '-').lower() if s else s
        self.env.filters['money'] = lambda s: f"${float(s):,.2f}" if s else "$0.00"
        self.env.filters['percentage'] = lambda s: f"{float(s):.1f}%" if s else "0.0%"
        self.env.filters['truncate_words'] = lambda s, num=10: ' '.join(str(s).split()[:num]) + ('...' if len(str(s).split()) > num else '') if s else ''
        self.env.filters['loop_info'] = self._create_loop_info_filter()
        self.env.filters['render_attributes'] = self._render_attributes_filter
    
    def _register_globals(self) -> None:
        """Register global template functions"""
        self.env.globals['csrf_token'] = self._csrf_token
        self.env.globals['old'] = self._old_input
        self.env.globals['route'] = self._route_helper
        self.env.globals['asset'] = self._asset_helper
        self.env.globals['config'] = self._config_helper
        self.env.globals['now'] = datetime.now
        self.env.globals['class_names'] = self._class_helper
        self.env.globals['styles'] = self._style_helper
        self.env.globals['debug_and_die'] = self._debug_and_die
        self.env.globals['dump_vars'] = self._dump_vars
        self.env.globals['__'] = self._translate  # i18n function
        self.env.globals['trans'] = self._translate
        self.env.globals['trans_choice'] = self._translate_choice
        self.env.globals['_once_blocks'] = self.once_blocks
        self.env.globals['_stacks'] = self.stacks
        self.env.globals['_fragments'] = self.fragments
        self.env.globals['_sections'] = self.current_sections
        self.env.globals['_macros'] = self.macros
        self.env.globals['debug_mode'] = self.debug
        self.env.globals['component_exists'] = self._component_exists
        self.env.globals['vite'] = self._vite_helper
        self.env.globals['livewire_styles'] = self._livewire_styles_helper
        self.env.globals['livewire_scripts'] = self._livewire_scripts_helper
    
    def _csrf_token(self) -> str:
        """Generate CSRF token (placeholder)"""
        return "csrf_token_placeholder"
    
    def _old_input(self, key: str, default: Any = None) -> Any:
        """Get old input value (placeholder)"""
        return default
    
    def _route_helper(self, name: str, **params: Any) -> str:
        """Generate route URL (placeholder)"""
        return f"/{name}"
    
    def _asset_helper(self, path: str) -> str:
        """Generate asset URL"""
        return f"/assets/{path.lstrip('/')}"
    
    def _config_helper(self, key: str, default: Any = None) -> Any:
        """Get config value (placeholder)"""
        return default
    
    def _class_helper(self, *classes: Any) -> str:
        """Conditional class helper"""
        result = []
        for cls in classes:
            if isinstance(cls, dict):
                for class_name, condition in cls.items():
                    if condition:
                        result.append(class_name)
            elif isinstance(cls, (list, tuple)):
                result.extend(str(c) for c in cls if c)
            elif cls:
                result.append(str(cls))
        return ' '.join(result)
    
    def _style_helper(self, **styles: str) -> str:
        """Conditional style helper"""
        result = []
        for property_name, value in styles.items():
            if value:
                # Convert snake_case to kebab-case
                css_property = property_name.replace('_', '-')
                result.append(f"{css_property}: {value}")
        return '; '.join(result)
    
    def _debug_and_die(self, *variables: Any) -> str:
        """Debug and die helper"""
        import json
        output = "<pre style='background: #1a1a1a; color: #ff6b6b; padding: 1rem; border-radius: 4px; font-family: monospace;'>"
        output += "DEBUG & DIE\n" + "="*50 + "\n"
        
        for i, var in enumerate(variables):
            try:
                if hasattr(var, '__dict__'):
                    var_json = json.dumps(var.__dict__, indent=2, default=str)
                else:
                    var_json = json.dumps(var, indent=2, default=str)
                output += f"Variable {i + 1}:\n{var_json}\n\n"
            except Exception:
                output += f"Variable {i + 1}:\n{str(var)}\n\n"
        
        output += "</pre>"
        return output
    
    def _dump_vars(self, *variables: Any) -> str:
        """Dump variables helper"""
        import json
        output = "<div style='background: #f8f9fa; border: 1px solid #dee2e6; padding: 1rem; margin: 1rem 0; border-radius: 4px;'>"
        output += "<strong>DUMP:</strong><br>"
        
        for i, var in enumerate(variables):
            try:
                if hasattr(var, '__dict__'):
                    var_json = json.dumps(var.__dict__, indent=2, default=str)
                else:
                    var_json = json.dumps(var, indent=2, default=str)
                output += f"<pre>{var_json}</pre>"
            except Exception:
                output += f"<pre>{str(var)}</pre>"
        
        output += "</div>"
        return output
    
    def _translate(self, key: str, replacements: Optional[Dict[str, Any]] = None, locale: Optional[str] = None) -> str:
        """Translation helper (placeholder)"""
        # In a real implementation, this would look up translations
        text = key  # Fallback to key if translation not found
        
        if replacements:
            for placeholder, value in replacements.items():
                text = text.replace(f":{placeholder}", str(value))
        
        return text
    
    def _translate_choice(self, key: str, count: int, replacements: Optional[Dict[str, Any]] = None, locale: Optional[str] = None) -> str:
        """Pluralization helper (placeholder)"""
        # Simple pluralization logic
        if count == 1:
            return self._translate(f"{key}.singular", replacements, locale)
        else:
            return self._translate(f"{key}.plural", replacements, locale)
    
    def _component_exists(self, component_name: str) -> bool:
        """Check if a component exists"""
        component_path = f"components/{component_name}.blade.html"
        for template_dir in self.template_paths:
            if (Path(template_dir) / component_path).exists():
                return True
        return False
    
    def _vite_helper(self, *assets: str) -> str:
        """Vite asset helper (placeholder)"""
        result = []
        for asset in assets:
            if asset.endswith('.css'):
                result.append(f'<link rel="stylesheet" href="/build/{asset}">')
            elif asset.endswith('.js'):
                result.append(f'<script type="module" src="/build/{asset}"></script>')
        return '\n'.join(result)
    
    def _livewire_styles_helper(self) -> str:
        """Livewire styles helper (placeholder)"""
        return '<style>[wire\\:loading] { display: none; }</style>'
    
    def _livewire_scripts_helper(self) -> str:
        """Livewire scripts helper (placeholder)"""
        return '<script src="/livewire/livewire.js" defer></script>'
    
    def _create_blade_loader(self, template_paths: List[str]) -> 'BladeFileSystemLoader':
        """Create custom Blade loader"""
        return BladeFileSystemLoader(template_paths, self)
    
    def directive(self, name: str, callback: Callable[[str], str]) -> None:
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
        return "{% if not current_user or not current_user.can('" + permission + "') %}"
    
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
        if ',' in content:
            parts = content.split(',', 1)
            template = parts[0].strip().strip("'\"")
        else:
            template = content.strip().strip("'\"")
        
        # Add .blade.html extension if not present
        if not template.endswith('.blade.html'):
            template += '.blade.html'
            
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
    
    def _include_first_directive(self, content: str) -> str:
        """Convert @includeFirst to Jinja2"""
        # Parse includeFirst(['template1', 'template2'])
        templates = content.strip().strip('[]').replace("'", '').replace('"', '').split(',')
        template_checks = []
        for template in templates:
            template = template.strip()
            template_checks.append(f"'{template}'")
        return f"{{% for _template in [{', '.join(template_checks)}] %}}{{% if _template in get_template_names() %}}{{% include _template %}}{{% break %}}{{% endif %}}{{% endfor %}}"
    
    def _error_directive(self, content: str) -> str:
        """Convert @error to Jinja2"""
        field = content.strip().strip("'\"")
        return f"{{% if errors and '{field}' in errors %}}"
    
    def _isset_directive(self, content: str) -> str:
        """Convert @isset to Jinja2"""
        variable = content.strip().strip('()')
        return f"{{% if {variable} is defined and {variable} is not none %}}"
    
    def _empty_directive(self, content: str) -> str:
        """Convert @empty to Jinja2"""
        variable = content.strip().strip('()')
        return f"{{% if {variable} is not defined or not {variable} or ({variable} is iterable and {variable}|length == 0) %}}"
    
    def _switch_directive(self, content: str) -> str:
        """Convert @switch to Jinja2"""
        variable = content.strip().strip('()')
        return f"{{% set _switch_var = {variable} %}}{{% if false %}}{{# switch start #}}"
    
    def _case_directive(self, content: str) -> str:
        """Convert @case to Jinja2"""
        value = content.strip().strip('()')
        return f"{{% elif _switch_var == {value} %}}"
    
    def _production_directive(self, content: str) -> str:
        """Convert @production to Jinja2"""
        return "{% if config('app.env') == 'production' %}"
    
    def _env_directive(self, content: str) -> str:
        """Convert @env to Jinja2"""
        environments = content.strip().strip('()')
        if ',' in environments:
            env_list = [env.strip().strip("'\"") for env in environments.split(',')]
            env_check = ' or '.join([f"config('app.env') == '{env}'" for env in env_list])
            return f"{{% if {env_check} %}}"
        else:
            env = environments.strip("'\"")
            return f"{{% if config('app.env') == '{env}' %}}"
    
    def _hasrole_directive(self, content: str) -> str:
        """Convert @hasrole to Jinja2"""
        role = content.strip().strip("'\"")
        return f"{{% if current_user and current_user.has_role('{role}') %}}"
    
    def _hasanyrole_directive(self, content: str) -> str:
        """Convert @hasanyrole to Jinja2"""
        roles = content.strip().strip('[]')
        return f"{{% if current_user and current_user.has_any_role([{roles}]) %}}"
    
    def _haspermission_directive(self, content: str) -> str:
        """Convert @haspermission to Jinja2"""
        permission = content.strip().strip("'\"")
        return f"{{% if current_user and current_user.can('{permission}') %}}"
    
    def _dd_directive(self, content: str) -> str:
        """Debug and die directive"""
        variables = content.strip() if content else 'None'
        return f"{{{{ debug_and_die({variables}) }}}}"
    
    def _dump_directive(self, content: str) -> str:
        """Dump variables directive"""
        variables = content.strip() if content else 'None'
        return f"{{{{ dump_vars({variables}) }}}}"
    
    def _livewire_directive(self, content: str) -> str:
        """Livewire component directive"""
        component = content.strip().strip("'\"")
        return f'<livewire:{component} />'
    
    def _entangle_directive(self, content: str) -> str:
        """Entangle directive for Alpine.js"""
        variable = content.strip().strip("'\"")
        return f"@entangle('{variable}')"
    
    def _once_directive(self, content: str) -> str:
        """Once directive - render content only once per request"""
        block_id = content.strip().strip("'\"") if content else "default"
        return f"{{% if '{block_id}' not in _once_blocks %}}{{% set _ = _once_blocks.add('{block_id}') %}}"
    
    def _prepend_directive(self, content: str) -> str:
        """Prepend directive - add to beginning of stack"""
        stack_name = content.strip().strip("'\"")
        return f"{{% set _prepend_stack = '{stack_name}' %}}"
    
    def _fragment_directive(self, content: str) -> str:
        """Fragment directive - define reusable template fragments"""
        fragment_name = content.strip().strip("'\"")
        return f"{{% set _current_fragment = '{fragment_name}' %}}"
    
    def _show_directive(self, content: str) -> str:
        """Show directive - immediately output section content"""
        return "{{ _current_section_content | safe }}"
    
    def _slot_directive(self, content: str) -> str:
        """Slot directive for component slots"""
        if ':' in content:
            # Named slot: @slot('name', $data)
            parts = content.split(':', 1)
            slot_name = parts[0].strip().strip("'\"")
            slot_data = parts[1].strip()
            return f"{{% set _slot_{slot_name} = {slot_data} %}}"
        else:
            slot_name = content.strip().strip("'\"")
            return f"{{% set _current_slot = '{slot_name}' %}}"
    
    def _props_directive(self, content: str) -> str:
        """Props directive for component properties with defaults and validation"""
        # Parse props array with defaults: ['title', 'description' => 'Default desc', 'required' => true]
        if content.strip().startswith('[') and content.strip().endswith(']'):
            # Array syntax
            return f"{{% set _props = {content} %}}{{% set _validated_props = validate_props(_props) %}}"
        else:
            # Simple list
            props_list = [p.strip().strip("'\"") for p in content.split(',')]
            return f"{{% set _props = {props_list} %}}"
    
    def _class_directive(self, content: str) -> str:
        """Class directive for conditional classes"""
        return f"{{{{ class_names({content}) }}}}"
    
    def _style_directive(self, content: str) -> str:
        """Style directive for conditional styles"""
        return f"{{{{ styles({content}) }}}}"
    
    def _old_directive(self, content: str) -> str:
        """Old directive for form input values"""
        field_name = content.strip().strip("'\"")
        if ',' in field_name:
            field, default = [x.strip().strip("'\"") for x in field_name.split(',', 1)]
            return f"{{{{ old('{field}', '{default}') }}}}"
        return f"{{{{ old('{field_name}') }}}}"
    
    def _errors_directive(self, content: str) -> str:
        """Errors directive for form validation errors"""
        if content:
            field_name = content.strip().strip("'\"")
            return f"{{{{ errors.get('{field_name}', []) | join('<br>') | safe }}}}"
        return f"{{{{ errors | tojson | safe }}}}"
    
    def _debug_directive(self, content: str) -> str:
        """Debug directive - only show in debug mode"""
        return "{% if debug_mode %}"
    
    def _include_unless_directive(self, content: str) -> str:
        """Convert @includeUnless to Jinja2"""
        # Parse includeUnless($condition, 'template')
        parts = content.split(',', 1)
        if len(parts) == 2:
            condition = parts[0].strip()
            template = parts[1].strip().strip(')').strip("'\"")
            if not template.endswith('.blade.html'):
                template += '.blade.html'
            return f"{{% if not ({condition}) %}}{{% include '{template}' %}}{{% endif %}}"
        return ""
    
    def _each_directive(self, content: str) -> str:
        """Convert @each to Jinja2 - iterate array with empty state"""
        # Parse @each('view', $items, 'item', 'empty-view')
        parts = [p.strip().strip("'\"") for p in content.split(',')]
        if len(parts) >= 3:
            view_name = parts[0]
            items_var = parts[1]
            item_var = parts[2]
            empty_view = parts[3] if len(parts) > 3 else None
            
            result = f"{{% for {item_var} in {items_var} %}}{{% include '{view_name}.blade.html' %}}{{% endfor %}}"
            if empty_view:
                result = f"{{% if {items_var} %}}" + result + f"{{% else %}}{{% include '{empty_view}.blade.html' %}}{{% endif %}}"
            
            return result
        return ""
    
    def _php_directive(self, content: str) -> str:
        """PHP directive - convert to Jinja2 set statement"""
        return f"{{% set _php_block %}}"
    
    def _macro_directive(self, content: str) -> str:
        """Macro directive for reusable code snippets"""
        macro_name = content.strip().strip("'\"")
        return f"{{% macro {macro_name}() %}}"
    
    def _has_section_directive(self, content: str) -> str:
        """Check if section exists"""
        section_name = content.strip().strip("'\"")
        return f"{{% if '{section_name}' in _sections %}}"
    
    def _section_missing_directive(self, content: str) -> str:
        """Check if section is missing"""
        section_name = content.strip().strip("'\"")
        return f"{{% if '{section_name}' not in _sections %}}"
    
    def _lang_directive(self, content: str) -> str:
        """Language/localization directive"""
        # Parse @lang('key', ['param' => 'value'])
        parts = content.split(',', 1)
        key = parts[0].strip().strip("'\"")
        replacements = parts[1].strip() if len(parts) > 1 else '{}'
        return f"{{{{ __('{key}', {replacements}) }}}}"
    
    def _choice_directive(self, content: str) -> str:
        """Choice directive for pluralization"""
        # Parse @choice('key', $count, ['param' => 'value'])
        parts = content.split(',')
        if len(parts) >= 2:
            key = parts[0].strip().strip("'\"")
            count = parts[1].strip()
            replacements = parts[2].strip() if len(parts) > 2 else '{}'
            return f"{{{{ trans_choice('{key}', {count}, {replacements}) }}}}"
        return ""
    
    def _component_first_directive(self, content: str) -> str:
        """Component first directive - try multiple components"""
        components = content.strip().strip('[]').split(',')
        components = [c.strip().strip("'\"") for c in components]
        
        result = ""
        for i, component in enumerate(components):
            if i == 0:
                result = f"{{% if component_exists('{component}') %}}{{% include 'components/{component}.blade.html' %}}"
            else:
                result += f"{{% elif component_exists('{component}') %}}{{% include 'components/{component}.blade.html' %}}"
        
        result += "{% endif %}"
        return result
    
    def _aware_directive(self, content: str) -> str:
        """Aware directive for component data awareness"""
        variables = content.strip().strip('[]')
        return f"{{% set _aware_vars = [{variables}] %}}"
    
    def _attributes_directive(self, content: str) -> str:
        """Attributes directive for component attribute rendering"""
        return "{{ _attributes | render_attributes | safe }}"
    
    def _vite_directive(self, content: str) -> str:
        """Vite asset directive"""
        assets = content.strip().strip('[]')
        return f"{{{{ vite({assets}) | safe }}}}"
    
    def _livewire_styles_directive(self, content: str) -> str:
        """Livewire styles directive"""
        return "{{ livewire_styles() | safe }}"
    
    def _livewire_scripts_directive(self, content: str) -> str:
        """Livewire scripts directive"""
        return "{{ livewire_scripts() | safe }}"
    
    def _create_loop_info_filter(self) -> Callable[..., Any]:
        """Create a filter that provides Laravel-style loop information"""
        def loop_info_filter(loop_obj: Any) -> Dict[str, Any]:
            """Convert Jinja2 loop object to Laravel-style loop object"""
            if not hasattr(loop_obj, 'index'):
                return {}
            
            return {
                'index': loop_obj.index,       # 1-based index
                'index0': loop_obj.index0,     # 0-based index  
                'revindex': loop_obj.revindex, # reverse 1-based
                'revindex0': loop_obj.revindex0, # reverse 0-based
                'first': loop_obj.first,       # is first item
                'last': loop_obj.last,         # is last item
                'length': loop_obj.length,     # total length
                'count': loop_obj.length,      # alias for length
                'remaining': loop_obj.length - loop_obj.index, # remaining items
                'depth': getattr(loop_obj, 'depth', 1), # nesting depth
                'parent': getattr(loop_obj, 'parent', None), # parent loop
                'even': loop_obj.index % 2 == 0,  # is even iteration
                'odd': loop_obj.index % 2 == 1,   # is odd iteration
            }
        
        return loop_info_filter
    
    def _render_attributes_filter(self, attributes: Dict[str, Any]) -> str:
        """Render HTML attributes from dictionary"""
        if not attributes:
            return ""
        
        result = []
        for key, value in attributes.items():
            if value is None or value is False:
                continue
            elif value is True:
                result.append(key)
            else:
                escaped_value = str(value).replace('"', '&quot;')
                result.append(f'{key}="{escaped_value}"')
        
        return ' '.join(result)
    
    def compile_blade(self, template_content: str) -> str:
        """Convert Blade syntax to Jinja2 syntax"""
        
        # Handle @extends
        def fix_extends_path(match: re.Match[str]) -> str:
            template_name = match.group(1)
            # Add .blade.html extension if not present
            if not template_name.endswith('.blade.html'):
                template_name += '.blade.html'
            return f"{{% extends '{template_name}' %}}"
        
        template_content = re.sub(
            r"@extends\s*\(\s*['\"](.+?)['\"]\s*\)",
            fix_extends_path,
            template_content
        )
        
        # Handle @section and @endsection with enhanced features
        def section_replacer(match: re.Match[str]) -> str:
            section_name = match.group(1)
            section_content = match.group(2) if len(match.groups()) > 1 else None
            
            if section_content:
                # Inline section: @section('name', 'content')
                return f"{{% block {section_name} %}}{section_content}{{% endblock %}}"
            else:
                # Block section: @section('name')
                return f"{{% block {section_name} %}}"
        
        template_content = re.sub(
            r"@section\s*\(\s*['\"](.+?)['\"]\s*(?:,\s*['\"](.+?)['\"]\s*)?\)",
            section_replacer,
            template_content
        )
        template_content = template_content.replace("@endsection", "{% endblock %}")
        
        # Handle @yield with default content
        def yield_replacer(match: re.Match[str]) -> str:
            section_name = match.group(1)
            default_content = match.group(2) if len(match.groups()) > 1 else ""
            
            if default_content:
                return f"{{% block {section_name} %}}{default_content}{{% endblock %}}"
            else:
                return f"{{% block {section_name} %}}{{% endblock %}}"
        
        template_content = re.sub(
            r"@yield\s*\(\s*['\"](.+?)['\"]\s*(?:,\s*['\"](.+?)['\"]\s*)?\)",
            yield_replacer,
            template_content
        )
        
        # Handle @parent
        template_content = template_content.replace("@parent", "{{ super() }}")
        
        # Handle @overwrite (replaces section completely)
        template_content = re.sub(r"@overwrite\s*", "{% endblock %}", template_content)
        
        # Handle @append (appends to parent section)  
        template_content = re.sub(r"@append\s*", "{{ super() }}{% endblock %}", template_content)
        
        # Handle @if, @elseif, @else, @endif
        template_content = re.sub(r"@if\s*\(\s*(.+?)\s*\)", r"{% if \1 %}", template_content)
        template_content = re.sub(r"@elseif\s*\(\s*(.+?)\s*\)", r"{% elif \1 %}", template_content)
        template_content = template_content.replace("@else", "{% else %}")
        template_content = template_content.replace("@endif", "{% endif %}")
        
        # Handle @for, @endfor
        template_content = re.sub(
            r"@for\s*\(\s*(.+?)\s*\)",
            lambda m: self._convert_php_for_to_jinja(m.group(1)),
            template_content
        )
        template_content = template_content.replace("@endfor", "{% endfor %}")
        
        # Handle @foreach, @endforeach with loop variables
        def foreach_replacer(match: re.Match[str]) -> str:
            items = match.group(1).strip()
            item_vars = match.group(2).strip()
            
            # Handle multiple variables: foreach($users as $key => $user)
            if '=>' in item_vars:
                key_var, value_var = [v.strip() for v in item_vars.split('=>', 1)]
                return f"{{% for {key_var}, {value_var} in {items}.items() %}}"
            else:
                return f"{{% for {item_vars} in {items} %}}"
        
        template_content = re.sub(
            r"@foreach\s*\(\s*(.+?)\s+as\s+(.+?)\s*\)",
            foreach_replacer,
            template_content
        )
        template_content = template_content.replace("@endforeach", "{% endfor %}")
        
        # Handle @while, @endwhile (note: Jinja2 doesn't have while, use for with break)
        template_content = re.sub(r"@while\s*\(\s*(.+?)\s*\)", r"{% set _while_condition = \1 %}{% if _while_condition %}", template_content)
        template_content = re.sub(r"@endwhile", "{% endif %}", template_content)
        
        # Handle @break and @continue
        template_content = template_content.replace("@break", "{% break %}")
        template_content = template_content.replace("@continue", "{% continue %}")
        
        # Handle @php and @endphp blocks
        template_content = re.sub(
            r"@php\s*\n?(.*?)\n?@endphp",
            r"{% set _ = '' %}",  # PHP blocks are converted to no-op
            template_content,
            flags=re.DOTALL
        )
        
        # Handle @macro and @endmacro
        def macro_replacer(match: re.Match[str]) -> str:
            macro_name = match.group(1)
            macro_content = match.group(2)
            self.macros[macro_name] = macro_content
            return f"{{% macro {macro_name}() %}}{macro_content}{{% endmacro %}}"
        
        template_content = re.sub(
            r"@macro\s*\(\s*['\"](.+?)['\"]\s*\)(.*?)@endmacro",
            macro_replacer,
            template_content,
            flags=re.DOTALL
        )
        
        # Handle @push and @endpush (stack sections)
        def push_replacer(match: re.Match[str]) -> str:
            stack_name = match.group(1)
            return f"{{% if '{stack_name}' not in _stacks %}}{{% set _ = _stacks.update({{'{stack_name}': []}}) %}}{{% endif %}}"
        
        template_content = re.sub(
            r"@push\s*\(\s*['\"](.+?)['\"]\s*\)",
            push_replacer,
            template_content
        )
        template_content = template_content.replace("@endpush", "")
        
        # Handle @prepend
        def prepend_replacer(match: re.Match[str]) -> str:
            stack_name = match.group(1)
            return f"{{% if '{stack_name}' not in _stacks %}}{{% set _ = _stacks.update({{'{stack_name}': []}}) %}}{{% endif %}}"
        
        template_content = re.sub(
            r"@prepend\s*\(\s*['\"](.+?)['\"]\s*\)",
            prepend_replacer,
            template_content
        )
        
        # Handle @stack
        template_content = re.sub(
            r"@stack\s*\(\s*['\"](.+?)['\"]\s*\)",
            r"{% for _item in _stacks.get('\1', []) %}{{ _item | safe }}{% endfor %}",
            template_content
        )
        
        # Handle custom directives
        for name, directive in self.directives.items():
            pattern = rf"@{name}(?:\s*\(\s*(.+?)\s*\))?"
            # Create a closure to capture the directive callback properly
            def make_replacer(callback: Callable[..., str]) -> Callable[[re.Match[str]], str]:
                return lambda m: callback(m.group(1) or '')
            
            template_content = re.sub(
                pattern,
                make_replacer(directive.callback),
                template_content
            )
        
        # Handle Blade comments {{-- comment --}}
        template_content = template_content.replace('{{--', '{#').replace('--}}', '#}')
        
        # Handle unescaped output {!! variable !!}
        template_content = re.sub(r"\{\!\!\s*(.+?)\s*\!\!\}", r"{{ \1 | safe }}", template_content)
        
        # Handle x-components syntax: <x-component-name attributes>
        def component_replacer(match: re.Match[str]) -> str:
            tag_name = match.group(1)
            attributes = match.group(2).strip() if match.group(2) else ""
            is_self_closing = match.group(3) is not None
            
            component_name = tag_name.replace('-', '_')
            
            if attributes:
                return f"{{% include 'components/{tag_name}.blade.html' %}}"
            else:
                return f"{{% include 'components/{tag_name}.blade.html' %}}"
        
        # Match <x-component /> and <x-component>
        template_content = re.sub(
            r'<x-([a-zA-Z0-9\-_]+)([^>]*?)(\s*/\s*)?>',
            component_replacer,
            template_content
        )
        
        # Handle closing component tags </x-component>
        template_content = re.sub(r'</x-[a-zA-Z0-9\-_]+>', '', template_content)
        
        # Handle component slots <x-slot name="name">content</x-slot>
        def slot_replacer(match: re.Match[str]) -> str:
            slot_name = match.group(1).strip('"\'') if match.group(1) else 'default'
            slot_content = match.group(2) if match.group(2) else ''
            return f"{{% set _{slot_name}_slot %}}{slot_content}{{% endset %}}"
        
        template_content = re.sub(
            r'<x-slot(?:\s+name=["\']([^"\']*)["\'])?>(.*?)</x-slot>',
            slot_replacer,
            template_content,
            flags=re.DOTALL
        )
        
        # Handle components with content
        def component_with_content_replacer(match: re.Match[str]) -> str:
            tag_name = match.group(1)
            attributes = match.group(2).strip() if match.group(2) else ""
            content = match.group(3) if match.group(3) else ""
            
            # For now, just include the component without slot handling
            return f"{{% include 'components/{tag_name}.blade.html' %}}"
        
        # Match components with content
        template_content = re.sub(
            r'<x-([a-zA-Z0-9\-_]+)([^>]*?)>(.*?)</x-\1>',
            component_with_content_replacer,
            template_content,
            flags=re.DOTALL
        )
        
        # Handle components
        template_content = self.component_compiler.compile_components(template_content)
        
        # Handle escaped output {{ variable }} (already Jinja2 compatible)
        
        return template_content
    
    def _convert_php_for_to_jinja(self, for_content: str) -> str:
        """Convert PHP-style for loop to Jinja2"""
        # Parse for($i = 0; $i < 10; $i++)
        match = re.match(r'\s*\$?(\w+)\s*=\s*(\d+);\s*\$?\w+\s*<\s*(\d+);\s*\$?\w+\+\+', for_content)
        if match:
            var, start, end = match.groups()
            return f"{{% for {var} in range({start}, {end}) %}}"
        
        # Fallback for other for loop patterns
        return "{% for item in range(10) %}"
    
    def share(self, key: str, value: Any) -> None:
        """Share data with all views"""
        self.shared_data[key] = value
    
    def composer(self, view_pattern: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a view composer"""
        if view_pattern not in self.view_composers:
            self.view_composers[view_pattern] = []
        self.view_composers[view_pattern].append(callback)
    
    def _apply_composers(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply view composers to context"""
        for pattern, composers in self.view_composers.items():
            if self._matches_pattern(template_name, pattern):
                for composer in composers:
                    composer_result = composer(context)
                    if composer_result and isinstance(composer_result, dict):
                        context.update(composer_result)
        return context
    
    def _matches_pattern(self, template_name: str, pattern: str) -> bool:
        """Check if template name matches pattern"""
        if pattern == '*':
            return True
        pattern = pattern.replace('*', '.*')
        return bool(re.match(pattern, template_name))
    
    def _get_cache_key(self, template_path: str) -> str:
        """Generate cache key for template"""
        return hashlib.md5(template_path.encode()).hexdigest()
    
    def _get_cached_template(self, template_path: str) -> Optional[Template]:
        """Get cached compiled template"""
        if self.debug:
            return None
            
        cache_key = self._get_cache_key(template_path)
        cache_file = Path(self.cache_path) / f"{cache_key}.cache"
        
        if not cache_file.exists():
            return None
            
        try:
            template_mtime = os.path.getmtime(template_path)
            cache_mtime = os.path.getmtime(cache_file)
            
            if template_mtime > cache_mtime:
                return None
                
            # For now, disable complex caching and just return None
            # In production, you'd implement proper template caching
            return None
        except (OSError, pickle.PickleError):
            return None
    
    def _cache_template(self, template_path: str, template: Template) -> None:
        """Cache compiled template"""
        if self.debug:
            return
            
        cache_key = self._get_cache_key(template_path)
        cache_file = Path(self.cache_path) / f"{cache_key}.cache"
        
        try:
            # Store the compiled source instead of the template object
            # since Jinja2 templates can't be pickled due to closures
            template_data = {
                'source': template.source if hasattr(template, 'source') else '',
                'filename': template.filename,
                'globals': getattr(template, 'globals', {})
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(template_data, f)
        except (OSError, pickle.PickleError, AttributeError):
            pass  # Silently fail cache write
    
    def clear_cache(self) -> None:
        """Clear all cached templates"""
        cache_path = Path(self.cache_path)
        if cache_path.exists():
            for cache_file in cache_path.glob('*.cache'):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        with self._lock:
            self._template_cache.clear()
    
    def render(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a Blade template"""
        if context is None:
            context = {}
        
        # Merge shared data
        final_context = {**self.shared_data, **context}
        
        # Add service context
        service_context = self.service_provider.get_template_context()
        final_context.update(service_context)
        
        # Apply view composers
        final_context = self._apply_composers(template_name, final_context)
        
        # Find template file
        template_path = self._find_template(template_name)
        
        # Try to get from cache first
        template = self._get_cached_template(template_path)
        
        if template is None:
            # Load and compile template
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            except FileNotFoundError:
                raise FileNotFoundError(f"Template '{template_name}' not found")
            
            compiled_content = self.compile_blade(template_content)
            template = self.env.from_string(compiled_content)
            
            # Cache the compiled template
            self._cache_template(template_path, template)
        
        return template.render(**final_context)
    
    def register_component(self, name: str, component_class: Union[type, str]) -> None:
        """Register a custom component"""
        self.component_registry.register(name, component_class)
    
    def get_fragment(self, name: str) -> str:
        """Get a template fragment"""
        return self.fragments.get(name, "")
    
    def clear_stacks(self) -> None:
        """Clear all template stacks"""
        self.stacks.clear()
    
    def clear_once_blocks(self) -> None:
        """Clear all @once block tracking"""
        self.once_blocks.clear()
    
    def add_to_stack(self, stack_name: str, content: str, prepend: bool = False) -> None:
        """Add content to a stack programmatically"""
        if stack_name not in self.stacks:
            self.stacks[stack_name] = []
        
        if prepend:
            self.stacks[stack_name].insert(0, content)
        else:
            self.stacks[stack_name].append(content)
    
    def get_service(self, name: str) -> Any:
        """Get a service from the service container"""
        return self.service_provider.container.get(name)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value"""
        config_service = self.get_service('config_service')
        config_service.set(key, value)
    
    def set_user(self, user: Any) -> None:
        """Set current authenticated user"""
        auth_service = self.get_service('auth')
        auth_service.set_user(user)
    
    def set_request(self, request: Any) -> None:
        """Set current request context"""
        request_service = self.get_service('request')
        request_service.set_request(request)
    
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


def blade(template_paths: Optional[List[str]] = None) -> BladeEngine:
    """Get or create global Blade engine instance"""
    global _blade_engine
    
    if _blade_engine is None or template_paths:
        if template_paths is None:
            template_paths = ['resources/views']
        _blade_engine = BladeEngine(template_paths, debug=True)  # Always debug mode in global instance
    
    return _blade_engine


def view(template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Laravel-style view helper"""
    return blade().render(template_name, context)


def view_share(key: str, value: Any) -> None:
    """Share data with all views globally"""
    blade().share(key, value)


def view_composer(view_pattern: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
    """Register a view composer globally"""
    blade().composer(view_pattern, callback)


def blade_config(key: str, value: Any = None) -> Any:
    """Get or set Blade configuration"""
    engine = blade()
    if value is not None:
        engine.set_config(key, value)
        return value
    return engine.get_service('config_service').get(key)


def blade_service(name: str) -> Any:
    """Get a service from the Blade container"""
    return blade().get_service(name)


class BladeFileSystemLoader(FileSystemLoader):
    """Custom Jinja2 loader that compiles Blade templates on the fly"""
    
    def __init__(self, searchpath: Union[str, List[str]], blade_engine: 'BladeEngine'):
        super().__init__(searchpath)
        self.blade_engine = blade_engine
    
    def get_source(self, environment: Environment, template: str) -> Tuple[str, str, Callable[[], bool]]:
        """Override to compile Blade templates"""
        source, path, uptodate = super().get_source(environment, template)
        
        # Only compile .blade.html templates
        if template.endswith('.blade.html'):
            compiled_source = self.blade_engine.compile_blade(source)
            return compiled_source, path, uptodate
        
        return source, path, uptodate