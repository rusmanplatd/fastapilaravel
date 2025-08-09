from __future__ import annotations

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.Http.Controllers.Api.AuthController import get_current_user
from app.Http.Controllers.Web.WebAuthController import web_auth_controller
from app.Http.Controllers.Web.WebMFAController import web_mfa_controller
from app.Models import User
from app.Http.Middleware.SessionMiddleware import get_session
from config.database import get_db
from typing_extensions import Annotated

"""
Laravel-style Web Routes.

Here is where you can register web routes for your application. These
routes are loaded by the RouteServiceProvider within a group which
contains the "web" middleware group. Now create something great!
"""

web_router = APIRouter()
templates = Jinja2Templates(directory="resources/views")


# Helper function to get current user from session
def get_current_user_from_session(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from session."""
    session = request.session
    
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    return {
        'id': user_id,
        'name': session.get('user_name'),
        'email': session.get('user_email')
    }

@web_router.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request) -> HTMLResponse:
    """Welcome page route."""
    user = get_current_user_from_session(request)
    return templates.TemplateResponse("welcome.html", {
        "request": request,
        "user": user,
        "title": "Welcome"
    })


@web_router.get("/about", response_class=HTMLResponse, name="about")
async def about() -> str:
    """About page route."""
    return """
    <html>
        <head><title>About - FastAPI Laravel</title></head>
        <body>
            <h1>About Us</h1>
            <p>This is a FastAPI application with Laravel-style architecture.</p>
            <ul>
                <li>Laravel-style MVC patterns</li>
                <li>Service Providers & Dependency Injection</li>
                <li>Eloquent-style Models & Relationships</li>
                <li>Middleware & Route Groups</li>
                <li>Form Requests & Validation</li>
                <li>Broadcasting & Events</li>
            </ul>
            <a href="/">Back to Home</a>
        </body>
    </html>
    """


@web_router.get("/contact", response_class=HTMLResponse, name="contact")
async def contact() -> str:
    """Contact page route.""" 
    return """
    <html>
        <head><title>Contact - FastAPI Laravel</title></head>
        <body>
            <h1>Contact Us</h1>
            <p>Get in touch with us!</p>
            <a href="/">Back to Home</a>
        </body>
    </html>
    """


async def get_current_user_optional() -> User | None:
    """Get current user if available, None otherwise."""
    try:
        # This would need to be implemented based on your auth logic
        return None  # For now, return None
    except:
        return None

@web_router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(
    current_user: Annotated[User | None, Depends(get_current_user_optional)]
) -> str:
    """User dashboard route."""
    if current_user:
        return f"""
        <html>
            <head><title>Dashboard - FastAPI Laravel</title></head>
            <body>
                <h1>Dashboard - Welcome {current_user.name}</h1>
                <p>Email: {current_user.email}</p>
                <a href="/">Back to Home</a>
            </body>
        </html>
        """
    return """
    <html>
        <head><title>Login Required - FastAPI Laravel</title></head>
        <body>
            <h1>Please login to access dashboard</h1>
            <p><a href="/api/v1/auth/login">Login via API</a></p>
            <a href="/">Back to Home</a>
        </body>
    </html>
    """


# Route model binding example (Laravel-style)
@web_router.get("/users/{user_id:int}", response_class=HTMLResponse, name="users.show")
async def show_user(user_id: int) -> str:
    """Show user profile (route model binding example)."""
    return f"""
    <html>
        <head><title>User {user_id} - FastAPI Laravel</title></head>
        <body>
            <h1>User Profile - ID: {user_id}</h1>
            <p>This demonstrates Laravel-style route model binding.</p>
            <a href="/">Back to Home</a>
        </body>
    </html>
    """


# Resource route examples (Laravel-style)
@web_router.get("/posts", response_class=HTMLResponse, name="posts.index")
async def posts_index() -> str:
    """Posts index page."""
    return """
    <html>
        <head><title>Posts - FastAPI Laravel</title></head>
        <body>
            <h1>All Posts</h1>
            <p>This would display a list of blog posts.</p>
            <ul>
                <li><a href="/posts/1">Post 1</a></li>
                <li><a href="/posts/2">Post 2</a></li>
                <li><a href="/posts/3">Post 3</a></li>
            </ul>
            <a href="/">Back to Home</a>
        </body>
    </html>
    """


@web_router.get("/posts/{post_id:int}", response_class=HTMLResponse, name="posts.show")
async def posts_show(post_id: int) -> str:
    """Show single post."""
    return f"""
    <html>
        <head><title>Post {post_id} - FastAPI Laravel</title></head>
        <body>
            <h1>Post {post_id}</h1>
            <p>This would display the content of blog post {post_id}.</p>
            <a href="/posts">Back to Posts</a> | <a href="/">Back to Home</a>
        </body>
    </html>
    """


# Authentication Routes
@web_router.get("/login", response_class=HTMLResponse, name="login")
async def show_login_form(request: Request) -> HTMLResponse:
    """Show login form."""
    return await web_auth_controller.show_login_form(request)


@web_router.post("/login", name="login.post")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: Optional[str] = Form(None),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """Process login form."""
    return await web_auth_controller.login(request, email, password, remember, db)


@web_router.get("/register", response_class=HTMLResponse, name="register")
async def show_register_form(request: Request) -> HTMLResponse:
    """Show registration form."""
    return await web_auth_controller.show_register_form(request)


@web_router.post("/register", name="register.post")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirmation: str = Form(...),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """Process registration form."""
    return await web_auth_controller.register(request, name, email, password, password_confirmation, db)


@web_router.post("/logout", name="logout")
async def logout(request: Request) -> RedirectResponse:
    """Logout user."""
    return await web_auth_controller.logout(request)


@web_router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request) -> HTMLResponse:
    """Show user dashboard."""
    return await web_auth_controller.dashboard(request)


# MFA Routes
@web_router.get("/login/mfa", response_class=HTMLResponse, name="mfa.verify")
async def mfa_verification_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Show MFA verification page."""
    return await web_mfa_controller.mfa_verification_page(request, db)


@web_router.post("/login/mfa/verify", name="mfa.verify.post")
async def verify_mfa(
    request: Request,
    method: str = Form(...),
    code: Optional[str] = Form(None),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """Verify MFA during login."""
    return await web_mfa_controller.verify_mfa(request, method, code, db)


# Security Settings Routes
@web_router.get("/security", response_class=HTMLResponse, name="security")
async def security_settings(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Show security settings page."""
    return await web_mfa_controller.security_settings(request, db)


# TOTP Routes
@web_router.get("/security/mfa/setup-totp", response_class=HTMLResponse, name="totp.setup")
async def setup_totp(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Show TOTP setup page."""
    return await web_mfa_controller.setup_totp(request, db)


@web_router.post("/security/mfa/verify-totp-setup", name="totp.verify")
async def verify_totp_setup(
    request: Request,
    verification_code: str = Form(...),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """Verify TOTP setup."""
    return await web_mfa_controller.verify_totp_setup(request, verification_code, db)


@web_router.post("/security/mfa/disable-totp", name="totp.disable")
async def disable_totp(
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """Disable TOTP authentication."""
    return await web_mfa_controller.disable_totp(request, password, db)


# WebAuthn Routes
@web_router.get("/security/mfa/setup-webauthn", response_class=HTMLResponse, name="webauthn.setup")
async def setup_webauthn(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Show WebAuthn setup page."""
    return await web_mfa_controller.setup_webauthn(request, db)


@web_router.get("/security/mfa/webauthn/registration-options", name="webauthn.registration.options")
async def webauthn_registration_options(request: Request, db: Session = Depends(get_db)):
    """Generate WebAuthn registration options."""
    return await web_mfa_controller.webauthn_registration_options(request, db)


@web_router.post("/security/mfa/webauthn/registration-verify", name="webauthn.registration.verify")
async def webauthn_registration_verify(request: Request, db: Session = Depends(get_db)):
    """Verify WebAuthn registration."""
    return await web_mfa_controller.webauthn_registration_verify(request, db)


@web_router.get("/security/mfa/webauthn/authentication-options", name="webauthn.auth.options")
async def webauthn_authentication_options(request: Request, db: Session = Depends(get_db)):
    """Generate WebAuthn authentication options."""
    return await web_mfa_controller.webauthn_authentication_options(request, db)