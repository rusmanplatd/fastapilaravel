"""Create OAuth2 Analytics Tables

Migration for creating OAuth2 analytics and reporting tables.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Text, DateTime, Boolean, Integer
from sqlalchemy.types import JSON, Float
from datetime import datetime


def upgrade() -> None:
    """Create OAuth2 analytics tables."""
    
    # OAuth2 Analytics Events table
    op.create_table(
        'oauth2_analytics_events',
        
        # Primary key
        sa.Column('id', sa.Integer, primary_key=True),
        
        # Event identification
        sa.Column('event_type', String(50), nullable=False, index=True),
        sa.Column('event_category', String(50), nullable=False, default='oauth2'),
        
        # Associated entities
        sa.Column('client_id', String(255), nullable=True, index=True),
        sa.Column('user_id', String(255), nullable=True, index=True),
        
        # Request information
        sa.Column('ip_address', String(45), nullable=True),  # IPv6 support
        sa.Column('user_agent', Text, nullable=True),
        sa.Column('request_id', String(255), nullable=True),
        
        # OAuth2 specific data
        sa.Column('grant_type', String(50), nullable=True),
        sa.Column('scope', Text, nullable=True),
        sa.Column('response_type', String(50), nullable=True),
        
        # Performance metrics
        sa.Column('response_time_ms', Integer, nullable=True),
        
        # Event data (JSON)
        sa.Column('event_data', JSON, nullable=True),
        
        # Status and error information
        sa.Column('success', Boolean, default=True, nullable=False),
        sa.Column('error_code', String(50), nullable=True),
        sa.Column('error_description', Text, nullable=True),
        
        # Geographic and device info
        sa.Column('country', String(2), nullable=True),
        sa.Column('city', String(100), nullable=True),
        sa.Column('device_type', String(50), nullable=True),
        sa.Column('browser', String(100), nullable=True),
        
        # Timestamps
        sa.Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        
        # Performance indexes
        sa.Index('idx_oauth2_analytics_event_type_time', 'event_type', 'created_at'),
        sa.Index('idx_oauth2_analytics_client_time', 'client_id', 'created_at'),
        sa.Index('idx_oauth2_analytics_user_time', 'user_id', 'created_at'),
        sa.Index('idx_oauth2_analytics_success_time', 'success', 'created_at'),
    )
    
    # OAuth2 Metrics Summary table
    op.create_table(
        'oauth2_metrics_summary',
        
        # Primary key
        sa.Column('id', sa.Integer, primary_key=True),
        
        # Time period
        sa.Column('date', DateTime, nullable=False, index=True),
        sa.Column('hour', Integer, nullable=True, index=True),  # 0-23 for hourly, null for daily
        
        # Aggregation level
        sa.Column('aggregation_level', String(10), nullable=False, default='daily'),  # daily, hourly
        
        # Client breakdown
        sa.Column('client_id', String(255), nullable=True, index=True),
        
        # Token metrics
        sa.Column('tokens_issued', Integer, default=0, nullable=False),
        sa.Column('tokens_refreshed', Integer, default=0, nullable=False),
        sa.Column('tokens_revoked', Integer, default=0, nullable=False),
        sa.Column('tokens_expired', Integer, default=0, nullable=False),
        
        # Request metrics
        sa.Column('authorization_requests', Integer, default=0, nullable=False),
        sa.Column('token_requests', Integer, default=0, nullable=False),
        sa.Column('introspection_requests', Integer, default=0, nullable=False),
        
        # Success/failure rates
        sa.Column('successful_requests', Integer, default=0, nullable=False),
        sa.Column('failed_requests', Integer, default=0, nullable=False),
        
        # Grant type breakdown
        sa.Column('authorization_code_grants', Integer, default=0, nullable=False),
        sa.Column('client_credentials_grants', Integer, default=0, nullable=False),
        sa.Column('password_grants', Integer, default=0, nullable=False),
        sa.Column('refresh_token_grants', Integer, default=0, nullable=False),
        sa.Column('device_code_grants', Integer, default=0, nullable=False),
        
        # Performance metrics
        sa.Column('avg_response_time_ms', Float, nullable=True),
        sa.Column('max_response_time_ms', Integer, nullable=True),
        sa.Column('min_response_time_ms', Integer, nullable=True),
        
        # Security metrics
        sa.Column('security_events', Integer, default=0, nullable=False),
        sa.Column('rate_limited_requests', Integer, default=0, nullable=False),
        
        # Unique users and clients
        sa.Column('unique_users', Integer, default=0, nullable=False),
        sa.Column('unique_clients', Integer, default=0, nullable=False),
        
        # Timestamps
        sa.Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        
        # Indexes
        sa.Index('idx_oauth2_metrics_date_level', 'date', 'aggregation_level'),
        sa.Index('idx_oauth2_metrics_client_date', 'client_id', 'date'),
        sa.Index('idx_oauth2_metrics_hour_date', 'hour', 'date'),
    )
    
    # OAuth2 Client Analytics table
    op.create_table(
        'oauth2_client_analytics',
        
        # Primary key
        sa.Column('id', sa.Integer, primary_key=True),
        
        # Client identification
        sa.Column('client_id', String(255), nullable=False, index=True),
        
        # Time period
        sa.Column('date', DateTime, nullable=False, index=True),
        
        # Usage statistics
        sa.Column('total_requests', Integer, default=0, nullable=False),
        sa.Column('successful_requests', Integer, default=0, nullable=False),
        sa.Column('failed_requests', Integer, default=0, nullable=False),
        
        # Token statistics
        sa.Column('access_tokens_issued', Integer, default=0, nullable=False),
        sa.Column('refresh_tokens_issued', Integer, default=0, nullable=False),
        sa.Column('tokens_revoked', Integer, default=0, nullable=False),
        
        # User engagement
        sa.Column('unique_users', Integer, default=0, nullable=False),
        sa.Column('returning_users', Integer, default=0, nullable=False),
        sa.Column('new_users', Integer, default=0, nullable=False),
        
        # Scope usage (JSON arrays and objects)
        sa.Column('most_used_scopes', JSON, nullable=True),
        sa.Column('scope_usage_count', JSON, nullable=True),
        
        # Performance
        sa.Column('avg_response_time', Float, nullable=True),
        
        # Error analysis
        sa.Column('error_breakdown', JSON, nullable=True),
        
        # Geographic distribution
        sa.Column('country_distribution', JSON, nullable=True),
        
        # Device/browser analytics
        sa.Column('device_type_distribution', JSON, nullable=True),
        sa.Column('browser_distribution', JSON, nullable=True),
        
        # Timestamps
        sa.Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        
        # Indexes
        sa.Index('idx_oauth2_client_analytics_client_date', 'client_id', 'date'),
    )
    
    # OAuth2 User Analytics table
    op.create_table(
        'oauth2_user_analytics',
        
        # Primary key
        sa.Column('id', sa.Integer, primary_key=True),
        
        # User identification
        sa.Column('user_id', String(255), nullable=False, index=True),
        
        # Time period
        sa.Column('date', DateTime, nullable=False, index=True),
        
        # Usage patterns
        sa.Column('total_sessions', Integer, default=0, nullable=False),
        sa.Column('total_tokens_issued', Integer, default=0, nullable=False),
        
        # Client usage
        sa.Column('clients_used', JSON, nullable=True),
        sa.Column('client_usage_count', JSON, nullable=True),
        
        # Scope preferences
        sa.Column('scopes_requested', JSON, nullable=True),
        sa.Column('scope_request_count', JSON, nullable=True),
        
        # Consent behavior
        sa.Column('consents_granted', Integer, default=0, nullable=False),
        sa.Column('consents_denied', Integer, default=0, nullable=False),
        sa.Column('consents_revoked', Integer, default=0, nullable=False),
        
        # Geographic and device info
        sa.Column('countries_accessed_from', JSON, nullable=True),
        sa.Column('devices_used', JSON, nullable=True),
        
        # Security metrics
        sa.Column('failed_attempts', Integer, default=0, nullable=False),
        
        # Timestamps
        sa.Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        
        # Indexes
        sa.Index('idx_oauth2_user_analytics_user_date', 'user_id', 'date'),
    )
    
    # OAuth2 Performance Metrics table
    op.create_table(
        'oauth2_performance_metrics',
        
        # Primary key
        sa.Column('id', sa.Integer, primary_key=True),
        
        # Endpoint identification
        sa.Column('endpoint', String(255), nullable=False, index=True),
        sa.Column('method', String(10), nullable=False, default='POST'),
        
        # Time period
        sa.Column('timestamp', DateTime, nullable=False, index=True),
        
        # Performance data
        sa.Column('response_time_ms', Integer, nullable=False),
        sa.Column('cpu_usage_percent', Float, nullable=True),
        sa.Column('memory_usage_mb', Float, nullable=True),
        
        # Request details
        sa.Column('request_size_bytes', Integer, nullable=True),
        sa.Column('response_size_bytes', Integer, nullable=True),
        
        # Status
        sa.Column('status_code', Integer, nullable=False, index=True),
        
        # Additional metrics
        sa.Column('database_queries', Integer, nullable=True),
        sa.Column('cache_hits', Integer, nullable=True),
        sa.Column('cache_misses', Integer, nullable=True),
        
        # Timestamps
        sa.Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        
        # Indexes
        sa.Index('idx_oauth2_performance_endpoint_time', 'endpoint', 'timestamp'),
        sa.Index('idx_oauth2_performance_status_time', 'status_code', 'timestamp'),
    )


def downgrade() -> None:
    """Drop OAuth2 analytics tables."""
    op.drop_table('oauth2_performance_metrics')
    op.drop_table('oauth2_user_analytics')
    op.drop_table('oauth2_client_analytics')
    op.drop_table('oauth2_metrics_summary')
    op.drop_table('oauth2_analytics_events')