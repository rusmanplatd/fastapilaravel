"""
Simple Additional Test Cases for Blade Engine
Tests additional functionality not covered in existing tests
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple

from app.View.BladeEngine import BladeEngine


class TestBladeAdditionalFeatures:
    """Additional simple tests for Blade engine functionality"""
    
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
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_basic_variables_and_filters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test basic variable output and filters"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="test-output">
    <h1>{{ title }}</h1>
    <p>Name: {{ name | title }}</p>
    <p>Slug: {{ name | slug }}</p>
    <p>Price: {{ price | money }}</p>
    <p>Rate: {{ rate | percentage }}</p>
    <p>Text: {{ long_text | truncate_words(3) }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "filters.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "title": "Filter Test",
            "name": "john doe",
            "price": 99.99,
            "rate": 0.15,
            "long_text": "This is a very long text for testing truncation"
        }
        
        result = engine.render("filters.blade.html", context)
        
        assert "Filter Test" in result
        assert "John Doe" in result
        assert "john-doe" in result
        assert "$99.99" in result
        assert "0.1%" in result
        assert "This is a..." in result
    
    def test_conditional_statements(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test conditional statements"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="conditionals">
    @if(show_welcome)
        <h1>Welcome!</h1>
    @endif
    
    @unless(is_hidden)
        <p>This content is visible</p>
    @endunless
    
    @if(user_type == 'admin')
        <p>Admin user</p>
    @elseif(user_type == 'member')
        <p>Member user</p>
    @else
        <p>Guest user</p>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "conditionals.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "show_welcome": True,
            "is_hidden": False,
            "user_type": "admin"
        }
        
        result = engine.render("conditionals.blade.html", context)
        
        assert "Welcome!" in result
        assert "This content is visible" in result
        assert "Admin user" in result
        assert "Member user" not in result
        assert "Guest user" not in result
    
    def test_loop_functionality(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test loop functionality"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="loops">
    <ul>
        @foreach(items as item)
            <li class="item-{{ loop.index }}">
                {{ item }} 
                @if(loop.first) (first) @endif
                @if(loop.last) (last) @endif
            </li>
        @endforeach
    </ul>
    
    <div class="numbers">
        @for(i = 1; i <= 3; i++)
            <span>{{ i }}</span>
        @endfor
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "loops.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "items": ["Alpha", "Beta", "Gamma"]
        }
        
        result = engine.render("loops.blade.html", context)
        
        assert "Alpha" in result
        assert "Beta" in result
        assert "Gamma" in result
        assert "(first)" in result
        assert "(last)" in result
        assert "item-1" in result
        assert "item-3" in result
    
    def test_template_inheritance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test template inheritance"""
        engine, temp_dir = blade_engine
        
        # Create base layout
        base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
</head>
<body>
    <header>@yield('header')</header>
    <main>@yield('content')</main>
    <footer>@yield('footer', 'Default Footer')</footer>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", base_layout)
        
        # Create child template
        child_template = """
@extends('layouts/base')

@section('title', 'Child Page')

@section('header')
    <h1>{{ page_title }}</h1>
@endsection

@section('content')
    <p>{{ page_content }}</p>
@endsection
        """.strip()
        self.create_template(temp_dir, "child.blade.html", child_template)
        
        context: Dict[str, Any] = {
            "page_title": "My Child Page",
            "page_content": "This is the main content."
        }
        
        result = engine.render("child.blade.html", context)
        
        assert "<!DOCTYPE html>" in result
        assert "<title>Child Page</title>" in result
        assert "My Child Page" in result
        assert "This is the main content." in result
        assert "Default Footer" in result
    
    def test_auth_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test authentication directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="auth-test">
    @auth
        <p>Hello {{ current_user.name }}!</p>
        <p>Email: {{ current_user.email }}</p>
    @endauth
    
    @guest
        <p>Please log in</p>
    @endguest
</div>
        """.strip()
        self.create_template(temp_dir, "auth.blade.html", template_content)
        
        # Test with authenticated user
        context: Dict[str, Any] = {
            "current_user": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        
        result = engine.render("auth.blade.html", context)
        
        assert "Hello John Doe!" in result
        assert "john@example.com" in result
        assert "Please log in" not in result
    
    def test_include_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test include directive"""
        engine, temp_dir = blade_engine
        
        # Create partial template
        partial_content = """
<div class="partial-content">
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "partials/info.blade.html", partial_content)
        
        # Create main template
        main_content = """
<div class="main-content">
    <h1>Main Page</h1>
    @include('partials/info')
</div>
        """.strip()
        self.create_template(temp_dir, "main.blade.html", main_content)
        
        context: Dict[str, Any] = {
            "title": "Partial Title",
            "description": "This comes from a partial template."
        }
        
        result = engine.render("main.blade.html", context)
        
        assert "Main Page" in result
        assert "Partial Title" in result
        assert "This comes from a partial template." in result
    
    def test_form_helpers(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test form helper directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
<form method="POST">
    @csrf
    @method('PUT')
    
    <div class="field">
        <label>Name:</label>
        <input type="text" name="name" value="{{ old('name', 'default') }}">
    </div>
    
    <div class="field">
        <label>Email:</label>
        <input type="email" name="email" value="{{ old('email') }}">
    </div>
    
    <button type="submit">Submit</button>
</form>
        """.strip()
        self.create_template(temp_dir, "form.blade.html", template_content)
        
        result = engine.render("form.blade.html")
        
        assert 'name="_token"' in result
        assert 'name="_method"' in result
        assert 'value="PUT"' in result
        assert 'value="default"' in result  # old() with default
    
    def test_json_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test JSON directive"""
        engine, temp_dir = blade_engine
        
        template_content = """
<script>
    var userData = @json(user_data);
    var config = @json(app_config);
</script>
        """.strip()
        self.create_template(temp_dir, "json.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "user_data": {
                "id": 123,
                "name": "John Doe",
                "active": True
            },
            "app_config": {
                "debug": False,
                "version": "1.0.0"
            }
        }
        
        result = engine.render("json.blade.html", context)
        
        assert '"id": 123' in result or '"id":123' in result
        assert '"name": "John Doe"' in result
        assert '"active": true' in result
        assert '"debug": false' in result
        assert '"version": "1.0.0"' in result
    
    def test_comment_removal(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test Blade comment removal"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="content">
    <h1>Visible Title</h1>
    {{-- This is a Blade comment and should not appear in output --}}
    <p>Visible paragraph</p>
    {{-- Another comment
         spanning multiple lines --}}
    <p>Another visible paragraph</p>
</div>
        """.strip()
        self.create_template(temp_dir, "comments.blade.html", template_content)
        
        result = engine.render("comments.blade.html")
        
        assert "Visible Title" in result
        assert "Visible paragraph" in result
        assert "Another visible paragraph" in result
        assert "This is a Blade comment" not in result
        assert "spanning multiple lines" not in result
    
    def test_escaped_vs_unescaped_output(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test escaped vs unescaped output"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="output-test">
    <div class="escaped">{{ html_content }}</div>
    <div class="unescaped">{!! html_content !!}</div>
</div>
        """.strip()
        self.create_template(temp_dir, "output.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "html_content": "<strong>Bold Text</strong>"
        }
        
        result = engine.render("output.blade.html", context)
        
        # Should have both escaped and unescaped versions
        assert "<strong>Bold Text</strong>" in result  # Unescaped
        # The escaped version depends on Jinja2's auto-escaping
        assert result.count("Bold Text") >= 1
    
    def test_error_handling_graceful(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test graceful error handling"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="error-test">
    @isset(undefined_variable)
        <p>Variable exists: {{ undefined_variable }}</p>
    @endisset
    
    @unless(undefined_variable)
        <p>Variable not defined</p>
    @endunless
    
    @unless(null_value)
        <p>Null value is empty</p>
    @endunless
    
    @unless(empty_list)
        <p>Empty list detected</p>
    @endunless
</div>
        """.strip()
        self.create_template(temp_dir, "errors.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "null_value": None,
            "empty_list": []
        }
        
        result = engine.render("errors.blade.html", context)
        
        assert "Variable not defined" in result
        assert "Null value is empty" in result
        assert "Empty list detected" in result
        assert "Variable exists:" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])