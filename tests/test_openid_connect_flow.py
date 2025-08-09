"""Test OpenID Connect Flow - Google IDP Style

This test suite validates the complete OpenID Connect implementation
including discovery, authorization, token exchange, and userinfo endpoints.
"""

from __future__ import annotations

import json
import pytest
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from main import app
from app.Models.User import User
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2Scope import OAuth2Scope
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.database import get_database


class TestOpenIDConnectFlow:
    """Test suite for OpenID Connect flows."""
    
    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def db(self) -> Session:
        """Get database session."""
        return next(get_database())
    
    @pytest.fixture
    def test_user(self, db: Session) -> User:
        """Create a test user with OpenID Connect claims."""
        user = User(
            name="John Doe",
            email="john.doe@example.com",
            password="hashed_password",
            is_active=True,
            is_verified=True,
            # OpenID Connect standard claims
            given_name="John",
            family_name="Doe",
            nickname="johnny",
            picture="https://example.com/avatar.jpg",
            profile="https://example.com/profile",
            website="https://johndoe.com",
            email_verified_at=datetime.utcnow(),
            locale="en-US",
            zoneinfo="America/New_York"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @pytest.fixture
    def oauth2_client(self, db: Session) -> OAuth2Client:
        """Create a test OAuth2 client with OpenID Connect support."""
        client = OAuth2Client(
            client_id="test_client_id",
            client_secret="test_client_secret",
            name="Test OpenID Connect Client",
            redirect_uris="http://localhost:3000/callback",
            allowed_scopes="openid,profile,email",
            grant_types="authorization_code,refresh_token",
            response_types="code,id_token,token",
            is_confidential=True,
            # OpenID Connect specific fields
            logo_uri="https://example.com/logo.png",
            client_uri="https://example.com",
            policy_uri="https://example.com/privacy",
            tos_uri="https://example.com/terms",
            subject_type="public",
            id_token_signed_response_alg="RS256",
            token_endpoint_auth_method="client_secret_basic"
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        return client
    
    @pytest.fixture
    def oauth2_scopes(self, db: Session) -> None:
        """Create OAuth2 scopes."""
        scopes = [
            OAuth2Scope(scope_id="openid", name="OpenID", description="OpenID Connect scope"),
            OAuth2Scope(scope_id="profile", name="Profile", description="Access to profile information"),
            OAuth2Scope(scope_id="email", name="Email", description="Access to email address"),
        ]
        for scope in scopes:
            db.add(scope)
        db.commit()
    
    def test_openid_connect_discovery(self, client: TestClient) -> None:
        """Test OpenID Connect Discovery endpoint."""
        response = client.get("/.well-known/openid-configuration")
        
        assert response.status_code == 200
        discovery = response.json()
        
        # Verify required discovery fields
        assert discovery["issuer"] == "http://testserver"
        assert discovery["authorization_endpoint"] == "http://testserver/oauth/authorize"
        assert discovery["token_endpoint"] == "http://testserver/oauth/token"
        assert discovery["userinfo_endpoint"] == "http://testserver/oauth/userinfo"
        assert discovery["jwks_uri"] == "http://testserver/.well-known/jwks.json"
        
        # Verify supported features
        assert "openid" in discovery["scopes_supported"]
        assert "profile" in discovery["scopes_supported"]
        assert "email" in discovery["scopes_supported"]
        assert "code" in discovery["response_types_supported"]
        assert "authorization_code" in discovery["grant_types_supported"]
        assert "RS256" in discovery["id_token_signing_alg_values_supported"]
        assert "public" in discovery["subject_types_supported"]
    
    def test_jwks_endpoint(self, client: TestClient) -> None:
        """Test JWKS endpoint for ID token verification."""
        response = client.get("/.well-known/jwks.json")
        
        assert response.status_code == 200
        jwks = response.json()
        
        assert "keys" in jwks
        assert len(jwks["keys"]) > 0
        
        # Verify JWK structure
        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert "kid" in key
        assert "n" in key  # RSA modulus
        assert "e" in key  # RSA exponent
    
    def test_authorization_endpoint_with_openid_scope(
        self, 
        client: TestClient, 
        db: Session,
        test_user: User,
        oauth2_client: OAuth2Client,
        oauth2_scopes: None
    ) -> None:
        """Test authorization endpoint with OpenID Connect parameters."""
        # Simulate authenticated user session (would normally be handled by middleware)
        auth_params = {
            "client_id": oauth2_client.client_id,
            "redirect_uri": "http://localhost:3000/callback",
            "response_type": "code",
            "scope": "openid profile email",
            "state": "random_state_value",
            "nonce": "random_nonce_value",
            "user_id": str(test_user.id)
        }
        
        # This would normally be a POST to the authorization endpoint after user consent
        oauth_service = OAuth2AuthServerService()
        auth_response = oauth_service.handle_authorization_request(
            db=db,
            **auth_params
        )
        
        assert "code" in auth_response
        assert auth_response["state"] == "random_state_value"
        assert "redirect_uri" in auth_response
    
    def test_token_endpoint_with_openid_connect(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        oauth2_client: OAuth2Client,
        oauth2_scopes: None
    ) -> None:
        """Test token endpoint returning ID token for OpenID Connect flow."""
        # First, create an authorization code
        oauth_service = OAuth2AuthServerService()
        auth_code = oauth_service.create_authorization_code(
            db=db,
            client=oauth2_client,
            user=test_user,
            redirect_uri="http://localhost:3000/callback",
            scopes=["openid", "profile", "email"],
            nonce="test_nonce"
        )
        
        # Exchange authorization code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "client_id": oauth2_client.client_id,
            "client_secret": oauth2_client.client_secret,
            "code": auth_code.code_id,
            "redirect_uri": "http://localhost:3000/callback",
            "nonce": "test_nonce"
        }
        
        response = client.post("/oauth/token", data=token_data)
        
        assert response.status_code == 200
        token_response = response.json()
        
        # Verify token response includes ID token
        assert "access_token" in token_response
        assert "token_type" in token_response
        assert "expires_in" in token_response
        assert "scope" in token_response
        assert "id_token" in token_response  # OpenID Connect ID token
        
        # Verify scopes include OpenID Connect scopes
        assert "openid" in token_response["scope"]
        assert "profile" in token_response["scope"]
        assert "email" in token_response["scope"]
    
    def test_userinfo_endpoint(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        oauth2_client: OAuth2Client,
        oauth2_scopes: None
    ) -> None:
        """Test UserInfo endpoint returning user claims."""
        # Create access token with profile and email scopes
        oauth_service = OAuth2AuthServerService()
        access_token = oauth_service.create_access_token(
            db=db,
            client=oauth2_client,
            user=test_user,
            scopes=["openid", "profile", "email"]
        )
        
        # Request userinfo with access token
        headers = {"Authorization": f"Bearer {access_token.token}"}
        response = client.get("/oauth/userinfo", headers=headers)
        
        assert response.status_code == 200
        userinfo = response.json()
        
        # Verify required sub claim
        assert userinfo["sub"] == str(test_user.id)
        
        # Verify profile claims (if profile scope is present)
        assert userinfo["name"] == test_user.name
        assert userinfo["given_name"] == test_user.given_name
        assert userinfo["family_name"] == test_user.family_name
        assert userinfo["nickname"] == test_user.nickname
        assert userinfo["picture"] == test_user.picture
        assert userinfo["profile"] == test_user.profile
        assert userinfo["website"] == test_user.website
        assert userinfo["locale"] == test_user.locale
        
        # Verify email claims (if email scope is present)
        assert userinfo["email"] == test_user.email
        assert userinfo["email_verified"] is True
    
    def test_userinfo_endpoint_limited_scopes(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        oauth2_client: OAuth2Client,
        oauth2_scopes: None
    ) -> None:
        """Test UserInfo endpoint with limited scopes."""
        # Create access token with only openid scope
        oauth_service = OAuth2AuthServerService()
        access_token = oauth_service.create_access_token(
            db=db,
            client=oauth2_client,
            user=test_user,
            scopes=["openid"]
        )
        
        # Request userinfo with limited access token
        headers = {"Authorization": f"Bearer {access_token.token}"}
        response = client.get("/oauth/userinfo", headers=headers)
        
        assert response.status_code == 200
        userinfo = response.json()
        
        # Should only contain sub claim for openid scope
        assert userinfo["sub"] == str(test_user.id)
        
        # Should not contain profile or email claims
        assert "name" not in userinfo
        assert "email" not in userinfo
        assert "given_name" not in userinfo
    
    def test_id_token_validation(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        oauth2_client: OAuth2Client,
        oauth2_scopes: None
    ) -> None:
        """Test ID token creation and validation."""
        oauth_service = OAuth2AuthServerService()
        
        # Create ID token
        id_token = oauth_service.create_id_token(
            user=test_user,
            client=oauth2_client,
            nonce="test_nonce",
            scopes=["openid", "profile", "email"]
        )
        
        assert id_token is not None
        assert isinstance(id_token, str)
        
        # Validate ID token
        payload = oauth_service.validate_id_token(id_token, oauth2_client.client_id)
        
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
        assert payload["aud"] == oauth2_client.client_id
        assert payload["iss"] == oauth_service.issuer
        assert payload["nonce"] == "test_nonce"
        
        # Verify profile claims in ID token
        assert payload["email"] == test_user.email
        assert payload["name"] == test_user.name
        assert payload["given_name"] == test_user.given_name
        assert payload["family_name"] == test_user.family_name
    
    def test_oauth2_discovery_endpoint(self, client: TestClient) -> None:
        """Test OAuth 2.0 Authorization Server Metadata endpoint."""
        response = client.get("/oauth/discovery")
        
        assert response.status_code == 200
        metadata = response.json()
        
        # Verify OAuth2 server metadata
        assert metadata["issuer"] == "http://testserver"
        assert metadata["authorization_endpoint"] == "http://testserver/oauth/authorize"
        assert metadata["token_endpoint"] == "http://testserver/oauth/token"
        assert metadata["revocation_endpoint"] == "http://testserver/oauth/revoke"
        assert metadata["introspection_endpoint"] == "http://testserver/oauth/introspect"
        
        # Verify supported grant types and auth methods
        assert "authorization_code" in metadata["grant_types_supported"]
        assert "client_credentials" in metadata["grant_types_supported"]
        assert "refresh_token" in metadata["grant_types_supported"]
        assert "client_secret_basic" in metadata["token_endpoint_auth_methods_supported"]


if __name__ == "__main__":
    pytest.main([__file__])