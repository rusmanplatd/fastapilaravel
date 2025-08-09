from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.Services.AuthService import AuthService, auth_service
from app.Http.Middleware.SessionMiddleware import get_session
from app.Models.User import User
from config.database import get_db

templates = Jinja2Templates(directory="resources/views")


class WebAuthController:
    """Web authentication controller with session-based auth."""
    
    def __init__(self, auth_service: AuthService = auth_service):
        self.auth_service = auth_service
    
    async def show_login_form(self, request: Request) -> HTMLResponse:
        """Show login form."""
        session = request.session
        errors = session.pop('errors', {})
        old_input = session.pop('old_input', {})
        
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "errors": errors,
            "old": old_input,
            "title": "Login"
        })
    
    async def show_register_form(self, request: Request) -> HTMLResponse:
        """Show registration form."""
        session = request.session
        errors = session.pop('errors', {})
        old_input = session.pop('old_input', {})
        
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "errors": errors,
            "old": old_input,
            "title": "Register"
        })
    
    async def login(
        self,
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        remember: Optional[str] = Form(None),
        db: Session = Depends(get_db)
    ) -> RedirectResponse:
        """Process login form."""
        session = request.session
        
        try:
            # Attempt authentication
            result = await self.auth_service.authenticate(email, password, db)
            
            if not result.success or not result.user:
                session['errors'] = {'email': ['Invalid credentials']}
                session['old_input'] = {'email': email}
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            
            # Check if MFA is required
            from app.Services.MFAService import MFAService
            mfa_service = MFAService(db)
            user_mfa_status = mfa_service.get_mfa_status(result.user)
            
            if user_mfa_status['mfa_enabled']:
                # Store user in MFA challenge state
                session['mfa_user_id'] = result.user.id
                session['mfa_required'] = True
                return RedirectResponse(url="/login/mfa", status_code=status.HTTP_302_FOUND)
            
            # No MFA required, complete login
            session['user_id'] = result.user.id
            session['user_name'] = result.user.name
            session['user_email'] = result.user.email
            session['success'] = 'Welcome back!'
            
            # Redirect to dashboard
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
            
        except Exception as e:
            session['errors'] = {'email': [str(e)]}
            session['old_input'] = {'email': email}
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    async def register(
        self,
        request: Request,
        name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        password_confirmation: str = Form(...),
        db: Session = Depends(get_db)
    ) -> RedirectResponse:
        """Process registration form."""
        session = request.session
        
        # Basic validation
        errors: Dict[str, list[str]] = {}
        
        if len(name.strip()) < 2:
            errors['name'] = ['Name must be at least 2 characters']
        
        if '@' not in email or '.' not in email:
            errors['email'] = ['Please enter a valid email address']
        
        if len(password) < 8:
            errors['password'] = ['Password must be at least 8 characters']
        
        if password != password_confirmation:
            errors['password_confirmation'] = ['Password confirmation does not match']
        
        # Check if email exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            errors['email'] = ['Email address already in use']
        
        if errors:
            session['errors'] = errors
            session['old_input'] = {
                'name': name,
                'email': email
            }
            return RedirectResponse(url="/register", status_code=status.HTTP_302_FOUND)
        
        try:
            # Create user
            user_data = {
                'name': name.strip(),
                'email': email.lower().strip(),
                'password': password
            }
            
            result = await self.auth_service.register(user_data, db)
            
            if not result.success or not result.user:
                session['errors'] = {'email': ['Registration failed']}
                session['old_input'] = {
                    'name': name,
                    'email': email
                }
                return RedirectResponse(url="/register", status_code=status.HTTP_302_FOUND)
            
            # Auto-login after registration
            session['user_id'] = result.user.id
            session['user_name'] = result.user.name
            session['user_email'] = result.user.email
            session['success'] = 'Welcome! Your account has been created.'
            
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
            
        except Exception as e:
            session['errors'] = {'email': [str(e)]}
            session['old_input'] = {
                'name': name,
                'email': email
            }
            return RedirectResponse(url="/register", status_code=status.HTTP_302_FOUND)
    
    async def logout(self, request: Request) -> RedirectResponse:
        """Logout user."""
        session = request.session
        
        # Clear user session data
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session['success'] = 'You have been logged out successfully.'
        
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    async def dashboard(self, request: Request) -> HTMLResponse:
        """Show user dashboard."""
        session = request.session
        
        if not session.get('user_id'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        success_message = session.pop('success', None)
        
        return templates.TemplateResponse("auth/dashboard.html", {
            "request": request,
            "user": {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'email': session.get('user_email')
            },
            "success": success_message,
            "title": "Dashboard"
        })


# Create instance
web_auth_controller = WebAuthController()