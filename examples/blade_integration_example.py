"""
Example of integrating Blade Template Engine with FastAPI
Demonstrates how to use the Blade engine in FastAPI routes and middleware
"""
from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

# Import our Blade engine
from app.View import blade, view, view_share, view_composer

# Create FastAPI app
app = FastAPI(title="Blade Template Integration Example")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Blade engine with template paths
template_paths = [
    "resources/views",
    "resources/views/examples"
]
blade_engine = blade(template_paths)

# Share global data with all views
view_share("app_name", "FastAPI Laravel")
view_share("app_version", "1.0.0")
view_share("current_year", datetime.now().year)

# Example view composer for dashboard
def dashboard_composer(context: Dict[str, Any]) -> Dict[str, Any]:
    """Compose additional data for dashboard views"""
    return {
        "total_users": 1250,
        "active_sessions": 45,
        "api_calls_today": 12500,
        "recent_activities": [
            {
                "description": "New user registered",
                "created_at": datetime.now()
            },
            {
                "description": "System backup completed",
                "created_at": datetime.now()
            }
        ]
    }

# Register view composer
view_composer("dashboard*", dashboard_composer)


# Example user class for authentication context
class User:
    def __init__(self, name: str, email: str, roles: List[str] = None, permissions: List[str] = None):
        self.name = name
        self.email = email
        self.id = 1
        self.roles = roles or []
        self.permissions = permissions or []
        self.created_at = datetime.now()
        self.stats = {
            "posts": 25,
            "followers": 150,
            "following": 75,
            "points": 890
        }
        self.recent_activities = [
            {"description": "Updated profile information", "created_at": datetime.now()},
            {"description": "Posted a new article", "created_at": datetime.now()},
        ]
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)
    
    def can(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions


# Mock authentication dependency
async def get_current_user() -> Optional[User]:
    """Mock function to get current authenticated user"""
    # In real app, this would check JWT token, session, etc.
    return User(
        name="John Doe",
        email="john@example.com",
        roles=["admin", "moderator"],
        permissions=["view-users", "edit-users", "create-products", "edit-products"]
    )


# Mock function to get categories for product listing
def get_categories():
    """Mock function to get product categories"""
    return [
        {"id": 1, "name": "Electronics"},
        {"id": 2, "name": "Books"},
        {"id": 3, "name": "Clothing"},
        {"id": 4, "name": "Home & Garden"},
    ]


# Mock function to get products
def get_products(search: str = None, category: int = None, sort: str = "name"):
    """Mock function to get products"""
    products = [
        {
            "id": 1,
            "name": "Smartphone Pro Max",
            "description": "Latest smartphone with advanced features and excellent camera quality",
            "price": 999.99,
            "sale_price": 899.99,
            "stock_quantity": 15,
            "category": {"name": "Electronics"},
            "rating": 4.5,
            "reviews_count": 128,
            "image": "products/smartphone.jpg",
            "featured": True
        },
        {
            "id": 2,
            "name": "Programming Book Collection",
            "description": "Complete collection of programming books for developers",
            "price": 149.99,
            "sale_price": None,
            "stock_quantity": 0,
            "category": {"name": "Books"},
            "rating": 4.8,
            "reviews_count": 45,
            "image": None,
            "featured": False
        },
        {
            "id": 3,
            "name": "Designer T-Shirt",
            "description": "Comfortable cotton t-shirt with modern design",
            "price": 29.99,
            "sale_price": None,
            "stock_quantity": 3,
            "category": {"name": "Clothing"},
            "rating": 4.2,
            "reviews_count": 67,
            "image": "products/tshirt.jpg",
            "featured": False
        }
    ]
    
    # Mock pagination object
    class MockPagination:
        def __init__(self, items):
            self.items = items
            self.has_pages = False
        
        def __iter__(self):
            return iter(self.items)
        
        def links(self):
            return ""  # Mock pagination links
    
    return MockPagination(products)


@app.get("/", response_class=HTMLResponse)
async def home(current_user: Optional[User] = Depends(get_current_user)):
    """Home page using Blade template"""
    context = {
        "current_user": current_user,
        "message": "Welcome to FastAPI with Blade Templates!",
        "features": [
            "Laravel-style Blade templating",
            "Template inheritance and sections",
            "Custom directives and filters",
            "View composition and shared data",
            "Template caching for performance"
        ]
    }
    
    return HTMLResponse(view("dashboard", context))


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(current_user: Optional[User] = Depends(get_current_user)):
    """Dashboard page with view composer"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    context = {
        "current_user": current_user,
    }
    
    return HTMLResponse(view("dashboard", context))


@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def user_profile(user_id: int, current_user: Optional[User] = Depends(get_current_user)):
    """User profile page"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # In real app, fetch user by ID
    user = current_user  # Mock: using current user as viewed user
    
    context = {
        "current_user": current_user,
        "user": user,
    }
    
    return HTMLResponse(view("examples/user-profile", context))


@app.get("/products", response_class=HTMLResponse)
async def product_list(
    request: Request,
    search: Optional[str] = None,
    category: Optional[int] = None,
    sort: str = "name",
    current_user: Optional[User] = Depends(get_current_user)
):
    """Product listing page"""
    context = {
        "current_user": current_user,
        "products": get_products(search, category, sort),
        "categories": get_categories(),
        "request": {
            "get": lambda key: {
                "search": search,
                "category": category,
                "sort": sort
            }.get(key)
        }
    }
    
    return HTMLResponse(view("examples/product-list", context))


@app.get("/contact", response_class=HTMLResponse)
async def contact_form(current_user: Optional[User] = Depends(get_current_user)):
    """Contact form page"""
    context = {
        "current_user": current_user,
        "old": lambda key, default=None: default,  # Mock old input function
        "route": lambda name: f"/{name}",  # Mock route function
        "session": {}  # Mock session
    }
    
    return HTMLResponse(view("examples/form-example", context))


@app.post("/contact", response_class=HTMLResponse)
async def contact_submit(
    name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    subject: str = Form(...),
    priority: str = Form("normal"),
    message: str = Form(...),
    subscribe_newsletter: bool = Form(False),
    agree_terms: bool = Form(...),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Handle contact form submission"""
    
    # Mock form validation
    errors = {}
    if not name:
        errors["name"] = "Name is required"
    if not email or "@" not in email:
        errors["email"] = "Valid email is required"
    if not subject:
        errors["subject"] = "Subject is required"
    if not message:
        errors["message"] = "Message is required"
    if not agree_terms:
        errors["agree_terms"] = "You must agree to the terms"
    
    if errors:
        # Return form with errors
        context = {
            "current_user": current_user,
            "errors": errors,
            "old": lambda key, default=None: {
                "name": name,
                "email": email,
                "phone": phone,
                "subject": subject,
                "priority": priority,
                "message": message,
                "subscribe_newsletter": subscribe_newsletter
            }.get(key, default),
            "route": lambda name: f"/{name}",
            "session": {}
        }
        return HTMLResponse(view("examples/form-example", context))
    
    # Mock successful form processing
    context = {
        "current_user": current_user,
        "old": lambda key, default=None: default,
        "route": lambda name: f"/{name}",
        "session": {"success": "Thank you for your message! We'll get back to you soon."}
    }
    
    return HTMLResponse(view("examples/form-example", context))


@app.get("/blade-test", response_class=HTMLResponse)
async def blade_test():
    """Test various Blade features"""
    
    # Create a test template dynamically to demonstrate Blade compilation
    test_template_content = """
    <h1>Blade Test Page</h1>
    
    <h2>Basic Variable Output</h2>
    <p>Hello, {{ name }}!</p>
    
    <h2>Conditional Directives</h2>
    @if(show_admin)
        <p>Admin content is visible</p>
    @else
        <p>Regular user content</p>
    @endif
    
    @unless(hide_message)
        <p>This message is shown unless hide_message is true</p>
    @endunless
    
    <h2>Loop Directives</h2>
    @if(items)
        <ul>
        @foreach(items as item)
            <li>{{ item }}</li>
        @endforeach
        </ul>
    @endif
    
    @forelse(empty_items as item)
        <p>Item: {{ item }}</p>
    @empty
        <p>No items to display</p>
    @endforelse
    
    <h2>Authentication Directives</h2>
    @auth
        <p>You are logged in!</p>
    @endauth
    
    @guest
        <p>Please log in to continue</p>
    @endguest
    
    <h2>Permission Directives</h2>
    @can('edit-posts')
        <button>Edit Post</button>
    @endcan
    
    @cannot('delete-posts')
        <p>You cannot delete posts</p>
    @endcannot
    
    <h2>Custom Filters</h2>
    <p>Title case: {{ text | title }}</p>
    <p>Slug: {{ text | slug }}</p>
    <p>Money: {{ price | money }}</p>
    <p>Percentage: {{ rate | percentage }}</p>
    
    <h2>JSON Output</h2>
    <script>
        var data = @json(data);
        console.log(data);
    </script>
    
    <h2>Unescaped HTML</h2>
    <p>Escaped: {{ html_content }}</p>
    <p>Unescaped: {!! html_content !!}</p>
    
    <h2>Comments (invisible)</h2>
    {{-- This is a Blade comment and should not appear in output --}}
    <p>This text should appear after the invisible comment</p>
    """
    
    # Write test template
    test_template_path = "resources/views/blade-test.blade.html"
    os.makedirs(os.path.dirname(test_template_path), exist_ok=True)
    with open(test_template_path, 'w') as f:
        f.write(test_template_content)
    
    # Mock user for testing
    test_user = User(
        name="Test User",
        email="test@example.com",
        roles=["admin"],
        permissions=["edit-posts", "create-posts"]
    )
    
    context = {
        "name": "Blade Tester",
        "show_admin": True,
        "hide_message": False,
        "items": ["Item 1", "Item 2", "Item 3"],
        "empty_items": [],
        "current_user": test_user,
        "text": "hello world example",
        "price": 123.45,
        "rate": 0.75,
        "data": {"key": "value", "number": 42, "array": [1, 2, 3]},
        "html_content": "<strong>Bold text</strong>"
    }
    
    return HTMLResponse(view("blade-test", context))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 error page"""
    context = {
        "error_code": 404,
        "error_message": "Page Not Found",
        "error_description": "The page you are looking for could not be found."
    }
    
    # You could create a custom error template
    error_html = f"""
    <html>
        <head><title>404 - Page Not Found</title></head>
        <body>
            <h1>{context['error_code']} - {context['error_message']}</h1>
            <p>{context['error_description']}</p>
            <a href="/">Go Home</a>
        </body>
    </html>
    """
    
    return HTMLResponse(error_html, status_code=404)


if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI with Blade Template Engine...")
    print("Available endpoints:")
    print("  GET  /               - Home page")
    print("  GET  /dashboard      - Dashboard (requires auth)")
    print("  GET  /profile/1      - User profile (requires auth)")
    print("  GET  /products       - Product listing")
    print("  GET  /contact        - Contact form")
    print("  POST /contact        - Contact form submission")
    print("  GET  /blade-test     - Blade features test page")
    print()
    print("Blade Template Features:")
    print("  ✓ Template inheritance (@extends, @section, @yield)")
    print("  ✓ Conditional directives (@if, @unless, @auth, @guest)")
    print("  ✓ Loop directives (@foreach, @forelse)")
    print("  ✓ Permission directives (@can, @cannot, @hasrole)")
    print("  ✓ Include directives (@include, @includeIf)")
    print("  ✓ Custom filters (ucfirst, slug, money, percentage)")
    print("  ✓ View composition and shared data")
    print("  ✓ Template caching for performance")
    print("  ✓ Blade comments and unescaped output")
    
    uvicorn.run("blade_integration_example:app", host="0.0.0.0", port=8000, reload=True)