"""ULID Utilities

This module provides ULID (Universally Unique Lexicographically Sortable Identifier)
utility functions for the application.
"""

from __future__ import annotations

import uuid
import time
import os
from typing import Optional
from datetime import datetime


class ULIDUtils:
    """Utility class for ULID operations."""
    
    # Base32 encoding (Crockford's Base32)
    ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    TIMESTAMP_LENGTH = 10
    RANDOMNESS_LENGTH = 16
    ULID_LENGTH = TIMESTAMP_LENGTH + RANDOMNESS_LENGTH
    
    @staticmethod
    def generate() -> str:
        """
        Generate a new ULID.
        
        Returns:
            A ULID string (26 characters)
        """
        timestamp = int(time.time() * 1000)  # milliseconds
        randomness = os.urandom(10)  # 10 bytes = 80 bits
        
        return ULIDUtils._encode_timestamp(timestamp) + ULIDUtils._encode_randomness(randomness)
    
    @staticmethod
    def generate_at_time(timestamp: datetime) -> str:
        """
        Generate a ULID for a specific timestamp.
        
        Args:
            timestamp: The datetime to use for the ULID
            
        Returns:
            A ULID string (26 characters)
        """
        ts_ms = int(timestamp.timestamp() * 1000)
        randomness = os.urandom(10)
        
        return ULIDUtils._encode_timestamp(ts_ms) + ULIDUtils._encode_randomness(randomness)
    
    @staticmethod
    def is_valid(ulid: str) -> bool:
        """
        Check if a string is a valid ULID.
        
        Args:
            ulid: The string to validate
            
        Returns:
            True if valid ULID, False otherwise
        """
        if not isinstance(ulid, str):
            return False
            
        if len(ulid) != ULIDUtils.ULID_LENGTH:
            return False
            
        return all(char in ULIDUtils.ENCODING for char in ulid)
    
    @staticmethod
    def extract_timestamp(ulid: str) -> Optional[datetime]:
        """
        Extract timestamp from ULID.
        
        Args:
            ulid: The ULID string
            
        Returns:
            DateTime object or None if invalid ULID
        """
        if not ULIDUtils.is_valid(ulid):
            return None
            
        timestamp_part = ulid[:ULIDUtils.TIMESTAMP_LENGTH]
        timestamp_ms = ULIDUtils._decode_timestamp(timestamp_part)
        
        return datetime.fromtimestamp(timestamp_ms / 1000)
    
    @staticmethod
    def _encode_timestamp(timestamp_ms: int) -> str:
        """Encode timestamp to base32 string."""
        result = ""
        for _ in range(ULIDUtils.TIMESTAMP_LENGTH):
            result = ULIDUtils.ENCODING[timestamp_ms % 32] + result
            timestamp_ms //= 32
        return result
    
    @staticmethod
    def _encode_randomness(randomness: bytes) -> str:
        """Encode randomness bytes to base32 string."""
        # Convert bytes to integer
        value = int.from_bytes(randomness, byteorder='big')
        
        result = ""
        for _ in range(ULIDUtils.RANDOMNESS_LENGTH):
            result = ULIDUtils.ENCODING[value % 32] + result
            value //= 32
            
        return result
    
    @staticmethod
    def _decode_timestamp(encoded: str) -> int:
        """Decode base32 timestamp string to milliseconds."""
        value = 0
        for char in encoded:
            value = value * 32 + ULIDUtils.ENCODING.index(char)
        return value
    
    @staticmethod
    def generate_client_id() -> str:
        """Generate a client ID (shorter ULID for OAuth2 clients)."""
        return ULIDUtils.generate()[:20]  # 20 characters for client IDs
    
    @staticmethod
    def generate_token_id() -> str:
        """Generate a token ID (full ULID for tokens)."""
        return ULIDUtils.generate()
    
    @staticmethod
    def generate_code_id() -> str:
        """Generate an authorization code ID."""
        return ULIDUtils.generate()
    
    @staticmethod
    def generate_scope_id() -> str:
        """Generate a scope ID (shorter for readability)."""
        return ULIDUtils.generate()[:16]  # 16 characters for scope IDs


def generate_ulid() -> str:
    """Convenience function to generate a ULID."""
    return ULIDUtils.generate()


def is_valid_ulid(ulid: str) -> bool:
    """Convenience function to validate a ULID."""
    return ULIDUtils.is_valid(ulid)


# Type alias for ULID
ULID = str