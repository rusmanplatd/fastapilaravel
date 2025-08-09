from __future__ import annotations

from .HashManager import (
    HashManager,
    Hasher,
    BcryptHasher,
    MD5Hasher,
    SHA256Hasher,
    PBKDF2Hasher,
    get_hash_manager,
    hash_make,
    hash_check,
    hash_needs_rehash,
    hash_info
)

# Alias for Laravel-style usage
Hash = HashManager

__all__ = [
    'HashManager',
    'Hash',
    'Hasher',
    'BcryptHasher',
    'MD5Hasher',
    'SHA256Hasher',
    'PBKDF2Hasher',
    'get_hash_manager',
    'hash_make',
    'hash_check',
    'hash_needs_rehash',
    'hash_info'
]