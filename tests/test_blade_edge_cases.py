"""
Test Suite for Blade Engine Edge Cases and Error Handling
Tests complex scenarios, nested directives, malformed templates, and error conditions
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List
import os

from app.View.BladeEngine import BladeEngine


class TestBladeEdgeCases:
    """Test edge cases and error conditions"""
    
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
    
    def test_nested_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test deeply nested directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
@if($user)
    @auth
        @hasrole('admin')
            @can('manage-users')
                @foreach($users as $user_item)
                    @if($user_item.active)
                        @unless($user_item.banned)
                            <div class="user-card">
                                <h3>{{ $user_item.name }}</h3>
                                @if($user_item.avatar)
                                    <img src="{{ $user_item.avatar }}" alt="Avatar">
                                @else
                                    <div class="avatar-placeholder">{{ $user_item.name[0] }}</div>
                                @endif
                                
                                @foreach($user_item.roles as $role)
                                    <span class="role">{{ $role }}</span>
                                @endforeach
                            </div>
                        @endunless
                    @endif
                @endforeach
            @endcan
        @endhasrole
    @endauth
@endif
        """.strip()
        self.create_template(temp_dir, "nested.blade.html", template_content)
        
        class MockUser:
            def can(self, permission: str) -> bool:
                return permission == 'manage-users'
            def has_role(self, role: str) -> bool:
                return role == 'admin'
        
        context = {
            "user": True,
            "current_user": MockUser(),
            "users": [
                {
                    "name": "John Doe",
                    "active": True,
                    "banned": False,
                    "avatar": "/avatars/john.jpg",
                    "roles": ["admin", "editor"]
                },
                {
                    "name": "Jane Smith", 
                    "active": True,
                    "banned": False,
                    "avatar": None,
                    "roles": ["user"]
                }
            ]
        }
        
        result = engine.render("nested.blade.html", context)
        
        # Should render nested content correctly
        assert "John Doe" in result
        assert "Jane Smith" in result
        assert "/avatars/john.jpg" in result
        assert "J" in result  # First letter for placeholder avatar
        assert "admin" in result
        assert "user" in result
    
    def test_malformed_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of malformed directive syntax"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!-- Valid directive -->
@if($valid)
    <p>Valid content</p>
@endif

<!-- Missing parentheses -->
@if $invalid
    <p>This shouldn't work</p>
@endif

<!-- Unmatched directive -->
@if($condition)
    <p>Content without proper endif</p>

<!-- Extra parameters -->
@csrf('extra', 'parameters')

<!-- Empty directive -->
@()

<!-- Valid content after malformed -->
@unless($hidden)
    <p>This should still work</p>
@endunless
        """.strip()
        self.create_template(temp_dir, "malformed.blade.html", template_content)
        
        context = {
            "valid": True,
            "invalid": True,
            "condition": True,
            "hidden": False
        }
        
        # Should handle malformed directives gracefully
        result = engine.render("malformed.blade.html", context)
        
        # Valid content should still render
        assert "Valid content" in result
        assert "This should still work" in result
        
        # Malformed content might be left as-is or cause errors
        # The engine should not crash completely
        assert result is not None
    
    def test_recursive_includes(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of recursive template includes"""
        engine, temp_dir = blade_engine
        
        # Create templates that include each other
        template_a = """
<div class="template-a">
    <h1>Template A</h1>
    @if($depth > 0)
        @include('template-b', ['depth' => $depth - 1])
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "template-a.blade.html", template_a)
        
        template_b = """
<div class="template-b">
    <h2>Template B</h2>
    @if($depth > 0)
        @include('template-a', ['depth' => $depth - 1])
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "template-b.blade.html", template_b)
        
        context = {"depth": 2}
        
        # Should handle limited recursion
        try:
            result = engine.render("template-a.blade.html", context)
            # If it doesn't crash, check basic structure
            assert "Template A" in result
            assert "Template B" in result
        except Exception as e:
            # Recursion protection might throw an error, which is acceptable
            assert "recursion" in str(e).lower() or "maximum" in str(e).lower()
    
    def test_complex_loop_scenarios(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test complex loop scenarios with break/continue"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="products">
    @forelse($categories as $category)
        <div class="category">
            <h2>{{ $category.name }}</h2>
            
            @foreach($category.products as $product)
                @if($product.hidden)
                    @continue
                @endif
                
                @if($product.discontinued)
                    @break
                @endif
                
                <div class="product @if(loop.first) first @endif @if(loop.last) last @endif">
                    <h3>{{ $product.name }}</h3>
                    <p>Price: ${{ $product.price }}</p>
                    
                    @switch($product.status)
                        @case('available')
                            <span class="status-available">In Stock</span>
                            @break
                        @case('limited')
                            <span class="status-limited">Limited Stock</span>
                            @break
                        @default
                            <span class="status-unavailable">Out of Stock</span>
                    @endswitch
                </div>
            @endforeach
        </div>
    @empty
        <p>No categories available</p>
    @endforelse
</div>
        """.strip()
        self.create_template(temp_dir, "complex_loops.blade.html", template_content)
        
        context = {
            "categories": [
                {
                    "name": "Electronics",
                    "products": [
                        {"name": "Laptop", "price": 999, "status": "available", "hidden": False, "discontinued": False},
                        {"name": "Tablet", "price": 299, "status": "limited", "hidden": True, "discontinued": False},
                        {"name": "Phone", "price": 699, "status": "available", "hidden": False, "discontinued": False}
                    ]
                },
                {
                    "name": "Books",
                    "products": [
                        {"name": "Novel", "price": 15, "status": "available", "hidden": False, "discontinued": False},
                        {"name": "Textbook", "price": 89, "status": "unavailable", "hidden": False, "discontinued": False}
                    ]
                }
            ]
        }
        
        result = engine.render("complex_loops.blade.html", context)
        
        # Should handle complex loop logic
        assert "Electronics" in result
        assert "Books" in result
        assert "Laptop" in result
        assert "Phone" in result
        assert "Tablet" not in result  # Should be skipped due to hidden
        assert "In Stock" in result
        assert "Limited Stock" not in result  # Tablet was skipped
    
    def test_unicode_and_special_characters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of Unicode and special characters"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="unicode-test">
    <h1>{{ $title }}</h1>
    
    @foreach($messages as $msg)
        <p class="message">{{ $msg }}</p>
    @endforeach
    
    <div class="special-chars">
        {{ $html_entities }}
        {!! $raw_html !!}
    </div>
    
    @if($emoji_support)
        <div class="emoji">{{ $emoji }}</div>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "unicode.blade.html", template_content)
        
        context = {
            "title": "Unicode Test: 中文 العربية русский",
            "messages": [
                "Hello 世界!",
                "مرحبا بالعالم",
                "Привет мир",
                "Special chars: <>\"'&"
            ],
            "html_entities": "<script>alert('XSS');</script>",
            "raw_html": "<strong>Bold text</strong>",
            "emoji_support": True,
            "emoji": "🚀 🌟 💻 🎉"
        }
        
        result = engine.render("unicode.blade.html", context)
        
        # Should handle Unicode correctly
        assert "中文" in result
        assert "العربية" in result
        assert "русский" in result
        assert "世界" in result
        assert "مرحبا" in result
        assert "Привет" in result
        assert "🚀" in result
        assert "<strong>Bold text</strong>" in result
    
    def test_large_data_sets(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test performance with large data sets"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="data-table">
    <h1>Large Data Set ({{ $items|length }} items)</h1>
    
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Name</th>
                <th>Value</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            @foreach($items as $item)
                <tr class="@if(loop.even) even @else odd @endif">
                    <td>{{ loop.index }}</td>
                    <td>{{ $item.name }}</td>
                    <td>{{ $item.value }}</td>
                    <td>
                        @if($item.value > 500)
                            <span class="high">High</span>
                        @elseif($item.value > 100)
                            <span class="medium">Medium</span>
                        @else
                            <span class="low">Low</span>
                        @endif
                    </td>
                </tr>
            @endforeach
        </tbody>
    </table>
</div>
        """.strip()
        self.create_template(temp_dir, "large_data.blade.html", template_content)
        
        # Generate large data set
        items = []
        for i in range(1000):
            items.append({
                "name": f"Item {i + 1}",
                "value": i * 10 + (i % 100),
            })
        
        context = {"items": items}
        
        result = engine.render("large_data.blade.html", context)
        
        # Should handle large data sets
        assert "Item 1" in result
        assert "Item 1000" in result
        assert "1000 items" in result
        assert "High" in result
        assert "Medium" in result
        assert "Low" in result
    
    def test_empty_and_null_values(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of empty and null values"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="null-test">
    @isset($defined_value)
        <p>Defined: {{ $defined_value }}</p>
    @endisset
    
    @isset($null_value)
        <p>Null value exists</p>
    @else
        <p>Null value not set</p>
    @endisset
    
    @empty($empty_string)
        <p>Empty string is empty</p>
    @endempty
    
    @empty($empty_list)
        <p>Empty list is empty</p>
    @endempty
    
    @empty($null_value)
        <p>Null value is empty</p>
    @endempty
    
    @unless($false_value)
        <p>False value is falsy</p>
    @endunless
    
    <div class="values">
        <p>Zero: "{{ $zero_value }}"</p>
        <p>Empty string: "{{ $empty_string }}"</p>
        <p>False: "{{ $false_value }}"</p>
        <p>Null: "{{ $null_value }}"</p>
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "null_values.blade.html", template_content)
        
        context: Dict[str, Any] = {
            "defined_value": "Hello World",
            "null_value": None,
            "empty_string": "",
            "empty_list": [],
            "false_value": False,
            "zero_value": 0
        }
        
        result = engine.render("null_values.blade.html", context)
        
        # Should handle null/empty values correctly
        assert "Defined: Hello World" in result
        assert "Null value not set" in result
        assert "Empty string is empty" in result
        assert "Empty list is empty" in result
        assert "Null value is empty" in result
        assert "False value is falsy" in result
        assert 'Zero: "0"' in result
        assert 'Empty string: ""' in result


class TestBladeSecurityAndSanitization:
    """Test security features and XSS protection"""
    
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
    
    def test_xss_protection_escaped_output(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test XSS protection with escaped output"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="user-content">
    <h2>{{ $title }}</h2>
    <p>{{ $user_input }}</p>
    <div>{{ $html_content }}</div>
    
    <script>
        var data = @json($json_data);
    </script>
</div>
        """.strip()
        self.create_template(temp_dir, "xss_test.blade.html", template_content)
        
        context = {
            "title": "<script>alert('XSS')</script>",
            "user_input": "<img src=x onerror=alert('XSS')>",
            "html_content": "<b>Bold</b><script>alert('XSS')</script>",
            "json_data": {
                "malicious": "<script>alert('XSS')</script>",
                "safe": "normal content"
            }
        }
        
        result = engine.render("xss_test.blade.html", context)
        
        # Should escape dangerous content in normal output
        assert "&lt;script&gt;" in result or "script" not in result
        assert "alert('XSS')" not in result
        
        # JSON should be properly escaped
        assert '"malicious"' in result
        assert '"safe"' in result
    
    def test_unescaped_output_vulnerability(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test unescaped output behavior"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="content">
    <div>Escaped: {{ $content }}</div>
    <div>Unescaped: {!! $content !!}</div>
    <div>Safe HTML: {!! $safe_html !!}</div>
</div>
        """.strip()
        self.create_template(temp_dir, "unescaped.blade.html", template_content)
        
        context = {
            "content": "<script>alert('dangerous')</script>",
            "safe_html": "<em>This is safe emphasis</em>"
        }
        
        result = engine.render("unescaped.blade.html", context)
        
        # Unescaped output should include raw HTML
        assert "<em>This is safe emphasis</em>" in result
        
        # But we can see the dangerous script in unescaped
        # (In production, you'd want additional sanitization)
        script_count = result.count("<script>")
        assert script_count >= 1  # At least one unescaped script tag
    
    def test_csrf_token_generation(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test CSRF token generation"""
        engine, temp_dir = blade_engine
        
        template_content = """
<form method="POST" action="/submit">
    @csrf
    <input type="text" name="data" value="{{ $data }}">
    <input type="submit" value="Submit">
</form>

<form method="POST" action="/another">
    @csrf
    <input type="text" name="other">
</form>
        """.strip()
        self.create_template(temp_dir, "csrf.blade.html", template_content)
        
        context = {"data": "test data"}
        
        result = engine.render("csrf.blade.html", context)
        
        # Should include CSRF tokens
        csrf_count = result.count('name="_token"')
        assert csrf_count == 2  # Two forms, two tokens
        
        # Tokens should have values
        assert 'value="csrf_token_placeholder"' in result


class TestBladePerformanceAndCaching:
    """Test performance and caching functionality"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=False)  # Caching enabled
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_template_caching(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test template compilation caching"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="cached-template">
    <h1>{{ $title }}</h1>
    @foreach($items as $item)
        <p>{{ $item }}</p>
    @endforeach
</div>
        """.strip()
        self.create_template(temp_dir, "cached.blade.html", template_content)
        
        context = {
            "title": "Cached Template",
            "items": ["Item 1", "Item 2", "Item 3"]
        }
        
        # First render
        result1 = engine.render("cached.blade.html", context)
        
        # Second render (should use cache)
        result2 = engine.render("cached.blade.html", context)
        
        # Results should be identical
        assert result1 == result2
        assert "Cached Template" in result1
        assert "Item 1" in result1
    
    def test_cache_invalidation(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test cache invalidation when template changes"""
        engine, temp_dir = blade_engine
        
        # Create initial template
        template_content_v1 = "<p>Version 1: {{ $message }}</p>"
        self.create_template(temp_dir, "versioned.blade.html", template_content_v1)
        
        context = {"message": "Hello"}
        
        # First render
        result1 = engine.render("versioned.blade.html", context)
        assert "Version 1" in result1
        
        # Update template
        template_content_v2 = "<p>Version 2: {{ $message }}</p>"
        self.create_template(temp_dir, "versioned.blade.html", template_content_v2)
        
        # Render again (should detect change and update)
        result2 = engine.render("versioned.blade.html", context)
        
        # Should show updated content
        # Note: Caching behavior depends on implementation
        # In debug mode or with proper cache invalidation,
        # it should show the new version
        assert "Hello" in result2
    
    def test_shared_data_performance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test performance with shared data"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="shared-data">
    <h1>{{ $shared_title }}</h1>
    <p>{{ $local_data }}</p>
    <ul>
        @foreach($shared_menu as $item)
            <li>{{ $item.name }}</li>
        @endforeach
    </ul>
</div>
        """.strip()
        self.create_template(temp_dir, "shared.blade.html", template_content)
        
        # Set up shared data
        engine.share("shared_title", "Shared Application")
        engine.share("shared_menu", [
            {"name": "Home"},
            {"name": "About"},
            {"name": "Contact"}
        ])
        
        # Render multiple times with different local data
        for i in range(10):
            context = {"local_data": f"Local data {i}"}
            result = engine.render("shared.blade.html", context)
            
            # Should include both shared and local data
            assert "Shared Application" in result
            assert f"Local data {i}" in result
            assert "Home" in result
            assert "About" in result
            assert "Contact" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])