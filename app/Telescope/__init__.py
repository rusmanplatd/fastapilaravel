from __future__ import annotations

"""
Laravel Telescope Implementation for FastAPI

Provides debugging, monitoring, and request inspection functionality
similar to Laravel Telescope for development and production environments.
"""

from .TelescopeManager import TelescopeManager
from .Watchers import (
    RequestWatcher,
    QueryWatcher,
    CommandWatcher,
    ExceptionWatcher,
    JobWatcher,
    CacheWatcher,
    RedisWatcher,
    MailWatcher,
    NotificationWatcher,
)
from .Middleware import TelescopeMiddleware
from .Dashboard import TelescopeDashboard
from .Facades import Telescope

__all__ = [
    'TelescopeManager',
    'RequestWatcher',
    'QueryWatcher', 
    'CommandWatcher',
    'ExceptionWatcher',
    'JobWatcher',
    'CacheWatcher',
    'RedisWatcher',
    'MailWatcher',
    'NotificationWatcher',
    'TelescopeMiddleware',
    'TelescopeDashboard',
    'Telescope',
]