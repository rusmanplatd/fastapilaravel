from __future__ import annotations

from typing import Dict, Any
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.Http.Controllers.Api.AuthController import AuthController, get_current_user
from app.Http.Schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse
)
from app.Models import User
from config import get_database

auth_router: APIRouter = APIRouter(prefix="/auth", tags=["Authentication"])
auth_controller: AuthController = AuthController()


@auth_router.post("/register", response_model=Dict[str, Any])
async def register(
    user_data: UserRegister, 
    request: Request,
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    return await auth_controller.register(user_data, request, db)


@auth_router.post("/login", response_model=Dict[str, Any])
async def login(
    login_data: UserLogin,
    request: Request,
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    return await auth_controller.login(login_data, request, db)


@auth_router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    return auth_controller.refresh_token(refresh_data, db)


@auth_router.post("/logout", response_model=Dict[str, Any])
async def logout(
    db: Annotated[Session, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    return auth_controller.logout(current_user, db)


@auth_router.get("/profile", response_model=Dict[str, Any])
async def get_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    return await auth_controller.get_profile(current_user, request)


@auth_router.put("/profile", response_model=Dict[str, Any])
async def update_profile(
    profile_data: UpdateProfileRequest,
    db: Annotated[Session, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    return auth_controller.update_profile(profile_data, current_user, db)


@auth_router.post("/change-password", response_model=Dict[str, Any])
async def change_password(
    password_data: ChangePasswordRequest,
    db: Annotated[Session, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    return auth_controller.change_password(password_data, current_user, db)


@auth_router.post("/forgot-password", response_model=Dict[str, Any])
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    return auth_controller.forgot_password(forgot_data, db)


@auth_router.post("/reset-password", response_model=Dict[str, Any])
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    return auth_controller.reset_password(reset_data, db)


@auth_router.post("/verify-email", response_model=Dict[str, Any])
async def verify_email(
    db: Annotated[Session, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    return auth_controller.verify_email(current_user, db)