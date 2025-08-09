from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from .TelescopeManager import TelescopeManager


class TelescopeDashboard:
    """
    Laravel Telescope Dashboard for FastAPI
    
    Provides a web-based interface for viewing application monitoring data.
    """
    
    def __init__(self, telescope_manager: TelescopeManager):
        self.telescope = telescope_manager
    
    async def render_dashboard(self, request: Request) -> HTMLResponse:
        """Render the main Telescope dashboard."""
        dashboard_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Telescope Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
                .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .nav { display: flex; gap: 15px; margin: 20px 0; }
                .nav a { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }
                .nav a:hover { background: #0056b3; }
                .nav a.active { background: #28a745; }
                .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
                .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
                .stat-label { color: #666; margin-top: 5px; }
                .content { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔭 Laravel Telescope Dashboard</h1>
                <p>Application monitoring and debugging for FastAPI</p>
                
                <div class="nav">
                    <a href="/telescope/" class="active">Dashboard</a>
                    <a href="/telescope/requests">Requests</a>
                    <a href="/telescope/queries">Queries</a>
                    <a href="/telescope/jobs">Jobs</a>
                    <a href="/telescope/mail">Mail</a>
                    <a href="/telescope/cache">Cache</a>
                    <a href="/telescope/exceptions">Exceptions</a>
                    <a href="/telescope/redis">Redis</a>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="requests-count">-</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="queries-count">-</div>
                    <div class="stat-label">Database Queries</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="exceptions-count">-</div>
                    <div class="stat-label">Exceptions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="jobs-count">-</div>
                    <div class="stat-label">Queue Jobs</div>
                </div>
            </div>
            
            <div class="content">
                <h2>Recent Activity</h2>
                <div id="recent-activity">
                    <p>Loading recent activity...</p>
                </div>
            </div>
            
            <script>
                async function loadStats() {
                    try {
                        const response = await fetch('/telescope/api/stats');
                        const stats = await response.json();
                        
                        document.getElementById('requests-count').textContent = stats.requests || 0;
                        document.getElementById('queries-count').textContent = stats.queries || 0;
                        document.getElementById('exceptions-count').textContent = stats.exceptions || 0;
                        document.getElementById('jobs-count').textContent = stats.jobs || 0;
                    } catch (error) {
                        console.error('Failed to load stats:', error);
                    }
                }
                
                async function loadRecentActivity() {
                    try {
                        const response = await fetch('/telescope/api/entries?limit=10');
                        const entries = await response.json();
                        
                        const activityHtml = entries.map(entry => `
                            <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                                <strong>${entry.type}</strong> - ${entry.content.method || ''} ${entry.content.path || entry.content.query || ''}
                                <small style="float: right; color: #666;">${new Date(entry.created_at).toLocaleString()}</small>
                            </div>
                        `).join('');
                        
                        document.getElementById('recent-activity').innerHTML = activityHtml || '<p>No recent activity</p>';
                    } catch (error) {
                        console.error('Failed to load recent activity:', error);
                        document.getElementById('recent-activity').innerHTML = '<p>Failed to load recent activity</p>';
                    }
                }
                
                // Load data on page load and refresh periodically
                loadStats();
                loadRecentActivity();
                setInterval(loadStats, 30000); // Refresh every 30 seconds
                setInterval(loadRecentActivity, 30000);
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=dashboard_html)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        return await self.telescope.get_stats()
    
    async def get_entries(
        self,
        entry_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get telescope entries."""
        return await self.telescope.get_entries(entry_type, limit, offset)
    
    async def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific telescope entry."""
        return await self.telescope.get_entry(entry_id)
    
    async def clear_entries(self, entry_type: Optional[str] = None) -> Dict[str, str]:
        """Clear telescope entries."""
        await self.telescope.clear_entries(entry_type)
        return {"message": "Entries cleared successfully"}
    
    async def render_requests(self, request: Request) -> HTMLResponse:
        """Render the requests page."""
        # This would render a more detailed requests view
        return HTMLResponse(content="<h1>Requests - Coming Soon</h1>")
    
    async def render_queries(self, request: Request) -> HTMLResponse:
        """Render the queries page."""
        # This would render a more detailed queries view
        return HTMLResponse(content="<h1>Queries - Coming Soon</h1>")
    
    async def render_jobs(self, request: Request) -> HTMLResponse:
        """Render the jobs page."""
        # This would render a more detailed jobs view
        return HTMLResponse(content="<h1>Jobs - Coming Soon</h1>")
    
    async def render_mail(self, request: Request) -> HTMLResponse:
        """Render the mail page."""
        # This would render a more detailed mail view
        return HTMLResponse(content="<h1>Mail - Coming Soon</h1>")
    
    async def render_cache(self, request: Request) -> HTMLResponse:
        """Render the cache page."""
        # This would render a more detailed cache view
        return HTMLResponse(content="<h1>Cache - Coming Soon</h1>")
    
    async def render_exceptions(self, request: Request) -> HTMLResponse:
        """Render the exceptions page."""
        # This would render a more detailed exceptions view
        return HTMLResponse(content="<h1>Exceptions - Coming Soon</h1>")
    
    async def render_redis(self, request: Request) -> HTMLResponse:
        """Render the redis page."""
        # This would render a more detailed redis view
        return HTMLResponse(content="<h1>Redis - Coming Soon</h1>")