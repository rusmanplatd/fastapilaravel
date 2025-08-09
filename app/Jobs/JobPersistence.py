"""
Production-ready Job Persistence and Recovery System
"""
from __future__ import annotations

import json
import pickle
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid
import hashlib

from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, LargeBinary
try:
    from sqlalchemy import DateTime
except ImportError:
    from sqlalchemy.sql.sqltypes import DateTime
try:
    from sqlalchemy.ext.declarative import declarative_base
except ImportError:
    from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.Jobs.Job import ShouldQueue
from app.Jobs.Chain import JobChain, ChainStatus
from app.Jobs.MetricsCollector import get_metrics_collector
from config.database import get_database


Base = declarative_base()  # type: ignore


class PersistenceMethod(Enum):
    """Methods for job persistence."""
    DATABASE = "database"
    FILE_SYSTEM = "filesystem"
    REDIS = "redis"
    HYBRID = "hybrid"


class RecoveryStrategy(Enum):
    """Strategies for job recovery."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass
class PersistenceConfig:
    """Configuration for job persistence."""
    method: PersistenceMethod = PersistenceMethod.DATABASE
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.DELAYED
    retention_days: int = 30
    compression_enabled: bool = True
    encryption_enabled: bool = False
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    auto_recovery_enabled: bool = True
    recovery_delay_seconds: int = 60
    max_recovery_attempts: int = 3


class PersistedJob(Base):
    """Database model for persisted jobs."""
    __tablename__ = 'persisted_jobs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    job_type = Column(String(255), nullable=False, index=True)
    queue_name = Column(String(255), nullable=False, index=True)
    
    # Job state
    status = Column(String(50), nullable=False, index=True)
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Serialized job data
    serialized_job = Column(LargeBinary, nullable=True)  # Pickled job object
    job_data = Column(Text, nullable=True)  # JSON job data
    job_args = Column(Text, nullable=True)  # JSON serialized args
    job_kwargs = Column(Text, nullable=True)  # JSON serialized kwargs
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Recovery metadata
    recovery_attempts = Column(Integer, default=0)
    last_recovery_at = Column(DateTime, nullable=True)
    recovery_strategy = Column(String(50), nullable=True)
    
    # Tags and context
    tags = Column(Text, nullable=True)  # JSON
    context_data = Column(Text, nullable=True)  # JSON
    
    # Chain information
    chain_id = Column(String(255), nullable=True, index=True)
    chain_step = Column(Integer, nullable=True)
    
    def serialize_job_data(self, job: Any) -> None:
        """Serialize job data for persistence."""
        try:
            # Store both pickled object and JSON data
            self.serialized_job = pickle.dumps(job)
            
            # Also store JSON representation for inspection
            self.job_data = json.dumps({
                'job_type': type(job).__name__,
                'job_module': type(job).__module__,
                'attributes': {k: v for k, v in job.__dict__.items() 
                             if not k.startswith('_') and self._is_serializable(v)}
            }, default=str)
            
        except Exception as e:
            logging.error(f"Failed to serialize job {self.job_id}: {str(e)}")
            # Fallback to JSON-only storage
            self.job_data = json.dumps({
                'job_type': type(job).__name__,
                'error': f"Serialization failed: {str(e)}"
            }, default=str)
    
    def deserialize_job(self) -> Optional[Any]:
        """Deserialize job from persistence."""
        if self.serialized_job:
            try:
                return pickle.loads(self.serialized_job)
            except Exception as e:
                logging.error(f"Failed to deserialize job {self.job_id}: {str(e)}")
        
        # Try to reconstruct from JSON data
        if self.job_data:
            try:
                job_info = json.loads(self.job_data)
                # This would require a job registry to reconstruct jobs
                # For now, return None and log the failure
                logging.warning(f"Cannot reconstruct job {self.job_id} from JSON data")
                return None
            except Exception as e:
                logging.error(f"Failed to reconstruct job {self.job_id}: {str(e)}")
        
        return None
    
    def _is_serializable(self, value: Any) -> bool:
        """Check if a value is JSON serializable."""
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False


class PersistedChain(Base):
    """Database model for persisted job chains."""
    __tablename__ = 'persisted_chains'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chain_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    
    # Chain state
    status = Column(String(50), nullable=False, index=True)
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=False)
    
    # Serialized chain data
    serialized_chain = Column(LargeBinary, nullable=True)
    chain_data = Column(Text, nullable=True)  # JSON chain data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Recovery metadata
    recovery_attempts = Column(Integer, default=0)
    last_recovery_at = Column(DateTime, nullable=True)
    
    # Configuration
    retry_config = Column(Text, nullable=True)  # JSON
    callbacks_config = Column(Text, nullable=True)  # JSON
    
    def serialize_chain_data(self, chain: JobChain) -> None:
        """Serialize chain data for persistence."""
        try:
            self.serialized_chain = pickle.dumps(chain)
            
            # JSON representation for inspection
            self.chain_data = json.dumps({
                'name': chain.name,
                'status': chain.status.value,
                'current_step': chain.current_step,
                'total_steps': len(chain.steps),
                'steps': [
                    {
                        'name': step.name,
                        'job_type': type(step.job).__name__,
                        'delay': step.delay,
                        'retry_on_failure': step.retry_on_failure,
                        'continue_on_failure': step.continue_on_failure
                    }
                    for step in chain.steps
                ]
            }, default=str)
            
        except Exception as e:
            logging.error(f"Failed to serialize chain {self.chain_id}: {str(e)}")
    
    def deserialize_chain(self) -> Optional[JobChain]:
        """Deserialize chain from persistence."""
        if self.serialized_chain:
            try:
                return pickle.loads(self.serialized_chain)
            except Exception as e:
                logging.error(f"Failed to deserialize chain {self.chain_id}: {str(e)}")
        
        return None


class JobPersistenceManager:
    """Manages job persistence and recovery operations."""
    
    def __init__(self, config: Optional[PersistenceConfig] = None) -> None:
        self.config = config or PersistenceConfig()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self.metrics_collector = get_metrics_collector()
        
        # Database setup
        self.engine = None
        self.session_factory = None
        self._setup_database()
        
        # Recovery tracking
        self.recovery_in_progress: Dict[str, bool] = {}
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        
        # Auto-recovery timer
        self._recovery_timer: Optional[threading.Timer] = None
        if self.config.auto_recovery_enabled:
            self._start_auto_recovery()
    
    def _setup_database(self) -> None:
        """Setup database connection and tables."""
        try:
            # Use existing database connection
            db_session = next(get_database())
            self.engine = db_session.bind
            self.session_factory = sessionmaker(bind=self.engine)
            
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            self.logger.info("Job persistence database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to setup persistence database: {str(e)}")
            raise
    
    def persist_job(
        self,
        job: ShouldQueue,
        job_id: str,
        queue_name: str = "default",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Persist a job for recovery."""
        with self._lock:
            session = self.session_factory()
            try:
                # Check if job already persisted
                existing = session.query(PersistedJob).filter(
                    PersistedJob.job_id == job_id
                ).first()
                
                if existing:
                    self.logger.debug(f"Job {job_id} already persisted, updating...")
                    persisted_job = existing
                else:
                    persisted_job = PersistedJob(job_id=job_id)
                    session.add(persisted_job)
                
                # Update job data
                persisted_job.job_type = type(job).__name__
                persisted_job.queue_name = queue_name
                persisted_job.status = "persisted"
                persisted_job.serialize_job_data(job)
                
                # Add metadata
                if context:
                    persisted_job.context_data = json.dumps(context, default=str)
                if tags:
                    persisted_job.tags = json.dumps(tags)
                
                # Chain information if available
                if hasattr(job, '_chain_id'):
                    persisted_job.chain_id = job._chain_id
                if hasattr(job, '_chain_step'):
                    persisted_job.chain_step = job._chain_step
                
                session.commit()
                
                # Record metrics
                self.metrics_collector.increment_counter("jobs.persisted.total")
                self.metrics_collector.increment_counter(f"jobs.persisted.{queue_name}")
                
                self.logger.info(f"Job {job_id} persisted successfully")
                return persisted_job.id
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to persist job {job_id}: {str(e)}")
                raise
            finally:
                session.close()
    
    def persist_chain(
        self,
        chain: JobChain,
        chain_id: str
    ) -> str:
        """Persist a job chain for recovery."""
        with self._lock:
            session = self.session_factory()
            try:
                # Check if chain already persisted
                existing = session.query(PersistedChain).filter(
                    PersistedChain.chain_id == chain_id
                ).first()
                
                if existing:
                    persisted_chain = existing
                else:
                    persisted_chain = PersistedChain(chain_id=chain_id)
                    session.add(persisted_chain)
                
                # Update chain data
                persisted_chain.name = chain.name or "Unnamed Chain"
                persisted_chain.status = chain.status.value
                persisted_chain.current_step = chain.current_step
                persisted_chain.total_steps = len(chain.steps)
                persisted_chain.serialize_chain_data(chain)
                
                # Store retry configuration
                if chain.retry_config:
                    persisted_chain.retry_config = json.dumps({
                        'strategy': chain.retry_config.strategy.value,
                        'base_delay': chain.retry_config.base_delay,
                        'max_delay': chain.retry_config.max_delay,
                        'multiplier': chain.retry_config.multiplier,
                        'jitter': chain.retry_config.jitter,
                        'max_retries': chain.retry_config.max_retries
                    })
                
                session.commit()
                
                # Record metrics
                self.metrics_collector.increment_counter("chains.persisted.total")
                
                self.logger.info(f"Chain {chain_id} persisted successfully")
                return persisted_chain.id
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to persist chain {chain_id}: {str(e)}")
                raise
            finally:
                session.close()
    
    def mark_job_failed(
        self,
        job_id: str,
        error_message: str,
        error_type: str,
        stack_trace: Optional[str] = None
    ) -> bool:
        """Mark a persisted job as failed."""
        session = self.session_factory()
        try:
            persisted_job = session.query(PersistedJob).filter(
                PersistedJob.job_id == job_id
            ).first()
            
            if not persisted_job:
                return False
            
            persisted_job.status = "failed"
            persisted_job.failed_at = datetime.now()
            persisted_job.error_message = error_message
            persisted_job.error_type = error_type
            persisted_job.stack_trace = stack_trace
            persisted_job.attempts += 1
            
            session.commit()
            
            self.metrics_collector.increment_counter("jobs.failed_persisted.total")
            
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to mark job {job_id} as failed: {str(e)}")
            return False
        finally:
            session.close()
    
    def mark_job_completed(self, job_id: str) -> bool:
        """Mark a persisted job as completed."""
        session = self.session_factory()
        try:
            persisted_job = session.query(PersistedJob).filter(
                PersistedJob.job_id == job_id
            ).first()
            
            if not persisted_job:
                return False
            
            persisted_job.status = "completed"
            persisted_job.completed_at = datetime.now()
            
            session.commit()
            
            self.metrics_collector.increment_counter("jobs.completed_persisted.total")
            
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to mark job {job_id} as completed: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_failed_jobs(
        self,
        limit: int = 100,
        queue_name: Optional[str] = None,
        job_type: Optional[str] = None
    ) -> List[PersistedJob]:
        """Get failed jobs for recovery."""
        session = self.session_factory()
        try:
            query = session.query(PersistedJob).filter(
                PersistedJob.status == "failed"
            )
            
            if queue_name:
                query = query.filter(PersistedJob.queue_name == queue_name)
            
            if job_type:
                query = query.filter(PersistedJob.job_type == job_type)
            
            # Order by failed_at to process oldest first
            query = query.order_by(PersistedJob.failed_at.asc())
            
            return query.limit(limit).all()
            
        finally:
            session.close()
    
    def get_recoverable_jobs(self) -> List[PersistedJob]:
        """Get jobs that are eligible for recovery."""
        session = self.session_factory()
        try:
            # Get jobs that failed and haven't exceeded max recovery attempts
            query = session.query(PersistedJob).filter(
                PersistedJob.status == "failed",
                PersistedJob.recovery_attempts < self.config.max_recovery_attempts
            )
            
            # Apply recovery delay if configured
            if self.config.recovery_strategy == RecoveryStrategy.DELAYED:
                cutoff_time = datetime.now() - timedelta(
                    seconds=self.config.recovery_delay_seconds
                )
                query = query.filter(PersistedJob.failed_at < cutoff_time)
            
            return query.order_by(PersistedJob.failed_at.asc()).all()
            
        finally:
            session.close()
    
    def recover_job(self, job_id: str) -> bool:
        """Recover a specific failed job."""
        with self._lock:
            if job_id in self.recovery_in_progress:
                self.logger.warning(f"Job {job_id} recovery already in progress")
                return False
            
            self.recovery_in_progress[job_id] = True
            
            try:
                session = self.session_factory()
                try:
                    persisted_job = session.query(PersistedJob).filter(
                        PersistedJob.job_id == job_id
                    ).first()
                    
                    if not persisted_job:
                        self.logger.error(f"Persisted job {job_id} not found")
                        return False
                    
                    if persisted_job.recovery_attempts >= self.config.max_recovery_attempts:
                        self.logger.warning(f"Job {job_id} has exceeded max recovery attempts")
                        return False
                    
                    # Deserialize the job
                    job = persisted_job.deserialize_job()
                    if not job:
                        self.logger.error(f"Failed to deserialize job {job_id}")
                        return False
                    
                    # Update recovery metadata
                    persisted_job.recovery_attempts += 1
                    persisted_job.last_recovery_at = datetime.now()
                    persisted_job.status = "recovering"
                    
                    session.commit()
                    
                    # Re-queue the job
                    from app.Services.QueueService import QueueService
                    db = next(get_database())
                    queue_service = QueueService(db)
                    
                    recovered_job_id = queue_service.push(job, persisted_job.queue_name)
                    
                    # Update status to recovered
                    persisted_job.status = "recovered"
                    session.commit()
                    
                    # Record metrics
                    self.metrics_collector.increment_counter("jobs.recovered.total")
                    self.metrics_collector.increment_counter(f"jobs.recovered.{persisted_job.queue_name}")
                    
                    self.logger.info(f"Job {job_id} recovered successfully as {recovered_job_id}")
                    
                    # Execute recovery callbacks
                    if job_id in self.recovery_callbacks:
                        for callback in self.recovery_callbacks[job_id]:
                            try:
                                callback(job_id, True, None)
                            except Exception as e:
                                self.logger.error(f"Recovery callback failed: {str(e)}")
                    
                    return True
                    
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Failed to recover job {job_id}: {str(e)}")
                    
                    # Execute error callbacks
                    if job_id in self.recovery_callbacks:
                        for callback in self.recovery_callbacks[job_id]:
                            try:
                                callback(job_id, False, str(e))
                            except Exception as callback_error:
                                self.logger.error(f"Recovery callback failed: {str(callback_error)}")
                    
                    return False
                finally:
                    session.close()
                    
            finally:
                if job_id in self.recovery_in_progress:
                    del self.recovery_in_progress[job_id]
    
    def recover_failed_jobs(
        self,
        limit: int = 10,
        queue_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recover multiple failed jobs."""
        recoverable_jobs = self.get_recoverable_jobs()
        
        if queue_name:
            recoverable_jobs = [
                job for job in recoverable_jobs 
                if job.queue_name == queue_name
            ]
        
        if limit:
            recoverable_jobs = recoverable_jobs[:limit]
        
        results = {
            "attempted": len(recoverable_jobs),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for persisted_job in recoverable_jobs:
            try:
                if self.recover_job(persisted_job.job_id):
                    results["successful"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Job {persisted_job.job_id}: {str(e)}")
        
        self.logger.info(
            f"Recovery batch completed: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['attempted']} attempted"
        )
        
        return results
    
    def _start_auto_recovery(self) -> None:
        """Start automatic recovery timer."""
        def recovery_task():
            try:
                if self.config.auto_recovery_enabled:
                    self.recover_failed_jobs(limit=5)  # Recover up to 5 jobs at a time
            except Exception as e:
                self.logger.error(f"Auto-recovery task failed: {str(e)}")
            finally:
                # Reschedule
                if self.config.auto_recovery_enabled:
                    self._recovery_timer = threading.Timer(
                        self.config.recovery_delay_seconds,
                        recovery_task
                    )
                    self._recovery_timer.daemon = True
                    self._recovery_timer.start()
        
        self._recovery_timer = threading.Timer(
            self.config.recovery_delay_seconds,
            recovery_task
        )
        self._recovery_timer.daemon = True
        self._recovery_timer.start()
        
        self.logger.info("Auto-recovery timer started")
    
    def register_recovery_callback(
        self,
        job_id: str,
        callback: Callable[[str, bool, Optional[str]], None]
    ) -> None:
        """Register a callback for job recovery events."""
        if job_id not in self.recovery_callbacks:
            self.recovery_callbacks[job_id] = []
        self.recovery_callbacks[job_id].append(callback)
    
    def cleanup_old_records(self, days: int = None) -> int:
        """Clean up old persistence records."""
        days = days or self.config.retention_days
        cutoff_date = datetime.now() - timedelta(days=days)
        
        session = self.session_factory()
        try:
            # Clean up completed jobs older than retention period
            deleted_jobs = session.query(PersistedJob).filter(
                PersistedJob.status == "completed",
                PersistedJob.completed_at < cutoff_date
            ).delete()
            
            # Clean up completed chains
            deleted_chains = session.query(PersistedChain).filter(
                PersistedChain.status == "completed",
                PersistedChain.completed_at < cutoff_date
            ).delete()
            
            session.commit()
            
            total_deleted = deleted_jobs + deleted_chains
            self.logger.info(f"Cleaned up {total_deleted} old persistence records")
            
            return total_deleted
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to cleanup old records: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_persistence_stats(self) -> Dict[str, Any]:
        """Get persistence system statistics."""
        session = self.session_factory()
        try:
            stats = {}
            
            # Job statistics
            job_stats = session.query(PersistedJob.status).all()
            job_counts = {}
            for status, in job_stats:
                job_counts[status] = job_counts.get(status, 0) + 1
            
            stats["jobs"] = {
                "total": len(job_stats),
                "by_status": job_counts
            }
            
            # Chain statistics  
            chain_stats = session.query(PersistedChain.status).all()
            chain_counts = {}
            for status, in chain_stats:
                chain_counts[status] = chain_counts.get(status, 0) + 1
            
            stats["chains"] = {
                "total": len(chain_stats),
                "by_status": chain_counts
            }
            
            # System info
            stats["system"] = {
                "auto_recovery_enabled": self.config.auto_recovery_enabled,
                "recovery_strategy": self.config.recovery_strategy.value,
                "retention_days": self.config.retention_days,
                "max_recovery_attempts": self.config.max_recovery_attempts,
                "recovery_in_progress": len(self.recovery_in_progress)
            }
            
            return stats
            
        finally:
            session.close()
    
    def stop_auto_recovery(self) -> None:
        """Stop automatic recovery."""
        if self._recovery_timer:
            self._recovery_timer.cancel()
            self.config.auto_recovery_enabled = False
            self.logger.info("Auto-recovery stopped")


# Global persistence manager instance
_persistence_manager: Optional[JobPersistenceManager] = None


def get_persistence_manager(config: Optional[PersistenceConfig] = None) -> JobPersistenceManager:
    """Get the global persistence manager instance."""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = JobPersistenceManager(config)
    return _persistence_manager


# Decorator for automatic job persistence
def persist_job(
    auto_recover: bool = True,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
):
    """
    Decorator for automatic job persistence.
    
    Args:
        auto_recover: Whether to enable automatic recovery for this job
        context: Additional context data to store
        tags: Tags for categorizing the job
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            persistence_manager = get_persistence_manager()
            
            # Generate job ID
            job_id = f"{func.__name__}_{int(time.time())}_{hash(str(args) + str(kwargs))}"
            
            try:
                # Create a minimal job representation for persistence
                # This would need to be expanded based on your job structure
                class PersistentJobWrapper(ShouldQueue):
                    def __init__(self, func, args, kwargs):
                        super().__init__()
                        self.func_name = func.__name__
                        self.func_module = func.__module__
                        self.args = args
                        self.kwargs = kwargs
                    
                    def handle(self):
                        # This would need proper implementation
                        pass
                
                job_wrapper = PersistentJobWrapper(func, args, kwargs)
                
                # Persist the job
                persistence_manager.persist_job(
                    job=job_wrapper,
                    job_id=job_id,
                    context=context,
                    tags=tags
                )
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Mark as completed
                persistence_manager.mark_job_completed(job_id)
                
                return result
                
            except Exception as e:
                # Mark as failed
                import traceback
                persistence_manager.mark_job_failed(
                    job_id=job_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    stack_trace=traceback.format_exc()
                )
                raise
        
        return wrapper
    return decorator