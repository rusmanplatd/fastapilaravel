from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.Http.Controllers import AuthController, get_current_user
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
async def register(user_data: UserRegister, db: Session = Depends(get_database)) -> Dict[str, Any]:
    return auth_controller.register(user_data, db)


@auth_router.post("/login", response_model=Dict[str, Any])
async def login(login_data: UserLogin, db: Session = Depends(get_database)) -> Dict[str, Any]:
    return auth_controller.login(login_data, db)


@auth_router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_database)) -> Dict[str, Any]:
    return auth_controller.refresh_token(refresh_data, db)


@auth_router.post("/logout", response_model=Dict[str, Any])
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
) -> Dict[str, Any]:
    return auth_controller.logout(current_user, db)


@auth_router.get("/profile", response_model=Dict[str, Any])
async def get_profile(current_user: User = Depends(get_current_user)):
    return auth_controller.get_profile(current_user)


@auth_router.put("/profile", response_model=dict)
async def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return auth_controller.update_profile(profile_data, current_user, db)


@auth_router.post("/change-password", response_model=dict)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return auth_controller.change_password(password_data, current_user, db)


@auth_router.post("/forgot-password", response_model=dict)
async def forgot_password(forgot_data: ForgotPasswordRequest, db: Session = Depends(get_database)):
    return auth_controller.forgot_password(forgot_data, db)


@auth_router.post("/reset-password", response_model=dict)
async def reset_password(reset_data: ResetPasswordRequest, db: Session = Depends(get_database)):
    return auth_controller.reset_password(reset_data, db)


@auth_router.post("/verify-email", response_model=dict)
async def verify_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return auth_controller.verify_email(current_user, db)