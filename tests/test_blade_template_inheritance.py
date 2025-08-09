"""
Test Suite for Blade Template Inheritance and Composition
Tests @extends, @section, @yield, @parent, complex layouts and nested inheritance
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import os

from app.View.BladeEngine import BladeEngine


class TestBladeTemplateInheritance:
    """Test template inheritance features"""
    
    @pytest.fixture
    def blade_engine(self) -> Any:
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
    
    def test_basic_template_inheritance(self, blade_engine: Any) -> None:
        """Test basic @extends and @section functionality"""
        engine, temp_dir = blade_engine
        
        # Create base layout template
        layout_content = """
<!DOCTYPE html>
<html lang="{{ $locale ?? 'en' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'Default Title')</title>
    
    @hasSection('meta')
        @yield('meta')
    @endif
    
    <link rel="stylesheet" href="/css/app.css">
    @yield('styles')
</head>
<body class="@yield('body_class', 'default-body')">
    <header class="main-header">
        @yield('header')
    </header>
    
    <nav class="main-nav">
        @yield('navigation', '<div>Default Navigation</div>')
    </nav>
    
    <main class="main-content">
        @yield('content')
    </main>
    
    <footer class="main-footer">
        @yield('footer', '<p>&copy; 2025 Default Footer</p>')
    </footer>
    
    <script src="/js/app.js"></script>
    @yield('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", layout_content)
        
        # Create child template
        child_content = """
@extends('layouts/base')

@section('title', 'Home Page')

@section('meta')
    <meta name="description" content="Welcome to our homepage">
    <meta name="keywords" content="home, welcome, main">
@endsection

@section('header')
    <h1>Welcome to Our Site</h1>
    <div class="header-actions">
        <a href="/login">Login</a>
        <a href="/register">Register</a>
    </div>
@endsection

@section('content')
    <div class="hero-section">
        <h2>{{ $page_title }}</h2>
        <p>{{ $page_description }}</p>
        
        @if($featured_items)
            <div class="featured-items">
                @foreach($featured_items as $item)
                    <div class="featured-item">
                        <h3>{{ $item.title }}</h3>
                        <p>{{ $item.description }}</p>
                    </div>
                @endforeach
            </div>
        @endif
    </div>
@endsection

@section('styles')
    <style>
        .hero-section { padding: 2rem; }
        .featured-item { margin: 1rem 0; }
    </style>
@endsection

@section('scripts')
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Homepage loaded');
        });
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "pages/home.blade.html", child_content)
        
        context = {
            "locale": "en",
            "page_title": "Welcome Home",
            "page_description": "This is our amazing homepage with great content.",
            "featured_items": [
                {"title": "Feature 1", "description": "Description of feature 1"},
                {"title": "Feature 2", "description": "Description of feature 2"}
            ]
        }
        
        result = engine.render("pages/home.blade.html", context)
        
        # Test inheritance structure
        assert "<!DOCTYPE html>" in result
        assert '<title>Home Page</title>' in result
        assert 'lang="en"' in result
        
        # Test section content
        assert "Welcome to Our Site" in result
        assert "Welcome Home" in result
        assert "This is our amazing homepage" in result
        assert "Feature 1" in result
        assert "Feature 2" in result
        
        # Test default content
        assert "Default Navigation" in result
        assert "&copy; 2025 Default Footer" in result
        
        # Test styles and scripts
        assert ".hero-section { padding: 2rem; }" in result
        assert "console.log('Homepage loaded');" in result
        
        # Test meta tags
        assert 'name="description"' in result
        assert 'name="keywords"' in result
    
    def test_nested_template_inheritance(self, blade_engine: Any) -> None:
        """Test multi-level template inheritance"""
        engine, temp_dir = blade_engine
        
        # Base layout
        base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
    @yield('head')
</head>
<body>
    <div class="app">
        @yield('app_content')
    </div>
    @yield('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", base_layout)
        
        # Admin layout (extends base)
        admin_layout = """
@extends('layouts/app')

@section('title')
    Admin Panel - @yield('page_title')
@endsection

@section('head')
    <link rel="stylesheet" href="/css/admin.css">
    @yield('admin_styles')
@endsection

@section('app_content')
    <div class="admin-wrapper">
        <aside class="admin-sidebar">
            @yield('sidebar', '<nav>Default Admin Menu</nav>')
        </aside>
        
        <main class="admin-main">
            <div class="admin-header">
                <h1>@yield('page_title', 'Admin Dashboard')</h1>
                @yield('page_actions')
            </div>
            
            <div class="admin-content">
                @yield('content')
            </div>
        </main>
    </div>
@endsection

@section('scripts')
    <script src="/js/admin.js"></script>
    @yield('admin_scripts')
@endsection
        """.strip()
        self.create_template(temp_dir, "layouts/admin.blade.html", admin_layout)
        
        # Specific admin page (extends admin layout)
        users_page = """
@extends('layouts/admin')

@section('page_title', 'User Management')

@section('sidebar')
    <nav class="admin-nav">
        <a href="/admin/dashboard" class="nav-link">Dashboard</a>
        <a href="/admin/users" class="nav-link active">Users</a>
        <a href="/admin/settings" class="nav-link">Settings</a>
    </nav>
@endsection

@section('page_actions')
    <div class="page-actions">
        <button class="btn btn-primary" onclick="addUser()">Add User</button>
        <button class="btn btn-secondary" onclick="exportUsers()">Export</button>
    </div>
@endsection

@section('content')
    <div class="users-table">
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                @forelse($users as $user)
                    <tr>
                        <td>{{ $user.id }}</td>
                        <td>{{ $user.name }}</td>
                        <td>{{ $user.email }}</td>
                        <td>
                            <button onclick="editUser({{ $user.id }})">Edit</button>
                            <button onclick="deleteUser({{ $user.id }})">Delete</button>
                        </td>
                    </tr>
                @empty
                    <tr>
                        <td colspan="4" class="no-data">No users found</td>
                    </tr>
                @endforelse
            </tbody>
        </table>
    </div>
@endsection

@section('admin_styles')
    <style>
        .users-table { margin-top: 1rem; }
        .data-table { width: 100%; }
        .no-data { text-align: center; font-style: italic; }
    </style>
@endsection

@section('admin_scripts')
    <script>
        function addUser() { console.log('Adding user'); }
        function editUser(id) { console.log('Editing user', id); }
        function deleteUser(id) { console.log('Deleting user', id); }
        function exportUsers() { console.log('Exporting users'); }
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "admin/users.blade.html", users_page)
        
        context = {
            "users": [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
                {"id": 3, "name": "Bob Johnson", "email": "bob@example.com"}
            ]
        }
        
        result = engine.render("admin/users.blade.html", context)
        
        # Test multi-level inheritance
        assert "<!DOCTYPE html>" in result
        assert "<title>Admin Panel - User Management</title>" in result
        assert "admin.css" in result
        assert "admin.js" in result
        
        # Test nested sections
        assert "nav-link active" in result
        assert "Add User" in result
        assert "Export" in result
        
        # Test content rendering
        assert "John Doe" in result
        assert "john@example.com" in result
        assert "Jane Smith" in result
        assert "Bob Johnson" in result
        
        # Test JavaScript functions
        assert "function addUser()" in result
        assert "function editUser(id)" in result
        
        # Test CSS styles
        assert ".users-table { margin-top: 1rem; }" in result
    
    def test_section_parent_functionality(self, blade_engine: Any) -> None:
        """Test @parent directive for extending parent sections"""
        engine, temp_dir = blade_engine
        
        # Base template with section content
        base_template = """
<div class="layout">
    <div class="styles">
        @yield('styles')
    </div>
    
    <div class="content">
        @yield('content')
    </div>
    
    <div class="scripts">
        @yield('scripts')
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", base_template)
        
        # Middle layer that adds to sections
        middle_template = """
@extends('layouts/base')

@section('styles')
    <style>
        /* Base styles from middle layer */
        .container { max-width: 1200px; margin: 0 auto; }
        .card { border: 1px solid #ddd; border-radius: 4px; }
    </style>
@endsection

@section('content')
    <div class="container">
        <header class="page-header">
            <h1>@yield('page_title', 'Default Page')</h1>
        </header>
        
        <div class="page-content">
            @yield('page_content')
        </div>
    </div>
@endsection

@section('scripts')
    <script>
        // Base scripts from middle layer
        console.log('Middle layer loaded');
        
        function showAlert(message) {
            alert(message);
        }
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "layouts/page.blade.html", middle_template)
        
        # Final template that extends parent sections
        final_template = """
@extends('layouts/page')

@section('page_title', 'Enhanced Page with Parent Content')

@section('styles')
    @parent
    <style>
        /* Additional styles extending parent */
        .enhanced-section { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            color: white;
        }
        .feature-box {
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 8px;
        }
    </style>
@endsection

@section('page_content')
    <div class="enhanced-section">
        <h2>Welcome to Enhanced Page</h2>
        <p>{{ $welcome_message }}</p>
        
        @if($features)
            <div class="features">
                @foreach($features as $feature)
                    <div class="feature-box card">
                        <h3>{{ $feature.title }}</h3>
                        <p>{{ $feature.description }}</p>
                        
                        @if($feature.enabled)
                            <span class="status enabled">Enabled</span>
                        @else
                            <span class="status disabled">Disabled</span>
                        @endif
                    </div>
                @endforeach
            </div>
        @endif
        
        <button onclick="showAlert('Parent function works!')" class="btn">
            Test Parent Script
        </button>
    </div>
@endsection

@section('scripts')
    @parent
    <script>
        // Additional scripts extending parent
        console.log('Final layer loaded');
        
        function enhancedAlert(message, type = 'info') {
            // Enhanced version of parent function
            const prefix = type.toUpperCase() + ': ';
            showAlert(prefix + message);
        }
        
        // Initialize enhanced features
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Enhanced page ready');
        });
    </script>
@endsection
        """.strip()
        self.create_template(temp_dir, "enhanced-page.blade.html", final_template)
        
        context = {
            "welcome_message": "This page demonstrates parent section extension.",
            "features": [
                {
                    "title": "Advanced Styling",
                    "description": "Gradient backgrounds and modern design",
                    "enabled": True
                },
                {
                    "title": "Enhanced JavaScript",
                    "description": "Extended functionality with parent support",
                    "enabled": True
                },
                {
                    "title": "Future Feature",
                    "description": "Coming soon in the next release",
                    "enabled": False
                }
            ]
        }
        
        result = engine.render("enhanced-page.blade.html", context)
        
        # Test that parent content is included
        assert "/* Base styles from middle layer */" in result
        assert ".container { max-width: 1200px;" in result
        assert ".card { border: 1px solid #ddd;" in result
        
        # Test that child content is added
        assert ".enhanced-section {" in result
        assert "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" in result
        assert ".feature-box {" in result
        
        # Test parent JavaScript inclusion
        assert "console.log('Middle layer loaded');" in result
        assert "function showAlert(message)" in result
        
        # Test child JavaScript addition
        assert "console.log('Final layer loaded');" in result
        assert "function enhancedAlert(message, type = 'info')" in result
        
        # Test content rendering
        assert "Enhanced Page with Parent Content" in result
        assert "This page demonstrates parent section extension" in result
        assert "Advanced Styling" in result
        assert "Enhanced JavaScript" in result
        assert "Future Feature" in result
        assert "Enabled" in result
        assert "Disabled" in result
    
    def test_section_overwrite_and_append(self, blade_engine: Any) -> None:
        """Test @overwrite and @append directives"""
        engine, temp_dir = blade_engine
        
        # Base layout
        base_layout = """
<div class="document">
    <div class="metadata">
        @yield('metadata')
    </div>
    
    <div class="introduction">
        @yield('introduction')
    </div>
    
    <div class="main-content">
        @yield('content')
    </div>
    
    <div class="conclusion">
        @yield('conclusion')
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "layouts/document.blade.html", base_layout)
        
        # Child template demonstrating overwrite and append
        child_template = """
@extends('layouts/document')

@section('metadata')
    <meta name="author" content="Original Author">
    <meta name="date" content="2025-01-01">
@endsection

@section('introduction')
    <h1>Document Introduction</h1>
    <p>This is the original introduction text.</p>
@endsection

@section('content')
    <h2>Main Content</h2>
    <p>{{ $main_content }}</p>
    
    <!-- This section will be overwritten -->
    <div class="temporary-content">
        <p>This content will be replaced.</p>
    </div>
@endsection

@section('conclusion')
    <h2>Original Conclusion</h2>
    <p>This is the original conclusion.</p>
@endsection

<!-- Overwrite the content section completely -->
@section('content')
    <h2>Completely New Content</h2>
    <p>{{ $main_content }}</p>
    
    <div class="enhanced-content">
        <h3>Enhanced Features</h3>
        @if($features)
            <ul>
                @foreach($features as $feature)
                    <li>{{ $feature }}</li>
                @endforeach
            </ul>
        @endif
    </div>
    
    <div class="statistics">
        <h3>Document Statistics</h3>
        <p>Word count: {{ $word_count }}</p>
        <p>Reading time: {{ $reading_time }} minutes</p>
    </div>
@overwrite

<!-- Append to the conclusion section -->
@section('conclusion')
    @parent
    
    <div class="additional-notes">
        <h3>Additional Notes</h3>
        <p>{{ $additional_notes }}</p>
        
        @if($references)
            <h4>References</h4>
            <ol>
                @foreach($references as $reference)
                    <li>{{ $reference }}</li>
                @endforeach
            </ol>
        @endif
    </div>
    
    <div class="document-footer">
        <p><em>Last updated: {{ $last_updated }}</em></p>
    </div>
@append
        """.strip()
        self.create_template(temp_dir, "document.blade.html", child_template)
        
        context = {
            "main_content": "This is the main body of our document with important information.",
            "features": [
                "Advanced formatting",
                "Cross-references",
                "Automatic table of contents",
                "Export to multiple formats"
            ],
            "word_count": 1250,
            "reading_time": 5,
            "additional_notes": "Please review the attached appendices for supplementary information.",
            "references": [
                "Smith, J. (2024). Template Engine Design Patterns",
                "Doe, A. (2023). Modern Web Development Practices",
                "Johnson, B. (2025). Blade Template Engine Guide"
            ],
            "last_updated": "January 15, 2025"
        }
        
        result = engine.render("document.blade.html", context)
        
        # Test that @overwrite replaced the content section
        assert "Completely New Content" in result
        assert "Enhanced Features" in result
        assert "Document Statistics" in result
        assert "Word count: 1250" in result
        assert "Reading time: 5 minutes" in result
        
        # Test that temporary content was overwritten
        assert "This content will be replaced." not in result
        assert "temporary-content" not in result
        
        # Test that @append added to conclusion
        assert "Original Conclusion" in result  # Parent content
        assert "Additional Notes" in result     # Appended content
        assert "Please review the attached appendices" in result
        
        # Test references list
        assert "Smith, J. (2024)" in result
        assert "Doe, A. (2023)" in result
        assert "Johnson, B. (2025)" in result
        
        # Test document footer
        assert "Last updated: January 15, 2025" in result
        
        # Test features list
        assert "Advanced formatting" in result
        assert "Cross-references" in result
        assert "Automatic table of contents" in result


class TestBladeComplexInheritanceScenarios:
    """Test complex inheritance scenarios and edge cases"""
    
    @pytest.fixture
    def blade_engine(self) -> Any:
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
    
    def test_conditional_sections(self, blade_engine: Any) -> None:
        """Test conditional section rendering"""
        engine, temp_dir = blade_engine
        
        # Layout with conditional sections
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
    
    @hasSection('critical_css')
        <style>
            /* Critical CSS */
            @yield('critical_css')
        </style>
    @endif
    
    @sectionMissing('external_css')
        <link rel="stylesheet" href="/css/default.css">
    @endsectionMissing
    
    @yield('external_css')
</head>
<body>
    @hasSection('header')
        <header>@yield('header')</header>
    @else
        <header><h1>Default Header</h1></header>
    @endif
    
    <main>
        @yield('content')
    </main>
    
    @hasSection('sidebar')
        <aside>@yield('sidebar')</aside>
    @endif
    
    @hasSection('modal')
        <div class="modal-backdrop">
            @yield('modal')
        </div>
    @endif
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/conditional.blade.html", layout_content)
        
        # Page with some sections defined
        page_with_sections = """
@extends('layouts/conditional')

@section('title', 'Page with Sections')

@section('critical_css')
    body { margin: 0; padding: 0; }
    .hero { background: #007acc; color: white; }
@endsection

@section('header')
    <div class="hero">
        <h1>{{ $page_title }}</h1>
        <p>{{ $page_subtitle }}</p>
    </div>
@endsection

@section('content')
    <div class="content">
        <h2>Main Content</h2>
        <p>{{ $content_text }}</p>
    </div>
@endsection

@section('sidebar')
    <div class="sidebar-widget">
        <h3>Related Links</h3>
        @if($related_links)
            <ul>
                @foreach($related_links as $link)
                    <li><a href="{{ $link.url }}">{{ $link.title }}</a></li>
                @endforeach
            </ul>
        @endif
    </div>
@endsection
        """.strip()
        self.create_template(temp_dir, "page-with-sections.blade.html", page_with_sections)
        
        # Page with minimal sections
        page_minimal = """
@extends('layouts/conditional')

@section('title', 'Minimal Page')

@section('external_css')
    <link rel="stylesheet" href="/css/custom.css">
@endsection

@section('content')
    <div class="simple-content">
        <h2>{{ $simple_title }}</h2>
        <p>{{ $simple_text }}</p>
    </div>
@endsection
        """.strip()
        self.create_template(temp_dir, "page-minimal.blade.html", page_minimal)
        
        # Test page with sections
        context1 = {
            "page_title": "Welcome to Our Site",
            "page_subtitle": "Discover amazing features",
            "content_text": "This page has custom header and sidebar.",
            "related_links": [
                {"url": "/about", "title": "About Us"},
                {"url": "/contact", "title": "Contact"}
            ]
        }
        
        result1 = engine.render("page-with-sections.blade.html", context1)
        
        # Should include custom sections
        assert "body { margin: 0; padding: 0; }" in result1  # Critical CSS
        assert "Welcome to Our Site" in result1              # Custom header
        assert "Discover amazing features" in result1
        assert "Related Links" in result1                    # Sidebar
        assert "About Us" in result1
        assert "Contact" in result1
        assert "Default Header" not in result1               # Custom header overrides default
        
        # Test minimal page
        context2 = {
            "simple_title": "Simple Page",
            "simple_text": "This is a simple page with minimal sections."
        }
        
        result2 = engine.render("page-minimal.blade.html", context2)
        
        # Should use defaults where sections missing
        assert "Default Header" in result2                   # No custom header defined
        assert "/css/custom.css" in result2                  # Custom external CSS
        assert "/css/default.css" not in result2             # External CSS provided, so default skipped
        assert "Simple Page" in result2
        assert "Related Links" not in result2               # No sidebar section


if __name__ == "__main__":
    pytest.main([__file__, "-v"])