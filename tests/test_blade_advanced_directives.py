"""
Test Suite for Advanced Blade Directives
Tests @includeWhen, @includeUnless, @each, @php, @macro, @lang, @choice, etc.
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine


class TestBladeAdvancedIncludeDirectives:
    """Test advanced include directives"""
    
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
    
    def test_include_when_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @includeWhen directive"""
        engine, temp_dir = blade_engine
        
        # Create partial to be included conditionally
        partial_content = "<div class='success-message'>{{ message }}</div>"
        self.create_template(temp_dir, "partials/success.blade.html", partial_content)
        
        # Main template with conditional includes
        main_content = """
<div class="page">
    <h1>{{ title }}</h1>
    
    @includeWhen($success, 'partials/success', ['message' => 'Operation completed!'])
    
    @includeWhen($show_nav, 'partials/navigation')
    
    <div class="content">{{ content }}</div>
</div>
        """.strip()
        self.create_template(temp_dir, "main.blade.html", main_content)
        
        context = {
            "title": "Test Page",
            "success": True,
            "show_nav": False,
            "content": "Main content here"
        }
        
        result = engine.render("main.blade.html", context)
        
        # Should include success partial when condition is true
        assert "Operation completed!" in result
        assert "Test Page" in result
        assert "Main content here" in result
    
    def test_include_unless_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @includeUnless directive"""
        engine, temp_dir = blade_engine
        
        # Create error partial
        error_content = "<div class='error'>{{ error_message }}</div>"
        self.create_template(temp_dir, "partials/error.blade.html", error_content)
        
        # Main template
        main_content = """
<div class="form">
    @includeUnless($validation_passed, 'partials/error', ['error_message' => 'Validation failed'])
    
    @includeUnless($user_authenticated, 'partials/login-prompt')
    
    <form>{{ form_content }}</form>
</div>
        """.strip()
        self.create_template(temp_dir, "form.blade.html", main_content)
        
        context = {
            "validation_passed": False,  # Should show error
            "user_authenticated": True,   # Should NOT show login prompt
            "form_content": "Form fields here"
        }
        
        result = engine.render("form.blade.html", context)
        
        # Should include error when validation failed
        assert "Validation failed" in result
        assert "Form fields here" in result
    
    def test_include_first_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @includeFirst directive"""
        engine, temp_dir = blade_engine
        
        # Create multiple templates (only some exist)
        second_choice = "<nav>Secondary Navigation</nav>"
        self.create_template(temp_dir, "partials/nav-secondary.blade.html", second_choice)
        
        third_choice = "<nav>Default Navigation</nav>"
        self.create_template(temp_dir, "partials/nav-default.blade.html", third_choice)
        
        # Main template with includeFirst
        main_content = """
<div class="layout">
    @includeFirst(['partials/nav-primary', 'partials/nav-secondary', 'partials/nav-default'])
    
    <main>{{ content }}</main>
</div>
        """.strip()
        self.create_template(temp_dir, "layout.blade.html", main_content)
        
        context = {"content": "Page content"}
        
        result = engine.render("layout.blade.html", context)
        
        # Should include the first template that exists (nav-secondary)
        assert "Secondary Navigation" in result
        assert "Page content" in result


class TestBladeEachDirective:
    """Test @each directive"""
    
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
    
    def test_each_directive_with_data(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @each directive with data"""
        engine, temp_dir = blade_engine
        
        # Create item template
        item_template = """
<div class="user-item">
    <h3>{{ user.name }}</h3>
    <p>{{ user.email }}</p>
    <small>Joined: {{ user.joined_at }}</small>
</div>
        """.strip()
        self.create_template(temp_dir, "partials/user-item.blade.html", item_template)
        
        # Create empty template
        empty_template = """
<div class="no-users">
    <p>No users found.</p>
    <a href="/invite">Invite some users</a>
</div>
        """.strip()
        self.create_template(temp_dir, "partials/no-users.blade.html", empty_template)
        
        # Main template using @each
        main_content = """
<div class="user-list">
    <h2>User Directory</h2>
    
    @each('partials/user-item', $users, 'user', 'partials/no-users')
</div>
        """.strip()
        self.create_template(temp_dir, "user-list.blade.html", main_content)
        
        context = {
            "users": [
                {"name": "Alice Johnson", "email": "alice@example.com", "joined_at": "2024-01-15"},
                {"name": "Bob Smith", "email": "bob@example.com", "joined_at": "2024-02-20"},
                {"name": "Carol Davis", "email": "carol@example.com", "joined_at": "2024-03-10"}
            ]
        }
        
        result = engine.render("user-list.blade.html", context)
        
        # Should render each user
        assert "Alice Johnson" in result
        assert "Bob Smith" in result
        assert "Carol Davis" in result
        assert "alice@example.com" in result
        assert "User Directory" in result
        
        # Should not show empty template
        assert "No users found" not in result
    
    def test_each_directive_empty_state(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @each directive with empty collection"""
        engine, temp_dir = blade_engine
        
        # Create templates
        item_template = "<div>{{ item.name }}</div>"
        empty_template = "<p>Nothing to display.</p>"
        
        self.create_template(temp_dir, "partials/item.blade.html", item_template)
        self.create_template(temp_dir, "partials/empty.blade.html", empty_template)
        
        main_content = """
<div class="items">
    @each('partials/item', $items, 'item', 'partials/empty')
</div>
        """.strip()
        self.create_template(temp_dir, "items.blade.html", main_content)
        
        context: Dict[str, List[Any]] = {"items": []}  # Empty collection
        
        result = engine.render("items.blade.html", context)
        
        # Should show empty template
        assert "Nothing to display." in result


class TestBladePHPAndMacros:
    """Test @php and @macro directives"""
    
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
    
    def test_php_blocks(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @php blocks"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="calculations">
    @php
        // This would be PHP code in Laravel
        $total = 0;
        foreach ($items as $item) {
            $total += $item['price'];
        }
        $tax = $total * 0.08;
        $grand_total = $total + $tax;
    @endphp
    
    <h3>Order Summary</h3>
    <p>Subtotal: {{ subtotal }}</p>
    <p>Tax: {{ tax }}</p>
    <p>Total: {{ total }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "order-summary.blade.html", template_content)
        
        context = {
            "subtotal": 100.00,
            "tax": 8.00, 
            "total": 108.00
        }
        
        result = engine.render("order-summary.blade.html", context)
        
        # PHP blocks should be processed (converted to no-op)
        # Values should come from context
        assert "Order Summary" in result
        assert "Subtotal: 100.0" in result
        assert "Tax: 8.0" in result
    
    def test_macro_definition_and_usage(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @macro definition and usage"""
        engine, temp_dir = blade_engine
        
        template_content = """
@macro('button')
    <button class="btn {{ $type ?? 'primary' }}" {{ $attributes ?? '' }}>
        {{ $text ?? 'Button' }}
    </button>
@endmacro

<div class="form">
    <h2>{{ title }}</h2>
    
    {{ button(['type' => 'success', 'text' => 'Save']) }}
    {{ button(['type' => 'danger', 'text' => 'Delete']) }}
    {{ button(['text' => 'Default Button']) }}
</div>
        """.strip()
        self.create_template(temp_dir, "macro-test.blade.html", template_content)
        
        context = {"title": "Macro Test Form"}
        
        result = engine.render("macro-test.blade.html", context)
        
        # Should define and use macros
        assert "Macro Test Form" in result
        # The macro system compiles to Jinja2 macros
        assert "btn" in result


class TestBladeLocalization:
    """Test @lang and @choice directives"""
    
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
    
    def test_lang_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @lang directive for translations"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="welcome">
    <h1>@lang('welcome.title')</h1>
    <p>@lang('welcome.message', ['name' => $user.name])</p>
    
    <nav>
        <a href="/home">@lang('nav.home')</a>
        <a href="/about">@lang('nav.about')</a>
        <a href="/contact">@lang('nav.contact')</a>
    </nav>
    
    <footer>
        @lang('footer.copyright', ['year' => $current_year])
    </footer>
</div>
        """.strip()
        self.create_template(temp_dir, "welcome.blade.html", template_content)
        
        context = {
            "user": {"name": "John Doe"},
            "current_year": 2025
        }
        
        result = engine.render("welcome.blade.html", context)
        
        # Language keys should be processed
        assert "welcome.title" in result
        assert "welcome.message" in result
        assert "nav.home" in result
    
    def test_choice_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @choice directive for pluralization"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="stats">
    <h2>Statistics</h2>
    
    <div class="stat-item">
        <span class="count">{{ post_count }}</span>
        <span class="label">@choice('messages.posts', $post_count)</span>
    </div>
    
    <div class="stat-item">
        <span class="count">{{ comment_count }}</span>
        <span class="label">@choice('messages.comments', $comment_count)</span>
    </div>
    
    <div class="stat-item">
        <span class="count">{{ user_count }}</span>
        <span class="label">@choice('messages.users', $user_count, ['min' => 1])</span>
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "stats.blade.html", template_content)
        
        context = {
            "post_count": 1,
            "comment_count": 15,
            "user_count": 42
        }
        
        result = engine.render("stats.blade.html", context)
        
        # Pluralization should be processed
        assert "Statistics" in result
        assert "messages.posts" in result
        assert "messages.comments" in result
        assert "messages.users" in result


class TestBladeSectionConditionals:
    """Test @hasSection and @sectionMissing directives"""
    
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
    
    def test_has_section_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @hasSection directive"""
        engine, temp_dir = blade_engine
        
        # Layout template
        layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Default Title')</title>
    
    @hasSection('custom_styles')
        <style>@yield('custom_styles')</style>
    @endhasSection
</head>
<body>
    @hasSection('header')
        <header>@yield('header')</header>
    @endhasSection
    
    <main>@yield('content')</main>
    
    @hasSection('sidebar')
        <aside>@yield('sidebar')</aside>
    @endhasSection
    
    @sectionMissing('footer')
        <footer>Default Footer Content</footer>
    @endsectionMissing
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "layout.blade.html", layout_content)
        
        # Page template with some sections
        page_content = """
@extends('layout')

@section('title', 'Page with Header')

@section('header')
    <h1>Custom Header</h1>
    <nav>Navigation here</nav>
@endsection

@section('content')
    <h2>Main Content</h2>
    <p>This page has a custom header but no sidebar.</p>
@endsection

@section('custom_styles')
    .custom-header { background: blue; }
@endsection
        """.strip()
        self.create_template(temp_dir, "page-with-header.blade.html", page_content)
        
        result = engine.render("page-with-header.blade.html")
        
        # Should include header (section exists)
        assert "Custom Header" in result
        assert "Navigation here" in result
        
        # Should include custom styles (section exists) 
        assert ".custom-header" in result
        
        # Should include default footer (section missing)
        assert "Default Footer Content" in result
        
        # Should not include sidebar (section missing, no @sectionMissing)
        assert "<aside>" not in result


class TestBladeComponentAdvanced:
    """Test advanced component features"""
    
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
    
    def test_component_first_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @componentFirst directive"""
        engine, temp_dir = blade_engine
        
        # Create second choice component (first doesn't exist)
        alert_secondary = """
<div class="alert-secondary alert-{{ type }}">
    {{ message }}
</div>
        """.strip()
        self.create_template(temp_dir, "components/alert-secondary.blade.html", alert_secondary)
        
        # Main template using componentFirst
        main_content = """
<div class="notifications">
    @componentFirst(['alert-primary', 'alert-secondary', 'alert-default'], [
        'type' => 'warning',
        'message' => 'This is a warning message'
    ])
</div>
        """.strip()
        self.create_template(temp_dir, "notifications.blade.html", main_content)
        
        result = engine.render("notifications.blade.html")
        
        # Should use the first component that exists (alert-secondary)
        assert "alert-secondary" in result
        assert "alert-warning" in result
        assert "This is a warning message" in result
    
    def test_aware_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @aware directive"""
        engine, temp_dir = blade_engine
        
        component_content = """
@aware(['theme', 'size'])

<div class="widget widget-{{ theme }} widget-{{ size }}">
    <h3>{{ title }}</h3>
    <div class="widget-body">
        {{ slot }}
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "components/widget.blade.html", component_content)
        
        main_content = """
<div class="dashboard" data-theme="{{ theme }}" data-size="{{ default_size }}">
    <x-widget title="Sales Data">
        <p>Revenue: {{ revenue }}</p>
    </x-widget>
    
    <x-widget title="User Stats">
        <p>Active Users: {{ active_users }}</p>
    </x-widget>
</div>
        """.strip()
        self.create_template(temp_dir, "dashboard.blade.html", main_content)
        
        context = {
            "theme": "dark",
            "default_size": "large",
            "revenue": "$50,000",
            "active_users": "1,234"
        }
        
        result = engine.render("dashboard.blade.html", context)
        
        # Should use aware variables in components
        assert "data-theme=\"dark\"" in result
        assert "data-size=\"large\"" in result
        assert "Sales Data" in result
        assert "$50,000" in result
    
    def test_attributes_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @attributes directive"""
        engine, temp_dir = blade_engine
        
        component_content = """
@props(['type' => 'button', 'variant' => 'primary'])

<button type="{{ type }}" 
        class="btn btn-{{ variant }}"
        @attributes>
    {{ slot }}
</button>
        """.strip()
        self.create_template(temp_dir, "components/button.blade.html", component_content)
        
        main_content = """
<form class="example-form">
    <x-button type="submit" variant="success" class="mr-2" id="submit-btn">
        Save Changes
    </x-button>
    
    <x-button variant="secondary" onclick="cancel()" data-confirm="true">
        Cancel
    </x-button>
</form>
        """.strip()
        self.create_template(temp_dir, "form-example.blade.html", main_content)
        
        result = engine.render("form-example.blade.html")
        
        # Should render button with all attributes
        assert "Save Changes" in result
        assert "Cancel" in result
        assert 'type="submit"' in result
        assert "btn-success" in result
        assert "btn-secondary" in result


class TestBladeAssetDirectives:
    """Test @vite, @livewireStyles, @livewireScripts"""
    
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
    
    def test_vite_directive(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @vite directive"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
    
    @vite('resources/css/admin.css')
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="app">{{ content }}</div>
    
    @vite('resources/js/dashboard.js')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "vite-example.blade.html", template_content)
        
        context = {
            "title": "Vite Integration Test",
            "content": "Application content here"
        }
        
        result = engine.render("vite-example.blade.html", context)
        
        # Should include Vite asset tags
        assert "Vite Integration Test" in result
        assert "/build/" in result  # Vite build directory
        assert "resources/css/app.css" in result
        assert "resources/js/app.js" in result
    
    def test_livewire_directives(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @livewireStyles and @livewireScripts"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Livewire App</title>
    <link href="/css/app.css" rel="stylesheet">
    @livewireStyles
</head>
<body>
    <div class="container">
        <h1>Livewire Components</h1>
        <div wire:loading>Loading...</div>
        
        {{ content }}
    </div>
    
    @livewireScripts
    <script src="/js/app.js"></script>
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "livewire-app.blade.html", template_content)
        
        context = {"content": "Livewire component content"}
        
        result = engine.render("livewire-app.blade.html", context)
        
        # Should include Livewire assets
        assert "Livewire App" in result
        assert "wire:loading" in result
        assert "livewire.js" in result
        assert "[wire\\:loading]" in result  # Livewire styles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])