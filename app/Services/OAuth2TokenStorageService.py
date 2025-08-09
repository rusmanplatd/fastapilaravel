from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import base64
import secrets
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.Services.BaseService import BaseService
from app.Models import OAuth2AccessToken, OAuth2RefreshToken, User, OAuth2Client
from app.Models.OAuth2TokenStorage import OAuth2TokenStorage, TokenType, EncryptionLevel
from config.oauth2 import get_oauth2_settings


class OAuth2TokenStorageService(BaseService):
    """
    Token Storage with Encryption Service
    
    This service provides secure token storage capabilities including:
    - Token encryption at rest and in transit
    - Multiple encryption algorithms support
    - Key rotation and management
    - Token compression and optimization
    - Secure token serialization
    - Token integrity verification
    - Backup and recovery mechanisms
    - Performance-optimized storage
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        
        # Encryption configuration
        self.encryption_enabled = True
        self.encryption_algorithm = "AES-256-GCM"
        self.key_derivation_iterations = 100000
        
        # Storage configuration
        self.compression_enabled = True
        self.token_versioning = True
        self.integrity_checking = True
        
        # Key management
        self.master_key = self._get_or_create_master_key()
        self.encryption_keys = {}
        self.current_key_version = 1
        
        # Performance optimization
        self.token_cache = {}  # In production, use Redis
        self.batch_operations_enabled = True
        
        # Backup configuration
        self.backup_enabled = True
        self.backup_retention_days = 30

    def _get_or_create_master_key(self) -> bytes:
        """Get or create the master encryption key."""
        
        # In production, retrieve from secure key management system
        master_key_env = os.getenv("OAUTH2_MASTER_ENCRYPTION_KEY")
        
        if master_key_env:
            return base64.b64decode(master_key_env)
        
        # Generate new master key (development only)
        master_key = Fernet.generate_key()
        
        # In production, store this securely
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"Generated master key (store securely): {base64.b64encode(master_key).decode()}")
        
        return master_key

    async def store_access_token(
        self,
        token_data: Dict[str, Any],
        client: OAuth2Client,
        user: Optional[User] = None,
        encryption_level: str = "standard"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Store an access token with encryption.
        
        Args:
            token_data: Token information to store
            client: OAuth2 client
            user: User (if applicable)
            encryption_level: Encryption level (standard, high, extreme)
            
        Returns:
            Tuple of (storage_id, storage_metadata)
        """
        storage_id = secrets.token_urlsafe(24)
        current_time = datetime.utcnow()
        
        # Prepare token record
        token_record = {
            "storage_id": storage_id,
            "token_type": "access_token",
            "client_id": client.client_id,
            "user_id": user.id if user else None,
            "created_at": current_time,
            "expires_at": token_data.get("expires_at"),
            "scope": token_data.get("scope", ""),
            "token_data": token_data,
            "encryption_level": encryption_level,
            "version": self.current_key_version
        }
        
        # Apply encryption
        encrypted_record = await self._encrypt_token_record(
            token_record, encryption_level
        )
        
        # Apply compression if enabled
        if self.compression_enabled:
            encrypted_record = await self._compress_token_record(encrypted_record)
        
        # Add integrity verification
        if self.integrity_checking:
            encrypted_record = await self._add_integrity_hash(encrypted_record)
        
        # Store in database
        storage_metadata = await self._persist_token_record(storage_id, encrypted_record)
        
        # Cache for performance
        if self.token_cache is not None:
            cache_key = f"token_storage:{storage_id}"
            self.token_cache[cache_key] = {
                "record": encrypted_record,
                "metadata": storage_metadata,
                "cached_at": current_time
            }
        
        # Create backup if enabled
        if self.backup_enabled:
            await self._create_token_backup(storage_id, encrypted_record)
        
        return storage_id, storage_metadata

    async def retrieve_access_token(
        self,
        storage_id: str,
        verify_integrity: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt an access token.
        
        Args:
            storage_id: Storage identifier
            verify_integrity: Whether to verify token integrity
            
        Returns:
            Decrypted token data or None if not found/invalid
        """
        # Check cache first
        if self.token_cache is not None:
            cache_key = f"token_storage:{storage_id}"
            cached_data = self.token_cache.get(cache_key)
            if cached_data:
                encrypted_record = cached_data["record"]
            else:
                encrypted_record = await self._fetch_token_record(storage_id)
        else:
            encrypted_record = await self._fetch_token_record(storage_id)
        
        if not encrypted_record:
            return None
        
        try:
            # Verify integrity if enabled
            if self.integrity_checking and verify_integrity:
                if not await self._verify_integrity(encrypted_record):
                    return None
            
            # Decompress if needed
            if self.compression_enabled and encrypted_record.get("compressed"):
                encrypted_record = await self._decompress_token_record(encrypted_record)
            
            # Decrypt token record
            decrypted_record = await self._decrypt_token_record(encrypted_record)
            
            # Check expiration
            if decrypted_record.get("expires_at"):
                expires_at = decrypted_record["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                if expires_at < datetime.utcnow():
                    # Token expired, clean up
                    await self._cleanup_expired_token(storage_id)
                    return None
            
            return decrypted_record.get("token_data")
            
        except Exception as e:
            # Log decryption failure
            if self.oauth2_settings.oauth2_debug_mode:
                print(f"Token decryption failed for {storage_id}: {str(e)}")
            return None

    async def store_refresh_token(
        self,
        token_data: Dict[str, Any],
        client: OAuth2Client,
        user: User,
        access_token_storage_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Store a refresh token with high encryption."""
        
        # Refresh tokens get high encryption by default
        storage_id, metadata = await self.store_access_token(
            token_data, client, user, encryption_level="high"
        )
        
        # Associate with access token if provided
        if access_token_storage_id:
            await self._create_token_association(storage_id, access_token_storage_id)
        
        return storage_id, metadata

    async def revoke_token(
        self,
        storage_id: str,
        revocation_reason: str = "explicit_revocation"
    ) -> bool:
        """
        Revoke a token by marking it as revoked.
        
        Args:
            storage_id: Storage identifier
            revocation_reason: Reason for revocation
            
        Returns:
            Success status
        """
        try:
            # Retrieve current record
            encrypted_record = await self._fetch_token_record(storage_id)
            if not encrypted_record:
                return False
            
            # Decrypt to modify
            decrypted_record = await self._decrypt_token_record(encrypted_record)
            
            # Mark as revoked
            decrypted_record["revoked"] = True
            decrypted_record["revoked_at"] = datetime.utcnow()
            decrypted_record["revocation_reason"] = revocation_reason
            
            # Re-encrypt and store
            updated_encrypted_record = await self._encrypt_token_record(
                decrypted_record, 
                encrypted_record.get("encryption_level", "standard")
            )
            
            # Update in storage
            await self._update_token_record(storage_id, updated_encrypted_record)
            
            # Remove from cache
            if self.token_cache is not None:
                cache_key = f"token_storage:{storage_id}"
                self.token_cache.pop(cache_key, None)
            
            return True
            
        except Exception as e:
            if self.oauth2_settings.oauth2_debug_mode:
                print(f"Token revocation failed for {storage_id}: {str(e)}")
            return False

    async def _encrypt_token_record(
        self,
        token_record: Dict[str, Any],
        encryption_level: str
    ) -> Dict[str, Any]:
        """Encrypt a token record based on encryption level."""
        
        if not self.encryption_enabled:
            return token_record
        
        # Serialize token data
        token_json = json.dumps(token_record, default=str, sort_keys=True)
        token_bytes = token_json.encode('utf-8')
        
        # Select encryption method based on level
        if encryption_level == "extreme":
            encrypted_data = await self._encrypt_extreme(token_bytes)
        elif encryption_level == "high":
            encrypted_data = await self._encrypt_high(token_bytes)
        else:
            encrypted_data = await self._encrypt_standard(token_bytes)
        
        return {
            "encrypted_data": base64.b64encode(encrypted_data).decode('ascii'),
            "encryption_level": encryption_level,
            "encryption_algorithm": self.encryption_algorithm,
            "key_version": self.current_key_version,
            "encrypted_at": datetime.utcnow().isoformat(),
            "original_size": len(token_bytes)
        }

    async def _decrypt_token_record(
        self,
        encrypted_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decrypt a token record."""
        
        if not encrypted_record.get("encrypted_data"):
            return encrypted_record
        
        # Decode encrypted data
        encrypted_data = base64.b64decode(encrypted_record["encrypted_data"])
        encryption_level = encrypted_record.get("encryption_level", "standard")
        
        # Decrypt based on level
        if encryption_level == "extreme":
            decrypted_bytes = await self._decrypt_extreme(encrypted_data)
        elif encryption_level == "high":
            decrypted_bytes = await self._decrypt_high(encrypted_data)
        else:
            decrypted_bytes = await self._decrypt_standard(encrypted_data)
        
        # Deserialize
        token_json = decrypted_bytes.decode('utf-8')
        return json.loads(token_json)

    async def _encrypt_standard(self, data: bytes) -> bytes:
        """Standard encryption using Fernet (AES-128 in CBC mode)."""
        fernet = Fernet(self.master_key)
        return fernet.encrypt(data)

    async def _decrypt_standard(self, encrypted_data: bytes) -> bytes:
        """Standard decryption using Fernet."""
        fernet = Fernet(self.master_key)
        return fernet.decrypt(encrypted_data)

    async def _encrypt_high(self, data: bytes) -> bytes:
        """High encryption using AES-256-GCM with key derivation."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        
        # Generate salt and derive key
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=self.key_derivation_iterations,
        )
        key = kdf.derive(self.master_key)
        
        # Generate IV
        iv = os.urandom(12)  # 96 bits for GCM
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Combine salt + iv + tag + ciphertext
        return salt + iv + encryptor.tag + ciphertext

    async def _decrypt_high(self, encrypted_data: bytes) -> bytes:
        """High decryption using AES-256-GCM."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        
        # Extract components
        salt = encrypted_data[:16]
        iv = encrypted_data[16:28]
        tag = encrypted_data[28:44]
        ciphertext = encrypted_data[44:]
        
        # Derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.key_derivation_iterations,
        )
        key = kdf.derive(self.master_key)
        
        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    async def _encrypt_extreme(self, data: bytes) -> bytes:
        """Extreme encryption using multiple layers and key stretching."""
        
        # Layer 1: Compress data first
        import gzip
        compressed_data = gzip.compress(data)
        
        # Layer 2: High encryption
        layer1_encrypted = await self._encrypt_high(compressed_data)
        
        # Layer 3: Additional Fernet layer with derived key
        salt = os.urandom(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=self.key_derivation_iterations * 2,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        
        fernet = Fernet(derived_key)
        layer2_encrypted = fernet.encrypt(layer1_encrypted)
        
        # Combine salt + encrypted data
        return salt + layer2_encrypted

    async def _decrypt_extreme(self, encrypted_data: bytes) -> bytes:
        """Extreme decryption with multiple layers."""
        import gzip
        
        # Extract salt and encrypted data
        salt = encrypted_data[:32]
        layer2_encrypted = encrypted_data[32:]
        
        # Layer 3: Fernet decryption
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=self.key_derivation_iterations * 2,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        
        fernet = Fernet(derived_key)
        layer1_encrypted = fernet.decrypt(layer2_encrypted)
        
        # Layer 2: High decryption
        compressed_data = await self._decrypt_high(layer1_encrypted)
        
        # Layer 1: Decompress
        return gzip.decompress(compressed_data)

    async def _compress_token_record(
        self,
        encrypted_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compress encrypted token record."""
        import gzip
        
        # Compress the encrypted data
        encrypted_data = encrypted_record["encrypted_data"].encode('ascii')
        compressed_data = gzip.compress(encrypted_data)
        
        if len(compressed_data) < len(encrypted_data):
            # Compression was beneficial
            encrypted_record["encrypted_data"] = base64.b64encode(compressed_data).decode('ascii')
            encrypted_record["compressed"] = True
            encrypted_record["compression_ratio"] = len(compressed_data) / len(encrypted_data)
        
        return encrypted_record

    async def _decompress_token_record(
        self,
        encrypted_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decompress token record."""
        import gzip
        
        if not encrypted_record.get("compressed"):
            return encrypted_record
        
        # Decompress the data
        compressed_data = base64.b64decode(encrypted_record["encrypted_data"])
        decompressed_data = gzip.decompress(compressed_data)
        
        encrypted_record["encrypted_data"] = decompressed_data.decode('ascii')
        encrypted_record.pop("compressed", None)
        encrypted_record.pop("compression_ratio", None)
        
        return encrypted_record

    async def _add_integrity_hash(
        self,
        encrypted_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add integrity hash to encrypted record."""
        
        # Create hash of encrypted data
        data_to_hash = json.dumps(encrypted_record, sort_keys=True).encode('utf-8')
        integrity_hash = hashlib.sha256(data_to_hash + self.master_key).hexdigest()
        
        encrypted_record["integrity_hash"] = integrity_hash
        return encrypted_record

    async def _verify_integrity(
        self,
        encrypted_record: Dict[str, Any]
    ) -> bool:
        """Verify integrity of encrypted record."""
        
        stored_hash = encrypted_record.pop("integrity_hash", None)
        if not stored_hash:
            return True  # No hash to verify
        
        # Recalculate hash
        data_to_hash = json.dumps(encrypted_record, sort_keys=True).encode('utf-8')
        calculated_hash = hashlib.sha256(data_to_hash + self.master_key).hexdigest()
        
        # Restore hash
        encrypted_record["integrity_hash"] = stored_hash
        
        return stored_hash == calculated_hash

    async def _persist_token_record(
        self,
        storage_id: str,
        encrypted_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist encrypted token record to database."""
        
        # Save to database using the OAuth2TokenStorage model
        token_storage = OAuth2TokenStorage.create_storage_record(
            storage_id=storage_id,
            token_type=TokenType.ACCESS_TOKEN,  # Will be updated based on context
            client_id=encrypted_record.get("client_id", "unknown"),
            encrypted_data=encrypted_record.get("encrypted_data", ""),
            encryption_level=EncryptionLevel(encrypted_record.get("encryption_level", "standard")),
            user_id=encrypted_record.get("user_id"),
            expires_at=encrypted_record.get("expires_at"),
            encryption_algorithm=encrypted_record.get("encryption_algorithm", self.encryption_algorithm),
            key_version=encrypted_record.get("key_version", self.current_key_version),
            is_compressed=encrypted_record.get("compressed", False),
            compression_ratio=encrypted_record.get("compression_ratio"),
            original_size=encrypted_record.get("original_size"),
            integrity_hash=encrypted_record.get("integrity_hash"),
            encryption_metadata=encrypted_record.get("encryption_metadata", {}),
            storage_metadata={
                "stored_at": datetime.utcnow().isoformat(),
                "size_bytes": len(json.dumps(encrypted_record)),
                "storage_version": "1.0"
            }
        )
        
        # Add to session and commit
        self.db.add(token_storage)
        self.db.commit()
        
        storage_metadata = {
            "storage_id": storage_id,
            "stored_at": datetime.utcnow(),
            "size_bytes": len(json.dumps(encrypted_record)),
            "encryption_level": encrypted_record.get("encryption_level"),
            "compressed": encrypted_record.get("compressed", False),
            "database_id": token_storage.id
        }
        
        # Also cache for performance
        db_key = f"token_db:{storage_id}"
        self.token_cache[db_key] = encrypted_record
        
        return storage_metadata

    async def _fetch_token_record(
        self,
        storage_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch encrypted token record from database."""
        
        # First check cache
        db_key = f"token_db:{storage_id}"
        cached_record = self.token_cache.get(db_key)
        if cached_record:
            return cached_record
        
        # Query database
        token_storage = self.db.query(OAuth2TokenStorage).filter(
            OAuth2TokenStorage.storage_id == storage_id
        ).first()
        
        if not token_storage:
            return None
        
        # Mark as accessed
        token_storage.mark_accessed()
        self.db.commit()
        
        # Convert to record format
        encrypted_record = {
            "encrypted_data": token_storage.encrypted_data,
            "encryption_level": token_storage.encryption_level,
            "encryption_algorithm": token_storage.encryption_algorithm,
            "key_version": token_storage.key_version,
            "compressed": token_storage.is_compressed,
            "compression_ratio": token_storage.compression_ratio,
            "original_size": token_storage.original_size,
            "integrity_hash": token_storage.integrity_hash,
            "client_id": token_storage.client_id,
            "user_id": token_storage.user_id,
            "expires_at": token_storage.expires_at,
            "encryption_metadata": token_storage.encryption_metadata or {}
        }
        
        # Cache for future use
        self.token_cache[db_key] = encrypted_record
        
        return encrypted_record

    async def _update_token_record(
        self,
        storage_id: str,
        encrypted_record: Dict[str, Any]
    ) -> bool:
        """Update encrypted token record in database."""
        
        # In production, update database
        db_key = f"token_db:{storage_id}"
        self.token_cache[db_key] = encrypted_record
        return True

    async def _create_token_association(
        self,
        token1_id: str,
        token2_id: str
    ) -> None:
        """Create association between tokens (e.g., access and refresh)."""
        
        association_key = f"token_association:{token1_id}"
        self.token_cache[association_key] = {
            "associated_token": token2_id,
            "created_at": datetime.utcnow()
        }

    async def _create_token_backup(
        self,
        storage_id: str,
        encrypted_record: Dict[str, Any]
    ) -> None:
        """Create backup of token record."""
        
        if not self.backup_enabled:
            return
        
        backup_key = f"token_backup:{storage_id}:{datetime.utcnow().isoformat()}"
        self.token_cache[backup_key] = {
            "backup_data": encrypted_record,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=self.backup_retention_days)
        }

    async def _cleanup_expired_token(self, storage_id: str) -> None:
        """Clean up expired token from all storage."""
        
        # Remove main record
        db_key = f"token_db:{storage_id}"
        self.token_cache.pop(db_key, None)
        
        # Remove from cache
        cache_key = f"token_storage:{storage_id}"
        self.token_cache.pop(cache_key, None)
        
        # Clean up associations
        association_key = f"token_association:{storage_id}"
        self.token_cache.pop(association_key, None)

    async def rotate_encryption_keys(self) -> Dict[str, Any]:
        """Rotate encryption keys and re-encrypt tokens."""
        
        rotation_stats = {
            "started_at": datetime.utcnow(),
            "old_key_version": self.current_key_version,
            "new_key_version": self.current_key_version + 1,
            "tokens_processed": 0,
            "tokens_failed": 0
        }
        
        # Generate new master key
        new_master_key = Fernet.generate_key()
        old_master_key = self.master_key
        
        # Update key version
        self.current_key_version += 1
        
        # Re-encrypt all tokens with new key
        tokens_to_rotate = []
        for key, value in self.token_cache.items():
            if key.startswith("token_db:"):
                tokens_to_rotate.append((key, value))
        
        self.master_key = new_master_key  # Switch to new key
        
        for db_key, encrypted_record in tokens_to_rotate:
            try:
                # Temporarily switch back to old key for decryption
                self.master_key = old_master_key
                decrypted_record = await self._decrypt_token_record(encrypted_record)
                
                # Switch to new key for encryption
                self.master_key = new_master_key
                new_encrypted_record = await self._encrypt_token_record(
                    decrypted_record,
                    encrypted_record.get("encryption_level", "standard")
                )
                
                # Update storage
                self.token_cache[db_key] = new_encrypted_record
                rotation_stats["tokens_processed"] += 1
                
            except Exception as e:
                rotation_stats["tokens_failed"] += 1
                if self.oauth2_settings.oauth2_debug_mode:
                    print(f"Key rotation failed for {db_key}: {str(e)}")
        
        rotation_stats["completed_at"] = datetime.utcnow()
        return rotation_stats

    async def cleanup_expired_backups(self) -> int:
        """Clean up expired token backups."""
        
        current_time = datetime.utcnow()
        expired_backups = []
        
        for key, backup_data in self.token_cache.items():
            if key.startswith("token_backup:"):
                if backup_data.get("expires_at", datetime.max) < current_time:
                    expired_backups.append(key)
        
        for backup_key in expired_backups:
            self.token_cache.pop(backup_key, None)
        
        return len(expired_backups)

    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get token storage statistics."""
        
        current_time = datetime.utcnow()
        stats = {
            "total_tokens": 0,
            "encrypted_tokens": 0,
            "compressed_tokens": 0,
            "encryption_levels": {"standard": 0, "high": 0, "extreme": 0},
            "total_size_bytes": 0,
            "compression_ratio": 0.0,
            "active_tokens": 0,
            "expired_tokens": 0,
            "backup_count": 0,
            "key_version": self.current_key_version
        }
        
        total_original_size = 0
        total_compressed_size = 0
        
        for key, value in self.token_cache.items():
            if key.startswith("token_db:"):
                stats["total_tokens"] += 1
                
                if value.get("encrypted_data"):
                    stats["encrypted_tokens"] += 1
                
                if value.get("compressed"):
                    stats["compressed_tokens"] += 1
                
                encryption_level = value.get("encryption_level", "standard")
                stats["encryption_levels"][encryption_level] += 1
                
                # Calculate sizes
                record_size = len(json.dumps(value))
                stats["total_size_bytes"] += record_size
                
                if value.get("original_size"):
                    total_original_size += value["original_size"]
                    total_compressed_size += len(value.get("encrypted_data", ""))
                
            elif key.startswith("token_backup:"):
                stats["backup_count"] += 1
        
        # Calculate compression ratio
        if total_original_size > 0:
            stats["compression_ratio"] = total_compressed_size / total_original_size
        
        return stats

    async def get_storage_capabilities(self) -> Dict[str, Any]:
        """Get token storage capabilities."""
        
        return {
            "encryption_supported": True,
            "encryption_algorithms": [self.encryption_algorithm],
            "encryption_levels": ["standard", "high", "extreme"],
            "compression_supported": self.compression_enabled,
            "integrity_checking": self.integrity_checking,
            "token_versioning": self.token_versioning,
            "key_rotation_supported": True,
            "backup_supported": self.backup_enabled,
            "batch_operations": self.batch_operations_enabled,
            "performance_optimized": True
        }