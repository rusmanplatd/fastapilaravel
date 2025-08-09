from __future__ import annotations

import asyncio
import json
import signal
import time
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from ..Command import Command
from app.Queue.QueueManager import global_queue_manager


@dataclass
class QueueMetrics:
    """Queue performance metrics."""
    total_jobs: int = 0
    processed_jobs: int = 0
    failed_jobs: int = 0
    retried_jobs: int = 0
    average_processing_time: float = 0.0
    jobs_per_minute: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    uptime: float = 0.0
    failure_rate: float = 0.0
    queue_size: int = 0


@dataclass
class WorkerInfo:
    """Worker process information."""
    pid: int
    queue: str
    connection: str
    started_at: datetime
    status: str  # running, paused, stopping
    metrics: QueueMetrics
    
    
@dataclass
class JobInfo:
    """Job information for monitoring."""
    id: str
    type: str
    queue: str
    status: str  # pending, running, completed, failed, retrying
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


class QueueWorkCommand(Command):
    """Advanced queue worker with real-time monitoring and health checks."""
    
    signature = "queue:work {connection?=default : The connection name} {--queue=default : The queue to process} {--daemon : Run in daemon mode} {--delay=0 : Delay failed jobs} {--memory=128 : Memory limit in MB} {--sleep=3 : Sleep time when no jobs} {--timeout=60 : Job timeout in seconds} {--tries=3 : Number of attempts} {--health-check=60 : Health check interval in seconds} {--memory-leak-threshold=50 : Memory leak threshold in MB} {--max-jobs=1000 : Maximum jobs before restart} {--metrics-interval=30 : Metrics collection interval} {--dashboard : Enable real-time dashboard} {--log-file= : Custom log file path} {--auto-scale : Enable auto-scaling} {--worker-id= : Custom worker identifier}"
    description = "Advanced queue worker with monitoring, auto-scaling, and health checks"
    help = "Process queued jobs with comprehensive monitoring, health checks, and auto-scaling capabilities"
    
    def __init__(self) -> None:
        super().__init__()
        self.should_quit = False
        self.paused = False
        self.worker_id = None
        self.metrics = QueueMetrics()
        self.job_history: List[JobInfo] = []
        self.health_stats: Dict[str, Any] = {
            'jobs_processed': 0,
            'jobs_failed': 0,
            'memory_usage': [],
            'start_time': None,
            'last_health_check': 0,
            'last_metrics_update': 0,
            'processing_times': [],
            'error_log': []
        }
        self.dashboard_thread: Optional[threading.Thread] = None
        self.metrics_thread: Optional[threading.Thread] = None
    
    async def handle(self) -> None:
        """Execute the queue worker."""
        connection = self.argument("connection", "default")
        queue_name = self.option("queue", "default")
        daemon_mode = self.option("daemon", False)
        delay = int(self.option("delay", 0))
        memory_limit = int(self.option("memory", 128))
        sleep_time = int(self.option("sleep", 3))
        timeout = int(self.option("timeout", 60))
        max_tries = int(self.option("tries", 3))
        health_check_interval = int(self.option("health-check", 60))
        memory_leak_threshold = int(self.option("memory-leak-threshold", 50))
        
        # Initialize health stats
        self.health_stats['start_time'] = time.time()
        
        # Set up signal handlers
        self.trap([signal.SIGTERM, signal.SIGINT], self._handle_signal)
        self.trap([signal.SIGUSR2], self._handle_pause_signal)
        
        self.info(f"Queue worker started on '{connection}' connection")
        self.comment(f"Processing queue: {queue_name}")
        self.comment(f"Memory limit: {memory_limit}MB, Sleep: {sleep_time}s, Timeout: {timeout}s")
        self.comment(f"Health monitoring: {health_check_interval}s intervals, Memory leak threshold: {memory_leak_threshold}MB")
        
        try:
            from app.Queue.QueueManager import global_queue_manager
            worker = global_queue_manager.create_worker_for_queue(connection)
            
            jobs_processed = 0
            start_time = time.time()
            
            while not self.should_quit:
                if self.paused:
                    self.warn("Queue worker paused. Send SIGUSR2 to resume.")
                    await asyncio.sleep(sleep_time)
                    continue
                
                # Perform health checks
                current_time = time.time()
                if current_time - self.health_stats['last_health_check'] >= health_check_interval:
                    await self._perform_health_check(memory_limit, memory_leak_threshold)
                    self.health_stats['last_health_check'] = current_time
                
                # Check memory usage
                if self._check_memory_usage(memory_limit):
                    self.warn(f"Memory limit exceeded ({memory_limit}MB). Stopping worker.")
                    break
                
                # Process next job
                job = global_queue_manager.get_driver(connection).pop(queue_name)
                
                if job:
                    self.comment(f"Processing job: {job.get('id', 'unknown')} ({job.get('type', 'unknown')})")
                    
                    try:
                        start_job_time = time.time()
                        # Process the job using the worker
                        worker.work()  # Let worker handle the job
                        # Worker.work() returns None, so we don't use the return value
                        
                        job_time = time.time() - start_job_time
                        jobs_processed += 1
                        self.health_stats['jobs_processed'] += 1
                        
                        self.info(f"✅ Job completed in {job_time:.2f}s (Total: {jobs_processed})")
                        
                    except asyncio.TimeoutError:
                        self.error(f"❌ Job timed out after {timeout}s")
                        
                    except Exception as e:
                        self.error(f"❌ Job failed: {e}")
                        self.health_stats['jobs_failed'] += 1
                        
                        # Retry logic would be handled by the queue manager
                        # For now, just log the error
                        self.warn(f"Job failed: {str(e)}")
                else:
                    # No jobs available
                    if not daemon_mode and jobs_processed == 0:
                        self.info("No jobs to process")
                        break
                    
                    await asyncio.sleep(sleep_time)
                
                # Show stats periodically
                if jobs_processed > 0 and jobs_processed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = jobs_processed / elapsed * 60  # jobs per minute
                    self.comment(f"Stats: {jobs_processed} jobs, {rate:.1f}/min")
            
            self.info(f"Queue worker stopped. Processed {jobs_processed} jobs.")
            
        except ImportError:
            self.error("Queue system not available")
        except Exception as e:
            self.error(f"Queue worker failed: {e}")
    
    async def _setup_monitoring(self, enable_dashboard: bool, metrics_interval: int) -> None:
        """Set up monitoring systems."""
        if enable_dashboard:
            self.dashboard_thread = threading.Thread(target=self._run_dashboard, daemon=True)
            self.dashboard_thread.start()
            self.comment("📊 Dashboard started on http://localhost:8080/queue-dashboard")
        
        if metrics_interval > 0:
            self.metrics_thread = threading.Thread(
                target=self._collect_metrics, 
                args=(metrics_interval,), 
                daemon=True
            )
            self.metrics_thread.start()
            self.comment(f"📈 Metrics collection started (interval: {metrics_interval}s)")
    
    def _run_dashboard(self) -> None:
        """Run simple web dashboard for queue monitoring."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import urllib.parse
            
            class DashboardHandler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    if self.path == '/queue-dashboard':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        
                        html = self._generate_dashboard_html()
                        self.wfile.write(html.encode())
                    elif self.path == '/api/metrics':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        
                        metrics_data = self._get_metrics_json()
                        self.wfile.write(metrics_data.encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def _generate_dashboard_html(self) -> str:
                    return '''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Queue Dashboard</title>
                        <style>
                            body { font-family: Arial, sans-serif; margin: 20px; }
                            .metric { display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ddd; }
                            .status { color: green; }
                            .error { color: red; }
                        </style>
                    </head>
                    <body>
                        <h1>Queue Worker Dashboard</h1>
                        <div id="metrics"></div>
                        <script>
                            function updateMetrics() {
                                fetch('/api/metrics')
                                    .then(response => response.json())
                                    .then(data => {
                                        document.getElementById('metrics').innerHTML = 
                                            '<div class="metric">Jobs Processed: ' + data.processed_jobs + '</div>' +
                                            '<div class="metric">Failed Jobs: ' + data.failed_jobs + '</div>' +
                                            '<div class="metric">Jobs/Min: ' + data.jobs_per_minute.toFixed(1) + '</div>' +
                                            '<div class="metric">Memory: ' + data.memory_usage.toFixed(1) + 'MB</div>' +
                                            '<div class="metric">CPU: ' + data.cpu_usage.toFixed(1) + '%</div>';
                                    });
                            }
                            setInterval(updateMetrics, 5000);
                            updateMetrics();
                        </script>
                    </body>
                    </html>
                    '''
                
                def _get_metrics_json(self) -> str:
                    return json.dumps(asdict(self.server.queue_command.metrics))  # type: ignore[attr-defined]
                
                def log_message(self, format: str, *args: Any) -> None:
                    pass  # Suppress HTTP request logs
            
            server = HTTPServer(('localhost', 8080), DashboardHandler)
            server.queue_command = self  # type: ignore[attr-defined]
            server.serve_forever()
            
        except Exception as e:
            self.warn(f"Dashboard failed to start: {e}")
    
    def _collect_metrics(self, interval: int) -> None:
        """Background metrics collection."""
        while not self.should_quit:
            try:
                self._update_metrics()
                time.sleep(interval)
            except Exception as e:
                self.warn(f"Metrics collection error: {e}")
                time.sleep(interval)
    
    def _update_metrics(self) -> None:
        """Update performance metrics."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # Update basic metrics
            self.metrics.memory_usage = process.memory_info().rss / 1024 / 1024
            self.metrics.cpu_usage = getattr(process, 'cpu_percent', lambda: 0.0)()
            self.metrics.uptime = time.time() - self.health_stats['start_time']
            
            # Calculate rates
            if self.health_stats['processing_times']:
                self.metrics.average_processing_time = sum(self.health_stats['processing_times']) / len(self.health_stats['processing_times'])
            
            if self.metrics.uptime > 0:
                self.metrics.jobs_per_minute = (self.metrics.processed_jobs / self.metrics.uptime) * 60
            
            # Calculate failure rate
            total_attempts = self.metrics.processed_jobs + self.metrics.failed_jobs
            if total_attempts > 0:
                self.metrics.failure_rate = (self.metrics.failed_jobs / total_attempts) * 100
            
            # Save metrics to file for persistence
            self._save_metrics_to_file()
            
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            self.warn(f"Failed to update metrics: {e}")
    
    def _save_metrics_to_file(self) -> None:
        """Save metrics to file for monitoring."""
        try:
            metrics_dir = Path("storage/logs/queue")
            metrics_dir.mkdir(parents=True, exist_ok=True)
            
            metrics_file = metrics_dir / f"worker-{self.worker_id}-metrics.json"
            
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'worker_id': self.worker_id,
                'metrics': asdict(self.metrics),
                'health_stats': {k: v for k, v in self.health_stats.items() if k not in ['memory_usage', 'processing_times']},
                'recent_jobs': [asdict(job) for job in self.job_history[-10:]]  # Last 10 jobs
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
                
        except Exception as e:
            self.warn(f"Failed to save metrics: {e}")
    
    def _handle_signal(self, sig_num: int) -> None:
        """Handle shutdown signals."""
        signal_name = signal.Signals(sig_num).name
        self.warn(f"Received {signal_name}. Shutting down gracefully...")
        self.should_quit = True
    
    def _handle_pause_signal(self, sig_num: int) -> None:
        """Handle pause/resume signal."""
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        self.info(f"Queue worker {status}")
    
    def _check_memory_usage(self, limit_mb: int) -> bool:
        """Check if memory usage exceeds limit."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb: float = process.memory_info().rss / 1024 / 1024
            
            # Track memory usage for leak detection
            self.health_stats['memory_usage'].append({
                'time': time.time(),
                'memory_mb': memory_mb
            })
            
            # Keep only last 100 measurements
            if len(self.health_stats['memory_usage']) > 100:
                self.health_stats['memory_usage'] = self.health_stats['memory_usage'][-100:]
            
            return memory_mb > limit_mb
        except ImportError:
            return False
    
    async def _perform_health_check(self, memory_limit: int, memory_leak_threshold: int) -> None:
        """Perform comprehensive health check."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            current_memory = process.memory_info().rss / 1024 / 1024
            cpu_percent = getattr(process, 'cpu_percent', lambda: 0.0)()
            
            # Memory leak detection
            if self._detect_memory_leak(memory_leak_threshold):
                self.warn("🚨 Memory leak detected! Memory usage is increasing consistently.")
                self.comment(f"Current memory usage: {current_memory:.1f}MB")
                
                # Consider auto-restart if memory usage is dangerous
                if current_memory > memory_limit * 0.9:
                    self.error("Memory usage approaching limit. Worker will restart after current job.")
                    self.should_quit = True
            
            # Performance monitoring
            jobs_per_minute = self._calculate_job_rate()
            uptime = time.time() - self.health_stats['start_time']
            failure_rate = self._calculate_failure_rate()
            
            # Log health status
            if self.is_verbose():
                self.comment("📊 Health Check:")
                self.comment(f"  Memory: {current_memory:.1f}MB / {memory_limit}MB")
                self.comment(f"  CPU: {cpu_percent:.1f}%")
                self.comment(f"  Jobs/min: {jobs_per_minute:.1f}")
                self.comment(f"  Failure rate: {failure_rate:.1f}%")
                self.comment(f"  Uptime: {int(uptime)}s")
            
            # Alert on high failure rate
            if failure_rate > 25:
                self.warn(f"⚠️  High job failure rate: {failure_rate:.1f}%")
            
            # Alert on high CPU usage
            if cpu_percent > 80:
                self.warn(f"⚠️  High CPU usage: {cpu_percent:.1f}%")
                
        except ImportError:
            self.warn("psutil not available. Health monitoring limited.")
        except Exception as e:
            self.warn(f"Health check failed: {e}")
    
    def _detect_memory_leak(self, threshold_mb: int) -> bool:
        """Detect potential memory leaks."""
        memory_history = self.health_stats['memory_usage']
        
        if len(memory_history) < 10:
            return False
        
        # Check if memory usage has been consistently increasing
        recent_memories = [m['memory_mb'] for m in memory_history[-10:]]
        oldest_memory = recent_memories[0]
        newest_memory = recent_memories[-1]
        
        # Memory leak if consistent increase over threshold
        memory_increase: float = newest_memory - oldest_memory
        return memory_increase > threshold_mb
    
    def _calculate_job_rate(self) -> float:
        """Calculate jobs per minute."""
        uptime = time.time() - self.health_stats['start_time']
        if uptime < 60:
            return 0.0
        
        return float(self.health_stats['jobs_processed'] / uptime) * 60
    
    def _calculate_failure_rate(self) -> float:
        """Calculate job failure rate percentage."""
        total_jobs = self.health_stats['jobs_processed'] + self.health_stats['jobs_failed']
        if total_jobs == 0:
            return 0.0
        
        return float(self.health_stats['jobs_failed'] / total_jobs) * 100


class QueueListenCommand(Command):
    """Listen to a queue and restart workers when needed."""
    
    signature = "queue:listen {connection?=default : The connection name} {--queue=default : The queue to listen to} {--delay=0 : Delay failed jobs} {--memory=128 : Memory limit in MB} {--sleep=3 : Sleep time when no jobs} {--timeout=60 : Job timeout}"
    description = "Listen to a queue and restart workers"
    help = "Start a queue listener that restarts workers when they die"
    
    async def handle(self) -> None:
        """Execute the queue listener."""
        connection = self.argument("connection", "default")
        queue_name = self.option("queue", "default")
        
        self.info(f"Queue listener started for '{connection}' connection")
        self.comment(f"Listening to queue: {queue_name}")
        
        restart_count = 0
        
        while True:
            try:
                self.comment(f"Starting queue worker... (Restart #{restart_count})")
                
                # Start worker process
                options = {
                    "connection": connection,
                    "--queue": queue_name,
                    "--delay": self.option("delay", 0),
                    "--memory": self.option("memory", 128),
                    "--sleep": self.option("sleep", 3),
                    "--timeout": self.option("timeout", 60),
                    "--daemon": True,
                }
                
                await self.call("queue:work", options)
                
                # If we get here, worker exited
                restart_count += 1
                self.warn(f"Queue worker exited. Restarting in 5 seconds...")
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                self.info("Queue listener stopped by user")
                break
            except Exception as e:
                self.error(f"Queue listener error: {e}")
                await asyncio.sleep(5)


class QueueStatsCommand(Command):
    """Display queue statistics."""
    
    signature = "queue:stats {connection?=default : The connection name} {--refresh=5 : Auto-refresh interval in seconds}"
    description = "Display queue statistics"
    help = "Show detailed statistics about queues and jobs"
    
    async def handle(self) -> None:
        """Execute the queue stats command."""
        connection = self.argument("connection", "default")
        refresh_interval = int(self.option("refresh", 5))
        
        try:
            from app.Queue.QueueManager import global_queue_manager
            
            if refresh_interval > 0:
                # Auto-refresh mode
                self.info(f"Queue statistics (refreshing every {refresh_interval}s)")
                self.comment("Press Ctrl+C to stop")
                
                while True:
                    try:
                        await self._show_stats(global_queue_manager, connection)
                        await asyncio.sleep(refresh_interval)
                        
                        # Clear screen for next update
                        print("\033[2J\033[H", end="")
                        
                    except KeyboardInterrupt:
                        self.new_line()
                        self.info("Statistics monitoring stopped")
                        break
            else:
                # One-time display
                await self._show_stats(global_queue_manager, connection)
        
        except ImportError:
            self.error("Queue system not available")
        except Exception as e:
            self.error(f"Failed to get queue statistics: {e}")
    
    async def _show_stats(self, queue_manager: Any, connection: str) -> None:
        """Show queue statistics."""
        self.info(f"Queue Statistics - Connection: {connection}")
        self.line("=" * 60)
        
        # Get queue info
        queues = await global_queue_manager.get_queues(connection)
        
        if not queues:
            self.warn("No queues found")
            return
        
        # Queue overview
        queue_data = []
        total_pending = 0
        total_failed = 0
        
        for queue_name in queues:
            pending = global_queue_manager.get_driver(connection).size(queue_name)
            failed = await global_queue_manager.failed_count(queue_name, connection)
            
            total_pending += pending
            total_failed += failed
            
            queue_data.append([
                queue_name,
                str(pending),
                str(failed),
                "Active" if pending > 0 else "Idle"
            ])
        
        self.comment("Queue Overview:")
        self.table(["Queue", "Pending", "Failed", "Status"], queue_data)
        
        # Summary stats
        self.new_line()
        summary_data = [
            ["Total Queues", str(len(queues))],
            ["Total Pending Jobs", str(total_pending)],
            ["Total Failed Jobs", str(total_failed)],
            ["Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]
        
        self.table(["Metric", "Value"], summary_data)
        
        # Recent jobs (if available)
        try:
            recent_jobs = await global_queue_manager.recent_jobs(connection, limit=5)
            if recent_jobs:
                self.new_line()
                self.comment("Recent Jobs:")
                
                job_data = []
                for job in recent_jobs:
                    job_data.append([
                        job.get('id', 'Unknown')[:20],
                        job.get('queue', 'default'),
                        job.get('status', 'Unknown'),
                        job.get('created_at', 'Unknown'),
                    ])
                
                self.table(["Job ID", "Queue", "Status", "Created"], job_data)
        except Exception:
            pass


class QueueFailedCommand(Command):
    """List or manage failed queue jobs."""
    
    signature = "queue:failed {--id= : Show specific failed job} {--flush : Delete all failed jobs}"
    description = "List all failed queue jobs"
    help = "Display and manage failed queue jobs"
    
    async def handle(self) -> None:
        """Execute the failed jobs command."""
        job_id = self.option("id")
        flush_all = self.option("flush", False)
        
        try:
            from app.Queue.QueueManager import global_queue_manager
            
            if flush_all:
                if self.confirm("Delete all failed jobs?", False):
                    count = await global_queue_manager.flush_failed()
                    self.info(f"✅ Deleted {count} failed jobs")
                else:
                    self.info("Operation cancelled")
                return
            
            if job_id:
                await self._show_failed_job(global_queue_manager, job_id)
            else:
                await self._list_failed_jobs(global_queue_manager)
        
        except ImportError:
            self.error("Queue system not available")
        except Exception as e:
            self.error(f"Failed to get failed jobs: {e}")
    
    async def _show_failed_job(self, queue_manager: Any, job_id: str) -> None:
        """Show details of a specific failed job."""
        job = await global_queue_manager.get_failed_job(job_id)
        
        if not job:
            self.error(f"Failed job with ID '{job_id}' not found")
            return
        
        self.info(f"Failed Job Details: {job_id}")
        self.line("=" * 60)
        
        details = [
            ["Job ID", job.get('id', 'Unknown')],
            ["Queue", job.get('queue', 'Unknown')],
            ["Job Class", job.get('job_class', 'Unknown')],
            ["Failed At", job.get('failed_at', 'Unknown')],
            ["Attempts", str(job.get('attempts', 0))],
            ["Exception", job.get('exception', 'No exception info')],
        ]
        
        self.table(["Property", "Value"], details)
        
        # Show job payload
        if 'payload' in job:
            self.new_line()
            self.comment("Job Payload:")
            self.line(json.dumps(job['payload'], indent=2))
        
        # Show stack trace if available
        if 'stack_trace' in job:
            self.new_line()
            self.comment("Stack Trace:")
            self.line(job['stack_trace'])
    
    async def _list_failed_jobs(self, queue_manager: Any) -> None:
        """List all failed jobs."""
        failed_jobs = await global_queue_manager.get_failed_jobs()
        
        if not failed_jobs:
            self.info("No failed jobs found")
            return
        
        self.info(f"Failed Jobs ({len(failed_jobs)})")
        self.line("=" * 60)
        
        job_data = []
        for job in failed_jobs:
            job_data.append([
                job.get('id', 'Unknown')[:20] + "...",
                job.get('queue', 'default'),
                job.get('job_class', 'Unknown')[:30],
                job.get('failed_at', 'Unknown'),
                str(job.get('attempts', 0)),
            ])
        
        self.table(["Job ID", "Queue", "Job Class", "Failed At", "Attempts"], job_data)
        
        self.new_line()
        self.comment("Use --id=<job_id> to see details of a specific job")
        self.comment("Use --flush to delete all failed jobs")


class QueueRetryCommand(Command):
    """Retry failed queue jobs."""
    
    signature = "queue:retry {id? : Job ID to retry} {--all : Retry all failed jobs} {--queue= : Retry jobs from specific queue}"
    description = "Retry failed queue jobs"
    help = "Retry one or more failed jobs"
    
    async def handle(self) -> None:
        """Execute the retry command."""
        job_id = self.argument("id")
        retry_all = self.option("all", False)
        queue_name = self.option("queue")
        
        try:
            from app.Queue.QueueManager import global_queue_manager
            
            if retry_all:
                await self._retry_all_failed(global_queue_manager, queue_name)
            elif job_id:
                await self._retry_single_job(global_queue_manager, job_id)
            else:
                self.error("Specify a job ID or use --all to retry all failed jobs")
        
        except ImportError:
            self.error("Queue system not available")
        except Exception as e:
            self.error(f"Failed to retry jobs: {e}")
    
    async def _retry_single_job(self, queue_manager: Any, job_id: str) -> None:
        """Retry a single failed job."""
        success = await global_queue_manager.retry_failed(job_id)
        
        if success:
            self.info(f"✅ Job {job_id} has been retried")
        else:
            self.error(f"Failed to retry job {job_id}")
    
    async def _retry_all_failed(self, queue_manager: Any, queue_name: Optional[str]) -> None:
        """Retry all failed jobs."""
        if queue_name:
            if not self.confirm(f"Retry all failed jobs in '{queue_name}' queue?", False):
                self.info("Operation cancelled")
                return
        else:
            if not self.confirm("Retry ALL failed jobs?", False):
                self.info("Operation cancelled")
                return
        
        count = await global_queue_manager.retry_all_failed(queue_name)
        self.info(f"✅ Retried {count} failed jobs")


class QueueClearCommand(Command):
    """Clear all jobs from a queue."""
    
    signature = "queue:clear {queue?=default : Queue name to clear} {connection?=default : Connection name}"
    description = "Clear all jobs from a queue"
    help = "Remove all pending jobs from the specified queue"
    
    async def handle(self) -> None:
        """Execute the clear command."""
        queue_name = self.argument("queue", "default")
        connection = self.argument("connection", "default")
        
        if not self.confirm(f"Clear all jobs from '{queue_name}' queue?", False):
            self.info("Operation cancelled")
            return
        
        try:
            from app.Queue.QueueManager import global_queue_manager
            
            count = await global_queue_manager.clear(queue_name, connection)
            self.info(f"✅ Cleared {count} jobs from '{queue_name}' queue")
        
        except ImportError:
            self.error("Queue system not available")
        except Exception as e:
            self.error(f"Failed to clear queue: {e}")


class QueueRestartCommand(Command):
    """Restart queue workers gracefully."""
    
    signature = "queue:restart"
    description = "Restart all queue workers"
    help = "Send restart signal to all queue workers"
    
    async def handle(self) -> None:
        """Execute the restart command."""
        self.info("Signaling queue workers to restart...")
        
        try:
            # Create restart file
            restart_file = Path("storage/framework/queue.restart")
            restart_file.parent.mkdir(parents=True, exist_ok=True)
            restart_file.write_text(str(time.time()))
            
            self.info("✅ Restart signal sent to queue workers")
            self.comment("Workers will restart after completing current jobs")
        
        except Exception as e:
            self.error(f"Failed to signal restart: {e}")


class QueueMonitorCommand(Command):
    """Monitor queue performance in real-time."""
    
    signature = "queue:monitor {--connection=default : Connection to monitor} {--refresh=2 : Refresh interval}"
    description = "Monitor queue performance in real-time"
    help = "Display real-time queue performance metrics"
    
    async def handle(self) -> None:
        """Execute the monitor command."""
        connection = self.option("connection", "default")
        refresh_interval = int(self.option("refresh", 2))
        
        self.info("Queue Performance Monitor")
        self.comment(f"Connection: {connection}, Refresh: {refresh_interval}s")
        self.comment("Press Ctrl+C to stop")
        
        try:
            from app.Queue.QueueManager import global_queue_manager
            
            while True:
                try:
                    # Clear screen
                    print("\033[2J\033[H", end="")
                    
                    await self._show_performance_metrics(global_queue_manager, connection)
                    await asyncio.sleep(refresh_interval)
                
                except KeyboardInterrupt:
                    self.new_line()
                    self.info("Queue monitoring stopped")
                    break
        
        except ImportError:
            self.error("Queue system not available")
        except Exception as e:
            self.error(f"Queue monitoring failed: {e}")
    
    async def _show_performance_metrics(self, queue_manager: Any, connection: str) -> None:
        """Show real-time performance metrics."""
        now = datetime.now()
        
        self.info(f"Queue Monitor - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        self.line("=" * 80)
        
        # Get real-time metrics
        metrics = await global_queue_manager.get_metrics(connection)
        
        # Jobs per second
        self.comment("Throughput:")
        throughput_data = [
            ["Jobs/second", f"{metrics.get('jobs_per_second', 0):.2f}"],
            ["Jobs/minute", f"{metrics.get('jobs_per_minute', 0):.1f}"],
            ["Peak throughput", f"{metrics.get('peak_throughput', 0):.2f}/s"],
        ]
        self.table(["Metric", "Value"], throughput_data)
        
        # Queue sizes
        self.new_line()
        self.comment("Queue Sizes:")
        queue_sizes = metrics.get('queue_sizes', {})
        
        if queue_sizes:
            size_data = [[name, str(size)] for name, size in queue_sizes.items()]
            self.table(["Queue", "Pending Jobs"], size_data)
        else:
            self.line("No queues found")
        
        # Worker status
        self.new_line()
        self.comment("Workers:")
        worker_data = [
            ["Active Workers", str(metrics.get('active_workers', 0))],
            ["Total Workers", str(metrics.get('total_workers', 0))],
            ["Memory Usage", f"{metrics.get('memory_usage', 0):.1f} MB"],
        ]
        self.table(["Metric", "Value"], worker_data)
        
        # Recent activity
        if 'recent_jobs' in metrics:
            self.new_line()
            self.comment("Recent Activity:")
            recent_data = []
            
            for job in metrics['recent_jobs'][-5:]:  # Last 5 jobs
                recent_data.append([
                    job.get('id', 'Unknown')[:15],
                    job.get('status', 'Unknown'),
                    job.get('duration', '0.0s'),
                    job.get('queue', 'default'),
                ])
            
            self.table(["Job ID", "Status", "Duration", "Queue"], recent_data)


class MakeJobCommand(Command):
    """Generate a new job class."""
    
    signature = "make:job {name : The name of the job class} {--sync : Create a synchronous job}"
    description = "Create a new job class"
    help = "Generate a new queueable job class"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        is_sync = self.option("sync", False)
        
        if not name:
            self.error("Job name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Job"):
            name += "Job"
        
        job_path = Path(f"app/Jobs/{name}.py")
        job_path.parent.mkdir(parents=True, exist_ok=True)
        
        if job_path.exists():
            if not self.confirm(f"Job {name} already exists. Overwrite?"):
                self.info("Job creation cancelled.")
                return
        
        content = self._generate_job_content(name, is_sync)
        job_path.write_text(content)
        
        self.info(f"✅ Job created: {job_path}")
        self.comment("Don't forget to import and dispatch your job where needed")
        self.comment(f"Example: {name}.dispatch(arg1, arg2)")
    
    def _generate_job_content(self, job_name: str, is_sync: bool) -> str:
        """Generate job class content."""
        base_class = "SyncJob" if is_sync else "Job"
        job_type = "synchronous" if is_sync else "asynchronous"
        
        return f'''from __future__ import annotations

from typing import Any
from app.Jobs.{base_class} import {base_class}


class {job_name}({base_class}):
    """
    {job_type.title()} job for processing tasks.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the job with required data."""
        super().__init__()
        
        # Store job data
        # self.user_id = args[0] if args else None
        # self.options = kwargs
        
        # Set job options
        self.queue = "default"  # Queue name
        self.delay = 0  # Delay in seconds
        self.timeout = 60  # Timeout in seconds
        self.max_tries = 3  # Maximum attempts
    
    {"async " if not is_sync else ""}def handle(self) -> None:
        """Execute the job."""
        # Add your job logic here
        
        # Example:
        # self.info(f"Processing job for user {{self.user_id}}")
        
        # Your business logic here
        pass
    
    def failed(self, exception: Exception) -> None:
        """Handle job failure."""
        # Clean up resources, send notifications, etc.
        self.error(f"Job failed: {{exception}}")
    
    def __repr__(self) -> str:
        """String representation of the job."""
        return f"{job_name}()"
'''
# Register commands
from app.Console.Artisan import register_command

register_command(QueueWorkCommand)
register_command(QueueListenCommand)
register_command(QueueStatsCommand)
register_command(QueueFailedCommand)
register_command(QueueRetryCommand)
register_command(QueueClearCommand)
register_command(QueueRestartCommand)
register_command(QueueMonitorCommand)
register_command(MakeJobCommand)
