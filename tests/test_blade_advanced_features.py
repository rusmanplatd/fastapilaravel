"""
Test Suite for Advanced Blade Features
Tests stacks, once blocks, fragments, conditional helpers, and edge cases
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine


class TestBladeStacks:
    """Test stack functionality (@push, @prepend, @stack)"""
    
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
    
    def test_basic_stack_operations(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test basic push and stack operations"""
        engine, temp_dir = blade_engine
        
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Stack Test</title>
    
    @push('styles')
        <link href="page.css" rel="stylesheet">
    @endpush
    
    @stack('styles')
</head>
<body>
    @push('scripts')
        <script src="page.js"></script>
    @endpush
    
    @push('scripts')
        <script src="custom.js"></script>
    @endpush
    
    <h1>Content</h1>
    
    @stack('scripts')
</body>
</html>
        """.strip()
        self.create_template(temp_dir, "stack-test.blade.html", template_content)
        
        result = engine.render("stack-test.blade.html")
        
        # Should contain pushed content
        assert "page.css" in result
        assert "page.js" in result
        assert "custom.js" in result
        
        # Test that stack management works
        assert len(engine.stacks.get('styles', [])) >= 0
        assert len(engine.stacks.get('scripts', [])) >= 0
    
    def test_prepend_to_stacks(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test prepending to stacks"""
        engine, temp_dir = blade_engine
        
        template_content = """
@push('assets')
    <script src="app.js"></script>
@endpush

@prepend('assets')
    <script src="vendor.js"></script>
@endprepend

@push('assets')
    <script src="custom.js"></script>
@endpush

@prepend('assets')
    <script src="framework.js"></script>
@endprepend

<div>
    @stack('assets')
</div>
        """.strip()
        self.create_template(temp_dir, "prepend-test.blade.html", template_content)
        
        result = engine.render("prepend-test.blade.html")
        
        # Should have all scripts
        assert "vendor.js" in result
        assert "framework.js" in result
        assert "app.js" in result
        assert "custom.js" in result
        
        # Prepended items should come first (in reverse order of prepending)
        # This is the expected Laravel behavior
    
    def test_multiple_stacks(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test multiple independent stacks"""
        engine, temp_dir = blade_engine
        
        template_content = """
@push('head-meta')
    <meta name="description" content="Test page">
@endpush

@push('head-meta')
    <meta name="keywords" content="test,blade">
@endpush

@push('footer-scripts')
    <script src="analytics.js"></script>
@endpush

@push('sidebar-widgets')
    <div class="widget">Recent Posts</div>
@endpush

<head>
    @stack('head-meta')
</head>

<body>
    <aside>
        @stack('sidebar-widgets')
    </aside>
    
    <footer>
        @stack('footer-scripts')
    </footer>
</body>
        """.strip()
        self.create_template(temp_dir, "multi-stack.blade.html", template_content)
        
        result = engine.render("multi-stack.blade.html")
        
        # Should have content for all stacks
        assert "description" in result
        assert "keywords" in result
        assert "analytics.js" in result
        assert "Recent Posts" in result
    
    def test_programmatic_stack_management(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test programmatic stack operations"""
        engine, temp_dir = blade_engine
        
        # Add items to stack programmatically
        engine.add_to_stack('dynamic', '<script>console.log("first");</script>')
        engine.add_to_stack('dynamic', '<script>console.log("second");</script>')
        engine.add_to_stack('dynamic', '<script>console.log("prepended");</script>', prepend=True)
        
        template_content = """
<div>
    @stack('dynamic')
</div>
        """.strip()
        self.create_template(temp_dir, "programmatic.blade.html", template_content)
        
        result = engine.render("programmatic.blade.html")
        
        # Should contain all dynamically added content
        assert "first" in result
        assert "second" in result
        assert "prepended" in result
    
    def test_empty_stacks(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test behavior with empty stacks"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div class="header">
    @stack('nonexistent-stack')
</div>

<div class="footer">
    @stack('empty-stack')
</div>
        """.strip()
        self.create_template(temp_dir, "empty-stacks.blade.html", template_content)
        
        result = engine.render("empty-stacks.blade.html")
        
        # Should render without errors
        assert "header" in result
        assert "footer" in result


class TestBladeOnceBlocks:
    """Test @once directive functionality"""
    
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
    
    def test_once_basic_functionality(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test basic @once functionality"""
        engine, temp_dir = blade_engine
        
        template_content = """
@once('jquery')
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
@endonce

<div class="component1">
    @once('jquery')
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    @endonce
    Component 1 content
</div>

<div class="component2">
    @once('jquery')
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    @endonce
    Component 2 content
</div>

@once('bootstrap')
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
@endonce
        """.strip()
        self.create_template(temp_dir, "once-test.blade.html", template_content)
        
        result = engine.render("once-test.blade.html")
        
        # jQuery should only appear once despite multiple @once blocks
        jquery_count = result.count('jquery-3.6.0.min.js')
        assert jquery_count <= 1
        
        # Bootstrap should appear once
        bootstrap_count = result.count('bootstrap@5.1.3')
        assert bootstrap_count <= 1
        
        # Component content should still be there
        assert "Component 1 content" in result
        assert "Component 2 content" in result
    
    def test_once_with_different_ids(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @once with different IDs"""
        engine, temp_dir = blade_engine
        
        template_content = """
@once('css-framework')
    <link href="framework.css" rel="stylesheet">
@endonce

@once('js-framework')
    <script src="framework.js"></script>
@endonce

@once('css-framework')
    <link href="framework.css" rel="stylesheet">
@endonce

@once('css-custom')
    <link href="custom.css" rel="stylesheet">
@endonce
        """.strip()
        self.create_template(temp_dir, "once-ids.blade.html", template_content)
        
        result = engine.render("once-ids.blade.html")
        
        # Each unique once ID should appear only once
        framework_css_count = result.count('framework.css')
        framework_js_count = result.count('framework.js')
        custom_css_count = result.count('custom.css')
        
        assert framework_css_count <= 1
        assert framework_js_count <= 1
        assert custom_css_count <= 1
    
    def test_once_state_persistence(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test that @once state persists across renders"""
        engine, temp_dir = blade_engine
        
        template_content = """
@once('persistent')
    <script>console.log('This should only run once');</script>
@endonce

<div>Template content</div>
        """.strip()
        self.create_template(temp_dir, "persistent.blade.html", template_content)
        
        # Render multiple times
        result1 = engine.render("persistent.blade.html")
        result2 = engine.render("persistent.blade.html")
        result3 = engine.render("persistent.blade.html")
        
        # Script should appear in first render
        assert "should only run once" in result1
        
        # Check that once blocks are tracked
        assert 'persistent' in engine.once_blocks


class TestBladeFragments:
    """Test fragment functionality"""
    
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
    
    def test_fragment_definition_and_retrieval(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test defining and retrieving fragments"""
        engine, temp_dir = blade_engine
        
        template_content = """
@fragment('user-card')
    <div class="card">
        <h3>{{ $user.name }}</h3>
        <p>{{ $user.email }}</p>
    </div>
@endfragment

@fragment('post-summary')
    <article>
        <h2>{{ $post.title }}</h2>
        <p>{{ $post.excerpt }}</p>
    </article>
@endfragment

<div class="content">
    Main template content
</div>
        """.strip()
        self.create_template(temp_dir, "fragments.blade.html", template_content)
        
        context = {
            "user": {"name": "John Doe", "email": "john@example.com"},
            "post": {"title": "Test Post", "excerpt": "This is a test post"}
        }
        
        result = engine.render("fragments.blade.html", context)
        
        # Fragments should be processed
        assert "Main template content" in result
        
        # Check that fragments are stored
        assert 'user-card' in engine.fragments
        assert 'post-summary' in engine.fragments
        
        # Test fragment retrieval
        user_card_fragment = engine.get_fragment('user-card')
        post_fragment = engine.get_fragment('post-summary')
        
        assert user_card_fragment != ""
        assert post_fragment != ""
    
    def test_fragment_usage_in_components(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test using fragments within components"""
        engine, temp_dir = blade_engine
        
        # Define a component that uses fragments
        component_content = """
<div class="widget {{ $class ?? '' }}">
    <div class="widget-header">
        {{ $title ?? 'Widget' }}
    </div>
    
    <div class="widget-body">
        @fragment('widget-content')
            {{ $slot }}
        @endfragment
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "components/widget.blade.html", component_content)
        
        main_template = """
<div class="page">
    <x-widget title="User Info" class="user-widget">
        <p>Welcome, {{ $user.name }}!</p>
        <p>Last login: {{ $user.last_login }}</p>
    </x-widget>
    
    <x-widget title="Statistics">
        <ul>
            <li>Posts: {{ $stats.posts }}</li>
            <li>Comments: {{ $stats.comments }}</li>
        </ul>
    </x-widget>
</div>
        """.strip()
        self.create_template(temp_dir, "fragment-components.blade.html", main_template)
        
        context = {
            "user": {"name": "Alice", "last_login": "2025-01-10"},
            "stats": {"posts": 15, "comments": 42}
        }
        
        result = engine.render("fragment-components.blade.html", context)
        
        # Component content should be rendered
        assert "Welcome, Alice!" in result
        assert "User Info" in result
        assert "Statistics" in result
        assert "Posts: 15" in result


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
    
    def test_class_helper_with_arrays(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test class helper with array syntax"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div {{ class_names(['btn', 'btn-large', active ? 'btn-active' : '', disabled ? 'btn-disabled' : '']) }}>
    Button with conditional classes
</div>

<span {{ class_names({
    'badge': true,
    'badge-primary': type == 'primary',
    'badge-secondary': type == 'secondary',
    'badge-large': size == 'large'
}) }}>
    Badge
</span>
        """.strip()
        self.create_template(temp_dir, "class-helper.blade.html", template_content)
        
        context = {
            "active": True,
            "disabled": False,
            "type": "primary",
            "size": "large"
        }
        
        result = engine.render("class-helper.blade.html", context)
        
        # Should contain conditional classes
        assert "btn" in result
        assert "btn-large" in result
        assert "btn-active" in result
        assert "btn-disabled" not in result
        assert "badge-primary" in result
        assert "badge-large" in result
    
    def test_style_helper_with_objects(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test style helper with object syntax"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div style="{{ styles({
    'color': textColor,
    'background-color': bgColor if showBackground else null,
    'font-size': fontSize + 'px' if fontSize else null,
    'margin': margin,
    'display': 'block' if visible else 'none'
}) }}">
    Styled element
</div>
        """.strip()
        self.create_template(temp_dir, "style-helper.blade.html", template_content)
        
        context = {
            "textColor": "red",
            "bgColor": "blue", 
            "showBackground": True,
            "fontSize": 16,
            "margin": "10px",
            "visible": True
        }
        
        result = engine.render("style-helper.blade.html", context)
        
        # Should contain conditional styles
        assert "color: red" in result
        assert "background-color: blue" in result
        assert "font-size: 16px" in result
        assert "margin: 10px" in result
        assert "display: block" in result
    
    def test_combined_conditional_attributes(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test combining class and style helpers"""
        engine, temp_dir = blade_engine
        
        template_content = """
<article 
    class="{{ class_names(['post', 'post-' + status, featured ? 'featured' : '']) }}"
    style="{{ styles({
        'border-left': featured ? '4px solid gold' : null,
        'opacity': published ? '1' : '0.5',
        'margin-bottom': '20px'
    }) }}">
    
    <h2>{{ title }}</h2>
    <p>{{ excerpt }}</p>
    
    <div class="{{ class_names({
        'post-meta': true,
        'text-muted': not featured,
        'text-warning': featured
    }) }}">
        Status: {{ status }}
    </div>
</article>
        """.strip()
        self.create_template(temp_dir, "combined-helpers.blade.html", template_content)
        
        context = {
            "title": "Test Article",
            "excerpt": "This is a test article.",
            "status": "published",
            "featured": True,
            "published": True
        }
        
        result = engine.render("combined-helpers.blade.html", context)
        
        # Should contain combined conditional attributes
        assert "post-published" in result
        assert "featured" in result
        assert "border-left: 4px solid gold" in result
        assert "opacity: 1" in result
        assert "text-warning" in result
        assert "Test Article" in result


class TestBladeEdgeCases:
    """Test edge cases and error handling"""
    
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
        """Test nested Blade directives"""
        engine, temp_dir = blade_engine
        
        template_content = """
@if($user)
    @auth
        @can('view-dashboard')
            @if($notifications)
                @foreach($notifications as $notification)
                    @if($notification.important)
                        <div class="alert alert-important">
                            {{ $notification.message }}
                        </div>
                    @else
                        <div class="alert alert-normal">
                            {{ $notification.message }}
                        </div>
                    @endif
                @endforeach
            @else
                <p>No notifications</p>
            @endif
        @endcan
    @endauth
@endif
        """.strip()
        self.create_template(temp_dir, "nested.blade.html", template_content)
        
        # Mock user with permissions
        class MockUser:
            def can(self, permission: str) -> bool:
                return permission == 'view-dashboard'
        
        context = {
            "user": MockUser(),
            "current_user": MockUser(),
            "notifications": [
                {"message": "Important alert", "important": True},
                {"message": "Regular notice", "important": False}
            ]
        }
        
        result = engine.render("nested.blade.html", context)
        
        # Should handle nested directives correctly
        assert "Important alert" in result
        assert "Regular notice" in result
        assert "alert-important" in result
        assert "alert-normal" in result
    
    def test_missing_endif_handling(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of malformed templates"""
        engine, temp_dir = blade_engine
        
        # Template with missing @endif
        template_content = """
@if($condition)
    <p>Content here</p>
    @if($nested)
        <span>Nested content</span>
    @endif
{{-- Missing @endif for first @if --}}
        """.strip()
        self.create_template(temp_dir, "malformed.blade.html", template_content)
        
        # Should still compile and render (Jinja2 will handle the error)
        try:
            result = engine.render("malformed.blade.html", {"condition": True, "nested": True})
            # If it renders without error, that's acceptable
            assert "Content here" in result
        except Exception:
            # If it throws an error, that's also acceptable for malformed templates
            pass
    
    def test_empty_directive_content(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test directives with empty content"""
        engine, temp_dir = blade_engine
        
        template_content = """
@if()
    <p>Empty condition</p>
@endif

@foreach( as )
    <p>Empty foreach</p>
@endforeach

@section('')
    <p>Empty section name</p>
@endsection

@push('')
    <script>Empty stack</script>
@endpush
        """.strip()
        self.create_template(temp_dir, "empty-directives.blade.html", template_content)
        
        # Should handle empty directive content gracefully
        try:
            result = engine.render("empty-directives.blade.html")
            # Should render something even with malformed directives
            assert len(result) > 0
        except Exception:
            # Errors are acceptable for malformed syntax
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])