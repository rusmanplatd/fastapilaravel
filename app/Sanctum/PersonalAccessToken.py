from __future__ import annotations

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ..Models.BaseModel import BaseModel


class PersonalAccessToken(BaseModel):
    """
    Laravel Sanctum Personal Access Token model.
    
    Stores API tokens for SPA authentication and API access.
    """
    
    __tablename__ = 'personal_access_tokens'
    
    # Table columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    tokenable_type = Column(String(255), nullable=False)  # Model class name
    tokenable_id = Column(Integer, nullable=False)        # Model ID
    name = Column(String(255), nullable=False)            # Token name
    token = Column(String(64), unique=True, nullable=False)  # Hashed token
    abilities = Column(Text, nullable=True)               # JSON encoded abilities
    last_used_at = Column(DateTime, nullable=True)        # Last usage timestamp
    expires_at = Column(DateTime, nullable=True)          # Token expiration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(
        self,
        tokenable_type: str,
        tokenable_id: int,
        name: str,
        abilities: List[str] = None,
        expires_at: Optional[datetime] = None
    ):
        self.tokenable_type = tokenable_type
        self.tokenable_id = tokenable_id
        self.name = name
        self.abilities = self._encode_abilities(abilities or ['*'])
        self.expires_at = expires_at
        
        # Generate the actual token
        self.plain_text_token = self._generate_token()
        self.token = self._hash_token(self.plain_text_token)
    
    def _generate_token(self) -> str:
        """Generate a new random token."""
        # Generate a 40-character random token (Laravel Sanctum format)
        return secrets.token_hex(20)
    
    def _hash_token(self, token: str) -> str:
        """Hash the token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _encode_abilities(self, abilities: List[str]) -> str:
        """Encode abilities as JSON string."""
        import json
        return json.dumps(abilities)
    
    def _decode_abilities(self) -> List[str]:
        """Decode abilities from JSON string."""
        import json
        if not self.abilities:
            return ['*']
        try:
            return json.loads(self.abilities)
        except (json.JSONDecodeError, TypeError):
            return ['*']
    
    def get_abilities(self) -> List[str]:
        """Get the token's abilities."""
        return self._decode_abilities()
    
    def can(self, ability: str) -> bool:
        """Check if the token has a specific ability."""
        abilities = self.get_abilities()
        
        # Wildcard permission
        if '*' in abilities:
            return True
        
        # Exact match
        if ability in abilities:
            return True
        
        # Check for wildcard patterns (e.g., 'posts:*' matches 'posts:create')
        for token_ability in abilities:
            if token_ability.endswith('*'):
                prefix = token_ability[:-1]
                if ability.startswith(prefix):
                    return True
        
        return False
    
    def cant(self, ability: str) -> bool:
        """Check if the token does NOT have a specific ability."""
        return not self.can(ability)
    
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def mark_as_used(self) -> None:
        """Mark the token as used (update last_used_at)."""
        self.last_used_at = datetime.utcnow()
    
    def revoke(self) -> bool:
        """Revoke the token by deleting it."""
        try:
            # In a real implementation, you'd delete from database
            # For now, we'll mark it as expired
            self.expires_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    @classmethod
    def find_token(cls, token: str) -> Optional[PersonalAccessToken]:
        """Find a token by its plain text value."""
        # In a real implementation, you'd query the database
        # This is a simplified version for demonstration
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # Query would look like:
        # return db.session.query(cls).filter(cls.token == hashed_token).first()
        
        # For now, return None (would be implemented with actual database)
        return None
    
    @classmethod
    def create_token(
        cls,
        tokenable_type: str,
        tokenable_id: int,
        name: str,
        abilities: List[str] = None,
        expires_at: Optional[datetime] = None
    ) -> PersonalAccessToken:
        """Create a new personal access token."""
        token = cls(
            tokenable_type=tokenable_type,
            tokenable_id=tokenable_id,
            name=name,
            abilities=abilities,
            expires_at=expires_at
        )
        
        # In a real implementation, you'd save to database here
        # db.session.add(token)
        # db.session.commit()
        
        return token
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'abilities': self.get_abilities(),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PersonalAccessToken(id={self.id}, name='{self.name}', tokenable={self.tokenable_type}:{self.tokenable_id})>"