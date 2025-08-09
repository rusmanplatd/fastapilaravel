from __future__ import annotations

import os
from typing import Generator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

__all__ = [
    "engine", "Base", "SessionLocal", "get_database", "get_db", "get_db_session", 
    "create_tables", "DATABASE_URL", "SQLALCHEMY_DATABASE_URL", "DATABASE_CONFIG"
]


def get_database_url() -> str:
    """Build database URL based on connection type."""
    connection = os.getenv('DB_CONNECTION', 'postgresql')
    
    if connection == 'postgresql':
        user = os.getenv('DB_USERNAME', 'postgres')
        password = os.getenv('DB_PASSWORD', 'password')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_DATABASE', 'fastapilaravel')
        
        if user and password and database:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            return os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fastapilaravel")
    
    elif connection == 'mysql':
        user = os.getenv('DB_USERNAME', '')
        password = os.getenv('DB_PASSWORD', '')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '3306')
        database = os.getenv('DB_DATABASE', '')
        charset = os.getenv('DB_CHARSET', 'utf8mb4')
        
        if user and password and database:
            return f"mysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
        else:
            return os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fastapilaravel")
    
    elif connection == 'sqlite':
        return os.getenv("DATABASE_URL", "sqlite:///./storage/database.db")
    
    else:  # Default to postgresql
        return os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/fastapilaravel")

DATABASE_URL: str = get_database_url()

# Alias for compatibility
SQLALCHEMY_DATABASE_URL = DATABASE_URL

def get_engine_config() -> Dict[str, Any]:
    """Get engine configuration based on database type."""
    config: Dict[str, Any] = {}
    
    if "sqlite" in DATABASE_URL:
        config["connect_args"] = {"check_same_thread": False}
    elif "postgresql" in DATABASE_URL:
        config.update({
            "pool_size": int(os.getenv('DB_POOL_SIZE', '5')),
            "max_overflow": int(os.getenv('DB_MAX_OVERFLOW', '10')),
            "pool_timeout": int(os.getenv('DB_POOL_TIMEOUT', '30')),
            "pool_recycle": int(os.getenv('DB_POOL_RECYCLE', '3600')),
            "pool_pre_ping": True,
        })
    elif "mysql" in DATABASE_URL:
        config.update({
            "pool_size": int(os.getenv('DB_POOL_SIZE', '5')),
            "max_overflow": int(os.getenv('DB_MAX_OVERFLOW', '10')),
            "pool_timeout": int(os.getenv('DB_POOL_TIMEOUT', '30')),
            "pool_recycle": int(os.getenv('DB_POOL_RECYCLE', '3600')),
            "pool_pre_ping": True,
        })
    
    # Add echo setting for debugging
    config["echo"] = os.getenv('DB_ECHO', '').lower() == 'true'
    
    return config

engine_config = get_engine_config()
engine: Engine = create_engine(DATABASE_URL, **engine_config)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Laravel-style Database Configuration
DATABASE_CONFIG = {
    'default': os.getenv('DB_CONNECTION', 'postgresql'),
    'connections': {
        'default': {
            'driver': 'postgresql',
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_DATABASE', 'fastapilaravel'),
            'username': os.getenv('DB_USERNAME', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'prefix': os.getenv('DB_PREFIX', ''),
            'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
            'echo': os.getenv('DB_ECHO', '').lower() == 'true',
            'log_queries': os.getenv('DB_LOG_QUERIES', '').lower() == 'true',
        },
        
        'sqlite': {
            'driver': 'sqlite',
            'database': os.getenv('DB_DATABASE', 'storage/database.db'),
            'prefix': '',
            'foreign_key_constraints': True,
            'journal_mode': 'WAL',
            'synchronous': 'NORMAL',
            'timeout': 30,
            'echo': os.getenv('DB_ECHO', '').lower() == 'true',
            'log_queries': os.getenv('DB_LOG_QUERIES', '').lower() == 'true',
        },
        
        'mysql': {
            'driver': 'mysql',
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'database': os.getenv('DB_DATABASE', ''),
            'username': os.getenv('DB_USERNAME', ''),
            'password': os.getenv('DB_PASSWORD', ''),
            'charset': os.getenv('DB_CHARSET', 'utf8mb4'),
            'prefix': os.getenv('DB_PREFIX', ''),
            'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
            'echo': os.getenv('DB_ECHO', '').lower() == 'true',
            'log_queries': os.getenv('DB_LOG_QUERIES', '').lower() == 'true',
        },
        
        'postgresql': {
            'driver': 'postgresql',
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_DATABASE', ''),
            'username': os.getenv('DB_USERNAME', ''),
            'password': os.getenv('DB_PASSWORD', ''),
            'prefix': os.getenv('DB_PREFIX', ''),
            'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
            'echo': os.getenv('DB_ECHO', '').lower() == 'true',
            'log_queries': os.getenv('DB_LOG_QUERIES', '').lower() == 'true',
        },
        
        'testing': {
            'driver': 'postgresql',
            'host': os.getenv('TEST_DB_HOST', 'localhost'),
            'port': int(os.getenv('TEST_DB_PORT', '5432')),
            'database': os.getenv('TEST_DB_DATABASE', 'fastapilaravel_test'),
            'username': os.getenv('TEST_DB_USERNAME', 'postgres'),
            'password': os.getenv('TEST_DB_PASSWORD', 'password'),
            'prefix': '',
            'pool_size': 1,
            'max_overflow': 0,
            'echo': False,
            'log_queries': True,
        },
        
        'testing_memory': {
            'driver': 'sqlite',
            'database': ':memory:',
            'prefix': '',
            'foreign_key_constraints': True,
            'echo': False,
            'log_queries': True,
        }
    },
    
    'migrations': {
        'table': 'migrations',
        'directory': 'database/migrations'
    }
}


def get_database() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias for FastAPI dependency injection
get_db = get_database
get_db_session = get_database


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)