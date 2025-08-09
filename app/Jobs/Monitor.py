from __future__ import annotations

import os
import json
import time
import socket
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from collections import defaultdict

from config.database import get_database

if TYPE_CHECKING:
    from app.Jobs.Job import ShouldQueue
    from app.Models.JobMetric import JobMetric


@dataclass
class PerformanceMetrics:
    """Performance metrics for job execution."""
    avg_duration_ms: float
    avg_memory_mb: float
    success_rate: float
    total_jobs: int
    failed_jobs: int
    avg_attempts: float


class JobMonitor:
    """
    Job monitoring system that tracks execution metrics and performance.
    """
    
    def __init__(self) -> None:
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
    
    def start_job(self, job: ShouldQueue, worker_id: str) -> str:
        """Start monitoring a job."""
        job_uuid = self._generate_job_uuid(job)
        
        # Record start time and initial metrics
        start_time = datetime.now(timezone.utc)
        
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            initial_memory = 0.0
        
        self.active_jobs[job_uuid] = {
            "job": job,
            "start_time": start_time,
            "initial_memory": initial_memory,
            "worker_id": worker_id
        }
        
        # Create job metric record
        self._create_job_metric(job, job_uuid, worker_id, start_time)
        
        return job_uuid
    
    def finish_job(self, job_uuid: str, success: bool = True, error: Optional[Exception] = None) -> None:
        """Finish monitoring a job."""
        if job_uuid not in self.active_jobs:
            return
        
        job_data = self.active_jobs[job_uuid]
        end_time = datetime.now(timezone.utc)
        
        # Calculate metrics
        duration = end_time - job_data["start_time"]
        duration_ms = int(duration.total_seconds() * 1000)
        
        try:
            import psutil
            process = psutil.Process()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage = final_memory - job_data["initial_memory"]
        except ImportError:
            memory_usage = 0.0
        
        # Update job metric
        self._update_job_metric(job_uuid, success, duration_ms, memory_usage, error)
        
        # Remove from active jobs
        del self.active_jobs[job_uuid]
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get currently active jobs."""
        active = []
        for job_uuid, data in self.active_jobs.items():
            runtime = datetime.now(timezone.utc) - data["start_time"]
            active.append({
                "job_uuid": job_uuid,
                "job_class": data["job"].__class__.__name__,
                "runtime_seconds": runtime.total_seconds(),
                "worker_id": data["worker_id"]
            })
        return active
    
    def get_job_performance(
        self,
        job_class: Optional[str] = None,
        queue: Optional[str] = None,
        hours: int = 24
    ) -> PerformanceMetrics:
        """Get performance metrics for jobs."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            # Build query
            query = db.query(JobMetric)
            
            if job_class:
                query = query.filter(JobMetric.job_class.contains(job_class))
            
            if queue:
                query = query.filter(JobMetric.queue == queue)
            
            # Filter by time range
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            query = query.filter(JobMetric.started_at >= cutoff)
            
            metrics = query.all()
            
            if not metrics:
                return PerformanceMetrics(0, 0, 100.0, 0, 0, 0)
            
            # Calculate averages
            total_jobs = len(metrics)
            failed_jobs = sum(1 for m in metrics if m.status == "failed")
            
            completed_metrics = [m for m in metrics if m.duration_ms is not None]
            
            avg_duration = sum(m.duration_ms for m in completed_metrics if m.duration_ms is not None) / len(completed_metrics) if completed_metrics else 0
            
            memory_metrics = [m for m in metrics if m.memory_peak_mb is not None]
            avg_memory = sum(m.memory_peak_mb for m in memory_metrics if m.memory_peak_mb is not None) / len(memory_metrics) if memory_metrics else 0
            
            avg_attempts = sum(m.attempts for m in metrics) / total_jobs
            success_rate = ((total_jobs - failed_jobs) / total_jobs) * 100 if total_jobs > 0 else 100
            
            return PerformanceMetrics(
                avg_duration_ms=avg_duration,
                avg_memory_mb=avg_memory,
                success_rate=success_rate,
                total_jobs=total_jobs,
                failed_jobs=failed_jobs,
                avg_attempts=avg_attempts
            )
            
        finally:
            db.close()
    
    def get_queue_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics grouped by queue."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            metrics = db.query(JobMetric).filter(JobMetric.started_at >= cutoff).all()
            
            queue_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "avg_duration_ms": 0,
                "avg_memory_mb": 0
            })
            
            for metric in metrics:
                queue = metric.queue
                queue_stats[queue]["total_jobs"] += 1
                
                if metric.status == "completed":
                    queue_stats[queue]["completed_jobs"] += 1
                elif metric.status == "failed":
                    queue_stats[queue]["failed_jobs"] += 1
            
            # Calculate averages
            for queue, stats in queue_stats.items():
                queue_metrics = [m for m in metrics if m.queue == queue]
                
                completed_metrics = [m for m in queue_metrics if m.duration_ms is not None]
                if completed_metrics:
                    stats["avg_duration_ms"] = sum(m.duration_ms for m in completed_metrics if m.duration_ms is not None) / len(completed_metrics)
                
                memory_metrics = [m for m in queue_metrics if m.memory_peak_mb is not None]
                if memory_metrics:
                    stats["avg_memory_mb"] = sum(m.memory_peak_mb for m in memory_metrics if m.memory_peak_mb is not None) / len(memory_metrics)
                
                stats["success_rate"] = (stats["completed_jobs"] / stats["total_jobs"] * 100) if stats["total_jobs"] > 0 else 100
            
            return dict(queue_stats)
            
        finally:
            db.close()
    
    def get_slow_jobs(self, threshold_ms: int = 30000, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest jobs above threshold."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            slow_jobs = (
                db.query(JobMetric)
                .filter(JobMetric.duration_ms >= threshold_ms)
                .order_by(JobMetric.duration_ms.desc())
                .limit(limit)
                .all()
            )
            
            return [job.to_dict() for job in slow_jobs]
            
        finally:
            db.close()
    
    def get_memory_hungry_jobs(self, threshold_mb: int = 100, limit: int = 10) -> List[Dict[str, Any]]:
        """Get jobs using most memory."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            hungry_jobs = (
                db.query(JobMetric)
                .filter(JobMetric.memory_peak_mb >= threshold_mb)
                .order_by(JobMetric.memory_peak_mb.desc())
                .limit(limit)
                .all()
            )
            
            return [job.to_dict() for job in hungry_jobs]
            
        finally:
            db.close()
    
    def cleanup_old_metrics(self, days: int = 30) -> int:
        """Clean up metrics older than specified days."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            deleted_count = (
                db.query(JobMetric)
                .filter(JobMetric.started_at < cutoff)
                .delete()
            )
            
            db.commit()
            return int(deleted_count)
            
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def _generate_job_uuid(self, job: ShouldQueue) -> str:
        """Generate unique UUID for job tracking."""
        import uuid
        return str(uuid.uuid4())
    
    def _create_job_metric(self, job: ShouldQueue, job_uuid: str, worker_id: str, start_time: datetime) -> None:
        """Create initial job metric record."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            # Calculate payload size
            payload_size = len(json.dumps(job.serialize()).encode('utf-8'))
            
            metric = JobMetric(
                job_uuid=job_uuid,
                job_class=f"{job.__class__.__module__}.{job.__class__.__name__}",
                queue=job.options.queue,
                started_at=start_time,
                status="running",
                attempts=getattr(job, 'attempts', 1),
                worker_id=worker_id,
                worker_hostname=self.hostname,
                worker_pid=self.pid,
                payload_size=payload_size,
                tags=json.dumps(job.get_tags()),
                batch_id=getattr(job, '_batch_id', None)
            )
            
            db.add(metric)
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Failed to create job metric: {str(e)}")
        finally:
            db.close()
    
    def _update_job_metric(
        self,
        job_uuid: str,
        success: bool,
        duration_ms: int,
        memory_usage_mb: float,
        error: Optional[Exception] = None
    ) -> None:
        """Update job metric with completion data."""
        db = next(get_database())
        try:
            from app.Models.JobMetric import JobMetric
            
            metric = db.query(JobMetric).filter(JobMetric.job_uuid == job_uuid).first()
            
            if metric:
                if success:
                    metric.mark_completed(duration_ms, memory_usage_mb)
                else:
                    metric.mark_failed(error or Exception("Unknown error"), duration_ms)
                
                metric.memory_usage_mb = memory_usage_mb
                
                db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Failed to update job metric: {str(e)}")
        finally:
            db.close()


# Global job monitor instance
global_job_monitor = JobMonitor()