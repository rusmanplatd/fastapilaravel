from __future__ import annotations

import hashlib
import bcrypt
from typing import Any, Optional


class HashCast:
    """Inbound-only cast for hashing sensitive data like passwords."""
    
    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Optional[str]:
        """Hash the value using bcrypt."""
        if value is None:
            return None
        
        # If value is already hashed (starts with $2b$), return as is
        if isinstance(value, str) and value.startswith('$2b$'):
            return value
        
        # Hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(str(value).encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        if not hashed_password:
            return False
        
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False


class MD5HashCast:
    """Cast for MD5 hashing (not recommended for passwords)."""
    
    def get(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Optional[str]:
        """Return the hash as is."""
        return value  # type: ignore[no-any-return]
    
    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Optional[str]:
        """Hash the value using MD5."""
        if value is None:
            return None
        
        return hashlib.md5(str(value).encode()).hexdigest()