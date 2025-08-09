from __future__ import annotations

import os
import json
import base64
import hmac
import hashlib
from typing import Any, Dict, Optional, Union, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets


class EncryptionException(Exception):
    """Exception raised when encryption/decryption fails."""
    pass


class Encrypter:
    """Laravel-style encryption service."""
    
    def __init__(self, key: str, cipher: str = 'AES-256-CBC') -> None:
        self.key = key
        self.cipher = cipher
        self._fernet = self._create_fernet_instance()
    
    def _create_fernet_instance(self) -> Fernet:
        """Create Fernet instance from key."""
        # Convert Laravel app key to Fernet key
        if self.key.startswith('base64:'):
            key_data = base64.b64decode(self.key[7:])
        else:
            key_data = self.key.encode()
        
        # Derive a 32-byte key for Fernet
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'laravel_salt',  # Static salt for consistency
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_data))
        
        return Fernet(derived_key)
    
    def encrypt(self, value: Any, serialize: bool = True) -> str:
        """Encrypt a value."""
        try:
            # Serialize value if needed
            if serialize:
                if isinstance(value, (dict, list)):
                    payload = json.dumps(value, separators=(',', ':'))
                else:
                    payload = str(value)
            else:
                payload = value
            
            # Encrypt the payload
            encrypted_data = self._fernet.encrypt(payload.encode())
            
            # Create Laravel-style encrypted payload
            encrypted_payload = {
                'iv': base64.b64encode(os.urandom(16)).decode(),
                'value': base64.b64encode(encrypted_data).decode(),
                'mac': None
            }
            
            # Add MAC for integrity
            payload_json = json.dumps(encrypted_payload, separators=(',', ':'))
            mac = self._create_mac(payload_json)
            encrypted_payload['mac'] = mac
            
            # Base64 encode the final payload
            return base64.b64encode(
                json.dumps(encrypted_payload, separators=(',', ':')).encode()
            ).decode()
            
        except Exception as e:
            raise EncryptionException(f"Encryption failed: {str(e)}")
    
    def decrypt(self, payload: str, unserialize: bool = True) -> Any:
        """Decrypt a value."""
        try:
            # Decode the payload
            try:
                decoded_payload = base64.b64decode(payload.encode()).decode()
                data = json.loads(decoded_payload)
            except (ValueError, json.JSONDecodeError):
                raise EncryptionException("Invalid encrypted payload format")
            
            # Verify MAC
            if not self._verify_mac(data):
                raise EncryptionException("MAC verification failed")
            
            # Decrypt the value
            encrypted_data = base64.b64decode(data['value'].encode())
            decrypted_data = self._fernet.decrypt(encrypted_data)
            decrypted_value = decrypted_data.decode()
            
            # Unserialize if needed
            if unserialize:
                try:
                    # Try to parse as JSON first
                    return json.loads(decrypted_value)
                except json.JSONDecodeError:
                    # Return as string if not valid JSON
                    return decrypted_value
            else:
                return decrypted_value
                
        except Exception as e:
            raise EncryptionException(f"Decryption failed: {str(e)}")
    
    def encrypt_string(self, value: str) -> str:
        """Encrypt a string without serialization."""
        return self.encrypt(value, serialize=False)
    
    def decrypt_string(self, payload: str) -> str:
        """Decrypt a string without unserialization."""
        result = self.decrypt(payload, unserialize=False)
        return str(result)
    
    def _create_mac(self, payload: str) -> str:
        """Create MAC for payload integrity."""
        mac_key = f"laravel_session.{self.key}"
        return hmac.new(
            mac_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_mac(self, data: Dict[str, Any]) -> bool:
        """Verify MAC for payload integrity."""
        if 'mac' not in data:
            return False
        
        provided_mac = data['mac']
        
        # Create payload without MAC for verification
        payload_data = {k: v for k, v in data.items() if k != 'mac'}
        payload_data['mac'] = None  # Set to None for consistent MAC calculation
        payload_json = json.dumps(payload_data, separators=(',', ':'))
        
        expected_mac = self._create_mac(payload_json)
        
        return hmac.compare_digest(provided_mac, expected_mac)
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key."""
        key = base64.b64encode(os.urandom(32)).decode()
        return f"base64:{key}"
    
    def supported(self, cipher: str) -> bool:
        """Check if cipher is supported."""
        return cipher in ['AES-256-CBC', 'AES-128-CBC']


class EncryptCookies:
    """Helper class for encrypting cookies."""
    
    def __init__(self, encrypter: Encrypter, except_cookies: Optional[List[str]] = None) -> None:
        self.encrypter = encrypter
        self.except_cookies = except_cookies or []
    
    def encrypt(self, name: str, value: str) -> str:
        """Encrypt cookie value if not in exceptions."""
        if name in self.except_cookies:
            return value
        
        return self.encrypter.encrypt_string(value)
    
    def decrypt(self, name: str, value: str) -> Optional[str]:
        """Decrypt cookie value if not in exceptions."""
        if name in self.except_cookies:
            return value
        
        try:
            return self.encrypter.decrypt_string(value)
        except EncryptionException:
            return None


class EncryptionManager:
    """Manager for encryption services."""
    
    def __init__(self, default_key: Optional[str] = None) -> None:
        self.default_key = default_key or self._generate_default_key()
        self._encrypters: Dict[str, Encrypter] = {}
    
    def _generate_default_key(self) -> str:
        """Generate default encryption key."""
        return Encrypter.generate_key()
    
    def driver(self, name: str = 'default') -> Encrypter:
        """Get encrypter instance."""
        if name not in self._encrypters:
            key = self.default_key if name == 'default' else self._get_key_for_driver(name)
            self._encrypters[name] = Encrypter(key)
        
        return self._encrypters[name]
    
    def _get_key_for_driver(self, name: str) -> str:
        """Get encryption key for specific driver."""
        # In a real app, this would come from config
        return self.default_key
    
    def encrypt(self, value: Any, serialize: bool = True) -> str:
        """Encrypt using default driver."""
        return self.driver().encrypt(value, serialize)
    
    def decrypt(self, payload: str, unserialize: bool = True) -> Any:
        """Decrypt using default driver."""
        return self.driver().decrypt(payload, unserialize)
    
    def encrypt_string(self, value: str) -> str:
        """Encrypt string using default driver."""
        return self.driver().encrypt_string(value)
    
    def decrypt_string(self, payload: str) -> str:
        """Decrypt string using default driver."""
        return self.driver().decrypt_string(payload)


# Global encryption manager
encryption_manager = EncryptionManager()


def encrypt(value: Any, serialize: bool = True) -> str:
    """Encrypt a value."""
    return encryption_manager.encrypt(value, serialize)


def decrypt(payload: str, unserialize: bool = True) -> Any:
    """Decrypt a value."""
    return encryption_manager.decrypt(payload, unserialize)


def encrypt_string(value: str) -> str:
    """Encrypt a string."""
    return encryption_manager.encrypt_string(value)


def decrypt_string(payload: str) -> str:
    """Decrypt a string."""
    return encryption_manager.decrypt_string(payload)