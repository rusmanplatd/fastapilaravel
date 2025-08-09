"""
Enhanced Features Configuration
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta

@dataclass
class MiddlewareConfig:
    """Enhanced middleware configuration."""
    enabled: bool = True
    priority: int = 50
    config: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class AuthConfig:
    """Enhanced authentication configuration."""
    default_guard: str = "api"
    session_lifetime: int = 120  # minutes
    token_lifetime: int = 60     # minutes
    remember_me_lifetime: int = 43200  # minutes (30 days)
    mfa_required: bool = False
    allow_impersonation: bool = True
    trusted_networks: List[str] = field(default_factory=lambda: ["127.0.0.1", "::1"])

@dataclass 
class PolicyConfig:
    """Enhanced policy configuration."""
    cache_enabled: bool = True
    cache_ttl: int = 300  # seconds
    track_usage: bool = True
    rate_limiting: bool = True
    maintenance_mode_check: bool = True

@dataclass
class RouteConfig:
    """Enhanced routing configuration."""
    auto_discovery: bool = True
    route_caching: bool = True  
    versioning: bool = True
    api_documentation: bool = True
    metrics_tracking: bool = True

@dataclass
class MonitoringConfig:
    """Enhanced monitoring configuration."""
    performance_tracking: bool = True
    slow_request_threshold: float = 1.0
    memory_monitoring: bool = False
    cpu_monitoring: bool = False  
    database_query_tracking: bool = True
    dashboard_enabled: bool = True

# Enhanced Features Configuration
ENHANCED_FEATURES_CONFIG = {
    "middleware": {
        "manager_enabled": True,
        "development_mode": True,  # Set to False for production
        "default_middleware": {
            "performance": MiddlewareConfig(
                enabled=True,
                priority=20,
                config={
                    "log_slow_requests": True,
                    "slow_request_threshold": 1.0,
                    "monitor_memory": True,
                    "monitor_cpu": True,
                    "track_database_queries": True
                }
            ),
            "enhanced_auth": MiddlewareConfig(
                enabled=True,
                priority=30,
                config={
                    "exclude_paths": [
                        "/docs", "/redoc", "/openapi.json",
                        "/health", "/metrics", "/favicon.ico",
                        "/api/v1/auth/login", "/api/v1/auth/register"
                    ]
                }
            ),
            "activity_log": MiddlewareConfig(
                enabled=True,
                priority=40,
                config={
                    "log_requests": True,
                    "log_responses": True,
                    "exclude_paths": ["/health", "/metrics"]
                }
            ),
            "cache": MiddlewareConfig(
                enabled=True,
                priority=60,
                config={
                    "cache_control_max_age": 300,
                    "enable_etag": True
                }
            )
        }
    },
    
    "auth": AuthConfig(
        default_guard="api",
        session_lifetime=120,
        token_lifetime=60,
        remember_me_lifetime=43200,
        mfa_required=False,
        allow_impersonation=True,
        trusted_networks=["127.0.0.1", "::1", "10.0.0.0/8", "192.168.0.0/16"]
    ),
    
    "policies": PolicyConfig(
        cache_enabled=True,
        cache_ttl=300,
        track_usage=True,
        rate_limiting=True,
        maintenance_mode_check=True
    ),
    
    "routing": RouteConfig(
        auto_discovery=True,
        route_caching=True,
        versioning=True,
        api_documentation=True,
        metrics_tracking=True
    ),
    
    "monitoring": MonitoringConfig(
        performance_tracking=True,
        slow_request_threshold=1.0,
        memory_monitoring=False,  # Disable in production
        cpu_monitoring=False,     # Disable in production
        database_query_tracking=True,
        dashboard_enabled=True
    )
}

# Production overrides
PRODUCTION_OVERRIDES = {
    "middleware": {
        "development_mode": False,
        "default_middleware": {
            "performance": MiddlewareConfig(
                enabled=True,
                priority=20,
                config={
                    "log_slow_requests": True,
                    "slow_request_threshold": 2.0,  # More lenient
                    "monitor_memory": False,
                    "monitor_cpu": False,
                    "track_database_queries": True
                }
            )
        }
    },
    "auth": AuthConfig(
        session_lifetime=60,  # Shorter in production
        token_lifetime=30,    # Shorter in production
        mfa_required=True,    # Require MFA in production
        trusted_networks=[]  # Define actual trusted networks
    ),
    "monitoring": MonitoringConfig(
        memory_monitoring=False,
        cpu_monitoring=False,
        slow_request_threshold=2.0
    )
}

def get_config(environment: str = "development") -> Dict[str, Any]:
    """Get configuration based on environment."""
    config = ENHANCED_FEATURES_CONFIG.copy()
    
    if environment == "production":
        # Apply production overrides
        config.update(PRODUCTION_OVERRIDES)
    
    return config

def is_feature_enabled(feature_path: str, environment: str = "development") -> bool:
    """Check if a feature is enabled."""
    config = get_config(environment)
    
    # Navigate through the nested config
    parts = feature_path.split('.')
    current = config
    
    try:
        current_value: Any = current
        for part in parts:
            if isinstance(current_value, dict):
                current_value = current_value[part]
            else:
                return False
        
        # If it's a boolean, return it directly
        if isinstance(current_value, bool):
            return current_value
        
        # If it's a dataclass, check for 'enabled' attribute
        if hasattr(current_value, 'enabled'):
            enabled_attr = getattr(current_value, 'enabled')
            return bool(enabled_attr)
        
        # If it's a dict with 'enabled' key
        if isinstance(current_value, dict) and 'enabled' in current_value:
            enabled_value = current_value['enabled']
            return bool(enabled_value)
        
        return True  # Default to enabled if not specified
    except (KeyError, TypeError, AttributeError):
        return False

def get_feature_config(feature_path: str, environment: str = "development") -> Any:
    """Get configuration for a specific feature."""
    config = get_config(environment)
    
    parts = feature_path.split('.')
    current = config
    
    try:
        for part in parts:
            current = current[part]
        return current
    except (KeyError, TypeError):
        return None

# Feature flags for easy toggling
FEATURE_FLAGS = {
    "enhanced_middleware": True,
    "enhanced_routing": True,
    "enhanced_auth": True,
    "enhanced_policies": True,
    "monitoring_dashboard": True,
    "route_caching": True,
    "policy_caching": True,
    "performance_tracking": True,
    "activity_logging": True,
    "mfa_enforcement": False,  # Enable in production
    "impersonation": True,
    "rate_limiting": True,
    "maintenance_mode": False
}

def feature_enabled(feature_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return FEATURE_FLAGS.get(feature_name, False)

def set_feature_flag(feature_name: str, enabled: bool) -> None:
    """Set a feature flag."""
    FEATURE_FLAGS[feature_name] = enabled

def get_all_feature_flags() -> Dict[str, bool]:
    """Get all feature flags."""
    return FEATURE_FLAGS.copy()

# Enhanced security settings
SECURITY_CONFIG = {
    "password_policy": {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True, 
        "require_numbers": True,
        "require_special_chars": True,
        "max_age_days": 90,
        "prevent_reuse": 5
    },
    "session_security": {
        "secure_cookies": True,
        "http_only": True,
        "same_site": "strict",
        "regenerate_on_login": True
    },
    "rate_limiting": {
        "login_attempts": {
            "max_attempts": 5,
            "window_minutes": 15,
            "lockout_minutes": 30
        },
        "api_requests": {
            "max_requests": 1000,
            "window_minutes": 60
        },
        "password_reset": {
            "max_attempts": 3,
            "window_minutes": 60
        }
    }
}

def get_security_config() -> Dict[str, Any]:
    """Get security configuration."""
    return SECURITY_CONFIG.copy()