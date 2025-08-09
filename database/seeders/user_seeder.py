from __future__ import annotations

from sqlalchemy.orm import Session
from app.Models.User import User
from config.database import SessionLocal


def seed_users() -> None:
    db: Session = SessionLocal()
    
    try:
        # Check if users already exist
        if db.query(User).first():
            print("Users already seeded")
            return
        
        users = [
            {
                "name": "Admin User",
                "email": "admin@example.com",
                "password": "hashed_password_here",
                "is_active": True,
                "is_verified": True
            },
            {
                "name": "Test User",
                "email": "test@example.com", 
                "password": "hashed_password_here",
                "is_active": True,
                "is_verified": False
            }
        ]
        
        for user_data in users:
            user = User(**user_data)
            db.add(user)
        
        db.commit()
        print("Users seeded successfully")
        
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()