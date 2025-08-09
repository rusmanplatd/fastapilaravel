"""OAuth2 Analytics Service

This service provides analytics and reporting capabilities for OAuth2 usage,
including event tracking, metrics aggregation, and dashboard data generation.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from datetime import datetime, timedelta
import json
from collections import defaultdict, Counter

from app.Services.BaseService import BaseService
from app.Models.OAuth2Analytics import (
    OAuth2AnalyticsEvent, OAuth2MetricsSummary, OAuth2ClientAnalytics,
    OAuth2UserAnalytics, OAuth2PerformanceMetrics, OAuth2EventType
)
from app.Models import OAuth2Client, User, OAuth2AccessToken, OAuth2RefreshToken
from app.Models.OAuth2TokenStorage import OAuth2TokenStorage


class OAuth2AnalyticsService(BaseService):
    """OAuth2 Analytics and Reporting Service."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.event_buffer = []
        self.buffer_size = 100
        self.real_time_events = []
        
    async def track_event(
        self,
        event_type: OAuth2EventType,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        performance_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        error_description: Optional[str] = None
    ) -> OAuth2AnalyticsEvent:
        """Track an OAuth2 event for analytics."""
        
        event = OAuth2AnalyticsEvent(
            event_type=event_type.value,
            event_category="oauth2",
            client_id=client_id,
            user_id=user_id,
            ip_address=request_data.get("ip_address") if request_data else None,
            user_agent=request_data.get("user_agent") if request_data else None,
            request_id=request_data.get("request_id") if request_data else None,
            grant_type=request_data.get("grant_type") if request_data else None,
            scope=request_data.get("scope") if request_data else None,
            response_type=request_data.get("response_type") if request_data else None,
            response_time_ms=performance_data.get("response_time_ms") if performance_data else None,
            event_data=request_data or {},
            success=success,
            error_code=error_code,
            error_description=error_description,
            country=request_data.get("country") if request_data else None,
            city=request_data.get("city") if request_data else None,
            device_type=request_data.get("device_type") if request_data else None,
            browser=request_data.get("browser") if request_data else None
        )
        
        # Add to buffer for batch processing
        self.event_buffer.append(event)
        
        # Add to real-time events (keep last 1000)
        self.real_time_events.append(event)
        if len(self.real_time_events) > 1000:
            self.real_time_events.pop(0)
        
        # Flush buffer if full
        if len(self.event_buffer) >= self.buffer_size:
            await self.flush_events()
        
        return event
    
    async def flush_events(self) -> int:
        """Flush buffered events to database."""
        
        if not self.event_buffer:
            return 0
        
        events_to_flush = self.event_buffer.copy()
        self.event_buffer.clear()
        
        # Bulk insert events
        self.db.bulk_save_objects(events_to_flush)
        self.db.commit()
        
        return len(events_to_flush)
    
    async def generate_daily_summary(self, date: datetime) -> OAuth2MetricsSummary:
        """Generate daily summary metrics for a specific date."""
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Query events for the day
        events = self.db.query(OAuth2AnalyticsEvent).filter(
            and_(
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date
            )
        ).all()
        
        # Calculate metrics
        metrics = self._calculate_metrics_from_events(events)
        
        # Create or update summary record
        summary = self.db.query(OAuth2MetricsSummary).filter(
            and_(
                OAuth2MetricsSummary.date == start_date,
                OAuth2MetricsSummary.aggregation_level == "daily",
                OAuth2MetricsSummary.client_id.is_(None)
            )
        ).first()
        
        if not summary:
            summary = OAuth2MetricsSummary(
                date=start_date,
                aggregation_level="daily"
            )
        
        # Update metrics
        for key, value in metrics.items():
            if hasattr(summary, key):
                setattr(summary, key, value)
        
        self.db.merge(summary)
        self.db.commit()
        
        return summary
    
    async def generate_hourly_summary(self, date: datetime, hour: int) -> OAuth2MetricsSummary:
        """Generate hourly summary metrics."""
        
        start_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        events = self.db.query(OAuth2AnalyticsEvent).filter(
            and_(
                OAuth2AnalyticsEvent.created_at >= start_time,
                OAuth2AnalyticsEvent.created_at < end_time
            )
        ).all()
        
        metrics = self._calculate_metrics_from_events(events)
        
        summary = self.db.query(OAuth2MetricsSummary).filter(
            and_(
                OAuth2MetricsSummary.date == date.replace(hour=0, minute=0, second=0, microsecond=0),
                OAuth2MetricsSummary.hour == hour,
                OAuth2MetricsSummary.aggregation_level == "hourly",
                OAuth2MetricsSummary.client_id.is_(None)
            )
        ).first()
        
        if not summary:
            summary = OAuth2MetricsSummary(
                date=date.replace(hour=0, minute=0, second=0, microsecond=0),
                hour=hour,
                aggregation_level="hourly"
            )
        
        for key, value in metrics.items():
            if hasattr(summary, key):
                setattr(summary, key, value)
        
        self.db.merge(summary)
        self.db.commit()
        
        return summary
    
    def _calculate_metrics_from_events(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, Any]:
        """Calculate metrics from a list of events."""
        
        metrics = {
            "tokens_issued": 0,
            "tokens_refreshed": 0,
            "tokens_revoked": 0,
            "tokens_expired": 0,
            "authorization_requests": 0,
            "token_requests": 0,
            "introspection_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "authorization_code_grants": 0,
            "client_credentials_grants": 0,
            "password_grants": 0,
            "refresh_token_grants": 0,
            "device_code_grants": 0,
            "security_events": 0,
            "rate_limited_requests": 0,
            "unique_users": 0,
            "unique_clients": 0,
            "avg_response_time_ms": 0.0,
            "max_response_time_ms": 0,
            "min_response_time_ms": 0
        }
        
        if not events:
            return metrics
        
        unique_users = set()
        unique_clients = set()
        response_times = []
        
        for event in events:
            # Count event types
            if event.event_type == OAuth2EventType.TOKEN_ISSUED.value:
                metrics["tokens_issued"] += 1
            elif event.event_type == OAuth2EventType.TOKEN_REFRESHED.value:
                metrics["tokens_refreshed"] += 1
            elif event.event_type == OAuth2EventType.TOKEN_REVOKED.value:
                metrics["tokens_revoked"] += 1
            elif event.event_type == OAuth2EventType.TOKEN_EXPIRED.value:
                metrics["tokens_expired"] += 1
            elif event.event_type == OAuth2EventType.AUTHORIZATION_REQUEST.value:
                metrics["authorization_requests"] += 1
            elif event.event_type == OAuth2EventType.TOKEN_REQUEST.value:
                metrics["token_requests"] += 1
            elif event.event_type == OAuth2EventType.TOKEN_INTROSPECTED.value:
                metrics["introspection_requests"] += 1
            
            # Count grant types
            if event.grant_type == "authorization_code":
                metrics["authorization_code_grants"] += 1
            elif event.grant_type == "client_credentials":
                metrics["client_credentials_grants"] += 1
            elif event.grant_type == "password":
                metrics["password_grants"] += 1
            elif event.grant_type == "refresh_token":
                metrics["refresh_token_grants"] += 1
            elif event.grant_type == "device_code":
                metrics["device_code_grants"] += 1
            
            # Count success/failure
            if event.success:
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1
            
            # Count security events
            if event.event_type in [
                OAuth2EventType.INVALID_CLIENT.value,
                OAuth2EventType.INVALID_GRANT.value,
                OAuth2EventType.SUSPICIOUS_ACTIVITY.value
            ]:
                metrics["security_events"] += 1
            
            if event.event_type == OAuth2EventType.RATE_LIMITED.value:
                metrics["rate_limited_requests"] += 1
            
            # Track unique users and clients
            if event.user_id:
                unique_users.add(event.user_id)
            if event.client_id:
                unique_clients.add(event.client_id)
            
            # Track response times
            if event.response_time_ms:
                response_times.append(event.response_time_ms)
        
        metrics["unique_users"] = len(unique_users)
        metrics["unique_clients"] = len(unique_clients)
        
        # Calculate response time statistics
        if response_times:
            metrics["avg_response_time_ms"] = sum(response_times) / len(response_times)
            metrics["max_response_time_ms"] = max(response_times)
            metrics["min_response_time_ms"] = min(response_times)
        
        return metrics
    
    async def get_dashboard_data(
        self,
        days: int = 30,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard data for the specified period."""
        
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days)
        
        # Get daily summaries
        query = self.db.query(OAuth2MetricsSummary).filter(
            and_(
                OAuth2MetricsSummary.date >= start_date,
                OAuth2MetricsSummary.date < end_date,
                OAuth2MetricsSummary.aggregation_level == "daily"
            )
        )
        
        if client_id:
            query = query.filter(OAuth2MetricsSummary.client_id == client_id)
        else:
            query = query.filter(OAuth2MetricsSummary.client_id.is_(None))
        
        daily_summaries = query.order_by(OAuth2MetricsSummary.date).all()
        
        # Calculate totals
        totals = self._calculate_totals_from_summaries(daily_summaries)
        
        # Get recent events for activity feed
        recent_events = self.db.query(OAuth2AnalyticsEvent).filter(
            OAuth2AnalyticsEvent.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(desc(OAuth2AnalyticsEvent.created_at)).limit(50).all()
        
        # Get top clients
        top_clients = await self._get_top_clients(start_date, end_date)
        
        # Get error analysis
        error_analysis = await self._get_error_analysis(start_date, end_date)
        
        # Get performance metrics
        performance_metrics = await self._get_performance_metrics(start_date, end_date)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "totals": totals,
            "daily_summaries": [self._summary_to_dict(s) for s in daily_summaries],
            "recent_events": [self._event_to_dict(e) for e in recent_events],
            "top_clients": top_clients,
            "error_analysis": error_analysis,
            "performance_metrics": performance_metrics,
            "real_time_events": [self._event_to_dict(e) for e in self.real_time_events[-10:]]
        }
    
    async def get_client_analytics(
        self,
        client_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed analytics for a specific client."""
        
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days)
        
        # Get client info
        client = self.db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id
        ).first()
        
        if not client:
            raise ValueError(f"Client {client_id} not found")
        
        # Get client analytics records
        client_analytics = self.db.query(OAuth2ClientAnalytics).filter(
            and_(
                OAuth2ClientAnalytics.client_id == client_id,
                OAuth2ClientAnalytics.date >= start_date,
                OAuth2ClientAnalytics.date < end_date
            )
        ).order_by(OAuth2ClientAnalytics.date).all()
        
        # Get events for this client
        events = self.db.query(OAuth2AnalyticsEvent).filter(
            and_(
                OAuth2AnalyticsEvent.client_id == client_id,
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date
            )
        ).all()
        
        # Calculate client-specific metrics
        metrics = self._calculate_client_metrics(events)
        
        return {
            "client": {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "client_type": client.client_type,
                "created_at": client.created_at.isoformat() if client.created_at else None
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "metrics": metrics,
            "daily_analytics": [self._client_analytics_to_dict(ca) for ca in client_analytics],
            "scope_usage": self._analyze_scope_usage(events),
            "user_engagement": self._analyze_user_engagement(events),
            "geographic_distribution": self._analyze_geographic_distribution(events),
            "device_analytics": self._analyze_device_usage(events)
        }
    
    async def get_user_analytics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed analytics for a specific user."""
        
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days)
        
        # Get user info
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get user events
        events = self.db.query(OAuth2AnalyticsEvent).filter(
            and_(
                OAuth2AnalyticsEvent.user_id == user_id,
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date
            )
        ).all()
        
        return {
            "user": {
                "user_id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "client_usage": self._analyze_user_client_usage(events),
            "scope_preferences": self._analyze_user_scope_preferences(events),
            "session_patterns": self._analyze_user_session_patterns(events),
            "consent_behavior": self._analyze_user_consent_behavior(events)
        }
    
    async def _get_top_clients(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get top clients by usage."""
        
        client_usage = self.db.query(
            OAuth2AnalyticsEvent.client_id,
            func.count(OAuth2AnalyticsEvent.id).label('event_count'),
            func.count(func.distinct(OAuth2AnalyticsEvent.user_id)).label('unique_users')
        ).filter(
            and_(
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date,
                OAuth2AnalyticsEvent.client_id.isnot(None)
            )
        ).group_by(
            OAuth2AnalyticsEvent.client_id
        ).order_by(
            desc('event_count')
        ).limit(10).all()
        
        results = []
        for usage in client_usage:
            client = self.db.query(OAuth2Client).filter(
                OAuth2Client.client_id == usage.client_id
            ).first()
            
            results.append({
                "client_id": usage.client_id,
                "client_name": client.client_name if client else "Unknown",
                "event_count": usage.event_count,
                "unique_users": usage.unique_users
            })
        
        return results
    
    async def _get_error_analysis(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get error analysis for the period."""
        
        errors = self.db.query(
            OAuth2AnalyticsEvent.error_code,
            func.count(OAuth2AnalyticsEvent.id).label('count')
        ).filter(
            and_(
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date,
                OAuth2AnalyticsEvent.success == False,
                OAuth2AnalyticsEvent.error_code.isnot(None)
            )
        ).group_by(
            OAuth2AnalyticsEvent.error_code
        ).order_by(
            desc('count')
        ).all()
        
        return {
            "error_breakdown": [
                {"error_code": error.error_code, "count": error.count}
                for error in errors
            ],
            "total_errors": sum(error.count for error in errors)
        }
    
    async def _get_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get performance metrics for the period."""
        
        perf_data = self.db.query(
            func.avg(OAuth2AnalyticsEvent.response_time_ms).label('avg_response_time'),
            func.max(OAuth2AnalyticsEvent.response_time_ms).label('max_response_time'),
            func.min(OAuth2AnalyticsEvent.response_time_ms).label('min_response_time')
        ).filter(
            and_(
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date,
                OAuth2AnalyticsEvent.response_time_ms.isnot(None)
            )
        ).first()
        
        return {
            "avg_response_time_ms": float(perf_data.avg_response_time) if perf_data.avg_response_time else 0,
            "max_response_time_ms": perf_data.max_response_time or 0,
            "min_response_time_ms": perf_data.min_response_time or 0
        }
    
    def _calculate_totals_from_summaries(
        self,
        summaries: List[OAuth2MetricsSummary]
    ) -> Dict[str, Any]:
        """Calculate totals from summary records."""
        
        totals = {
            "tokens_issued": 0,
            "tokens_refreshed": 0,
            "tokens_revoked": 0,
            "authorization_requests": 0,
            "token_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "unique_users": 0,
            "unique_clients": 0
        }
        
        for summary in summaries:
            totals["tokens_issued"] += summary.tokens_issued
            totals["tokens_refreshed"] += summary.tokens_refreshed
            totals["tokens_revoked"] += summary.tokens_revoked
            totals["authorization_requests"] += summary.authorization_requests
            totals["token_requests"] += summary.token_requests
            totals["successful_requests"] += summary.successful_requests
            totals["failed_requests"] += summary.failed_requests
            totals["unique_users"] = max(totals["unique_users"], summary.unique_users)
            totals["unique_clients"] = max(totals["unique_clients"], summary.unique_clients)
        
        return totals
    
    def _calculate_client_metrics(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, Any]:
        """Calculate metrics specific to a client."""
        return self._calculate_metrics_from_events(events)
    
    def _analyze_scope_usage(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, int]:
        """Analyze scope usage patterns."""
        scope_counter = Counter()
        
        for event in events:
            if event.scope:
                scopes = event.scope.split()
                for scope in scopes:
                    scope_counter[scope] += 1
        
        return dict(scope_counter.most_common(10))
    
    def _analyze_user_engagement(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, Any]:
        """Analyze user engagement patterns."""
        user_events = defaultdict(int)
        
        for event in events:
            if event.user_id:
                user_events[event.user_id] += 1
        
        return {
            "total_users": len(user_events),
            "avg_events_per_user": sum(user_events.values()) / len(user_events) if user_events else 0,
            "most_active_users": dict(Counter(user_events).most_common(5))
        }
    
    def _analyze_geographic_distribution(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, int]:
        """Analyze geographic distribution of requests."""
        country_counter = Counter()
        
        for event in events:
            if event.country:
                country_counter[event.country] += 1
        
        return dict(country_counter.most_common(10))
    
    def _analyze_device_usage(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, Any]:
        """Analyze device and browser usage patterns."""
        device_counter = Counter()
        browser_counter = Counter()
        
        for event in events:
            if event.device_type:
                device_counter[event.device_type] += 1
            if event.browser:
                browser_counter[event.browser] += 1
        
        return {
            "device_types": dict(device_counter.most_common(5)),
            "browsers": dict(browser_counter.most_common(5))
        }
    
    def _analyze_user_client_usage(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, int]:
        """Analyze which clients a user uses most."""
        client_counter = Counter()
        
        for event in events:
            if event.client_id:
                client_counter[event.client_id] += 1
        
        return dict(client_counter.most_common(10))
    
    def _analyze_user_scope_preferences(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, int]:
        """Analyze user's scope preferences."""
        return self._analyze_scope_usage(events)
    
    def _analyze_user_session_patterns(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, Any]:
        """Analyze user session patterns."""
        session_times = []
        
        for event in events:
            if event.created_at:
                session_times.append(event.created_at.hour)
        
        hour_counter = Counter(session_times)
        
        return {
            "total_sessions": len(events),
            "hourly_distribution": dict(hour_counter),
            "most_active_hour": hour_counter.most_common(1)[0][0] if hour_counter else None
        }
    
    def _analyze_user_consent_behavior(self, events: List[OAuth2AnalyticsEvent]) -> Dict[str, Any]:
        """Analyze user consent behavior."""
        consent_granted = 0
        consent_denied = 0
        
        for event in events:
            if event.event_type == OAuth2EventType.USER_CONSENT.value:
                consent_granted += 1
            elif event.event_type == OAuth2EventType.AUTHORIZATION_DENIED.value:
                consent_denied += 1
        
        return {
            "consents_granted": consent_granted,
            "consents_denied": consent_denied,
            "approval_rate": consent_granted / (consent_granted + consent_denied) if (consent_granted + consent_denied) > 0 else 0
        }
    
    def _summary_to_dict(self, summary: OAuth2MetricsSummary) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "date": summary.date.isoformat(),
            "hour": summary.hour,
            "aggregation_level": summary.aggregation_level,
            "tokens_issued": summary.tokens_issued,
            "tokens_refreshed": summary.tokens_refreshed,
            "tokens_revoked": summary.tokens_revoked,
            "authorization_requests": summary.authorization_requests,
            "token_requests": summary.token_requests,
            "successful_requests": summary.successful_requests,
            "failed_requests": summary.failed_requests,
            "unique_users": summary.unique_users,
            "unique_clients": summary.unique_clients,
            "avg_response_time_ms": summary.avg_response_time_ms
        }
    
    def _event_to_dict(self, event: OAuth2AnalyticsEvent) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": event.id,
            "event_type": event.event_type,
            "client_id": event.client_id,
            "user_id": event.user_id,
            "success": event.success,
            "error_code": event.error_code,
            "response_time_ms": event.response_time_ms,
            "created_at": event.created_at.isoformat() if event.created_at else None
        }
    
    def _client_analytics_to_dict(self, analytics: OAuth2ClientAnalytics) -> Dict[str, Any]:
        """Convert client analytics to dictionary."""
        return {
            "date": analytics.date.isoformat(),
            "total_requests": analytics.total_requests,
            "successful_requests": analytics.successful_requests,
            "failed_requests": analytics.failed_requests,
            "unique_users": analytics.unique_users,
            "avg_response_time": analytics.avg_response_time
        }