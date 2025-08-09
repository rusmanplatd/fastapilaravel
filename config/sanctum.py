from __future__ import annotations

"""
Laravel Sanctum Configuration

Configure SPA authentication, API tokens, and security settings.
"""

import os
from typing import List, Dict, Any, Optional


# Stateful domains for SPA authentication
# These domains can make authenticated requests using cookies/sessions
STATEFUL_DOMAINS = [
    'localhost',
    'localhost:3000',  # React/Vue dev server
    '127.0.0.1',
    '127.0.0.1:3000',
    os.getenv('FRONTEND_URL', '').replace('http://', '').replace('https://', ''),
]

# Remove empty domains
STATEFUL_DOMAINS = [domain for domain in STATEFUL_DOMAINS if domain]

# CORS configuration for Sanctum
CORS_CONFIG = {
    'allow_origins': [
        'http://localhost:3000',
        'https://localhost:3000',
        os.getenv('FRONTEND_URL', 'http://localhost:3000'),
    ],
    'allow_credentials': True,
    'allow_methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    'allow_headers': ['*'],
    'expose_headers': ['X-Csrf-Token'],
}

# Token configuration
TOKEN_CONFIG = {
    # Default token name for SPA authentication
    'spa_token_name': 'SPA Token',
    
    # Token prefix (optional, e.g. 'myapp_')
    'token_prefix': os.getenv('SANCTUM_TOKEN_PREFIX', ''),
    
    # Default token expiration (None = never expires)
    'expiration': None,  # Set to number of minutes for expiration
    
    # Token length (in bytes, will be hex encoded so actual length is 2x)
    'token_length': 20,  # Results in 40-character token
    
    # Hash algorithm for tokens
    'hash_algorithm': 'sha256',
}

# Authentication configuration
AUTH_CONFIG = {
    # Authorization header name
    'header': 'Authorization',
    
    # Bearer prefix for authorization header
    'prefix': 'Bearer',
    
    # Cookie name for SPA authentication
    'cookie': os.getenv('SANCTUM_COOKIE_NAME', 'laravel_token'),
    
    # Cookie configuration
    'cookie_config': {
        'httponly': True,
        'secure': os.getenv('APP_ENV', 'development') == 'production',
        'samesite': 'lax',
        'max_age': int(os.getenv('SANCTUM_COOKIE_LIFETIME', '525600')) * 60,  # 1 year in seconds
    },
    
    # CSRF configuration
    'csrf_cookie': 'XSRF-TOKEN',
    'csrf_header': 'X-CSRF-TOKEN',
}

# Middleware configuration
MIDDLEWARE_CONFIG = {
    # Middleware name
    'middleware': 'auth:sanctum',
    
    # Guard name
    'guard': 'sanctum',
    
    # Rate limiting
    'rate_limit': {
        'enabled': True,
        'max_requests': 60,
        'per_minutes': 1,
    },
}

# Abilities configuration
ABILITIES_CONFIG = {
    # Default abilities for SPA tokens
    'spa_abilities': ['*'],
    
    # Default abilities for API tokens
    'api_abilities': ['read'],
    
    # Pre-defined abilities
    'defined_abilities': [
        'read',
        'write',
        'create',
        'update',
        'delete',
        'admin',
        'posts:create',
        'posts:read',
        'posts:update',
        'posts:delete',
        'users:read',
        'users:update',
        'users:delete',
    ],
}

# Database configuration
DATABASE_CONFIG = {
    # Personal access tokens table
    'tokens_table': 'personal_access_tokens',
    
    # Token cleanup configuration
    'cleanup': {
        'enabled': True,
        'schedule': '0 2 * * *',  # Run at 2 AM daily
        'keep_days': 365,  # Keep tokens for 1 year after expiration
    },
}

# Security configuration
SECURITY_CONFIG = {
    # Token rotation
    'rotate_tokens': False,
    
    # IP address validation
    'validate_ip': False,
    
    # User agent validation
    'validate_user_agent': False,
    
    # Maximum tokens per user
    'max_tokens_per_user': None,  # No limit
    
    # Prune expired tokens automatically
    'prune_expired': True,
    
    # Hash tokens in database (recommended)
    'hash_tokens': True,
}

# Logging configuration
LOGGING_CONFIG = {
    # Log token creation
    'log_token_creation': os.getenv('SANCTUM_LOG_TOKENS', 'false').lower() == 'true',
    
    # Log token usage
    'log_token_usage': os.getenv('SANCTUM_LOG_USAGE', 'false').lower() == 'true',
    
    # Log failed authentication attempts
    'log_failed_auth': True,
    
    # Log level for Sanctum events
    'log_level': os.getenv('SANCTUM_LOG_LEVEL', 'INFO'),
}

# API configuration
API_CONFIG = {
    # API prefix
    'api_prefix': '/api/v1',
    
    # Token endpoints
    'endpoints': {
        'tokens': '/auth/tokens',
        'revoke': '/auth/tokens/revoke',
        'revoke_all': '/auth/tokens/revoke-all',
        'current_user': '/auth/user',
    },
    
    # Response format
    'response_format': {
        'token_key': 'access_token',
        'user_key': 'user',
        'abilities_key': 'abilities',
    },
}

# Development configuration
DEVELOPMENT_CONFIG = {
    # Enable debug mode
    'debug': os.getenv('APP_ENV', 'development') == 'development',
    
    # Allow insecure connections in development
    'allow_insecure': os.getenv('APP_ENV', 'development') == 'development',
    
    # Test tokens for development
    'test_tokens': {
        'enabled': os.getenv('APP_ENV', 'development') == 'development',
        'tokens': {
            'test-token': {
                'user_id': 1,
                'abilities': ['*'],
                'expires_at': None,
            },
        },
    },
}

# Performance configuration
PERFORMANCE_CONFIG = {
    # Cache token lookups
    'cache_tokens': True,
    
    # Cache TTL in seconds
    'cache_ttl': 300,  # 5 minutes
    
    # Use Redis for token storage
    'use_redis': os.getenv('SANCTUM_USE_REDIS', 'false').lower() == 'true',
    
    # Redis configuration
    'redis_config': {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', '6379')),
        'db': int(os.getenv('SANCTUM_REDIS_DB', '0')),
        'password': os.getenv('REDIS_PASSWORD'),
    },
}

# Validation configuration
VALIDATION_CONFIG = {
    # Token name validation
    'token_name': {
        'required': True,
        'min_length': 1,
        'max_length': 255,
        'pattern': r'^[a-zA-Z0-9\s\-_]+$',
    },
    
    # Abilities validation
    'abilities': {
        'validate_existence': True,
        'allow_wildcards': True,
        'max_abilities': 100,
    },
}