from fastapi import FastAPI
from routes import api_router, web_router
from routes.oauth2 import router as oauth2_router
from app.Http.Middleware import add_cors_middleware
from config import create_tables, settings
from config.oauth2 import oauth2_settings

app = FastAPI(
    title=f"{settings.APP_NAME} with OAuth2",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="""
    FastAPI application with Laravel-style architecture and complete OAuth2 implementation.
    
    ## Features
    
    - **Laravel-style MVC Architecture**: Controllers, Services, Models, Middleware
    - **Complete OAuth2 Implementation**: All grant types, scopes, token management
    - **Strict Type Checking**: Full mypy coverage with comprehensive type hints
    - **Role-Based Access Control**: Spatie-like permissions and roles
    - **JWT Authentication**: Secure token-based authentication
    - **Database Migrations**: SQLAlchemy models with relationships
    
    ## OAuth2 Grant Types
    
    - Authorization Code (with PKCE support)
    - Client Credentials  
    - Password Grant
    - Refresh Token
    
    ## Authentication
    
    This API supports both traditional JWT authentication and OAuth2 authentication.
    Use the `/oauth/token` endpoint to obtain access tokens.
    """
)

add_cors_middleware(app)

# Include routers
app.include_router(web_router)
app.include_router(api_router)
app.include_router(oauth2_router)  # OAuth2 endpoints


# OAuth2 Server Metadata Endpoint
@app.get(
    "/.well-known/oauth-authorization-server",
    tags=["OAuth2"],
    summary="OAuth2 Server Metadata",
    description="RFC 8414: OAuth2 Authorization Server Metadata"
)
async def oauth2_server_metadata():
    """OAuth2 server metadata endpoint."""
    base_url = "http://localhost:8000"  # Should come from settings in production
    return oauth2_settings.to_server_metadata(base_url)


# OpenID Connect Discovery Endpoint
@app.get(
    "/.well-known/openid_configuration",
    tags=["OpenID Connect"],
    summary="OpenID Connect Discovery",
    description="OpenID Connect Discovery metadata"
)
async def openid_configuration():
    """OpenID Connect discovery endpoint."""
    if not oauth2_settings.oauth2_enable_openid_connect:
        return {"error": "OpenID Connect not enabled"}
    
    base_url = "http://localhost:8000"  # Should come from settings in production
    metadata = oauth2_settings.to_server_metadata(base_url)
    
    # Add OpenID Connect specific metadata
    metadata.update({
        "userinfo_endpoint": f"{base_url}{oauth2_settings.oauth2_userinfo_endpoint}",
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [oauth2_settings.oauth2_algorithm],
        "response_types_supported": ["code", "id_token", "code id_token"],
        "claims_supported": ["sub", "name", "email", "email_verified", "aud", "iss", "iat", "exp"]
    })
    
    return metadata


@app.on_event("startup")
async def startup_event():
    create_tables()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} with OAuth2 started!")
    print(f"📊 OAuth2 Settings:")
    print(f"   - Enabled Grants: {', '.join(oauth2_settings.oauth2_enabled_grants)}")
    print(f"   - Supported Scopes: {len(oauth2_settings.oauth2_supported_scopes)} scopes")
    print(f"   - Access Token TTL: {oauth2_settings.oauth2_access_token_expire_minutes} minutes")
    print(f"   - Refresh Token TTL: {oauth2_settings.oauth2_refresh_token_expire_days} days")
    print(f"   - PKCE Required: {oauth2_settings.oauth2_require_pkce}")
    print(f"   - OpenID Connect: {'Enabled' if oauth2_settings.oauth2_enable_openid_connect else 'Disabled'}")
    print(f"📝 API Documentation: http://localhost:8000/docs")
    print(f"🔍 OAuth2 Metadata: http://localhost:8000/.well-known/oauth-authorization-server")


@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=settings.DEBUG
    )