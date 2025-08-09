from __future__ import annotations

from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from ..Support.Facades.Facade import Facade
from .SanctumManager import SanctumManager
from .PersonalAccessToken import PersonalAccessToken


class Sanctum(Facade):
    """
    Laravel Sanctum Facade.
    
    Provides static-like access to Sanctum functionality.
    
    Examples:
        token = await Sanctum.create_token(user, 'API Token', ['read', 'write'])
        user = await Sanctum.authenticate(request)
        Sanctum.revoke_all_tokens_for(user)
    """
    
    _instance: Optional[SanctumManager] = None
    
    @classmethod
    def _get_manager(cls) -> SanctumManager:
        """Get the Sanctum manager instance."""
        if cls._instance is None:
            cls._instance = SanctumManager()
        return cls._instance
    
    @classmethod
    async def authenticate(cls, request) -> Optional[Any]:
        """Authenticate a request using Sanctum tokens."""
        return await cls._get_manager().authenticate(request)
    
    @classmethod
    async def find_token(cls, token: str) -> Optional[PersonalAccessToken]:
        """Find a personal access token by its plain text value."""
        return await cls._get_manager()._find_token(token)
    
    @classmethod
    async def validate_token_abilities(
        cls, 
        token: PersonalAccessToken, 
        required_abilities: List[str]
    ) -> bool:
        """Validate that a token has the required abilities."""
        return await cls._get_manager().validate_token_abilities(token, required_abilities)
    
    @classmethod
    def revoke_all_tokens(cls, tokenable_type: str, tokenable_id: int) -> int:
        """Revoke all tokens for a specific model."""
        return cls._get_manager().revoke_all_tokens(tokenable_type, tokenable_id)
    
    @classmethod
    def revoke_token_by_id(cls, token_id: int) -> bool:
        """Revoke a specific token by ID."""
        return cls._get_manager().revoke_token_by_id(token_id)
    
    @classmethod
    async def cleanup_expired_tokens(cls) -> int:
        """Clean up expired tokens."""
        return await cls._get_manager().cleanup_expired_tokens()
    
    @classmethod
    def configure(cls, **config) -> None:
        """Update Sanctum configuration."""
        cls._get_manager().configure(**config)
    
    @classmethod
    def get_config(cls, key: str = None) -> Any:
        """Get configuration value(s)."""
        return cls._get_manager().get_config(key)
    
    @classmethod
    async def get_token_stats(cls) -> Dict[str, Any]:
        """Get statistics about tokens."""
        return await cls._get_manager().get_token_stats()
    
    # Helper methods for common operations
    
    @classmethod
    def create_token_for_user(
        cls,
        user: Any,
        name: str,
        abilities: List[str] = None,
        expires_at: Optional[datetime] = None
    ):
        """
        Create a token for a user (requires HasApiTokens trait).
        
        Args:
            user: User model instance with HasApiTokens
            name: Name of the token
            abilities: List of abilities for the token
            expires_at: When the token should expire
            
        Returns:
            NewAccessToken instance
        """
        if not hasattr(user, 'create_token'):
            raise AttributeError(f"User model must use HasApiTokens trait")
        
        return user.create_token(name, abilities, expires_at)
    
    @classmethod
    def revoke_all_tokens_for_user(cls, user: Any) -> int:
        """
        Revoke all tokens for a user.
        
        Args:
            user: User model instance
            
        Returns:
            Number of tokens revoked
        """
        if not hasattr(user, 'revoke_all_tokens'):
            # Fallback to manager method
            return cls.revoke_all_tokens(
                user.__class__.__name__,
                getattr(user, 'id')
            )
        
        return user.revoke_all_tokens()
    
    @classmethod
    def get_user_tokens(cls, user: Any) -> List[PersonalAccessToken]:
        """
        Get all tokens for a user.
        
        Args:
            user: User model instance
            
        Returns:
            List of PersonalAccessToken instances
        """
        if not hasattr(user, 'tokens'):
            return []
        
        return user.tokens()
    
    @classmethod
    def check_user_token_ability(cls, user: Any, ability: str) -> bool:
        """
        Check if user's current token has a specific ability.
        
        Args:
            user: User model instance
            ability: Ability to check
            
        Returns:
            True if token has the ability
        """
        if not hasattr(user, 'token_can'):
            return False
        
        return user.token_can(ability)
    
    @classmethod
    def get_user_token_abilities(cls, user: Any) -> List[str]:
        """
        Get the abilities of the user's current token.
        
        Args:
            user: User model instance
            
        Returns:
            List of abilities
        """
        if not hasattr(user, 'get_token_abilities'):
            return []
        
        return user.get_token_abilities()
    
    # Configuration shortcuts
    
    @classmethod
    def use_cookie(cls, name: str = 'laravel_token') -> None:
        """Configure Sanctum to use cookie authentication."""
        cls.configure(cookie=name)
    
    @classmethod
    def use_prefix(cls, prefix: str) -> None:
        """Configure Sanctum to use a token prefix."""
        cls.configure(token_prefix=prefix)
    
    @classmethod
    def expires_in(cls, minutes: int = None, hours: int = None, days: int = None) -> None:
        """Configure default token expiration."""
        if minutes:
            expiration = minutes * 60
        elif hours:
            expiration = hours * 3600
        elif days:
            expiration = days * 86400
        else:
            expiration = None
        
        cls.configure(expiration=expiration)