from __future__ import annotations

"""
Social Authentication Routes - Laravel Socialite Style

Routes for social OAuth authentication with multiple providers including
GitHub, Google, Facebook, Twitter, LinkedIn, and Discord.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse

from app.Http.Controllers.SocialAuthController import SocialAuthController

router = APIRouter(prefix="/auth", tags=["Social Authentication"])

# Initialize controller
social_controller = SocialAuthController()


@router.get("/providers")
async def get_supported_providers():
    """Get list of supported and configured social providers."""
    return social_controller.get_supported_providers()


@router.get("/{provider}")
async def redirect_to_provider(provider: str, request: Request):
    """
    Redirect to social provider for authentication.
    
    Args:
        provider: Provider name (github, google, facebook, twitter, linkedin, discord)
        request: FastAPI request object
        
    Returns:
        Redirect response to OAuth provider
    """
    return await social_controller.redirect_to_provider(provider, request)


@router.get("/{provider}/callback")
async def handle_provider_callback(provider: str, request: Request):
    """
    Handle OAuth callback from social provider.
    
    Args:
        provider: Provider name
        request: FastAPI request object
        
    Returns:
        Authentication response with user data and access token
    """
    return await social_controller.handle_provider_callback(provider, request)


# Specific provider routes for clarity (optional)
@router.get("/github")
async def github_login(request: Request):
    """Redirect to GitHub for authentication."""
    return await social_controller.redirect_to_provider("github", request)


@router.get("/github/callback")
async def github_callback(request: Request):
    """Handle GitHub OAuth callback."""
    return await social_controller.handle_provider_callback("github", request)


@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google for authentication."""
    return await social_controller.redirect_to_provider("google", request)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    return await social_controller.handle_provider_callback("google", request)


@router.get("/facebook")
async def facebook_login(request: Request):
    """Redirect to Facebook for authentication."""
    return await social_controller.redirect_to_provider("facebook", request)


@router.get("/facebook/callback")
async def facebook_callback(request: Request):
    """Handle Facebook OAuth callback."""
    return await social_controller.handle_provider_callback("facebook", request)


@router.get("/twitter")
async def twitter_login(request: Request):
    """Redirect to Twitter for authentication."""
    return await social_controller.redirect_to_provider("twitter", request)


@router.get("/twitter/callback")
async def twitter_callback(request: Request):
    """Handle Twitter OAuth callback."""
    return await social_controller.handle_provider_callback("twitter", request)


@router.get("/linkedin")
async def linkedin_login(request: Request):
    """Redirect to LinkedIn for authentication."""
    return await social_controller.redirect_to_provider("linkedin", request)


@router.get("/linkedin/callback")
async def linkedin_callback(request: Request):
    """Handle LinkedIn OAuth callback."""
    return await social_controller.handle_provider_callback("linkedin", request)


@router.get("/discord")
async def discord_login(request: Request):
    """Redirect to Discord for authentication."""
    return await social_controller.redirect_to_provider("discord", request)


@router.get("/discord/callback")  
async def discord_callback(request: Request):
    """Handle Discord OAuth callback."""
    return await social_controller.handle_provider_callback("discord", request)