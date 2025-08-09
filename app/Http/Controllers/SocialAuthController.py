from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse

from app.Socialite import Socialite
from app.Models.User import User
from app.Services.AuthService import AuthService
from config.socialite import SOCIAL_PROVIDERS, SOCIALITE_SETTINGS
from .BaseController import BaseController


class SocialAuthController(BaseController):
    """
    Social Authentication Controller similar to Laravel Socialite controllers.
    
    Handles OAuth redirects and callbacks for social login providers.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.auth_service = AuthService()
        # Configure Socialite with provider settings
        Socialite.set_config(SOCIAL_PROVIDERS)
    
    async def redirect_to_provider(self, provider: str, request: Request) -> RedirectResponse:
        """
        Redirect user to social provider for authentication.
        
        Args:
            provider: Social provider name (github, google, etc.)
            request: FastAPI request object
            
        Returns:
            Redirect response to provider's OAuth page
        """
        try:
            social_provider = Socialite.driver(provider)
            redirect_url = social_provider.redirect(request)
            return RedirectResponse(url=redirect_url, status_code=302)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def handle_provider_callback(
        self, 
        provider: str, 
        request: Request
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback from social provider.
        
        Args:
            provider: Social provider name
            request: FastAPI request object
            
        Returns:
            Authentication response with token or user data
        """
        try:
            # Check for OAuth error
            error = request.query_params.get('error')
            if error:
                error_description = request.query_params.get('error_description', error)
                raise HTTPException(status_code=400, detail=f"OAuth error: {error_description}")
            
            # Get user from provider
            social_provider = Socialite.driver(provider)
            social_user = await social_provider.user(request)
            
            # Find or create user
            user = await self._find_or_create_user(social_user, provider)
            
            # Generate authentication token
            token_data = await self.auth_service.create_access_token(user.id)
            
            return {
                'message': 'Social authentication successful',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'provider': provider,
                    'provider_id': social_user.id,
                    'avatar': social_user.avatar,
                },
                'access_token': token_data['access_token'],
                'token_type': 'Bearer',
                'expires_in': token_data['expires_in'],
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Social authentication failed: {str(e)}")
    
    async def _find_or_create_user(self, social_user: Any, provider: str) -> User:
        """
        Find existing user or create new one from social data.
        
        Args:
            social_user: Social user data from provider
            provider: Provider name
            
        Returns:
            User instance
        """
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        from config.database import DATABASE_URL
        
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        
        async with SessionLocal() as db:
            user = None
            
            # First try to find user by provider ID
            if hasattr(User, f'{provider}_id'):
                user = db.query(User).filter(
                    getattr(User, f'{provider}_id') == social_user.id
                ).first()
            
            # Try to find by email if auto-linking is enabled
            if not user and social_user.email and SOCIALITE_SETTINGS.get('auto_link_users'):
                user = db.query(User).filter(User.email == social_user.email).first()
                
                # Link the social account to existing user
                if user and hasattr(User, f'{provider}_id'):
                    setattr(user, f'{provider}_id', social_user.id)
                    if social_user.avatar and hasattr(User, 'avatar'):
                        setattr(user, 'avatar', social_user.avatar)
                    db.commit()
            
            # Create new user if not found and auto-creation is enabled
            if not user and SOCIALITE_SETTINGS.get('auto_create_users'):
                user_data = {
                    'name': social_user.name or social_user.nickname or f'User {social_user.id}',
                    'email': social_user.email,
                    'email_verified_at': 'now()',  # Social accounts are considered verified
                }
                
                # Set provider-specific fields
                if hasattr(User, f'{provider}_id'):
                    user_data[f'{provider}_id'] = social_user.id
                
                if social_user.avatar and hasattr(User, 'avatar'):
                    user_data['avatar'] = social_user.avatar
                
                user = User(**user_data)
                db.add(user)
                db.commit()
                db.refresh(user)
                
                # Assign default role if specified
                default_role = SOCIALITE_SETTINGS.get('default_user_role')
                if default_role:
                    await self._assign_default_role(user, default_role, db)
            
            if not user:
                raise HTTPException(
                    status_code=400, 
                    detail="User not found and auto-creation is disabled"
                )
            
            return user
    
    async def _assign_default_role(self, user: User, role_name: str, db: Any) -> None:
        """Assign default role to new social user."""
        try:
            from app.Models.Role import Role
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                user.roles.append(role)
                db.commit()
        except Exception:
            # Ignore role assignment errors for now
            pass
    
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get list of supported and configured providers."""
        from config.socialite import get_configured_providers
        
        configured_providers = get_configured_providers()
        all_providers = Socialite.get_supported_providers()
        
        return {
            'supported': all_providers,
            'configured': configured_providers,
            'available_for_login': configured_providers,
        }