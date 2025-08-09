from __future__ import annotations

"""
Laravel Horizon Routes - Queue Dashboard and Monitoring

Routes for the Horizon queue monitoring dashboard and API endpoints.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.Horizon import Horizon

router = APIRouter(prefix="/horizon", tags=["Horizon Dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main Horizon dashboard page."""
    # This would render the dashboard template
    # For now, return a simple HTML response
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Horizon Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #3182ce; }
            .stat-label { color: #666; margin-top: 5px; }
            .nav { margin: 20px 0; }
            .nav a { background: #3182ce; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-right: 10px; }
            .nav a:hover { background: #2c5aa0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌅 Laravel Horizon Dashboard</h1>
            <p>Queue monitoring and management for FastAPI</p>
            <div class="nav">
                <a href="/horizon/api/stats">API Stats</a>
                <a href="/horizon/api/supervisors">Supervisors</a>
                <a href="/horizon/api/queues">Queues</a>
                <a href="/horizon/api/workers">Workers</a>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="supervisors">-</div>
                <div class="stat-label">Supervisors</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="workers">-</div>
                <div class="stat-label">Active Workers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="jobs">-</div>
                <div class="stat-label">Jobs Processed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="status">-</div>
                <div class="stat-label">Status</div>
            </div>
        </div>
        
        <script>
            async function loadStats() {
                try {
                    const response = await fetch('/horizon/api/stats');
                    const stats = await response.json();
                    
                    document.getElementById('supervisors').textContent = stats.overview?.total_supervisors || 0;
                    document.getElementById('workers').textContent = stats.overview?.active_workers || 0;
                    document.getElementById('jobs').textContent = stats.overview?.total_jobs_processed || 0;
                    document.getElementById('status').textContent = stats.overview?.status || 'Unknown';
                } catch (error) {
                    console.error('Failed to load stats:', error);
                }
            }
            
            // Load stats on page load and refresh every 5 seconds
            loadStats();
            setInterval(loadStats, 5000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=dashboard_html)


@router.get("/api/stats")
async def get_stats():
    """Get comprehensive Horizon statistics."""
    return await Horizon.get_stats()


@router.get("/api/supervisors")
async def get_supervisors():
    """Get supervisor information."""
    return await Horizon.get_supervisors()


@router.get("/api/queues")
async def get_queues():
    """Get queue information."""
    return await Horizon.get_queues()


@router.get("/api/workers")
async def get_workers():
    """Get worker information."""
    return await Horizon.get_workers()


@router.get("/api/jobs")
async def get_jobs():
    """Get job statistics."""
    return await Horizon.get_jobs()


@router.get("/api/metrics")
async def get_metrics():
    """Get system metrics."""
    return await Horizon.get_metrics()


@router.post("/api/pause")
async def pause_all():
    """Pause all supervisors."""
    await Horizon.pause()
    return {"message": "All supervisors paused"}


@router.post("/api/continue")
async def continue_all():
    """Continue all supervisors."""
    await Horizon.continue_processing()
    return {"message": "All supervisors continued"}


@router.post("/api/supervisors/{supervisor_name}/pause")
async def pause_supervisor(supervisor_name: str):
    """Pause a specific supervisor."""
    await Horizon.pause(supervisor_name)
    return {"message": f"Supervisor {supervisor_name} paused"}


@router.post("/api/supervisors/{supervisor_name}/continue") 
async def continue_supervisor(supervisor_name: str):
    """Continue a paused supervisor."""
    await Horizon.continue_processing(supervisor_name)
    return {"message": f"Supervisor {supervisor_name} continued"}


@router.get("/api/supervisors/{supervisor_name}")
async def get_supervisor_details(supervisor_name: str):
    """Get detailed information about a specific supervisor."""
    supervisors = await Horizon.get_supervisors()
    
    supervisor = next(
        (s for s in supervisors if s.get('name') == supervisor_name),
        None
    )
    
    if not supervisor:
        return JSONResponse(
            content={"error": f"Supervisor {supervisor_name} not found"},
            status_code=404
        )
    
    return supervisor


@router.get("/api/queues/{queue_name}")
async def get_queue_details(queue_name: str):
    """Get detailed information about a specific queue.""" 
    queues = await Horizon.get_queues()
    
    queue = queues.get(queue_name)
    if not queue:
        return JSONResponse(
            content={"error": f"Queue {queue_name} not found"},
            status_code=404
        )
    
    return queue


@router.get("/api/workers/{worker_id}")
async def get_worker_details(worker_id: str):
    """Get detailed information about a specific worker."""
    workers = await Horizon.get_workers()
    
    worker = next(
        (w for w in workers if w.get('id') == worker_id),
        None
    )
    
    if not worker:
        return JSONResponse(
            content={"error": f"Worker {worker_id} not found"},
            status_code=404
        )
    
    return worker


@router.get("/api/health")
async def health_check():
    """Health check endpoint for Horizon."""
    is_running = Horizon.is_running()
    
    return {
        "status": "healthy" if is_running else "stopped",
        "horizon_running": is_running,
        "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
    }