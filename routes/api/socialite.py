from __future__ import annotations

"""
Social Authentication Routes - Laravel Socialite Style

Routes for social OAuth authentication with multiple providers including
GitHub, Google, Facebook, Twitter, LinkedIn, and Discord.
"""

from typing import Dict, Any, Annotated
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.Http.Controllers.Api.SocialAuthController import SocialAuthController
from config.database import get_db

router = APIRouter(prefix="/auth", tags=["Social Authentication"])


@router.get("/providers")
async def get_supported_providers(db: Annotated[Session, Depends(get_db)]) -> Dict[str, Any]:
    """Get list of supported and configured social providers."""
    social_controller = SocialAuthController(db)
    return social_controller.get_supported_providers()


@router.get("/{provider}")
async def redirect_to_provider(provider: str, request: Request, db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    """
    Redirect to social provider for authentication.
    
    Args:
        provider: Provider name (github, google, facebook, twitter, linkedin, discord)
        request: FastAPI request object
        
    Returns:
        Redirect response to OAuth provider
    """
    social_controller = SocialAuthController(db)
    return await social_controller.redirect_to_provider(provider, request)


@router.get("/{provider}/callback")
async def handle_provider_callback(provider: str, request: Request, db: Annotated[Session, Depends(get_db)]) -> Dict[str, Any]:
    """
    Handle OAuth callback from social provider.
    
    Args:
        provider: Provider name
        request: FastAPI request object
        
    Returns:
        Authentication response with user data and access token
    """
    social_controller = SocialAuthController(db)
    return await social_controller.handle_provider_callback(provider, request)