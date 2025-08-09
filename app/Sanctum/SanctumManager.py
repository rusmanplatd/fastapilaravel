from __future__ import annotations

import hashlib
from typing import Optional, List, Dict, Any, Union, Type
from datetime import datetime
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .PersonalAccessToken import PersonalAccessToken


class SanctumManager:
    """
    Laravel Sanctum authentication manager.
    
    Handles SPA authentication and API token management.
    """
    
    def __init__(self):
        self.config = {
            'prefix': 'Bearer',
            'header': 'Authorization',
            'cookie': 'laravel_token',
            'expiration': None,  # No expiration by default
            'middleware': ['auth:sanctum'],
            'guard': 'sanctum',
            'token_prefix': '',  # Optional token prefix
            'spa_token_name': 'SPA Token',
        }
        
        # HTTP Bearer scheme for extracting tokens
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def authenticate(self, request: Request) -> Optional[Any]:
        """
        Authenticate a request using Sanctum tokens.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            The authenticated user model or None
        """
        # Try to get token from Authorization header
        token = await self._extract_token_from_header(request)
        
        # If no token in header, try cookie
        if not token:
            token = self._extract_token_from_cookie(request)
        
        if not token:
            return None
        
        # Find and validate the token
        access_token = await self._find_token(token)
        
        if not access_token:
            return None
        
        # Check if token is expired
        if access_token.is_expired():
            return None
        
        # Mark token as used
        access_token.mark_as_used()
        
        # Get the user model (this would typically query the database)
        user = await self._get_user_for_token(access_token)
        
        if user:
            # Set the current access token on the user
            if hasattr(user, 'set_current_access_token'):
                user.set_current_access_token(access_token)
        
        return user
    
    async def _extract_token_from_header(self, request: Request) -> Optional[str]:
        """Extract token from Authorization header."""
        try:
            credentials: HTTPAuthorizationCredentials = await self.bearer_scheme(request)
            if credentials and credentials.scheme.lower() == 'bearer':
                return credentials.credentials
        except Exception:
            pass
        
        return None
    
    def _extract_token_from_cookie(self, request: Request) -> Optional[str]:
        """Extract token from cookie."""
        cookie_name = self.config['cookie']
        return request.cookies.get(cookie_name)  # type: ignore[attr-defined]
    
    async def _find_token(self, token: str) -> Optional[PersonalAccessToken]:
        """
        Find a personal access token by its plain text value.
        
        Args:
            token: The plain text token
            
        Returns:
            PersonalAccessToken if found, None otherwise
        """
        # Remove any prefix
        if self.config['token_prefix']:
            prefix = self.config['token_prefix']
            if token.startswith(prefix):
                token = token[len(prefix):]
        
        # Hash the token to find it in the database
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # In a real implementation, this would query the database:
        # return await PersonalAccessToken.find_by_token(hashed_token)
        
        # For now, return None (placeholder for database query)
        return None
    
    async def _get_user_for_token(self, access_token: PersonalAccessToken) -> Optional[Any]:
        """
        Get the user model for a given access token.
        
        Args:
            access_token: The PersonalAccessToken
            
        Returns:
            User model instance or None
        """
        # In a real implementation, this would query the database:
        # user_class = self._get_model_class(access_token.tokenable_type)
        # return await user_class.find(access_token.tokenable_id)
        
        # For now, return None (placeholder for database query)
        return None
    
    def _get_model_class(self, model_name: str) -> Type:
        """Get the model class from its name."""
        # This would typically use a model registry or import the class
        # For now, return a placeholder
        return type(model_name, (), {})
    
    async def validate_token_abilities(
        self, 
        token: PersonalAccessToken, 
        required_abilities: List[str]
    ) -> bool:
        """
        Validate that a token has the required abilities.
        
        Args:
            token: The PersonalAccessToken
            required_abilities: List of required abilities
            
        Returns:
            True if token has all required abilities
        """
        for ability in required_abilities:
            if not token.can(ability):
                return False
        
        return True
    
    def revoke_all_tokens(self, tokenable_type: str, tokenable_id: int) -> int:
        """
        Revoke all tokens for a specific model.
        
        Args:
            tokenable_type: The model class name
            tokenable_id: The model ID
            
        Returns:
            Number of tokens revoked
        """
        # In a real implementation, this would update/delete from database:
        # return PersonalAccessToken.where(
        #     tokenable_type=tokenable_type,
        #     tokenable_id=tokenable_id
        # ).delete()
        
        return 0  # Placeholder
    
    def revoke_token_by_id(self, token_id: int) -> bool:
        """
        Revoke a specific token by ID.
        
        Args:
            token_id: ID of the token to revoke
            
        Returns:
            True if token was revoked
        """
        # In a real implementation, this would delete from database:
        # token = PersonalAccessToken.find(token_id)
        # if token:
        #     return token.delete()
        
        return False  # Placeholder
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        # In a real implementation, this would delete expired tokens:
        # return PersonalAccessToken.where(
        #     'expires_at', '<', datetime.utcnow()
        # ).delete()
        
        return 0  # Placeholder
    
    def configure(self, **config) -> None:
        """
        Update Sanctum configuration.
        
        Args:
            **config: Configuration options
        """
        self.config.update(config)
    
    def get_config(self, key: Optional[str] = None) -> Any:
        """
        Get configuration value(s).
        
        Args:
            key: Configuration key, or None to get all config
            
        Returns:
            Configuration value or entire config dict
        """
        if key:
            return self.config.get(key)
        return self.config.copy()
    
    async def get_token_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tokens.
        
        Returns:
            Dictionary with token statistics
        """
        # In a real implementation, this would query the database for stats
        return {
            'total_tokens': 0,
            'active_tokens': 0,
            'expired_tokens': 0,
            'tokens_by_type': {},
            'most_used_abilities': [],
        }