"""
Laravel-style Authentication Manager with multiple guards
"""
from __future__ import annotations

from typing import Dict, Type, Optional, Any
from fastapi import Request
from sqlalchemy.orm import Session

from app.Auth.Guards import Guard, SessionGuard, TokenGuard


class AuthManager:
    """
    Laravel-style Authentication Manager
    Manages multiple authentication guards
    """
    
    def __init__(self) -> None:
        self._guards: Dict[str, Guard] = {}
        self._default_guard = "web"
        self._guard_configs = {
            "web": {
                "driver": "session",
                "provider": "users"
            },
            "api": {
                "driver": "token",
                "provider": "users"
            }
        }
    
    def guard(self, name: Optional[str] = None) -> Guard:
        """Get a guard instance"""
        guard_name = name or self._default_guard
        
        if guard_name not in self._guards:
            self._guards[guard_name] = self._create_guard(guard_name)
        
        return self._guards[guard_name]
    
    def _create_guard(self, name: str) -> Guard:
        """Create a guard instance"""
        config = self._guard_configs.get(name, {})
        driver = config.get("driver", "session")
        provider = config.get("provider", "users")
        
        if driver == "session":
            return SessionGuard(provider)
        elif driver == "token":
            return TokenGuard(provider)
        else:
            raise ValueError(f"Unsupported guard driver: {driver}")
    
    def extend(self, driver: str, guard_class: Type[Guard]) -> None:
        """Extend with custom guard driver"""
        # Implementation for custom guard drivers
        pass
    
    def set_default_guard(self, name: str) -> None:
        """Set the default guard"""
        self._default_guard = name
    
    def get_default_guard(self) -> str:
        """Get the default guard name"""
        return self._default_guard
    
    def should_use(self, name: str) -> AuthManager:
        """Set the guard to be used for the current request"""
        self._default_guard = name
        return self
    
    # Proxy methods to default guard
    async def check(self) -> bool:
        """Determine if the current user is authenticated"""
        return await self.guard().check()
    
    async def guest(self) -> bool:
        """Determine if the current user is a guest"""
        return await self.guard().guest()
    
    async def user(self) -> Any:
        """Get the currently authenticated user"""
        return await self.guard().user()
    
    async def id(self) -> Optional[str]:
        """Get the ID for the currently authenticated user"""
        return await self.guard().id()
    
    async def validate(self, credentials: Dict[str, Any]) -> bool:
        """Validate user credentials without logging them in"""
        return await self.guard().validate(credentials)
    
    async def attempt(self, credentials: Dict[str, Any], remember: bool = False) -> bool:
        """Attempt to authenticate with given credentials"""
        return await self.guard().attempt(credentials, remember)
    
    async def once(self, credentials: Dict[str, Any]) -> bool:
        """Log a user into the application for a single request"""
        return await self.guard().once(credentials)
    
    async def login(self, user: Any, remember: bool = False) -> None:
        """Log a user into the application"""
        return await self.guard().login(user, remember)
    
    async def login_using_id(self, id: str, remember: bool = False) -> Any:
        """Log a user into the application using their ID"""
        return await self.guard().login_using_id(id, remember)
    
    async def logout(self) -> None:
        """Log the user out of the application"""
        return await self.guard().logout()
    
    def via(self, guard: str) -> Guard:
        """Get a specific guard instance"""
        return self.guard(guard)
    
    def set_request(self, request: Request) -> AuthManager:
        """Set request for all guards"""
        for guard in self._guards.values():
            if hasattr(guard, 'set_request'):
                guard.set_request(request)
        return self
    
    def set_db(self, db: Session) -> AuthManager:
        """Set database session for all guards"""
        for guard in self._guards.values():
            if hasattr(guard, 'set_db'):
                guard.set_db(db)
        return self


# Global auth manager instance
auth_manager = AuthManager()