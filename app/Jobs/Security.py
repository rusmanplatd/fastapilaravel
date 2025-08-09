from __future__ import annotations

import os
import json
import hmac
import hashlib
import secrets
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64

if TYPE_CHECKING:
    from app.Jobs.Job import ShouldQueue


class JobEncryption:
    """
    Job payload encryption system for secure job storage.
    """
    
    def __init__(self, key: Optional[bytes] = None, algorithm: str = "fernet") -> None:
        self.algorithm = algorithm
        
        if key is None:
            # Generate or get key from environment
            key_b64 = os.getenv("QUEUE_ENCRYPTION_KEY")
            if key_b64:
                self.key = base64.urlsafe_b64decode(key_b64.encode())
            else:
                self.key = self._generate_key()
        else:
            self.key = key
        
        if self.algorithm == "fernet":
            self.fernet = Fernet(base64.urlsafe_b64encode(self.key[:32]))
        elif self.algorithm == "aes":
            # AES-256 requires 32-byte key
            self.key = self.key[:32] if len(self.key) >= 32 else self.key.ljust(32, b'\0')
    
    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt job payload."""
        json_data = json.dumps(data).encode('utf-8')
        
        if self.algorithm == "fernet":
            encrypted = self.fernet.encrypt(json_data)
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        
        elif self.algorithm == "aes":
            # Generate random IV
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
            encryptor = cipher.encryptor()  # type: ignore[no-untyped-call]
            
            # Pad data to block size
            pad_length = 16 - (len(json_data) % 16)
            padded_data = json_data + bytes([pad_length] * pad_length)
            
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and encrypted data
            combined = iv + encrypted
            return base64.urlsafe_b64encode(combined).decode('utf-8')
        
        raise ValueError(f"Unsupported encryption algorithm: {self.algorithm}")
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt job payload."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            if self.algorithm == "fernet":
                decrypted = self.fernet.decrypt(encrypted_bytes)
                return json.loads(decrypted.decode('utf-8'))  # type: ignore[no-any-return]
            
            elif self.algorithm == "aes":
                # Extract IV and encrypted data
                iv = encrypted_bytes[:16]
                encrypted_payload = encrypted_bytes[16:]
                
                cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
                decryptor = cipher.decryptor()  # type: ignore[no-untyped-call]
                
                decrypted_padded = decryptor.update(encrypted_payload) + decryptor.finalize()
                
                # Remove padding
                pad_length = decrypted_padded[-1]
                decrypted = decrypted_padded[:-pad_length]
                
                return json.loads(decrypted.decode('utf-8'))  # type: ignore[no-any-return]
            
            else:
                raise ValueError(f"Unsupported encryption algorithm: {self.algorithm}")
                
        except Exception as e:
            raise ValueError(f"Failed to decrypt job payload: {str(e)}")
    
    def _generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return os.urandom(32)
    
    @staticmethod
    def generate_key_for_env() -> str:
        """Generate a base64-encoded key for environment variables."""
        key = os.urandom(32)
        return base64.urlsafe_b64encode(key).decode('utf-8')


class JobSigner:
    """
    Job payload signing for integrity verification.
    """
    
    def __init__(self, secret_key: Optional[str] = None) -> None:
        self.secret_key: str = secret_key or os.getenv("QUEUE_SIGNING_KEY") or "default-insecure-key"
        self.algorithm = "sha256"
    
    def sign(self, payload: str) -> str:
        """Sign job payload."""
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"{payload}.{signature}"
    
    def verify(self, signed_payload: str) -> str:
        """Verify and extract job payload."""
        try:
            payload, signature = signed_payload.rsplit('.', 1)
        except ValueError:
            raise ValueError("Invalid signed payload format")
        
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Payload signature verification failed")
        
        return payload


class JobTokenizer:
    """
    Time-limited job tokens for secure job execution.
    """
    
    def __init__(self, secret_key: Optional[str] = None) -> None:
        self.secret_key: str = secret_key or os.getenv("QUEUE_TOKEN_KEY") or "default-token-key"
        self.signer = JobSigner(self.secret_key)
    
    def generate_token(self, job_id: str, expires_in: int = 3600) -> str:
        """Generate time-limited token for job execution."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        token_data = {
            "job_id": job_id,
            "expires_at": expires_at.timestamp(),
            "nonce": secrets.token_hex(16)
        }
        
        token_payload = base64.urlsafe_b64encode(
            json.dumps(token_data).encode('utf-8')
        ).decode('utf-8')
        
        return self.signer.sign(token_payload)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode job token."""
        try:
            payload = self.signer.verify(token)
            token_data = json.loads(
                base64.urlsafe_b64decode(payload.encode('utf-8')).decode('utf-8')
            )
            
            # Check expiration
            if token_data["expires_at"] < datetime.now(timezone.utc).timestamp():
                raise ValueError("Token has expired")
            
            return token_data  # type: ignore[no-any-return]
            
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")


class SecureJobPayload:
    """
    Secure job payload wrapper with encryption and signing.
    """
    
    def __init__(
        self,
        encrypt: bool = True,
        sign: bool = True,
        encryption_key: Optional[bytes] = None,
        signing_key: Optional[str] = None
    ) -> None:
        self.encrypt = encrypt
        self.sign = sign
        
        if encrypt:
            self.encryptor = JobEncryption(encryption_key)
        
        if sign:
            self.signer = JobSigner(signing_key)
    
    def secure_payload(self, payload: Dict[str, Any]) -> str:
        """Secure job payload with encryption and/or signing."""
        processed_payload = json.dumps(payload)
        
        if self.encrypt:
            processed_payload = self.encryptor.encrypt(payload)
        
        if self.sign:
            processed_payload = self.signer.sign(processed_payload)
        
        return processed_payload
    
    def unsecure_payload(self, secured_payload: str) -> Dict[str, Any]:
        """Decrypt and verify job payload."""
        processed_payload = secured_payload
        
        if self.sign:
            processed_payload = self.signer.verify(processed_payload)
        
        if self.encrypt:
            return self.encryptor.decrypt(processed_payload)
        else:
            return json.loads(processed_payload)  # type: ignore[no-any-return]


class JobAccessControl:
    """
    Access control for job execution based on permissions.
    """
    
    def __init__(self) -> None:
        self.job_permissions: Dict[str, List[str]] = {}
        self.user_permissions: Dict[str, List[str]] = {}
    
    def set_job_permissions(self, job_class: str, permissions: List[str]) -> None:
        """Set required permissions for job class."""
        self.job_permissions[job_class] = permissions
    
    def set_user_permissions(self, user_id: str, permissions: List[str]) -> None:
        """Set user permissions."""
        self.user_permissions[user_id] = permissions
    
    def can_execute_job(self, user_id: str, job: ShouldQueue) -> bool:
        """Check if user can execute job."""
        job_class = f"{job.__class__.__module__}.{job.__class__.__name__}"
        
        required_permissions = self.job_permissions.get(job_class, [])
        if not required_permissions:
            return True  # No permissions required
        
        user_permissions = self.user_permissions.get(user_id, [])
        
        return all(perm in user_permissions for perm in required_permissions)
    
    def can_dispatch_job(self, user_id: str, job: ShouldQueue) -> bool:
        """Check if user can dispatch job."""
        # For now, same as execute permission
        return self.can_execute_job(user_id, job)


class SecureJob:
    """
    Mixin for jobs with built-in security features.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.secure_payload = SecureJobPayload()
        self.tokenizer = JobTokenizer()
        self.access_control = JobAccessControl()
        self.required_permissions: List[str] = []
        self.sensitive_fields: List[str] = []
    
    def set_required_permissions(self, permissions: List[str]) -> SecureJob:
        """Set permissions required to execute this job."""
        self.required_permissions = permissions
        job_class = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.access_control.set_job_permissions(job_class, permissions)
        return self
    
    def set_sensitive_fields(self, fields: List[str]) -> SecureJob:
        """Mark fields as sensitive (will be encrypted)."""
        self.sensitive_fields = fields
        return self
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job with security features."""
        data = super().serialize()  # type: ignore[misc]
        
        # Extract sensitive data for encryption
        if self.sensitive_fields:
            sensitive_data = {}
            for field in self.sensitive_fields:
                if field in data.get("data", {}):
                    sensitive_data[field] = data["data"].pop(field)
            
            if sensitive_data:
                data["encrypted_data"] = self.secure_payload.encryptor.encrypt(sensitive_data)
        
        return data  # type: ignore[no-any-return]
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> SecureJob:
        """Deserialize job with security features."""
        job = super().deserialize(data)  # type: ignore[misc]
        
        # Decrypt sensitive data
        if "encrypted_data" in data and hasattr(job, 'secure_payload'):
            sensitive_data = job.secure_payload.encryptor.decrypt(data["encrypted_data"])
            
            # Restore sensitive fields to job data
            for field, value in sensitive_data.items():
                setattr(job, field, value)
        
        return job  # type: ignore[no-any-return]
    
    def can_be_executed_by(self, user_id: str) -> bool:
        """Check if user can execute this job."""
        return self.access_control.can_execute_job(user_id, self)  # type: ignore[arg-type]


class JobAuditLogger:
    """
    Audit logger for job security events.
    """
    
    def __init__(self, log_file: Optional[str] = None) -> None:
        self.log_file = log_file or "storage/logs/job_security.log"
    
    def log_security_event(
        self,
        event_type: str,
        job_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log security-related job event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "job_id": job_id,
            "user_id": user_id,
            "details": details or {}
        }
        
        # In production, you'd write to a proper logging system
        print(f"SECURITY AUDIT: {json.dumps(event)}")
    
    def log_permission_denied(self, job_id: str, user_id: str, required_permissions: List[str]) -> None:
        """Log permission denied event."""
        self.log_security_event(
            "permission_denied",
            job_id,
            user_id,
            {"required_permissions": required_permissions}
        )
    
    def log_encryption_error(self, job_id: str, error: str) -> None:
        """Log encryption/decryption error."""
        self.log_security_event(
            "encryption_error",
            job_id,
            details={"error": error}
        )


# Global instances
global_job_encryption = JobEncryption()
global_job_signer = JobSigner()
global_job_tokenizer = JobTokenizer()
global_access_control = JobAccessControl()
global_audit_logger = JobAuditLogger()