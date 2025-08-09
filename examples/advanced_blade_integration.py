"""
Advanced Blade Template Engine Integration Example
Demonstrates all the advanced features including components, services, and more
"""
from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Dict, Any, Optional
import json

# Import advanced Blade features
from app.View import (
    BladeEngine, blade, view, view_share, view_composer,
    blade_config, blade_service, component_registry, BladeComponent,
    blade_service_provider, ServiceContract
)

# Create FastAPI app
app = FastAPI(title="Advanced Blade Features Demo")

# Initialize Blade with advanced features
template_paths = [
    "resources/views",
    "resources/views/components",
    "resources/views/examples"
]

# Setup Blade engine
blade_engine = blade(template_paths)

# Configure Blade services
blade_config('app.name', 'Advanced Blade Demo')
blade_config('app.env', 'development')
blade_config('app.debug', True)

# Setup translations
translator = blade_service('translator')
translator.load_translations('en', {
    'welcome.message': 'Welcome to :app_name, :name!',
    'nav.home': 'Home',
    'nav.dashboard': 'Dashboard',
    'nav.profile': 'Profile',
    'messages.notification.singular': 'You have :count notification',
    'messages.notification.plural': 'You have :count notifications'
})

# Setup URL service
url_service = blade_service('url')
url_service.register_route('home', '/')
url_service.register_route('dashboard', '/dashboard')
url_service.register_route('profile', '/profile/{id}')
url_service.register_route('users.show', '/users/{id}')

# Share global data
view_share('app_name', 'Advanced Blade Demo')
view_share('app_version', '2.0.0')


# Custom Service Example
class NotificationService(ServiceContract):
    """Custom notification service"""
    
    def __init__(self):
        self.notifications = []
    
    def get_name(self) -> str:
        return "notifications"
    
    def add(self, message: str, type: str = 'info') -> None:
        """Add a notification"""
        self.notifications.append({
            'message': message,
            'type': type,
            'id': len(self.notifications) + 1
        })
    
    def get_all(self):
        """Get all notifications"""
        return self.notifications
    
    def count(self) -> int:
        """Get notification count"""
        return len(self.notifications)
    
    def clear(self) -> None:
        """Clear all notifications"""
        self.notifications.clear()


# Register custom service
notification_service = NotificationService()
blade_service_provider.register_service(notification_service)


# Custom Component Example
class StatsCardComponent(BladeComponent):
    """Statistics card component"""
    
    def render(self) -> str:
        title = self.attributes.get('title', 'Statistic')
        value = self.attributes.get('value', '0')
        color = self.attributes.get('color', 'blue')
        icon = self.attributes.get('icon', '📊')
        
        color_classes = {
            'blue': 'bg-blue-50 text-blue-600',
            'green': 'bg-green-50 text-green-600',
            'red': 'bg-red-50 text-red-600',
            'yellow': 'bg-yellow-50 text-yellow-600'
        }
        
        css_class = color_classes.get(color, color_classes['blue'])
        
        return f'''
        <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    <div class="w-12 h-12 {css_class} rounded-lg flex items-center justify-center text-2xl">
                        {icon}
                    </div>
                </div>
                <div class="ml-4">
                    <p class="text-sm font-medium text-gray-500">{title}</p>
                    <p class="text-2xl font-semibold text-gray-900">{value}</p>
                </div>
            </div>
        </div>
        '''.strip()


# Register custom component
blade_engine.register_component('stats-card', StatsCardComponent)

# Mock user for demonstration
class MockUser:
    def __init__(self, id: int, name: str, email: str, roles: list = None):
        self.id = id
        self.name = name
        self.email = email
        self.roles = roles or ['user']
        self.permissions = ['view-dashboard', 'edit-profile']
    
    def has_role(self, role: str) -> bool:
        return role in self.roles
    
    def can(self, permission: str) -> bool:
        return permission in self.permissions


# Mock data and functions
def get_current_user():
    return MockUser(1, "John Doe", "john@example.com", ['admin', 'user'])

def get_dashboard_stats():
    return {
        'total_users': 1250,
        'active_sessions': 45,
        'api_calls_today': 12500,
        'revenue_today': 5420.50
    }

# View composers
def dashboard_composer(context: Dict[str, Any]) -> Dict[str, Any]:
    """Add dashboard-specific data"""
    stats = get_dashboard_stats()
    
    # Add notifications
    notifications = blade_service('notifications')
    notifications.add('Welcome to the dashboard!', 'success')
    notifications.add('System maintenance scheduled', 'warning')
    
    return {
        'dashboard_stats': stats,
        'notification_count': notifications.count(),
        'notifications': notifications.get_all()
    }

# Register view composer
view_composer('examples/advanced-features*', dashboard_composer)


@app.middleware("http")
async def add_blade_context(request: Request, call_next):
    """Middleware to set request context for Blade"""
    # Set current user
    user = get_current_user()
    blade_engine.set_user(user)
    
    # Set request context
    blade_engine.set_request(request)
    
    response = await call_next(request)
    return response


@app.get("/", response_class=HTMLResponse)
async def advanced_demo():
    """Advanced Blade features demonstration"""
    
    # Add some sample data
    context = {
        'page_title': 'Advanced Blade Features Demo',
        'show_debug': True,
        'users': [
            {'id': 1, 'name': 'Alice Johnson', 'role': 'Admin', 'active': True},
            {'id': 2, 'name': 'Bob Smith', 'role': 'User', 'active': False},
            {'id': 3, 'name': 'Carol Davis', 'role': 'Moderator', 'active': True}
        ],
        'errors': {},  # Empty for demo
        'notification_count': 2
    }
    
    return HTMLResponse(view("examples/advanced-features", context))


@app.get("/components-demo", response_class=HTMLResponse)
async def components_demo():
    """Component system demonstration"""
    
    template_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Components Demo</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-8">Component System Demo</h1>
            
            <!-- Stats Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <x-stats-card 
                    title="Total Users" 
                    value="1,250" 
                    color="blue" 
                    icon="👥"
                />
                
                <x-stats-card 
                    title="Revenue" 
                    value="$5,420" 
                    color="green" 
                    icon="💰"
                />
                
                <x-stats-card 
                    title="Orders" 
                    value="89" 
                    color="yellow" 
                    icon="📦"
                />
                
                <x-stats-card 
                    title="Issues" 
                    value="3" 
                    color="red" 
                    icon="⚠️"
                />
            </div>
            
            <!-- Alerts -->
            <div class="space-y-4">
                <x-alert type="success" dismissible>
                    <strong>Success!</strong> Your changes have been saved.
                </x-alert>
                
                <x-alert type="warning">
                    <strong>Warning!</strong> Please review your settings.
                </x-alert>
                
                <x-alert type="error">
                    <strong>Error!</strong> Something went wrong.
                </x-alert>
            </div>
            
            <!-- Card with Slots -->
            <x-card title="Advanced Card" class="mt-8">
                <x-slot name="header">
                    <div class="flex justify-between items-center">
                        <h3 class="text-lg font-semibold">Custom Header</h3>
                        <x-button size="small">Action</x-button>
                    </div>
                </x-slot>
                
                <p>This card demonstrates the slot system. Content can be injected into named slots for flexible layouts.</p>
                
                <x-slot name="footer">
                    <div class="flex justify-end space-x-2">
                        <x-button variant="secondary" size="small">Cancel</x-button>
                        <x-button variant="primary" size="small">Save</x-button>
                    </div>
                </x-slot>
            </x-card>
        </div>
    </body>
    </html>
    '''
    
    # Create temporary template
    temp_file = "/tmp/components_demo.blade.html"
    with open(temp_file, 'w') as f:
        f.write(template_content)
    
    # Render with component compilation
    compiled = blade_engine.compile_blade(template_content)
    
    return HTMLResponse(compiled)


@app.get("/services-demo", response_class=HTMLResponse)
async def services_demo():
    """Services and injection demonstration"""
    
    # Get services
    config_service = blade_service('config_service')
    auth = blade_service('auth')
    cache = blade_service('cache')
    notifications = blade_service('notifications')
    
    # Add some cache data
    cache.put('demo_data', {'cached_at': 'now', 'value': 'This is cached data'})
    
    # Add notifications
    notifications.clear()
    notifications.add('Services are working correctly!', 'success')
    notifications.add('Cache has been populated', 'info')
    
    template_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Services Demo</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-8">Services Demonstration</h1>
            
            <!-- Configuration Service -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Configuration Service</h2>
                <p><strong>App Name:</strong> {{ config('app.name') }}</p>
                <p><strong>Environment:</strong> {{ config('app.env') }}</p>
                <p><strong>Debug Mode:</strong> {{ config('app.debug') }}</p>
            </div>
            
            <!-- Authentication Service -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Authentication Service</h2>
                @auth
                    <p><strong>User:</strong> {{ auth.user().name }}</p>
                    <p><strong>ID:</strong> {{ auth.id() }}</p>
                    <p><strong>Email:</strong> {{ auth.user().email }}</p>
                @else
                    <p>Not authenticated</p>
                @endauth
            </div>
            
            <!-- Notifications Service -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Notifications Service</h2>
                <p><strong>Count:</strong> {{ notifications.count() }}</p>
                <div class="mt-4 space-y-2">
                    @foreach(notifications.get_all() as notification)
                        <div class="p-2 border-l-4 {{ 
                            'border-green-500 bg-green-50' if notification.type == 'success' 
                            else 'border-blue-500 bg-blue-50' 
                        }}">
                            {{ notification.message }}
                        </div>
                    @endforeach
                </div>
            </div>
            
            <!-- Translation Service -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Translation Service</h2>
                <p>{{ __('welcome.message', {'app_name': config('app.name'), 'name': auth.user().name}) }}</p>
                <p>{{ trans_choice('messages.notification', notifications.count(), {'count': notifications.count()}) }}</p>
            </div>
            
            <!-- Cache Service -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Cache Service</h2>
                <p><strong>Demo Data:</strong> {{ cache.get('demo_data').value if cache.has('demo_data') else 'Not cached' }}</p>
            </div>
            
            <!-- Debugging -->
            @dump(auth.user())
        </div>
    </body>
    </html>
    '''
    
    context = {}
    
    # Render directly with services injected
    compiled = blade_engine.compile_blade(template_content)
    template = blade_engine.env.from_string(compiled)
    
    # Get full context with services
    service_context = blade_engine.service_provider.get_template_context()
    final_context = {**context, **service_context}
    
    rendered = template.render(**final_context)
    
    return HTMLResponse(rendered)


@app.get("/api/test-blade-features")
async def test_blade_features():
    """API endpoint to test Blade features programmatically"""
    
    # Test configuration
    blade_config('test.setting', 'test_value')
    config_result = blade_config('test.setting')
    
    # Test cache
    cache = blade_service('cache')
    cache.put('api_test', {'timestamp': 'now', 'data': 'api data'})
    cache_result = cache.get('api_test')
    
    # Test notifications
    notifications = blade_service('notifications')
    notifications.add('API test notification', 'info')
    
    # Test template rendering
    simple_template = "Hello {{ name }}! Config: {{ config('app.name') }}"
    compiled = blade_engine.compile_blade(simple_template)
    template = blade_engine.env.from_string(compiled)
    
    service_context = blade_engine.service_provider.get_template_context()
    rendered = template.render(name="API User", **service_context)
    
    return {
        "blade_features": {
            "config_test": config_result,
            "cache_test": cache_result,
            "notification_count": notifications.count(),
            "template_render": rendered,
            "services_available": list(blade_service_provider.container.services.keys())
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Advanced Blade Template Engine Demo")
    print("=" * 50)
    print("Available Endpoints:")
    print("  GET  /                - Advanced features demo")
    print("  GET  /components-demo - Component system demo") 
    print("  GET  /services-demo   - Services and injection demo")
    print("  GET  /api/test-blade-features - API test of Blade features")
    print()
    print("✨ New Advanced Features:")
    print("  🧩 Component System     - Reusable UI components")
    print("  🛠️  Service Injection   - Dependency injection in templates")
    print("  📚 Stacks & Once       - Content organization")
    print("  🎨 Conditional Classes  - Dynamic styling")
    print("  🔄 Advanced Loops       - Enhanced iteration")
    print("  🌍 Internationalization - Multi-language support")
    print("  🔧 Debug Tools          - Development helpers")
    print("  ⚡ Template Fragments   - Reusable snippets")
    print("  🏗️  Multiple Layouts    - Complex inheritance")
    print()
    
    uvicorn.run("advanced_blade_integration:app", host="0.0.0.0", port=8000, reload=True)