"""
User Seeder
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from .SeederManager import Seeder

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

class UserSeeder(Seeder):
    """Seed users"""
    
    def run(self, db: Session) -> None:
        """Run the seeder"""
        from app.Models.User import User
        from app.Models.Role import Role
        from app.Models.Permission import Permission
        from database.factories.UserFactory import UserFactory
        from app.Support.ServiceContainer import container
        from datetime import datetime, timezone
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Create default admin user
            admin_user = db.query(User).filter(User.email == "admin@example.com").first()
            if not admin_user:
                admin_user = User(
                    name="Administrator",
                    email="admin@example.com",
                    password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewP/VQChQxm62YBa",  # "password"
                    is_active=True,
                    is_verified=True,
                    email_verified_at=datetime.now(timezone.utc),
                    mfa_enabled=True,
                    login_count=10,
                    timezone="UTC",
                    locale="en",
                    settings='{"theme": "dark", "notifications": {"email": true, "push": true}}',
                    preferences='{"language": "en", "date_format": "Y-m-d", "time_format": "24"}'
                )
                db.add(admin_user)
                logger.info("Created admin user")
            
            # Create test user
            test_user = db.query(User).filter(User.email == "user@example.com").first()
            if not test_user:
                test_user = User(
                    name="Test User",
                    email="user@example.com",
                    password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewP/VQChQxm62YBa",  # "password"
                    is_active=True,
                    is_verified=True,
                    email_verified_at=datetime.now(timezone.utc),
                    timezone="UTC",
                    locale="en",
                    settings='{"theme": "light", "notifications": {"email": true, "push": false}}',
                    preferences='{"language": "en", "date_format": "m/d/Y", "time_format": "12"}'
                )
                db.add(test_user)
                logger.info("Created test user")
            
            # Assign admin role to admin user
            try:
                admin_role = db.query(Role).filter(Role.name == "admin").first()
                if admin_role and admin_user and admin_role not in admin_user.roles:
                    admin_user.roles.append(admin_role)
                    logger.info("Assigned admin role to admin user")
            except Exception as e:
                logger.warning(f"Could not assign admin role: {e}")
            
            # Assign user role to test user
            try:
                user_role = db.query(Role).filter(Role.name == "user").first()
                if user_role and test_user and user_role not in test_user.roles:
                    test_user.roles.append(user_role)
                    logger.info("Assigned user role to test user")
            except Exception as e:
                logger.warning(f"Could not assign user role: {e}")
            
            # Create additional demo users using factory
            try:
                factory = UserFactory()
                
                # Create some verified users
                for i in range(5):
                    existing_user = db.query(User).filter(User.email == f"verified{i+1}@example.com").first()
                    if not existing_user:
                        user_data = factory.verified().definition()
                        user_data["email"] = f"verified{i+1}@example.com"
                        user_data["name"] = f"Verified User {i+1}"
                        
                        user = User(**user_data)
                        db.add(user)
                        logger.info(f"Created verified user {i+1}")
                
                # Create some unverified users
                for i in range(3):
                    existing_user = db.query(User).filter(User.email == f"unverified{i+1}@example.com").first()
                    if not existing_user:
                        user_data = factory.unverified().definition()
                        user_data["email"] = f"unverified{i+1}@example.com"
                        user_data["name"] = f"Unverified User {i+1}"
                        
                        user = User(**user_data)
                        db.add(user)
                        logger.info(f"Created unverified user {i+1}")
                
                # Create MFA-enabled users
                for i in range(2):
                    existing_user = db.query(User).filter(User.email == f"mfa{i+1}@example.com").first()
                    if not existing_user:
                        user_data = factory.mfa_enabled().definition()
                        user_data["email"] = f"mfa{i+1}@example.com"
                        user_data["name"] = f"MFA User {i+1}"
                        
                        user = User(**user_data)
                        db.add(user)
                        logger.info(f"Created MFA user {i+1}")
                        
            except Exception as e:
                logger.warning(f"Could not create factory users: {e}")
            
            db.commit()
            logger.info("UserSeeder completed successfully")
            
        except Exception as e:
            logger.error(f"Error in UserSeeder: {e}")
            db.rollback()
            raise