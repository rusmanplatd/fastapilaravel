from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
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
from app.Services import AuthService
from app.Models import User
from config import get_database


class AuthController(BaseController):
    
    def register(self, user_data: UserRegister, db: Session = Depends(get_database)):
        auth_service = AuthService(db)
        success, message, tokens = auth_service.register(user_data)
        
        if not success:
            self.validation_error(message)
        
        return self.success_response(
            data=tokens,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    def login(self, login_data: UserLogin, db: Session = Depends(get_database)):
        auth_service = AuthService(db)
        success, message, tokens = auth_service.login(login_data)
        
        if not success:
            self.error_response(message, status.HTTP_401_UNAUTHORIZED)
        
        return self.success_response(
            data=tokens,
            message=message
        )
    
    def refresh_token(self, refresh_data: RefreshTokenRequest, db: Session = Depends(get_database)):
        auth_service = AuthService(db)
        success, message, tokens = auth_service.refresh_token(refresh_data.refresh_token)
        
        if not success:
            self.error_response(message, status.HTTP_401_UNAUTHORIZED)
        
        return self.success_response(
            data=tokens,
            message=message
        )
    
    def change_password(
        self, 
        password_data: ChangePasswordRequest, 
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        auth_service = AuthService(db)
        success, message = auth_service.change_password(
            current_user, 
            password_data.current_password, 
            password_data.new_password
        )
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def forgot_password(self, forgot_data: ForgotPasswordRequest, db: Session = Depends(get_database)):
        auth_service = AuthService(db)
        success, message, reset_token = auth_service.forgot_password(forgot_data.email)
        
        return self.success_response(
            data={"reset_token": reset_token} if reset_token else None,
            message=message
        )
    
    def reset_password(self, reset_data: ResetPasswordRequest, db: Session = Depends(get_database)):
        auth_service = AuthService(db)
        success, message = auth_service.reset_password(
            reset_data.email,
            reset_data.token,
            reset_data.password
        )
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def logout(
        self, 
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        auth_service = AuthService(db)
        success, message = auth_service.logout(current_user)
        
        return self.success_response(message=message)
    
    def get_profile(self, current_user: User = Depends(get_current_user)):
        user_response = UserResponse.from_orm(current_user)
        return self.success_response(
            data=user_response,
            message="Profile retrieved successfully"
        )
    
    def update_profile(
        self,
        profile_data: UpdateProfileRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        auth_service = AuthService(db)
        
        update_data = {}
        if profile_data.name is not None:
            update_data["name"] = profile_data.name
        if profile_data.email is not None:
            update_data["email"] = profile_data.email
        
        success, message, updated_user = auth_service.update_profile(current_user, update_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        user_response = UserResponse.from_orm(updated_user)
        return self.success_response(
            data=user_response,
            message=message
        )
    
    def verify_email(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        auth_service = AuthService(db)
        success, message = auth_service.verify_email(current_user)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)


def get_current_user(token: str = Depends(verify_token_dependency), db: Session = Depends(get_database)) -> User:
    auth_service = AuthService(db)
    user = auth_service.get_current_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    return user


def verify_token_dependency():
    from app.Http.Middleware.AuthMiddleware import verify_token
    return verify_token