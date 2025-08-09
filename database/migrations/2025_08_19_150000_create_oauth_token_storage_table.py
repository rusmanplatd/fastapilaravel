"""Create OAuth2 Token Storage Table

Migration for creating OAuth2 token storage table with encryption support.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Text, DateTime, Boolean, Integer, LargeBinary
from sqlalchemy.types import JSON, Float
from datetime import datetime


def upgrade() -> None:
    """Create oauth2_token_storage table."""
    
    op.create_table(
        'oauth2_token_storage',
        
        # Primary key
        sa.Column('id', sa.Integer, primary_key=True),
        
        # Storage identification
        sa.Column('storage_id', String(50), unique=True, index=True, nullable=False),
        sa.Column('token_type', String(20), nullable=False, index=True),  # access_token, refresh_token, etc.
        
        # Associated entities
        sa.Column('client_id', String(255), nullable=False, index=True),
        sa.Column('user_id', String(255), nullable=True, index=True),
        
        # Token data (encrypted)
        sa.Column('encrypted_data', Text, nullable=False),
        sa.Column('encryption_metadata', JSON, nullable=True),
        
        # Encryption configuration
        sa.Column('encryption_level', String(20), nullable=False, default='standard'),
        sa.Column('encryption_algorithm', String(50), nullable=False, default='AES-256-GCM'),
        sa.Column('key_version', Integer, nullable=False, default=1),
        
        # Compression and optimization
        sa.Column('is_compressed', Boolean, default=False, nullable=False),
        sa.Column('compression_ratio', Float, nullable=True),
        sa.Column('original_size', Integer, nullable=True),
        
        # Integrity verification
        sa.Column('integrity_hash', String(64), nullable=True),
        sa.Column('checksum', String(32), nullable=True),
        
        # Token lifecycle
        sa.Column('expires_at', DateTime, nullable=True, index=True),
        sa.Column('revoked_at', DateTime, nullable=True),
        sa.Column('revocation_reason', String(100), nullable=True),
        sa.Column('is_revoked', Boolean, default=False, nullable=False, index=True),
        
        # Performance and caching
        sa.Column('access_count', Integer, default=0, nullable=False),
        sa.Column('last_accessed_at', DateTime, nullable=True),
        sa.Column('cache_key', String(100), nullable=True, index=True),
        
        # Backup and recovery
        sa.Column('backup_status', String(20), default='none', nullable=False),
        sa.Column('backup_location', String(255), nullable=True),
        sa.Column('backup_created_at', DateTime, nullable=True),
        
        # Audit trail
        sa.Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('created_by', String(255), nullable=True),
        sa.Column('encryption_context', JSON, nullable=True),
        
        # Additional metadata
        sa.Column('token_scope', Text, nullable=True),
        sa.Column('token_abilities', JSON, nullable=True),
        sa.Column('storage_metadata', JSON, nullable=True),
        
        # Performance indexes
        sa.Index('idx_oauth2_storage_client_type', 'client_id', 'token_type'),
        sa.Index('idx_oauth2_storage_user_type', 'user_id', 'token_type'),
        sa.Index('idx_oauth2_storage_expires', 'expires_at', 'is_revoked'),
        sa.Index('idx_oauth2_storage_access_time', 'last_accessed_at'),
        sa.Index('idx_oauth2_storage_encryption', 'encryption_level', 'key_version'),
    )


def downgrade() -> None:
    """Drop oauth2_token_storage table."""
    op.drop_table('oauth2_token_storage')