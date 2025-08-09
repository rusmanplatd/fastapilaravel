from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING, cast
from app.Support.Facades.Facade import Facade

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Auth.AuthManager import AuthManager
    from app.Utils.ULIDUtils import ULID


class Auth(Facade):
    """
    Laravel-style Auth Facade.
    
    Provides static-like access to authentication functionality,
    similar to Laravel's Auth facade.
    """
    
    @staticmethod
    def get_facade_accessor() -> str:
        """Get the registered name of the component."""
        return 'auth'
    
    @classmethod
    def user(cls) -> Optional['User']:
        """
        Get the currently authenticated user.
        
        @return: The authenticated user or None
        """
        return cast(Optional['User'], cls.get_facade_root().user())
    
    @classmethod
    def id(cls) -> Optional['ULID']:
        """
        Get the ID of the currently authenticated user.
        
        @return: The user ID or None
        """
        user = cls.user()
        return user.id if user else None
    
    @classmethod
    def check(cls) -> bool:
        """
        Determine if the current user is authenticated.
        
        @return: True if authenticated, False otherwise
        """
        return cls.user() is not None
    
    @classmethod
    def guest(cls) -> bool:
        """
        Determine if the current user is a guest.
        
        @return: True if guest, False otherwise
        """
        return not cls.check()
    
    @classmethod
    def login(cls, user: 'User', remember: bool = False) -> bool:
        """
        Log a user into the application.
        
        @param user: The user to log in
        @param remember: Whether to remember the user
        @return: True if successful
        """
        return cast(bool, cls.get_facade_root().login(user, remember))
    
    @classmethod
    def login_using_id(cls, user_id: 'ULID', remember: bool = False) -> Optional['User']:
        """
        Log the given user ID into the application.
        
        @param user_id: The user ID to log in
        @param remember: Whether to remember the user  
        @return: The user if successful, None otherwise
        """
        return cast(Optional['User'], cls.get_facade_root().login_using_id(user_id, remember))
    
    @classmethod
    def once(cls, credentials: Dict[str, Any]) -> bool:
        """
        Log a user into the application without sessions or cookies.
        
        @param credentials: The user credentials
        @return: True if successful
        """
        return cast(bool, cls.get_facade_root().once(credentials))
    
    @classmethod
    def attempt(cls, credentials: Dict[str, Any], remember: bool = False) -> bool:
        """
        Attempt to authenticate a user using the given credentials.
        
        @param credentials: The authentication credentials
        @param remember: Whether to remember the user
        @return: True if successful
        """
        return cast(bool, cls.get_facade_root().attempt(credentials, remember))
    
    @classmethod
    def validate(cls, credentials: Dict[str, Any]) -> bool:
        """
        Validate a user's credentials.
        
        @param credentials: The credentials to validate
        @return: True if valid
        """
        return cast(bool, cls.get_facade_root().validate(credentials))
    
    @classmethod
    def logout(cls) -> None:
        """Log the user out of the application."""
        cls.get_facade_root().logout()
    
    @classmethod
    def logout_other_devices(cls, password: str, attribute: str = 'password') -> Optional['User']:
        """
        Invalidate other sessions for the current user.
        
        @param password: The user's password
        @param attribute: The password attribute name
        @return: The user if successful
        """
        return cast(Optional['User'], cls.get_facade_root().logout_other_devices(password, attribute))
    
    @classmethod
    def guard(cls, name: Optional[str] = None) -> 'AuthManager':
        """
        Get a guard instance by name.
        
        @param name: The guard name
        @return: The guard instance
        """
        return cast('AuthManager', cls.get_facade_root().guard(name))
    
    @classmethod
    def set_user(cls, user: 'User') -> None:
        """
        Set the current user.
        
        @param user: The user to set
        """
        cls.get_facade_root().set_user(user)
    
    @classmethod
    def forget_user(cls) -> None:
        """Forget the current user."""
        cls.get_facade_root().forget_user()
    
    @classmethod
    def via_remember(cls) -> bool:
        """
        Determine if the user was authenticated via "remember me" cookie.
        
        @return: True if via remember me
        """
        return cast(bool, cls.get_facade_root().via_remember())
    
    @classmethod
    def should_use(cls, name: str) -> None:
        """
        Set the default guard the factory should serve.
        
        @param name: The guard name
        """
        cls.get_facade_root().should_use(name)


# Alias for easier imports (similar to Laravel)
auth = Auth