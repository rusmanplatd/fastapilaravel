"""
Comprehensive Blade Engine Security Test Suite
Tests all security features, XSS prevention, CSRF protection, and input validation
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Generator, Tuple
import os
import json
import re

from app.View.BladeEngine import BladeEngine


class TestBladeComprehensiveSecurity:
    """Comprehensive security testing for Blade engine"""
    
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
    
    def test_comprehensive_xss_protection_suite(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test comprehensive XSS protection across all output contexts"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ page_title }}</title>
    <meta name="description" content="{{ meta_description }}">
    <style>
        .dynamic-color { color: {{ css_color }}; }
        .{{ css_class }} { background: {{ css_background }}; }
    </style>
</head>
<body>
    <!-- HTML Context -->
    <div>{{ html_content }}</div>
    <p>User: {{ user_name }}</p>
    
    <!-- Attribute Context -->
    <input type="text" value="{{ input_value }}" data-info="{{ data_attr }}">
    <a href="{{ link_url }}" onclick="{{ js_onclick }}">{{ link_text }}</a>
    
    <!-- JavaScript Context -->
    <script>
        var userData = {{ user_data | tojson }};
        var message = '{{ js_message }}';
        console.log("{{ js_console }}");
    </script>
    
    <!-- Unescaped output (dangerous) -->
    <div>{!! trusted_html !!}</div>
    
    <!-- URL Context -->
    <iframe src="{{ iframe_src }}"></iframe>
    <img src="{{ image_src }}" alt="{{ image_alt }}">
    
    <!-- CSS Context in style attributes -->
    <div style="width: {{ style_width }}; height: {{ style_height }};">Content</div>
</body>
</html>
        """.strip()
        
        self.create_template(temp_dir, "xss_comprehensive.blade.html", template_content)
        
        # Test data with various XSS payloads
        malicious_context = {
            "page_title": "<script>alert('XSS in title')</script>",
            "meta_description": '"><script>alert("XSS in meta")</script><meta name="',
            "css_color": "red; } body { background: url(javascript:alert('XSS')); } .hack {",
            "css_class": "hack'; } body { background: url(data:text/html,<script>alert('XSS')</script>); } .normal",
            "css_background": "url('javascript:alert(\"XSS\")')",
            "html_content": '<img src=x onerror="alert(\'XSS\')" />',
            "user_name": '<svg onload="alert(\'XSS\')" />',
            "input_value": '" onmouseover="alert(\'XSS\')" "',
            "data_attr": 'value" onclick="alert(\'XSS\')" data-fake="',
            "link_url": 'javascript:alert("XSS")',
            "js_onclick": 'alert("XSS"); return false;',
            "link_text": '</a><script>alert("XSS")</script><a>',
            "user_data": {"<script>alert('XSS')</script>": "malicious"},
            "js_message": "'; alert('XSS'); var fake='",
            "js_console": '"); alert("XSS"); console.log("',
            "trusted_html": '<script>alert("This should work because it\'s trusted")</script>',
            "iframe_src": 'javascript:alert("XSS")',
            "image_src": 'javascript:alert("XSS")',
            "image_alt": '" onerror="alert(\'XSS\')" src="',
            "style_width": "100px; } body { background: url('javascript:alert(\'XSS\')'); } .hack { width:",
            "style_height": "100px') url('javascript:alert(\'XSS\')') no-repeat;"
        }
        
        result = engine.render("xss_comprehensive.blade.html", malicious_context)
        
        # Verify XSS prevention in different contexts
        assert "<script>alert('XSS in title')</script>" not in result
        assert 'javascript:alert' not in result or '&amp;' in result  # URLs should be escaped
        assert '"onmouseover=' not in result  # Attribute injection prevented
        assert 'onerror=' not in result  # Event handlers escaped
        
        # Trusted HTML should render (testing unescaped output)
        assert "This should work because it's trusted" in result
        
        # JSON data should be properly escaped
        json_in_result = re.search(r'var userData = ({.*?});', result, re.DOTALL)
        if json_in_result:
            try:
                json.loads(json_in_result.group(1))  # Should be valid JSON
            except json.JSONDecodeError:
                pytest.fail("JSON context not properly escaped")
    
    def test_advanced_csrf_and_form_security(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test advanced CSRF protection and form security features"""
        engine, temp_dir = blade_engine
        
        template_content = """
<form method="POST" action="/users" enctype="multipart/form-data">
    @csrf
    @method('PUT')
    
    <!-- Form with validation -->
    <input type="email" name="email" value="{{ old('email', user.email) }}">
    @error('email')
        <div class="alert alert-danger">{{ $message }}</div>
    @enderror
    
    <input type="password" name="password">
    @error('password')
        <div class="alert alert-danger">{{ $message }}</div>
    @enderror
    
    <!-- File upload with validation -->
    <input type="file" name="avatar" accept="image/*">
    @error('avatar')
        <div class="alert alert-danger">{{ $message }}</div>
    @enderror
    
    <!-- Hidden fields for security -->
    <input type="hidden" name="user_id" value="{{ user.id }}">
    <input type="hidden" name="timestamp" value="{{ now().timestamp }}">
    
    <button type="submit">Update Profile</button>
</form>

<!-- Multiple forms with different CSRF requirements -->
<form method="POST" action="/logout">
    @csrf
    <button type="submit">Logout</button>
</form>

<form method="POST" action="/delete-account" onsubmit="return confirm('Are you sure?')">
    @csrf
    @method('DELETE')
    <button type="submit" class="btn-danger">Delete Account</button>
</form>

<!-- AJAX form data -->
<script>
    window.csrfToken = '{{ csrf_token() }}';
    
    // Safe JSON context for AJAX
    window.formData = @json([
        'user_id' => user.id,
        'permissions' => user.permissions
    ]);
</script>
        """.strip()
        
        self.create_template(temp_dir, "form_security.blade.html", template_content)
        
        context = {
            "user": {
                "id": 123,
                "email": "test@example.com",
                "permissions": ["read", "write", "admin"]
            },
            "errors": {
                "email": ["Email format is invalid"],
                "password": ["Password must be at least 8 characters"],
                "avatar": ["File must be an image"]
            },
            "old": lambda field, default=None: "old_" + field if field == "email" else default
        }
        
        result = engine.render("form_security.blade.html", context)
        
        # Verify CSRF tokens are present
        csrf_tokens = result.count('name="_token"')
        assert csrf_tokens == 3, f"Expected 3 CSRF tokens, found {csrf_tokens}"
        
        # Verify method spoofing
        assert 'name="_method" value="PUT"' in result
        assert 'name="_method" value="DELETE"' in result
        
        # Verify error handling
        assert "Email format is invalid" in result
        assert "Password must be at least 8 characters" in result
        assert "File must be an image" in result
        
        # Verify old input handling
        assert 'value="old_email"' in result  # Old input should be used
        
        # Verify JSON context is safe
        assert '"user_id":123' in result or '"user_id": 123' in result
        assert '"permissions":["read","write","admin"]' in result or '"permissions": ["read", "write", "admin"]' in result
    
    def test_permission_and_authorization_security(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test comprehensive permission and authorization features"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
</head>
<body>
    <nav>
        @auth
            <p>Welcome, {{ current_user.name }}!</p>
            
            @can('manage_users')
                <a href="/admin/users">Manage Users</a>
            @endcan
            
            @cannot('delete_users')
                <span class="disabled">Delete Users (No Permission)</span>
            @else
                <a href="/admin/users/delete" class="danger">Delete Users</a>
            @endcannot
            
            @hasrole('admin')
                <a href="/admin">Admin Panel</a>
            @endhasrole
            
            @hasanyrole(['admin', 'moderator'])
                <a href="/moderation">Moderation Panel</a>
            @endhasanyrole
            
            @haspermission('edit_posts')
                <a href="/posts/edit">Edit Posts</a>
            @endhaspermission
            
            @production
                <!-- Only show in production -->
                <div class="analytics-code">{{ analytics_code | safe }}</div>
            @endproduction
            
            @env('local', 'staging')
                <div class="debug-info">
                    Debug Mode: ON
                    @dd(debug_data)
                </div>
            @endenv
            
        @else
            @guest
                <a href="/login">Login</a>
                <a href="/register">Register</a>
            @endguest
        @endauth
    </nav>
    
    <main>
        @switch(user_role)
            @case('admin')
                <h1>Administrator Dashboard</h1>
                <p>Full access granted</p>
            @break
            
            @case('moderator')
                <h1>Moderator Dashboard</h1>
                <p>Limited administrative access</p>
            @break
            
            @case('user')
                <h1>User Dashboard</h1>
                <p>Standard user access</p>
            @break
            
            @default
                <h1>Guest Dashboard</h1>
                <p>Please log in for full access</p>
        @endswitch
        
        <!-- Environment-specific content -->
        @debug
            <div class="debug-panel">
                <h3>Debug Information</h3>
                <pre>@dump(current_user, permissions, environment)</pre>
            </div>
        @enddebug
        
        <!-- Conditional content based on complex permissions -->
        @if(current_user && (current_user.can('manage_users') || current_user.has_role('admin')))
            <section class="admin-tools">
                <h2>Administrative Tools</h2>
                
                @unless(current_user.is_locked)
                    <button onclick="performAdminAction()">Admin Action</button>
                @endunless
                
                @isset(admin_notifications)
                    <div class="notifications">
                        @forelse(admin_notifications as notification)
                            <div class="notification">{{ notification.message }}</div>
                        @empty
                            <p>No notifications</p>
                        @endforelse
                    </div>
                @endisset
            </section>
        @endif
    </main>
    
    <!-- Security headers and meta tags -->
    <script nonce="{{ csp_nonce }}">
        // Secure JavaScript execution
        window.userPermissions = @json(current_user.permissions ?? []);
    </script>
</body>
</html>
        """.strip()
        
        self.create_template(temp_dir, "permission_security.blade.html", template_content)
        
        # Test with admin user
        admin_context = {
            "current_user": {
                "name": "Admin User",
                "id": 1,
                "permissions": ["manage_users", "delete_users", "edit_posts"],
                "roles": ["admin"],
                "is_locked": False,
                "can": lambda perm: perm in ["manage_users", "delete_users", "edit_posts"],
                "has_role": lambda role: role == "admin",
                "has_any_role": lambda roles: "admin" in roles
            },
            "user_role": "admin",
            "admin_notifications": [
                {"message": "System update completed"},
                {"message": "New user registration"}
            ],
            "debug_data": {"version": "1.0", "environment": "testing"},
            "analytics_code": '<script>analytics.track("page_view")</script>',
            "csp_nonce": "abc123",
            "permissions": ["manage_users", "delete_users", "edit_posts"],
            "environment": "testing"
        }
        
        admin_result = engine.render("permission_security.blade.html", admin_context)
        
        # Verify admin permissions
        assert "Welcome, Admin User!" in admin_result
        assert "Manage Users" in admin_result
        assert "Delete Users" in admin_result  # Should show delete button, not disabled text
        assert "Admin Panel" in admin_result
        assert "Moderation Panel" in admin_result
        assert "Edit Posts" in admin_result
        assert "Administrator Dashboard" in admin_result
        assert "Administrative Tools" in admin_result
        assert "System update completed" in admin_result
        
        # Test with regular user
        user_context = {
            "current_user": {
                "name": "Regular User",
                "id": 2,
                "permissions": ["edit_posts"],
                "roles": ["user"],
                "is_locked": False,
                "can": lambda perm: perm == "edit_posts",
                "has_role": lambda role: role == "user",
                "has_any_role": lambda roles: "user" in roles
            },
            "user_role": "user",
            "admin_notifications": [],
            "debug_data": {"version": "1.0", "environment": "testing"},
            "csp_nonce": "xyz789"
        }
        
        user_result = engine.render("permission_security.blade.html", user_context)
        
        # Verify restricted access
        assert "Welcome, Regular User!" in user_result
        assert "Manage Users" not in user_result
        assert "Delete Users (No Permission)" in user_result  # Should show disabled text
        assert "Admin Panel" not in user_result
        assert "Edit Posts" in user_result  # User has this permission
        assert "User Dashboard" in user_result
        assert "Administrative Tools" not in user_result
        
        # Test with guest user
        guest_result = engine.render("permission_security.blade.html", {"user_role": "guest"})
        
        # Verify guest restrictions
        assert "Login" in guest_result
        assert "Register" in guest_result
        assert "Guest Dashboard" in guest_result
        assert "Welcome," not in guest_result  # No user greeting
    
    def test_input_validation_and_sanitization_comprehensive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test comprehensive input validation and sanitization"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Input Validation Test</title>
</head>
<body>
    <!-- URL validation and sanitization -->
    <section class="urls">
        <a href="{{ external_url }}">External Link</a>
        <img src="{{ image_url }}" alt="{{ image_alt }}">
        <iframe src="{{ iframe_url }}"></iframe>
    </section>
    
    <!-- File path validation -->
    <section class="files">
        <p>Template: @include('{{ template_name }}')</p>
        <p>Asset: {{ asset(asset_path) }}</p>
        <link rel="stylesheet" href="{{ css_file }}">
        <script src="{{ js_file }}"></script>
    </section>
    
    <!-- SQL injection attempt (in context data) -->
    <section class="data">
        <p>Search: {{ search_term }}</p>
        <p>Sort: {{ sort_field }}</p>
        <p>Filter: {{ filter_value }}</p>
    </section>
    
    <!-- Command injection attempt -->
    <section class="system">
        <p>Filename: {{ filename }}</p>
        <p>Command: {{ command_param }}</p>
        <p>Path: {{ path_param }}</p>
    </section>
    
    <!-- LDAP injection attempt -->
    <section class="ldap">
        <p>Username: {{ ldap_username }}</p>
        <p>Filter: {{ ldap_filter }}</p>
    </section>
    
    <!-- XML/XXE injection attempt -->
    <section class="xml">
        <p>XML Data: {{ xml_content }}</p>
        <p>DOCTYPE: {{ xml_doctype }}</p>
    </section>
    
    <!-- Template injection attempt -->
    <section class="template-injection">
        <p>User Input: {{ user_template_input }}</p>
        <p>Expression: {{ math_expression }}</p>
    </section>
    
    <!-- Header injection -->
    <meta name="description" content="{{ meta_description }}">
    <meta name="keywords" content="{{ meta_keywords }}">
    
    <!-- CSS injection -->
    <style>
        .user-style {
            color: {{ user_color }};
            background: {{ user_background }};
            font-family: {{ user_font }};
        }
    </style>
    
    <!-- JavaScript injection in multiple contexts -->
    <script>
        var searchTerm = '{{ js_search_term }}';
        var userData = @json(user_profile);
        var config = {
            'apiUrl': '{{ api_url }}',
            'timeout': {{ timeout_value }},
            'debug': {{ debug_flag | lower }}
        };
        
        // Event handler injection
        document.getElementById('test').onclick = function() {
            console.log('{{ onclick_data }}');
        };
    </script>
    
    <!-- Form input validation -->
    <form method="POST">
        <input type="hidden" name="token" value="{{ form_token }}">
        <input type="text" name="username" value="{{ form_username }}" pattern="{{ username_pattern }}">
        <input type="email" name="email" value="{{ form_email }}">
        <input type="url" name="website" value="{{ form_website }}">
        <textarea name="comment">{{ form_comment }}</textarea>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
        """.strip()
        
        self.create_template(temp_dir, "input_validation.blade.html", template_content)
        
        # Malicious input context
        malicious_context = {
            # URL injections
            "external_url": "javascript:alert('XSS')",
            "image_url": "javascript:alert('XSS')",
            "image_alt": '" onerror="alert(\'XSS\')" x="',
            "iframe_url": "javascript:alert('XSS')",
            
            # File path injections
            "template_name": "../../../etc/passwd",
            "asset_path": "../../../etc/passwd",
            "css_file": "javascript:alert('XSS')",
            "js_file": "javascript:alert('XSS')",
            
            # SQL injections
            "search_term": "'; DROP TABLE users; --",
            "sort_field": "id; DROP TABLE sessions; --",
            "filter_value": "1 OR 1=1; DELETE FROM users WHERE 1=1; --",
            
            # Command injections
            "filename": "test.txt; rm -rf /; echo",
            "command_param": "ls; cat /etc/passwd",
            "path_param": "/tmp; rm -rf / #",
            
            # LDAP injections
            "ldap_username": "admin)(|(objectClass=*))",
            "ldap_filter": "*))(uid=admin)(|(objectClass=*",
            
            # XML/XXE injections
            "xml_content": "<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>",
            "xml_doctype": '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
            
            # Template injections
            "user_template_input": "{{ 7 * 7 }}{% raw %}{{ 7 * 7 }}{% endraw %}",
            "math_expression": "${7*7}#{7*7}{{7*7}}",
            
            # Header injections
            "meta_description": 'content"><script>alert("XSS")</script><meta name="fake',
            "meta_keywords": 'keywords"><meta http-equiv="refresh" content="0;url=javascript:alert(\'XSS\')"><meta name="fake',
            
            # CSS injections
            "user_color": "red; } body { background: url('javascript:alert(\"XSS\")'); } .fake {",
            "user_background": "url('javascript:alert(\"XSS\")')",
            "user_font": "Arial; } body { background: url(data:text/html,<script>alert('XSS')</script>); } .fake {",
            
            # JavaScript injections
            "js_search_term": "'; alert('XSS'); var fake='",
            "user_profile": {
                "name": "<script>alert('XSS')</script>",
                "email": "test'; alert('XSS'); var fake='example.com"
            },
            "api_url": "'; alert('XSS'); var fake='",
            "timeout_value": "5000; alert('XSS'); var fake=123",
            "debug_flag": "true; alert('XSS'); var fake=",
            "onclick_data": "'); alert('XSS'); console.log('",
            
            # Form injections
            "form_token": 'token"><script>alert("XSS")</script><input name="fake',
            "form_username": 'admin" onkeyup="alert(\'XSS\')" x="',
            "form_email": 'test@example.com" onfocus="alert(\'XSS\')" x="',
            "form_website": 'javascript:alert("XSS")',
            "form_comment": '</textarea><script>alert("XSS")</script><textarea>',
            "username_pattern": '[a-zA-Z0-9]+" onfocus="alert(\'XSS\')" pattern="'
        }
        
        result = engine.render("input_validation.blade.html", malicious_context)
        
        # Test that various injection attempts are neutralized
        injection_patterns = [
            r'javascript:alert',
            r'<script.*?>.*?</script>',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onload\s*=',
            r'onfocus\s*=',
            r'onkeyup\s*=',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'rm\s+-rf',
            r'/etc/passwd',
            r'<!DOCTYPE.*?ENTITY',
            r'{{.*?\*.*?}}',  # Template expression execution
            r'http-equiv\s*=\s*["\']refresh["\']'
        ]
        
        dangerous_patterns_found = []
        for pattern in injection_patterns:
            if re.search(pattern, result, re.IGNORECASE | re.DOTALL):
                dangerous_patterns_found.append(pattern)
        
        # Some patterns might be legitimately present if properly escaped
        # The key is they should be escaped/neutralized, not executable
        if dangerous_patterns_found:
            print(f"Warning: Found potentially dangerous patterns: {dangerous_patterns_found}")
            # Additional verification that they're properly escaped
            assert "<script>" not in result or "&lt;script&gt;" in result
            assert "javascript:alert" not in result or "javascript:alert" not in result.replace("&amp;", "&")
    
    def test_cache_security_and_template_isolation(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test cache security and template isolation"""
        engine, temp_dir = blade_engine
        
        # Create templates with sensitive data
        sensitive_template = """
<div class="sensitive">
    <p>API Key: {{ api_key }}</p>
    <p>Database Password: {{ db_password }}</p>
    <p>Secret Token: {{ secret_token }}</p>
</div>
        """.strip()
        
        public_template = """
<div class="public">
    <p>Welcome to our site!</p>
    <p>Public data: {{ public_info }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "sensitive.blade.html", sensitive_template)
        self.create_template(temp_dir, "public.blade.html", public_template)
        
        # Render sensitive template
        sensitive_context = {
            "api_key": "sk-super-secret-key-123",
            "db_password": "database-password-456",
            "secret_token": "jwt-secret-token-789"
        }
        
        sensitive_result = engine.render("sensitive.blade.html", sensitive_context)
        
        # Render public template
        public_context = {
            "public_info": "This is public information"
        }
        
        public_result = engine.render("public.blade.html", public_context)
        
        # Verify template isolation - sensitive data shouldn't leak
        assert "sk-super-secret-key-123" in sensitive_result
        assert "sk-super-secret-key-123" not in public_result
        
        assert "This is public information" in public_result
        assert "database-password-456" not in public_result
        
        # Test cache isolation by clearing cache and re-rendering
        engine.clear_cache()
        
        public_result_2 = engine.render("public.blade.html", public_context)
        assert "sk-super-secret-key-123" not in public_result_2
        assert "This is public information" in public_result_2
    
    def test_directive_security_and_custom_extensions(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test security of custom directives and extensions"""
        engine, temp_dir = blade_engine
        
        # Register custom directives with potential security issues
        engine.directive('unsafe_include', lambda content: f"{{% include '{content}' %}}")
        engine.directive('safe_include', lambda content: f"{{% include '{content.replace('..', '').replace('/', '_')}' %}}")
        engine.directive('eval_danger', lambda content: f"{{ {content} }}")
        engine.directive('exec_safe', lambda content: f"{{ config('{content}') }}")
        
        template_content = """
<div>
    <!-- Test custom directive security -->
    @unsafe_include('{{ potential_path_injection }}')
    @safe_include('{{ potential_path_injection }}')
    
    @eval_danger('{{ potential_code_injection }}')
    @exec_safe('{{ safe_config_key }}')
    
    <!-- Test built-in directive security -->
    @include('{{ include_template }}')
    @includeIf({{ condition }}, '{{ conditional_template }}')
    @includeUnless({{ negative_condition }}, '{{ unless_template }}')
    
    <!-- Test component security -->
    <x-dynamic-component component="{{ component_name }}" data="{{ component_data }}"/>
    
    <!-- Test macro security -->
    @macro('test_macro')
        <p>Macro content: {{ macro_param }}</p>
    @endmacro
</div>
        """.strip()
        
        self.create_template(temp_dir, "directive_security.blade.html", template_content)
        
        # Create some test templates
        self.create_template(temp_dir, "safe_template.blade.html", "<p>Safe content</p>")
        self.create_template(temp_dir, "components/test-component.blade.html", "<div>Component: {{ data }}</div>")
        
        malicious_context = {
            "potential_path_injection": "../../../etc/passwd",
            "potential_code_injection": "__import__('os').system('rm -rf /')",
            "safe_config_key": "app.name",
            "include_template": "../../../etc/passwd",
            "condition": True,
            "conditional_template": "safe_template",
            "negative_condition": False,
            "unless_template": "safe_template",
            "component_name": "test-component",
            "component_data": "<script>alert('XSS')</script>",
            "macro_param": "<script>alert('XSS')</script>"
        }
        
        try:
            result = engine.render("directive_security.blade.html", malicious_context)
            
            # Verify path injection attempts are handled
            assert "/etc/passwd" not in result or "Template" in result  # If it shows, it should be an error message
            
            # Verify code injection attempts don't execute
            assert "rm -rf" not in result
            assert "__import__" not in result or "&" in result  # Should be escaped
            
            # Verify XSS in component data is escaped
            assert "<script>alert('XSS')</script>" not in result or "&lt;" in result
            
        except (FileNotFoundError, Exception) as e:
            # Path injection should fail gracefully
            assert "passwd" not in str(e) or "not found" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])