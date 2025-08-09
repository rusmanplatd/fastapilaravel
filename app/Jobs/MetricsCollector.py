"""
Comprehensive Job Execution Metrics Collection System
"""
from __future__ import annotations

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Deque
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import json
import statistics
import logging


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class JobPhase(Enum):
    """Job execution phases for detailed tracking."""
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRIED = "retried"


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobMetrics:
    """Comprehensive metrics for a job execution."""
    job_id: str
    job_type: str
    queue_name: str
    
    # Timing metrics
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration: Optional[float] = None
    total_duration: Optional[float] = None
    queue_wait_time: Optional[float] = None
    
    # Execution metrics
    phase: JobPhase = JobPhase.QUEUED
    success: bool = False
    retry_count: int = 0
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    io_operations: int = 0
    
    # Business metrics
    records_processed: int = 0
    bytes_processed: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Tags and metadata
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics over a time period."""
    period_start: datetime
    period_end: datetime
    job_count: int
    success_count: int
    failure_count: int
    retry_count: int
    
    # Timing statistics
    avg_processing_duration: float
    p50_processing_duration: float
    p95_processing_duration: float
    p99_processing_duration: float
    min_processing_duration: float
    max_processing_duration: float
    
    avg_queue_wait_time: float
    p95_queue_wait_time: float
    
    # Throughput metrics
    jobs_per_second: float
    jobs_per_minute: float
    
    # Resource statistics
    avg_memory_usage: float
    peak_memory_usage: float
    avg_cpu_usage: float
    
    # Error statistics
    error_rate: float
    retry_rate: float
    top_errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Queue statistics
    queue_stats: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Comprehensive metrics collection system for job execution.
    """
    
    def __init__(self, retention_hours: int = 168) -> None:  # 7 days default
        self.retention_hours = retention_hours
        self.job_metrics: Dict[str, JobMetrics] = {}
        self.metric_points: Dict[str, Deque[Any]] = defaultdict(lambda: deque(maxlen=10000))
        self.aggregated_metrics: Dict[str, AggregatedMetrics] = {}
        
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.active_timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Cleanup timer
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()
    
    def record_job_queued(
        self,
        job_id: str,
        job_type: str,
        queue_name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record when a job is queued."""
        with self._lock:
            metrics = JobMetrics(
                job_id=job_id,
                job_type=job_type,
                queue_name=queue_name,
                queued_at=datetime.now(),
                phase=JobPhase.QUEUED,
                tags=tags or {}
            )
            self.job_metrics[job_id] = metrics
            
            # Update counters
            self.counters[f"jobs.queued.{queue_name}"] += 1
            self.counters[f"jobs.queued.{job_type}"] += 1
            self.counters["jobs.queued.total"] += 1
            
            self.logger.debug(f"Job {job_id} queued in {queue_name}")
    
    def record_job_started(self, job_id: str) -> None:
        """Record when a job starts processing."""
        with self._lock:
            if job_id not in self.job_metrics:
                self.logger.warning(f"Job {job_id} not found in metrics")
                return
            
            metrics = self.job_metrics[job_id]
            now = datetime.now()
            metrics.started_at = now
            metrics.phase = JobPhase.STARTED
            
            # Calculate queue wait time
            if metrics.queued_at:
                metrics.queue_wait_time = (now - metrics.queued_at).total_seconds()
                self._record_histogram(
                    f"jobs.queue_wait_time.{metrics.queue_name}",
                    metrics.queue_wait_time
                )
            
            self.counters[f"jobs.started.{metrics.queue_name}"] += 1
            self.counters["jobs.started.total"] += 1
            
            self.logger.debug(f"Job {job_id} started processing")
    
    def record_job_completed(
        self,
        job_id: str,
        success: bool,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        records_processed: int = 0,
        bytes_processed: int = 0,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record job completion."""
        with self._lock:
            if job_id not in self.job_metrics:
                self.logger.warning(f"Job {job_id} not found in metrics")
                return
            
            metrics = self.job_metrics[job_id]
            now = datetime.now()
            metrics.completed_at = now
            metrics.success = success
            metrics.phase = JobPhase.COMPLETED if success else JobPhase.FAILED
            metrics.error_message = error_message
            metrics.error_type = error_type
            metrics.records_processed = records_processed
            metrics.bytes_processed = bytes_processed
            
            if custom_metrics:
                metrics.custom_metrics.update(custom_metrics)
            
            # Calculate durations
            if metrics.started_at:
                metrics.processing_duration = (now - metrics.started_at).total_seconds()
                self._record_histogram(
                    f"jobs.processing_duration.{metrics.queue_name}",
                    metrics.processing_duration
                )
            
            if metrics.queued_at:
                metrics.total_duration = (now - metrics.queued_at).total_seconds()
                self._record_histogram(
                    f"jobs.total_duration.{metrics.queue_name}",
                    metrics.total_duration
                )
            
            # Update counters
            status = "success" if success else "failure"
            self.counters[f"jobs.{status}.{metrics.queue_name}"] += 1
            self.counters[f"jobs.{status}.{metrics.job_type}"] += 1
            self.counters[f"jobs.{status}.total"] += 1
            
            if not success and error_type:
                self.counters[f"jobs.errors.{error_type}"] += 1
            
            # Record throughput metrics
            if records_processed > 0:
                self._record_histogram(
                    f"jobs.records_processed.{metrics.job_type}",
                    records_processed
                )
            
            if bytes_processed > 0:
                self._record_histogram(
                    f"jobs.bytes_processed.{metrics.job_type}",
                    bytes_processed
                )
            
            self.logger.debug(
                f"Job {job_id} completed - Success: {success}, "
                f"Duration: {metrics.processing_duration:.2f}s"
            )
    
    def record_job_retry(self, job_id: str, retry_count: int) -> None:
        """Record a job retry attempt."""
        with self._lock:
            if job_id in self.job_metrics:
                metrics = self.job_metrics[job_id]
                metrics.retry_count = retry_count
                metrics.phase = JobPhase.RETRIED
                
                self.counters[f"jobs.retried.{metrics.queue_name}"] += 1
                self.counters["jobs.retried.total"] += 1
                
                self.logger.debug(f"Job {job_id} retry attempt {retry_count}")
    
    def record_resource_usage(
        self,
        job_id: str,
        memory_mb: float,
        cpu_percent: float,
        io_operations: int = 0
    ) -> None:
        """Record resource usage for a job."""
        with self._lock:
            if job_id in self.job_metrics:
                metrics = self.job_metrics[job_id]
                metrics.peak_memory_mb = max(metrics.peak_memory_mb, memory_mb)
                metrics.cpu_usage_percent = cpu_percent
                metrics.io_operations += io_operations
                
                # Record as gauge metrics
                self.gauges[f"jobs.memory_usage.{metrics.queue_name}"] = memory_mb
                self.gauges[f"jobs.cpu_usage.{metrics.queue_name}"] = cpu_percent
    
    def start_timer(self, timer_name: str) -> None:
        """Start a named timer."""
        with self._lock:
            self.active_timers[timer_name] = time.time()
    
    def end_timer(self, timer_name: str) -> Optional[float]:
        """End a named timer and return duration."""
        with self._lock:
            if timer_name in self.active_timers:
                duration = time.time() - self.active_timers[timer_name]
                del self.active_timers[timer_name]
                self._record_histogram(f"timers.{timer_name}", duration)
                return duration
            return None
    
    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        with self._lock:
            self.counters[counter_name] += value
    
    def set_gauge(self, gauge_name: str, value: float) -> None:
        """Set a gauge metric value."""
        with self._lock:
            self.gauges[gauge_name] = value
    
    def record_histogram(self, histogram_name: str, value: float) -> None:
        """Record a value in a histogram."""
        with self._lock:
            self._record_histogram(histogram_name, value)
    
    def _record_histogram(self, name: str, value: float) -> None:
        """Internal histogram recording."""
        self.histograms[name].append(value)
        # Keep only last 1000 values per histogram
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]
    
    def get_job_metrics(self, job_id: str) -> Optional[JobMetrics]:
        """Get metrics for a specific job."""
        with self._lock:
            return self.job_metrics.get(job_id)
    
    def get_queue_metrics(self, queue_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated metrics for a queue."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            queue_jobs = [
                metrics for metrics in self.job_metrics.values()
                if metrics.queue_name == queue_name and metrics.queued_at > cutoff_time
            ]
            
            if not queue_jobs:
                return {"queue_name": queue_name, "job_count": 0}
            
            return self._calculate_aggregated_metrics(queue_jobs, queue_name)
    
    def get_overall_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get overall system metrics."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_jobs = [
                metrics for metrics in self.job_metrics.values()
                if metrics.queued_at > cutoff_time
            ]
            
            if not recent_jobs:
                return {"job_count": 0}
            
            return self._calculate_aggregated_metrics(recent_jobs, "overall")
    
    def _calculate_aggregated_metrics(
        self,
        jobs: List[JobMetrics],
        scope: str
    ) -> Dict[str, Any]:
        """Calculate aggregated metrics from job list."""
        if not jobs:
            return {}
        
        # Basic counts
        total_jobs = len(jobs)
        successful_jobs = sum(1 for job in jobs if job.success)
        failed_jobs = total_jobs - successful_jobs
        total_retries = sum(job.retry_count for job in jobs)
        
        # Timing metrics
        processing_durations = [
            job.processing_duration for job in jobs
            if job.processing_duration is not None
        ]
        
        queue_wait_times = [
            job.queue_wait_time for job in jobs
            if job.queue_wait_time is not None
        ]
        
        # Resource metrics
        memory_values = [job.peak_memory_mb for job in jobs if job.peak_memory_mb > 0]
        cpu_values = [job.cpu_usage_percent for job in jobs if job.cpu_usage_percent > 0]
        
        # Calculate statistics
        result = {
            "scope": scope,
            "period_hours": 24,
            "job_count": total_jobs,
            "success_count": successful_jobs,
            "failure_count": failed_jobs,
            "retry_count": total_retries,
            "success_rate": (successful_jobs / total_jobs) * 100 if total_jobs > 0 else 0,
            "error_rate": (failed_jobs / total_jobs) * 100 if total_jobs > 0 else 0,
            "retry_rate": (total_retries / total_jobs) * 100 if total_jobs > 0 else 0
        }
        
        # Processing duration statistics
        if processing_durations:
            result.update({
                "avg_processing_duration": statistics.mean(processing_durations),
                "min_processing_duration": min(processing_durations),
                "max_processing_duration": max(processing_durations),
                "p50_processing_duration": statistics.median(processing_durations),
                "p95_processing_duration": self._percentile(processing_durations, 95),
                "p99_processing_duration": self._percentile(processing_durations, 99)
            })
        
        # Queue wait time statistics
        if queue_wait_times:
            result.update({
                "avg_queue_wait_time": statistics.mean(queue_wait_times),
                "p95_queue_wait_time": self._percentile(queue_wait_times, 95)
            })
        
        # Resource statistics
        if memory_values:
            result.update({
                "avg_memory_usage": statistics.mean(memory_values),
                "peak_memory_usage": max(memory_values)
            })
        
        if cpu_values:
            result["avg_cpu_usage"] = statistics.mean(cpu_values)
        
        # Throughput calculations
        if jobs:
            time_span = (max(job.queued_at for job in jobs) - 
                        min(job.queued_at for job in jobs)).total_seconds()
            if time_span > 0:
                result["jobs_per_second"] = total_jobs / time_span
                result["jobs_per_minute"] = (total_jobs / time_span) * 60
        
        # Top errors
        error_counts: Dict[str, int] = defaultdict(int)
        for job in jobs:
            if not job.success and job.error_type:
                error_counts[job.error_type] += 1
        
        result["top_errors"] = [
            {"error_type": error_type, "count": count}
            for error_type, count in sorted(error_counts.items(), 
                                          key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return result
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index == int(index):
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_current_counters(self) -> Dict[str, int]:
        """Get current counter values."""
        with self._lock:
            return dict(self.counters)
    
    def get_current_gauges(self) -> Dict[str, float]:
        """Get current gauge values."""
        with self._lock:
            return dict(self.gauges)
    
    def get_histogram_stats(self, histogram_name: str) -> Dict[str, float]:
        """Get statistics for a histogram."""
        with self._lock:
            values = self.histograms.get(histogram_name, [])
            if not values:
                return {}
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99)
            }
    
    def cleanup_old_metrics(self) -> int:
        """Clean up old metrics beyond retention period."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
            
            old_job_ids = [
                job_id for job_id, metrics in self.job_metrics.items()
                if metrics.queued_at < cutoff_time
            ]
            
            for job_id in old_job_ids:
                del self.job_metrics[job_id]
            
            self.logger.info(f"Cleaned up {len(old_job_ids)} old metric records")
            return len(old_job_ids)
    
    def _start_cleanup_timer(self) -> None:
        """Start periodic cleanup timer."""
        def cleanup_task() -> None:
            self.cleanup_old_metrics()
            self._start_cleanup_timer()  # Reschedule
        
        # Run cleanup every hour
        self._cleanup_timer = threading.Timer(3600, cleanup_task)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        with self._lock:
            return {
                "total_jobs_tracked": len(self.job_metrics),
                "active_counters": len(self.counters),
                "active_gauges": len(self.gauges),
                "active_histograms": len(self.histograms),
                "retention_hours": self.retention_hours,
                "memory_usage": {
                    "job_metrics_count": len(self.job_metrics),
                    "counter_count": len(self.counters),
                    "gauge_count": len(self.gauges),
                    "histogram_count": len(self.histograms)
                }
            }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations with metrics collection."""
    
    def __init__(self, timer_name: str, collector: Optional[MetricsCollector] = None):
        self.timer_name = timer_name
        self.collector = collector or get_metrics_collector()
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None
    
    def __enter__(self) -> MetricsTimer:
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time:
            self.duration = time.time() - self.start_time
            self.collector.record_histogram(self.timer_name, self.duration)


# Decorator for automatic job metrics collection
def collect_job_metrics(
    job_type: Optional[str] = None,
    queue_name: Optional[str] = None,
    collect_resources: bool = False
) -> Callable[..., Any]:
    """
    Decorator for automatic job metrics collection.
    
    Args:
        job_type: Override job type (defaults to function name)
        queue_name: Override queue name (defaults to 'default')
        collect_resources: Whether to collect resource usage metrics
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            collector = get_metrics_collector()
            func_job_type = job_type or func.__name__
            func_queue_name = queue_name or 'default'
            job_id = f"{func_job_type}_{id(func)}_{int(time.time())}"
            
            # Record job queued
            collector.record_job_queued(job_id, func_job_type, func_queue_name)
            
            # Record job started
            collector.record_job_started(job_id)
            
            success = False
            error_message = None
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_message = str(e)
                error_type = type(e).__name__
                raise
            finally:
                # Record completion
                collector.record_job_completed(
                    job_id=job_id,
                    success=success,
                    error_message=error_message,
                    error_type=error_type
                )
        
        return wrapper
    return decorator