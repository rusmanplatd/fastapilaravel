"""
Test Suite for Blade Engine Filters and Global Functions
Tests custom filters, helper functions, and template globals
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Iterator, Tuple, Generator
import os
from datetime import datetime, timedelta

from app.View.BladeEngine import BladeEngine


class TestBladeCustomFilters:
    """Test custom Jinja2 filters"""
    
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
    
    def test_string_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test string manipulation filters"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="string-filters">
    <p>Original: "{{ $text }}"</p>
    <p>Uppercase First: "{{ $text | ucfirst }}"</p>
    <p>Title Case: "{{ $text | title }}"</p>
    <p>Slug: "{{ $text | slug }}"</p>
    
    <p>Long Text: "{{ $long_text }}"</p>
    <p>Truncated (5 words): "{{ $long_text | truncate_words(5) }}"</p>
    <p>Truncated (default): "{{ $long_text | truncate_words }}"</p>
    
    <p>Complex Text: "{{ $complex_text | slug }}"</p>
    <p>Empty Text: "{{ $empty_text | ucfirst }}"</p>
</div>
        """.strip()
        self.create_template(temp_dir, "string_filters.blade.html", template_content)
        
        context = {
            "text": "hello world testing",
            "long_text": "This is a very long text that should be truncated after several words for testing purposes",
            "complex_text": "Hello World! This has SPECIAL characters & symbols @#$%",
            "empty_text": ""
        }
        
        result = engine.render("string_filters.blade.html", context)
        
        # Test ucfirst filter
        assert "Hello world testing" in result
        
        # Test title filter  
        assert "Hello World Testing" in result
        
        # Test slug filter
        assert "hello-world-testing" in result
        assert "hello-world-this-has-special-characters-symbols" in result
        
        # Test truncate_words filter
        assert "This is a very long..." in result
        assert "This is a very long text that should be truncated after..." in result
        
        # Test empty string handling
        assert '""' in result  # Empty text should remain empty
    
    def test_numeric_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test numeric formatting filters"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="numeric-filters">
    <p>Price 1: {{ $price1 | money }}</p>
    <p>Price 2: {{ $price2 | money }}</p>
    <p>Price 3: {{ $price3 | money }}</p>
    
    <p>Rate 1: {{ $rate1 | percentage }}</p>
    <p>Rate 2: {{ $rate2 | percentage }}</p>
    <p>Rate 3: {{ $rate3 | percentage }}</p>
    
    <p>Zero: {{ $zero | money }}</p>
    <p>Null: {{ $null_value | money }}</p>
    <p>String Number: {{ $string_number | money }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "numeric_filters.blade.html", template_content)
        
        context = {
            "price1": 29.99,
            "price2": 1000.50,
            "price3": 5,
            "rate1": 0.75,
            "rate2": 0.1234,
            "rate3": 1.5,
            "zero": 0,
            "null_value": None,
            "string_number": "42.99"
        }
        
        result = engine.render("numeric_filters.blade.html", context)
        
        # Test money filter
        assert "$29.99" in result
        assert "$1,000.50" in result
        assert "$5.00" in result
        assert "$0.00" in result  # Zero handling
        assert "$0.00" in result  # Null handling (appears twice)
        assert "$42.99" in result  # String conversion
        
        # Test percentage filter
        assert "0.8%" in result  # 0.75 rounded
        assert "0.1%" in result  # 0.1234 rounded
        assert "1.5%" in result
    
    def test_loop_info_filter(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test loop information filter"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="loop-info">
    @foreach($items as $item)
        <div class="item">
            <p>Item: {{ $item }}</p>
            <p>Index: {{ loop.index }}</p>
            <p>First: {{ loop.first }}</p>
            <p>Last: {{ loop.last }}</p>
            <p>Even: {{ loop.even }}</p>
            <p>Odd: {{ loop.odd }}</p>
            <p>Remaining: {{ loop.remaining }}</p>
            <p>Count: {{ loop.count }}</p>
        </div>
        @if(!loop.last)
            <hr>
        @endif
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "loop_info.blade.html", template_content)
        
        context = {
            "items": ["Alpha", "Beta", "Gamma", "Delta"]
        }
        
        result = engine.render("loop_info.blade.html", context)
        
        # Should contain loop information
        assert "Item: Alpha" in result
        assert "Item: Delta" in result
        assert "Index: 1" in result  # 1-based
        assert "Index: 4" in result
        assert "First: True" in result
        assert "Last: True" in result
        assert "Even: True" in result  # Index 2, 4
        assert "Odd: True" in result   # Index 1, 3
        assert "Count: 4" in result
        assert "Remaining:" in result  # Should show remaining count
    
    def test_render_attributes_filter(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test HTML attributes rendering filter"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="attributes-test">
    <input {{ $input_attrs | render_attributes | safe }}>
    <button {{ $button_attrs | render_attributes | safe }}>Click</button>
    <div {{ $div_attrs | render_attributes | safe }}>Content</div>
    <span {{ $empty_attrs | render_attributes | safe }}>Empty</span>
</div>
        """.strip()
        self.create_template(temp_dir, "attributes.blade.html", template_content)
        
        context = {
            "input_attrs": {
                "type": "text",
                "name": "username",
                "id": "username-input",
                "class": "form-control",
                "required": True,
                "disabled": False,
                "data-test": 'value with "quotes"'
            },
            "button_attrs": {
                "type": "submit",
                "class": "btn btn-primary",
                "onclick": "handleClick()"
            },
            "div_attrs": {
                "id": "main-content",
                "hidden": None,  # Should be ignored
                "data-loaded": True
            },
            "empty_attrs": {}
        }
        
        result = engine.render("attributes.blade.html", context)
        
        # Test attribute rendering
        assert 'type="text"' in result
        assert 'name="username"' in result  
        assert 'class="form-control"' in result
        assert 'required' in result  # Boolean true becomes attribute name only
        assert 'disabled' not in result  # Boolean false omitted
        assert 'data-test="value with &quot;quotes&quot;"' in result  # Escaped quotes
        
        assert 'type="submit"' in result
        assert 'class="btn btn-primary"' in result
        assert 'onclick="handleClick()"' in result
        
        assert 'id="main-content"' in result
        assert 'data-loaded="True"' in result
        assert 'hidden' not in result  # None values omitted


class TestBladeGlobalFunctions:
    """Test global template functions"""
    
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
    
    def test_helper_functions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test utility helper functions"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="helpers">
    <!-- CSRF Token -->
    <p>CSRF: {{ csrf_token() }}</p>
    
    <!-- Route Helper -->
    <a href="{{ route('home') }}">Home</a>
    <a href="{{ route('user.profile', user_id=123) }}">Profile</a>
    
    <!-- Asset Helper -->
    <img src="{{ asset('images/logo.png') }}">
    <link href="{{ asset('css/app.css') }}" rel="stylesheet">
    
    <!-- Config Helper -->
    <p>App Name: {{ config('app.name', 'Default App') }}</p>
    <p>Debug: {{ config('app.debug', False) }}</p>
    
    <!-- Old Input Helper -->
    <input type="text" name="email" value="{{ old('email', 'default@example.com') }}">
    <input type="text" name="name" value="{{ old('name') }}">
</div>
        """.strip()
        self.create_template(temp_dir, "helpers.blade.html", template_content)
        
        result = engine.render("helpers.blade.html")
        
        # Test helper function outputs
        assert "CSRF: csrf_token_placeholder" in result
        assert 'href="/home"' in result
        assert 'href="/user.profile"' in result  # Basic route generation
        assert 'src="/assets/images/logo.png"' in result
        assert 'href="/assets/css/app.css"' in result
        assert "App Name: Default App" in result  # Default config value
        assert "Debug: False" in result
        assert 'value="default@example.com"' in result  # Old input with default
        assert 'value=""' in result or 'value="None"' in result  # Old input without default
    
    def test_class_and_style_helpers(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test class_names and styles helper functions"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="class-style-helpers">
    <!-- Class helper tests -->
    <div class="{{ class_names('btn', 'btn-primary', extra_classes) }}">Button 1</div>
    
    <div class="{{ class_names({
        'active': is_active,
        'disabled': is_disabled,
        'large': is_large
    }) }}">Button 2</div>
    
    <div class="{{ class_names('base-class', {
        'conditional-1': condition_1,
        'conditional-2': condition_2
    }, ['extra', 'classes']) }}">Button 3</div>
    
    <!-- Style helper tests -->
    <div style="{{ styles(color=text_color, background_color=bg_color, font_weight=font_weight) }}">Styled 1</div>
    
    <div style="{{ styles(width='100px', height=dynamic_height, display=display_type) }}">Styled 2</div>
    
    <div style="{{ styles(margin_top='20px', padding_left='10px', border_radius='4px') }}">Styled 3</div>
</div>
        """.strip()
        self.create_template(temp_dir, "class_style_helpers.blade.html", template_content)
        
        context = {
            "extra_classes": "extra-btn",
            "is_active": True,
            "is_disabled": False,
            "is_large": True,
            "condition_1": True,
            "condition_2": False,
            "text_color": "red",
            "bg_color": "blue",
            "font_weight": "bold",
            "dynamic_height": "200px",
            "display_type": None  # Should be excluded
        }
        
        result = engine.render("class_style_helpers.blade.html", context)
        
        # Test class_names function
        assert 'class="btn btn-primary extra-btn"' in result
        assert 'class="active large"' in result  # disabled should be excluded
        assert 'class="base-class conditional-1 extra classes"' in result
        
        # Test styles function
        assert 'style="color: red; background-color: blue; font-weight: bold"' in result
        assert 'style="width: 100px; height: 200px"' in result  # display excluded
        assert 'style="margin-top: 20px; padding-left: 10px; border-radius: 4px"' in result
    
    def test_debug_functions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test debug helper functions"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="debug-helpers">
    <h2>Debug Information</h2>
    
    <!-- Debug and Die -->
    <div class="dd-section">
        {{ debug_and_die(debug_data) }}
    </div>
    
    <!-- Dump Variables -->
    <div class="dump-section">
        {{ dump_vars(simple_var, complex_var) }}
    </div>
    
    <!-- Debug Mode Check -->
    @if(debug_mode)
        <p>Application is in debug mode</p>
    @else
        <p>Application is in production mode</p>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "debug_helpers.blade.html", template_content)
        
        context = {
            "debug_data": {
                "user_id": 123,
                "username": "testuser",
                "permissions": ["read", "write"]
            },
            "simple_var": "Hello World",
            "complex_var": {
                "nested": {
                    "key": "value",
                    "number": 42,
                    "list": [1, 2, 3]
                }
            }
        }
        
        result = engine.render("debug_helpers.blade.html", context)
        
        # Test debug functions
        assert "DEBUG & DIE" in result
        assert "user_id" in result
        assert "testuser" in result
        assert "permissions" in result
        
        assert "DUMP:" in result
        assert "Hello World" in result
        assert "nested" in result
        assert "42" in result
        
        # Debug mode should be true (engine created with debug=True)
        assert "Application is in debug mode" in result
    
    def test_translation_functions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test translation helper functions"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="translations">
    <!-- Basic translation -->
    <h1>{{ __('welcome.title') }}</h1>
    <p>{{ trans('welcome.message', {'name': user_name}) }}</p>
    
    <!-- Translation choice (pluralization) -->
    <p>{{ trans_choice('messages.items', item_count, {'count': item_count}) }}</p>
    <p>{{ trans_choice('messages.users', user_count, {'count': user_count}) }}</p>
    
    <!-- Fallback to key when translation missing -->
    <p>{{ __('missing.key') }}</p>
    
    <!-- With replacements -->
    <p>{{ __('greetings.hello', {'time': current_time, 'weather': weather}) }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "translations.blade.html", template_content)
        
        context = {
            "user_name": "John Doe",
            "item_count": 1,
            "user_count": 5,
            "current_time": "morning",
            "weather": "sunny"
        }
        
        result = engine.render("translations.blade.html", context)
        
        # Test translation functions (fallback to keys)
        assert "welcome.title" in result
        assert "welcome.message" in result
        assert "John Doe" in result  # Replacement should work
        
        assert "messages.items" in result
        assert "messages.users" in result
        
        assert "missing.key" in result  # Fallback
        
        assert "greetings.hello" in result
        assert "morning" in result  # Replacements
        assert "sunny" in result
    
    def test_component_functions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test component-related helper functions"""
        engine, temp_dir = blade_engine
        
        # Create a test component
        component_content = """
<div class="test-component">
    <h3>{{ title }}</h3>
    <p>{{ content }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "components/test-card.blade.html", component_content)
        
        template_content = """
<div class="component-helpers">
    <!-- Component exists check -->
    @if(component_exists('test-card'))
        <p>Test card component exists</p>
        @include('components/test-card.blade.html', {'title': 'Test Title', 'content': 'Test Content'})
    @endif
    
    @if(component_exists('non-existent'))
        <p>This should not appear</p>
    @else
        <p>Non-existent component does not exist</p>
    @endif
    
    <!-- Multiple component checks -->
    @if(component_exists('button'))
        <p>Button component exists</p>
    @endif
    
    @if(component_exists('card'))
        <p>Card component exists</p>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "component_helpers.blade.html", template_content)
        
        result = engine.render("component_helpers.blade.html")
        
        # Test component_exists function
        assert "Test card component exists" in result
        assert "Test Title" in result
        assert "Test Content" in result
        
        assert "Non-existent component does not exist" in result
        assert "This should not appear" not in result


class TestBladeAssetAndViteHelpers:
    """Test asset management and Vite integration helpers"""
    
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
    
    def test_vite_helper(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test Vite asset helper function"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Vite Assets</title>
    
    <!-- Single asset -->
    {{ vite('resources/css/app.css') | safe }}
    
    <!-- Multiple assets -->
    {{ vite('resources/js/app.js', 'resources/css/styles.css') | safe }}
    
    <!-- Mix of CSS and JS -->
    {{ vite('vendor/bootstrap.css', 'vendor/jquery.js', 'resources/css/custom.css') | safe }}
</head>
<body>
    <h1>Vite Integration Test</h1>
    
    <!-- Page-specific assets -->
    {{ vite('resources/js/dashboard.js') | safe }}
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "vite_assets.blade.html", template_content)
        
        result = engine.render("vite_assets.blade.html")
        
        # Test Vite asset generation
        assert 'rel="stylesheet"' in result  # CSS link tags
        assert 'type="module"' in result     # Modern JS module tags
        assert '/build/' in result           # Vite build directory
        
        # Should include all specified assets
        assert 'resources/css/app.css' in result
        assert 'resources/js/app.js' in result
        assert 'resources/css/styles.css' in result
        assert 'vendor/bootstrap.css' in result
        assert 'vendor/jquery.js' in result
        assert 'resources/js/dashboard.js' in result
    
    def test_livewire_helpers(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test Livewire integration helpers"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Livewire App</title>
    <link href="/css/bootstrap.css" rel="stylesheet">
    
    <!-- Livewire Styles -->
    {{ livewire_styles() | safe }}
    
    <style>
        .custom-loading { opacity: 0.5; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Livewire Components</h1>
        
        <div wire:loading class="loading-indicator">
            Loading...
        </div>
        
        <div class="components">
            <!-- Livewire components would be here -->
            <div wire:click="handleClick">Click me</div>
            <input wire:model="searchQuery" type="text" placeholder="Search...">
        </div>
    </div>
    
    <!-- Livewire Scripts -->
    {{ livewire_scripts() | safe }}
    
    <script>
        // Custom JavaScript
        console.log('App loaded');
    </script>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "livewire_app.blade.html", template_content)
        
        result = engine.render("livewire_app.blade.html")
        
        # Test Livewire styles
        assert "[wire\\:loading]" in result  # Livewire CSS for loading states
        assert "display: none" in result      # Default loading state
        
        # Test Livewire scripts
        assert "livewire.js" in result       # Main Livewire JavaScript
        assert 'defer' in result             # Script should be deferred
        
        # Livewire directives should remain in HTML
        assert "wire:loading" in result
        assert "wire:click" in result
        assert "wire:model" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])