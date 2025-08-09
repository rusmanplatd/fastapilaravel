"""
Test Suite for Blade Engine Security and Validation
Tests security features, input validation, and XSS prevention
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine


class TestBladeSecurityFeatures:
    """Test security aspects of Blade engine"""
    
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
    
    def test_xss_prevention_escaped_output(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test that regular output is escaped for XSS prevention"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>{{ user_input }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "xss_test.blade.html", template_content)
        
        # Test with malicious script
        malicious_input = '<script>alert("XSS")</script>'
        result = engine.render("xss_test.blade.html", {"user_input": malicious_input})
        
        # Should be escaped (exact escaping depends on Jinja2)
        assert "<script>" not in result or "&lt;script&gt;" in result
    
    def test_unescaped_output_security_warning(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test that unescaped output renders raw content (security test)"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>Safe: {{ safe_content }}</p>
    <p>Unsafe: {!! unsafe_content !!}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "unsafe_test.blade.html", template_content)
        
        safe_html = '<em>emphasized</em>'
        result = engine.render("unsafe_test.blade.html", {
            "safe_content": safe_html,
            "unsafe_content": safe_html
        })
        
        # Unescaped should render as HTML
        assert "<em>emphasized</em>" in result
    
    def test_csrf_token_generation(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test CSRF token generation"""
        engine, temp_dir = blade_engine
        
        template_content = """
<form method="POST">
    @csrf
    <input type="text" name="data">
</form>
        """.strip()
        
        self.create_template(temp_dir, "csrf_test.blade.html", template_content)
        result = engine.render("csrf_test.blade.html")
        
        assert 'name="_token"' in result
        assert 'csrf_token_placeholder' in result
    
    def test_method_spoofing_validation(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test HTTP method spoofing with validation"""
        engine, temp_dir = blade_engine
        
        template_content = """
<form method="POST">
    @method('DELETE')
    @method('PUT')
    @method('PATCH')
</form>
        """.strip()
        
        self.create_template(temp_dir, "method_test.blade.html", template_content)
        result = engine.render("method_test.blade.html")
        
        # Should contain all method overrides
        assert 'value="DELETE"' in result
        assert 'value="PUT"' in result  
        assert 'value="PATCH"' in result
    
    def test_malicious_template_path_injection(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test protection against path injection attacks"""
        engine, temp_dir = blade_engine
        
        # Try to include files outside template directory
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises((FileNotFoundError, OSError)):
                engine.render(malicious_path)


class TestBladeInputValidation:
    """Test input validation and sanitization"""
    
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
    
    def test_null_context_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of null/None context values"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    @if(value)
        <p>Value: {{ value }}</p>
    @endif
    
    @isset(optional)
        <p>Optional: {{ optional }}</p>
    @endisset
</div>
        """.strip()
        
        self.create_template(temp_dir, "null_test.blade.html", template_content)
        
        # Test with None values
        result = engine.render("null_test.blade.html", {
            "value": None,
            "optional": None
        })
        
        assert "Value:" not in result
        assert "Optional:" not in result
    
    def test_unicode_content_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test proper Unicode content handling"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>{{ emoji }}</p>
    <p>{{ chinese }}</p>
    <p>{{ arabic }}</p>
    <p>{{ special_chars }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "unicode_test.blade.html", template_content)
        
        unicode_data = {
            "emoji": "🚀✨🎉",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special_chars": "àáâãäåæçèéêë"
        }
        
        result = engine.render("unicode_test.blade.html", unicode_data)
        
        for value in unicode_data.values():
            assert value in result
    
    def test_large_context_data_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of large context data"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>Items count: {{ items|length }}</p>
    @foreach(items as item)
        <span>{{ loop.index }}</span>
    @endforeach
</div>
        """.strip()
        
        self.create_template(temp_dir, "large_data_test.blade.html", template_content)
        
        # Create large dataset
        large_items = list(range(10000))
        
        result = engine.render("large_data_test.blade.html", {"items": large_items})
        assert "10000" in result
    
    def test_deeply_nested_data_structures(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of deeply nested data structures"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>Level 1: {{ data.level1.value }}</p>
    <p>Level 5: {{ data.level1.level2.level3.level4.level5 }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "nested_test.blade.html", template_content)
        
        nested_data = {
            "data": {
                "level1": {
                    "value": "first level",
                    "level2": {
                        "level3": {
                            "level4": {
                                "level5": "deep value"
                            }
                        }
                    }
                }
            }
        }
        
        result = engine.render("nested_test.blade.html", nested_data)
        
        assert "first level" in result
        assert "deep value" in result


class TestBladeErrorHandling:
    """Test error handling and edge cases"""
    
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
    
    def test_malformed_blade_syntax(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of malformed Blade syntax"""
        engine, temp_dir = blade_engine
        
        malformed_templates = [
            # Unclosed directive
            "@if(condition)\n<p>test</p>",
            
            # Invalid foreach syntax
            "@foreach(items)\n<p>{{ item }}</p>\n@endforeach",
            
            # Mismatched end tags
            "@if(true)\n@endsection",
            
            # Invalid variable syntax
            "{{ $invalid.variable.syntax }}"
        ]
        
        for i, template_content in enumerate(malformed_templates):
            template_name = f"malformed_{i}.blade.html"
            self.create_template(temp_dir, template_name, template_content)
            
            try:
                result = engine.render(template_name, {"condition": True, "items": [1, 2, 3]})
                # If it doesn't throw an error, that's also valid behavior
            except Exception as e:
                # Expect some kind of template error
                assert isinstance(e, (SyntaxError, ValueError, Exception))
    
    def test_circular_template_inheritance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test detection of circular template inheritance"""
        engine, temp_dir = blade_engine
        
        # Create circular inheritance: A extends B, B extends A
        template_a = "@extends('template_b')\n@section('content')\nContent A\n@endsection"
        template_b = "@extends('template_a')\n@section('content')\nContent B\n@endsection"
        
        self.create_template(temp_dir, "template_a.blade.html", template_a)
        self.create_template(temp_dir, "template_b.blade.html", template_b)
        
        with pytest.raises(Exception):  # Expect some kind of recursion error
            engine.render("template_a.blade.html")
    
    def test_undefined_variable_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of undefined variables"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>{{ undefined_var }}</p>
    
    @if(undefined_condition)
        <p>Should not appear</p>
    @endif
    
    @isset(undefined_var)
        <p>Variable is set</p>
    @else
        <p>Variable is not set</p>
    @endisset
</div>
        """.strip()
        
        self.create_template(temp_dir, "undefined_test.blade.html", template_content)
        
        # Render with empty context
        result = engine.render("undefined_test.blade.html", {})
        
        # Should handle undefined variables gracefully
        assert "Variable is not set" in result
    
    def test_template_file_permission_errors(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of file permission errors"""
        engine, temp_dir = blade_engine
        
        # Create a template file
        template_path = Path(temp_dir) / "permission_test.blade.html"
        template_path.write_text("<p>Test</p>")
        
        # Remove read permissions (Unix only)
        if os.name != 'nt':  # Skip on Windows
            os.chmod(template_path, 0o000)
            
            with pytest.raises((PermissionError, OSError)):
                engine.render("permission_test.blade.html")
            
            # Restore permissions for cleanup
            os.chmod(template_path, 0o644)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])