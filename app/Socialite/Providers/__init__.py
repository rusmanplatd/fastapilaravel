from __future__ import annotations

"""
Social authentication providers similar to Laravel Socialite drivers.
"""

from .GitHubProvider import GitHubProvider
from .GoogleProvider import GoogleProvider
from .TwitterProvider import TwitterProvider
from .FacebookProvider import FacebookProvider
from .LinkedInProvider import LinkedInProvider
from .DiscordProvider import DiscordProvider

__all__ = [
    'GitHubProvider',
    'GoogleProvider', 
    'TwitterProvider',
    'FacebookProvider',
    'LinkedInProvider',
    'DiscordProvider',
]