from .CORSMiddleware import add_cors_middleware
from .AuthMiddleware import verify_token, AuthMiddleware
from .PerformanceMiddleware import PerformanceMiddleware
from .ActivityLogMiddleware import ActivityLogMiddleware
from .PermissionMiddleware import (
    require_permission,
    require_role,
    require_permission_or_role,
    check_permission,
    check_role,
    check_any_permission,
    check_all_permissions,
    check_any_role,
    check_all_roles,
    can,
    is_role,
    has_any_permission,
    has_all_permissions,
    has_any_role,
    has_all_roles
)
from .MFAMiddleware import MFAMiddleware, require_mfa, verify_mfa_session
from .CacheMiddleware import (
    CacheMiddleware,
    ResponseCacheMiddleware,
    CacheTagMiddleware,
    DEFAULT_CACHE_RULES
)
from .MiddlewareManager import (
    MiddlewareManager,
    create_default_middleware_manager,
    setup_production_middleware,
    setup_development_middleware,
    middleware_manager,
    get_middleware_stats,
    MiddlewareHealthChecker,
    health_checker
)
from .TrimStrings import TrimStrings
from .SubstituteBindings import SubstituteBindings, RouteModelBinding, model_binding
from .ThrottleRequests import ThrottleRequests, throttle, NamedThrottle
from .RedirectIfAuthenticated import RedirectIfAuthenticated
from .EncryptCookies import EncryptCookies
from .TrustProxies import TrustProxies
from .LocaleMiddleware import LocaleMiddleware
from .OAuth2Middleware import OAuth2Middleware

__all__ = [
    "add_cors_middleware", 
    "verify_token", 
    "AuthMiddleware",
    "PerformanceMiddleware",
    "ActivityLogMiddleware",
    "require_permission",
    "require_role", 
    "require_permission_or_role",
    "check_permission",
    "check_role",
    "check_any_permission",
    "check_all_permissions",
    "check_any_role",
    "check_all_roles",
    "can",
    "is_role",
    "has_any_permission",
    "has_all_permissions",
    "has_any_role",
    "has_all_roles",
    "MFAMiddleware",
    "require_mfa",
    "verify_mfa_session",
    # Cache middleware
    "CacheMiddleware",
    "ResponseCacheMiddleware", 
    "CacheTagMiddleware",
    "DEFAULT_CACHE_RULES",
    # Enhanced middleware manager
    "MiddlewareManager",
    "create_default_middleware_manager",
    "setup_production_middleware",
    "setup_development_middleware",
    "middleware_manager",
    "get_middleware_stats",
    "MiddlewareHealthChecker",
    "health_checker",
    # New Laravel-style middleware
    "TrimStrings",
    "SubstituteBindings", 
    "RouteModelBinding",
    "model_binding",
    "ThrottleRequests",
    "throttle",
    "NamedThrottle", 
    "RedirectIfAuthenticated",
    "EncryptCookies",
    "TrustProxies",
    "LocaleMiddleware",
    "OAuth2Middleware"
]