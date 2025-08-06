#!/usr/bin/env python3
"""OAuth2 Database Seeder - Laravel Passport Style

This seeder creates default OAuth2 clients and scopes for the application
similar to Laravel Passport's database seeders.
"""

from __future__ import annotations

import sys
import os
from typing import List
from datetime import datetime

# Add the parent directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from config.database import get_db_session
from database.migrations.create_oauth_clients_table import OAuthClient
from database.migrations.create_oauth_scopes_table import OAuthScope
from app.Services.OAuth2ClientService import OAuth2ClientService
from app.Services.OAuth2ScopesService import OAuth2ScopesService


class OAuth2Seeder:
    """OAuth2 database seeder for clients and scopes."""
    
    def __init__(self) -> None:
        self.client_service = OAuth2ClientService()
        self.scope_service = OAuth2ScopesService()
    
    def seed_scopes(self, db: Session) -> List[OAuthScope]:
        """
        Seed default OAuth2 scopes.
        
        Args:
            db: Database session
        
        Returns:
            List of created scopes
        """
        print("🎯 Seeding OAuth2 scopes...")
        
        scopes_data = [
            {
                "scope_id": "read",
                "name": "Read Access",
                "description": "Read access to your account information and data"
            },
            {
                "scope_id": "write",
                "name": "Write Access", 
                "description": "Write and modify your account information and data"
            },
            {
                "scope_id": "admin",
                "name": "Admin Access",
                "description": "Full administrative access to all resources"
            },
            {
                "scope_id": "users",
                "name": "User Management",
                "description": "Create, read, update, and delete user accounts"
            },
            {
                "scope_id": "roles",
                "name": "Role Management",
                "description": "Manage roles and permissions"
            },
            {
                "scope_id": "permissions",
                "name": "Permission Management", 
                "description": "Manage individual permissions"
            },
            {
                "scope_id": "oauth-clients",
                "name": "OAuth Client Management",
                "description": "Manage OAuth2 clients and applications"
            },
            {
                "scope_id": "oauth-tokens",
                "name": "OAuth Token Management",
                "description": "Manage OAuth2 tokens and access control"
            },
            {
                "scope_id": "profile",
                "name": "Profile Access",
                "description": "Access to your basic profile information"
            },
            {
                "scope_id": "email",
                "name": "Email Access",
                "description": "Access to your email address"
            },
            {
                "scope_id": "openid",
                "name": "OpenID Connect",
                "description": "OpenID Connect identity information"
            },
            {
                "scope_id": "offline_access",
                "name": "Offline Access",
                "description": "Maintain access when user is not present (refresh tokens)"
            },
            {
                "scope_id": "api",
                "name": "API Access",
                "description": "General API access scope"
            },
            {
                "scope_id": "mobile",
                "name": "Mobile App Access",
                "description": "Access from mobile applications"
            },
            {
                "scope_id": "web",
                "name": "Web App Access",
                "description": "Access from web applications"
            }
        ]
        
        created_scopes = []
        
        for scope_data in scopes_data:
            # Check if scope already exists
            existing_scope = self.scope_service.get_scope_by_id(db, scope_data["scope_id"])
            
            if existing_scope:
                print(f"  ⚠️  Scope '{scope_data['scope_id']}' already exists, skipping...")
                continue
            
            try:
                scope = self.scope_service.create_scope(
                    db=db,
                    scope_id=scope_data["scope_id"],
                    name=scope_data["name"],
                    description=scope_data["description"]
                )
                created_scopes.append(scope)
                print(f"  ✅ Created scope: {scope.scope_id} - {scope.name}")
                
            except Exception as e:
                print(f"  ❌ Failed to create scope '{scope_data['scope_id']}': {str(e)}")
        
        print(f"📝 Created {len(created_scopes)} OAuth2 scopes\n")
        return created_scopes
    
    def seed_clients(self, db: Session) -> List[OAuthClient]:
        """
        Seed default OAuth2 clients.
        
        Args:
            db: Database session
        
        Returns:
            List of created clients
        """
        print("🔑 Seeding OAuth2 clients...")
        
        created_clients = []
        
        # 1. Personal Access Client
        try:
            personal_client = self.client_service.create_personal_access_client(
                db=db,
                name="FastAPI Laravel Personal Access Client"
            )
            created_clients.append(personal_client)
            print(f"  ✅ Created personal access client: {personal_client.name}")
            print(f"     Client ID: {personal_client.client_id}")
            
        except Exception as e:
            print(f"  ❌ Failed to create personal access client: {str(e)}")
        
        # 2. Password Grant Client
        try:
            password_client = self.client_service.create_password_client(
                db=db,
                name="FastAPI Laravel Password Grant Client",
                redirect_uri="http://localhost:8000/auth/callback"
            )
            created_clients.append(password_client)
            print(f"  ✅ Created password grant client: {password_client.name}")
            print(f"     Client ID: {password_client.client_id}")
            
        except Exception as e:
            print(f"  ❌ Failed to create password grant client: {str(e)}")
        
        # 3. Authorization Code Client (Web App)
        try:
            web_client = self.client_service.create_authorization_code_client(
                db=db,
                name="FastAPI Laravel Web Application",
                redirect_uri="http://localhost:3000/auth/callback,http://localhost:8080/auth/callback",
                confidential=True
            )
            created_clients.append(web_client)
            print(f"  ✅ Created web application client: {web_client.name}")
            print(f"     Client ID: {web_client.client_id}")
            
        except Exception as e:
            print(f"  ❌ Failed to create web application client: {str(e)}")
        
        # 4. Authorization Code Client (Mobile App - Public)
        try:
            mobile_client = self.client_service.create_authorization_code_client(
                db=db,
                name="FastAPI Laravel Mobile Application",
                redirect_uri="com.example.app://oauth/callback",
                confidential=False  # Public client for mobile
            )
            created_clients.append(mobile_client)
            print(f"  ✅ Created mobile application client: {mobile_client.name}")
            print(f"     Client ID: {mobile_client.client_id}")
            
        except Exception as e:
            print(f"  ❌ Failed to create mobile application client: {str(e)}")
        
        # 5. Client Credentials Client (API to API)
        try:
            api_client = self.client_service.create_client_credentials_client(
                db=db,
                name="FastAPI Laravel API Client"
            )
            created_clients.append(api_client)
            print(f"  ✅ Created API client credentials client: {api_client.name}")
            print(f"     Client ID: {api_client.client_id}")
            
        except Exception as e:
            print(f"  ❌ Failed to create API client: {str(e)}")
        
        # 6. Test/Development Client
        try:
            test_client = self.client_service.create_authorization_code_client(
                db=db,
                name="FastAPI Laravel Test Client",
                redirect_uri="http://localhost:8000/test/callback,http://127.0.0.1:8000/test/callback",
                confidential=True
            )
            created_clients.append(test_client)
            print(f"  ✅ Created test/development client: {test_client.name}")
            print(f"     Client ID: {test_client.client_id}")
            
        except Exception as e:
            print(f"  ❌ Failed to create test client: {str(e)}")
        
        print(f"🔐 Created {len(created_clients)} OAuth2 clients\n")
        return created_clients
    
    def display_client_credentials(self, clients: List[OAuthClient]) -> None:
        """
        Display client credentials for reference.
        
        Args:
            clients: List of created clients
        """
        if not clients:
            return
        
        print("=" * 80)
        print("🔒 OAUTH2 CLIENT CREDENTIALS")
        print("=" * 80)
        print("⚠️  IMPORTANT: Store these credentials securely!")
        print("📝 Client secrets are hashed and cannot be retrieved later.")
        print("🔄 Use the regenerate-secret endpoint to create new secrets.\n")
        
        for client in clients:
            print(f"📋 {client.name}")
            print(f"   Client ID: {client.client_id}")
            print(f"   Confidential: {'Yes' if client.is_confidential() else 'No'}")
            print(f"   Personal Access: {'Yes' if client.personal_access_client else 'No'}")
            print(f"   Password Grant: {'Yes' if client.password_client else 'No'}")
            print(f"   Redirect URI: {client.redirect}")
            
            if client.is_confidential():
                print("   ⚠️  Client Secret: [HASHED - Use OAuth2 endpoints to authenticate]")
            
            print()
        
        print("=" * 80)
    
    def seed_all(self, db: Session) -> None:
        """
        Seed all OAuth2 data.
        
        Args:
            db: Database session
        """
        print("🚀 Starting OAuth2 database seeding...\n")
        
        try:
            # Seed scopes first (clients may reference them)
            scopes = self.seed_scopes(db)
            
            # Seed clients
            clients = self.seed_clients(db)
            
            # Display summary
            self.display_client_credentials(clients)
            
            print("✅ OAuth2 seeding completed successfully!")
            print(f"📊 Summary: {len(scopes)} scopes, {len(clients)} clients created")
            
        except Exception as e:
            print(f"❌ OAuth2 seeding failed: {str(e)}")
            db.rollback()
            raise
    
    def clean_oauth2_data(self, db: Session) -> None:
        """
        Clean all OAuth2 data (use with caution).
        
        Args:
            db: Database session
        """
        print("🧹 Cleaning OAuth2 data...")
        
        try:
            # Delete clients (cascade will handle tokens)
            client_count = db.query(OAuthClient).count()
            db.query(OAuthClient).delete()
            
            # Delete scopes
            scope_count = db.query(OAuthScope).count()
            db.query(OAuthScope).delete()
            
            db.commit()
            
            print(f"🗑️  Deleted {client_count} clients and {scope_count} scopes")
            print("✅ OAuth2 data cleanup completed")
            
        except Exception as e:
            print(f"❌ OAuth2 cleanup failed: {str(e)}")
            db.rollback()
            raise


def main() -> None:
    """Main seeder function."""
    seeder = OAuth2Seeder()
    
    # Get command line argument
    action = sys.argv[1] if len(sys.argv) > 1 else "seed"
    
    # Get database session
    db_gen = get_db_session()
    db = next(db_gen)
    
    try:
        if action == "seed":
            seeder.seed_all(db)
        elif action == "clean":
            response = input("⚠️  This will delete ALL OAuth2 data. Continue? [y/N]: ")
            if response.lower() == 'y':
                seeder.clean_oauth2_data(db)
            else:
                print("❌ Operation cancelled")
        elif action == "reseed":
            print("🔄 Reseeding OAuth2 data (clean + seed)...")
            seeder.clean_oauth2_data(db)
            print()
            seeder.seed_all(db)
        else:
            print("Usage: python oauth2_seeder.py [seed|clean|reseed]")
            print("  seed   - Create default OAuth2 clients and scopes")
            print("  clean  - Remove all OAuth2 data")
            print("  reseed - Clean and seed OAuth2 data")
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Seeder failed: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()