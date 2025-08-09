from __future__ import annotations

from typing import Dict, Union, List
from fastapi import FastAPI
from routes import api_router, web_router
from routes.oauth2 import router as oauth2_router
from routes.discovery import router as discovery_router
from routes.api.mfa import router as mfa_router
from routes.monitoring import router as monitoring_router
from app.Http.Controllers.Api.OpenIDConnectController import openid_router
from app.Http.Middleware import (
    add_cors_middleware, 
    setup_development_middleware,
    setup_production_middleware,
    middleware_manager
)
from app.Routing import route_manager
from app.Policies.Policy import gate
from app.Models.User import User
from app.Policies.UserPolicy import UserPolicy
from app.Foundation.Application import create_application
from config import create_tables, settings
from config.oauth2 import oauth2_settings
from config.features import get_config, feature_enabled, get_all_feature_flags

# Create Laravel-style application using bootstrap/application.py
from bootstrap.application import create_app

laravel_app = create_app()

# Register and boot service providers
laravel_app.register_configured_providers()
laravel_app.boot()

# Get enhanced configuration
enhanced_config = get_config("development")  # Would detect environment properly
enabled_features = [name for name, enabled in get_all_feature_flags().items() if enabled]

app = FastAPI(
    title=f"{settings.APP_NAME} with Enhanced Laravel Features",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description=f"""
    FastAPI application with Laravel-style architecture and enhanced enterprise features.
    
    ## Core Features
    
    - **Laravel-style MVC Architecture**: Controllers, Services, Models, Middleware
    - **Complete OAuth2 Implementation**: All grant types, scopes, token management
    - **Strict Type Checking**: Full mypy coverage with comprehensive type hints
    - **Role-Based Access Control**: Spatie-like permissions and roles
    - **JWT Authentication**: Secure token-based authentication
    - **Multi-Factor Authentication**: TOTP and WebAuthn support
    - **Database Migrations**: SQLAlchemy models with relationships
    
    ## Enhanced Features ({len(enabled_features)} enabled)
    
    - **Enhanced Middleware Manager**: Advanced middleware orchestration with priorities
    - **Enhanced Routing System**: Route metrics, caching, and auto-discovery
    - **Enhanced Authentication Guards**: Multiple guard types with session/token support
    - **Enhanced Authorization Policies**: Context-aware policies with caching and rules
    - **Monitoring Dashboard**: Comprehensive system monitoring and health checks
    - **Feature Flag System**: Dynamic feature toggling and configuration
    - **Performance Tracking**: Route-level performance metrics and analysis
    - **Security Enhancements**: Advanced rate limiting and security policies
    
    ## OAuth2 Grant Types
    
    - Authorization Code (with PKCE support)
    - Client Credentials  
    - Password Grant
    - Refresh Token
    
    ## Monitoring Endpoints
    
    - `/monitoring/dashboard` - System overview and metrics
    - `/monitoring/health` - Health check and diagnostics
    - `/monitoring/metrics` - Performance metrics
    - `/monitoring/security` - Security configuration status
    
    ## Authentication
    
    This API supports both traditional JWT authentication and OAuth2 authentication.
    Use the `/oauth/token` endpoint to obtain access tokens.
    
    **Enabled Features**: {', '.join(enabled_features)}
    """
)

# Set FastAPI app in Laravel application
laravel_app.set_fastapi_app(app)

# Add session middleware for web authentication
from starlette.middleware.sessions import SessionMiddleware
import secrets
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY or secrets.token_urlsafe(32))

# Setup enhanced middleware based on configuration
if feature_enabled("enhanced_middleware"):
    if enhanced_config["middleware"]["development_mode"]:
        setup_development_middleware(app)
    else:
        setup_production_middleware(app)
else:
    # Fallback to basic CORS middleware
    add_cors_middleware(app)

# Setup enhanced policies
if feature_enabled("enhanced_policies"):
    gate.policy(User, UserPolicy)

# Include routers
app.include_router(web_router)
app.include_router(api_router)
# Google-style user management endpoints (implement when needed)
app.include_router(oauth2_router)  # OAuth2 endpoints
app.include_router(discovery_router)  # OAuth2/OpenID Connect discovery endpoints
app.include_router(openid_router)  # OpenID Connect endpoints
app.include_router(mfa_router)  # MFA endpoints

# Include monitoring router if feature is enabled
if feature_enabled("monitoring_dashboard"):
    app.include_router(monitoring_router)  # Enhanced monitoring endpoints


# OAuth2 Server Metadata Endpoint
@app.get(
    "/.well-known/oauth-authorization-server",
    tags=["OAuth2"],
    summary="OAuth2 Server Metadata",
    description="RFC 8414: OAuth2 Authorization Server Metadata"
)
async def oauth2_server_metadata() -> Dict[str, Union[str, List[str], bool]]:
    """OAuth2 server metadata endpoint."""
    base_url = "http://localhost:8000"  # Should come from settings in production
    return oauth2_settings.to_server_metadata(base_url)


# Note: OpenID Connect endpoints are now handled by OpenIDConnectController
# This includes:
# - /.well-known/openid-configuration
# - /.well-known/jwks.json
# - /oauth/userinfo
# - /oauth/discovery


@app.on_event("startup")
async def startup_event() -> None:
    create_tables()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} with Laravel-style Architecture started!")
    print(f"🏗️  Laravel Application: {laravel_app.__class__.__name__} (Environment: {laravel_app.environment()})")
    
    # Enhanced startup information
    print(f"🎯 Enhanced Features ({len(enabled_features)} enabled):")
    for feature in enabled_features[:10]:  # Show first 10 features
        print(f"   ✅ {feature.replace('_', ' ').title()}")
    if len(enabled_features) > 10:
        print(f"   ... and {len(enabled_features) - 10} more features")
    
    print(f"📊 OAuth2 Settings:")
    print(f"   - Enabled Grants: {', '.join(oauth2_settings.oauth2_enabled_grants)}")
    print(f"   - Supported Scopes: {len(oauth2_settings.oauth2_supported_scopes)} scopes")
    print(f"   - Access Token TTL: {oauth2_settings.oauth2_access_token_expire_minutes} minutes")
    print(f"   - Refresh Token TTL: {oauth2_settings.oauth2_refresh_token_expire_days} days")
    print(f"   - PKCE Required: {oauth2_settings.oauth2_require_pkce}")
    print(f"   - OpenID Connect: {'Enabled' if oauth2_settings.oauth2_enable_openid_connect else 'Disabled'}")
    
    # Enhanced system information
    print(f"🛠️  Enhanced System:")
    print(f"   - Middleware Manager: {'Enabled' if feature_enabled('enhanced_middleware') else 'Disabled'}")
    print(f"   - Route Metrics: {'Enabled' if feature_enabled('enhanced_routing') else 'Disabled'}")
    print(f"   - Policy Caching: {'Enabled' if feature_enabled('policy_caching') else 'Disabled'}")
    print(f"   - Performance Tracking: {'Enabled' if feature_enabled('performance_tracking') else 'Disabled'}")
    print(f"   - Monitoring Dashboard: {'Enabled' if feature_enabled('monitoring_dashboard') else 'Disabled'}")
    
    print(f"📝 API Documentation: http://localhost:8000/docs")
    print(f"🔍 OAuth2 Metadata: http://localhost:8000/.well-known/oauth-authorization-server")
    
    if feature_enabled("monitoring_dashboard"):
        print(f"📊 Monitoring Dashboard: http://localhost:8000/monitoring/dashboard")
        print(f"🏥 Health Check: http://localhost:8000/monitoring/health")
    
    # Route summary
    total_routes = len(route_manager.routes)
    if total_routes > 0:
        print(f"🛣️  Routes: {total_routes} registered routes with enhanced tracking")
    
    # Middleware summary
    middleware_info = middleware_manager.get_middleware_info()
    print(f"🔧 Middleware: {middleware_info['enabled_count']}/{middleware_info['registered_count']} enabled")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    print("🛑 Laravel FastAPI Application shutting down...")
    laravel_app.terminate()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=settings.DEBUG
    )