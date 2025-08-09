"""
Test Suite for Blade Engine Custom Extensions and Extensibility
Tests custom directive registration, filter additions, and plugin functionality
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Generator, Tuple, List
import os
import re

from app.View.BladeEngine import BladeEngine, BladeDirective


class TestBladeCustomDirectives:
    """Test custom directive registration and functionality"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_simple_custom_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test registration and use of simple custom directive"""
        engine, temp_dir = blade_engine
        
        # Register a simple custom directive
        def alert_directive(content: str) -> str:
            message = content.strip().strip('"\'')
            return f'<div class="alert alert-info">{message}</div>'
        
        engine.directive('alert', alert_directive)
        
        template_content = """
<div>
    <h1>Alerts Test</h1>
    @alert('This is an info message')
    @alert("This is another alert")
</div>
        """.strip()
        
        self.create_template(temp_dir, "custom_alert.blade.html", template_content)
        result = engine.render("custom_alert.blade.html")
        
        assert '<div class="alert alert-info">This is an info message</div>' in result
        assert '<div class="alert alert-info">This is another alert</div>' in result
    
    def test_parametrized_custom_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom directive with multiple parameters"""
        engine, temp_dir = blade_engine
        
        # Register directive that handles multiple parameters
        def button_directive(content: str) -> str:
            # Parse parameters like: 'primary', 'Submit', 'type=submit'
            params = [p.strip().strip('"\'') for p in content.split(',')]
            
            style = params[0] if len(params) > 0 else 'default'
            text = params[1] if len(params) > 1 else 'Button'
            button_type = 'button'
            
            # Look for type parameter
            for param in params[2:]:
                if 'type=' in param:
                    button_type = param.split('=')[1].strip()
            
            return f'<button type="{button_type}" class="btn btn-{style}">{text}</button>'
        
        engine.directive('button', button_directive)
        
        template_content = """
<form>
    @button('primary', 'Submit', 'type=submit')
    @button('secondary', 'Cancel')
    @button('danger', 'Delete', 'type=button')
</form>
        """.strip()
        
        self.create_template(temp_dir, "custom_button.blade.html", template_content)
        result = engine.render("custom_button.blade.html")
        
        assert 'class="btn btn-primary"' in result
        assert 'type="submit"' in result
        assert '>Submit<' in result
        assert 'class="btn btn-secondary"' in result
        assert '>Cancel<' in result
        assert 'class="btn btn-danger"' in result
        assert '>Delete<' in result
    
    def test_conditional_custom_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom directive with conditional logic"""
        engine, temp_dir = blade_engine
        
        # Register directive that generates conditional content
        def feature_flag_directive(content: str) -> str:
            flag_name = content.strip().strip('"\'')
            return f"{{% if features.get('{flag_name}', False) %}}"
        
        def end_feature_directive(content: str) -> str:
            return "{% endif %}"
        
        engine.directive('feature', feature_flag_directive)
        engine.directive('endfeature', end_feature_directive)
        
        template_content = """
<div>
    <h1>Feature Flags</h1>
    
    @feature('new_ui')
        <div class="new-ui">New UI is enabled!</div>
    @endfeature
    
    @feature('beta_features')
        <div class="beta">Beta features are available</div>
    @endfeature
    
    @feature('disabled_feature')
        <div>This should not appear</div>
    @endfeature
</div>
        """.strip()
        
        self.create_template(temp_dir, "feature_flags.blade.html", template_content)
        
        context = {
            'features': {
                'new_ui': True,
                'beta_features': True,
                'disabled_feature': False
            }
        }
        
        result = engine.render("feature_flags.blade.html", context)
        
        assert "New UI is enabled!" in result
        assert "Beta features are available" in result
        assert "This should not appear" not in result
    
    def test_nested_custom_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test nesting custom directives"""
        engine, temp_dir = blade_engine
        
        # Register card and card-body directives
        def card_directive(content: str) -> str:
            title = content.strip().strip('"\'') if content.strip() else ''
            card_html = '<div class="card">'
            if title:
                card_html += f'<div class="card-header">{title}</div>'
            return card_html
        
        def card_body_directive(content: str) -> str:
            return '<div class="card-body">'
        
        def end_card_directive(content: str) -> str:
            return '</div>'  # Close card
        
        def end_card_body_directive(content: str) -> str:
            return '</div>'  # Close card-body
        
        engine.directive('card', card_directive)
        engine.directive('cardbody', card_body_directive)
        engine.directive('endcard', end_card_directive)
        engine.directive('endcardbody', end_card_body_directive)
        
        template_content = """
<div class="container">
    @card('User Profile')
        @cardbody
            <h5>{{ user.name }}</h5>
            <p>{{ user.email }}</p>
            
            @card('Settings')
                @cardbody
                    <p>Nested card content</p>
                @endcardbody
            @endcard
        @endcardbody
    @endcard
</div>
        """.strip()
        
        self.create_template(temp_dir, "nested_cards.blade.html", template_content)
        
        context = {
            'user': {
                'name': 'John Doe',
                'email': 'john@example.com'
            }
        }
        
        result = engine.render("nested_cards.blade.html", context)
        
        assert '<div class="card">' in result
        assert '<div class="card-header">User Profile</div>' in result
        assert '<div class="card-body">' in result
        assert 'John Doe' in result
        assert 'john@example.com' in result
        assert 'Nested card content' in result
    
    def test_directive_with_context_access(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom directive that needs context access"""
        engine, temp_dir = blade_engine
        
        # Register directive that uses template context
        def user_badge_directive(content: str) -> str:
            # This is a simplified example - in real implementation,
            # you'd need to pass context through the directive system
            return """
            {% if current_user %}
                <span class="badge badge-success">{{ current_user.name }}</span>
            {% else %}
                <span class="badge badge-secondary">Guest</span>
            {% endif %}
            """.strip()
        
        engine.directive('userbadge', user_badge_directive)
        
        template_content = """
<nav>
    <div class="navbar">
        @userbadge
    </div>
</nav>
        """.strip()
        
        self.create_template(temp_dir, "user_badge.blade.html", template_content)
        
        # Test with logged in user
        result = engine.render("user_badge.blade.html", {
            'current_user': {'name': 'Alice'}
        })
        
        assert 'badge badge-success' in result
        assert 'Alice' in result
        
        # Test with guest
        result = engine.render("user_badge.blade.html", {
            'current_user': None
        })
        
        assert 'badge badge-secondary' in result
        assert 'Guest' in result


class TestBladeCustomFilters:
    """Test custom filter registration and functionality"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_custom_string_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom string manipulation filters"""
        engine, temp_dir = blade_engine
        
        # Register custom filters
        def reverse_filter(s: Any) -> str:
            return str(s)[::-1] if s else ''
        
        def repeat_filter(s: Any, times: int = 2) -> str:
            return str(s) * int(times) if s else ''
        
        def camel_case_filter(s: Any) -> str:
            if not s:
                return ''
            words = str(s).replace('_', ' ').replace('-', ' ').split()
            return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
        
        engine.env.filters['reverse'] = reverse_filter
        engine.env.filters['repeat'] = repeat_filter  
        engine.env.filters['camelcase'] = camel_case_filter
        
        template_content = """
<div>
    <p>Original: {{ text }}</p>
    <p>Reversed: {{ text | reverse }}</p>
    <p>Repeated: {{ text | repeat(3) }}</p>
    <p>Camel Case: {{ snake_text | camelcase }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "string_filters.blade.html", template_content)
        
        context = {
            'text': 'hello',
            'snake_text': 'hello_world_test'
        }
        
        result = engine.render("string_filters.blade.html", context)
        
        assert 'Original: hello' in result
        assert 'Reversed: olleh' in result  
        assert 'Repeated: hellohellohello' in result
        assert 'Camel Case: helloWorldTest' in result
    
    def test_custom_date_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom date/time filters"""
        engine, temp_dir = blade_engine
        
        from datetime import datetime, timedelta
        
        # Register custom date filters
        def time_ago_filter(dt: Any) -> str:
            if not dt:
                return ''
            
            now = datetime.now()
            if isinstance(dt, str):
                # Simple string to datetime conversion
                try:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except Exception:
                    return str(dt)
            
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hours ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        
        def format_date_filter(dt: Any, format_str: str = '%Y-%m-%d') -> str:
            if not dt:
                return ''
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except Exception:
                    return str(dt)
            return dt.strftime(format_str)
        
        engine.env.filters['timeago'] = time_ago_filter
        engine.env.filters['dateformat'] = format_date_filter
        
        template_content = """
<div>
    <p>Created: {{ created_at | timeago }}</p>
    <p>Updated: {{ updated_at | dateformat('%B %d, %Y') }}</p>
    <p>Due Date: {{ due_date | dateformat('%Y-%m-%d %H:%M') }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "date_filters.blade.html", template_content)
        
        now = datetime.now()
        context = {
            'created_at': now - timedelta(hours=2),
            'updated_at': now - timedelta(days=5),
            'due_date': now + timedelta(days=7)
        }
        
        result = engine.render("date_filters.blade.html", context)
        
        assert 'hours ago' in result
        assert 'Created:' in result
        assert 'Updated:' in result
        assert 'Due Date:' in result
    
    def test_custom_collection_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom filters for collections/arrays"""
        engine, temp_dir = blade_engine
        
        # Register collection filters
        def pluck_filter(items: Any, key: Any) -> List[Any]:
            """Pluck a key from each item in a collection"""
            if not items:
                return []
            result = []
            for item in items:
                if isinstance(item, dict) and key in item:
                    result.append(item[key])
                elif hasattr(item, key):
                    result.append(getattr(item, key))
            return result
        
        def where_filter(items: Any, key: Any, value: Any) -> List[Any]:
            """Filter items where key equals value"""
            if not items:
                return []
            result = []
            for item in items:
                if isinstance(item, dict):
                    if item.get(key) == value:
                        result.append(item)
                elif hasattr(item, key):
                    if getattr(item, key) == value:
                        result.append(item)
            return result
        
        def chunk_filter(items: Any, size: Any) -> List[Any]:
            """Split collection into chunks"""
            if not items:
                return []
            size = int(size)
            return [items[i:i + size] for i in range(0, len(items), size)]
        
        engine.env.filters['pluck'] = pluck_filter
        engine.env.filters['where'] = where_filter
        engine.env.filters['chunk'] = chunk_filter
        
        template_content = """
<div>
    <h3>All Names:</h3>
    <ul>
    @foreach(users | pluck('name') as name)
        <li>{{ name }}</li>
    @endforeach
    </ul>
    
    <h3>Active Users:</h3>
    <ul>
    @foreach(users | where('active', true) as user)
        <li>{{ user.name }} ({{ user.email }})</li>
    @endforeach
    </ul>
    
    <h3>Users in Groups:</h3>
    @foreach(users | chunk(2) as group)
        <div class="group">
        @foreach(group as user)
            <span>{{ user.name }}</span>
        @endforeach
        </div>
    @endforeach
</div>
        """.strip()
        
        self.create_template(temp_dir, "collection_filters.blade.html", template_content)
        
        users = [
            {'name': 'Alice', 'email': 'alice@test.com', 'active': True},
            {'name': 'Bob', 'email': 'bob@test.com', 'active': False}, 
            {'name': 'Carol', 'email': 'carol@test.com', 'active': True},
            {'name': 'Dave', 'email': 'dave@test.com', 'active': True}
        ]
        
        result = engine.render("collection_filters.blade.html", {'users': users})
        
        # Check pluck filter
        assert 'Alice' in result
        assert 'Bob' in result
        assert 'Carol' in result
        assert 'Dave' in result
        
        # Check where filter (active users only)
        assert 'alice@test.com' in result
        assert 'carol@test.com' in result  
        assert 'dave@test.com' in result
        # Bob should not appear in active users section


class TestBladeExtensibilityArchitecture:
    """Test the extensibility architecture of Blade engine"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_plugin_like_extension_system(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test implementing a plugin-like extension system"""
        engine, temp_dir = blade_engine
        
        class FormPlugin:
            """Example plugin that adds form-related directives"""
            
            def __init__(self, blade_engine: BladeEngine) -> None:
                self.engine = blade_engine
                self.register_directives()
            
            def register_directives(self) -> None:
                self.engine.directive('form', self.form_directive)
                self.engine.directive('endform', self.end_form_directive)
                self.engine.directive('input', self.input_directive)
                self.engine.directive('textarea', self.textarea_directive)
                self.engine.directive('select', self.select_directive)
            
            def form_directive(self, content: str) -> str:
                # Parse form attributes
                params = content.strip()
                if params:
                    return f'<form {params}>'
                return '<form>'
            
            def end_form_directive(self, content: str) -> str:
                return '</form>'
            
            def input_directive(self, content: str) -> str:
                # Parse: type, name, value, attributes
                parts = [p.strip().strip('"\'') for p in content.split(',')]
                input_type = parts[0] if len(parts) > 0 else 'text'
                name = parts[1] if len(parts) > 1 else ''
                value = parts[2] if len(parts) > 2 else ''
                
                attrs = f'type="{input_type}" name="{name}"'
                if value:
                    attrs += f' value="{value}"'
                
                return f'<input {attrs}>'
            
            def textarea_directive(self, content: str) -> str:
                params = content.strip().strip('"\'')
                return f'<textarea name="{params}">{{{{ old(\'{params}\') }}</textarea>'
            
            def select_directive(self, content: str) -> str:
                name = content.strip().strip('"\'')
                return f'<select name="{name}">'
        
        # Install the plugin
        form_plugin = FormPlugin(engine)
        
        template_content = """
@form('method="POST" action="/submit"')
    <div class="form-group">
        <label>Name:</label>
        @input('text', 'name', '{{ old("name") }}')
    </div>
    
    <div class="form-group">
        <label>Email:</label>
        @input('email', 'email')
    </div>
    
    <div class="form-group">
        <label>Message:</label>
        @textarea('message')
    </div>
    
    <button type="submit">Submit</button>
@endform
        """.strip()
        
        self.create_template(temp_dir, "plugin_form.blade.html", template_content)
        
        result = engine.render("plugin_form.blade.html")
        
        assert '<form method="POST" action="/submit">' in result
        assert '<input type="text" name="name"' in result
        assert '<input type="email" name="email"' in result
        assert '<textarea name="message">' in result
        assert '</form>' in result
    
    def test_chainable_filter_extensions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test chainable filter extension system"""
        engine, temp_dir = blade_engine
        
        class StringUtilsPlugin:
            """Plugin that adds chainable string utilities"""
            
            def __init__(self, blade_engine: BladeEngine) -> None:
                self.engine = blade_engine
                self.register_filters()
            
            def register_filters(self) -> None:
                self.engine.env.filters['trim_start'] = lambda s, chars=' ': str(s).lstrip(chars)
                self.engine.env.filters['trim_end'] = lambda s, chars=' ': str(s).rstrip(chars)
                self.engine.env.filters['pad_left'] = lambda s, width, char=' ': str(s).rjust(int(width), char)
                self.engine.env.filters['pad_right'] = lambda s, width, char=' ': str(s).ljust(int(width), char)
                self.engine.env.filters['pascal_case'] = self.pascal_case_filter
                self.engine.env.filters['kebab_case'] = self.kebab_case_filter
            
            def pascal_case_filter(self, s: Any) -> str:
                if not s:
                    return ''
                words = re.sub(r'[_\-\s]+', ' ', str(s)).split()
                return ''.join(word.capitalize() for word in words)
            
            def kebab_case_filter(self, s: Any) -> str:
                if not s:
                    return ''
                # Convert PascalCase and camelCase to kebab-case
                s = re.sub(r'([A-Z])', r'-\1', str(s)).lower()
                s = re.sub(r'[_\s]+', '-', s)
                return s.strip('-')
        
        # Install the plugin
        string_utils = StringUtilsPlugin(engine)
        
        template_content = """
<div>
    <p>Original: "{{ text }}"</p>
    <p>Trimmed: "{{ text | trim_start | trim_end }}"</p>
    <p>Padded: "{{ short_text | pad_left(10, '*') | pad_right(15, '-') }}"</p>
    <p>Pascal: {{ snake_text | pascal_case }}</p>
    <p>Kebab: {{ pascal_text | kebab_case }}</p>
    <p>Chained: {{ messy_text | trim_start | pascal_case | kebab_case }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "chainable_filters.blade.html", template_content)
        
        context = {
            'text': '  hello world  ',
            'short_text': 'hi',
            'snake_text': 'hello_world_example',
            'pascal_text': 'HelloWorldExample',
            'messy_text': '  some_messy_text  '
        }
        
        result = engine.render("chainable_filters.blade.html", context)
        
        assert 'Original: "  hello world  "' in result
        assert 'Trimmed: "hello world"' in result
        assert 'Pascal: HelloWorldExample' in result
        assert 'Kebab: hello-world-example' in result
    
    def test_dynamic_directive_registration(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test dynamic directive registration at runtime"""
        engine, temp_dir = blade_engine
        
        # Register directives dynamically based on configuration
        directive_config = {
            'success': {'class': 'alert-success', 'icon': '✓'},
            'warning': {'class': 'alert-warning', 'icon': '⚠'},  
            'error': {'class': 'alert-danger', 'icon': '✗'},
            'info': {'class': 'alert-info', 'icon': 'ℹ'}
        }
        
        # Dynamically create directives
        for directive_name, config in directive_config.items():
            def create_alert_directive(alert_class, icon):
                def directive_func(content):
                    message = content.strip().strip('"\'')
                    return f'<div class="alert {alert_class}"><span>{icon}</span> {message}</div>'
                return directive_func
            
            engine.directive(
                f'{directive_name}_alert',
                create_alert_directive(config['class'], config['icon'])
            )
        
        template_content = """
<div>
    @success_alert('Operation completed successfully!')
    @warning_alert('Please review your settings')
    @error_alert('An error occurred while processing')
    @info_alert('Additional information available')
</div>
        """.strip()
        
        self.create_template(temp_dir, "dynamic_directives.blade.html", template_content)
        
        result = engine.render("dynamic_directives.blade.html")
        
        assert 'alert-success' in result and '✓' in result
        assert 'alert-warning' in result and '⚠' in result
        assert 'alert-danger' in result and '✗' in result
        assert 'alert-info' in result and 'ℹ' in result
        assert 'Operation completed successfully!' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])