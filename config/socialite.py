from __future__ import annotations

"""
Social Authentication Configuration

Configuration for Laravel Socialite-style social authentication providers.
Set up your OAuth2 client credentials for each provider you want to use.
"""

import os
from typing import Dict, Any, Optional, List

# Base configuration for social providers
SOCIAL_PROVIDERS: Dict[str, Dict[str, Any]] = {
    'github': {
        'client_id': os.getenv('GITHUB_CLIENT_ID', ''),
        'client_secret': os.getenv('GITHUB_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:8000/auth/github/callback'),
        'scopes': ['user:email'],
    },
    
    'google': {
        'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback'),
        'scopes': [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email'
        ],
    },
    
    'facebook': {
        'client_id': os.getenv('FACEBOOK_CLIENT_ID', ''),
        'client_secret': os.getenv('FACEBOOK_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('FACEBOOK_REDIRECT_URI', 'http://localhost:8000/auth/facebook/callback'),
        'scopes': ['email', 'public_profile'],
    },
    
    'twitter': {
        'client_id': os.getenv('TWITTER_CLIENT_ID', ''),
        'client_secret': os.getenv('TWITTER_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('TWITTER_REDIRECT_URI', 'http://localhost:8000/auth/twitter/callback'),
        'scopes': ['tweet.read', 'users.read'],
    },
    
    'linkedin': {
        'client_id': os.getenv('LINKEDIN_CLIENT_ID', ''),
        'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('LINKEDIN_REDIRECT_URI', 'http://localhost:8000/auth/linkedin/callback'),
        'scopes': ['openid', 'profile', 'email'],
    },
    
    'discord': {
        'client_id': os.getenv('DISCORD_CLIENT_ID', ''),
        'client_secret': os.getenv('DISCORD_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:8000/auth/discord/callback'),
        'scopes': ['identify', 'email'],
    },
}

# Settings
SOCIALITE_SETTINGS = {
    # Whether to use state parameter for CSRF protection (recommended)
    'use_state': True,
    
    # Session key for storing OAuth state
    'state_session_key': 'oauth_state',
    
    # Default scopes for each provider (can be overridden in SOCIAL_PROVIDERS)
    'default_scopes': {
        'github': ['user:email'],
        'google': [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email'
        ],
        'facebook': ['email', 'public_profile'],
        'twitter': ['tweet.read', 'users.read'],
        'linkedin': ['openid', 'profile', 'email'],
        'discord': ['identify', 'email'],
    },
    
    # Whether to automatically link social accounts with existing users based on email
    'auto_link_users': True,
    
    # Whether to automatically create users if they don't exist
    'auto_create_users': True,
    
    # Default role to assign to new social users
    'default_user_role': 'user',
}


def get_provider_config(provider: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific provider."""
    return SOCIAL_PROVIDERS.get(provider)


def is_provider_configured(provider: str) -> bool:
    """Check if a provider has all required configuration."""
    config = get_provider_config(provider)
    if not config:
        return False
    
    required_keys = ['client_id', 'client_secret', 'redirect_uri']
    return all(config.get(key) for key in required_keys)


def get_configured_providers() -> List[str]:
    """Get list of providers that are fully configured."""
    return [
        provider for provider in SOCIAL_PROVIDERS.keys()
        if is_provider_configured(provider)
    ]