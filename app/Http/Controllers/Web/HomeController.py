from __future__ import annotations

from typing import Dict, Any
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.Http.Controllers.BaseController import BaseController


class HomeController(BaseController):
    """
    Home Controller.
    
    Handles the home page and basic application routes,
    similar to Laravel's HomeController.
    """
    
    def __init__(self) -> None:
        super().__init__()
    
    async def index(self, request: Request) -> HTMLResponse:
        """
        Show the application homepage.
        
        @param request: The HTTP request
        @return: The homepage HTML response
        """
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FastAPI Laravel</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .links a { display: inline-block; margin: 10px 15px 10px 0; padding: 8px 16px; 
                         background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
                .links a:hover { background: #0056b3; }
                .features li { margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 FastAPI with Laravel Architecture</h1>
                <p class="lead">A powerful FastAPI application built with Laravel conventions and patterns.</p>
                
                <div class="card">
                    <h2>🏗️ Architecture Features</h2>
                    <ul class="features">
                        <li><strong>Laravel-style MVC:</strong> Controllers, Services, Models with proper separation</li>
                        <li><strong>Service Providers:</strong> Dependency injection and service container</li>
                        <li><strong>Eloquent-style Models:</strong> Active Record pattern with relationships</li>
                        <li><strong>Middleware Stack:</strong> Laravel-like HTTP kernel and middleware groups</li>
                        <li><strong>Form Requests:</strong> Validation with authorization</li>
                        <li><strong>Broadcasting:</strong> Real-time events and WebSocket support</li>
                        <li><strong>Queue System:</strong> Background job processing</li>
                        <li><strong>OAuth2 Server:</strong> Complete authentication system</li>
                    </ul>
                </div>
                
                <div class="card">
                    <h2>🔗 Quick Links</h2>
                    <div class="links">
                        <a href="/about">About</a>
                        <a href="/contact">Contact</a>
                        <a href="/dashboard">Dashboard</a>
                        <a href="/docs">API Docs</a>
                        <a href="/api/v1/">API</a>
                        <a href="/posts">Posts</a>
                    </div>
                </div>
                
                <div class="card">
                    <h2>⚡ Development Tools</h2>
                    <div class="links">
                        <a href="/monitoring/dashboard">Monitoring</a>
                        <a href="/monitoring/health">Health Check</a>
                        <a href="/.well-known/oauth-authorization-server">OAuth2 Metadata</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)
    
    async def about(self, request: Request) -> HTMLResponse:
        """
        Show the about page.
        
        @param request: The HTTP request
        @return: The about page HTML response  
        """
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>About - FastAPI Laravel</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .back-link { display: inline-block; margin-top: 20px; color: #007bff; text-decoration: none; }
                .back-link:hover { text-decoration: underline; }
                .tech-stack { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
                .tech-item { background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📖 About FastAPI Laravel</h1>
                
                <div class="card">
                    <h2>🎯 Project Vision</h2>
                    <p>This project demonstrates how to build a FastAPI application using Laravel's elegant patterns and conventions. 
                    It combines the speed and modern Python features of FastAPI with the mature architectural patterns of Laravel.</p>
                </div>
                
                <div class="card">
                    <h2>🛠️ Technology Stack</h2>
                    <div class="tech-stack">
                        <div class="tech-item">
                            <strong>FastAPI</strong><br>
                            High-performance async web framework
                        </div>
                        <div class="tech-item">
                            <strong>SQLAlchemy</strong><br>
                            Powerful ORM with Eloquent-style patterns  
                        </div>
                        <div class="tech-item">
                            <strong>Pydantic</strong><br>
                            Data validation and serialization
                        </div>
                        <div class="tech-item">
                            <strong>JWT & OAuth2</strong><br>
                            Secure authentication system
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🏛️ Laravel-Inspired Architecture</h2>
                    <ul>
                        <li><strong>Application Foundation:</strong> Laravel-style app container and service providers</li>
                        <li><strong>HTTP Kernel:</strong> Middleware stack management like Laravel</li>
                        <li><strong>Route Groups:</strong> Organized routing with middleware groups</li>
                        <li><strong>Eloquent Models:</strong> Active Record pattern with relationships</li>
                        <li><strong>Form Requests:</strong> Validation with authorization logic</li>
                        <li><strong>Service Container:</strong> Dependency injection and binding</li>
                        <li><strong>Event System:</strong> Event dispatching and listeners</li>
                        <li><strong>Queue System:</strong> Background job processing</li>
                    </ul>
                </div>
                
                <a href="/" class="back-link">← Back to Home</a>
            </div>
        </body>
        </html>
        """)
    
    async def contact(self, request: Request) -> HTMLResponse:
        """
        Show the contact page.
        
        @param request: The HTTP request
        @return: The contact page HTML response
        """  
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact - FastAPI Laravel</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 600px; margin: 0 auto; }
                .card { background: #f8f9fa; padding: 30px; border-radius: 8px; text-align: center; }
                .back-link { display: inline-block; margin-top: 20px; color: #007bff; text-decoration: none; }
                .back-link:hover { text-decoration: underline; }
                .contact-info { text-align: left; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>📞 Contact Us</h1>
                    <p>Get in touch with the FastAPI Laravel team!</p>
                    
                    <div class="contact-info">
                        <h3>📧 Project Information</h3>
                        <p><strong>GitHub:</strong> FastAPI Laravel Architecture</p>
                        <p><strong>Documentation:</strong> Available at /docs</p>
                        <p><strong>API:</strong> RESTful API at /api/v1/</p>
                        
                        <h3>🚀 Features</h3>
                        <ul>
                            <li>OAuth2 Authentication Server</li>
                            <li>Real-time Broadcasting</li>
                            <li>Background Queue Processing</li>
                            <li>Comprehensive Monitoring</li>
                        </ul>
                    </div>
                    
                    <a href="/" class="back-link">← Back to Home</a>
                </div>
            </div>
        </body>
        </html>
        """)
    
    async def dashboard(self, request: Request) -> Dict[str, Any]:
        """
        Show the dashboard (API response).
        
        @param request: The HTTP request
        @return: Dashboard data
        """
        return {
            "message": "Dashboard data",
            "user": getattr(request.state, 'user', None),
            "timestamp": "2025-08-14T00:00:00Z"
        }