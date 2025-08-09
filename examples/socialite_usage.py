#!/usr/bin/env python3
"""
Laravel Socialite Usage Examples

This script demonstrates how to use the Laravel Socialite implementation
for social authentication in FastAPI applications.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.middleware.sessions import SessionMiddleware

# Import Socialite components
from app.Socialite import Socialite, SocialiteManager
from app.Socialite.Providers import GitHubProvider, GoogleProvider
from config.socialite import SOCIAL_PROVIDERS


async def basic_socialite_usage():
    """Basic Socialite usage examples."""
    
    print("=== Laravel Socialite Usage Examples ===\n")
    
    # 1. Configure Socialite
    print("1. Configuring Socialite with providers...")
    Socialite.set_config(SOCIAL_PROVIDERS)
    
    # Check supported providers
    providers = Socialite.get_supported_providers()
    print(f"   Supported providers: {providers}")
    
    configured = [p for p in providers if Socialite.is_configured(p)]
    print(f"   Configured providers: {configured}")
    
    # 2. Get provider instance
    print("\n2. Getting GitHub provider...")
    try:
        github = Socialite.driver('github')
        print(f"   GitHub provider: {github.__class__.__name__}")
        print(f"   Client ID: {github.client_id[:8]}...")
        print(f"   Redirect URI: {github.redirect_uri}")
        print(f"   Scopes: {github.scopes}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Customize provider settings
    print("\n3. Customizing provider settings...")
    try:
        github = (Socialite.driver('github')
                 .set_scopes(['user:email', 'read:user'])
                 .with_parameters({'allow_signup': 'true'}))
        print(f"   Updated scopes: {github.scopes}")
        print(f"   Custom parameters: {github.parameters}")
    except Exception as e:
        print(f"   Error: {e}")


async def custom_provider_example():
    """Example of creating a custom social provider."""
    
    print("\n=== Custom Provider Example ===\n")
    
    from app.Socialite.Providers.AbstractProvider import AbstractProvider
    from app.Socialite.Contracts import User
    
    class CustomProvider(AbstractProvider):
        """Example custom OAuth provider."""
        
        def get_auth_endpoint(self) -> str:
            return 'https://example.com/oauth/authorize'
        
        def get_token_endpoint(self) -> str:
            return 'https://example.com/oauth/token'
        
        def get_user_endpoint(self) -> str:
            return 'https://api.example.com/user'
        
        def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
            return User(
                id=user_data['id'],
                name=user_data.get('name'),
                email=user_data.get('email'),
                avatar=user_data.get('avatar_url'),
                raw=user_data
            )
    
    # Register custom provider
    Socialite.extend('custom', CustomProvider)
    
    print("   Custom provider registered successfully!")
    print(f"   Updated providers: {Socialite.get_supported_providers()}")


def fastapi_integration_example():
    """Example of integrating Socialite with FastAPI."""
    
    print("\n=== FastAPI Integration Example ===\n")
    
    app = FastAPI(title="Social Auth Demo")
    app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
    
    # Configure Socialite
    Socialite.set_config(SOCIAL_PROVIDERS)
    
    @app.get("/login/{provider}")
    async def login(provider: str, request: Request):
        """Redirect to social provider."""
        try:
            social_provider = Socialite.driver(provider)
            redirect_url = social_provider.redirect(request)
            return {"redirect_url": redirect_url}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/callback/{provider}")
    async def callback(provider: str, request: Request):
        """Handle OAuth callback."""
        try:
            social_provider = Socialite.driver(provider)
            user = await social_provider.user(request)
            return {
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "avatar": user.avatar,
                    "provider": provider
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    print("   FastAPI app configured with social auth routes:")
    print("   - GET /login/{provider} - Redirect to provider")
    print("   - GET /callback/{provider} - Handle callback")


async def advanced_features_example():
    """Example of advanced Socialite features."""
    
    print("\n=== Advanced Features Example ===\n")
    
    # 1. Stateless authentication (not recommended for production)
    print("1. Stateless authentication...")
    try:
        github = Socialite.driver('github').stateless()
        print("   ✓ State verification disabled")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Custom scopes and parameters
    print("\n2. Custom scopes and parameters...")
    try:
        github = (Socialite.driver('github')
                 .set_scopes(['user:email', 'read:user', 'public_repo'])
                 .with_parameters({
                     'allow_signup': 'true',
                     'login': 'suggested_username'
                 }))
        print(f"   ✓ Scopes: {github.scopes}")
        print(f"   ✓ Parameters: {github.parameters}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Multiple provider configurations
    print("\n3. Multiple provider management...")
    manager = SocialiteManager({
        'github': {
            'client_id': 'github_client_id',
            'client_secret': 'github_secret',
            'redirect_uri': 'http://localhost:8000/auth/github/callback'
        },
        'google': {
            'client_id': 'google_client_id', 
            'client_secret': 'google_secret',
            'redirect_uri': 'http://localhost:8000/auth/google/callback'
        }
    })
    
    print(f"   ✓ Configured providers: {list(manager.config.keys())}")


def environment_setup_example():
    """Example of environment setup for social providers."""
    
    print("\n=== Environment Setup Example ===\n")
    
    example_env = """
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Facebook OAuth
FACEBOOK_CLIENT_ID=your_facebook_app_id
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret
FACEBOOK_REDIRECT_URI=http://localhost:8000/auth/facebook/callback

# Twitter OAuth 2.0
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
TWITTER_REDIRECT_URI=http://localhost:8000/auth/twitter/callback

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback

# Discord OAuth
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
"""
    
    print("   Environment variables for social providers:")
    print(example_env)
    
    print("\n   Configuration files:")
    print("   - config/socialite.py - Main configuration")
    print("   - app/Socialite/ - Provider implementations")
    print("   - routes/socialite.py - Authentication routes")


async def main():
    """Run all Socialite examples."""
    await basic_socialite_usage()
    await custom_provider_example()
    fastapi_integration_example()
    await advanced_features_example()
    environment_setup_example()
    
    print("\n=== Summary ===")
    print("✅ Laravel Socialite implementation complete!")
    print("📚 Features implemented:")
    print("   - GitHub, Google, Facebook, Twitter, LinkedIn, Discord providers")
    print("   - OAuth 2.0 with PKCE support (Twitter)")
    print("   - Custom provider registration")
    print("   - State parameter CSRF protection") 
    print("   - Configurable scopes and parameters")
    print("   - FastAPI integration with session support")
    print("   - User data mapping and transformation")
    print("   - Automatic user linking and creation")
    
    print("\n🚀 Ready to authenticate with social providers!")


if __name__ == "__main__":
    asyncio.run(main())