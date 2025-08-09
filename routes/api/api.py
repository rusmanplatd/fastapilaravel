from __future__ import annotations

from typing import Dict, Union
from typing_extensions import Annotated
from fastapi import APIRouter, Depends
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Http.Controllers.Api.AuthController import get_current_user
from app.Models import User
from app.Routing import route_manager, middleware_group, route_group
from .auth import auth_router
from .user import user_router
from .permissions import permissions_router
from .roles import roles_router
from .examples import examples_router
from .activity_log import activity_log_router
from .organizations import router as organizations_router
from .departments import router as departments_router
from .job_levels import router as job_levels_router
from .job_positions import router as job_positions_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(permissions_router)
api_router.include_router(roles_router)
api_router.include_router(examples_router)
api_router.include_router(activity_log_router)
api_router.include_router(organizations_router)
api_router.include_router(departments_router)
api_router.include_router(job_levels_router)
api_router.include_router(job_positions_router)


@api_router.get("/")
async def root() -> Dict[str, str]:
    return {"message": "FastAPI with Laravel Structure"}


@api_router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "message": "Application is running"}


@api_router.get("/protected")
async def protected_route(current_user: Annotated[User, Depends(get_current_user)]) -> Dict[str, Union[str, Dict[str, Union[int, str]]]]:
    return {
        "message": "This is a protected route", 
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email
        }
    }


# Register routes with the enhanced route manager for metrics and analysis
def register_api_routes() -> None:
    """Register API routes with the route manager."""
    route_manager.register_route(
        name="api.root",
        path="/api/v1/",
        method="GET",
        handler=root,
        tags=["api", "general"],
        auth_required=False,
        cache_ttl=300
    )
    
    route_manager.register_route(
        name="api.health",
        path="/api/v1/health",
        method="GET", 
        handler=health_check,
        tags=["api", "health"],
        auth_required=False,
        cache_ttl=60
    )
    
    route_manager.register_route(
        name="api.protected",
        path="/api/v1/protected",
        method="GET",
        handler=protected_route,
        tags=["api", "auth"],
        auth_required=True,
        permissions=["user:read"]
    )


# Register the routes
register_api_routes()