"""
Test suite for Blade Template Engine
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine, blade, view, view_share, view_composer


class TestBladeEngine:
    """Test cases for BladeEngine class"""
    
    @pytest.fixture
    def temp_dir(self) -> Generator[str, None, None]:
        """Create temporary directory for templates"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def blade_engine(self, temp_dir: str) -> BladeEngine:
        """Create BladeEngine instance with temp directory"""
        return BladeEngine([temp_dir], debug=True)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w') as f:
            f.write(content)
    
    def test_basic_template_rendering(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test basic template rendering"""
        content = "<h1>Hello, {{ name }}!</h1>"
        self.create_template(temp_dir, "hello.blade.html", content)
        
        result = blade_engine.render("hello.blade.html", {"name": "World"})
        assert result == "<h1>Hello, World!</h1>"
    
    def test_blade_extends_and_sections(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @extends and @section directives"""
        # Create layout template
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
</head>
<body>
    @yield('content')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layout.blade.html", layout_content)
        
        # Create child template
        child_content = """
@extends('layout')

@section('title', 'Test Page')

@section('content')
    <h1>This is the content</h1>
@endsection
        """.strip()
        self.create_template(temp_dir, "child.blade.html", child_content)
        
        result = blade_engine.render("child.blade.html")
        assert "<title>Test Page</title>" in result
        assert "<h1>This is the content</h1>" in result
    
    def test_auth_directives(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @auth and @guest directives"""
        content = """
@auth
    <p>Welcome, authenticated user!</p>
@endauth

@guest
    <p>Please log in.</p>
@endguest
        """.strip()
        self.create_template(temp_dir, "auth.blade.html", content)
        
        # Test with authenticated user
        result = blade_engine.render("auth.blade.html", {"current_user": {"name": "John"}})
        assert "Welcome, authenticated user!" in result
        assert "Please log in." not in result
        
        # Test as guest
        result = blade_engine.render("auth.blade.html", {"current_user": None})
        assert "Welcome, authenticated user!" not in result
        assert "Please log in." in result
    
    def test_conditional_directives(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @if, @else, @endif directives"""
        content = """
@if(show_message)
    <p>Message is shown</p>
@else
    <p>Message is hidden</p>
@endif
        """.strip()
        self.create_template(temp_dir, "conditional.blade.html", content)
        
        result = blade_engine.render("conditional.blade.html", {"show_message": True})
        assert "Message is shown" in result
        assert "Message is hidden" not in result
        
        result = blade_engine.render("conditional.blade.html", {"show_message": False})
        assert "Message is shown" not in result
        assert "Message is hidden" in result
    
    def test_unless_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @unless directive"""
        content = """
@unless(user_logged_in)
    <p>Please log in to continue</p>
@endunless
        """.strip()
        self.create_template(temp_dir, "unless.blade.html", content)
        
        result = blade_engine.render("unless.blade.html", {"user_logged_in": False})
        assert "Please log in to continue" in result
        
        result = blade_engine.render("unless.blade.html", {"user_logged_in": True})
        assert "Please log in to continue" not in result
    
    def test_foreach_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @foreach directive"""
        content = """
<ul>
@foreach(items as item)
    <li>{{ item }}</li>
@endforeach
</ul>
        """.strip()
        self.create_template(temp_dir, "foreach.blade.html", content)
        
        result = blade_engine.render("foreach.blade.html", {"items": ["Item 1", "Item 2", "Item 3"]})
        assert "<li>Item 1</li>" in result
        assert "<li>Item 2</li>" in result
        assert "<li>Item 3</li>" in result
    
    def test_forelse_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @forelse directive"""
        content = """
@forelse(items as item)
    <p>{{ item }}</p>
@empty
    <p>No items found</p>
@endforelse
        """.strip()
        self.create_template(temp_dir, "forelse.blade.html", content)
        
        # Test with items
        result = blade_engine.render("forelse.blade.html", {"items": ["Item 1", "Item 2"]})
        assert "Item 1" in result
        assert "No items found" not in result
        
        # Test with empty list
        result = blade_engine.render("forelse.blade.html", {"items": []})
        assert "No items found" in result
    
    def test_can_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @can and @cannot directives"""
        content = """
@can('edit-post')
    <button>Edit Post</button>
@endcan

@cannot('delete-post')
    <p>You cannot delete this post</p>
@endcannot
        """.strip()
        self.create_template(temp_dir, "can.blade.html", content)
        
        # Mock user with can method
        class MockUser:
            def can(self, permission: str) -> bool:
                return permission == 'edit-post'
        
        result = blade_engine.render("can.blade.html", {"current_user": MockUser()})
        assert "<button>Edit Post</button>" in result
        assert "You cannot delete this post" in result
    
    def test_include_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @include directive"""
        # Create partial template
        partial_content = "<p>This is a partial: {{ message }}</p>"
        self.create_template(temp_dir, "partial.blade.html", partial_content)
        
        # Create main template
        main_content = """
<h1>Main Template</h1>
@include('partial')
        """.strip()
        self.create_template(temp_dir, "main.blade.html", main_content)
        
        result = blade_engine.render("main.blade.html", {"message": "Hello from partial"})
        assert "Main Template" in result
        assert "This is a partial: Hello from partial" in result
    
    def test_json_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @json directive"""
        content = """
<script>
    var data = @json(data);
</script>
        """.strip()
        self.create_template(temp_dir, "json.blade.html", content)
        
        result = blade_engine.render("json.blade.html", {"data": {"key": "value", "number": 42}})
        assert '"key": "value"' in result or "'key': 'value'" in result
        assert "42" in result
    
    def test_csrf_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @csrf directive"""
        content = """
<form method="POST">
    @csrf
    <input type="text" name="name">
</form>
        """.strip()
        self.create_template(temp_dir, "csrf.blade.html", content)
        
        result = blade_engine.render("csrf.blade.html")
        assert '<input type="hidden" name="_token"' in result
    
    def test_method_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @method directive"""
        content = """
<form method="POST">
    @method('PUT')
    <input type="text" name="name">
</form>
        """.strip()
        self.create_template(temp_dir, "method.blade.html", content)
        
        result = blade_engine.render("method.blade.html")
        assert '<input type="hidden" name="_method" value="PUT">' in result
    
    def test_blade_comments(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test Blade comments removal"""
        content = """
<h1>Visible content</h1>
{{-- This is a Blade comment --}}
<p>More visible content</p>
        """.strip()
        self.create_template(temp_dir, "comments.blade.html", content)
        
        result = blade_engine.render("comments.blade.html")
        assert "Visible content" in result
        assert "More visible content" in result
        assert "This is a Blade comment" not in result
    
    def test_unescaped_output(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test unescaped output {!! !!}"""
        content = """
<div>
    Escaped: {{ html_content }}
    Unescaped: {!! html_content !!}
</div>
        """.strip()
        self.create_template(temp_dir, "unescaped.blade.html", content)
        
        result = blade_engine.render("unescaped.blade.html", {"html_content": "<b>Bold</b>"})
        # The escaped version should have escaped HTML
        # The unescaped version should have raw HTML
        assert result.count("<b>Bold</b>") >= 1  # At least the unescaped version
    
    def test_custom_directive(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test custom directive registration"""
        # Register custom directive
        blade_engine.directive('alert', lambda content: f'<div class="alert">{content.strip()}</div>')
        
        content = """
@alert('This is an alert message')
        """.strip()
        self.create_template(temp_dir, "custom.blade.html", content)
        
        result = blade_engine.render("custom.blade.html")
        assert '<div class="alert">This is an alert message</div>' in result
    
    def test_shared_data(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test shared data functionality"""
        content = "<p>Shared: {{ shared_value }}</p><p>Local: {{ local_value }}</p>"
        self.create_template(temp_dir, "shared.blade.html", content)
        
        blade_engine.share("shared_value", "Global Value")
        
        result = blade_engine.render("shared.blade.html", {"local_value": "Local Value"})
        assert "Shared: Global Value" in result
        assert "Local: Local Value" in result
    
    def test_view_composer(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test view composer functionality"""
        content = "<p>From composer: {{ composer_data }}</p>"
        self.create_template(temp_dir, "composer.blade.html", content)
        
        def test_composer(context: Dict[str, Any]) -> Dict[str, Any]:
            return {"composer_data": "Injected by composer"}
        
        blade_engine.composer("composer*", test_composer)
        
        result = blade_engine.render("composer.blade.html")
        assert "From composer: Injected by composer" in result
    
    def test_template_caching(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test template caching functionality"""
        content = "<p>Cached template: {{ value }}</p>"
        self.create_template(temp_dir, "cached.blade.html", content)
        
        # First render
        result1 = blade_engine.render("cached.blade.html", {"value": "First"})
        assert "Cached template: First" in result1
        
        # Second render (should use cache)
        result2 = blade_engine.render("cached.blade.html", {"value": "Second"})
        assert "Cached template: Second" in result2
        
        # Clear cache
        blade_engine.clear_cache()
        
        # Third render (cache cleared)
        result3 = blade_engine.render("cached.blade.html", {"value": "Third"})
        assert "Cached template: Third" in result3
    
    def test_template_not_found(self, blade_engine: BladeEngine) -> None:
        """Test template not found error"""
        with pytest.raises(FileNotFoundError, match="Template 'nonexistent.blade.html' not found"):
            blade_engine.render("nonexistent.blade.html")
    
    def test_custom_filters(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test custom Jinja2 filters"""
        content = """
<p>{{ text | ucfirst }}</p>
<p>{{ text | slug }}</p>
<p>{{ price | money }}</p>
<p>{{ rate | percentage }}</p>
<p>{{ long_text | truncate_words(3) }}</p>
        """.strip()
        self.create_template(temp_dir, "filters.blade.html", content)
        
        context: Dict[str, Any] = {
            "text": "hello world",
            "price": 29.99,
            "rate": 0.75,
            "long_text": "This is a very long text that should be truncated"
        }
        
        result = blade_engine.render("filters.blade.html", context)
        assert "Hello world" in result  # ucfirst
        assert "hello-world" in result  # slug
        assert "$29.99" in result       # money
        assert "0.8%" in result         # percentage
        assert "This is a..." in result # truncate_words


class TestBladeGlobalFunctions:
    """Test global Blade helper functions"""
    
    def test_view_function(self, tmp_path: Path) -> None:
        """Test global view() function"""
        # Create a template
        template_content = "<h1>{{ message }}</h1>"
        template_path = tmp_path / "test.blade.html"
        template_path.write_text(template_content)
        
        # Initialize blade engine with temp path
        blade([str(tmp_path)])
        
        result = view("test.blade.html", {"message": "Hello World"})
        assert "Hello World" in result
    
    def test_view_share_function(self, tmp_path: Path) -> None:
        """Test global view_share() function"""
        template_content = "<p>{{ shared_data }}</p>"
        template_path = tmp_path / "shared.blade.html"
        template_path.write_text(template_content)
        
        # Initialize and share data
        blade([str(tmp_path)])
        view_share("shared_data", "Globally shared value")
        
        result = view("shared.blade.html")
        assert "Globally shared value" in result
    
    def test_view_composer_function(self, tmp_path: Path) -> None:
        """Test global view_composer() function"""
        template_content = "<p>{{ composed_value }}</p>"
        template_path = tmp_path / "composed.blade.html"
        template_path.write_text(template_content)
        
        def composer(context: Dict[str, Any]) -> Dict[str, Any]:
            return {"composed_value": "Value from global composer"}
        
        # Initialize and register composer
        blade([str(tmp_path)])
        view_composer("composed*", composer)
        
        result = view("composed.blade.html")
        assert "Value from global composer" in result


class TestBladeAdvancedDirectives:
    """Test advanced Blade directives"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        """Create BladeEngine instance with temp directory"""
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w') as f:
            f.write(content)
    
    def test_error_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @error directive"""
        engine, temp_dir = blade_engine
        content = """
@error('email')
    <span class="error">{{ error }}</span>
@enderror
        """.strip()
        self.create_template(temp_dir, "error.blade.html", content)
        
        # Test with error
        errors: Dict[str, str] = {"email": "Email is required"}
        result = engine.render("error.blade.html", {"errors": errors, "error": "Email is required"})
        assert "Email is required" in result
        
        # Test without error
        result = engine.render("error.blade.html", {"errors": {}})
        assert "Email is required" not in result
    
    def test_isset_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @isset directive"""
        engine, temp_dir = blade_engine
        content = """
@isset(user.name)
    <p>User name: {{ user.name }}</p>
@endisset
        """.strip()
        self.create_template(temp_dir, "isset.blade.html", content)
        
        # Test with set variable
        user: Dict[str, str] = {"name": "John Doe"}
        result = engine.render("isset.blade.html", {"user": user})
        assert "User name: John Doe" in result
        
        # Test with unset variable
        result = engine.render("isset.blade.html", {"user": {}})
        assert "User name:" not in result
    
    def test_production_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @production directive"""
        engine, temp_dir = blade_engine
        content = """
@production
    <script src="/js/app.min.js"></script>
@endproduction
        """.strip()
        self.create_template(temp_dir, "production.blade.html", content)
        
        # Mock config function to return production environment
        def mock_config(key: str) -> str | None:
            if key == 'app.env':
                return 'production'
            return None
        
        engine.env.globals['config'] = mock_config
        
        result = engine.render("production.blade.html")
        assert "app.min.js" in result
    
    def test_hasrole_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @hasrole directive"""
        engine, temp_dir = blade_engine
        content = """
@hasrole('admin')
    <button>Admin Panel</button>
@endhasrole
        """.strip()
        self.create_template(temp_dir, "hasrole.blade.html", content)
        
        # Mock user with has_role method
        class MockUser:
            def has_role(self, role: str) -> bool:
                return role == 'admin'
        
        result = engine.render("hasrole.blade.html", {"current_user": MockUser()})
        assert "Admin Panel" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])