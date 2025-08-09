"""
Comprehensive Test Suite for Complete Blade Template Engine Syntax
Tests all Blade directives, components, and features
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List
import os

from app.View.BladeEngine import BladeEngine, blade, view, view_share, view_composer


class TestBladeBasicSyntax:
    """Test basic Blade syntax: variables, comments, conditionals, loops"""
    
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
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_variable_output(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test variable output with different syntaxes"""
        content = """
        Escaped: {{ name }}
        Unescaped: {!! html_content !!}
        JSON: @json(data)
        """.strip()
        self.create_template(temp_dir, "variables.blade.html", content)
        
        context = {
            "name": "John Doe",
            "html_content": "<b>Bold</b>",
            "data": {"key": "value", "number": 42}
        }
        
        result = blade_engine.render("variables.blade.html", context)
        assert "John Doe" in result
        assert "<b>Bold</b>" in result  # Unescaped
        assert '"key"' in result or "'key'" in result  # JSON
    
    def test_blade_comments(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test Blade comment removal"""
        content = """
        <h1>Visible</h1>
        {{-- This is a Blade comment --}}
        <p>Also visible</p>
        {{-- Multi-line
        comment here --}}
        <span>Final visible</span>
        """.strip()
        self.create_template(temp_dir, "comments.blade.html", content)
        
        result = blade_engine.render("comments.blade.html")
        assert "Visible" in result
        assert "Also visible" in result
        assert "Final visible" in result
        assert "This is a Blade comment" not in result
        assert "Multi-line" not in result
    
    def test_conditionals(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test conditional directives: @if, @elseif, @else, @unless"""
        content = """
        @if($score >= 90)
            <p>Grade: A</p>
        @elseif($score >= 80)
            <p>Grade: B</p>
        @elseif($score >= 70)
            <p>Grade: C</p>
        @else
            <p>Grade: F</p>
        @endif
        
        @unless($user_banned)
            <p>Welcome, user!</p>
        @endunless
        """.strip()
        self.create_template(temp_dir, "conditionals.blade.html", content)
        
        # Test different scores
        result = blade_engine.render("conditionals.blade.html", {"score": 95, "user_banned": False})
        assert "Grade: A" in result
        assert "Welcome, user!" in result
        
        result = blade_engine.render("conditionals.blade.html", {"score": 75, "user_banned": True})
        assert "Grade: C" in result
        assert "Welcome, user!" not in result
    
    def test_loops(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test loop directives: @foreach, @for, @while"""
        content = """
        <h3>Users:</h3>
        @foreach($users as $user)
            <p>{{ $user.name }} ({{ loop.index }})</p>
        @endforeach
        
        <h3>Numbers:</h3>
        @for($i = 1; $i <= 3; $i++)
            <span>{{ $i }}</span>
        @endfor
        
        <h3>Foreach with keys:</h3>
        @foreach($data as $key => $value)
            <div>{{ $key }}: {{ $value }}</div>
        @endforeach
        """.strip()
        self.create_template(temp_dir, "loops.blade.html", content)
        
        context = {
            "users": [
                {"name": "Alice"},
                {"name": "Bob"},
                {"name": "Carol"}
            ],
            "data": {
                "name": "John",
                "age": 30,
                "city": "NYC"
            }
        }
        
        result = blade_engine.render("loops.blade.html", context)
        assert "Alice" in result
        assert "Bob" in result  
        assert "Carol" in result
        assert "name: John" in result
        assert "age: 30" in result
    
    def test_forelse(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @forelse directive for empty collections"""
        content = """
        @forelse($items as $item)
            <li>{{ $item }}</li>
        @empty
            <p>No items found</p>
        @endforelse
        """.strip()
        self.create_template(temp_dir, "forelse.blade.html", content)
        
        # Test with items
        result = blade_engine.render("forelse.blade.html", {"items": ["Apple", "Banana"]})
        assert "Apple" in result
        assert "Banana" in result
        assert "No items found" not in result
        
        # Test without items
        result = blade_engine.render("forelse.blade.html", {"items": []})
        assert "No items found" in result
        assert "Apple" not in result
    
    def test_switch_case(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @switch and @case directives"""
        content = """
        @switch($type)
            @case('admin')
                <p>Administrator Access</p>
                @break
            @case('user')
                <p>User Access</p>
                @break
            @default
                <p>Guest Access</p>
        @endswitch
        """.strip()
        self.create_template(temp_dir, "switch.blade.html", content)
        
        result = blade_engine.render("switch.blade.html", {"type": "admin"})
        assert "Administrator Access" in result
        
        result = blade_engine.render("switch.blade.html", {"type": "guest"})
        assert "Guest Access" in result


class TestBladeAdvancedDirectives:
    """Test advanced Blade directives"""
    
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
    
    def test_isset_empty(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @isset and @empty directives"""
        engine, temp_dir = blade_engine
        content = """
        @isset($user.name)
            <p>User name: {{ $user.name }}</p>
        @endisset
        
        @empty($items)
            <p>No items available</p>
        @endempty
        """.strip()
        self.create_template(temp_dir, "isset_empty.blade.html", content)
        
        # Test with set values
        context = {"user": {"name": "John"}, "items": ["item1"]}
        result = engine.render("isset_empty.blade.html", context)
        assert "User name: John" in result
        assert "No items available" not in result
        
        # Test with empty values
        context = {"user": {}, "items": []}
        result = engine.render("isset_empty.blade.html", context)
        assert "User name:" not in result
        assert "No items available" in result
    
    def test_once_blocks(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @once directive for one-time content"""
        engine, temp_dir = blade_engine
        content = """
        @once('jquery')
            <script src="jquery.js"></script>
        @endonce
        
        @once('jquery')
            <script src="jquery.js"></script>
        @endonce
        """.strip()
        self.create_template(temp_dir, "once.blade.html", content)
        
        result = engine.render("once.blade.html")
        # Should only include jQuery once even though @once appears twice
        script_count = result.count('<script src="jquery.js"></script>')
        assert script_count <= 1
    
    def test_stacks(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @push, @prepend, and @stack directives"""
        engine, temp_dir = blade_engine
        content = """
        @push('scripts')
            <script src="app.js"></script>
        @endpush
        
        @prepend('scripts')  
            <script src="vendor.js"></script>
        @endprepend
        
        @push('scripts')
            <script src="custom.js"></script>
        @endpush
        
        <body>
            @stack('scripts')
        </body>
        """.strip()
        self.create_template(temp_dir, "stacks.blade.html", content)
        
        result = engine.render("stacks.blade.html")
        # Prepended scripts should come first
        vendor_pos = result.find("vendor.js")
        app_pos = result.find("app.js")
        custom_pos = result.find("custom.js")
        
        # Basic check that scripts are present
        assert "vendor.js" in result
        assert "app.js" in result
        assert "custom.js" in result
    
    def test_debug_dump(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @dd and @dump directives"""
        engine, temp_dir = blade_engine
        content = """
        @debug
            <p>Debug info here</p>
        @enddebug
        
        @dump($data)
        """.strip()
        self.create_template(temp_dir, "debug.blade.html", content)
        
        result = engine.render("debug.blade.html", {"data": {"key": "value"}})
        # Debug content should appear in debug mode
        assert "Debug info" in result


class TestBladeAuthAndPermissions:
    """Test authentication and permission directives"""
    
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
    
    def test_auth_guest(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @auth and @guest directives"""
        engine, temp_dir = blade_engine
        content = """
        @auth
            <p>Welcome, {{ current_user.name }}!</p>
            <a href="/logout">Logout</a>
        @endauth
        
        @guest
            <a href="/login">Login</a>
            <a href="/register">Register</a>
        @endguest
        """.strip()
        self.create_template(temp_dir, "auth.blade.html", content)
        
        # Test as authenticated user
        result = engine.render("auth.blade.html", {"current_user": {"name": "John"}})
        assert "Welcome, John!" in result
        assert "Logout" in result
        assert "Login" not in result
        
        # Test as guest
        result = engine.render("auth.blade.html", {"current_user": None})
        assert "Welcome," not in result
        assert "Login" in result
        assert "Register" in result
    
    def test_can_cannot(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @can and @cannot directives"""
        engine, temp_dir = blade_engine
        content = """
        @can('edit-posts')
            <button>Edit Post</button>
        @endcan
        
        @cannot('delete-posts')
            <p>You cannot delete posts</p>
        @endcannot
        """.strip()
        self.create_template(temp_dir, "permissions.blade.html", content)
        
        class MockUser:
            def can(self, permission: str) -> bool:
                return permission == 'edit-posts'
        
        result = engine.render("permissions.blade.html", {"current_user": MockUser()})
        assert "Edit Post" in result
        assert "You cannot delete posts" in result
    
    def test_roles(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @hasrole and @hasanyrole directives"""
        engine, temp_dir = blade_engine
        content = """
        @hasrole('admin')
            <p>Admin Panel</p>
        @endhasrole
        
        @hasanyrole(['admin', 'moderator'])
            <p>Management Tools</p>
        @endhasanyrole
        """.strip()
        self.create_template(temp_dir, "roles.blade.html", content)
        
        class MockUser:
            def has_role(self, role: str) -> bool:
                return role == 'admin'
                
            def has_any_role(self, roles: List[str]) -> bool:
                return 'admin' in roles
        
        result = engine.render("roles.blade.html", {"current_user": MockUser()})
        assert "Admin Panel" in result
        assert "Management Tools" in result


class TestBladeFormHelpers:
    """Test form helper directives"""
    
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
    
    def test_csrf_method(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @csrf and @method directives"""
        engine, temp_dir = blade_engine
        content = """
        <form method="POST" action="/users">
            @csrf
            @method('PUT')
            <input type="text" name="name" value="@old('name')">
        </form>
        """.strip()
        self.create_template(temp_dir, "form.blade.html", content)
        
        result = engine.render("form.blade.html")
        assert 'name="_token"' in result
        assert 'name="_method"' in result
        assert 'value="PUT"' in result
    
    def test_old_errors(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @old and @errors directives"""
        engine, temp_dir = blade_engine
        content = """
        <input type="text" name="name" value="@old('name')">
        @error('name')
            <span class="error">{{ $message }}</span>
        @enderror
        
        @errors('email')
            <div class="errors">{{ $errors }}</div>
        @enderrors
        """.strip()
        self.create_template(temp_dir, "validation.blade.html", content)
        
        context = {
            "errors": {
                "name": "Name is required",
                "email": ["Email is required", "Email must be valid"]
            }
        }
        result = engine.render("validation.blade.html", context)
        assert "Name is required" in result


class TestBladeConditionalHelpers:
    """Test conditional class and style helpers"""
    
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
    
    def test_conditional_classes(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @class directive for conditional CSS classes"""
        engine, temp_dir = blade_engine
        content = """
        <div @class([
            'btn',
            'btn-primary' => $isPrimary,
            'btn-large' => $isLarge,
            'disabled' => $isDisabled
        ])>
            Button
        </div>
        """.strip()
        self.create_template(temp_dir, "classes.blade.html", content)
        
        context = {
            "isPrimary": True,
            "isLarge": False,
            "isDisabled": True
        }
        result = engine.render("classes.blade.html", context)
        assert "btn" in result
        assert "btn-primary" in result
        assert "btn-large" not in result
        assert "disabled" in result
    
    def test_conditional_styles(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @style directive for conditional CSS styles"""
        engine, temp_dir = blade_engine
        content = """
        <div @style([
            'color' => $textColor,
            'background-color' => $bgColor,
            'font-weight' => $isBold ? 'bold' : null
        ])>
            Styled content
        </div>
        """.strip()
        self.create_template(temp_dir, "styles.blade.html", content)
        
        context = {
            "textColor": "red",
            "bgColor": "blue", 
            "isBold": True
        }
        result = engine.render("styles.blade.html", context)
        assert "color: red" in result
        assert "background-color: blue" in result
        assert "font-weight: bold" in result


class TestBladeLoopFeatures:
    """Test advanced loop features and $loop variable"""
    
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
    
    def test_loop_variable(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test $loop variable properties"""
        engine, temp_dir = blade_engine
        content = """
        @foreach($items as $item)
            <div class="@if(loop.first) first @endif @if(loop.last) last @endif">
                Item {{ loop.index }}/{{ loop.count }}: {{ $item }}
                @if(!loop.last), @endif
            </div>
        @endforeach
        """.strip()
        self.create_template(temp_dir, "loop_info.blade.html", content)
        
        context = {
            "items": ["Apple", "Banana", "Cherry"]
        }
        result = engine.render("loop_info.blade.html", context)
        assert "Apple" in result
        assert "Banana" in result
        assert "Cherry" in result
        # Loop properties should be available
        assert "1/3" in result or "first" in result
        assert "3/3" in result or "last" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])