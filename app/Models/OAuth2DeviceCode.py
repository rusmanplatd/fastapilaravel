"""OAuth2 Device Code Model - RFC 8628

This model represents device authorization codes for the Device Authorization Grant flow
as defined in RFC 8628.
"""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.Models.BaseModel import BaseModel


class OAuth2DeviceCode(BaseModel):
    """OAuth2 Device Authorization Code model (RFC 8628)."""
    
    __tablename__ = "oauth_device_codes"
    
    # Device code (opaque, long-lived identifier)
    device_code: str = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Device verification code (opaque identifier)"
    )
    
    # User code (short, user-friendly code)
    user_code: str = Column(
        String(16),
        unique=True,
        nullable=False,
        index=True,
        comment="User verification code (user-friendly)"
    )
    
    # Client relationship
    client_id: str = Column(
        String(255),
        ForeignKey("oauth_clients.id"),
        nullable=False,
        comment="OAuth2 client identifier"
    )
    
    # Requested scope
    scope: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Requested OAuth2 scopes"
    )
    
    # User authorization
    user_id: Optional[str] = Column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who authorized the device"
    )
    
    # Authorization status
    authorized_at: Optional[datetime] = Column(
        DateTime,
        nullable=True,
        comment="When the device was authorized"
    )
    
    denied: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether authorization was denied"
    )
    
    denied_at: Optional[datetime] = Column(
        DateTime,
        nullable=True,
        comment="When authorization was denied"
    )
    
    # Expiration
    expires_at: datetime = Column(
        DateTime,
        nullable=False,
        comment="When the device code expires"
    )
    
    # Polling configuration
    interval: int = Column(
        Integer,
        default=5,
        nullable=False,
        comment="Minimum polling interval in seconds"
    )
    
    last_polled_at: Optional[datetime] = Column(
        DateTime,
        nullable=True,
        comment="Last time the device polled for tokens"
    )
    
    # Verification URIs
    verification_uri: str = Column(
        String(255),
        nullable=False,
        comment="Base verification URI"
    )
    
    verification_uri_complete: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="Complete verification URI with user code"
    )
    
    # Relationships
    client = relationship("OAuth2Client", back_populates="device_codes")
    user = relationship("User", back_populates="device_authorizations")
    
    def is_expired(self) -> bool:
        """
        Check if the device code has expired.
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def is_authorized(self) -> bool:
        """
        Check if the device has been authorized by a user.
        
        Returns:
            True if authorized, False otherwise
        """
        return self.user_id is not None and not self.denied
    
    def is_pending(self) -> bool:
        """
        Check if authorization is still pending.
        
        Returns:
            True if pending, False if authorized, denied, or expired
        """
        return (
            self.user_id is None and 
            not self.denied and 
            not self.is_expired()
        )
    
    def get_scopes(self) -> List[str]:
        """
        Get the list of requested scopes.
        
        Returns:
            List of scope strings
        """
        if not self.scope:
            return []
        return self.scope.split()
    
    def time_until_expiry(self) -> timedelta:
        """
        Get time until expiration.
        
        Returns:
            Time until expiry (negative if expired)
        """
        return self.expires_at - datetime.utcnow()
    
    def can_poll(self) -> bool:
        """
        Check if the device can poll for tokens based on interval.
        
        Returns:
            True if polling is allowed, False if too soon
        """
        if not self.last_polled_at:
            return True
        
        time_since_last_poll = (datetime.utcnow() - self.last_polled_at).total_seconds()
        return time_since_last_poll >= self.interval
    
    def get_status(self) -> str:
        """
        Get the current status of the device authorization.
        
        Returns:
            Status string
        """
        if self.is_expired():
            return "expired"
        elif self.denied:
            return "denied"
        elif self.is_authorized():
            return "authorized"
        else:
            return "pending"
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "device_code": self.device_code,
            "user_code": self.user_code,
            "client_id": self.client_id,
            "scope": self.scope,
            "user_id": self.user_id,
            "authorized_at": self.authorized_at.isoformat() if self.authorized_at else None,
            "denied": self.denied,
            "denied_at": self.denied_at.isoformat() if self.denied_at else None,
            "expires_at": self.expires_at.isoformat(),
            "interval": self.interval,
            "last_polled_at": self.last_polled_at.isoformat() if self.last_polled_at else None,
            "verification_uri": self.verification_uri,
            "verification_uri_complete": self.verification_uri_complete,
            "status": self.get_status(),
            "is_expired": self.is_expired(),
            "is_authorized": self.is_authorized(),
            "is_pending": self.is_pending(),
            "can_poll": self.can_poll(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }