"""OAuth2 Consent Controller - Google IDP Style

This controller handles OAuth2 consent screen functionality similar to Google's
authorization flow with proper scope display and user consent management.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Union, cast
from typing_extensions import Annotated
from fastapi import HTTPException, Depends, status
from starlette.requests import Request
from fastapi.param_functions import Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import urllib.parse

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
from app.Models.User import User
from app.Http.Middleware.OAuth2Middleware import get_current_user_from_token as get_current_user
from config.database import get_db_session

templates = Jinja2Templates(directory="resources/views")


class OAuth2ConsentController(BaseController):
    """Controller for OAuth2 consent screen operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth_service = OAuth2AuthServerService()
    
    def _get_scope_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Get Google-style scope descriptions."""
        return {
            "openid": {
                "title": "Verify your identity",
                "description": "Confirm your identity and grant access to your basic profile information",
                "icon": "user"
            },
            "profile": {
                "title": "See your personal info",
                "description": "See your personal info, including any personal info you've made publicly available",
                "icon": "profile"
            },
            "email": {
                "title": "See your primary email address",
                "description": "See your primary email address and confirm it's verified",
                "icon": "email"
            },
            "phone": {
                "title": "See your phone number",
                "description": "See your phone number and confirm it's verified",
                "icon": "phone"
            },
            "address": {
                "title": "See your address",
                "description": "See your street address, country, and postal code",
                "icon": "location"
            },
            "offline_access": {
                "title": "Maintain access to your data",
                "description": "Maintain access to your data while you're offline",
                "icon": "refresh"
            },
            "read": {
                "title": "Read access to your data",
                "description": "View your data and information",
                "icon": "read"
            },
            "write": {
                "title": "Modify your data",
                "description": "Create, edit, and delete your data",
                "icon": "write"
            },
            "admin": {
                "title": "Administrative access",
                "description": "Full administrative access to manage your account and data",
                "icon": "admin"
            }
        }
    
    def _parse_scopes(self, scope_string: Optional[str]) -> List[str]:
        """Parse scope string into list of scopes."""
        if not scope_string:
            return []
        return [s.strip() for s in scope_string.split() if s.strip()]
    
    async def show_consent(
        self,
        request: Request,
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(get_current_user)],
        client_id: str = "",
        redirect_uri: str = "",
        response_type: str = "code",
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None,
        display: Optional[str] = None,
        max_age: Optional[int] = None,
        ui_locales: Optional[str] = None,
        id_token_hint: Optional[str] = None,
        login_hint: Optional[str] = None,
        acr_values: Optional[str] = None
    ) -> Union[HTMLResponse, RedirectResponse, JSONResponse]:
        """
        Show OAuth2 consent screen (Google IDP style).
        
        Args:
            request: FastAPI request object
            db: Database session
            current_user: Authenticated user
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI after authorization
            response_type: OAuth2 response type
            scope: Requested scopes
            state: State parameter for CSRF protection
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
            nonce: OpenID Connect nonce
            prompt: OpenID Connect prompt parameter
            display: Display hint
            max_age: Maximum authentication age
            ui_locales: UI locales
            id_token_hint: ID token hint
            login_hint: Login hint
            acr_values: Authentication context class reference values
        
        Returns:
            HTML consent screen
        """
        try:
            # Validate client
            client = db.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.is_active == True
            ).first()
            
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid client"
                )
            
            # Validate redirect URI
            allowed_redirect_uris = client.get_redirect_uris()
            if redirect_uri not in allowed_redirect_uris:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid redirect URI"
                )
            
            # Parse and validate scopes
            requested_scopes = self._parse_scopes(scope)
            client_scopes = client.get_allowed_scopes()
            
            # Filter scopes to only those allowed by client
            valid_scopes = [s for s in requested_scopes if s in client_scopes]
            
            # Get scope descriptions
            scope_descriptions = self._get_scope_descriptions()
            scope_details = []
            
            for scope_name in valid_scopes:
                if scope_name in scope_descriptions:
                    scope_details.append({
                        "name": scope_name,
                        **scope_descriptions[scope_name]
                    })
                else:
                    # Fallback for unknown scopes
                    scope_details.append({
                        "name": scope_name,
                        "title": scope_name.replace("_", " ").title(),
                        "description": f"Access to {scope_name} functionality",
                        "icon": "default"
                    })
            
            # Check if user has previously consented to this client
            # For now, always show consent screen (like Google with prompt=consent)
            show_consent_screen = True
            
            if prompt == "none":
                # Immediate response required - no consent screen
                show_consent_screen = False
            elif prompt == "consent":
                # Force consent screen
                show_consent_screen = True
            
            # Prepare consent screen context
            context = {
                "request": request,
                "user": current_user,
                "client": client,
                "client_name": client.name,
                "client_logo": getattr(client, "logo_uri", None),
                "client_uri": getattr(client, "client_uri", None),
                "policy_uri": getattr(client, "policy_uri", None),
                "tos_uri": getattr(client, "tos_uri", None),
                "scopes": scope_details,
                "scope_count": len(scope_details),
                "authorization_params": {
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "response_type": response_type,
                    "scope": scope,
                    "state": state,
                    "code_challenge": code_challenge,
                    "code_challenge_method": code_challenge_method,
                    "nonce": nonce,
                    "prompt": prompt,
                    "display": display,
                    "max_age": max_age,
                    "ui_locales": ui_locales,
                    "id_token_hint": id_token_hint,
                    "login_hint": login_hint,
                    "acr_values": acr_values
                },
                "show_advanced": len([s for s in valid_scopes if s in ["admin", "write", "offline_access"]]) > 0
            }
            
            if not show_consent_screen and prompt == "none":
                # Auto-approve for immediate response
                auth_params = cast(Dict[str, Any], context["authorization_params"])
                # Create form-like parameters for auto-approval
                form_params = {
                    "action": "allow",
                    "client_id": auth_params.get("client_id", ""),
                    "redirect_uri": auth_params.get("redirect_uri", ""),
                    "response_type": auth_params.get("response_type", "code"),
                    "scope": auth_params.get("scope"),
                    "state": auth_params.get("state"),
                    "code_challenge": auth_params.get("code_challenge"),
                    "code_challenge_method": auth_params.get("code_challenge_method"),
                    "nonce": auth_params.get("nonce"),
                    "prompt": auth_params.get("prompt")
                }
                return await self._handle_consent_internal(
                    request=request,
                    db=db,
                    current_user=current_user,
                    **form_params
                )
            
            return templates.TemplateResponse(
                "oauth/consent.html",
                context
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to show consent screen: {str(e)}"
            )
    
    async def handle_consent(
        self,
        request: Request,
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(get_current_user)],
        action: str = Form(...),
        client_id: str = Form(...),
        redirect_uri: str = Form(...),
        response_type: str = Form(default="code"),
        scope: Optional[str] = Form(default=None),
        state: Optional[str] = Form(default=None),
        code_challenge: Optional[str] = Form(default=None),
        code_challenge_method: Optional[str] = Form(default=None),
        nonce: Optional[str] = Form(default=None),
        prompt: Optional[str] = Form(default=None),
        display: Optional[str] = Form(default=None),
        max_age: Optional[int] = Form(default=None),
        ui_locales: Optional[str] = Form(default=None),
    ) -> Union[RedirectResponse, JSONResponse]:
        """Handle consent form submission (with Form parameters)."""
        return await self._handle_consent_internal(
            request=request,
            db=db,
            current_user=current_user,
            action=action,
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
            prompt=prompt,
            display=display,
            max_age=max_age,
            ui_locales=ui_locales,
        )

    async def _handle_consent_internal(
        self,
        request: Request,
        db: Session,
        current_user: User,
        action: str,
        client_id: str,
        redirect_uri: str,
        response_type: str = "code",
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None,
        display: Optional[str] = None,
        max_age: Optional[int] = None,
        ui_locales: Optional[str] = None,
        id_token_hint: Optional[str] = None,
        login_hint: Optional[str] = None,
        acr_values: Optional[str] = None
    ) -> Union[RedirectResponse, JSONResponse]:
        """
        Handle user consent response.
        
        Args:
            request: FastAPI request object
            db: Database session
            current_user: Authenticated user
            action: User action ("allow" or "deny")
            ... (other OAuth2 parameters)
        
        Returns:
            Redirect response to client or error page
        """
        try:
            # Validate client
            client = db.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.is_active == True
            ).first()
            
            if not client:
                return self._create_error_redirect(
                    redirect_uri,
                    "invalid_client",
                    "Invalid client identifier",
                    state
                )
            
            # Check user action
            if action.lower() == "deny":
                return self._create_error_redirect(
                    redirect_uri,
                    "access_denied",
                    "The user denied the request",
                    state
                )
            
            if action.lower() != "allow":
                return self._create_error_redirect(
                    redirect_uri,
                    "invalid_request",
                    "Invalid action parameter",
                    state
                )
            
            # Generate authorization code
            auth_response = self.oauth_service.create_authorization_code(
                db=db,
                client=client,
                user=current_user,
                redirect_uri=redirect_uri,
                scopes=scope.split(' ') if scope else [],
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                nonce=nonce
            )
            
            # Build redirect URL
            redirect_params = {
                "code": auth_response.code_id,
                "state": state
            }
            
            # Remove None values
            redirect_params = {k: v for k, v in redirect_params.items() if v is not None}
            
            # Create redirect URL
            parsed_url = urllib.parse.urlparse(redirect_uri)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            # Convert redirect_params to list format to match parse_qs format
            redirect_params_list = {k: [v] for k, v in redirect_params.items() if v is not None}
            query_params.update(redirect_params_list)
            
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            redirect_url = urllib.parse.urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            return RedirectResponse(url=redirect_url, status_code=302)
            
        except HTTPException as e:
            return self._create_error_redirect(
                redirect_uri,
                "server_error",
                str(getattr(e, 'detail', str(e))),
                state
            )
        except Exception as e:
            return self._create_error_redirect(
                redirect_uri,
                "server_error",
                f"Authorization failed: {str(e)}",
                state
            )
    
    def _create_error_redirect(
        self,
        redirect_uri: str,
        error: str,
        error_description: str,
        state: Optional[str] = None
    ) -> RedirectResponse:
        """Create error redirect response."""
        error_params = {
            "error": error,
            "error_description": error_description
        }
        
        if state:
            error_params["state"] = state
        
        # Create error redirect URL
        parsed_url = urllib.parse.urlparse(redirect_uri)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        # Convert error_params values to lists to match parse_qs format
        error_params_list = {k: [v] for k, v in error_params.items()}
        query_params.update(error_params_list)
        
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        error_url = urllib.parse.urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return RedirectResponse(url=error_url, status_code=302)