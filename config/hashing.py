from __future__ import annotations

import os
from typing import Dict, Any

# Default hash driver
default = os.getenv('HASH_DRIVER', 'bcrypt')

# Hash drivers configuration
drivers: Dict[str, Dict[str, Any]] = {
    'bcrypt': {
        'driver': 'bcrypt',
        'rounds': int(os.getenv('BCRYPT_ROUNDS', 12)),
        'verify': True,
    },
    
    'argon': {
        'driver': 'argon',
        'memory': int(os.getenv('ARGON_MEMORY', 65536)),  # 64 MB
        'threads': int(os.getenv('ARGON_THREADS', 1)),
        'time': int(os.getenv('ARGON_TIME', 4)),
        'verify': True,
    },
    
    'argon2id': {
        'driver': 'argon2id',
        'memory': int(os.getenv('ARGON_MEMORY', 65536)),  # 64 MB
        'threads': int(os.getenv('ARGON_THREADS', 1)),
        'time': int(os.getenv('ARGON_TIME', 4)),
        'verify': True,
    },
    
    'pbkdf2': {
        'driver': 'pbkdf2',
        'algorithm': os.getenv('PBKDF2_ALGORITHM', 'sha256'),
        'iterations': int(os.getenv('PBKDF2_ITERATIONS', 100000)),
        'verify': True,
    },
    
    'sha256': {
        'driver': 'sha256',
        'salt': os.getenv('SHA256_SALT', ''),
        'verify': True,
    },
    
    'md5': {
        'driver': 'md5',
        'verify': False,  # MD5 is deprecated
    },
}

# Rehashing configuration
auto_rehash = True
rehash_on_login = True

# Password validation rules
password_min_length = 8
password_require_uppercase = True
password_require_lowercase = True
password_require_numbers = True
password_require_symbols = True
password_max_length = 255

# Common weak passwords to reject
weak_passwords = [
    'password', '123456', '123456789', 'qwerty', 'abc123',
    'password123', 'admin', 'letmein', 'welcome', 'monkey',
    'dragon', 'master', 'shadow', 'superman', 'michael',
    'football', 'baseball', 'batman', 'trustno1', 'jordan23'
]

# Password history
remember_password_history = 5
password_history_days = 90

# Rate limiting for password attempts
max_password_attempts = 5
lockout_duration = 900  # 15 minutes in seconds
progressive_lockout = True

# Password complexity scoring
complexity_min_score = 3  # Out of 5
complexity_factors = {
    'length': {'min': 8, 'max': 20, 'weight': 2},
    'uppercase': {'weight': 1},
    'lowercase': {'weight': 1},
    'numbers': {'weight': 1},
    'symbols': {'weight': 2},
    'unique_chars': {'min': 6, 'weight': 1},
    'no_common_patterns': {'weight': 2},
    'no_dictionary_words': {'weight': 1},
}

# Encryption for sensitive data
encryption_key = os.getenv('APP_KEY', '')
encryption_cipher = 'aes-256-cbc'