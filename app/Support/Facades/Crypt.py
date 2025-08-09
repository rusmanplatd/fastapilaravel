from __future__ import annotations

from typing import Any
from app.Encryption.Encrypter import encryption_manager


class Crypt:
    """Laravel-style Crypt facade."""
    
    @staticmethod
    def encrypt(value: Any, serialize: bool = True) -> str:
        """Encrypt a value."""
        return encryption_manager.encrypt(value, serialize)
    
    @staticmethod
    def decrypt(payload: str, unserialize: bool = True) -> Any:
        """Decrypt a value."""
        return encryption_manager.decrypt(payload, unserialize)
    
    @staticmethod
    def encrypt_string(value: str) -> str:
        """Encrypt a string without serialization."""
        return encryption_manager.encrypt_string(value)
    
    @staticmethod
    def decrypt_string(payload: str) -> str:
        """Decrypt a string without unserialization."""
        return encryption_manager.decrypt_string(payload)
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key."""
        from app.Encryption.Encrypter import Encrypter
        return Encrypter.generate_key()
    
    @staticmethod
    def driver(name: str = 'default') -> Any:
        """Get encrypter driver."""
        return encryption_manager.driver(name)