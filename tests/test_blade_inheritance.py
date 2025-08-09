"""
Test Suite for Blade Template Inheritance
Tests @extends, @section, @yield, @parent, @overwrite, @append functionality
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine


class TestBladeTemplateInheritance:
    """Test template inheritance features"""
    
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
    
    def test_basic_inheritance(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test basic @extends and @section functionality"""
        # Create master layout
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Default Title')</title>
    <meta name="description" content="@yield('meta_description', 'Default description')">
</head>
<body>
    <header>
        @yield('header')
    </header>
    
    <nav>
        @section('navigation')
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/about">About</a></li>
            </ul>
        @show
    </nav>
    
    <main>
        @yield('content')
    </main>
    
    <aside>
        @yield('sidebar')
    </aside>
    
    <footer>
        @section('footer')
            <p>&copy; 2025 My Website</p>
        @show
    </footer>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", layout_content)
        
        # Create child template
        page_content = """
@extends('layouts/app')

@section('title', 'Home Page')

@section('meta_description', 'Welcome to our home page')

@section('header')
    <h1>Welcome to My Website</h1>
    <p>This is the header content</p>
@endsection

@section('content')
    <h2>Main Content</h2>
    <p>This is the main content of the page.</p>
    
    @include('partials/featured-posts')
@endsection

@section('sidebar')
    <h3>Sidebar</h3>
    <ul>
        <li>Recent Posts</li>
        <li>Categories</li>
        <li>Archives</li>
    </ul>
@endsection
        """.strip()
        self.create_template(temp_dir, "pages/home.blade.html", page_content)
        
        # Create partial template
        partial_content = """
<section class="featured">
    <h3>Featured Posts</h3>
    @foreach($featured_posts as $post)
        <article>
            <h4>{{ $post.title }}</h4>
            <p>{{ $post.excerpt }}</p>
        </article>
    @endforeach
</section>
        """.strip()
        self.create_template(temp_dir, "partials/featured-posts.blade.html", partial_content)
        
        # Test rendering
        context = {
            "featured_posts": [
                {"title": "First Post", "excerpt": "This is the first post"},
                {"title": "Second Post", "excerpt": "This is the second post"}
            ]
        }
        
        result = blade_engine.render("pages/home.blade.html", context)
        
        # Check that layout structure is present
        assert "<title>Home Page</title>" in result
        assert "Welcome to My Website" in result
        assert "Main Content" in result
        assert "Sidebar" in result
        assert "&copy; 2025 My Website" in result
        
        # Check that partial content is included
        assert "Featured Posts" in result
        assert "First Post" in result
        assert "Second Post" in result
    
    def test_section_overriding(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test section overriding and @parent functionality"""
        # Create base layout
        base_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
</head>
<body>
    <div class="container">
        @section('content')
            <p>Default content from base template</p>
        @show
    </div>
    
    <div class="scripts">
        @section('scripts')
            <script src="base.js"></script>
        @show
    </div>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/base.blade.html", base_content)
        
        # Create child template that uses @parent
        child_content = """
@extends('layouts/base')

@section('title', 'Child Page')

@section('content')
    @parent
    <p>Additional content from child template</p>
@endsection

@section('scripts')
    @parent
    <script src="child.js"></script>
@endsection
        """.strip()
        self.create_template(temp_dir, "pages/child.blade.html", child_content)
        
        result = blade_engine.render("pages/child.blade.html")
        
        # Check that parent content is included
        assert "Default content from base template" in result
        assert "Additional content from child template" in result
        assert "base.js" in result
        assert "child.js" in result
    
    def test_section_append_overwrite(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test @append and @overwrite functionality"""
        # Create layout with sections
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    @section('styles')
        <link href="app.css" rel="stylesheet">
    @show
</head>
<body>
    @section('content')
        <p>Base content</p>
    @show
    
    @section('scripts')
        <script src="app.js"></script>
    @show
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/master.blade.html", layout_content)
        
        # Child template with append and overwrite
        child_content = """
@extends('layouts/master')

@section('styles')
    @parent
    <link href="custom.css" rel="stylesheet">
@append

@section('content')
    <h1>New Content</h1>
    <p>This completely replaces the base content</p>
@overwrite

@section('scripts')
    @parent
    <script src="custom.js"></script>
@append
        """.strip()
        self.create_template(temp_dir, "pages/custom.blade.html", child_content)
        
        result = blade_engine.render("pages/custom.blade.html")
        
        # Appended sections should have both parent and child content
        assert "app.css" in result
        assert "custom.css" in result
        assert "app.js" in result
        assert "custom.js" in result
        
        # Overwritten section should only have child content
        assert "New Content" in result
        assert "Base content" not in result  # Should be completely replaced
    
    def test_nested_inheritance(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test multiple levels of template inheritance"""
        # Master template
        master_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
    @section('meta')
        <meta charset="UTF-8">
    @show
</head>
<body>
    @yield('body')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/master.blade.html", master_content)
        
        # App layout (extends master)
        app_content = """
@extends('layouts/master')

@section('meta')
    @parent
    <meta name="viewport" content="width=device-width, initial-scale=1">
@append

@section('body')
    <div class="app">
        <header>@yield('header')</header>
        <main>@yield('content')</main>
        <footer>@yield('footer')</footer>
    </div>
@endsection
        """.strip()
        self.create_template(temp_dir, "layouts/app.blade.html", app_content)
        
        # Page template (extends app)
        page_content = """
@extends('layouts/app')

@section('title', 'Nested Page')

@section('header')
    <h1>Page Header</h1>
@endsection

@section('content')
    <p>Page content goes here</p>
@endsection

@section('footer')
    <p>Page footer</p>
@endsection
        """.strip()
        self.create_template(temp_dir, "pages/nested.blade.html", page_content)
        
        result = blade_engine.render("pages/nested.blade.html")
        
        # Check all levels are rendered correctly
        assert "<title>Nested Page</title>" in result
        assert "charset=UTF-8" in result
        assert "viewport" in result
        assert "Page Header" in result
        assert "Page content goes here" in result
        assert "Page footer" in result
        assert '<div class="app">' in result
    
    def test_conditional_sections(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test conditional section rendering"""
        layout_content = """
<!DOCTYPE html>
<html>
<body>
    @hasSection('header')
        <header>@yield('header')</header>
    @endif
    
    <main>@yield('content')</main>
    
    @hasSection('sidebar')
        <aside>@yield('sidebar')</aside>
    @endif
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/conditional.blade.html", layout_content)
        
        # Page with header but no sidebar
        page_content = """
@extends('layouts/conditional')

@section('header')
    <h1>Page with header</h1>
@endsection

@section('content')
    <p>Main content</p>
@endsection
        """.strip()
        self.create_template(temp_dir, "pages/with-header.blade.html", page_content)
        
        result = blade_engine.render("pages/with-header.blade.html")
        
        # Should have header but not sidebar
        assert "<header>" in result
        assert "Page with header" in result
        assert "Main content" in result
        # Should not have sidebar since no @hasSection('sidebar') content
        
    def test_section_with_default_content(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test sections with default content and yielding"""
        layout_content = """
<html>
<head>
    <title>@yield('title', 'Default Site Title')</title>
</head>
<body>
    @section('navigation')
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
    @show
    
    @yield('content')
    
    @section('footer')
        <footer>&copy; 2025 Default Footer</footer>
    @show
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layouts/defaults.blade.html", layout_content)
        
        # Child template that doesn't override navigation or footer
        child_content = """
@extends('layouts/defaults')

@section('content')
    <main>Just the main content, using default nav and footer</main>
@endsection
        """.strip()
        self.create_template(temp_dir, "pages/minimal.blade.html", child_content)
        
        result = blade_engine.render("pages/minimal.blade.html")
        
        # Should have default title, navigation, and footer
        assert "Default Site Title" in result
        assert "<nav>" in result
        assert "Home</a>" in result
        assert "About</a>" in result
        assert "Just the main content" in result
        assert "Default Footer" in result


class TestBladeYieldSectionEdgeCases:
    """Test edge cases and complex scenarios for yield/section"""
    
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
    
    def test_inline_sections(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test inline section definitions"""
        engine, temp_dir = blade_engine
        
        layout_content = """
<html>
<head><title>@yield('title')</title></head>
<body>@yield('content')</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layout.blade.html", layout_content)
        
        page_content = """
@extends('layout')

@section('title', 'Inline Title')

@section('content', '<p>Inline content</p>')
        """.strip()
        self.create_template(temp_dir, "inline.blade.html", page_content)
        
        result = engine.render("inline.blade.html")
        assert "Inline Title" in result
        assert "Inline content" in result
    
    def test_empty_sections(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test behavior with empty sections"""
        engine, temp_dir = blade_engine
        
        layout_content = """
<div class="header">@yield('header', 'Default Header')</div>
<div class="content">@yield('content')</div>
<div class="footer">@yield('footer')</div>
        """.strip()
        self.create_template(temp_dir, "layout.blade.html", layout_content)
        
        page_content = """
@extends('layout')

@section('header')
@endsection

@section('content')
    <p>Only content, empty header and footer</p>
@endsection
        """.strip()
        self.create_template(temp_dir, "empty-sections.blade.html", page_content)
        
        result = engine.render("empty-sections.blade.html")
        assert "Only content" in result
        # Empty section should override default
        assert "Default Header" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])