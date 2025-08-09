from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from typing import Dict, Any
from app.Http.Controllers import get_current_user
from app.Models import User
from typing_extensions import Annotated

"""
Laravel-style Web Routes.

Here is where you can register web routes for your application. These
routes are loaded by the RouteServiceProvider within a group which
contains the "web" middleware group. Now create something great!
"""

web_router = APIRouter()


@web_router.get("/", response_class=HTMLResponse, name="home")
async def home() -> str:
    """Welcome page route."""
    return """
    <html>
        <head><title>FastAPI Laravel</title></head>
        <body>
            <h1>Welcome to FastAPI with Laravel Structure</h1>
            <p>This application follows Laravel conventions and patterns.</p>
            <ul>
                <li><a href="/about">About</a></li>
                <li><a href="/contact">Contact</a></li>
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="/docs">API Documentation</a></li>
            </ul>
        </body>
    </html>
    """


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