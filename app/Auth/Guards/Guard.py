"""
Laravel-style Authentication Guards
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Type, Protocol
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from database.migrations.create_users_table import User
from app.Utils.JWTUtils import JWTUtils


class Authenticatable(Protocol):
    """Protocol for authenticatable models"""
    id: str
    email: str
    password: str
    is_active: bool
    remember_token: Optional[str]


class Guard(ABC):
    """Base authentication guard"""
    
    def __init__(self, provider: str = "users"):
        self.provider = provider
        self._user: Optional[Authenticatable] = None
    
    @abstractmethod
    async def attempt(self, credentials: Dict[str, Any], remember: bool = False) -> bool:
        """Attempt to authenticate with given credentials"""
        pass
    
    @abstractmethod
    async def check(self) -> bool:
        """Determine if the current user is authenticated"""
        pass
    
    @abstractmethod
    async def guest(self) -> bool:
        """Determine if the current user is a guest"""
        pass
    
    @abstractmethod
    async def user(self) -> Optional[Authenticatable]:
        """Get the currently authenticated user"""
        pass
    
    @abstractmethod
    async def id(self) -> Optional[str]:
        """Get the ID for the currently authenticated user"""
        pass
    
    @abstractmethod
    async def validate(self, credentials: Dict[str, Any]) -> bool:
        """Validate user credentials without logging them in"""
        pass
    
    @abstractmethod
    async def login(self, user: Authenticatable, remember: bool = False) -> None:
        """Log a user into the application"""
        pass
    
    @abstractmethod
    async def login_using_id(self, id: str, remember: bool = False) -> Optional[Authenticatable]:
        """Log a user into the application using their ID"""
        pass
    
    @abstractmethod
    async def once(self, credentials: Dict[str, Any]) -> bool:
        """Log a user into the application for a single request"""
        pass
    
    @abstractmethod
    async def logout(self) -> None:
        """Log the user out of the application"""
        pass
    
    def has_user(self) -> bool:
        """Check if a user is set on the guard"""
        return self._user is not None
    
    def set_user(self, user: Optional[Authenticatable]) -> None:
        """Set the current user"""
        self._user = user


class SessionGuard(Guard):
    """Session-based authentication guard"""
    
    def __init__(self, provider: str = "users"):
        super().__init__(provider)
        self.session: Optional[Dict[str, Any]] = None
        self.request: Optional[Request] = None
        self.db: Optional[Session] = None
    
    def set_request(self, request: Request) -> None:
        """Set the current request"""
        self.request = request
        self.session = getattr(request.state, 'session', {})
    
    def set_db(self, db: Session) -> None:
        """Set the database session"""
        self.db = db
    
    async def attempt(self, credentials: Dict[str, Any], remember: bool = False) -> bool:
        """Attempt to authenticate with given credentials"""
        if await self.validate(credentials):
            user = await self._retrieve_by_credentials(credentials)
            if user:
                await self.login(user, remember)
                return True
        return False
    
    async def check(self) -> bool:
        """Determine if the current user is authenticated"""
        return await self.user() is not None
    
    async def guest(self) -> bool:
        """Determine if the current user is a guest"""
        return not await self.check()
    
    async def user(self) -> Optional[User]:
        """Get the currently authenticated user"""
        if self._user is not None:
            return self._user
        
        user_id = self._get_session_id()
        if user_id and self.db:
            self._user = self.db.query(User).filter(User.id == user_id).first()
            return self._user
        
        return None
    
    async def id(self) -> Optional[str]:
        """Get the ID for the currently authenticated user"""
        user = await self.user()
        return user.id if user else None
    
    async def validate(self, credentials: Dict[str, Any]) -> bool:
        """Validate user credentials without logging them in"""
        user = await self._retrieve_by_credentials(credentials)
        return user is not None and self._verify_password(user, credentials.get('password'))
    
    async def login(self, user: User, remember: bool = False) -> None:
        """Log a user into the application"""
        self._update_session(user.id)
        
        if remember:
            self._queue_remember_cookie(user)
        
        self._user = user
    
    async def login_using_id(self, id: str, remember: bool = False) -> Optional[User]:
        """Log a user into the application using their ID"""
        if self.db:
            user = self.db.query(User).filter(User.id == id).first()
            if user:
                await self.login(user, remember)
                return user
        return None
    
    async def once(self, credentials: Dict[str, Any]) -> bool:
        """Log a user into the application for a single request"""
        if await self.validate(credentials):
            user = await self._retrieve_by_credentials(credentials)
            if user:
                self.set_user(user)
                return True
        return False
    
    async def logout(self) -> None:
        """Log the user out of the application"""
        self._clear_session()
        self._clear_remember_cookie()
        self._user = None
    
    def _get_session_id(self) -> Optional[str]:
        """Get the user ID from session"""
        return self.session.get('user_id') if self.session else None
    
    def _update_session(self, user_id: str) -> None:
        """Update session with user ID"""
        if self.session is not None:
            self.session['user_id'] = user_id
    
    def _clear_session(self) -> None:
        """Clear user ID from session"""
        if self.session is not None:
            self.session.pop('user_id', None)
    
    def _queue_remember_cookie(self, user: User) -> None:
        """Queue remember me cookie"""
        # Implementation would depend on your cookie/session handling
        pass
    
    def _clear_remember_cookie(self) -> None:
        """Clear remember me cookie"""
        # Implementation would depend on your cookie/session handling
        pass
    
    async def _retrieve_by_credentials(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Retrieve user by credentials"""
        if not self.db:
            return None
        
        email = credentials.get('email')
        if email:
            return self.db.query(User).filter(User.email == email).first()
        
        return None
    
    def _verify_password(self, user: User, password: str) -> bool:
        """Verify user password"""
        from app.Utils.PasswordUtils import PasswordUtils
        return PasswordUtils.verify_password(password, user.password)


class TokenGuard(Guard):
    """Token-based authentication guard (JWT)"""
    
    def __init__(self, provider: str = "users"):
        super().__init__(provider)
        self.request: Optional[Request] = None
        self.db: Optional[Session] = None
    
    def set_request(self, request: Request) -> None:
        """Set the current request"""
        self.request = request
    
    def set_db(self, db: Session) -> None:
        """Set the database session"""
        self.db = db
    
    async def attempt(self, credentials: Dict[str, Any], remember: bool = False) -> bool:
        """Attempt to authenticate with given credentials"""
        if await self.validate(credentials):
            user = await self._retrieve_by_credentials(credentials)
            if user:
                await self.login(user, remember)
                return True
        return False
    
    async def check(self) -> bool:
        """Determine if the current user is authenticated"""
        return await self.user() is not None
    
    async def guest(self) -> bool:
        """Determine if the current user is a guest"""
        return not await self.check()
    
    async def user(self) -> Optional[User]:
        """Get the currently authenticated user"""
        if self._user is not None:
            return self._user
        
        token = self._get_token_from_request()
        if token:
            try:
                payload = JWTUtils.decode_token(token)
                user_id = payload.get('user_id')
                
                if user_id and self.db:
                    self._user = self.db.query(User).filter(User.id == user_id).first()
                    return self._user
            except Exception:
                pass
        
        return None
    
    async def id(self) -> Optional[str]:
        """Get the ID for the currently authenticated user"""
        user = await self.user()
        return user.id if user else None
    
    async def validate(self, credentials: Dict[str, Any]) -> bool:
        """Validate user credentials without logging them in"""
        user = await self._retrieve_by_credentials(credentials)
        return user is not None and self._verify_password(user, credentials.get('password'))
    
    async def login(self, user: User, remember: bool = False) -> None:
        """Log a user into the application"""
        # For token guard, login means generating a token
        # This would typically be handled by the controller
        self._user = user
    
    async def login_using_id(self, id: str, remember: bool = False) -> Optional[User]:
        """Log a user into the application using their ID"""
        if self.db:
            user = self.db.query(User).filter(User.id == id).first()
            if user:
                await self.login(user, remember)
                return user
        return None
    
    async def once(self, credentials: Dict[str, Any]) -> bool:
        """Log a user into the application for a single request"""
        if await self.validate(credentials):
            user = await self._retrieve_by_credentials(credentials)
            if user:
                self.set_user(user)
                return True
        return False
    
    async def logout(self) -> None:
        """Log the user out of the application"""
        # For token guard, logout means invalidating the token
        # This could involve blacklisting the token
        self._user = None
    
    def _get_token_from_request(self) -> Optional[str]:
        """Extract token from request"""
        if not self.request:
            return None
        
        # Check Authorization header
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check query parameter
        return self.request.query_params.get('token')
    
    async def _retrieve_by_credentials(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Retrieve user by credentials"""
        if not self.db:
            return None
        
        email = credentials.get('email')
        if email:
            return self.db.query(User).filter(User.email == email).first()
        
        return None
    
    def _verify_password(self, user: User, password: str) -> bool:
        """Verify user password"""
        from app.Utils.PasswordUtils import PasswordUtils
        return PasswordUtils.verify_password(password, user.password)