"""
Test Suite for Blade Engine Service Integration
Tests service provider, dependency injection, and service directives
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Generator, Tuple, List
import os

from app.View.BladeEngine import BladeEngine


class MockAuthService:
    """Mock authentication service"""
    
    def __init__(self) -> None:
        self.user: Optional[Dict[str, Any]] = None
    
    def set_user(self, user: Optional[Dict[str, Any]]) -> None:
        self.user = user
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        return self.user
    
    def check(self) -> bool:
        return self.user is not None
    
    def guest(self) -> bool:
        return self.user is None


class MockConfigService:
    """Mock configuration service"""
    
    def __init__(self) -> None:
        self.config = {
            'app.name': 'Test Application',
            'app.env': 'testing',
            'app.debug': True,
            'mail.driver': 'smtp',
            'cache.default': 'file'
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
    
    def has(self, key: str) -> bool:
        return key in self.config


class MockRequestService:
    """Mock request service"""
    
    def __init__(self) -> None:
        self.request_data: Dict[str, Any] = {}
        self.old_input: Dict[str, Any] = {}
    
    def set_request(self, request: Dict[str, Any]) -> None:
        self.request_data = request
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.request_data.get(key, default)
    
    def input(self, key: str, default: Any = None) -> Any:
        return self.request_data.get(key, default)
    
    def old(self, key: str, default: Any = None) -> Any:
        return self.old_input.get(key, default)
    
    def set_old_input(self, data: Dict[str, Any]) -> None:
        self.old_input = data


class TestBladeServiceIntegration:
    """Test service provider and dependency injection"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        
        # Register mock services
        auth_service = MockAuthService()
        config_service = MockConfigService()
        request_service = MockRequestService()
        
        engine.service_provider.container.bind('auth', lambda: auth_service)
        engine.service_provider.container.bind('config_service', lambda: config_service)
        engine.service_provider.container.bind('request', lambda: request_service)
        
        yield (engine, temp_path, auth_service, config_service, request_service)
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_service_injection_in_templates(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test service injection through template context"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        # Set up services
        auth_service.set_user({"id": 1, "name": "John Doe", "email": "john@example.com"})
        request_service.set_old_input({"username": "johndoe", "email": "john@example.com"})
        
        template_content = """
<div class="service-integration">
    <!-- Auth service integration -->
    <div class="auth-section">
        @if(current_user)
            <p>Welcome, {{ current_user.name }}!</p>
            <p>Email: {{ current_user.email }}</p>
        @else
            <p>Please log in</p>
        @endif
    </div>
    
    <!-- Config service integration -->
    <div class="config-section">
        <h1>{{ config('app.name') }}</h1>
        <p>Environment: {{ config('app.env') }}</p>
        <p>Debug Mode: {{ config('app.debug') }}</p>
        <p>Unknown Config: {{ config('unknown.key', 'default_value') }}</p>
    </div>
    
    <!-- Request service integration -->
    <div class="request-section">
        <form>
            <input type="text" name="username" value="{{ old('username') }}">
            <input type="email" name="email" value="{{ old('email') }}">
            <input type="text" name="phone" value="{{ old('phone', '+1') }}">
        </form>
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "services.blade.html", template_content)
        
        result = engine.render("services.blade.html")
        
        # Test auth service integration
        assert "Welcome, John Doe!" in result
        assert "Email: john@example.com" in result
        assert "Please log in" not in result
        
        # Test config service integration
        assert "Test Application" in result
        assert "Environment: testing" in result
        assert "Debug Mode: True" in result
        assert "Unknown Config: default_value" in result
        
        # Test request service integration (old input)
        assert 'value="johndoe"' in result
        assert 'value="john@example.com"' in result
        assert 'value="+1"' in result  # Default value when not in old input
    
    def test_service_directives(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test custom service-based directives"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        # Set up test scenario
        auth_service.set_user({
            "id": 1,
            "name": "Admin User",
            "roles": ["admin", "editor"],
            "permissions": ["manage_users", "edit_posts"]
        })
        
        config_service.set('feature.flags.beta_features', True)
        config_service.set('feature.flags.maintenance_mode', False)
        
        template_content = """
<div class="service-directives">
    <!-- Environment-based conditionals -->
    @env('testing', 'development')
        <div class="dev-tools">Development Tools Available</div>
    @endenv
    
    @env('production')
        <div class="production-notice">Production Environment</div>
    @endenv
    
    <!-- Feature flag conditionals -->
    @if(config('feature.flags.beta_features'))
        <div class="beta-features">
            <h3>Beta Features</h3>
            <button>Try New Dashboard</button>
        </div>
    @endif
    
    @unless(config('feature.flags.maintenance_mode'))
        <div class="app-content">
            <p>Application is running normally</p>
        </div>
    @endunless
    
    <!-- User role and permission checks -->
    @hasrole('admin')
        <nav class="admin-nav">
            <a href="/admin">Admin Panel</a>
            <a href="/users">Manage Users</a>
        </nav>
    @endhasrole
    
    @haspermission('edit_posts')
        <div class="post-actions">
            <button>Create Post</button>
            <button>Edit Posts</button>
        </div>
    @endhaspermission
    
    @can('manage_users')
        <div class="user-management">
            <h3>User Management</h3>
            <button>Add User</button>
            <button>Delete User</button>
        </div>
    @endcan
</div>
        """.strip()
        self.create_template(temp_dir, "service_directives.blade.html", template_content)
        
        result = engine.render("service_directives.blade.html")
        
        # Test environment directives
        assert "Development Tools Available" in result
        assert "Production Environment" not in result
        
        # Test feature flag conditionals
        assert "Beta Features" in result
        assert "Try New Dashboard" in result
        assert "Application is running normally" in result
        
        # Test role and permission directives
        assert "Admin Panel" in result
        assert "Manage Users" in result
        assert "Create Post" in result
        assert "Edit Posts" in result
        assert "User Management" in result
    
    def test_service_configuration_changes(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test dynamic service configuration changes"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        template_content = """
<div class="dynamic-config">
    <h1>{{ config('app.name', 'Default App') }}</h1>
    <p>Theme: {{ config('ui.theme', 'light') }}</p>
    <p>Language: {{ config('app.locale', 'en') }}</p>
    
    @if(config('app.debug'))
        <div class="debug-info">Debug mode is enabled</div>
    @endif
    
    @production
        <div class="production-warning">Running in production</div>
    @endproduction
</div>
        """.strip()
        self.create_template(temp_dir, "dynamic_config.blade.html", template_content)
        
        # First render with default config
        result1 = engine.render("dynamic_config.blade.html")
        assert "Test Application" in result1
        assert "Theme: light" in result1
        assert "Language: en" in result1
        assert "Debug mode is enabled" in result1
        
        # Change configuration
        config_service.set('app.name', 'Updated Application')
        config_service.set('ui.theme', 'dark')
        config_service.set('app.locale', 'es')
        config_service.set('app.debug', False)
        config_service.set('app.env', 'production')
        
        # Second render with updated config
        result2 = engine.render("dynamic_config.blade.html")
        assert "Updated Application" in result2
        assert "Theme: dark" in result2
        assert "Language: es" in result2
        assert "Debug mode is enabled" not in result2
        # Note: @production directive needs proper implementation to test
    
    def test_service_error_handling(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test error handling when services are unavailable"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        template_content = """
<div class="error-handling">
    <!-- Test with missing user -->
    @auth
        <p>User: {{ current_user.name }}</p>
    @else
        <p>No user authenticated</p>
    @endauth
    
    <!-- Test with non-existent config -->
    <p>Missing Config: {{ config('non.existent.key', 'fallback_value') }}</p>
    
    <!-- Test with missing old input -->
    <input type="text" value="{{ old('missing_field', 'default') }}">
    
    <!-- Test service method calls -->
    @if(current_user and current_user.get('active', True))
        <p>User is active</p>
    @else
        <p>User is inactive or not found</p>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "error_handling.blade.html", template_content)
        
        # Test with no authenticated user
        auth_service.set_user(None)
        
        result = engine.render("error_handling.blade.html")
        
        # Should handle missing services gracefully
        assert "No user authenticated" in result
        assert "Missing Config: fallback_value" in result
        assert 'value="default"' in result
        assert "User is inactive or not found" in result


class TestBladeServiceProviderCustomization:
    """Test custom service provider features"""
    
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
    
    def test_custom_service_registration(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test registering custom services"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        # Create custom service
        class NotificationService:
            def __init__(self) -> None:
                self.notifications: List[Dict[str, str]] = []
            
            def add(self, message: str, type: str = 'info') -> None:
                self.notifications.append({'message': message, 'type': type})
            
            def get_all(self) -> List[Dict[str, str]]:
                return self.notifications
            
            def count(self) -> int:
                return len(self.notifications)
        
        # Register custom service
        notification_service = NotificationService()
        notification_service.add("Welcome to the application", "success")
        notification_service.add("Your profile is incomplete", "warning")
        
        engine.service_provider.container.bind('notifications', lambda: notification_service)
        
        template_content = """
<div class="notifications">
    <h3>Notifications ({{ notifications.count() }})</h3>
    
    @if(notifications.count() > 0)
        <div class="notification-list">
            @foreach(notifications.get_all() as $notification)
                <div class="alert alert-{{ $notification.type }}">
                    {{ $notification.message }}
                </div>
            @endforeach
        </div>
    @else
        <p>No notifications</p>
    @endif
</div>
        """.strip()
        self.create_template(temp_dir, "custom_service.blade.html", template_content)
        
        result = engine.render("custom_service.blade.html")
        
        # Should use custom service
        assert "Notifications (2)" in result
        assert "Welcome to the application" in result
        assert "Your profile is incomplete" in result
        assert "alert alert-success" in result
        assert "alert alert-warning" in result
    
    def test_service_scoping(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test service scoping and lifecycle"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        # Create services with different scopes
        class CounterService:
            def __init__(self) -> None:
                self.count = 0
            
            def increment(self) -> int:
                self.count += 1
                return self.count
            
            def get_count(self) -> int:
                return self.count
        
        # Singleton service
        counter_service = CounterService()
        engine.service_provider.container.bind('counter', lambda: counter_service)
        
        template_content = """
<div class="counter-test">
    <p>Initial Count: {{ counter.get_count() }}</p>
    <p>After Increment 1: {{ counter.increment() }}</p>
    <p>After Increment 2: {{ counter.increment() }}</p>
    <p>Final Count: {{ counter.get_count() }}</p>
</div>
        """.strip()
        self.create_template(temp_dir, "scoping.blade.html", template_content)
        
        result = engine.render("scoping.blade.html")
        
        # Should maintain state across template rendering
        assert "Initial Count: 0" in result
        assert "After Increment 1: 1" in result
        assert "After Increment 2: 2" in result
        assert "Final Count: 2" in result
    
    def test_service_dependency_injection(self, blade_engine: Tuple[BladeEngine, str, MockAuthService, MockConfigService, MockRequestService]) -> None:
        """Test dependency injection between services"""
        engine, temp_dir, auth_service, config_service, request_service = blade_engine
        
        # Create services with dependencies
        class LoggerService:
            def __init__(self) -> None:
                self.logs: List[str] = []
            
            def log(self, message: str, level: str = 'info') -> None:
                self.logs.append(f"[{level.upper()}] {message}")
            
            def get_logs(self) -> List[str]:
                return self.logs
        
        class UserService:
            def __init__(self, logger: LoggerService):
                self.logger = logger
                self.users: List[str] = []
            
            def add_user(self, name: str) -> None:
                self.users.append(name)
                self.logger.log(f"User {name} added", "info")
            
            def get_users(self) -> List[str]:
                return self.users
            
            def get_user_count(self) -> int:
                count = len(self.users)
                self.logger.log(f"User count requested: {count}", "debug")
                return count
        
        # Register services with dependency injection
        logger_service = LoggerService()
        user_service = UserService(logger_service)
        
        # Add some test data
        user_service.add_user("Alice")
        user_service.add_user("Bob")
        
        engine.service_provider.container.bind('logger', lambda: logger_service)
        engine.service_provider.container.bind('user_service', lambda: user_service)
        
        template_content = """
<div class="dependency-injection">
    <div class="users-section">
        <h3>Users ({{ user_service.get_user_count() }})</h3>
        <ul>
            @foreach(user_service.get_users() as $user)
                <li>{{ $user }}</li>
            @endforeach
        </ul>
    </div>
    
    <div class="logs-section">
        <h3>System Logs</h3>
        <ul>
            @foreach(logger.get_logs() as $log)
                <li>{{ $log }}</li>
            @endforeach
        </ul>
    </div>
</div>
        """.strip()
        self.create_template(temp_dir, "dependency_injection.blade.html", template_content)
        
        result = engine.render("dependency_injection.blade.html")
        
        # Should show dependency injection working
        assert "Users (2)" in result
        assert "Alice" in result
        assert "Bob" in result
        
        assert "[INFO] User Alice added" in result
        assert "[INFO] User Bob added" in result
        assert "[DEBUG] User count requested: 2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])