from __future__ import annotations

import asyncio
import json
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, cast
import redis.asyncio as redis
from dataclasses import dataclass, asdict, field


@dataclass
class MetricSnapshot:
    """Single metric data point."""
    timestamp: datetime
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        # tags now initialized with default_factory
        pass


@dataclass
class SystemMetrics:
    """System resource metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_used: int
    disk_usage: float
    load_average: List[float]
    redis_memory: int
    redis_connected_clients: int


@dataclass
class ThroughputMetrics:
    """Job throughput metrics."""
    timestamp: datetime
    jobs_per_minute: int
    jobs_per_hour: int
    average_job_time: float
    peak_throughput: int
    queue_name: str


class HorizonMetrics:
    """
    Metrics collection and storage system for Horizon.
    
    Collects and stores various system and application metrics
    for monitoring and performance analysis.
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0') -> None:
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        
        # Metric storage keys
        self.SYSTEM_METRICS_KEY = 'horizon:metrics:system'
        self.THROUGHPUT_METRICS_KEY = 'horizon:metrics:throughput'
        self.QUEUE_METRICS_KEY = 'horizon:metrics:queues'
        self.JOB_METRICS_KEY = 'horizon:metrics:jobs'
        
        # Retention settings (in seconds)
        self.RETENTION_PERIOD = 7 * 24 * 3600  # 7 days
        self.AGGREGATE_INTERVAL = 60  # 1 minute
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        self.redis = redis.from_url(self.redis_url)
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
        
        # Redis metrics
        if self.redis:
            redis_info = await self.redis.info('memory')
            redis_memory = redis_info.get('used_memory', 0) // (1024 * 1024)  # Convert to MB
            redis_clients = await self.redis.client_list()
        else:
            redis_memory = 0
            redis_clients = []
        
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            memory_total=memory.total,
            memory_used=memory.used,
            disk_usage=disk.percent,
            load_average=load_avg,
            redis_memory=redis_memory,
            redis_connected_clients=len(redis_clients)
        )
        
        # Store metrics
        await self._store_metric(self.SYSTEM_METRICS_KEY, metrics)
        
        return metrics
    
    async def collect_throughput_metrics(self, queue_name: str = 'default') -> ThroughputMetrics:
        """Collect job throughput metrics for a specific queue."""
        now = datetime.utcnow()
        
        # Get job counts for the last hour and minute
        jobs_last_minute = await self._count_jobs_in_timeframe(queue_name, 60)
        jobs_last_hour = await self._count_jobs_in_timeframe(queue_name, 3600)
        
        # Calculate average job processing time
        avg_job_time = await self._calculate_average_job_time(queue_name)
        
        # Get peak throughput (max jobs/minute in last hour)
        peak_throughput = await self._get_peak_throughput(queue_name, 3600)
        
        metrics = ThroughputMetrics(
            timestamp=now,
            jobs_per_minute=jobs_last_minute,
            jobs_per_hour=jobs_last_hour,
            average_job_time=avg_job_time,
            peak_throughput=peak_throughput,
            queue_name=queue_name
        )
        
        # Store metrics
        await self._store_metric(f"{self.THROUGHPUT_METRICS_KEY}:{queue_name}", metrics)
        
        return metrics
    
    async def collect_queue_metrics(self, queue_name: str) -> Dict[str, Any]:
        """Collect metrics for a specific queue."""
        now = datetime.utcnow()
        
        # Queue length metrics
        if self.redis:
            pending_jobs = await self.redis.llen(f"queue:{queue_name}")
            processing_jobs = await self.redis.llen(f"queue:{queue_name}:processing")
            failed_jobs = await self.redis.llen(f"queue:{queue_name}:failed")
        else:
            pending_jobs = processing_jobs = failed_jobs = 0
        
        # Job completion metrics
        completed_today = await self._count_completed_jobs(queue_name, 24 * 3600)
        completed_hour = await self._count_completed_jobs(queue_name, 3600)
        
        # Wait time metrics
        avg_wait_time = await self._calculate_average_wait_time(queue_name)
        
        metrics = {
            'timestamp': now.isoformat(),
            'queue_name': queue_name,
            'pending_jobs': pending_jobs,
            'processing_jobs': processing_jobs,
            'failed_jobs': failed_jobs,
            'completed_today': completed_today,
            'completed_hour': completed_hour,
            'average_wait_time': avg_wait_time,
        }
        
        # Store metrics
        await self._store_metric(f"{self.QUEUE_METRICS_KEY}:{queue_name}", metrics)
        
        return metrics
    
    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive metrics summary for the dashboard."""
        now = datetime.utcnow()
        since = now - timedelta(hours=hours)
        
        # System metrics
        system_metrics = await self._get_metrics_in_timeframe(
            self.SYSTEM_METRICS_KEY, since, now
        )
        
        # Throughput metrics
        throughput_metrics = await self._get_throughput_summary(since, now)
        
        # Queue metrics
        queue_metrics = await self._get_queue_summary()
        
        return {
            'system': system_metrics,
            'throughput': throughput_metrics,
            'queues': queue_metrics,
            'period': f"Last {hours} hours",
            'generated_at': now.isoformat()
        }
    
    async def get_throughput_chart_data(self, queue_name: str = 'default', hours: int = 24) -> List[Dict[str, Any]]:
        """Get throughput data formatted for charts."""
        now = datetime.utcnow()
        since = now - timedelta(hours=hours)
        
        metrics = await self._get_metrics_in_timeframe(
            f"{self.THROUGHPUT_METRICS_KEY}:{queue_name}", since, now
        )
        
        return [
            {
                'timestamp': metric['timestamp'],
                'jobs_per_minute': metric['jobs_per_minute'],
                'average_job_time': metric['average_job_time']
            }
            for metric in metrics
        ]
    
    async def get_system_chart_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get system metrics data formatted for charts."""
        now = datetime.utcnow()
        since = now - timedelta(hours=hours)
        
        metrics = await self._get_metrics_in_timeframe(
            self.SYSTEM_METRICS_KEY, since, now
        )
        
        return [
            {
                'timestamp': metric['timestamp'],
                'cpu_usage': metric['cpu_usage'],
                'memory_usage': metric['memory_usage'],
                'redis_memory': metric['redis_memory']
            }
            for metric in metrics
        ]
    
    async def cleanup_old_metrics(self) -> None:
        """Clean up metrics older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.RETENTION_PERIOD)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Clean up different metric types
        metric_keys = [
            self.SYSTEM_METRICS_KEY,
            self.THROUGHPUT_METRICS_KEY,
            self.QUEUE_METRICS_KEY,
            self.JOB_METRICS_KEY,
        ]
        
        for base_key in metric_keys:
            # Find all keys matching the pattern
            if self.redis:
                keys = await self.redis.keys(f"{base_key}*")
                
                for key in keys:
                    await self.redis.zremrangebyscore(key, 0, cutoff_timestamp)
    
    # Private helper methods
    
    async def _store_metric(self, key: str, metric: Union[SystemMetrics, ThroughputMetrics, Dict[str, Any]]) -> None:
        """Store a metric in Redis sorted set."""
        if isinstance(metric, (SystemMetrics, ThroughputMetrics)):
            data = asdict(metric)
            timestamp = metric.timestamp.timestamp()
        else:
            data = metric
            timestamp = datetime.fromisoformat(metric['timestamp']).timestamp() if 'timestamp' in metric else time.time()
        
        # Convert datetime objects to ISO strings for JSON serialization
        if 'timestamp' in data and isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        if self.redis:
            await self.redis.zadd(key, {json.dumps(data): timestamp})
    
    async def _get_metrics_in_timeframe(self, key: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get metrics from Redis within a specific timeframe."""
        start_timestamp = start_time.timestamp()
        end_timestamp = end_time.timestamp()
        
        if self.redis:
            results = await self.redis.zrangebyscore(key, start_timestamp, end_timestamp)
        else:
            results = []
        
        return [json.loads(result.decode()) for result in results]
    
    async def _count_jobs_in_timeframe(self, queue_name: str, seconds: int) -> int:
        """Count jobs processed in the last N seconds."""
        # This would typically query job completion logs
        # For now, return a simulated count
        key = f"horizon:job_completions:{queue_name}"
        cutoff_time = time.time() - seconds
        
        if self.redis:
            count = await self.redis.zcount(key, cutoff_time, '+inf')
        else:
            count = 0
        return cast(int, count)
    
    async def _calculate_average_job_time(self, queue_name: str) -> float:
        """Calculate average job processing time."""
        # This would analyze job timing data
        # For now, return a simulated average
        key = f"horizon:job_times:{queue_name}"
        if self.redis:
            recent_times = await self.redis.lrange(key, 0, 99)  # Last 100 jobs
        else:
            recent_times = []
        
        if not recent_times:
            return 0.0
        
        times = [float(t.decode()) for t in recent_times]
        return sum(times) / len(times)
    
    async def _get_peak_throughput(self, queue_name: str, seconds: int) -> int:
        """Get peak throughput in the specified time period."""
        # This would analyze throughput history
        # For now, return a simulated peak
        return 0  # Placeholder
    
    async def _count_completed_jobs(self, queue_name: str, seconds: int) -> int:
        """Count completed jobs in timeframe."""
        key = f"horizon:job_completions:{queue_name}"
        cutoff_time = time.time() - seconds
        
        if self.redis:
            return cast(int, await self.redis.zcount(key, cutoff_time, '+inf'))
        else:
            return 0
    
    async def _calculate_average_wait_time(self, queue_name: str) -> float:
        """Calculate average job wait time."""
        # This would analyze job queuing and start times
        # For now, return a simulated average
        return 0.0  # Placeholder
    
    async def _get_throughput_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get throughput summary across all queues."""
        summary = {
            'total_jobs_processed': 0,
            'average_throughput': 0.0,
            'peak_throughput': 0,
            'queues': {}
        }
        
        # This would aggregate data from all queue throughput metrics
        # For now, return the structure with placeholder data
        
        return summary
    
    async def _get_queue_summary(self) -> Dict[str, Any]:
        """Get summary of all queue metrics."""
        summary = {
            'total_queues': 0,
            'total_pending': 0,
            'total_processing': 0,
            'total_failed': 0,
            'queues': {}
        }
        
        # This would aggregate data from all queue metrics
        # For now, return the structure with placeholder data
        
        return summary