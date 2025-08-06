from __future__ import annotations

import os
from typing import Optional, List


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "FastAPI Laravel")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./storage/database.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    
    # Password Reset
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1"))
    
    # Email Verification
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = int(os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS", "24"))
    
    # CORS
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # API
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    
    # Email Settings (for future implementation)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    SMTP_SSL: bool = os.getenv("SMTP_SSL", "false").lower() == "true"
    
    # Application URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")


settings = Settings()