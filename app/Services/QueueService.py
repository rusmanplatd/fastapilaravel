from __future__ import annotations

import json
import uuid
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Sequence
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.sql import desc, asc
from sqlalchemy.orm import Session

from app.Services.BaseService import BaseService
from app.Jobs.Job import ShouldQueue
from config.database import get_database

if TYPE_CHECKING:
    from database.migrations.create_jobs_table import Job as JobModel
    from database.migrations.create_failed_jobs_table import FailedJob


class QueueService(BaseService):
    """
    Queue service for managing job queues.
    Similar to Laravel's Queue facade and queue manager.
    """
    
    def __init__(self, db: Session, connection: str = "default") -> None:
        super().__init__(db)
        self.connection = connection
        self.logger = logging.getLogger(__name__)
    
    def push(self, job: ShouldQueue, queue: Optional[str] = None) -> str:
        """
        Push a job onto the queue.
        
        Args:
            job: The job to queue
            queue: Optional queue name override
            
        Returns:
            The job ID
        """
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            # Serialize job data
            payload = job.serialize()
            
            # Create job model
            job_model = JobModel(
                queue=queue or job.options.queue,
                payload=json.dumps(payload),
                job_class=payload["job_class"],
                job_method=payload["job_method"],
                connection=self.connection,
                priority=job.options.priority,
                delay=job.options.delay,
                available_at=datetime.utcnow() + timedelta(seconds=job.options.delay)
            )
            
            db.add(job_model)
            db.commit()
            
            self.logger.info(f"Job {job_model.id} queued on '{job_model.queue}' queue")
            return job_model.id
            
        except Exception as e:
            self.logger.error(f"Failed to queue job: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def push_on(self, queue: str, job: ShouldQueue) -> str:
        """Push job to specific queue."""
        return self.push(job, queue)
    
    def later(self, delay: int, job: ShouldQueue, queue: Optional[str] = None) -> str:
        """Push job with delay in seconds."""
        job.delay_until(delay)
        return self.push(job, queue)
    
    def bulk(self, jobs: Sequence[ShouldQueue], queue: Optional[str] = None) -> List[str]:
        """Push multiple jobs to queue."""
        job_ids = []
        for job in jobs:
            job_ids.append(self.push(job, queue))
        return job_ids
    
    def size(self, queue: str = "default") -> int:
        """Get the size of the queue."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            return db.query(JobModel).filter(
                JobModel.queue == queue,
                JobModel.is_reserved == False
            ).count()
        finally:
            db.close()
    
    def get_jobs(
        self, 
        queue: str = "default", 
        limit: int = 50, 
        offset: int = 0,
        include_reserved: bool = False
    ) -> List[Dict[str, Any]]:
        """Get jobs from queue."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            query = db.query(JobModel).filter(JobModel.queue == queue)
            
            if not include_reserved:
                query = query.filter(JobModel.is_reserved == False)
            
            jobs = (
                query.order_by(desc(JobModel.priority), asc(JobModel.available_at))
                .offset(offset)
                .limit(limit)
                .all()
            )
            
            return [job.to_dict() for job in jobs]
        finally:
            db.close()
    
    def find_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Find a job by ID."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            return job.to_dict() if job else None
        finally:
            db.close()
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the queue."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            if job:
                db.delete(job)
                db.commit()
                self.logger.info(f"Job {job_id} deleted from queue")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete job {job_id}: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def clear_queue(self, queue: str = "default") -> int:
        """Clear all jobs from a queue."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            count = db.query(JobModel).filter(JobModel.queue == queue).count()
            db.query(JobModel).filter(JobModel.queue == queue).delete()
            db.commit()
            
            self.logger.info(f"Cleared {count} jobs from '{queue}' queue")
            return count
        except Exception as e:
            self.logger.error(f"Failed to clear queue '{queue}': {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def release_reserved_jobs(self, timeout: int = 3600) -> int:
        """Release jobs that have been reserved too long."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            
            timeout_time = datetime.utcnow() - timedelta(seconds=timeout)
            
            expired_jobs = db.query(JobModel).filter(
                JobModel.is_reserved == True,
                JobModel.reserved_at <= timeout_time
            ).all()
            
            count = 0
            for job in expired_jobs:
                job.release()
                count += 1
            
            if count > 0:
                db.commit()
                self.logger.info(f"Released {count} expired reserved jobs")
            
            return count
        except Exception as e:
            self.logger.error(f"Failed to release reserved jobs: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_failed_jobs(
        self, 
        limit: int = 50, 
        offset: int = 0,
        queue: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get failed jobs."""
        db = next(get_database())
        try:
            from database.migrations.create_failed_jobs_table import FailedJob
            
            query = db.query(FailedJob)
            
            if queue:
                query = query.filter(FailedJob.queue == queue)
            
            failed_jobs = (
                query.order_by(desc(FailedJob.failed_at))
                .offset(offset)
                .limit(limit)
                .all()
            )
            
            return [job.to_dict() for job in failed_jobs]
        finally:
            db.close()
    
    def retry_failed_job(self, failed_job_id: str, queue: Optional[str] = None) -> str:
        """Retry a failed job."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            from database.migrations.create_failed_jobs_table import FailedJob
            
            failed_job = db.query(FailedJob).filter(FailedJob.id == failed_job_id).first()
            if not failed_job:
                raise ValueError(f"Failed job {failed_job_id} not found")
            
            # Create new job from failed job
            new_job = JobModel(
                queue=queue or failed_job.queue,
                payload=failed_job.payload,
                job_class=failed_job.job_class,
                job_method=failed_job.job_method,
                connection=failed_job.connection,
                available_at=datetime.utcnow()
            )
            
            db.add(new_job)
            db.delete(failed_job)
            db.commit()
            
            self.logger.info(f"Failed job {failed_job_id} retried as job {new_job.id}")
            return new_job.id
            
        except Exception as e:
            self.logger.error(f"Failed to retry job {failed_job_id}: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def retry_all_failed_jobs(self, queue: Optional[str] = None) -> int:
        """Retry all failed jobs."""
        db = next(get_database())
        try:
            from database.migrations.create_failed_jobs_table import FailedJob
            
            query = db.query(FailedJob)
            if queue:
                query = query.filter(FailedJob.queue == queue)
            
            failed_jobs = query.all()
            count = 0
            
            for failed_job in failed_jobs:
                try:
                    self.retry_failed_job(failed_job.id)
                    count += 1
                except Exception as e:
                    self.logger.error(f"Failed to retry job {failed_job.id}: {str(e)}")
            
            self.logger.info(f"Retried {count} failed jobs")
            return count
            
        finally:
            db.close()
    
    def delete_failed_job(self, failed_job_id: str) -> bool:
        """Delete a failed job."""
        db = next(get_database())
        try:
            from database.migrations.create_failed_jobs_table import FailedJob
            
            failed_job = db.query(FailedJob).filter(FailedJob.id == failed_job_id).first()
            if failed_job:
                db.delete(failed_job)
                db.commit()
                self.logger.info(f"Failed job {failed_job_id} deleted")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete failed job {failed_job_id}: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def clear_failed_jobs(self, queue: Optional[str] = None) -> int:
        """Clear failed jobs."""
        db = next(get_database())
        try:
            from database.migrations.create_failed_jobs_table import FailedJob
            
            query = db.query(FailedJob)
            if queue:
                query = query.filter(FailedJob.queue == queue)
            
            count = query.count()
            query.delete()
            db.commit()
            
            self.logger.info(f"Cleared {count} failed jobs")
            return count
        except Exception as e:
            self.logger.error(f"Failed to clear failed jobs: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        db = next(get_database())
        try:
            from database.migrations.create_jobs_table import Job as JobModel
            from database.migrations.create_failed_jobs_table import FailedJob
            
            # Get stats for each queue
            queue_stats = {}
            
            # Get all queue names
            queues = db.query(JobModel.queue).distinct().all()
            queue_names = [q[0] for q in queues]
            
            for queue_name in queue_names:
                pending_jobs = db.query(JobModel).filter(
                    JobModel.queue == queue_name,
                    JobModel.is_reserved == False,
                    JobModel.available_at <= datetime.utcnow()
                ).count()
                
                delayed_jobs = db.query(JobModel).filter(
                    JobModel.queue == queue_name,
                    JobModel.is_reserved == False,
                    JobModel.available_at > datetime.utcnow()
                ).count()
                
                reserved_jobs = db.query(JobModel).filter(
                    JobModel.queue == queue_name,
                    JobModel.is_reserved == True
                ).count()
                
                failed_jobs = db.query(FailedJob).filter(
                    FailedJob.queue == queue_name
                ).count()
                
                queue_stats[queue_name] = {
                    "pending": pending_jobs,
                    "delayed": delayed_jobs,
                    "reserved": reserved_jobs,
                    "failed": failed_jobs,
                    "total": pending_jobs + delayed_jobs + reserved_jobs
                }
            
            # Overall stats
            total_jobs = db.query(JobModel).count()
            total_failed = db.query(FailedJob).count()
            
            return {
                "queues": queue_stats,
                "totals": {
                    "active_jobs": total_jobs,
                    "failed_jobs": total_failed
                }
            }
        finally:
            db.close()