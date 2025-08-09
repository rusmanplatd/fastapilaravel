"""
Laravel-style Job Registry and Queue Management
"""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, Type, Optional, List, Callable, Union, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from app.Jobs.Job import Job


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class JobResult:
    """Job execution result"""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobRegistry:
    """
    Laravel-style Job Registry
    Manages job types, scheduling, and execution tracking
    """
    
    def __init__(self) -> None:
        self._registered_jobs: Dict[str, Type[Job]] = {}
        self._job_results: Dict[str, JobResult] = {}
        self._scheduled_jobs: Dict[str, datetime] = {}
        self._recurring_jobs: Dict[str, Dict[str, Any]] = {}
        self._job_middlewares: List[Callable] = []
        self._global_timeout: Optional[int] = None
        self._retry_delays: List[int] = [1, 5, 10, 30, 60, 300]  # Exponential backoff
    
    def register(self, job_class: Type[Job], name: Optional[str] = None) -> None:
        """Register a job class"""
        job_name = name or job_class.__name__
        self._registered_jobs[job_name] = job_class
    
    def get_job_class(self, name: str) -> Optional[Type[Job]]:
        """Get registered job class by name"""
        return self._registered_jobs.get(name)
    
    def schedule(self, job: Job, run_at: datetime) -> str:
        """Schedule a job to run at specific time"""
        job_id = job.job_id or str(id(job))
        self._scheduled_jobs[job_id] = run_at
        
        # Store job result as pending
        self._job_results[job_id] = JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            metadata={
                'scheduled_at': run_at.isoformat(),
                'job_class': job.__class__.__name__
            }
        )
        
        return job_id
    
    def schedule_recurring(
        self,
        job_class: Type[Job],
        cron: str,
        name: Optional[str] = None,
        timezone: str = "UTC",
        **job_kwargs
    ) -> str:
        """Schedule a recurring job using cron expression"""
        job_name = name or f"{job_class.__name__}_recurring"
        
        self._recurring_jobs[job_name] = {
            'job_class': job_class,
            'cron': cron,
            'timezone': timezone,
            'kwargs': job_kwargs,
            'last_run': None,
            'next_run': self._calculate_next_run(cron),
            'enabled': True
        }
        
        return job_name
    
    def cancel_scheduled(self, job_id: str) -> bool:
        """Cancel a scheduled job"""
        if job_id in self._scheduled_jobs:
            del self._scheduled_jobs[job_id]
            
            # Update job result
            if job_id in self._job_results:
                self._job_results[job_id].status = JobStatus.CANCELLED
                self._job_results[job_id].completed_at = datetime.now()
            
            return True
        return False
    
    def get_scheduled_jobs(self) -> Dict[str, datetime]:
        """Get all scheduled jobs"""
        return self._scheduled_jobs.copy()
    
    def get_due_jobs(self) -> List[str]:
        """Get jobs that are due to run"""
        now = datetime.now()
        due_jobs = []
        
        for job_id, run_at in self._scheduled_jobs.items():
            if run_at <= now:
                due_jobs.append(job_id)
        
        return due_jobs
    
    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Get job execution result"""
        return self._job_results.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus, **kwargs) -> None:
        """Update job status and metadata"""
        if job_id not in self._job_results:
            self._job_results[job_id] = JobResult(job_id=job_id, status=status)
        
        result = self._job_results[job_id]
        result.status = status
        
        for key, value in kwargs.items():
            setattr(result, key, value)
    
    def add_middleware(self, middleware: Callable[..., Any]) -> None:
        """Add job middleware"""
        self._job_middlewares.append(middleware)
    
    def set_global_timeout(self, seconds: int) -> None:
        """Set global timeout for all jobs"""
        self._global_timeout = seconds
    
    def set_retry_delays(self, delays: List[int]) -> None:
        """Set retry delay intervals"""
        self._retry_delays = delays
    
    async def retry_job(self, job_id: str, attempt: int = 0) -> bool:
        """Retry a failed job"""
        result = self.get_job_result(job_id)
        if not result:
            return False
        
        # Check if we've exceeded max attempts
        if attempt >= len(self._retry_delays):
            result.status = JobStatus.FAILED
            return False
        
        # Schedule retry with delay
        delay = self._retry_delays[attempt]
        retry_at = datetime.now() + timedelta(seconds=delay)
        
        result.status = JobStatus.RETRYING
        result.attempts = attempt + 1
        result.metadata['retry_at'] = retry_at.isoformat()
        
        # Schedule the retry (this would integrate with your queue system)
        await asyncio.sleep(delay)
        
        return True
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job execution statistics"""
        stats = {
            'total_jobs': len(self._job_results),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0,
            'scheduled': len(self._scheduled_jobs),
            'recurring': len(self._recurring_jobs)
        }
        
        for result in self._job_results.values():
            stats[result.status.value] += 1
        
        return stats
    
    def cleanup_old_results(self, older_than: timedelta = timedelta(days=7)) -> int:
        """Clean up old job results"""
        cutoff = datetime.now() - older_than
        cleaned = 0
        
        to_remove = []
        for job_id, result in self._job_results.items():
            if (result.completed_at and result.completed_at < cutoff and
                result.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]):
                to_remove.append(job_id)
        
        for job_id in to_remove:
            del self._job_results[job_id]
            cleaned += 1
        
        return cleaned
    
    def _calculate_next_run(self, cron: str) -> datetime:
        """Calculate next run time for cron expression"""
        # This would use a proper cron parser like croniter
        # For now, return a placeholder
        return datetime.now() + timedelta(hours=1)
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export detailed metrics for monitoring"""
        stats = self.get_job_statistics()
        
        # Add timing statistics
        completed_jobs = [
            r for r in self._job_results.values() 
            if r.status == JobStatus.COMPLETED and r.started_at and r.completed_at
        ]
        
        if completed_jobs:
            execution_times = [
                (r.completed_at - r.started_at).total_seconds() 
                for r in completed_jobs
            ]
            
            stats['avg_execution_time'] = sum(execution_times) / len(execution_times)
            stats['max_execution_time'] = max(execution_times)
            stats['min_execution_time'] = min(execution_times)
        
        # Add failure rate
        if stats['total_jobs'] > 0:
            stats['failure_rate'] = stats['failed'] / stats['total_jobs']
            stats['success_rate'] = stats['completed'] / stats['total_jobs']
        
        return stats


class JobPipeline:
    """
    Laravel-style Job Pipeline
    Chain multiple jobs together with conditional execution
    """
    
    def __init__(self, name: str = ""):
        self.name = name
        self.jobs: List[Job] = []
        self.on_failure: Optional[Callable[..., Any]] = None
        self.on_success: Optional[Callable[..., Any]] = None
        self.stop_on_failure: bool = True
    
    def then(self, job: Job) -> JobPipeline:
        """Add a job to the pipeline"""
        self.jobs.append(job)
        return self
    
    def catch(self, callback: Callable[..., Any]) -> JobPipeline:
        """Set failure callback"""
        self.on_failure = callback
        return self
    
    def finally_do(self, callback: Callable[..., Any]) -> JobPipeline:
        """Set success callback"""
        self.on_success = callback
        return self
    
    def allow_failures(self) -> JobPipeline:
        """Allow pipeline to continue on job failures"""
        self.stop_on_failure = False
        return self
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the job pipeline"""
        results = []
        failed_jobs = []
        
        for i, job in enumerate(self.jobs):
            try:
                # Execute job (this would integrate with your queue system)
                result = await self._execute_job(job)
                results.append(result)
                
                if not result.get('success', False):
                    failed_jobs.append(i)
                    if self.stop_on_failure:
                        break
                        
            except Exception as e:
                failed_jobs.append(i)
                results.append({'success': False, 'error': str(e)})
                
                if self.stop_on_failure:
                    break
        
        pipeline_result = {
            'pipeline_name': self.name,
            'total_jobs': len(self.jobs),
            'executed_jobs': len(results),
            'failed_jobs': len(failed_jobs),
            'success': len(failed_jobs) == 0,
            'results': results
        }
        
        # Run callbacks
        if pipeline_result['success'] and self.on_success:
            self.on_success(pipeline_result)
        elif not pipeline_result['success'] and self.on_failure:
            self.on_failure(pipeline_result)
        
        return pipeline_result
    
    async def _execute_job(self, job: Job) -> Dict[str, Any]:
        """Execute a single job"""
        try:
            await job.handle()
            return {'success': True, 'job_class': job.__class__.__name__}
        except Exception as e:
            return {'success': False, 'error': str(e), 'job_class': job.__class__.__name__}


# Global job registry instance
job_registry = JobRegistry()


def schedule_job(job: Job, run_at: datetime) -> str:
    """Global helper to schedule a job"""
    return job_registry.schedule(job, run_at)


def schedule_in(job: Job, seconds: int) -> str:
    """Schedule a job to run after specified seconds"""
    run_at = datetime.now() + timedelta(seconds=seconds)
    return job_registry.schedule(job, run_at)


def schedule_at(job: Job, time_str: str) -> str:
    """Schedule a job to run at specified time (HH:MM format)"""
    # Parse time string and calculate next occurrence
    # This would use proper date parsing
    run_at = datetime.now().replace(hour=int(time_str.split(':')[0]), 
                                   minute=int(time_str.split(':')[1]))
    
    # If time has passed today, schedule for tomorrow
    if run_at <= datetime.now():
        run_at += timedelta(days=1)
    
    return job_registry.schedule(job, run_at)


def recurring(cron: str, name: str = "") -> Callable[[Type[Job]], Type[Job]]:
    """Decorator for recurring jobs"""
    def decorator(job_class: Type[Job]) -> Type[Job]:
        job_registry.schedule_recurring(job_class, cron, name)
        return job_class
    
    return decorator