from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import redis.asyncio as redis
from dataclasses import dataclass, asdict


@dataclass
class JobStatus:
    """Status information for a job."""
    id: str
    queue: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    payload: Dict[str, Any] = None
    exception: Optional[str] = None
    
    def __post_init__(self):
        if self.payload is None:
            self.payload = {}


@dataclass
class QueueStatus:
    """Status information for a queue."""
    name: str
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time: float
    longest_wait_time: float
    throughput_per_minute: float
    last_processed_at: Optional[datetime] = None


class JobMonitor:
    """
    Job monitoring system for tracking individual job lifecycle.
    
    Monitors job status changes, processing times, and failure rates.
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0') -> None:
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        
        # Job tracking keys
        self.ACTIVE_JOBS_KEY = 'horizon:monitoring:active_jobs'
        self.JOB_HISTORY_KEY = 'horizon:monitoring:job_history'
        self.JOB_METRICS_KEY = 'horizon:monitoring:job_metrics'
        self.FAILED_JOBS_KEY = 'horizon:monitoring:failed_jobs'
        
        # Monitoring state
        self.active_jobs: Dict[str, JobStatus] = {}
        self.job_statistics: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize Redis connection and load active jobs."""
        self.redis = redis.from_url(self.redis_url)
        await self._load_active_jobs()
    
    async def start_job(self, job_id: str, queue: str, worker_id: str, payload: Dict[str, Any]) -> None:
        """Record job start."""
        job_status = JobStatus(
            id=job_id,
            queue=queue,
            status='processing',
            started_at=datetime.utcnow(),
            worker_id=worker_id,
            payload=payload
        )
        
        self.active_jobs[job_id] = job_status
        
        # Store in Redis
        await self._store_job_status(job_status)
        await self._update_job_metrics('started', queue)
    
    async def complete_job(self, job_id: str, processing_time: float) -> None:
        """Record job completion."""
        if job_id not in self.active_jobs:
            return
        
        job_status = self.active_jobs[job_id]
        job_status.status = 'completed'
        job_status.completed_at = datetime.utcnow()
        
        # Move to history
        await self._move_to_history(job_status, processing_time)
        await self._update_job_metrics('completed', job_status.queue, processing_time)
        
        # Remove from active jobs
        del self.active_jobs[job_id]
        await self.redis.hdel(self.ACTIVE_JOBS_KEY, job_id)
    
    async def fail_job(self, job_id: str, exception: str, will_retry: bool = False) -> None:
        """Record job failure."""
        if job_id not in self.active_jobs:
            return
        
        job_status = self.active_jobs[job_id]
        job_status.attempts += 1
        job_status.exception = exception
        
        if will_retry and job_status.attempts < job_status.max_attempts:
            # Job will be retried
            job_status.status = 'pending'
            await self._store_job_status(job_status)
            await self._update_job_metrics('retried', job_status.queue)
        else:
            # Job permanently failed
            job_status.status = 'failed'
            job_status.failed_at = datetime.utcnow()
            
            # Move to failed jobs
            await self._store_failed_job(job_status)
            await self._update_job_metrics('failed', job_status.queue)
            
            # Remove from active jobs
            del self.active_jobs[job_id]
            await self.redis.hdel(self.ACTIVE_JOBS_KEY, job_id)
    
    async def monitor_active_jobs(self) -> None:
        """Monitor active jobs for timeouts and issues."""
        now = datetime.utcnow()
        timeout_threshold = timedelta(minutes=30)  # 30 minute timeout
        
        timed_out_jobs = []
        
        for job_id, job_status in self.active_jobs.items():
            if (job_status.started_at and 
                now - job_status.started_at > timeout_threshold):
                timed_out_jobs.append(job_id)
        
        # Handle timed out jobs
        for job_id in timed_out_jobs:
            await self.fail_job(job_id, "Job timed out", will_retry=True)
    
    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get comprehensive job statistics."""
        now = datetime.utcnow()
        
        # Active jobs by status
        active_by_status = {}
        active_by_queue = {}
        
        for job_status in self.active_jobs.values():
            status = job_status.status
            queue = job_status.queue
            
            active_by_status[status] = active_by_status.get(status, 0) + 1
            active_by_queue[queue] = active_by_queue.get(queue, 0) + 1
        
        # Recent metrics
        hourly_metrics = await self._get_recent_metrics(3600)  # Last hour
        daily_metrics = await self._get_recent_metrics(86400)  # Last day
        
        return {
            'active_jobs': {
                'total': len(self.active_jobs),
                'by_status': active_by_status,
                'by_queue': active_by_queue
            },
            'hourly_metrics': hourly_metrics,
            'daily_metrics': daily_metrics,
            'failed_jobs_count': await self.redis.zcard(self.FAILED_JOBS_KEY),
            'timestamp': now.isoformat()
        }
    
    async def get_recent_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently completed/failed jobs."""
        # Get recent job history
        recent_jobs = await self.redis.zrevrange(
            self.JOB_HISTORY_KEY, 0, limit - 1, withscores=True
        )
        
        jobs = []
        for job_data, timestamp in recent_jobs:
            job_info = json.loads(job_data.decode())
            job_info['timestamp'] = datetime.fromtimestamp(timestamp).isoformat()
            jobs.append(job_info)
        
        return jobs
    
    async def get_failed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed jobs."""
        failed_jobs = await self.redis.zrevrange(
            self.FAILED_JOBS_KEY, 0, limit - 1, withscores=True
        )
        
        jobs = []
        for job_data, timestamp in failed_jobs:
            job_info = json.loads(job_data.decode())
            job_info['failed_at'] = datetime.fromtimestamp(timestamp).isoformat()
            jobs.append(job_info)
        
        return jobs
    
    async def retry_failed_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        # This would re-queue the failed job
        # Implementation depends on the queue system
        return False  # Placeholder
    
    # Private helper methods
    
    async def _store_job_status(self, job_status: JobStatus) -> None:
        """Store job status in Redis."""
        job_data = asdict(job_status)
        # Convert datetime objects to ISO strings
        for key, value in job_data.items():
            if isinstance(value, datetime):
                job_data[key] = value.isoformat()
        
        await self.redis.hset(
            self.ACTIVE_JOBS_KEY,
            job_status.id,
            json.dumps(job_data)
        )
    
    async def _move_to_history(self, job_status: JobStatus, processing_time: float) -> None:
        """Move completed job to history."""
        job_data = {
            'id': job_status.id,
            'queue': job_status.queue,
            'status': job_status.status,
            'processing_time': processing_time,
            'worker_id': job_status.worker_id,
            'completed_at': job_status.completed_at.isoformat() if job_status.completed_at else None
        }
        
        timestamp = job_status.completed_at.timestamp() if job_status.completed_at else time.time()
        
        await self.redis.zadd(
            self.JOB_HISTORY_KEY,
            {json.dumps(job_data): timestamp}
        )
    
    async def _store_failed_job(self, job_status: JobStatus) -> None:
        """Store failed job for later analysis."""
        job_data = {
            'id': job_status.id,
            'queue': job_status.queue,
            'status': job_status.status,
            'exception': job_status.exception,
            'attempts': job_status.attempts,
            'worker_id': job_status.worker_id,
            'failed_at': job_status.failed_at.isoformat() if job_status.failed_at else None,
            'payload': job_status.payload
        }
        
        timestamp = job_status.failed_at.timestamp() if job_status.failed_at else time.time()
        
        await self.redis.zadd(
            self.FAILED_JOBS_KEY,
            {json.dumps(job_data): timestamp}
        )
    
    async def _update_job_metrics(self, event: str, queue: str, processing_time: float = None) -> None:
        """Update job metrics counters."""
        now = datetime.utcnow()
        minute_key = f"{self.JOB_METRICS_KEY}:{queue}:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"{self.JOB_METRICS_KEY}:{queue}:hour:{now.strftime('%Y%m%d%H')}"
        day_key = f"{self.JOB_METRICS_KEY}:{queue}:day:{now.strftime('%Y%m%d')}"
        
        # Increment counters
        await self.redis.hincrby(minute_key, event, 1)
        await self.redis.hincrby(hour_key, event, 1)
        await self.redis.hincrby(day_key, event, 1)
        
        # Set expiration
        await self.redis.expire(minute_key, 3600)  # 1 hour
        await self.redis.expire(hour_key, 86400)   # 1 day
        await self.redis.expire(day_key, 604800)   # 1 week
        
        # Store processing time if provided
        if processing_time is not None:
            await self.redis.lpush(f"{minute_key}:times", processing_time)
            await self.redis.ltrim(f"{minute_key}:times", 0, 99)  # Keep last 100
            await self.redis.expire(f"{minute_key}:times", 3600)
    
    async def _get_recent_metrics(self, seconds: int) -> Dict[str, Any]:
        """Get metrics for the recent time period."""
        now = datetime.utcnow()
        metrics = {
            'started': 0,
            'completed': 0,
            'failed': 0,
            'retried': 0,
            'average_processing_time': 0.0
        }
        
        # This would aggregate metrics from the time period
        # For now, return the structure with placeholder data
        
        return metrics
    
    async def _load_active_jobs(self) -> None:
        """Load active jobs from Redis on startup."""
        jobs_data = await self.redis.hgetall(self.ACTIVE_JOBS_KEY)
        
        for job_id, job_data in jobs_data.items():
            job_info = json.loads(job_data.decode())
            
            # Convert ISO strings back to datetime objects
            for key, value in job_info.items():
                if key.endswith('_at') and value:
                    job_info[key] = datetime.fromisoformat(value)
            
            self.active_jobs[job_id.decode()] = JobStatus(**job_info)


class QueueMonitor:
    """
    Queue monitoring system for tracking queue metrics and health.
    
    Monitors queue sizes, throughput, and performance metrics.
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0') -> None:
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        
        # Queue tracking
        self.QUEUE_METRICS_KEY = 'horizon:monitoring:queue_metrics'
        self.monitored_queues: Set[str] = {'default', 'emails', 'notifications'}
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        self.redis = redis.from_url(self.redis_url)
    
    async def collect_queue_metrics(self) -> Dict[str, QueueStatus]:
        """Collect metrics for all monitored queues."""
        queue_statuses = {}
        
        for queue_name in self.monitored_queues:
            status = await self._collect_single_queue_metrics(queue_name)
            queue_statuses[queue_name] = status
            
            # Store metrics
            await self._store_queue_metrics(status)
        
        return queue_statuses
    
    async def get_queue_metrics(self, queue_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current metrics for specific queues."""
        metrics = {}
        
        for queue_name in queue_names:
            if queue_name in self.monitored_queues:
                status = await self._collect_single_queue_metrics(queue_name)
                metrics[queue_name] = asdict(status)
        
        return metrics
    
    async def get_all_queue_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all monitored queues."""
        return await self.get_queue_metrics(list(self.monitored_queues))
    
    async def add_queue_to_monitoring(self, queue_name: str) -> None:
        """Add a queue to monitoring."""
        self.monitored_queues.add(queue_name)
    
    async def remove_queue_from_monitoring(self, queue_name: str) -> None:
        """Remove a queue from monitoring."""
        self.monitored_queues.discard(queue_name)
    
    async def _collect_single_queue_metrics(self, queue_name: str) -> QueueStatus:
        """Collect metrics for a single queue."""
        # Get queue sizes
        pending_jobs = await self.redis.llen(f"queue:{queue_name}")
        processing_jobs = await self.redis.llen(f"queue:{queue_name}:processing")
        
        # Get completed/failed counts from recent metrics
        completed_jobs = await self._get_recent_job_count(queue_name, 'completed', 3600)
        failed_jobs = await self._get_recent_job_count(queue_name, 'failed', 3600)
        
        # Calculate performance metrics
        avg_processing_time = await self._calculate_average_processing_time(queue_name)
        longest_wait_time = await self._calculate_longest_wait_time(queue_name)
        throughput = await self._calculate_throughput(queue_name, 60)  # Jobs per minute
        
        # Get last processed timestamp
        last_processed = await self._get_last_processed_time(queue_name)
        
        return QueueStatus(
            name=queue_name,
            pending_jobs=pending_jobs,
            processing_jobs=processing_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            average_processing_time=avg_processing_time,
            longest_wait_time=longest_wait_time,
            throughput_per_minute=throughput,
            last_processed_at=last_processed
        )
    
    async def _store_queue_metrics(self, status: QueueStatus) -> None:
        """Store queue metrics in Redis."""
        now = datetime.utcnow()
        key = f"{self.QUEUE_METRICS_KEY}:{status.name}:{now.strftime('%Y%m%d%H%M')}"
        
        metrics_data = asdict(status)
        # Convert datetime to ISO string
        if metrics_data.get('last_processed_at'):
            metrics_data['last_processed_at'] = status.last_processed_at.isoformat()
        
        await self.redis.hset(key, mapping=metrics_data)
        await self.redis.expire(key, 86400)  # Expire after 1 day
    
    async def _get_recent_job_count(self, queue_name: str, event: str, seconds: int) -> int:
        """Get count of specific job events in recent time."""
        # This would sum up job counts from metrics
        # For now, return a placeholder
        return 0
    
    async def _calculate_average_processing_time(self, queue_name: str) -> float:
        """Calculate average processing time for the queue."""
        # This would analyze recent processing times
        # For now, return a placeholder
        return 0.0
    
    async def _calculate_longest_wait_time(self, queue_name: str) -> float:
        """Calculate longest wait time in the queue."""
        # This would analyze job wait times
        # For now, return a placeholder
        return 0.0
    
    async def _calculate_throughput(self, queue_name: str, seconds: int) -> float:
        """Calculate jobs processed per time unit."""
        # This would count completed jobs in the time period
        # For now, return a placeholder
        return 0.0
    
    async def _get_last_processed_time(self, queue_name: str) -> Optional[datetime]:
        """Get timestamp of last processed job."""
        # This would query job completion logs
        # For now, return None
        return None