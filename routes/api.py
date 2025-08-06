from fastapi import APIRouter, Depends
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Http.Controllers import get_current_user
from app.Models import User
from .auth import auth_router
from .user import user_router
from .permissions import permissions_router
from .roles import roles_router
from .examples import examples_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(permissions_router)
api_router.include_router(roles_router)
api_router.include_router(examples_router)


@api_router.get("/")
async def root():
    return {"message": "FastAPI with Laravel Structure"}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Application is running"}


@api_router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {
        "message": "This is a protected route", 
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email
        }
    }