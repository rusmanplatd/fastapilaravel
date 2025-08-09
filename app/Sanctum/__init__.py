from __future__ import annotations

"""
Laravel Sanctum implementation for FastAPI.

Provides SPA authentication and API token management.
"""

from .SanctumManager import SanctumManager
from .PersonalAccessToken import PersonalAccessToken
from .HasApiTokens import HasApiTokens, NewAccessToken
from .Middleware import (
    SanctumAuthenticationMiddleware,
    sanctum_user,
    require_sanctum_auth,
    require_abilities,
    require_any_ability,
    optional_sanctum_auth,
    auth_sanctum,
    abilities,
    any_ability,
)
from .Facades import Sanctum

__all__ = [
    'SanctumManager',
    'PersonalAccessToken',
    'HasApiTokens',
    'NewAccessToken',
    'SanctumAuthenticationMiddleware',
    'sanctum_user',
    'require_sanctum_auth',
    'require_abilities',
    'require_any_ability',
    'optional_sanctum_auth',
    'auth_sanctum',
    'abilities',
    'any_ability',
    'Sanctum',
]