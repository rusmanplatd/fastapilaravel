from .api import api_router
from .web import web_router
from .auth import auth_router
from .user import user_router
from .permissions import permissions_router
from .roles import roles_router

__all__ = ["api_router", "web_router", "auth_router", "user_router", "permissions_router", "roles_router"]