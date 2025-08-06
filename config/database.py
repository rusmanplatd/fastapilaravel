import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.Models import Base


DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./storage/database.db"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)