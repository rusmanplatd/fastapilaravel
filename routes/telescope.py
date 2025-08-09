from __future__ import annotations

"""
Laravel Telescope Routes - Debug Dashboard and Monitoring

Routes for the Telescope debugging dashboard and API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.Telescope import Telescope

router = APIRouter(prefix="/telescope", tags=["Telescope Debug Dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Main Telescope dashboard page."""
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔭 Telescope Dashboard</title>
        <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f8fafc; }
            .header { background: #667eea; color: white; padding: 1.5rem 2rem; }
            .header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
            .nav { background: white; border-bottom: 1px solid #e2e8f0; padding: 0 2rem; }
            .nav-item { display: inline-block; padding: 1rem; cursor: pointer; border-bottom: 2px solid transparent; }
            .nav-item.active { border-bottom-color: #667eea; color: #667eea; }
            .nav-item:hover { background: #f7fafc; }
            .main { padding: 2rem; }
            .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
            .stat-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
            .stat-number { font-size: 2rem; font-weight: bold; color: #2d3748; }
            .stat-label { color: #718096; margin-top: 0.5rem; }
            .content { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .table { width: 100%; border-collapse: collapse; }
            .table th, .table td { padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
            .table th { background: #f7fafc; font-weight: 600; }
            .table tr:hover { background: #f7fafc; }
            .tag { background: #e2e8f0; color: #4a5568; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.25rem; }
            .tag.request { background: #c6f6d5; color: #22543d; }
            .tag.query { background: #bee3f8; color: #2a4365; }
            .tag.exception { background: #fed7d7; color: #742a2a; }
            .tag.job { background: #fef5e7; color: #744210; }
            .badge { padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
            .badge.success { background: #c6f6d5; color: #22543d; }
            .badge.error { background: #fed7d7; color: #742a2a; }
            .filter { margin-bottom: 1rem; }
            .filter select, .filter input { padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px; margin-right: 0.5rem; }
            .btn { background: #667eea; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; }
            .btn:hover { background: #5a6fd8; }
            .btn.danger { background: #e53e3e; }
            .btn.danger:hover { background: #c53030; }
        </style>
    </head>
    <body>
        <div id="app">
            <div class="header">
                <h1>🔭 Laravel Telescope</h1>
                <p>Application debugging and monitoring dashboard</p>
            </div>
            
            <div class="nav">
                <div class="nav-item" :class="{active: activeTab === 'requests'}" @click="activeTab = 'requests'">Requests</div>
                <div class="nav-item" :class="{active: activeTab === 'queries'}" @click="activeTab = 'queries'">Queries</div>
                <div class="nav-item" :class="{active: activeTab === 'exceptions'}" @click="activeTab = 'exceptions'">Exceptions</div>
                <div class="nav-item" :class="{active: activeTab === 'jobs'}" @click="activeTab = 'jobs'">Jobs</div>
                <div class="nav-item" :class="{active: activeTab === 'cache'}" @click="activeTab = 'cache'">Cache</div>
                <div class="nav-item" :class="{active: activeTab === 'redis'}" @click="activeTab = 'redis'">Redis</div>
                <div class="nav-item" :class="{active: activeTab === 'mail'}" @click="activeTab = 'mail'">Mail</div>
                <div class="nav-item" :class="{active: activeTab === 'notifications'}" @click="activeTab = 'notifications'">Notifications</div>
            </div>
            
            <div class="main">
                <!-- Statistics -->
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.total_entries || 0 }}</div>
                        <div class="stat-label">Total Entries</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ Object.keys(stats.entries_by_type || {}).length }}</div>
                        <div class="stat-label">Entry Types</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.retention_hours || 24 }}h</div>
                        <div class="stat-label">Retention</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" :class="stats.recording ? 'text-green-600' : 'text-red-600'">
                            {{ stats.recording ? 'ON' : 'OFF' }}
                        </div>
                        <div class="stat-label">Recording</div>
                    </div>
                </div>
                
                <!-- Controls -->
                <div class="filter">
                    <button class="btn" @click="toggleRecording">
                        {{ stats.recording ? 'Pause Recording' : 'Start Recording' }}
                    </button>
                    <button class="btn danger" @click="clearEntries">Clear Entries</button>
                    <button class="btn" @click="loadEntries">Refresh</button>
                </div>
                
                <!-- Entries Table -->
                <div class="content">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Content</th>
                                <th>Tags</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="entry in entries" :key="entry.uuid">
                                <td>
                                    <span class="tag" :class="entry.type">{{ entry.type }}</span>
                                </td>
                                <td>
                                    <div v-if="entry.type === 'request'">
                                        <strong>{{ entry.content.method }}</strong> {{ entry.content.uri }}
                                        <div>
                                            <span class="badge" :class="entry.content.response_status < 400 ? 'success' : 'error'">
                                                {{ entry.content.response_status }}
                                            </span>
                                            {{ entry.content.duration }}ms
                                        </div>
                                    </div>
                                    <div v-else-if="entry.type === 'query'">
                                        <code>{{ entry.content.sql }}</code>
                                        <div>{{ entry.content.time }}ms</div>
                                    </div>
                                    <div v-else-if="entry.type === 'exception'">
                                        <strong>{{ entry.content.class }}</strong>
                                        <div>{{ entry.content.message }}</div>
                                    </div>
                                    <div v-else-if="entry.type === 'job'">
                                        <strong>{{ entry.content.name }}</strong>
                                        <div>Queue: {{ entry.content.queue }} - {{ entry.content.status }}</div>
                                    </div>
                                    <div v-else>
                                        {{ JSON.stringify(entry.content) }}
                                    </div>
                                </td>
                                <td>
                                    <span v-for="tag in entry.tags" :key="tag" class="tag">{{ tag }}</span>
                                </td>
                                <td>{{ formatTime(entry.created_at) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <script>
            const { createApp } = Vue;
            
            createApp({
                data() {
                    return {
                        activeTab: 'requests',
                        entries: [],
                        stats: {},
                    }
                },
                mounted() {
                    this.loadStats();
                    this.loadEntries();
                    setInterval(this.loadEntries, 10000); // Refresh every 10 seconds
                },
                methods: {
                    async loadStats() {
                        try {
                            const response = await fetch('/telescope/api/stats');
                            this.stats = await response.json();
                        } catch (error) {
                            console.error('Failed to load stats:', error);
                        }
                    },
                    async loadEntries() {
                        try {
                            const type = this.activeTab === 'requests' ? 'request' : this.activeTab.slice(0, -1);
                            const response = await fetch(`/telescope/api/entries?type=${type}`);
                            this.entries = await response.json();
                        } catch (error) {
                            console.error('Failed to load entries:', error);
                        }
                    },
                    async toggleRecording() {
                        try {
                            const action = this.stats.recording ? 'pause' : 'resume';
                            await fetch(`/telescope/api/${action}`, { method: 'POST' });
                            this.loadStats();
                        } catch (error) {
                            console.error('Failed to toggle recording:', error);
                        }
                    },
                    async clearEntries() {
                        if (confirm('Are you sure you want to clear all entries?')) {
                            try {
                                await fetch('/telescope/api/clear', { method: 'DELETE' });
                                this.loadEntries();
                                this.loadStats();
                            } catch (error) {
                                console.error('Failed to clear entries:', error);
                            }
                        }
                    },
                    formatTime(timestamp) {
                        return new Date(timestamp).toLocaleString();
                    }
                },
                watch: {
                    activeTab() {
                        this.loadEntries();
                    }
                }
            }).mount('#app');
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=dashboard_html)


@router.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get Telescope statistics."""
    return await Telescope.get_statistics()


@router.get("/api/entries")
async def get_entries(
    type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get telescope entries with filtering."""
    return await Telescope.get_entries(type, tag, limit, offset)


@router.get("/api/entries/{entry_uuid}")
async def get_entry(entry_uuid: str) -> Dict[str, Any]:
    """Get a specific entry by UUID."""
    entry = await Telescope.get_entry(entry_uuid)
    if not entry:
        return JSONResponse(
            content={"error": f"Entry {entry_uuid} not found"},
            status_code=404
        )
    return entry


@router.post("/api/pause")
async def pause_recording() -> Dict[str, str]:
    """Pause Telescope recording."""
    Telescope.pause()
    return {"message": "Telescope recording paused"}


@router.post("/api/resume")
async def resume_recording() -> Dict[str, str]:
    """Resume Telescope recording."""
    Telescope.resume()
    return {"message": "Telescope recording resumed"}


@router.delete("/api/clear")
async def clear_entries(before: Optional[str] = Query(None)) -> Dict[str, str]:
    """Clear telescope entries."""
    count = await Telescope.clear_entries(before)
    return {"message": f"Cleared {count} entries"}


@router.get("/api/watchers")
async def get_watchers() -> Dict[str, Any]:
    """Get list of available watchers and their status."""
    stats = await Telescope.get_statistics()
    return {
        "watchers": stats.get("watchers", []),
        "recording": stats.get("recording", False),
        "enabled": stats.get("enabled", False)
    }


@router.post("/api/watchers/{watcher_name}/enable")
async def enable_watcher(watcher_name: str) -> Dict[str, str]:
    """Enable a specific watcher."""
    Telescope.enable_watcher(watcher_name)
    return {"message": f"Watcher {watcher_name} enabled"}


@router.post("/api/watchers/{watcher_name}/disable") 
async def disable_watcher(watcher_name: str) -> Dict[str, str]:
    """Disable a specific watcher."""
    Telescope.disable_watcher(watcher_name)
    return {"message": f"Watcher {watcher_name} disabled"}