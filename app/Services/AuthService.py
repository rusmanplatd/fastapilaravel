from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.Models import User
from app.Utils import JWTUtils, PasswordUtils
from app.Http.Schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.Services.BaseService import BaseService
from config.settings import settings


class AuthService(BaseService):
    
    def register(self, user_data: UserRegister) -> Tuple[bool, str, Optional[TokenResponse]]:
        try:
            existing_user = self.db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                return False, "Email already registered", None
            
            hashed_password = PasswordUtils.hash_password(user_data.password)
            
            user = User(
                name=user_data.name,
                email=user_data.email,
                password=hashed_password,
                is_active=True,
                is_verified=False
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            tokens = self._generate_tokens(user)
            
            return True, "User registered successfully", tokens
            
        except IntegrityError:
            self.db.rollback()
            return False, "Email already exists", None
        except Exception as e:
            self.db.rollback()
            return False, f"Registration failed: {str(e)}", None
    
    def login(self, login_data: UserLogin) -> Tuple[bool, str, Optional[TokenResponse]]:
        user = self.db.query(User).filter(User.email == login_data.email).first()
        
        if not user:
            return False, "Invalid email or password", None
        
        if not user.is_active:
            return False, "Account is deactivated", None
        
        if not PasswordUtils.verify_password(login_data.password, user.password):
            return False, "Invalid email or password", None
        
        tokens = self._generate_tokens(user)
        
        return True, "Login successful", tokens
    
    def refresh_token(self, refresh_token: str) -> Tuple[bool, str, Optional[TokenResponse]]:
        token_data = JWTUtils.verify_token(refresh_token, "refresh")
        
        if not token_data:
            return False, "Invalid refresh token", None
        
        user = self.db.query(User).filter(User.id == token_data["user_id"]).first()
        
        if not user or not user.is_active:
            return False, "Invalid user or account deactivated", None
        
        tokens = self._generate_tokens(user)
        
        return True, "Token refreshed successfully", tokens
    
    def get_current_user(self, token: str) -> Optional[User]:
        token_data = JWTUtils.verify_token(token, "access")
        
        if not token_data:
            return None
        
        user = self.db.query(User).filter(User.id == token_data["user_id"]).first()
        
        if not user or not user.is_active:
            return None
        
        return user
    
    def change_password(self, user: User, current_password: str, new_password: str) -> Tuple[bool, str]:
        if not PasswordUtils.verify_password(current_password, user.password):
            return False, "Current password is incorrect"
        
        try:
            user.password = PasswordUtils.hash_password(new_password)
            self.db.commit()
            return True, "Password changed successfully"
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to change password: {str(e)}"
    
    def update_profile(self, user: User, update_data: Dict[str, Any]) -> Tuple[bool, str, Optional[User]]:
        try:
            if 'email' in update_data and update_data['email'] != user.email:
                existing_user = self.db.query(User).filter(
                    User.email == update_data['email'],
                    User.id != user.id
                ).first()
                if existing_user:
                    return False, "Email already exists", None
                
                user.email_verified_at = None
                user.is_verified = False
            
            for key, value in update_data.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            
            return True, "Profile updated successfully", user
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to update profile: {str(e)}", None
    
    def forgot_password(self, email: str) -> Tuple[bool, str, Optional[str]]:
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            return True, "If the email exists, a reset link has been sent", None
        
        if not user.is_active:
            return False, "Account is deactivated", None
        
        reset_token = JWTUtils.create_reset_password_token(user.id)
        
        return True, "Password reset token generated", reset_token
    
    def reset_password(self, email: str, token: str, new_password: str) -> Tuple[bool, str]:
        user_id = JWTUtils.verify_reset_password_token(token)
        
        if not user_id:
            return False, "Invalid or expired reset token"
        
        user = self.db.query(User).filter(User.id == user_id, User.email == email).first()
        
        if not user:
            return False, "Invalid user"
        
        try:
            user.password = PasswordUtils.hash_password(new_password)
            self.db.commit()
            
            return True, "Password reset successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to reset password: {str(e)}"
    
    def verify_email(self, user: User) -> Tuple[bool, str]:
        try:
            user.email_verified_at = datetime.utcnow()
            user.is_verified = True
            self.db.commit()
            
            return True, "Email verified successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify email: {str(e)}"
    
    def logout(self, user: User) -> Tuple[bool, str]:
        try:
            user.remember_token = None
            self.db.commit()
            
            return True, "Logged out successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to logout: {str(e)}"
    
    def _generate_tokens(self, user: User) -> TokenResponse:
        access_token = JWTUtils.create_access_token({"sub": str(user.id)})
        refresh_token = JWTUtils.create_refresh_token({"sub": str(user.id)})
        
        user_response = UserResponse.model_validate(user)  # type: ignore[attr-defined]
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response
        )
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return PasswordUtils.verify_password(plain_password, hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        return PasswordUtils.hash_password(password)