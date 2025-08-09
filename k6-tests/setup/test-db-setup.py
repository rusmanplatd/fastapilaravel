"""
K6 Test Database Setup
Creates a fresh test database and seeds it with test data for k6 testing
"""

from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path
from typing import Any, Dict

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import psycopg2
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import application components
from config.database import Base, get_db
from config.settings import settings
from database.seeders.DatabaseSeeder import DatabaseSeeder
from app.Models.User import User
from app.Models.Role import Role
from app.Models.Permission import Permission
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2Scope import OAuth2Scope
from app.Models.Post import Post
from app.Models.Organization import Organization
from app.Models.Notification import Notification


class K6TestDatabaseSetup:
    """Handles database setup for k6 testing with fresh data"""
    
    def __init__(self, test_db_url: str = "postgresql://postgres:password@localhost:5432/test_k6_db"):
        self.test_db_url = test_db_url
        
        # Configure PostgreSQL connection
        if "postgresql" in test_db_url:
            self.engine = create_engine(
                test_db_url,
                echo=False,
                poolclass=NullPool,  # Disable connection pooling for testing
                pool_pre_ping=True,
                connect_args={
                    "options": "-c timezone=utc",
                    "connect_timeout": 10,
                }
            )
        else:
            # Fallback for SQLite
            self.engine = create_engine(
                test_db_url,
                echo=False,
                connect_args={"check_same_thread": False}
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _ensure_postgresql_database_exists(self) -> None:
        """Ensure PostgreSQL test database exists, create if not"""
        parsed_url = urlparse(self.test_db_url)
        db_name = parsed_url.path.lstrip('/')
        
        # Connection URL without database name for creating database
        base_url = f"{parsed_url.scheme}://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port}/postgres"
        
        try:
            # Connect to default postgres database to create test database
            base_engine = create_engine(base_url, isolation_level='AUTOCOMMIT')
            
            with base_engine.connect() as conn:
                # Drop database if exists and create fresh
                conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                
            base_engine.dispose()
            print(f"✅ PostgreSQL database '{db_name}' created successfully")
            
        except Exception as e:
            print(f"⚠️ Database creation warning: {str(e)}")
            # Continue anyway - database might already exist
        
    def create_tables(self) -> None:
        """Create all database tables"""
        print("Creating database tables...")
        
        # For PostgreSQL, we need to handle database creation differently
        if "postgresql" in self.test_db_url:
            self._ensure_postgresql_database_exists()
        
        try:
            Base.metadata.drop_all(bind=self.engine)  # Clean slate
            Base.metadata.create_all(bind=self.engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            raise
        
    def seed_test_data(self) -> Dict[str, Any]:
        """Seed database with comprehensive test data"""
        print("Seeding test data...")
        
        db = self.SessionLocal()
        seeder = DatabaseSeeder(db)
        
        try:
            # Seed base data
            seeder.run()
            
            # Create additional test-specific data
            self._create_k6_specific_data(db)
            
            db.commit()
            print("✅ Test data seeded successfully")
            
            # Return summary of created data
            return self._get_data_summary(db)
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error seeding test data: {str(e)}")
            raise
        finally:
            db.close()
    
    def _create_k6_specific_data(self, db) -> None:
        """Create specific data for k6 load testing"""
        
        # Create test users with different roles
        test_users = []
        
        # Regular test users (100)
        for i in range(100):
            user = User(
                name=f"TestUser{i:03d}",
                email=f"testuser{i:03d}@k6test.com",
                password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaTs8/GdBXoSb.1xcHPKkX5jO",  # password123
                phone=f"+1555000{i:04d}",
                is_active=True,
                email_verified_at="2025-01-01 00:00:00"
            )
            test_users.append(user)
            db.add(user)
        
        # Admin test users (10)
        for i in range(10):
            user = User(
                name=f"AdminUser{i:03d}",
                email=f"admin{i:03d}@k6test.com",
                password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaTs8/GdBXoSb.1xcHPKkX5jO",  # password123
                phone=f"+1555100{i:04d}",
                is_active=True,
                email_verified_at="2025-01-01 00:00:00"
            )
            test_users.append(user)
            db.add(user)
            
        db.flush()  # Get user IDs
        
        # Create OAuth2 clients for testing
        oauth_clients = [
            OAuth2Client(
                id="test-client-id",
                name="K6 Test Client",
                secret="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaTs8/GdBXoSb.1xcHPKkX5jO",  # test-client-secret
                redirect_uris=["http://localhost:3000/callback"],
                grant_types=["authorization_code", "refresh_token", "client_credentials"],
                response_types=["code"],
                scope="read write admin",
                is_active=True,
                user_id=test_users[0].id if test_users else None
            ),
            OAuth2Client(
                id="confidential-client",
                name="Confidential Test Client", 
                secret="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaTs8/GdBXoSb.1xcHPKkX5jO",  # confidential-secret
                redirect_uris=["http://localhost:3000/callback"],
                grant_types=["client_credentials"],
                response_types=["token"],
                scope="read write",
                is_active=True,
                user_id=test_users[1].id if len(test_users) > 1 else None
            ),
            OAuth2Client(
                id="public-client",
                name="Public Test Client",
                secret=None,  # Public client
                redirect_uris=["http://localhost:3000/callback"],
                grant_types=["authorization_code", "refresh_token"],
                response_types=["code"],
                scope="read",
                is_active=True,
                user_id=test_users[2].id if len(test_users) > 2 else None
            )
        ]
        
        for client in oauth_clients:
            db.add(client)
            
        # Create test posts (500)
        categories = ["tech", "news", "lifestyle", "sports", "science"]
        for i in range(500):
            post = Post(
                title=f"Test Post {i:03d}: {categories[i % len(categories)].title()} News",
                content=f"This is test post content number {i}. " * 10,  # Longer content
                category=categories[i % len(categories)],
                status="published" if i % 4 != 0 else "draft",  # 75% published
                author_id=test_users[i % len(test_users)].id if test_users else 1,
                created_at="2025-01-01 00:00:00",
                updated_at="2025-01-01 00:00:00"
            )
            db.add(post)
        
        # Create test organizations (20)
        industries = ["technology", "finance", "healthcare", "education", "retail"]
        for i in range(20):
            org = Organization(
                name=f"Test Organization {i:03d}",
                description=f"Test organization {i} in {industries[i % len(industries)]} industry",
                industry=industries[i % len(industries)],
                website=f"https://testorg{i:03d}.com",
                created_at="2025-01-01 00:00:00"
            )
            db.add(org)
            
        # Create test notifications (200)
        notification_types = ["email", "database", "sms", "push"]
        for i in range(200):
            notification = Notification(
                type=notification_types[i % len(notification_types)],
                notifiable_type="User",
                notifiable_id=test_users[i % len(test_users)].id if test_users else 1,
                data={
                    "title": f"Test Notification {i}",
                    "message": f"This is test notification content {i}",
                    "action_url": f"/notifications/{i}"
                },
                read_at=None if i % 3 != 0 else "2025-01-01 12:00:00",  # 2/3 unread
                created_at="2025-01-01 00:00:00"
            )
            db.add(notification)
    
    def _get_data_summary(self, db) -> Dict[str, Any]:
        """Get summary of seeded data"""
        return {
            "users": db.query(User).count(),
            "roles": db.query(Role).count(),
            "permissions": db.query(Permission).count(),
            "oauth2_clients": db.query(OAuth2Client).count(),
            "oauth2_scopes": db.query(OAuth2Scope).count(),
            "posts": db.query(Post).count(),
            "organizations": db.query(Organization).count(),
            "notifications": db.query(Notification).count(),
        }
    
    def clean_database(self) -> None:
        """Clean all data from database"""
        print("Cleaning test database...")
        
        db = self.SessionLocal()
        try:
            # Delete all data in reverse dependency order
            db.execute(text("DELETE FROM notifications"))
            db.execute(text("DELETE FROM posts"))
            db.execute(text("DELETE FROM oauth2_access_tokens"))
            db.execute(text("DELETE FROM oauth2_refresh_tokens"))
            db.execute(text("DELETE FROM oauth2_authorization_codes"))
            db.execute(text("DELETE FROM oauth2_clients"))
            db.execute(text("DELETE FROM user_role"))
            db.execute(text("DELETE FROM role_permission"))
            db.execute(text("DELETE FROM user_organizations"))
            db.execute(text("DELETE FROM organizations"))
            db.execute(text("DELETE FROM users"))
            db.execute(text("DELETE FROM roles"))
            db.execute(text("DELETE FROM permissions"))
            db.execute(text("DELETE FROM oauth2_scopes"))
            
            # Reset auto-increment counters
            if "sqlite" in self.test_db_url:
                db.execute(text("DELETE FROM sqlite_sequence"))
            elif "postgresql" in self.test_db_url:
                # Reset PostgreSQL sequences
                sequences = [
                    "users_id_seq", "roles_id_seq", "permissions_id_seq", 
                    "posts_id_seq", "organizations_id_seq", "notifications_id_seq",
                    "oauth2_clients_id_seq", "oauth2_scopes_id_seq"
                ]
                for seq in sequences:
                    try:
                        db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                    except Exception:
                        pass  # Sequence might not exist
            
            db.commit()
            print("✅ Database cleaned successfully")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error cleaning database: {str(e)}")
            raise
        finally:
            db.close()
    
    def reset_database(self) -> Dict[str, Any]:
        """Complete database reset - drop, create, seed"""
        print("Performing complete database reset...")
        
        self.create_tables()
        summary = self.seed_test_data()
        
        print("✅ Database reset completed successfully")
        print(f"Data summary: {summary}")
        
        return summary


def setup_test_database() -> Dict[str, Any]:
    """Main function to setup test database"""
    test_db_url = os.getenv("TEST_DB_URL") or os.getenv("K6_TEST_DB_URL") or "postgresql://postgres:k6_test_password@localhost:5433/test_k6_db"
    
    # For SQLite, remove existing database file
    if "sqlite" in test_db_url and test_db_url.startswith("sqlite:///"):
        db_file = test_db_url.replace("sqlite:///", "")
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Removed existing database file: {db_file}")
    
    # For PostgreSQL, database recreation is handled in _ensure_postgresql_database_exists()
    setup = K6TestDatabaseSetup(test_db_url)
    return setup.reset_database()


if __name__ == "__main__":
    import json
    
    print("🧪 K6 Test Database Setup")
    print("=" * 50)
    
    try:
        summary = setup_test_database()
        
        print("\n📊 Final Data Summary:")
        for entity, count in summary.items():
            print(f"  {entity}: {count}")
            
        print(f"\n✅ K6 test database setup completed successfully!")
        print(f"Database URL: {os.getenv('TEST_DB_URL') or os.getenv('K6_TEST_DB_URL') or 'postgresql://postgres:k6_test_password@localhost:5433/test_k6_db'}")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)