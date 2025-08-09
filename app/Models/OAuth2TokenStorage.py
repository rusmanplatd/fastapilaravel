"""OAuth2 Token Storage Model

Model for encrypted token storage with advanced security features.
"""

from __future__ import annotations

from sqlalchemy import String, Text, DateTime, Boolean, JSON, Integer, Float, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from app.Models.BaseModel import BaseModel


class TokenType(str, Enum):
    """Token types for storage."""
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    AUTHORIZATION_CODE = "authorization_code"
    DEVICE_CODE = "device_code"
    ID_TOKEN = "id_token"


class EncryptionLevel(str, Enum):
    """Encryption levels for token storage."""
    STANDARD = "standard"
    HIGH = "high"
    EXTREME = "extreme"


class BackupStatus(str, Enum):
    """Backup status for token storage."""
    NONE = "none"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class OAuth2TokenStorage(BaseModel):
    """OAuth2 Token Storage with encryption and security features."""
    
    __tablename__ = "oauth2_token_storage"
    
    # Storage identification
    storage_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Associated entities
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Token data (encrypted)
    encrypted_data: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Encryption configuration
    encryption_level: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    encryption_algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="AES-256-GCM")
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Compression and optimization
    is_compressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compression_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    original_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Integrity verification
    integrity_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # Token lifecycle
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Performance and caching
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cache_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Backup and recovery
    backup_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    backup_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    backup_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    encryption_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Additional metadata
    token_scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_abilities: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    storage_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_oauth2_storage_client_type', 'client_id', 'token_type'),
        Index('idx_oauth2_storage_user_type', 'user_id', 'token_type'),
        Index('idx_oauth2_storage_expires', 'expires_at', 'is_revoked'),
        Index('idx_oauth2_storage_access_time', 'last_accessed_at'),
        Index('idx_oauth2_storage_encryption', 'encryption_level', 'key_version'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2TokenStorage(storage_id='{self.storage_id}', token_type='{self.token_type}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked
    
    @property
    def storage_size_kb(self) -> float:
        """Get storage size in KB."""
        if not self.encrypted_data:
            return 0.0
        return len(self.encrypted_data.encode('utf-8')) / 1024
    
    @property
    def compression_savings(self) -> float:
        """Get compression savings percentage."""
        if not self.is_compressed or not self.compression_ratio:
            return 0.0
        return (1 - self.compression_ratio) * 100
    
    def get_token_scopes(self) -> List[str]:
        """Get list of token scopes."""
        if not self.token_scope:
            return []
        return [scope.strip() for scope in self.token_scope.split(" ") if scope.strip()]
    
    def set_token_scopes(self, scopes: List[str]) -> None:
        """Set token scopes from list."""
        self.token_scope = " ".join(scopes)
    
    def get_token_abilities(self) -> List[str]:
        """Get list of token abilities."""
        return self.token_abilities or []
    
    def set_token_abilities(self, abilities: List[str]) -> None:
        """Set token abilities."""
        self.token_abilities = abilities
    
    def mark_accessed(self) -> None:
        """Mark token as accessed."""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
    
    def revoke(self, reason: str = "explicit_revocation") -> None:
        """Revoke the token."""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
        self.revocation_reason = reason
    
    def set_backup_status(self, status: BackupStatus, location: Optional[str] = None) -> None:
        """Set backup status."""
        self.backup_status = status.value
        self.backup_location = location
        if status == BackupStatus.COMPLETED:
            self.backup_created_at = datetime.utcnow()
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """Get encryption information."""
        return {
            "level": self.encryption_level,
            "algorithm": self.encryption_algorithm,
            "key_version": self.key_version,
            "is_compressed": self.is_compressed,
            "compression_ratio": self.compression_ratio,
            "has_integrity_hash": bool(self.integrity_hash),
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "storage_size_kb": self.storage_size_kb,
            "compression_savings_percent": self.compression_savings,
            "backup_status": self.backup_status,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "storage_id": self.storage_id,
            "token_type": self.token_type,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revocation_reason": self.revocation_reason,
            "encryption_info": self.get_encryption_info(),
            "performance_metrics": self.get_performance_metrics(),
            "token_scopes": self.get_token_scopes(),
            "token_abilities": self.get_token_abilities(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def create_storage_record(
        cls,
        storage_id: str,
        token_type: TokenType,
        client_id: str,
        encrypted_data: str,
        encryption_level: EncryptionLevel = EncryptionLevel.STANDARD,
        user_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        **kwargs: Any
    ) -> OAuth2TokenStorage:
        """Create a new token storage record."""
        return cls(
            storage_id=storage_id,
            token_type=token_type.value,
            client_id=client_id,
            user_id=user_id,
            encrypted_data=encrypted_data,
            encryption_level=encryption_level.value,
            expires_at=expires_at,
            **kwargs
        )