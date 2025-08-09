from __future__ import annotations

"""
Example User model with Laravel Sanctum HasApiTokens trait.

This demonstrates how to add API token functionality to a User model.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.Models.BaseModel import BaseModel
from app.Sanctum.HasApiTokens import HasApiTokens, NewAccessToken
from app.Sanctum.PersonalAccessToken import PersonalAccessToken


class User(BaseModel, HasApiTokens):
    """
    User model with Sanctum API token functionality.
    
    Includes all the HasApiTokens methods for token management.
    """
    
    __tablename__ = 'users'
    
    # User columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String(255), nullable=False)  # Hashed password
    remember_token = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(
        self,
        name: str,
        email: str,
        password: str,
        is_active: bool = True
    ):
        self.name = name
        self.email = email
        self.password = password  # Should be hashed before storing
        self.is_active = is_active
    
    def is_verified(self) -> bool:
        """Check if the user's email is verified."""
        return self.email_verified_at is not None
    
    def verify_email(self) -> None:
        """Mark the user's email as verified."""
        self.email_verified_at = datetime.utcnow()
    
    def is_admin(self) -> bool:
        """Check if the user is an admin."""
        # This would typically check roles or permissions
        # For demo purposes, check if email contains 'admin'
        return 'admin' in self.email.lower()
    
    def can_create_tokens(self) -> bool:
        """Check if the user can create API tokens."""
        return self.is_active and self.is_verified()
    
    def get_default_token_abilities(self) -> List[str]:
        """Get default abilities for user tokens."""
        if self.is_admin():
            return ['*']  # Admin gets all abilities
        else:
            return ['read', 'write']  # Regular users get basic abilities
    
    def create_spa_token(self, device_name: str = None) -> NewAccessToken:
        """
        Create a token specifically for SPA authentication.
        
        Args:
            device_name: Name of the device/browser
            
        Returns:
            NewAccessToken for SPA use
        """
        token_name = f"SPA Token ({device_name})" if device_name else "SPA Token"
        
        return self.create_token(
            name=token_name,
            abilities=['*'],  # SPA tokens typically have full access
            expires_at=None   # SPA tokens don't expire by default
        )
    
    def create_api_token(
        self,
        name: str,
        abilities: List[str] = None,
        expires_in_days: int = None
    ) -> NewAccessToken:
        """
        Create a token specifically for API access.
        
        Args:
            name: Name of the API token
            abilities: Specific abilities for the token
            expires_in_days: Token expiration in days
            
        Returns:
            NewAccessToken for API use
        """
        from datetime import timedelta
        
        # Use provided abilities or defaults
        token_abilities = abilities or self.get_default_token_abilities()
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        return self.create_token(
            name=name,
            abilities=token_abilities,
            expires_at=expires_at
        )
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        This would typically integrate with a permission system.
        For demo purposes, we'll use simple rules.
        """
        # Admin has all permissions
        if self.is_admin():
            return True
        
        # Basic permissions for verified users
        if self.is_verified():
            basic_permissions = [
                'read',
                'write', 
                'create-posts',
                'edit-own-posts',
                'delete-own-posts'
            ]
            return permission in basic_permissions
        
        # Unverified users have limited permissions
        limited_permissions = ['read']
        return permission in limited_permissions
    
    def to_dict(self, include_tokens: bool = False) -> dict:
        """Convert user to dictionary for API responses."""
        user_dict = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            'is_active': self.is_active,
            'is_admin': self.is_admin(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_tokens:
            tokens = self.tokens()
            user_dict['tokens'] = [token.to_dict() for token in tokens]
            user_dict['token_count'] = len(tokens)
        
        # Include current token info if available
        current_token = self.current_access_token()
        if current_token:
            user_dict['current_token'] = {
                'id': current_token.id,
                'name': current_token.name,
                'abilities': current_token.get_abilities(),
                'last_used_at': current_token.last_used_at.isoformat() if current_token.last_used_at else None,
            }
        
        return user_dict
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


# Example usage and demonstration
def demonstrate_sanctum_usage():
    """
    Demonstrate how to use Sanctum with the User model.
    """
    
    # Create a user
    user = User(
        name="John Doe",
        email="john@example.com",
        password="hashed_password_here"
    )
    user.id = 1  # Simulate database ID
    user.verify_email()  # Verify email
    
    print("=== Sanctum HasApiTokens Demo ===\n")
    
    # Create different types of tokens
    print("1. Creating SPA Token:")
    spa_token = user.create_spa_token("Chrome Browser")
    print(f"   Token Name: {spa_token.access_token.name}")
    print(f"   Abilities: {spa_token.access_token.get_abilities()}")
    print(f"   Plain Text: {spa_token.plain_text_token[:20]}...")
    print()
    
    print("2. Creating API Token:")
    api_token = user.create_api_token(
        name="Mobile App",
        abilities=['read', 'write', 'create-posts'],
        expires_in_days=30
    )
    print(f"   Token Name: {api_token.access_token.name}")
    print(f"   Abilities: {api_token.access_token.get_abilities()}")
    print(f"   Expires: {api_token.access_token.expires_at}")
    print()
    
    print("3. Creating Limited Token:")
    limited_token = user.create_token(
        name="Read Only Access",
        abilities=['read'],
        expires_at=None
    )
    print(f"   Token Name: {limited_token.access_token.name}")
    print(f"   Abilities: {limited_token.access_token.get_abilities()}")
    print()
    
    # Demonstrate token abilities
    print("4. Testing Token Abilities:")
    user.set_current_access_token(api_token.access_token)
    print(f"   Can read: {user.token_can('read')}")
    print(f"   Can write: {user.token_can('write')}")
    print(f"   Can admin: {user.token_can('admin')}")
    print(f"   Can create posts: {user.token_can('create-posts')}")
    print()
    
    # Show user info with tokens
    print("5. User Info:")
    user_info = user.to_dict(include_tokens=False)
    for key, value in user_info.items():
        if key != 'current_token':
            print(f"   {key}: {value}")
    
    if 'current_token' in user_info:
        print("   Current Token:")
        for key, value in user_info['current_token'].items():
            print(f"     {key}: {value}")


if __name__ == "__main__":
    demonstrate_sanctum_usage()