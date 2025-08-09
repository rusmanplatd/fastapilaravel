from __future__ import annotations

import base64
from typing import Any, Optional, Dict
from cryptography.fernet import Fernet
import os


class EncryptedCast:
    """Cast for encrypting and decrypting sensitive data."""
    
    def __init__(self) -> None:
        # In production, get this from environment or config
        self.key = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
        if isinstance(self.key, str):
            self.key = self.key.encode()
        self.cipher = Fernet(self.key)
    
    def get(self, model: Any, key: str, value: Any, attributes: Dict[str, Any]) -> Optional[str]:
        """Decrypt the value."""
        if value is None:
            return None
        
        try:
            if isinstance(value, str):
                value = value.encode()
            return self.cipher.decrypt(value).decode()
        except Exception:
            # Return original value if decryption fails
            return value if isinstance(value, str) else str(value)
    
    def set(self, model: Any, key: str, value: Any, attributes: Dict[str, Any]) -> Optional[str]:
        """Encrypt the value."""
        if value is None:
            return None
        
        try:
            encrypted = self.cipher.encrypt(str(value).encode())
            return base64.b64encode(encrypted).decode()
        except Exception:
            # Return original value if encryption fails
            return str(value)