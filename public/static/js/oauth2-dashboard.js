// OAuth2 Analytics Dashboard JavaScript

class OAuth2Dashboard {
    constructor() {
        this.currentSection = 'overview';
        this.charts = {};
        this.realTimeEnabled = true;
        this.refreshInterval = null;
        this.realTimeInterval = null;
        this.darkMode = localStorage.getItem('darkMode') === 'true';
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDarkMode();
        this.loadDashboardData();
        this.startAutoRefresh();
        this.startRealTime();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('href').substring(1);
                this.showSection(section);
            });
        });

        // Time range selector
        document.getElementById('time-range').addEventListener('change', (e) => {
            this.loadDashboardData(parseInt(e.target.value));
        });

        // Dark mode toggle
        document.getElementById('dark-mode-toggle').addEventListener('click', () => {
            this.toggleDarkMode();
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadDashboardData();
        });

        // Export menu
        const exportMenu = document.getElementById('export-menu');
        exportMenu.addEventListener('click', (e) => {
            e.preventDefault();
            const dropdown = exportMenu.querySelector('div');
            dropdown.classList.toggle('hidden');
        });

        // Export buttons
        document.getElementById('export-csv').addEventListener('click', (e) => {
            e.preventDefault();
            this.exportData('csv');
        });

        document.getElementById('export-json').addEventListener('click', (e) => {
            e.preventDefault();
            this.exportData('json');
        });

        // Sidebar toggle
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            this.toggleSidebar();
        });

        // Real-time controls
        document.getElementById('pause-real-time').addEventListener('click', (e) => {
            this.toggleRealTime();
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#export-menu')) {
                document.querySelector('#export-menu div').classList.add('hidden');
            }
        });
    }

    setupDarkMode() {
        if (this.darkMode) {
            document.documentElement.classList.add('dark');
        }
    }

    toggleDarkMode() {
        this.darkMode = !this.darkMode;
        localStorage.setItem('darkMode', this.darkMode);
        document.documentElement.classList.toggle('dark');
        
        // Update charts for dark mode
        this.updateChartsTheme();
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('sidebar-active');
        sidebar.classList.toggle('sidebar-inactive');
    }

    showSection(section) {
        // Hide all sections
        document.querySelectorAll('section').forEach(s => s.classList.add('hidden'));
        
        // Show selected section
        const targetSection = document.getElementById(`${section}-section`);
        if (targetSection) {
            targetSection.classList.remove('hidden');
        }
        
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active', 'bg-blue-100', 'text-blue-700');
            link.classList.add('text-gray-600', 'hover:text-gray-900');
        });
        
        const activeLink = document.querySelector(`[href="#${section}"]`);
        if (activeLink) {
            activeLink.classList.add('active', 'bg-blue-100', 'text-blue-700');
            activeLink.classList.remove('text-gray-600', 'hover:text-gray-900');
        }
        
        this.currentSection = section;
        
        // Load section-specific data
        this.loadSectionData(section);
    }

    async loadDashboardData(days = 30) {
        this.showLoading(true);
        
        try {
            const response = await fetch(`/api/v1/oauth2/analytics/dashboard/data?days=${days}`);
            const data = await response.json();
            
            this.updateMetrics(data);
            this.updateCharts(data);
            this.updateTopClients(data.top_clients || []);
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showError('Failed to load dashboard data');
        } finally {
            this.showLoading(false);
        }
    }

    updateMetrics(data) {
        const totals = data.totals || {};
        
        document.getElementById('total-tokens').textContent = 
            this.formatNumber(totals.tokens_issued || 0);
            
        const successRate = totals.successful_requests && totals.failed_requests
            ? (totals.successful_requests / (totals.successful_requests + totals.failed_requests) * 100)
            : 0;
        document.getElementById('success-rate').textContent = `${successRate.toFixed(1)}%`;
        
        document.getElementById('active-users').textContent = 
            this.formatNumber(totals.unique_users || 0);
            
        const avgResponseTime = data.performance_metrics?.avg_response_time_ms || 0;
        document.getElementById('avg-response-time').textContent = `${avgResponseTime.toFixed(0)}ms`;
    }

    updateCharts(data) {
        this.updateTokenRequestsChart(data.daily_summaries || []);
        this.updateGrantTypesChart(data.totals || {});
    }

    updateTokenRequestsChart(dailySummaries) {
        const ctx = document.getElementById('token-requests-chart').getContext('2d');
        
        if (this.charts.tokenRequests) {
            this.charts.tokenRequests.destroy();
        }
        
        const isDark = document.documentElement.classList.contains('dark');
        const textColor = isDark ? '#e5e7eb' : '#374151';
        const gridColor = isDark ? '#374151' : '#e5e7eb';
        
        this.charts.tokenRequests = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dailySummaries.map(d => new Date(d.date).toLocaleDateString()),
                datasets: [
                    {
                        label: 'Successful Requests',
                        data: dailySummaries.map(d => d.successful_requests || 0),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'Failed Requests',
                        data: dailySummaries.map(d => d.failed_requests || 0),
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    },
                    x: {
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: textColor }
                    }
                }
            }
        });
    }

    updateGrantTypesChart(totals) {
        const ctx = document.getElementById('grant-types-chart').getContext('2d');
        
        if (this.charts.grantTypes) {
            this.charts.grantTypes.destroy();
        }
        
        const isDark = document.documentElement.classList.contains('dark');
        const textColor = isDark ? '#e5e7eb' : '#374151';
        
        const grantData = [
            totals.authorization_code_grants || 0,
            totals.client_credentials_grants || 0,
            totals.password_grants || 0,
            totals.refresh_token_grants || 0
        ];
        
        this.charts.grantTypes = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Authorization Code', 'Client Credentials', 'Password', 'Refresh Token'],
                datasets: [{
                    data: grantData,
                    backgroundColor: [
                        '#3b82f6',
                        '#10b981',
                        '#f59e0b',
                        '#ef4444'
                    ],
                    borderWidth: 2,
                    borderColor: isDark ? '#1f2937' : '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor }
                    }
                }
            }
        });
    }

    updateTopClients(clients) {
        const tbody = document.getElementById('top-clients-table');
        tbody.innerHTML = '';
        
        clients.forEach(client => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';
            
            const successRate = client.total_requests > 0 
                ? (client.successful_requests / client.total_requests * 100).toFixed(1)
                : '0';
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${client.client_name || client.client_id}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">${client.client_id}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    ${this.formatNumber(client.total_requests || 0)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        parseFloat(successRate) >= 95 ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' :
                        parseFloat(successRate) >= 80 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100' :
                        'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                    }">
                        ${successRate}%
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    ${client.last_used ? new Date(client.last_used).toLocaleDateString() : 'Never'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="viewClientDetails('${client.client_id}')" 
                            class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300">
                        View Details
                    </button>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }

    async loadSectionData(section) {
        switch (section) {
            case 'security':
                await this.loadSecurityData();
                break;
            case 'performance':
                await this.loadPerformanceData();
                break;
            case 'real-time':
                this.loadRealTimeData();
                break;
        }
    }

    async loadSecurityData() {
        try {
            const response = await fetch('/api/v1/oauth2/analytics/reports/security');
            const data = await response.json();
            
            const securityEvents = data.security_events || [];
            
            let alerts = 0, rateLimited = 0, invalidClients = 0;
            
            securityEvents.forEach(event => {
                switch (event.event_type) {
                    case 'suspicious_activity':
                        alerts += event.count;
                        break;
                    case 'rate_limited':
                        rateLimited += event.count;
                        break;
                    case 'invalid_client':
                        invalidClients += event.count;
                        break;
                }
            });
            
            document.getElementById('security-alerts').textContent = this.formatNumber(alerts);
            document.getElementById('rate-limited').textContent = this.formatNumber(rateLimited);
            document.getElementById('invalid-clients').textContent = this.formatNumber(invalidClients);
            
        } catch (error) {
            console.error('Failed to load security data:', error);
        }
    }

    async loadRealTimeData() {
        try {
            const response = await fetch('/api/v1/oauth2/analytics/real-time');
            const data = await response.json();
            
            this.updateRealTimeEvents(data.recent_events || []);
            
        } catch (error) {
            console.error('Failed to load real-time data:', error);
        }
    }

    updateRealTimeEvents(events) {
        const container = document.getElementById('real-time-events');
        
        events.forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.className = 'flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg';
            
            const statusColor = event.success ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
            const statusIcon = event.success ? 'fa-check-circle' : 'fa-times-circle';
            
            eventDiv.innerHTML = `
                <div class="flex items-center space-x-3">
                    <i class="fas ${statusIcon} ${statusColor}"></i>
                    <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-white">
                            ${event.event_type.replace(/_/g, ' ').toUpperCase()}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">
                            ${event.client_id || 'Unknown Client'}
                        </div>
                    </div>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                    ${new Date(event.created_at).toLocaleTimeString()}
                </div>
            `;
            
            container.insertBefore(eventDiv, container.firstChild);
            
            // Keep only last 20 events
            while (container.children.length > 20) {
                container.removeChild(container.lastChild);
            }
        });
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            if (this.currentSection === 'overview') {
                this.loadDashboardData();
            }
        }, 60000); // Refresh every minute
    }

    startRealTime() {
        this.realTimeInterval = setInterval(() => {
            if (this.realTimeEnabled && this.currentSection === 'real-time') {
                this.loadRealTimeData();
            }
        }, 5000); // Update every 5 seconds
    }

    toggleRealTime() {
        this.realTimeEnabled = !this.realTimeEnabled;
        const button = document.getElementById('pause-real-time');
        const status = document.getElementById('connection-status');
        
        if (this.realTimeEnabled) {
            button.innerHTML = '<i class="fas fa-pause"></i> Pause';
            status.innerHTML = '<div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div><span class="text-sm text-gray-600 dark:text-gray-400">Connected</span>';
        } else {
            button.innerHTML = '<i class="fas fa-play"></i> Resume';
            status.innerHTML = '<div class="w-2 h-2 bg-gray-500 rounded-full mr-2"></div><span class="text-sm text-gray-600 dark:text-gray-400">Paused</span>';
        }
    }

    async exportData(format) {
        const days = document.getElementById('time-range').value;
        
        try {
            const response = await fetch(`/api/v1/oauth2/analytics/export/${format}?days=${days}`);
            const data = await response.json();
            
            if (format === 'csv') {
                this.downloadFile(data.csv_data, data.filename, 'text/csv');
            } else {
                this.downloadFile(JSON.stringify(data, null, 2), `oauth2_analytics_${days}days.json`, 'application/json');
            }
            
        } catch (error) {
            console.error(`Failed to export ${format}:`, error);
            this.showError(`Failed to export ${format.toUpperCase()}`);
        }
    }

    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    updateChartsTheme() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        
        // Reload current data to recreate charts with new theme
        this.loadDashboardData();
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }

    showError(message) {
        // Simple error notification - could be enhanced with a proper notification system
        alert(message);
    }

    cleanup() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.realTimeInterval) {
            clearInterval(this.realTimeInterval);
        }
        
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
    }
}

// Global functions for button callbacks
function viewClientDetails(clientId) {
    window.location.href = `/admin/oauth2/clients/${clientId}`;
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new OAuth2Dashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.cleanup();
    }
});