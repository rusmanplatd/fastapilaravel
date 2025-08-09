"""OAuth2 Analytics Dashboard Controller

This controller provides endpoints for OAuth2 analytics dashboard,
including metrics, reporting, and real-time data.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2AnalyticsService import OAuth2AnalyticsService
from app.Models.OAuth2Analytics import OAuth2EventType
from app.Database.database import get_db
from app.Http.Middleware.auth_middleware import require_auth
from app.Http.Middleware.permission_middleware import require_permission


class OAuth2AnalyticsController(BaseController):
    """OAuth2 Analytics Dashboard Controller."""
    
    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter(prefix="/api/v1/oauth2/analytics", tags=["OAuth2 Analytics"])
        self.setup_routes()
    
    def setup_routes(self) -> None:
        """Setup analytics routes."""
        
        # Dashboard routes
        self.router.get("/dashboard")(self.get_dashboard)
        self.router.get("/dashboard/data")(self.get_dashboard_data)
        self.router.get("/real-time")(self.get_real_time_data)
        
        # Metrics routes
        self.router.get("/metrics/summary")(self.get_metrics_summary)
        self.router.get("/metrics/daily")(self.get_daily_metrics)
        self.router.get("/metrics/hourly")(self.get_hourly_metrics)
        
        # Client analytics
        self.router.get("/clients")(self.get_client_list)
        self.router.get("/clients/{client_id}")(self.get_client_analytics)
        self.router.get("/clients/{client_id}/events")(self.get_client_events)
        
        # User analytics
        self.router.get("/users/{user_id}")(self.get_user_analytics)
        self.router.get("/users/{user_id}/events")(self.get_user_events)
        
        # Event tracking
        self.router.post("/events")(self.track_event)
        self.router.get("/events")(self.get_events)
        self.router.get("/events/types")(self.get_event_types)
        
        # Performance metrics
        self.router.get("/performance")(self.get_performance_metrics)
        self.router.get("/performance/endpoints")(self.get_endpoint_performance)
        
        # Reports
        self.router.get("/reports/usage")(self.get_usage_report)
        self.router.get("/reports/security")(self.get_security_report)
        self.router.get("/reports/errors")(self.get_error_report)
        
        # Export functionality
        self.router.get("/export/csv")(self.export_csv)
        self.router.get("/export/json")(self.export_json)
    
    async def get_dashboard(
        self,
        request: Request,
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> HTMLResponse:
        """Render the analytics dashboard HTML page."""
        
        # In a real implementation, this would render an HTML template
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>OAuth2 Analytics Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; }
                .metric { text-align: center; margin: 10px 0; }
                .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
                .metric-label { color: #666; }
                .chart-container { position: relative; height: 300px; }
            </style>
        </head>
        <body>
            <h1>OAuth2 Analytics Dashboard</h1>
            <div class="dashboard">
                <div class="card">
                    <h3>Overview</h3>
                    <div class="metric">
                        <div class="metric-value" id="total-tokens">-</div>
                        <div class="metric-label">Total Tokens Issued</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="active-users">-</div>
                        <div class="metric-label">Active Users</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Token Requests</h3>
                    <div class="chart-container">
                        <canvas id="token-chart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Success Rate</h3>
                    <div class="chart-container">
                        <canvas id="success-chart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Recent Events</h3>
                    <div id="recent-events">
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
            
            <script>
                // Load dashboard data
                fetch('/api/v1/oauth2/analytics/dashboard/data')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('total-tokens').textContent = data.totals.tokens_issued;
                        document.getElementById('active-users').textContent = data.totals.unique_users;
                        
                        // Create charts
                        createTokenChart(data.daily_summaries);
                        createSuccessChart(data.totals);
                        displayRecentEvents(data.recent_events);
                    });
                
                function createTokenChart(dailySummaries) {
                    const ctx = document.getElementById('token-chart').getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: dailySummaries.map(d => new Date(d.date).toLocaleDateString()),
                            datasets: [{
                                label: 'Tokens Issued',
                                data: dailySummaries.map(d => d.tokens_issued),
                                borderColor: 'rgb(75, 192, 192)',
                                tension: 0.1
                            }]
                        }
                    });
                }
                
                function createSuccessChart(totals) {
                    const ctx = document.getElementById('success-chart').getContext('2d');
                    new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Successful', 'Failed'],
                            datasets: [{
                                data: [totals.successful_requests, totals.failed_requests],
                                backgroundColor: ['#28a745', '#dc3545']
                            }]
                        }
                    });
                }
                
                function displayRecentEvents(events) {
                    const container = document.getElementById('recent-events');
                    container.innerHTML = events.map(event => 
                        `<div><strong>${event.event_type}</strong> - ${new Date(event.created_at).toLocaleString()}</div>`
                    ).join('');
                }
                
                // Auto-refresh every 30 seconds
                setInterval(() => {
                    location.reload();
                }, 30000);
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
    
    async def get_dashboard_data(
        self,
        days: int = Query(30, ge=1, le=365),
        client_id: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Get dashboard data."""
        
        analytics_service = OAuth2AnalyticsService(db)
        return await analytics_service.get_dashboard_data(days=days, client_id=client_id)
    
    async def get_real_time_data(
        self,
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Get real-time analytics data."""
        
        analytics_service = OAuth2AnalyticsService(db)
        
        # Get recent events from the last hour
        recent_events = analytics_service.real_time_events[-20:]  # Last 20 events
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "recent_events": [analytics_service._event_to_dict(e) for e in recent_events],
            "event_count_last_hour": len([e for e in recent_events if e.created_at > datetime.utcnow() - timedelta(hours=1)]),
            "active_clients": len(set(e.client_id for e in recent_events if e.client_id)),
            "active_users": len(set(e.user_id for e in recent_events if e.user_id))
        }
    
    async def get_metrics_summary(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Get metrics summary."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=days)
        
        return {
            "period": dashboard_data["period"],
            "totals": dashboard_data["totals"],
            "performance": dashboard_data["performance_metrics"]
        }
    
    async def get_daily_metrics(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get daily metrics."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=days)
        
        return dashboard_data["daily_summaries"]
    
    async def get_hourly_metrics(
        self,
        date: str = Query(...),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get hourly metrics for a specific date."""
        
        try:
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        analytics_service = OAuth2AnalyticsService(db)
        hourly_metrics = []
        
        for hour in range(24):
            summary = await analytics_service.generate_hourly_summary(target_date, hour)
            hourly_metrics.append(analytics_service._summary_to_dict(summary))
        
        return hourly_metrics
    
    async def get_client_list(
        self,
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get list of clients with analytics summary."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=30)
        
        return dashboard_data["top_clients"]
    
    async def get_client_analytics(
        self,
        client_id: str,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Get detailed analytics for a specific client."""
        
        analytics_service = OAuth2AnalyticsService(db)
        try:
            return await analytics_service.get_client_analytics(client_id, days=days)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    async def get_client_events(
        self,
        client_id: str,
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get recent events for a specific client."""
        
        from app.Models.OAuth2Analytics import OAuth2AnalyticsEvent
        from sqlalchemy import desc
        
        events = db.query(OAuth2AnalyticsEvent).filter(
            OAuth2AnalyticsEvent.client_id == client_id
        ).order_by(desc(OAuth2AnalyticsEvent.created_at)).limit(limit).all()
        
        analytics_service = OAuth2AnalyticsService(db)
        return [analytics_service._event_to_dict(event) for event in events]
    
    async def get_user_analytics(
        self,
        user_id: str,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Get detailed analytics for a specific user."""
        
        analytics_service = OAuth2AnalyticsService(db)
        try:
            return await analytics_service.get_user_analytics(user_id, days=days)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    async def get_user_events(
        self,
        user_id: str,
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get recent events for a specific user."""
        
        from app.Models.OAuth2Analytics import OAuth2AnalyticsEvent
        from sqlalchemy import desc
        
        events = db.query(OAuth2AnalyticsEvent).filter(
            OAuth2AnalyticsEvent.user_id == user_id
        ).order_by(desc(OAuth2AnalyticsEvent.created_at)).limit(limit).all()
        
        analytics_service = OAuth2AnalyticsService(db)
        return [analytics_service._event_to_dict(event) for event in events]
    
    async def track_event(
        self,
        event_data: Dict[str, Any],
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Track a custom OAuth2 event."""
        
        try:
            event_type = OAuth2EventType(event_data["event_type"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid event_type")
        
        analytics_service = OAuth2AnalyticsService(db)
        
        event = await analytics_service.track_event(
            event_type=event_type,
            client_id=event_data.get("client_id"),
            user_id=event_data.get("user_id"),
            request_data=event_data.get("request_data"),
            performance_data=event_data.get("performance_data"),
            success=event_data.get("success", True),
            error_code=event_data.get("error_code"),
            error_description=event_data.get("error_description")
        )
        
        return analytics_service._event_to_dict(event)
    
    async def get_events(
        self,
        limit: int = Query(100, ge=1, le=1000),
        event_type: Optional[str] = Query(None),
        client_id: Optional[str] = Query(None),
        user_id: Optional[str] = Query(None),
        success: Optional[bool] = Query(None),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get events with optional filtering."""
        
        from app.Models.OAuth2Analytics import OAuth2AnalyticsEvent
        from sqlalchemy import desc, and_
        
        query = db.query(OAuth2AnalyticsEvent)
        filters = []
        
        if event_type:
            filters.append(OAuth2AnalyticsEvent.event_type == event_type)
        if client_id:
            filters.append(OAuth2AnalyticsEvent.client_id == client_id)
        if user_id:
            filters.append(OAuth2AnalyticsEvent.user_id == user_id)
        if success is not None:
            filters.append(OAuth2AnalyticsEvent.success == success)
        
        if filters:
            query = query.filter(and_(*filters))
        
        events = query.order_by(desc(OAuth2AnalyticsEvent.created_at)).limit(limit).all()
        
        analytics_service = OAuth2AnalyticsService(db)
        return [analytics_service._event_to_dict(event) for event in events]
    
    async def get_event_types(self) -> List[Dict[str, str]]:
        """Get available event types."""
        
        return [
            {"value": event_type.value, "label": event_type.value.replace("_", " ").title()}
            for event_type in OAuth2EventType
        ]
    
    async def get_performance_metrics(
        self,
        hours: int = Query(24, ge=1, le=168),  # Max 1 week
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Get performance metrics."""
        
        from app.Models.OAuth2Analytics import OAuth2PerformanceMetrics
        from sqlalchemy import func, desc
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = db.query(
            OAuth2PerformanceMetrics.endpoint,
            func.avg(OAuth2PerformanceMetrics.response_time_ms).label('avg_response_time'),
            func.max(OAuth2PerformanceMetrics.response_time_ms).label('max_response_time'),
            func.min(OAuth2PerformanceMetrics.response_time_ms).label('min_response_time'),
            func.count(OAuth2PerformanceMetrics.id).label('request_count')
        ).filter(
            OAuth2PerformanceMetrics.timestamp >= start_time
        ).group_by(
            OAuth2PerformanceMetrics.endpoint
        ).all()
        
        return {
            "period": {
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "hours": hours
            },
            "endpoints": [
                {
                    "endpoint": metric.endpoint,
                    "avg_response_time_ms": float(metric.avg_response_time),
                    "max_response_time_ms": metric.max_response_time,
                    "min_response_time_ms": metric.min_response_time,
                    "request_count": metric.request_count
                }
                for metric in metrics
            ]
        }
    
    async def get_endpoint_performance(
        self,
        endpoint: str,
        hours: int = Query(24, ge=1, le=168),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> List[Dict[str, Any]]:
        """Get performance data for a specific endpoint."""
        
        from app.Models.OAuth2Analytics import OAuth2PerformanceMetrics
        from sqlalchemy import desc
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = db.query(OAuth2PerformanceMetrics).filter(
            and_(
                OAuth2PerformanceMetrics.endpoint == endpoint,
                OAuth2PerformanceMetrics.timestamp >= start_time
            )
        ).order_by(desc(OAuth2PerformanceMetrics.timestamp)).limit(1000).all()
        
        return [
            {
                "timestamp": metric.timestamp.isoformat(),
                "response_time_ms": metric.response_time_ms,
                "status_code": metric.status_code,
                "request_size_bytes": metric.request_size_bytes,
                "response_size_bytes": metric.response_size_bytes
            }
            for metric in metrics
        ]
    
    async def get_usage_report(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Generate usage report."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=days)
        
        return {
            "report_type": "usage",
            "generated_at": datetime.utcnow().isoformat(),
            "period": dashboard_data["period"],
            "summary": dashboard_data["totals"],
            "daily_breakdown": dashboard_data["daily_summaries"],
            "top_clients": dashboard_data["top_clients"]
        }
    
    async def get_security_report(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Generate security report."""
        
        from app.Models.OAuth2Analytics import OAuth2AnalyticsEvent
        from sqlalchemy import func, desc, and_
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get security-related events
        security_events = db.query(
            OAuth2AnalyticsEvent.event_type,
            func.count(OAuth2AnalyticsEvent.id).label('count')
        ).filter(
            and_(
                OAuth2AnalyticsEvent.created_at >= start_date,
                OAuth2AnalyticsEvent.created_at < end_date,
                OAuth2AnalyticsEvent.event_type.in_([
                    OAuth2EventType.INVALID_CLIENT.value,
                    OAuth2EventType.INVALID_GRANT.value,
                    OAuth2EventType.SUSPICIOUS_ACTIVITY.value,
                    OAuth2EventType.RATE_LIMITED.value
                ])
            )
        ).group_by(OAuth2AnalyticsEvent.event_type).all()
        
        return {
            "report_type": "security",
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "security_events": [
                {"event_type": event.event_type, "count": event.count}
                for event in security_events
            ],
            "total_security_events": sum(event.count for event in security_events)
        }
    
    async def get_error_report(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Generate error report."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=days)
        
        return {
            "report_type": "errors",
            "generated_at": datetime.utcnow().isoformat(),
            "period": dashboard_data["period"],
            "error_analysis": dashboard_data["error_analysis"],
            "failed_requests": dashboard_data["totals"]["failed_requests"],
            "success_rate": dashboard_data["totals"]["successful_requests"] / 
                          (dashboard_data["totals"]["successful_requests"] + dashboard_data["totals"]["failed_requests"])
                          if (dashboard_data["totals"]["successful_requests"] + dashboard_data["totals"]["failed_requests"]) > 0 else 0
        }
    
    async def export_csv(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> JSONResponse:
        """Export analytics data as CSV."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=days)
        
        # Convert to CSV-like structure (would use actual CSV library in production)
        csv_data = "Date,Tokens Issued,Token Requests,Success Rate\n"
        
        for summary in dashboard_data["daily_summaries"]:
            total_requests = summary["successful_requests"] + summary["failed_requests"]
            success_rate = summary["successful_requests"] / total_requests if total_requests > 0 else 0
            csv_data += f"{summary['date']},{summary['tokens_issued']},{summary['token_requests']},{success_rate:.2%}\n"
        
        return JSONResponse(
            content={"csv_data": csv_data, "filename": f"oauth2_analytics_{days}days.csv"},
            headers={"Content-Disposition": "attachment; filename=oauth2_analytics.csv"}
        )
    
    async def export_json(
        self,
        days: int = Query(30, ge=1, le=365),
        db: Session = Depends(get_db),
        current_user = Depends(require_auth)
    ) -> Dict[str, Any]:
        """Export analytics data as JSON."""
        
        analytics_service = OAuth2AnalyticsService(db)
        dashboard_data = await analytics_service.get_dashboard_data(days=days)
        
        export_data = {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "export_type": "json",
                "period": dashboard_data["period"]
            },
            "data": dashboard_data
        }
        
        return export_data