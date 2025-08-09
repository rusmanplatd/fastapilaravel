"""
Test Suite for Blade Component System
Tests <x-component>, @slot, @props, component compilation and rendering
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
import os

from app.View.BladeEngine import BladeEngine
from app.View.BladeComponent import BladeComponent, ComponentRegistry


class TestBladeComponents:
    """Test Blade component functionality"""
    
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
    
    def test_anonymous_component_basic(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test basic anonymous component rendering"""
        # Create component template
        alert_component = """
<div class="alert alert-{{ $type ?? 'info' }} {{ $class ?? '' }}" 
     @if($id ?? false) id="{{ $id }}" @endif>
    @if($title ?? false)
        <h4 class="alert-title">{{ $title }}</h4>
    @endif
    
    <div class="alert-content">
        {{ $slot }}
    </div>
    
    @if($dismissible ?? false)
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "components/alert.blade.html", alert_component)
        
        # Use component in main template
        main_template = """
<div class="page">
    <x-alert type="success" title="Success!" dismissible="true">
        Your action was completed successfully!
    </x-alert>
    
    <x-alert type="danger">
        <strong>Error!</strong> Something went wrong.
    </x-alert>
    
    <x-alert class="mb-3" id="info-alert">
        This is an informational message.
    </x-alert>
</div>
        """.strip()
        self.create_template(temp_dir, "main.blade.html", main_template)
        
        result = blade_engine.render("main.blade.html")
        
        # Should contain component markup
        assert 'alert-success' in result
        assert 'Success!' in result
        assert 'completed successfully!' in result
        assert 'data-dismiss="alert"' in result
        
        assert 'alert-danger' in result
        assert 'Something went wrong' in result
        
        assert 'alert-info' in result  # default type
        assert 'id="info-alert"' in result
        assert 'mb-3' in result
    
    def test_component_with_slots(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test components with named slots"""
        # Create card component with multiple slots
        card_component = """
<div class="card {{ $class ?? '' }}">
    @if($header ?? false)
        <div class="card-header">
            {{ $header }}
        </div>
    @endif
    
    <div class="card-body">
        {{ $slot }}
        
        @if($actions ?? false)
            <div class="card-actions">
                {{ $actions }}
            </div>
        @endif
    </div>
    
    @if($footer ?? false)
        <div class="card-footer">
            {{ $footer }}
        </div>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "components/card.blade.html", card_component)
        
        # Use component with slots
        main_template = """
<x-card class="user-card">
    <x-slot name="header">
        <h3>User Profile</h3>
        <span class="badge">Premium</span>
    </x-slot>
    
    <div class="user-info">
        <h4>{{ $user.name }}</h4>
        <p>{{ $user.email }}</p>
        <p>Member since: {{ $user.created_at }}</p>
    </div>
    
    <x-slot name="actions">
        <button class="btn btn-primary">Edit Profile</button>
        <button class="btn btn-secondary">View Activity</button>
    </x-slot>
    
    <x-slot name="footer">
        <small class="text-muted">Last updated: {{ $user.updated_at }}</small>
    </x-slot>
</x-card>
        """.strip()
        self.create_template(temp_dir, "profile.blade.html", main_template)
        
        context = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com",
                "created_at": "2020-01-01",
                "updated_at": "2025-01-01"
            }
        }
        
        result = blade_engine.render("profile.blade.html", context)
        
        # Should contain all slot content
        assert "User Profile" in result
        assert "Premium" in result
        assert "John Doe" in result
        assert "john@example.com" in result
        assert "Edit Profile" in result
        assert "View Activity" in result
        assert "Last updated" in result
    
    def test_nested_components(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test nested component usage"""
        # Create button component
        button_component = """
<button type="{{ $type ?? 'button' }}" 
        class="btn btn-{{ $variant ?? 'primary' }} {{ $class ?? '' }}"
        @if($disabled ?? false) disabled @endif
        @if($onclick ?? false) onclick="{{ $onclick }}" @endif>
    {{ $slot }}
</button>
        """.strip()
        self.create_template(temp_dir, "components/button.blade.html", button_component)
        
        # Create form component that uses button
        form_component = """
<form method="{{ $method ?? 'POST' }}" action="{{ $action ?? '' }}" class="{{ $class ?? '' }}">
    @csrf
    
    <div class="form-content">
        {{ $slot }}
    </div>
    
    <div class="form-actions">
        @if($submit ?? true)
            <x-button type="submit" variant="primary">
                {{ $submitText ?? 'Submit' }}
            </x-button>
        @endif
        
        @if($cancel ?? false)
            <x-button variant="secondary" onclick="history.back()">
                Cancel
            </x-button>
        @endif
    </div>
</form>
        """.strip()
        self.create_template(temp_dir, "components/form.blade.html", form_component)
        
        # Use nested components
        main_template = """
<div class="container">
    <h1>Create New Post</h1>
    
    <x-form action="/posts" class="post-form" submit-text="Create Post" cancel="true">
        <div class="form-group">
            <label for="title">Title:</label>
            <input type="text" id="title" name="title" class="form-control">
        </div>
        
        <div class="form-group">
            <label for="content">Content:</label>
            <textarea id="content" name="content" class="form-control"></textarea>
        </div>
    </x-form>
</div>
        """.strip()
        self.create_template(temp_dir, "create-post.blade.html", main_template)
        
        result = blade_engine.render("create-post.blade.html")
        
        # Should contain nested component structure
        assert "Create New Post" in result
        assert 'method="POST"' in result
        assert 'action="/posts"' in result
        assert 'class="post-form"' in result
        assert "Create Post" in result  # Submit button text
        assert "Cancel" in result       # Cancel button
        assert "history.back()" in result
    
    def test_component_with_props(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test components with @props directive"""
        # Create component with props validation
        user_avatar_component = """
@props(['user', 'size' => 'md', 'rounded' => true, 'showStatus' => false])

@php
    $sizeClasses = [
        'sm' => 'w-8 h-8',
        'md' => 'w-12 h-12',
        'lg' => 'w-16 h-16',
        'xl' => 'w-24 h-24'
    ];
    $avatarClass = $sizeClasses[$size] ?? $sizeClasses['md'];
    $avatarClass .= $rounded ? ' rounded-full' : ' rounded';
@endphp

<div class="relative inline-block">
    <img src="{{ $user['avatar'] ?? '/default-avatar.png' }}" 
         alt="{{ $user['name'] ?? 'User' }}"
         class="object-cover {{ $avatarClass }} {{ $class ?? '' }}">
    
    @if($showStatus && isset($user['online']))
        <span class="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white
                     {{ $user['online'] ? 'bg-green-500' : 'bg-gray-400' }}"></span>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "components/user-avatar.blade.html", user_avatar_component)
        
        # Use component with different props
        main_template = """
<div class="user-list">
    <div class="user-item">
        <x-user-avatar :user="$admin" size="lg" show-status="true" />
        <span>{{ $admin.name }} (Admin)</span>
    </div>
    
    <div class="user-item">
        <x-user-avatar :user="$moderator" size="md" :rounded="false" />
        <span>{{ $moderator.name }} (Moderator)</span>
    </div>
    
    <div class="user-item">
        <x-user-avatar :user="$user" size="sm" />
        <span>{{ $user.name }}</span>
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "users.blade.html", main_template)
        
        context = {
            "admin": {
                "name": "Admin User",
                "avatar": "/admin-avatar.jpg",
                "online": True
            },
            "moderator": {
                "name": "Mod User", 
                "avatar": "/mod-avatar.jpg",
                "online": False
            },
            "user": {
                "name": "Regular User"
                # No avatar - should use default
            }
        }
        
        result = blade_engine.render("users.blade.html", context)
        
        # Should contain different avatar sizes and styles
        assert "Admin User" in result
        assert "Mod User" in result
        assert "Regular User" in result
        assert "/admin-avatar.jpg" in result
        assert "/default-avatar.png" in result  # Default for regular user
        assert "w-24 h-24" in result  # lg size
        assert "w-12 h-12" in result  # md size
        assert "w-8 h-8" in result    # sm size
    
    def test_class_based_components(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test class-based components"""
        # Register a class-based component
        class AlertComponent(BladeComponent):
            def __init__(self, **attributes: Any) -> None:
                super().__init__(**attributes)
                self.type = attributes.get('type', 'info')
                self.dismissible = attributes.get('dismissible', False)
                self.title = attributes.get('title', None)
            
            def render(self) -> str:
                classes = f"alert alert-{self.type}"
                if self.attributes.get('class'):
                    classes += f" {self.attributes['class']}"
                
                html = f'<div class="{classes}"'
                if self.attributes.get('id'):
                    html += f' id="{self.attributes["id"]}"'
                html += '>'
                
                if self.title:
                    html += f'<h4 class="alert-title">{self.title}</h4>'
                
                html += f'<div class="alert-content">{self.slots.get_slot("default").content}</div>'
                
                if self.dismissible:
                    html += '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>'
                
                html += '</div>'
                return html
        
        # Register the component
        blade_engine.register_component('class-alert', AlertComponent)
        
        # Use the class-based component
        main_template = """
<x-class-alert type="warning" title="Warning" dismissible="true" class="mb-4">
    This is a warning message from a class-based component.
</x-class-alert>
        """.strip()
        self.create_template(temp_dir, "class-component.blade.html", main_template)
        
        result = blade_engine.render("class-component.blade.html")
        
        # Should contain class-based component output
        assert "alert-warning" in result
        assert "Warning" in result
        assert "class-based component" in result
        assert "data-dismiss" in result
    
    def test_component_attributes_and_merge(self, blade_engine: BladeEngine, temp_dir: str) -> None:
        """Test component attribute handling and merging"""
        # Create input component that merges attributes
        input_component = """
@props(['name', 'type' => 'text', 'label' => null, 'required' => false])

<div class="form-group {{ $errors->has($name) ? 'has-error' : '' }}">
    @if($label)
        <label for="{{ $name }}" class="form-label">
            {{ $label }}
            @if($required) <span class="text-danger">*</span> @endif
        </label>
    @endif
    
    <input type="{{ $type }}" 
           name="{{ $name }}" 
           id="{{ $name }}"
           value="{{ old($name) }}"
           {{ $attributes->merge(['class' => 'form-control']) }}
           @if($required) required @endif>
    
    @error($name)
        <div class="form-error text-danger">{{ $message }}</div>
    @enderror
</div>
        """.strip()
        self.create_template(temp_dir, "components/form-input.blade.html", input_component)
        
        # Use component with merged attributes
        main_template = """
<form>
    <x-form-input name="email" 
                  type="email" 
                  label="Email Address" 
                  required="true"
                  class="form-control-lg"
                  placeholder="Enter your email" />
    
    <x-form-input name="password" 
                  type="password" 
                  label="Password"
                  required="true"
                  autocomplete="current-password" />
    
    <x-form-input name="bio" 
                  label="Bio (Optional)"
                  class="custom-textarea" />
</form>
        """.strip()
        self.create_template(temp_dir, "form.blade.html", main_template)
        
        result = blade_engine.render("form.blade.html")
        
        # Should merge classes and attributes properly
        assert 'type="email"' in result
        assert 'name="email"' in result
        assert "Email Address" in result
        assert "required" in result
        assert "form-control-lg" in result  # Merged class
        assert "form-control" in result     # Base class
        assert 'placeholder="Enter your email"' in result


class TestComponentRegistry:
    """Test component registration and management"""
    
    def test_component_registration(self) -> None:
        """Test registering different types of components"""
        registry = ComponentRegistry()
        
        # Register class-based component
        class TestComponent(BladeComponent):
            def render(self) -> str:
                return f"<div>Test: {self.attributes.get('message', '')}</div>"
        
        registry.register('test', TestComponent)
        
        # Register template-based component
        registry.register('template-comp', 'components/template.blade.html')
        
        # Register with alias
        registry.register('button', TestComponent, alias='btn')
        
        # Test retrieval
        assert registry.get('test') == TestComponent
        assert registry.get('template-comp') == 'components/template.blade.html'
        assert registry.get('btn') == TestComponent
        assert registry.has('test') is True
        assert registry.has('nonexistent') is False
    
    def test_component_namespaces(self) -> None:
        """Test component namespaces and organization"""
        registry = ComponentRegistry()
        
        class FormInput(BladeComponent):
            def render(self) -> str:
                return "<input>"
        
        class FormButton(BladeComponent):
            def render(self) -> str:
                return "<button>"
        
        # Register with namespace-like names
        registry.register('form.input', FormInput)
        registry.register('form.button', FormButton)
        registry.register('ui.card', 'components/ui/card.blade.html')
        
        assert registry.has('form.input')
        assert registry.has('form.button') 
        assert registry.has('ui.card')
        
        # Test listing components by prefix
        form_components = registry.get_by_prefix('form.')
        assert len(form_components) == 2
        assert 'form.input' in form_components
        assert 'form.button' in form_components


if __name__ == "__main__":
    pytest.main([__file__, "-v"])