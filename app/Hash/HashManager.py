from __future__ import annotations

import hashlib
import hmac
import bcrypt
import secrets
from typing import Any, Dict, Optional, Union, Callable
from abc import ABC, abstractmethod


class Hasher(ABC):
    """Abstract hasher interface."""
    
    @abstractmethod
    def make(self, value: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Hash the given value."""
        pass
    
    @abstractmethod
    def check(self, value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the given value matches the hash."""
        pass
    
    @abstractmethod
    def needs_rehash(self, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the hash needs to be rehashed."""
        pass


class BcryptHasher(Hasher):
    """Bcrypt password hasher."""
    
    def __init__(self, rounds: int = 12) -> None:
        self.rounds = rounds
    
    def make(self, value: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Hash the given value using bcrypt."""
        rounds = options.get('rounds', self.rounds) if options else self.rounds
        salt = bcrypt.gensalt(rounds=rounds)
        return bcrypt.hashpw(value.encode('utf-8'), salt).decode('utf-8')
    
    def check(self, value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the given value matches the bcrypt hash."""
        try:
            return bcrypt.checkpw(value.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def needs_rehash(self, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the bcrypt hash needs to be rehashed."""
        try:
            info = bcrypt.hashpw(b'test', hashed.encode('utf-8'))
            current_rounds = int(hashed.split('$')[2])
            desired_rounds = options.get('rounds', self.rounds) if options else self.rounds
            return bool(current_rounds < desired_rounds)
        except Exception:
            return True


class MD5Hasher(Hasher):
    """MD5 hasher (not recommended for passwords)."""
    
    def make(self, value: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Hash the given value using MD5."""
        return hashlib.md5(value.encode('utf-8')).hexdigest()
    
    def check(self, value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the given value matches the MD5 hash."""
        return self.make(value) == hashed
    
    def needs_rehash(self, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """MD5 hashes always need rehashing."""
        return True


class SHA256Hasher(Hasher):
    """SHA256 hasher."""
    
    def make(self, value: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Hash the given value using SHA256."""
        salt = options.get('salt', '') if options else ''
        return hashlib.sha256((salt + value).encode('utf-8')).hexdigest()
    
    def check(self, value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the given value matches the SHA256 hash."""
        return self.make(value, options) == hashed
    
    def needs_rehash(self, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """SHA256 hashes don't need rehashing."""
        return False


class PBKDF2Hasher(Hasher):
    """PBKDF2 hasher."""
    
    def __init__(self, iterations: int = 100000, hash_name: str = 'sha256') -> None:
        self.iterations = iterations
        self.hash_name = hash_name
    
    def make(self, value: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Hash the given value using PBKDF2."""
        iterations = options.get('iterations', self.iterations) if options else self.iterations
        hash_name = options.get('hash_name', self.hash_name) if options else self.hash_name
        salt_bytes = options.get('salt') if options else secrets.token_bytes(32)
        
        if isinstance(salt_bytes, str):
            salt_bytes = salt_bytes.encode('utf-8')
        elif salt_bytes is None:
            salt_bytes = secrets.token_bytes(32)
        
        dk = hashlib.pbkdf2_hmac(hash_name, value.encode('utf-8'), salt_bytes, iterations)
        
        # Format: algorithm$iterations$salt$hash
        salt_b64 = salt_bytes.hex()
        hash_b64 = dk.hex()
        return f"pbkdf2_{hash_name}${iterations}${salt_b64}${hash_b64}"
    
    def check(self, value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the given value matches the PBKDF2 hash."""
        try:
            parts = hashed.split('$')
            if len(parts) != 4:
                return False
            
            algorithm, iterations_str, salt_hex, hash_hex = parts
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            
            # Extract hash algorithm
            hash_name = algorithm.replace('pbkdf2_', '')
            
            # Compute hash
            dk = hashlib.pbkdf2_hmac(hash_name, value.encode('utf-8'), salt, iterations)
            
            return hmac.compare_digest(dk, expected_hash)
        except Exception:
            return False
    
    def needs_rehash(self, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the PBKDF2 hash needs to be rehashed."""
        try:
            parts = hashed.split('$')
            if len(parts) != 4:
                return True
            
            iterations = int(parts[1])
            desired_iterations = options.get('iterations', self.iterations) if options else self.iterations
            return bool(iterations < desired_iterations)
        except Exception:
            return True


class HashManager:
    """Laravel-style hash manager."""
    
    def __init__(self, default_driver: str = 'bcrypt') -> None:
        self._default_driver = default_driver
        self._drivers: Dict[str, Hasher] = {}
        self._custom_creators: Dict[str, Callable[[], Hasher]] = {}
        
        # Register default drivers
        self._register_default_drivers()
    
    def _register_default_drivers(self) -> None:
        """Register the default hash drivers."""
        self._drivers['bcrypt'] = BcryptHasher()
        self._drivers['md5'] = MD5Hasher()
        self._drivers['sha256'] = SHA256Hasher()
        self._drivers['pbkdf2'] = PBKDF2Hasher()
    
    def driver(self, name: Optional[str] = None) -> Hasher:
        """Get a hash driver."""
        name = name or self._default_driver
        
        if name not in self._drivers:
            self._drivers[name] = self._create_driver(name)
        
        return self._drivers[name]
    
    def _create_driver(self, name: str) -> Hasher:
        """Create a hash driver."""
        if name in self._custom_creators:
            creator = self._custom_creators[name]
            return creator()
        
        if name == 'bcrypt':
            return BcryptHasher()
        elif name == 'md5':
            return MD5Hasher()
        elif name == 'sha256':
            return SHA256Hasher()
        elif name == 'pbkdf2':
            return PBKDF2Hasher()
        else:
            raise ValueError(f"Hash driver '{name}' not supported")
    
    def extend(self, driver: str, creator: Callable[[], Hasher]) -> None:
        """Register a custom hash driver."""
        self._custom_creators[driver] = creator
    
    def make(self, value: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Hash the given value using the default driver."""
        return self.driver().make(value, options)
    
    def check(self, value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the given value matches the hash using the default driver."""
        return self.driver().check(value, hashed, options)
    
    def needs_rehash(self, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the hash needs to be rehashed using the default driver."""
        return self.driver().needs_rehash(hashed, options)
    
    def info(self, hashed: str) -> Dict[str, Any]:
        """Get information about the given hash."""
        if hashed.startswith('$2'):
            # Bcrypt hash
            parts = hashed.split('$')
            if len(parts) >= 4:
                return {
                    'algo': 'bcrypt',
                    'algoName': 'CRYPT_BLOWFISH',
                    'options': {
                        'cost': int(parts[2])
                    }
                }
        elif 'pbkdf2_' in hashed:
            # PBKDF2 hash
            parts = hashed.split('$')
            if len(parts) == 4:
                return {
                    'algo': 'pbkdf2',
                    'algoName': 'PBKDF2',
                    'options': {
                        'algorithm': parts[0],
                        'iterations': int(parts[1])
                    }
                }
        elif len(hashed) == 32:
            # Likely MD5
            return {
                'algo': 'md5',
                'algoName': 'MD5',
                'options': {}
            }
        elif len(hashed) == 64:
            # Likely SHA256
            return {
                'algo': 'sha256',
                'algoName': 'SHA256',
                'options': {}
            }
        
        return {
            'algo': 'unknown',
            'algoName': 'UNKNOWN',
            'options': {}
        }
    
    def get_default_driver(self) -> str:
        """Get the default hash driver."""
        return self._default_driver
    
    def set_default_driver(self, name: str) -> None:
        """Set the default hash driver."""
        self._default_driver = name


# Global hash manager instance
hash_manager_instance: Optional[HashManager] = None


def get_hash_manager() -> HashManager:
    """Get the global hash manager instance."""
    global hash_manager_instance
    if hash_manager_instance is None:
        hash_manager_instance = HashManager()
    return hash_manager_instance


def hash_make(value: str, options: Optional[Dict[str, Any]] = None) -> str:
    """Hash the given value."""
    return get_hash_manager().make(value, options)


def hash_check(value: str, hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
    """Check if the given value matches the hash."""
    return get_hash_manager().check(value, hashed, options)


def hash_needs_rehash(hashed: str, options: Optional[Dict[str, Any]] = None) -> bool:
    """Check if the hash needs to be rehashed."""
    return get_hash_manager().needs_rehash(hashed, options)


def hash_info(hashed: str) -> Dict[str, Any]:
    """Get information about the given hash."""
    return get_hash_manager().info(hashed)