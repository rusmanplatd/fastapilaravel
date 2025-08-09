"""OAuth2 Analytics Models

This module defines analytics models for tracking OAuth2 usage patterns,
performance metrics, and security events.
"""

from __future__ import annotations

from sqlalchemy import String, Text, DateTime, Integer, Boolean, JSON, Float, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from app.Models.BaseModel import BaseModel


class OAuth2EventType(str, Enum):
    """OAuth2 event types for analytics tracking."""
    
    # Authorization flow events
    AUTHORIZATION_REQUEST = "authorization_request"
    AUTHORIZATION_GRANTED = "authorization_granted"
    AUTHORIZATION_DENIED = "authorization_denied"
    
    # Token events
    TOKEN_REQUEST = "token_request"
    TOKEN_ISSUED = "token_issued"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_REVOKED = "token_revoked"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INTROSPECTED = "token_introspected"
    
    # Client events
    CLIENT_REGISTERED = "client_registered"
    CLIENT_UPDATED = "client_updated"
    CLIENT_DELETED = "client_deleted"
    
    # Security events
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    RATE_LIMITED = "rate_limited"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # User events
    USER_CONSENT = "user_consent"
    USER_CONSENT_REVOKED = "user_consent_revoked"


class OAuth2AnalyticsEvent(BaseModel):
    """OAuth2 analytics event tracking."""
    
    __tablename__ = "oauth2_analytics_events"
    
    # Event identification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, default="oauth2")
    
    # Associated entities
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Request information
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # OAuth2 specific data
    grant_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Performance metrics
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Event data (JSON)
    event_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Status and error information
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Geographic and device info
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_oauth2_analytics_event_type_time', 'event_type', 'created_at'),
        Index('idx_oauth2_analytics_client_time', 'client_id', 'created_at'),
        Index('idx_oauth2_analytics_user_time', 'user_id', 'created_at'),
        Index('idx_oauth2_analytics_success_time', 'success', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2AnalyticsEvent(event_type='{self.event_type}', client_id='{self.client_id}')>"


class OAuth2MetricsSummary(BaseModel):
    """Daily/hourly summary metrics for OAuth2 usage."""
    
    __tablename__ = "oauth2_metrics_summary"
    
    # Time period
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 0-23 for hourly, null for daily
    
    # Aggregation level
    aggregation_level: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")  # daily, hourly
    
    # Client breakdown
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Token metrics
    tokens_issued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_refreshed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_revoked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_expired: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Request metrics
    authorization_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    introspection_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Success/failure rates
    successful_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Grant type breakdown
    authorization_code_grants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    client_credentials_grants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    password_grants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refresh_token_grants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    device_code_grants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Performance metrics
    avg_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Security metrics
    security_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_limited_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Unique users and clients
    unique_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_clients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_metrics_date_level', 'date', 'aggregation_level'),
        Index('idx_oauth2_metrics_client_date', 'client_id', 'date'),
        Index('idx_oauth2_metrics_hour_date', 'hour', 'date'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2MetricsSummary(date='{self.date}', level='{self.aggregation_level}')>"


class OAuth2ClientAnalytics(BaseModel):
    """Analytics data for OAuth2 clients."""
    
    __tablename__ = "oauth2_client_analytics"
    
    # Client identification
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Time period
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Usage statistics
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Token statistics
    access_tokens_issued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refresh_tokens_issued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_revoked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # User engagement
    unique_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returning_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Scope usage
    most_used_scopes: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    scope_usage_count: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    # Performance
    avg_response_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Error analysis
    error_breakdown: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    # Geographic distribution
    country_distribution: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    # Device/browser analytics
    device_type_distribution: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    browser_distribution: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_client_analytics_client_date', 'client_id', 'date'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2ClientAnalytics(client_id='{self.client_id}', date='{self.date}')>"


class OAuth2UserAnalytics(BaseModel):
    """Analytics data for OAuth2 user behavior."""
    
    __tablename__ = "oauth2_user_analytics"
    
    # User identification
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Time period
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Usage patterns
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens_issued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Client usage
    clients_used: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    client_usage_count: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    # Scope preferences
    scopes_requested: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    scope_request_count: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    # Consent behavior
    consents_granted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consents_denied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consents_revoked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Geographic and device info
    countries_accessed_from: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    devices_used: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Security metrics
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_user_analytics_user_date', 'user_id', 'date'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2UserAnalytics(user_id='{self.user_id}', date='{self.date}')>"


class OAuth2PerformanceMetrics(BaseModel):
    """Performance metrics for OAuth2 endpoints."""
    
    __tablename__ = "oauth2_performance_metrics"
    
    # Endpoint identification
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="POST")
    
    # Time period
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Performance data
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Request details
    request_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Additional metrics
    database_queries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cache_hits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cache_misses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_performance_endpoint_time', 'endpoint', 'timestamp'),
        Index('idx_oauth2_performance_status_time', 'status_code', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2PerformanceMetrics(endpoint='{self.endpoint}', response_time={self.response_time_ms}ms)>"