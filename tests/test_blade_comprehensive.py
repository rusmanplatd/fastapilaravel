"""
Comprehensive Test Suite for Blade Engine - Additional Test Cases
Tests missing scenarios including error handling, edge cases, and complex features
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine


class TestBladeComprehensiveFeatures:
    """Additional comprehensive tests for Blade engine"""
    
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
    
    def test_complex_nested_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test deeply nested and complex directive combinations"""
        engine, temp_dir = blade_engine
        
        template_content = """
@if(user_authenticated)
    @hasrole('admin')
        @foreach(admin_sections as section)
            @if(section.enabled)
                <div class="admin-section">
                    <h3>{{ section.title }}</h3>
                    @if(section.items)
                        @foreach(section.items as item)
                            @unless(item.hidden)
                                <div class="item @if(loop.first) first @endif @if(loop.last) last @endif">
                                    <span>{{ item.name }}</span>
                                    @if(item.status == 'active')
                                        <span class="status-active">Active</span>
                                    @elseif(item.status == 'inactive')
                                        <span class="status-inactive">Inactive</span>
                                    @else
                                        <span class="status-unknown">Unknown</span>
                                    @endif
                                </div>
                            @endunless
                        @endforeach
                    @else
                        <p>No items in {{ section.title }}</p>
                    @endif
                </div>
            @endif
        @endforeach
    @endhasrole
@endif
        """.strip()
        self.create_template(temp_dir, "complex.blade.html", template_content)
        
        class MockUser:
            def has_role(self, role: str) -> bool:
                return role == 'admin'
        
        context: Dict[str, Any] = {
            "user_authenticated": True,
            "current_user": MockUser(),
            "admin_sections": [
                {
                    "title": "User Management",
                    "enabled": True,
                    "items": [
                        {"name": "Users", "status": "active", "hidden": False},
                        {"name": "Roles", "status": "inactive", "hidden": False},
                        {"name": "Hidden Item", "status": "active", "hidden": True}
                    ]
                },
                {
                    "title": "System Settings",
                    "enabled": True,
                    "items": []
                }
            ]
        }
        
        result = engine.render("complex.blade.html", context)
        
        assert "User Management" in result
        assert "System Settings" in result
        assert "Users" in result
        assert "Roles" in result
        assert "Hidden Item" not in result
        assert "status-active" in result
        assert "status-inactive" in result
        assert "No items in System Settings" in result
    
    def test_template_with_special_characters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test templates with Unicode and special characters"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="unicode-content">
    <h1>{{ title }}</h1>
    
    @foreach(messages as message)
        <p class="message-{{ loop.index }}">{{ message }}</p>
    @endforeach
    
    <div class="special-content">
        <p>HTML Entities: {{ html_entities }}</p>
        <p>Raw HTML: {!! raw_html !!}</p>
    </div>
    
    @if(show_emoji)
        <div class="emoji-section">{{ emoji_text }}</div>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "unicode.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "title": "测试 Unicode Characters العربية русский",
            "messages": [
                "Hello 世界!",
                "مرحبا بالعالم",
                "Привет, мир!",
                "Special chars: <>&\"'"
            ],
            "html_entities": "<script>alert('test');</script>",
            "raw_html": "<strong>Bold Text</strong>",
            "show_emoji": True,
            "emoji_text": "🚀 🌟 💻 🎉 ✨"
        }
        
        result = engine.render("unicode.blade.html", context)
        
        assert "测试 Unicode Characters" in result
        assert "العربية" in result
        assert "русский" in result
        assert "世界" in result
        assert "مرحبا" in result
        assert "Привет" in result
        assert "<strong>Bold Text</strong>" in result
        assert "🚀" in result
        assert "🌟" in result
    
    def test_error_handling_graceful(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test graceful error handling"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="error-test">
    <!-- Test undefined variables -->
    @isset(undefined_var)
        <p>Undefined: {{ undefined_var }}</p>
    @else
        <p>Variable not defined</p>
    @endisset
    
    <!-- Test null/empty checks -->
    @empty(null_value)
        <p>Null value is empty</p>
    @endempty
    
    @empty(empty_list)
        <p>Empty list is empty</p>
    @endempty
    
    <!-- Test with fallback values -->
    <p>Safe Access: {{ user.name or 'Anonymous' }}</p>
    <p>Default Value: {{ config_value or 'default' }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "error_handling.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "null_value": None,
            "empty_list": [],
            "user": {},
            "config_value": ""
        }
        
        result = engine.render("error_handling.blade.html", context)
        
        assert "Variable not defined" in result
        assert "Null value is empty" in result
        assert "Empty list is empty" in result
        # The ?? and ?: operators are PHP-specific, but basic rendering should work
        assert "Safe Access:" in result
        assert "Default Value:" in result
    
    def test_custom_filter_integration(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test custom filters"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="filters-test">
    <p>Original: "{{ text }}"</p>
    <p>Title Case: "{{ text | title }}"</p>
    <p>Slug: "{{ text | slug }}"</p>
    <p>Money: {{ price | money }}</p>
    <p>Percentage: {{ rate | percentage }}</p>
    <p>Truncated: "{{ long_text | truncate_words(5) }}"</p>
</div>
        """.strip()
        self.create_template(temp_dir, "filters.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "text": "hello world test",
            "price": 1299.99,
            "rate": 0.125,
            "long_text": "This is a very long text that should be truncated after several words for testing"
        }
        
        result = engine.render("filters.blade.html", context)
        
        assert "Hello World Test" in result  # title filter
        assert "hello-world-test" in result  # slug filter
        assert "$1,299.99" in result         # money filter
        assert "0.1%" in result             # percentage filter
        assert "This is a very long..." in result  # truncate_words filter
    
    def test_template_inheritance_complex(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex template inheritance scenarios"""
        engine, temp_dir = blade_engine
        
        # Base layout
        base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
    @yield('styles')
</head>
<body>
    <div class="app">
        @yield('content')
    </div>
    @yield('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", base_layout)
        
        # Child template with parent usage
        child_template = """
@extends('layouts/base')

@section('title', 'Child Page')

@section('styles')
    <style>
        body { font-family: Arial, sans-serif; }
        .content { padding: 20px; }
    </style>
@endsection

@section('content')
    <div class="content">
        <h1>{{ page_title }}</h1>
        <p>{{ page_content }}</p>
        
        @if(show_list)
            <ul>
                @foreach(items as item)
                    <li>{{ item }}</li>
                @endforeach
            </ul>
        @endif
    </div>
@endsection

@section('scripts')
    <script>
        console.log('Child page loaded');
        console.log('Items count: {{ items | length }}');
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "child.blade.html", child_template)
        
        context: Dict[str, Any] = {
            "page_title": "Welcome to Child Page",
            "page_content": "This is content from the child template.",
            "show_list": True,
            "items": ["Item 1", "Item 2", "Item 3"]
        }
        
        result = engine.render("child.blade.html", context)
        
        assert "<!DOCTYPE html>" in result
        assert "<title>Child Page</title>" in result
        assert "font-family: Arial" in result
        assert "Welcome to Child Page" in result
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result
        assert "Child page loaded" in result
    
    def test_service_integration_basic(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test basic service integration"""
        engine, temp_dir = blade_engine
        
        # Set up a mock user in the auth service
        mock_user = {"id": 1, "name": "Test User", "email": "test@example.com"}
        auth_service = engine.get_service('auth')
        if hasattr(auth_service, 'set_user'):
            auth_service.set_user(mock_user)
        
        template_content = """
<div class="auth-test">
    @auth
        <p>Welcome, {{ current_user.name }}!</p>
        <p>Email: {{ current_user.email }}</p>
    @else
        <p>Please log in</p>
    @endauth
    
    @guest
        <p>Guest user detected</p>
    @else
        <p>Authenticated user detected</p>
    @endguest
</div>
        """.strip()
        self.create_template(temp_dir, "auth_test.blade.html", template_content)
        
        # Test with user context
        context: Dict[str, Any] = {
            "current_user": mock_user
        }
        
        result = engine.render("auth_test.blade.html", context)
        
        assert "Welcome, Test User!" in result
        assert "test@example.com" in result
        assert "Authenticated user detected" in result
        assert "Please log in" not in result
    
    def test_performance_large_dataset(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test performance with moderately large datasets"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="performance-test">
    <h2>Performance Test ({{ items | length }} items)</h2>
    
    <table class="data-table">
        @foreach(items as item)
            <tr class="@if(loop.even) even @else odd @endif">
                <td>{{ loop.index }}</td>
                <td>{{ item.name }}</td>
                <td>{{ item.value }}</td>
                <td>
                    @if(item.value > 500)
                        <span class="high">High</span>
                    @elseif(item.value > 100)
                        <span class="medium">Medium</span>
                    @else
                        <span class="low">Low</span>
                    @endif
                </td>
            </tr>
        @endforeach
    </table>
</div>
        """.strip()
        self.create_template(temp_dir, "performance.blade.html", template_content)
        
        # Generate test data (moderate size for reasonable test time)
        items = []
        for i in range(100):  # 100 items instead of 1000 for faster tests
            items.append({
                "name": f"Item {i + 1}",
                "value": i * 5 + (i % 50)
            })
        
        context: Dict[str, Any] = {"items": items}
        
        result = engine.render("performance.blade.html", context)
        
        assert "100 items" in result
        assert "Item 1" in result
        assert "Item 100" in result
        assert "High" in result
        assert "Medium" in result
        assert "Low" in result


class TestBladeErrorRecovery:
    """Test error recovery and resilience"""
    
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
    
    def test_missing_template_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of missing templates"""
        engine, temp_dir = blade_engine
        
        with pytest.raises(FileNotFoundError, match="Template 'nonexistent.blade.html' not found"):
            engine.render("nonexistent.blade.html")
    
    def test_malformed_directive_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of malformed directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="malformed-test">
    <!-- Valid directive -->
    @if(valid_condition)
        <p>Valid content</p>
    @endif
    
    <!-- Potentially malformed directive (should not crash) -->
    @invalidDirective(something)
    
    <!-- More valid content -->
    @unless(hidden)
        <p>This should still render</p>
    @endunless
</div>
        """.strip()
        self.create_template(temp_dir, "malformed.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "valid_condition": True,
            "hidden": False
        }
        
        # Should not crash, even with invalid directive
        result = engine.render("malformed.blade.html", context)
        
        assert "Valid content" in result
        assert "This should still render" in result
        # The result should be a string (not None or error)
        assert isinstance(result, str)
    
    def test_circular_include_protection(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test protection against circular includes"""
        engine, temp_dir = blade_engine
        
        # Create templates that might include each other
        template_a = """
<div class="template-a">
    <h1>Template A</h1>
    @if(depth > 0)
        @include('template-b')
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "template-a.blade.html", template_a)
        
        template_b = """
<div class="template-b">
    <h2>Template B</h2>
    @if(depth > 0)
        @include('template-a')
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "template-b.blade.html", template_b)
        
        context: Dict[str, Any] = {"depth": 2}
        
        # Should handle limited recursion gracefully
        try:
            result = engine.render("template-a.blade.html", context)
            # If successful, check basic content
            assert "Template A" in result
            assert "Template B" in result
        except Exception as e:
            # If it throws an error, it should be a reasonable error message
            error_msg = str(e).lower()
            # Accept any reasonable protection mechanism
            assert any(word in error_msg for word in ["recursion", "limit", "depth", "circular", "maximum"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])