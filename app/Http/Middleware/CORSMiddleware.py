from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING, List, Union
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

# Explicit export for mypy
__all__ = ['FastAPICORSMiddleware', 'add_cors_middleware']


def add_cors_middleware(app: FastAPI) -> None:
    """
    Add CORS middleware with production-ready configuration.
    
    Configuration is loaded from environment variables:
    - CORS_ALLOWED_ORIGINS: Comma-separated list of allowed origins
    - CORS_ALLOW_CREDENTIALS: Whether to allow credentials (default: false)
    - CORS_ALLOWED_METHODS: Comma-separated list of allowed methods (default: GET,POST,PUT,DELETE)
    - CORS_ALLOWED_HEADERS: Comma-separated list of allowed headers
    - CORS_EXPOSE_HEADERS: Comma-separated list of headers to expose
    - CORS_MAX_AGE: Preflight cache duration in seconds (default: 86400)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get configuration from environment variables
        allowed_origins = _get_allowed_origins()
        allow_credentials = os.getenv('CORS_ALLOW_CREDENTIALS', 'false').lower() == 'true'
        allowed_methods = _get_list_from_env('CORS_ALLOWED_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
        allowed_headers = _get_list_from_env('CORS_ALLOWED_HEADERS', ['*'])
        expose_headers = _get_list_from_env('CORS_EXPOSE_HEADERS', [])
        max_age = int(os.getenv('CORS_MAX_AGE', '86400'))
        
        # Security warning for wildcard origins in production
        if '*' in allowed_origins and os.getenv('APP_ENV') == 'production':
            logger.warning("CORS wildcard origins detected in production environment. This may pose security risks.")
        
        app.add_middleware(
            FastAPICORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=allow_credentials,
            allow_methods=allowed_methods,
            allow_headers=allowed_headers,
            expose_headers=expose_headers,
            max_age=max_age,
        )
        
        logger.info(f"CORS middleware configured with origins: {allowed_origins}")
        
    except Exception as e:
        logger.error(f"Failed to configure CORS middleware: {e}")
        # Fallback to basic configuration
        app.add_middleware(
            FastAPICORSMiddleware,
            allow_origins=["http://localhost:3000"],  # Safe default
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )


def _get_allowed_origins() -> List[str]:
    """Get allowed origins from environment variable or return safe defaults."""
    origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '')
    
    if origins_env:
        return [origin.strip() for origin in origins_env.split(',') if origin.strip()]
    
    # Safe defaults based on environment
    environment = os.getenv('APP_ENV', 'production')
    
    if environment == 'development':
        return [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ]
    elif environment == 'testing':
        return ["http://localhost:3000"]
    else:
        # Production - no wildcards by default
        return []


def _get_list_from_env(env_var: str, default: List[str]) -> List[str]:
    """Get a list from environment variable or return default."""
    value = os.getenv(env_var, '')
    
    if value:
        return [item.strip() for item in value.split(',') if item.strip()]
    
    return default