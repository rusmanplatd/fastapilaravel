"""
K6 Test Helper Endpoints
FastAPI endpoints specifically for k6 testing setup and teardown
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.database import get_db
from k6_tests.setup.test_db_setup import K6TestDatabaseSetup


def create_test_endpoints(app: FastAPI) -> None:
    """Add test-specific endpoints to the FastAPI app"""
    
    @app.post("/test/db/setup")
    async def setup_test_database(db: Session = Depends(get_db)) -> JSONResponse:
        """Setup fresh test database with seeded data"""
        try:
            test_db_url = os.getenv("TEST_DB_URL", "postgresql://postgres:password@localhost:5432/test_k6_db")
            setup = K6TestDatabaseSetup(test_db_url)
            
            # Reset database completely
            summary = setup.reset_database()
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Test database setup completed",
                    "data": summary
                },
                status_code=200
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database setup failed: {str(e)}"
            )
    
    @app.post("/test/db/seed")
    async def seed_test_data(db: Session = Depends(get_db)) -> JSONResponse:
        """Seed test database with fresh data"""
        try:
            test_db_url = os.getenv("TEST_DB_URL", "postgresql://postgres:password@localhost:5432/test_k6_db")
            setup = K6TestDatabaseSetup(test_db_url)
            
            # Clean and reseed
            setup.clean_database()
            summary = setup.seed_test_data()
            
            return JSONResponse(
                content={
                    "status": "success", 
                    "message": "Test data seeded successfully",
                    "data": summary
                },
                status_code=200
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Data seeding failed: {str(e)}"
            )
    
    @app.delete("/test/db/clean") 
    async def clean_test_database(db: Session = Depends(get_db)) -> JSONResponse:
        """Clean all data from test database"""
        try:
            test_db_url = os.getenv("TEST_DB_URL", "postgresql://postgres:password@localhost:5432/test_k6_db")
            setup = K6TestDatabaseSetup(test_db_url)
            
            setup.clean_database()
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Test database cleaned successfully"
                },
                status_code=200
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database cleaning failed: {str(e)}"
            )
    
    @app.get("/test/db/status")
    async def get_database_status(db: Session = Depends(get_db)) -> JSONResponse:
        """Get current database status and record counts"""
        try:
            test_db_url = os.getenv("TEST_DB_URL", "postgresql://postgres:password@localhost:5432/test_k6_db")
            setup = K6TestDatabaseSetup(test_db_url)
            
            db_session = setup.SessionLocal()
            try:
                summary = setup._get_data_summary(db_session)
                
                return JSONResponse(
                    content={
                        "status": "success",
                        "database_url": test_db_url,
                        "data": summary,
                        "total_records": sum(summary.values())
                    },
                    status_code=200
                )
                
            finally:
                db_session.close()
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Status check failed: {str(e)}"
            )
    
    @app.post("/test/auth/create-user")
    async def create_test_user(user_data: Dict[str, Any], db: Session = Depends(get_db)) -> JSONResponse:
        """Create a test user for authentication testing"""
        try:
            from app.Models.User import User
            from app.Services.AuthService import AuthService
            
            auth_service = AuthService()
            
            # Create user with hashed password
            user = User(
                name=user_data.get("name", "Test User"),
                email=user_data["email"],
                password=auth_service.hash_password(user_data.get("password", "password123")),
                phone=user_data.get("phone"),
                is_active=True,
                email_verified_at="2025-01-01 00:00:00"
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Test user created",
                    "data": {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name
                    }
                },
                status_code=201
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User creation failed: {str(e)}"
            )
    
    @app.post("/test/oauth2/create-client")
    async def create_test_oauth2_client(
        client_data: Dict[str, Any], 
        db: Session = Depends(get_db)
    ) -> JSONResponse:
        """Create a test OAuth2 client"""
        try:
            from app.Models.OAuth2Client import OAuth2Client
            from app.Services.OAuth2ClientService import OAuth2ClientService
            
            client_service = OAuth2ClientService(db)
            
            # Create OAuth2 client
            client = OAuth2Client(
                id=client_data.get("client_id", f"test-client-{os.urandom(8).hex()}"),
                name=client_data.get("name", "Test OAuth2 Client"),
                secret=client_service.hash_secret(client_data.get("client_secret", "test-secret")),
                redirect_uris=client_data.get("redirect_uris", ["http://localhost:3000/callback"]),
                grant_types=client_data.get("grant_types", ["authorization_code", "refresh_token"]),
                response_types=client_data.get("response_types", ["code"]),
                scope=client_data.get("scope", "read write"),
                is_active=True
            )
            
            db.add(client)
            db.commit()
            db.refresh(client)
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Test OAuth2 client created",
                    "data": {
                        "client_id": client.id,
                        "name": client.name,
                        "scopes": client.scope.split() if client.scope else []
                    }
                },
                status_code=201
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth2 client creation failed: {str(e)}"
            )
    
    @app.get("/test/health")
    async def test_health_check() -> JSONResponse:
        """Health check endpoint for k6 tests"""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "FastAPI Laravel K6 Test Suite",
                "timestamp": "2025-01-01T00:00:00Z"
            },
            status_code=200
        )
    
    @app.get("/test/metrics")
    async def get_test_metrics(db: Session = Depends(get_db)) -> JSONResponse:
        """Get various metrics for test monitoring"""
        try:
            from app.Models.User import User
            from app.Models.Post import Post
            from app.Models.OAuth2AccessToken import OAuth2AccessToken
            
            # Collect various metrics
            metrics = {
                "database": {
                    "users_count": db.query(User).count(),
                    "posts_count": db.query(Post).count(),
                    "active_tokens_count": db.query(OAuth2AccessToken).count(),
                },
                "system": {
                    "environment": os.getenv("ENVIRONMENT", "testing"),
                    "database_url": os.getenv("TEST_DB_URL", "sqlite:///./test_k6.db"),
                },
                "features": {
                    "oauth2_enabled": True,
                    "mfa_enabled": True,
                    "notifications_enabled": True,
                    "queue_enabled": True,
                }
            }
            
            return JSONResponse(
                content={
                    "status": "success",
                    "metrics": metrics
                },
                status_code=200
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Metrics collection failed: {str(e)}"
            )