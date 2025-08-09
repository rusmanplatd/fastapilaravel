from __future__ import annotations

from typing import Dict, Any, Optional, Union
from fastapi import Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.Services.MFAService import MFAService
from app.Services.TOTPService import TOTPService
from app.Services.WebAuthnService import WebAuthnService
from app.Models.User import User
from app.Models.UserMFASettings import UserMFASettings
from config.database import get_db
import json
import qrcode
import io
import base64
from PIL import Image

templates = Jinja2Templates(directory="resources/views")


class WebMFAController:
    """Web MFA controller for browser-based MFA functionality."""
    
    def __init__(self):
        pass
    
    async def security_settings(
        self, 
        request: Request,
        db: Session = Depends(get_db)
    ) -> HTMLResponse:
        """Show MFA security settings page."""
        session = request.session
        
        if not session.get('user_id'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Get user and MFA status
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        mfa_service = MFAService(db)
        mfa_status = mfa_service.get_mfa_status(user)
        
        success_message = session.pop('success', None)
        error_message = session.pop('error', None)
        
        return templates.TemplateResponse("auth/security.html", {
            "request": request,
            "user": {
                'id': user.id,
                'name': user.name,
                'email': user.email
            },
            "mfa_status": mfa_status,
            "success": success_message,
            "error": error_message,
            "title": "Security Settings"
        })
    
    async def setup_totp(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> HTMLResponse:
        """Show TOTP setup page."""
        session = request.session
        
        if not session.get('user_id'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        totp_service = TOTPService(db)
        setup_data = totp_service.setup_totp(user)
        
        # Generate QR code
        qr_code_data = self._generate_qr_code(setup_data['provisioning_uri'])
        
        return templates.TemplateResponse("auth/mfa/totp_setup.html", {
            "request": request,
            "user": {
                'id': user.id,
                'name': user.name,
                'email': user.email
            },
            "secret": setup_data['secret'],
            "qr_code": qr_code_data,
            "provisioning_uri": setup_data['provisioning_uri'],
            "title": "Setup TOTP Authenticator"
        })
    
    async def verify_totp_setup(
        self,
        request: Request,
        verification_code: str = Form(...),
        db: Session = Depends(get_db)
    ) -> RedirectResponse:
        """Verify TOTP setup with user-provided code."""
        session = request.session
        
        if not session.get('user_id'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        try:
            totp_service = TOTPService(db)
            result = totp_service.verify_totp_setup(user, verification_code)
            
            if result['success']:
                session['success'] = 'TOTP authenticator has been successfully set up!'
                return RedirectResponse(url="/security", status_code=status.HTTP_302_FOUND)
            else:
                session['error'] = result.get('message', 'Invalid verification code')
                return RedirectResponse(url="/security/mfa/setup-totp", status_code=status.HTTP_302_FOUND)
                
        except Exception as e:
            session['error'] = f'Setup failed: {str(e)}'
            return RedirectResponse(url="/security/mfa/setup-totp", status_code=status.HTTP_302_FOUND)
    
    async def disable_totp(
        self,
        request: Request,
        password: str = Form(...),
        db: Session = Depends(get_db)
    ) -> RedirectResponse:
        """Disable TOTP authentication."""
        session = request.session
        
        if not session.get('user_id'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Verify password before disabling
        from app.Services.AuthService import auth_service
        auth_result = await auth_service.authenticate(user.email, password, db)
        
        if not auth_result.success:
            session['error'] = 'Invalid password. TOTP not disabled.'
            return RedirectResponse(url="/security", status_code=status.HTTP_302_FOUND)
        
        try:
            totp_service = TOTPService(db)
            result = totp_service.disable_totp(user)
            
            if result['success']:
                session['success'] = 'TOTP authenticator has been disabled.'
            else:
                session['error'] = result.get('message', 'Failed to disable TOTP')
                
        except Exception as e:
            session['error'] = f'Failed to disable TOTP: {str(e)}'
        
        return RedirectResponse(url="/security", status_code=status.HTTP_302_FOUND)
    
    async def setup_webauthn(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> HTMLResponse:
        """Show WebAuthn setup page."""
        session = request.session
        
        if not session.get('user_id'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        return templates.TemplateResponse("auth/mfa/webauthn_setup.html", {
            "request": request,
            "user": {
                'id': user.id,
                'name': user.name,
                'email': user.email
            },
            "title": "Setup WebAuthn Security Key"
        })
    
    async def webauthn_registration_options(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> JSONResponse:
        """Generate WebAuthn registration options."""
        session = request.session
        
        if not session.get('user_id'):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Not authenticated"}
            )
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "User not found"}
            )
        
        try:
            webauthn_service = WebAuthnService(db)
            options = webauthn_service.generate_registration_options(user)
            
            # Store challenge in session for verification
            session['webauthn_challenge'] = options['challenge']
            
            return JSONResponse(content=options)
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Failed to generate options: {str(e)}"}
            )
    
    async def webauthn_registration_verify(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> JSONResponse:
        """Verify WebAuthn registration response."""
        session = request.session
        
        if not session.get('user_id'):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Not authenticated"}
            )
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "User not found"}
            )
        
        challenge = session.get('webauthn_challenge')
        if not challenge:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "No active registration challenge"}
            )
        
        try:
            body = await request.json()
            webauthn_service = WebAuthnService(db)
            
            result = webauthn_service.verify_registration_response(
                user, 
                body, 
                challenge
            )
            
            if result['success']:
                # Clear challenge from session
                session.pop('webauthn_challenge', None)
                session['success'] = 'Security key has been successfully registered!'
                
                return JSONResponse(content={
                    "success": True,
                    "message": "WebAuthn registration successful",
                    "credential_id": result.get('credential_id')
                })
            else:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": result.get('message', 'Registration failed')}
                )
                
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Registration verification failed: {str(e)}"}
            )
    
    async def webauthn_authentication_options(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> JSONResponse:
        """Generate WebAuthn authentication options."""
        session = request.session
        
        if not session.get('user_id'):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Not authenticated"}
            )
        
        user = db.query(User).filter(User.id == session.get('user_id')).first()
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "User not found"}
            )
        
        try:
            webauthn_service = WebAuthnService(db)
            options = webauthn_service.generate_authentication_options(user)
            
            # Store challenge in session for verification
            session['webauthn_auth_challenge'] = options['challenge']
            
            return JSONResponse(content=options)
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Failed to generate options: {str(e)}"}
            )
    
    async def mfa_verification_page(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> HTMLResponse:
        """Show MFA verification page during login."""
        session = request.session
        
        # Check if user is in MFA challenge state
        if not session.get('mfa_user_id') or not session.get('mfa_required'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        user = db.query(User).filter(User.id == session.get('mfa_user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        mfa_service = MFAService(db)
        mfa_status = mfa_service.get_mfa_status(user)
        
        errors = session.pop('errors', {})
        
        return templates.TemplateResponse("auth/mfa/verify.html", {
            "request": request,
            "user": {
                'id': user.id,
                'name': user.name,
                'email': user.email
            },
            "mfa_status": mfa_status,
            "errors": errors,
            "title": "Multi-Factor Authentication"
        })
    
    async def verify_mfa(
        self,
        request: Request,
        method: str = Form(...),
        code: Optional[str] = Form(None),
        db: Session = Depends(get_db)
    ) -> RedirectResponse:
        """Verify MFA during login flow."""
        session = request.session
        
        if not session.get('mfa_user_id') or not session.get('mfa_required'):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        user = db.query(User).filter(User.id == session.get('mfa_user_id')).first()
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        try:
            mfa_service = MFAService(db)
            
            if method == 'totp':
                if not code:
                    session['errors'] = {'code': ['TOTP code is required']}
                    return RedirectResponse(url="/login/mfa", status_code=status.HTTP_302_FOUND)
                
                result = mfa_service.verify_totp(user, code)
            
            elif method == 'webauthn':
                # WebAuthn verification will be handled via JavaScript/AJAX
                result = {'success': True}
            
            else:
                session['errors'] = {'method': ['Invalid MFA method']}
                return RedirectResponse(url="/login/mfa", status_code=status.HTTP_302_FOUND)
            
            if result['success']:
                # Complete login
                session.pop('mfa_user_id', None)
                session.pop('mfa_required', None)
                session['user_id'] = user.id
                session['user_name'] = user.name
                session['user_email'] = user.email
                session['success'] = 'Welcome back!'
                
                return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
            else:
                session['errors'] = {'code': [result.get('message', 'Invalid code')]}
                return RedirectResponse(url="/login/mfa", status_code=status.HTTP_302_FOUND)
                
        except Exception as e:
            session['errors'] = {'code': [f'Verification failed: {str(e)}']}
            return RedirectResponse(url="/login/mfa", status_code=status.HTTP_302_FOUND)
    
    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """Generate QR code as base64 encoded image."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"


# Create instance
web_mfa_controller = WebMFAController()