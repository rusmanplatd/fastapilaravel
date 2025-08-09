from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .HorizonManager import HorizonManager


class HorizonDashboard:
    """
    Laravel Horizon-style web dashboard for queue monitoring.
    
    Provides a real-time web interface for monitoring queues,
    workers, jobs, and system metrics.
    """
    
    def __init__(self, horizon_manager: HorizonManager) -> None:
        self.horizon = horizon_manager
        self.templates = Jinja2Templates(directory="resources/views/horizon")
        self.active_connections: List[WebSocket] = []
    
    def setup_routes(self, app: FastAPI) -> None:
        """Setup dashboard routes in FastAPI app."""
        
        # Static files for dashboard assets
        app.mount("/horizon/assets", StaticFiles(directory="resources/assets/horizon"), name="horizon-assets")  # type: ignore[attr-defined]
        
        @app.get("/horizon", response_class=HTMLResponse)  # type: ignore[misc]
        async def dashboard_index(request: Request):
            """Main dashboard page."""
            stats = await self.horizon.get_dashboard_stats()
            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                "stats": stats,
                "title": "Horizon Dashboard"
            })
        
        @app.get("/horizon/api/stats")  # type: ignore[misc]
        async def get_stats():
            """API endpoint for dashboard statistics."""
            return await self.horizon.get_dashboard_stats()
        
        @app.get("/horizon/api/supervisors")  # type: ignore[misc]
        async def get_supervisors():
            """Get supervisor information."""
            stats = await self.horizon.get_dashboard_stats()
            return stats.get('supervisors', [])
        
        @app.get("/horizon/api/queues")  # type: ignore[misc]
        async def get_queues():
            """Get queue information."""
            stats = await self.horizon.get_dashboard_stats()
            return stats.get('queues', {})
        
        @app.get("/horizon/api/workers")  # type: ignore[misc]
        async def get_workers():
            """Get worker information."""
            stats = await self.horizon.get_dashboard_stats()
            return stats.get('workers', [])
        
        @app.get("/horizon/api/jobs")  # type: ignore[misc]
        async def get_jobs() -> Dict[str, Any]:
            """Get job statistics."""
            stats = await self.horizon.get_dashboard_stats()
            return stats.get('jobs', {})
        
        @app.get("/horizon/api/metrics")  # type: ignore[misc]
        async def get_metrics() -> Dict[str, Any]:
            """Get system metrics."""
            stats = await self.horizon.get_dashboard_stats()
            return stats.get('metrics', {})
        
        @app.post("/horizon/api/supervisors/{supervisor_name}/pause")  # type: ignore[misc]
        async def pause_supervisor(supervisor_name: str) -> Dict[str, str]:
            """Pause a supervisor."""
            await self.horizon.pause(supervisor_name)
            return {"message": f"Supervisor {supervisor_name} paused"}
        
        @app.post("/horizon/api/supervisors/{supervisor_name}/continue")  # type: ignore[misc]
        async def continue_supervisor(supervisor_name: str) -> Dict[str, str]:
            """Continue a paused supervisor."""
            await self.horizon.continue_processing(supervisor_name)
            return {"message": f"Supervisor {supervisor_name} continued"}
        
        @app.post("/horizon/api/pause")  # type: ignore[misc]
        async def pause_all() -> Dict[str, str]:
            """Pause all supervisors."""
            await self.horizon.pause()
            return {"message": "All supervisors paused"}
        
        @app.post("/horizon/api/continue")  # type: ignore[misc]
        async def continue_all() -> Dict[str, str]:
            """Continue all supervisors."""
            await self.horizon.continue_processing()
            return {"message": "All supervisors continued"}
        
        @app.websocket("/horizon/ws")  # type: ignore[attr-defined]
        async def websocket_endpoint(websocket: WebSocket) -> None:
            """WebSocket endpoint for real-time updates."""
            await self._handle_websocket(websocket)
    
    async def _handle_websocket(self, websocket: WebSocket) -> None:
        """Handle WebSocket connections for real-time updates."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                # Send periodic updates
                stats = await self.horizon.get_dashboard_stats()
                await websocket.send_json({
                    'type': 'stats_update',
                    'data': stats,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Wait for next update cycle (5 seconds)
                import asyncio
                await asyncio.sleep(5)
                
        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
        except Exception as e:
            print(f"WebSocket error: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast_update(self, update_type: str, data: Any) -> None:
        """Broadcast updates to all connected WebSocket clients."""
        if not self.active_connections:
            return
        
        message = {
            'type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Remove disconnected clients
        connected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                connected.append(connection)
            except Exception:
                # Client disconnected
                pass
        
        self.active_connections = connected


def create_dashboard_html() -> str:
    """Generate the HTML template for the Horizon dashboard."""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horizon Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; }
        .header { background: white; border-bottom: 1px solid #e2e8f0; padding: 1rem 2rem; }
        .header h1 { color: #2d3748; font-size: 1.5rem; }
        .nav { display: flex; gap: 2rem; margin-top: 1rem; }
        .nav button { background: none; border: 1px solid #e2e8f0; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; }
        .nav button.active { background: #3182ce; color: white; border-color: #3182ce; }
        .nav button:hover { background: #f7fafc; }
        .nav button.active:hover { background: #2c5aa0; }
        .main { padding: 2rem; }
        .grid { display: grid; gap: 1.5rem; }
        .grid-2 { grid-template-columns: repeat(2, 1fr); }
        .grid-3 { grid-template-columns: repeat(3, 1fr); }
        .grid-4 { grid-template-columns: repeat(4, 1fr); }
        .card { background: white; border-radius: 0.5rem; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .stat { text-align: center; }
        .stat-number { font-size: 2rem; font-weight: bold; color: #2d3748; }
        .stat-label { color: #718096; margin-top: 0.5rem; }
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
        .table th { background: #f7fafc; font-weight: 600; }
        .status { padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 500; }
        .status-running { background: #c6f6d5; color: #22543d; }
        .status-paused { background: #fed7d7; color: #742a2a; }
        .status-stopped { background: #e2e8f0; color: #4a5568; }
        .btn { background: #3182ce; color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; }
        .btn:hover { background: #2c5aa0; }
        .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
        .text-center { text-align: center; }
        .mt-4 { margin-top: 1rem; }
        #chart-container { height: 300px; }
    </style>
</head>
<body>
    <div id="app">
        <div class="header">
            <h1>🌅 Horizon Dashboard</h1>
            <div class="nav">
                <button @click="activeTab = 'overview'" :class="{active: activeTab === 'overview'}">Overview</button>
                <button @click="activeTab = 'supervisors'" :class="{active: activeTab === 'supervisors'}">Supervisors</button>
                <button @click="activeTab = 'queues'" :class="{active: activeTab === 'queues'}">Queues</button>
                <button @click="activeTab = 'workers'" :class="{active: activeTab === 'workers'}">Workers</button>
                <button @click="activeTab = 'jobs'" :class="{active: activeTab === 'jobs'}">Jobs</button>
                <button @click="activeTab = 'metrics'" :class="{active: activeTab === 'metrics'}">Metrics</button>
            </div>
        </div>
        
        <div class="main">
            <!-- Overview Tab -->
            <div v-if="activeTab === 'overview'">
                <div class="grid grid-4 mb-6">
                    <div class="card stat">
                        <div class="stat-number">{{ stats.overview?.total_supervisors || 0 }}</div>
                        <div class="stat-label">Supervisors</div>
                    </div>
                    <div class="card stat">
                        <div class="stat-number">{{ stats.overview?.active_workers || 0 }}</div>
                        <div class="stat-label">Active Workers</div>
                    </div>
                    <div class="card stat">
                        <div class="stat-number">{{ stats.overview?.total_jobs_processed || 0 }}</div>
                        <div class="stat-label">Jobs Processed</div>
                    </div>
                    <div class="card stat">
                        <div class="stat-number" :class="statusClass(stats.overview?.status)">{{ stats.overview?.status || 'Unknown' }}</div>
                        <div class="stat-label">Status</div>
                    </div>
                </div>
                
                <div class="grid grid-2">
                    <div class="card">
                        <h3>Quick Actions</h3>
                        <div class="mt-4">
                            <button class="btn btn-sm" @click="pauseAll">Pause All</button>
                            <button class="btn btn-sm" @click="continueAll" style="margin-left: 0.5rem;">Continue All</button>
                        </div>
                    </div>
                    <div class="card">
                        <h3>System Status</h3>
                        <div class="mt-4">
                            <div>Horizon: <span class="status" :class="statusClass(stats.overview?.status)">{{ stats.overview?.status || 'Unknown' }}</span></div>
                            <div style="margin-top: 0.5rem;">Last Updated: {{ new Date().toLocaleTimeString() }}</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Supervisors Tab -->
            <div v-if="activeTab === 'supervisors'">
                <div class="card">
                    <h3>Supervisors</h3>
                    <table class="table mt-4">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Status</th>
                                <th>Processes</th>
                                <th>Queues</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="supervisor in stats.supervisors || []" :key="supervisor.name">
                                <td>{{ supervisor.name }}</td>
                                <td><span class="status" :class="statusClass(supervisor.status)">{{ supervisor.status }}</span></td>
                                <td>{{ supervisor.processes }}</td>
                                <td>{{ supervisor.queues?.join(', ') || '' }}</td>
                                <td>
                                    <button class="btn btn-sm" @click="pauseSupervisor(supervisor.name)">Pause</button>
                                    <button class="btn btn-sm" @click="continueSupervisor(supervisor.name)" style="margin-left: 0.25rem;">Continue</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Queues Tab -->
            <div v-if="activeTab === 'queues'">
                <div class="card">
                    <h3>Queue Statistics</h3>
                    <table class="table mt-4">
                        <thead>
                            <tr>
                                <th>Queue</th>
                                <th>Pending Jobs</th>
                                <th>Processed Jobs</th>
                                <th>Failed Jobs</th>
                                <th>Avg. Processing Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(queue, name) in stats.queues || {}" :key="name">
                                <td>{{ name }}</td>
                                <td>{{ queue.pending_jobs || 0 }}</td>
                                <td>{{ queue.processed_jobs || 0 }}</td>
                                <td>{{ queue.failed_jobs || 0 }}</td>
                                <td>{{ queue.avg_processing_time || 0 }}s</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Workers Tab -->
            <div v-if="activeTab === 'workers'">
                <div class="card">
                    <h3>Worker Processes</h3>
                    <table class="table mt-4">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Supervisor</th>
                                <th>Status</th>
                                <th>PID</th>
                                <th>Jobs Processed</th>
                                <th>Current Job</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="worker in stats.workers || []" :key="worker.id">
                                <td>{{ worker.id }}</td>
                                <td>{{ worker.supervisor }}</td>
                                <td><span class="status" :class="statusClass(worker.status)">{{ worker.status }}</span></td>
                                <td>{{ worker.pid || 'N/A' }}</td>
                                <td>{{ worker.jobs_processed || 0 }}</td>
                                <td>{{ worker.current_job || 'Idle' }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Jobs Tab -->
            <div v-if="activeTab === 'jobs'">
                <div class="card">
                    <h3>Job Statistics</h3>
                    <div class="grid grid-3 mt-4">
                        <div class="stat">
                            <div class="stat-number">{{ stats.jobs?.total_jobs || 0 }}</div>
                            <div class="stat-label">Total Jobs</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ stats.jobs?.completed_jobs || 0 }}</div>
                            <div class="stat-label">Completed</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ stats.jobs?.failed_jobs || 0 }}</div>
                            <div class="stat-label">Failed</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Metrics Tab -->
            <div v-if="activeTab === 'metrics'">
                <div class="card">
                    <h3>System Metrics</h3>
                    <div class="grid grid-2 mt-4">
                        <div>
                            <h4>Throughput (Jobs/min)</h4>
                            <div id="chart-container">
                                <canvas id="throughputChart"></canvas>
                            </div>
                        </div>
                        <div>
                            <h4>System Resources</h4>
                            <div class="mt-4">
                                <div>Memory Usage: {{ stats.metrics?.memory_usage || 0 }}%</div>
                                <div>CPU Usage: {{ stats.metrics?.cpu_usage || 0 }}%</div>
                                <div>Redis Memory: {{ stats.metrics?.redis_memory || 0 }}MB</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const { createApp } = Vue;
        
        createApp({
            data() {
                return {
                    activeTab: 'overview',
                    stats: {},
                    ws: null,
                    chart: null
                }
            },
            mounted() {
                this.loadStats();
                this.setupWebSocket();
                this.setupPeriodicRefresh();
            },
            methods: {
                async loadStats() {
                    try {
                        const response = await fetch('/horizon/api/stats');
                        this.stats = await response.json();
                    } catch (error) {
                        console.error('Failed to load stats:', error);
                    }
                },
                setupWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    this.ws = new WebSocket(`${protocol}//${window.location.host}/horizon/ws`);
                    
                    this.ws.onmessage = (event) => {
                        const message = JSON.parse(event.data);
                        if (message.type === 'stats_update') {
                            this.stats = message.data;
                        }
                    };
                    
                    this.ws.onclose = () => {
                        setTimeout(() => this.setupWebSocket(), 5000);
                    };
                },
                setupPeriodicRefresh() {
                    setInterval(() => {
                        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                            this.loadStats();
                        }
                    }, 10000);
                },
                async pauseAll() {
                    try {
                        await fetch('/horizon/api/pause', { method: 'POST' });
                        this.loadStats();
                    } catch (error) {
                        console.error('Failed to pause:', error);
                    }
                },
                async continueAll() {
                    try {
                        await fetch('/horizon/api/continue', { method: 'POST' });
                        this.loadStats();
                    } catch (error) {
                        console.error('Failed to continue:', error);
                    }
                },
                async pauseSupervisor(name) {
                    try {
                        await fetch(`/horizon/api/supervisors/${name}/pause`, { method: 'POST' });
                        this.loadStats();
                    } catch (error) {
                        console.error('Failed to pause supervisor:', error);
                    }
                },
                async continueSupervisor(name) {
                    try {
                        await fetch(`/horizon/api/supervisors/${name}/continue`, { method: 'POST' });
                        this.loadStats();
                    } catch (error) {
                        console.error('Failed to continue supervisor:', error);
                    }
                },
                statusClass(status) {
                    return {
                        'status-running': status === 'running',
                        'status-paused': status === 'paused',
                        'status-stopped': status === 'stopped'
                    };
                }
            }
        }).mount('#app');
    </script>
</body>
</html>
    '''


# Create the dashboard template file
def setup_horizon_templates() -> None:
    """Setup Horizon dashboard templates."""
    import os
    
    template_dir = "resources/views/horizon"
    os.makedirs(template_dir, exist_ok=True)
    
    with open(f"{template_dir}/dashboard.html", "w") as f:
        f.write(create_dashboard_html())