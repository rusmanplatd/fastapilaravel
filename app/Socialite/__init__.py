from __future__ import annotations

"""
Laravel Socialite Implementation for FastAPI

Provides social authentication integration similar to Laravel Socialite
for multiple OAuth providers including GitHub, Google, Twitter, etc.
"""

from .SocialiteManager import SocialiteManager
from .Contracts import Provider, User as SocialUser
from .Providers import (
    GitHubProvider,
    GoogleProvider,
    TwitterProvider,
    FacebookProvider,
    LinkedInProvider,
    DiscordProvider,
)
from .Facades import Socialite

__all__ = [
    'SocialiteManager',
    'Provider',
    'SocialUser', 
    'GitHubProvider',
    'GoogleProvider',
    'TwitterProvider',
    'FacebookProvider',
    'LinkedInProvider',
    'DiscordProvider',
    'Socialite',
]