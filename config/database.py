from __future__ import annotations

import os
from typing import Generator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from app.Models import Base


DATABASE_URL: str = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./storage/database.db"
)

connect_args: Dict[str, Any] = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine: Engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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