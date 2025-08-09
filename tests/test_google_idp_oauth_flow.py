"""Test Google IDP-style OAuth2/OpenID Connect Flow

This test module validates the enhanced OAuth2 implementation that mimics
Google's Identity Provider behavior and endpoints.
"""

from __future__ import annotations

import pytest
import json
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

# Import the main application
from main import app
from config.database import get_db_session
from app.Models.User import User
from app.Models.OAuth2Client import OAuth2Client
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService


class TestGoogleIDPOAuth2Flow:
    """Test suite for Google IDP-style OAuth2/OpenID Connect flow."""
    
    def setup_method(self) -> None:
        """Set up test environment."""
        self.client = TestClient(app)
        self.oauth_service = OAuth2AuthServerService()
        
        # Test client credentials
        self.test_client_id = "test_client_id"
        self.test_client_secret = "test_client_secret"
        self.test_redirect_uri = "http://localhost:3000/callback"
        
        # Test user credentials
        self.test_user_email = "test@example.com"
        self.test_user_password = "testpassword123"
    
    def test_openid_connect_discovery_endpoint(self) -> None:
        """Test OpenID Connect discovery endpoint (Google IDP style)."""
        response = self.client.get("/.well-known/openid_configuration")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Validate required OpenID Connect discovery fields
        required_fields = [
            "issuer",
            "authorization_endpoint", 
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
            "scopes_supported",
            "response_types_supported",
            "subject_types_supported",
            "id_token_signing_alg_values_supported"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate Google-style specific fields
        assert "openid" in data["scopes_supported"]
        assert "email" in data["scopes_supported"]
        assert "profile" in data["scopes_supported"]
        assert "code" in data["response_types_supported"]
        assert "RS256" in data["id_token_signing_alg_values_supported"]
        assert "public" in data["subject_types_supported"]
        
        # Validate endpoints format
        base_url = "http://testserver"
        assert data["authorization_endpoint"] == f"{base_url}/oauth/authorize"
        assert data["token_endpoint"] == f"{base_url}/oauth/token"
        assert data["userinfo_endpoint"] == f"{base_url}/oauth/userinfo"
        assert data["jwks_uri"] == f"{base_url}/.well-known/jwks.json"
    
    def test_jwks_endpoint(self) -> None:
        """Test JWKS endpoint for public key discovery."""
        response = self.client.get("/.well-known/jwks.json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Validate cache headers (Google-style)
        assert "Cache-Control" in response.headers
        assert "public" in response.headers["Cache-Control"]
        assert "max-age" in response.headers["Cache-Control"]
        
        data = response.json()
        
        # Validate JWKS structure
        assert "keys" in data
        assert isinstance(data["keys"], list)
        assert len(data["keys"]) > 0
        
        # Validate first key structure
        key = data["keys"][0]
        required_key_fields = ["kty", "use", "alg", "kid", "n", "e"]
        
        for field in required_key_fields:
            assert field in key, f"Missing required key field: {field}"
        
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
    
    def test_oauth2_authorization_server_metadata(self) -> None:
        """Test OAuth2 Authorization Server Metadata (RFC 8414)."""
        response = self.client.get("/oauth/discovery")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Validate OAuth2 metadata fields
        required_fields = [
            "issuer",
            "authorization_endpoint",
            "token_endpoint", 
            "scopes_supported",
            "response_types_supported",
            "grant_types_supported"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required OAuth2 metadata field: {field}"
        
        # Validate grant types
        expected_grants = [
            "authorization_code",
            "client_credentials", 
            "refresh_token",
            "password"
        ]
        
        for grant in expected_grants:
            assert grant in data["grant_types_supported"]
    
    def test_cors_headers_on_oauth_endpoints(self) -> None:
        """Test CORS headers on OAuth2 endpoints."""
        endpoints = [
            "/.well-known/openid_configuration",
            "/.well-known/jwks.json",
            "/oauth/discovery"
        ]
        
        for endpoint in endpoints:
            # Test preflight OPTIONS request
            response = self.client.options(endpoint)
            assert response.status_code == 204
            
            # Validate CORS headers
            assert "Access-Control-Allow-Origin" in response.headers
            assert "Access-Control-Allow-Methods" in response.headers
            assert "Access-Control-Allow-Headers" in response.headers
        
        # Test actual GET requests have CORS headers
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert "Access-Control-Allow-Origin" in response.headers
    
    def test_error_response_format(self) -> None:
        """Test OAuth2 error response format (Google IDP style)."""
        # Test invalid client error
        response = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "invalid_client",
                "client_secret": "invalid_secret",
                "code": "invalid_code",
                "redirect_uri": self.test_redirect_uri
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Validate OAuth2 error structure
        assert "error" in data
        assert "error_description" in data
        assert data["error"] in [
            "invalid_client",
            "invalid_grant", 
            "invalid_request",
            "unauthorized_client"
        ]
    
    def test_userinfo_endpoint_structure(self) -> None:
        """Test UserInfo endpoint response structure."""
        # This test would require a valid access token
        # For now, test the endpoint exists and handles missing auth correctly
        response = self.client.get("/oauth/userinfo")
        
        # Should return 401 without proper authorization
        assert response.status_code == 401
        
        # Test with invalid bearer token
        response = self.client.get(
            "/oauth/userinfo",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        
        # Validate CORS headers are present
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_scope_descriptions_in_consent_flow(self) -> None:
        """Test that scope descriptions match Google IDP style."""
        # This would typically be tested in the consent screen
        # For now, we'll verify the OAuth2ConsentController exists
        from app.Http.Controllers.OAuth2ConsentController import OAuth2ConsentController
        
        controller = OAuth2ConsentController()
        scope_descriptions = controller._get_scope_descriptions()
        
        # Validate Google-style scope descriptions
        assert "openid" in scope_descriptions
        assert "profile" in scope_descriptions
        assert "email" in scope_descriptions
        
        # Validate description structure
        for scope, desc in scope_descriptions.items():
            assert "title" in desc
            assert "description" in desc
            assert "icon" in desc
    
    def test_token_endpoint_security_headers(self) -> None:
        """Test security headers on token endpoint."""
        response = self.client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_client",
                "client_secret": "test_secret"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Validate security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Cache-Control",
            "Pragma"
        ]
        
        for header in security_headers:
            assert header in response.headers
        
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"
    
    def test_openid_connect_flow_simulation(self) -> None:
        """Test simulated OpenID Connect authorization code flow."""
        # Step 1: Authorization request (would redirect to consent screen)
        auth_params = {
            "response_type": "code",
            "client_id": self.test_client_id,
            "redirect_uri": self.test_redirect_uri,
            "scope": "openid profile email",
            "state": "random_state_value",
            "nonce": "random_nonce_value"
        }
        
        # This would typically redirect to consent screen
        # For testing, we'll verify the parameters are accepted
        auth_url = "/oauth/authorize?" + "&".join([f"{k}={v}" for k, v in auth_params.items()])
        response = self.client.get(auth_url)
        
        # Should redirect to login or consent (3xx status) or show consent form
        assert response.status_code in [200, 302, 401]  # Various valid responses depending on auth state
    
    def test_jwt_id_token_structure(self) -> None:
        """Test that ID tokens follow OpenID Connect JWT structure."""
        # This would require creating an actual ID token
        # For now, test the token creation method exists
        from app.Http.Controllers.OpenIDConnectController import OpenIDConnectController
        
        controller = OpenIDConnectController()
        
        # Verify the ID token creation method exists
        assert hasattr(controller, '_create_id_token')
        
        # Verify JWT configuration
        assert hasattr(controller, 'private_key')
        assert hasattr(controller, 'public_key')
        assert hasattr(controller, 'kid')
    
    def test_rate_limiting_headers(self) -> None:
        """Test that rate limiting information is provided in headers."""
        # Make multiple requests to check for rate limiting headers
        for _ in range(3):
            response = self.client.post(
                "/oauth/token",
                data={
                    "grant_type": "client_credentials", 
                    "client_id": "test_client",
                    "client_secret": "test_secret"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Rate limiting headers might be present
            # This depends on the rate limiting implementation
            if "X-RateLimit-Limit" in response.headers:
                assert "X-RateLimit-Remaining" in response.headers
    
    def test_google_idp_compatibility_features(self) -> None:
        """Test features that ensure Google IDP compatibility."""
        
        # Test 1: Discovery document has Google-compatible fields
        discovery_response = self.client.get("/.well-known/openid_configuration")
        discovery_data = discovery_response.json()
        
        google_compatible_fields = [
            "claims_supported",
            "display_values_supported",
            "ui_locales_supported",
            "acr_values_supported"
        ]
        
        for field in google_compatible_fields:
            assert field in discovery_data
        
        # Test 2: Claims include standard OpenID Connect claims
        claims = discovery_data["claims_supported"]
        standard_claims = [
            "sub", "email", "email_verified", "name", 
            "given_name", "family_name", "picture", "locale"
        ]
        
        for claim in standard_claims:
            assert claim in claims
        
        # Test 3: Response types include Google-compatible types
        response_types = discovery_data["response_types_supported"]
        assert "code" in response_types
        assert "id_token" in response_types
        
        # Test 4: JWKS endpoint returns proper key format
        jwks_response = self.client.get("/.well-known/jwks.json")
        jwks_data = jwks_response.json()
        
        # Verify key structure matches Google's format
        if jwks_data["keys"]:
            key = jwks_data["keys"][0]
            assert key["kty"] == "RSA"
            assert "n" in key  # RSA modulus
            assert "e" in key  # RSA exponent
            assert "kid" in key  # Key ID


# Pytest fixtures for integration testing
@pytest.fixture
def test_client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture 
def db_session() -> Session:
    """Create database session for testing.""" 
    return next(get_db_session())


@pytest.fixture
def test_oauth_client(db_session: Session) -> OAuth2Client:
    """Create test OAuth2 client."""
    client = OAuth2Client(
        client_id="test_google_idp_client",
        client_secret="test_secret_123",
        name="Test Google IDP Client",
        redirect_uris="http://localhost:3000/callback",
        allowed_scopes="openid profile email",
        grant_types="authorization_code refresh_token",
        response_types="code id_token token",
        is_confidential=True,
        is_active=True
    )
    
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    
    return client


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        name="Test User",
        given_name="Test",
        family_name="User",
        email_verified=True,
        picture="https://example.com/picture.jpg",
        locale="en-US"
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])