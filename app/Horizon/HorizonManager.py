from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import redis.asyncio as redis  # type: ignore[import-untyped]
from dataclasses import dataclass, asdict

from app.Queue.QueueManager import QueueManager
from .Metrics import HorizonMetrics
from .Monitoring import JobMonitor, QueueMonitor


@dataclass
class SupervisorConfig:
    """Configuration for queue supervisors."""
    name: str
    connection: str = 'redis'
    queue: Optional[List[str]] = None
    processes: int = 1
    timeout: int = 60
    memory: int = 128
    tries: int = 3
    nice: int = 0
    balance: str = 'auto'
    min_processes: int = 1
    max_processes: int = 10
    balance_cooldown: int = 3
    balance_max_shift: int = 1
    rest: int = 0
    max_time: int = 0
    max_jobs: int = 1000
    
    def __post_init__(self):
        if self.queue is None:
            self.queue = ['default']


@dataclass
class WorkerProcess:
    """Represents a running worker process."""
    id: str
    supervisor: str
    queue: List[str]
    status: str  # 'starting', 'running', 'paused', 'stopping'
    started_at: datetime
    pid: Optional[int] = None
    memory_usage: int = 0
    jobs_processed: int = 0
    current_job: Optional[str] = None
    last_activity: Optional[datetime] = None


class HorizonManager:
    """
    Laravel Horizon-style queue management and monitoring system.
    
    Provides comprehensive queue monitoring, metrics collection,
    and worker process management for Redis-based queues.
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0') -> None:
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.queue_manager = QueueManager()
        self.metrics = HorizonMetrics(redis_url)
        self.job_monitor = JobMonitor(redis_url)
        self.queue_monitor = QueueMonitor(redis_url)
        
        # Supervisor configuration
        self.supervisors: Dict[str, SupervisorConfig] = {}
        self.workers: Dict[str, WorkerProcess] = {}
        
        # Horizon state
        self.is_running = False
        self.master_supervisors: Set[str] = set()
        
        # Default configuration
        self._setup_default_supervisors()
    
    async def initialize(self) -> None:
        """Initialize Redis connection and Horizon components."""
        self.redis = redis.from_url(self.redis_url)
        await self.metrics.initialize()
        await self.job_monitor.initialize()
        await self.queue_monitor.initialize()
    
    def _setup_default_supervisors(self) -> None:
        """Setup default supervisor configurations."""
        self.supervisors = {
            'default': SupervisorConfig(
                name='default',
                queue=['default'],
                processes=3,
                timeout=60,
                tries=3
            ),
            'emails': SupervisorConfig(
                name='emails',
                queue=['emails'],
                processes=2,
                timeout=30,
                tries=2
            ),
            'notifications': SupervisorConfig(
                name='notifications', 
                queue=['notifications'],
                processes=2,
                timeout=30,
                tries=3
            ),
        }
    
    async def start(self) -> None:
        """Start Horizon queue monitoring and workers."""
        if self.is_running:
            return
        
        await self.initialize()
        self.is_running = True
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_queues()),
            asyncio.create_task(self._monitor_jobs()),
            asyncio.create_task(self._collect_metrics()),
            asyncio.create_task(self._manage_workers()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop Horizon and all worker processes."""
        self.is_running = False
        
        # Stop all workers
        for worker_id in list(self.workers.keys()):
            await self._stop_worker(worker_id)
        
        # Close Redis connection
        if self.redis:
            await self.redis.close()
    
    async def pause(self, supervisor: Optional[str] = None) -> None:
        """Pause all workers or specific supervisor."""
        if supervisor:
            await self._pause_supervisor(supervisor)
        else:
            for supervisor_name in self.supervisors:
                await self._pause_supervisor(supervisor_name)
    
    async def continue_processing(self, supervisor: Optional[str] = None) -> None:
        """Continue processing after pause.""" 
        if supervisor:
            await self._continue_supervisor(supervisor)
        else:
            for supervisor_name in self.supervisors:
                await self._continue_supervisor(supervisor_name)
    
    async def _monitor_queues(self) -> None:
        """Monitor queue metrics and statistics."""
        while self.is_running:
            try:
                await self.queue_monitor.collect_queue_metrics()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"Queue monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_jobs(self) -> None:
        """Monitor individual job processing."""
        while self.is_running:
            try:
                await self.job_monitor.monitor_active_jobs()
                await asyncio.sleep(5)  # Check every 5 seconds  
            except Exception as e:
                print(f"Job monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self) -> None:
        """Collect and store system metrics."""
        while self.is_running:
            try:
                await self.metrics.collect_system_metrics()
                await self.metrics.collect_throughput_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                print(f"Metrics collection error: {e}")
                await asyncio.sleep(10)
    
    async def _manage_workers(self) -> None:
        """Manage worker processes based on load."""
        while self.is_running:
            try:
                for supervisor_name, config in self.supervisors.items():
                    await self._balance_workers(supervisor_name, config)
                await asyncio.sleep(30)  # Balance every 30 seconds
            except Exception as e:
                print(f"Worker management error: {e}")
                await asyncio.sleep(10)
    
    async def _balance_workers(self, supervisor_name: str, config: SupervisorConfig) -> None:
        """Balance worker processes based on queue load."""
        if config.balance == 'off':
            return
        
        # Get current workers for this supervisor
        supervisor_workers = [
            w for w in self.workers.values() 
            if w.supervisor == supervisor_name
        ]
        
        current_count = len(supervisor_workers)
        
        # Get queue metrics for balancing decision
        queue_metrics = await self.queue_monitor.get_queue_metrics(config.queue)
        pending_jobs = sum(q.get('pending_jobs', 0) for q in queue_metrics.values())
        
        # Determine target worker count
        if config.balance == 'auto':
            target_count = self._calculate_target_workers(
                pending_jobs, current_count, config
            )
        else:
            target_count = config.processes
        
        # Adjust workers
        if target_count > current_count and current_count < config.max_processes:
            # Add workers
            for _ in range(min(target_count - current_count, config.max_processes - current_count)):
                await self._start_worker(supervisor_name, config)
        elif target_count < current_count and current_count > config.min_processes:
            # Remove workers
            for _ in range(min(current_count - target_count, current_count - config.min_processes)):
                await self._stop_oldest_worker(supervisor_name)
    
    def _calculate_target_workers(self, pending_jobs: int, current_workers: int, config: SupervisorConfig) -> int:
        """Calculate target worker count based on pending jobs."""
        if pending_jobs == 0:
            return max(config.min_processes, 1)
        
        # Estimate workers needed (assuming 1 job per worker per minute)
        jobs_per_worker_per_minute = 1
        estimated_workers = min(
            max(config.min_processes, pending_jobs // jobs_per_worker_per_minute),
            config.max_processes
        )
        
        # Apply balance constraints
        max_shift = config.balance_max_shift
        if estimated_workers > current_workers + max_shift:
            return current_workers + max_shift
        elif estimated_workers < current_workers - max_shift:
            return max(current_workers - max_shift, config.min_processes)
        
        return estimated_workers
    
    async def _start_worker(self, supervisor_name: str, config: SupervisorConfig) -> str:
        """Start a new worker process."""
        worker_id = f"{supervisor_name}_{len(self.workers)}_{int(time.time())}"
        
        worker = WorkerProcess(
            id=worker_id,
            supervisor=supervisor_name,
            queue=config.queue,
            status='starting',
            started_at=datetime.utcnow()
        )
        
        self.workers[worker_id] = worker
        
        # In a real implementation, this would spawn an actual process
        # For now, we'll simulate the worker state
        worker.status = 'running'
        worker.pid = hash(worker_id) % 10000  # Simulated PID
        
        return worker_id
    
    async def _stop_worker(self, worker_id: str) -> None:
        """Stop a specific worker process."""
        if worker_id in self.workers:
            worker = self.workers[worker_id]
            worker.status = 'stopping'
            
            # In a real implementation, this would terminate the process
            # For now, we'll just remove from tracking
            del self.workers[worker_id]
    
    async def _stop_oldest_worker(self, supervisor_name: str) -> None:
        """Stop the oldest worker in a supervisor."""
        supervisor_workers = [
            (worker_id, worker) for worker_id, worker in self.workers.items()
            if worker.supervisor == supervisor_name
        ]
        
        if supervisor_workers:
            # Find oldest worker
            oldest_worker_id, _ = min(
                supervisor_workers, 
                key=lambda x: x[1].started_at
            )
            await self._stop_worker(oldest_worker_id)
    
    async def _pause_supervisor(self, supervisor_name: str) -> None:
        """Pause all workers in a supervisor."""
        for worker in self.workers.values():
            if worker.supervisor == supervisor_name:
                worker.status = 'paused'
    
    async def _continue_supervisor(self, supervisor_name: str) -> None:
        """Continue all paused workers in a supervisor."""
        for worker in self.workers.values():
            if worker.supervisor == supervisor_name and worker.status == 'paused':
                worker.status = 'running'
    
    # Dashboard data methods
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        return {
            'overview': await self._get_overview_stats(),
            'supervisors': await self._get_supervisor_stats(),
            'queues': await self._get_queue_stats(),
            'workers': await self._get_worker_stats(),
            'jobs': await self._get_job_stats(),
            'metrics': await self._get_metrics_summary(),
        }
    
    async def _get_overview_stats(self) -> Dict[str, Any]:
        """Get high-level overview statistics."""
        total_workers = len(self.workers)
        active_workers = len([w for w in self.workers.values() if w.status == 'running'])
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'total_supervisors': len(self.supervisors),
            'total_workers': total_workers,
            'active_workers': active_workers,
            'paused_workers': total_workers - active_workers,
            'total_jobs_processed': sum(w.jobs_processed for w in self.workers.values()),
        }
    
    async def _get_supervisor_stats(self) -> List[Dict[str, Any]]:
        """Get supervisor-specific statistics."""
        stats = []
        
        for name, config in self.supervisors.items():
            supervisor_workers = [w for w in self.workers.values() if w.supervisor == name]
            
            stats.append({
                'name': name,
                'status': 'running' if any(w.status == 'running' for w in supervisor_workers) else 'stopped',
                'processes': len(supervisor_workers),
                'queues': config.queue,
                'config': asdict(config)
            })
        
        return stats
    
    async def _get_queue_stats(self) -> Dict[str, Any]:
        """Get queue-specific statistics."""
        return await self.queue_monitor.get_all_queue_metrics()
    
    async def _get_worker_stats(self) -> List[Dict[str, Any]]:
        """Get worker-specific statistics."""
        return [
            {
                'id': worker_id,
                'supervisor': worker.supervisor,
                'status': worker.status,
                'queues': worker.queue,
                'started_at': worker.started_at.isoformat(),
                'pid': worker.pid,
                'jobs_processed': worker.jobs_processed,
                'current_job': worker.current_job,
                'memory_usage': worker.memory_usage,
            }
            for worker_id, worker in self.workers.items()
        ]
    
    async def _get_job_stats(self) -> Dict[str, Any]:
        """Get job processing statistics."""
        return await self.job_monitor.get_job_statistics()
    
    async def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary for dashboard."""
        return await self.metrics.get_metrics_summary()