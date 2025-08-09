from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .PersonalAccessToken import PersonalAccessToken


@dataclass
class NewAccessToken:
    """
    Represents a newly created access token with the plain text token.
    
    Similar to Laravel Sanctum's NewAccessToken class.
    """
    access_token: PersonalAccessToken
    plain_text_token: str
    
    def to_array(self) -> Dict[str, Any]:
        """Convert to array format for API responses."""
        return {
            'access_token': self.access_token.to_dict(),
            'plain_text_token': self.plain_text_token,
        }


class HasApiTokens:
    """
    Laravel Sanctum HasApiTokens trait.
    
    Adds API token functionality to any model (typically User).
    """
    
    def create_token(
        self,
        name: str,
        abilities: List[str] = None,
        expires_at: Optional[datetime] = None
    ) -> NewAccessToken:
        """
        Create a new personal access token for the model.
        
        Args:
            name: Name of the token
            abilities: List of abilities/permissions for the token
            expires_at: When the token should expire
            
        Returns:
            NewAccessToken with the created token and plain text token
        """
        from .PersonalAccessToken import PersonalAccessToken
        
        # Create the token
        token = PersonalAccessToken.create_token(
            tokenable_type=self.__class__.__name__,
            tokenable_id=getattr(self, 'id'),
            name=name,
            abilities=abilities or ['*'],
            expires_at=expires_at
        )
        
        # Return both the token model and the plain text token
        return NewAccessToken(
            access_token=token,
            plain_text_token=token.plain_text_token
        )
    
    def tokens(self) -> List[PersonalAccessToken]:
        """
        Get all tokens for this model.
        
        Returns:
            List of PersonalAccessToken instances
        """
        # In a real implementation, this would query the database:
        # return PersonalAccessToken.query.filter(
        #     PersonalAccessToken.tokenable_type == self.__class__.__name__,
        #     PersonalAccessToken.tokenable_id == self.id
        # ).all()
        
        return []  # Placeholder for actual database query
    
    def current_access_token(self) -> Optional[PersonalAccessToken]:
        """
        Get the current access token for the model.
        
        This is typically set by the authentication middleware.
        
        Returns:
            Current PersonalAccessToken or None
        """
        return getattr(self, '_current_access_token', None)
    
    def set_current_access_token(self, token: PersonalAccessToken) -> None:
        """
        Set the current access token for the model.
        
        Args:
            token: The PersonalAccessToken to set as current
        """
        self._current_access_token = token
    
    def token_can(self, ability: str) -> bool:
        """
        Check if the current token has a specific ability.
        
        Args:
            ability: The ability to check
            
        Returns:
            True if the current token has the ability, False otherwise
        """
        token = self.current_access_token()
        if not token:
            return False
        
        return token.can(ability)
    
    def token_cant(self, ability: str) -> bool:
        """
        Check if the current token does NOT have a specific ability.
        
        Args:
            ability: The ability to check
            
        Returns:
            True if the current token does NOT have the ability, False otherwise
        """
        return not self.token_can(ability)
    
    def revoke_all_tokens(self) -> int:
        """
        Revoke all tokens for this model.
        
        Returns:
            Number of tokens revoked
        """
        tokens = self.tokens()
        revoked_count = 0
        
        for token in tokens:
            if token.revoke():
                revoked_count += 1
        
        return revoked_count
    
    def revoke_current_token(self) -> bool:
        """
        Revoke the current access token.
        
        Returns:
            True if token was revoked, False otherwise
        """
        token = self.current_access_token()
        if not token:
            return False
        
        return token.revoke()
    
    def revoke_token(self, token_id: int) -> bool:
        """
        Revoke a specific token by ID.
        
        Args:
            token_id: ID of the token to revoke
            
        Returns:
            True if token was revoked, False otherwise
        """
        tokens = self.tokens()
        
        for token in tokens:
            if token.id == token_id:
                return token.revoke()
        
        return False
    
    def get_token_abilities(self) -> List[str]:
        """
        Get the abilities of the current token.
        
        Returns:
            List of abilities for the current token
        """
        token = self.current_access_token()
        if not token:
            return []
        
        return token.get_abilities()
    
    def with_access_token(self, token: PersonalAccessToken):
        """
        Set the current access token and return self for chaining.
        
        Args:
            token: The PersonalAccessToken to set as current
            
        Returns:
            Self for method chaining
        """
        self.set_current_access_token(token)
        return self
    
    def create_token_with_expiry(
        self,
        name: str,
        abilities: List[str] = None,
        minutes: int = None,
        hours: int = None,
        days: int = None
    ) -> NewAccessToken:
        """
        Create a token with a specific expiry time.
        
        Args:
            name: Name of the token
            abilities: List of abilities/permissions for the token
            minutes: Expire after this many minutes
            hours: Expire after this many hours
            days: Expire after this many days
            
        Returns:
            NewAccessToken with the created token and plain text token
        """
        expires_at = None
        
        if any([minutes, hours, days]):
            expires_at = datetime.utcnow()
            
            if minutes:
                expires_at += timedelta(minutes=minutes)
            if hours:
                expires_at += timedelta(hours=hours)
            if days:
                expires_at += timedelta(days=days)
        
        return self.create_token(
            name=name,
            abilities=abilities,
            expires_at=expires_at
        )