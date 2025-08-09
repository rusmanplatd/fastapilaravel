from __future__ import annotations

import json
from typing import List, Dict, Any, Optional, Callable, Union, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from app.Jobs.Job import ShouldQueue
from app.Jobs.RetryManager import get_retry_manager, BackoffConfig, RetryStrategy
from app.Jobs.MetricsCollector import get_metrics_collector, JobPhase
from config.database import get_database

if TYPE_CHECKING:
    from app.Models.Job import Job as JobModel


class ChainStatus(Enum):
    """Status of job chain execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ChainStep:
    """Represents a step in a job chain."""
    job: ShouldQueue
    name: Optional[str] = None
    delay: int = 0  # Delay before executing this step
    retry_on_failure: bool = True
    continue_on_failure: bool = False


class JobChain:
    """
    Job chaining system that executes jobs sequentially.
    Similar to Laravel's job chaining functionality.
    """
    
    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or f"Chain-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.steps: List[ChainStep] = []
        self.chain_id: Optional[str] = None
        self.current_step: int = 0
        self.status = ChainStatus.PENDING
        
        # Callbacks
        self.on_success_callback: Optional[Callable[[], None]] = None
        self.on_failure_callback: Optional[Callable[[Exception], None]] = None
        self.on_step_callback: Optional[Callable[[int, ChainStep], None]] = None
        
        # Retry configuration
        self.retry_config: Optional[BackoffConfig] = None
        self.step_retry_configs: Dict[int, BackoffConfig] = {}
    
    def add(self, job: ShouldQueue, name: Optional[str] = None, delay: int = 0) -> JobChain:
        """Add a job to the chain."""
        step = ChainStep(job=job, name=name, delay=delay)
        self.steps.append(step)
        return self
    
    def then(self, job: ShouldQueue, name: Optional[str] = None, delay: int = 0) -> JobChain:
        """Add a job to execute after previous job completes (alias for add)."""
        return self.add(job, name, delay)
    
    def retry_step_on_failure(self, retry: bool = True) -> JobChain:
        """Set retry behavior for the last added step."""
        if self.steps:
            self.steps[-1].retry_on_failure = retry
        return self
    
    def continue_on_failure(self, continue_chain: bool = True) -> JobChain:
        """Allow chain to continue even if last step fails."""
        if self.steps:
            self.steps[-1].continue_on_failure = continue_chain
        return self
    
    def on_success(self, callback: Callable[[], None]) -> JobChain:
        """Set success callback for entire chain."""
        self.on_success_callback = callback
        return self
    
    def on_failure(self, callback: Callable[[Exception], None]) -> JobChain:
        """Set failure callback for entire chain."""
        self.on_failure_callback = callback
        return self
    
    def on_step(self, callback: Callable[[int, ChainStep], None]) -> JobChain:
        """Set callback executed before each step."""
        self.on_step_callback = callback
        return self
    
    def with_retry(
        self,
        max_retries: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ) -> JobChain:
        """Configure retry settings for the entire chain."""
        self.retry_config = BackoffConfig(
            strategy=strategy,
            base_delay=base_delay,
            max_delay=max_delay,
            multiplier=multiplier,
            jitter=jitter,
            max_retries=max_retries
        )
        return self
    
    def with_step_retry(
        self,
        step_index: int,
        max_retries: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ) -> JobChain:
        """Configure retry settings for a specific step."""
        self.step_retry_configs[step_index] = BackoffConfig(
            strategy=strategy,
            base_delay=base_delay,
            max_delay=max_delay,
            multiplier=multiplier,
            jitter=jitter,
            max_retries=max_retries
        )
        return self
    
    def dispatch(self, queue: Optional[str] = None) -> str:
        """Dispatch the job chain."""
        if not self.steps:
            raise ValueError("Cannot dispatch empty job chain")
        
        self.chain_id = self._create_chain_record()
        self.status = ChainStatus.RUNNING
        
        # Register chain in registry for step completion tracking
        from app.Jobs.ChainRegistry import ChainRegistry
        registry = ChainRegistry.get_instance()
        registry.register_chain(self.chain_id, self)
        
        # Record chain metrics
        metrics_collector = get_metrics_collector()
        metrics_collector.record_job_queued(
            job_id=self.chain_id,
            job_type="job_chain",
            queue_name=queue or "default",
            tags={
                "chain_name": self.name,
                "total_steps": str(len(self.steps)),
                "has_retry_config": str(self.retry_config is not None)
            }
        )
        
        # Start with first job
        self._dispatch_step(0, queue)
        
        return self.chain_id
    
    def _dispatch_step(self, step_index: int, queue: Optional[str] = None) -> None:
        """Dispatch a specific step in the chain."""
        if step_index >= len(self.steps):
            self._complete_chain()
            return
        
        step = self.steps[step_index]
        
        # Record step metrics
        metrics_collector = get_metrics_collector()
        step_job_id = f"{self.chain_id}_step_{step_index}"
        metrics_collector.record_job_queued(
            job_id=step_job_id,
            job_type=type(step.job).__name__,
            queue_name=queue or "default",
            tags={
                "chain_id": self.chain_id,
                "chain_name": self.name,
                "step_index": str(step_index),
                "step_name": step.name or f"Step_{step_index}",
                "has_delay": str(step.delay > 0),
                "continue_on_failure": str(step.continue_on_failure)
            }
        )
        
        # Execute step callback
        if self.on_step_callback:
            self.on_step_callback(step_index, step)
        
        # Add chain metadata to job
        step.job._chain_id = self.chain_id  # type: ignore
        step.job._chain_step = step_index  # type: ignore
        
        # Dispatch job with delay
        if step.delay > 0:
            step.job.delay_until(step.delay)
        
        from app.Services.QueueService import QueueService
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        queue_service.push(step.job, queue)
    
    def handle_step_completion(self, step_index: int, success: bool, error: Optional[Exception] = None) -> None:
        """Handle completion of a chain step."""
        if step_index >= len(self.steps):
            return
        
        step = self.steps[step_index]
        
        # Record step completion metrics
        metrics_collector = get_metrics_collector()
        step_job_id = f"{self.chain_id}_step_{step_index}"
        
        metrics_collector.record_job_completed(
            job_id=step_job_id,
            success=success,
            error_message=str(error) if error else None,
            error_type=type(error).__name__ if error else None,
            custom_metrics={
                "step_index": step_index,
                "continue_on_failure": step.continue_on_failure
            }
        )
        
        if success:
            # Clear any retry record for this step
            retry_manager = get_retry_manager()
            retry_manager.clear_retry_record(step_job_id)
            
            # Move to next step
            next_step = step_index + 1
            if next_step < len(self.steps):
                self.current_step = next_step
                self._dispatch_step(next_step)
            else:
                self._complete_chain()
        else:
            # Handle failure with retry logic
            if self._should_retry_step(step_index, error):
                # Record retry attempt
                retry_manager = get_retry_manager()
                retry_info = retry_manager.get_retry_info(step_job_id)
                if retry_info:
                    metrics_collector.record_job_retry(step_job_id, retry_info.current_attempt)
                
                self._retry_step(step_index, error)
            elif step.continue_on_failure:
                # Continue to next step despite failure
                next_step = step_index + 1
                if next_step < len(self.steps):
                    self.current_step = next_step
                    self._dispatch_step(next_step)
                else:
                    self._complete_chain()
            else:
                # Fail entire chain
                self._fail_chain(error)
    
    def _complete_chain(self) -> None:
        """Complete the job chain successfully."""
        self.status = ChainStatus.COMPLETED
        self._update_chain_record()
        
        # Record chain completion metrics
        if self.chain_id:
            metrics_collector = get_metrics_collector()
            metrics_collector.record_job_completed(
                job_id=self.chain_id,
                success=True,
                custom_metrics={
                    "total_steps": len(self.steps),
                    "completed_steps": len(self.steps),
                    "chain_name": self.name
                }
            )
        
        # Unregister from registry
        if self.chain_id:
            from app.Jobs.ChainRegistry import ChainRegistry
            registry = ChainRegistry.get_instance()
            registry.unregister_chain(self.chain_id)
        
        if self.on_success_callback:
            try:
                self.on_success_callback()
            except Exception as e:
                import logging
                logging.error(f"Chain success callback error: {str(e)}")
    
    def _fail_chain(self, error: Optional[Exception] = None) -> None:
        """Fail the job chain."""
        self.status = ChainStatus.FAILED
        self._update_chain_record()
        
        # Record chain failure metrics
        if self.chain_id:
            metrics_collector = get_metrics_collector()
            metrics_collector.record_job_completed(
                job_id=self.chain_id,
                success=False,
                error_message=str(error) if error else "Chain failed",
                error_type=type(error).__name__ if error else "ChainFailure",
                custom_metrics={
                    "total_steps": len(self.steps),
                    "completed_steps": self.current_step,
                    "failed_at_step": self.current_step,
                    "chain_name": self.name
                }
            )
        
        # Unregister from registry
        if self.chain_id:
            from app.Jobs.ChainRegistry import ChainRegistry
            registry = ChainRegistry.get_instance()
            registry.unregister_chain(self.chain_id)
        
        if self.on_failure_callback and error:
            try:
                self.on_failure_callback(error)
            except Exception as e:
                import logging
                logging.error(f"Chain failure callback error: {str(e)}")
    
    def _should_retry_step(self, step_index: int, error: Optional[Exception]) -> bool:
        """Check if a step should be retried."""
        if not error:
            return False
        
        # Get retry configuration for this step
        config = self.step_retry_configs.get(step_index, self.retry_config)
        if not config:
            return False
        
        retry_manager = get_retry_manager()
        step_job_id = f"{self.chain_id}_step_{step_index}"
        
        return retry_manager.should_retry(step_job_id, error)
    
    def _retry_step(self, step_index: int, error: Exception) -> None:
        """Retry a failed step."""
        retry_manager = get_retry_manager()
        step_job_id = f"{self.chain_id}_step_{step_index}"
        
        def retry_callback():
            """Callback to execute the retry."""
            try:
                self._dispatch_step(step_index)
            except Exception as retry_error:
                # If retry also fails, handle completion with failure
                self.handle_step_completion(step_index, False, retry_error)
        
        delay = retry_manager.schedule_retry(step_job_id, error, retry_callback)
        
        if delay is not None:
            # Schedule the retry
            import threading
            retry_timer = threading.Timer(delay, retry_callback)
            retry_timer.start()
            
            import logging
            logging.info(f"Chain {self.chain_id} step {step_index} scheduled for retry in {delay:.2f} seconds")
        else:
            # No more retries, proceed with failure handling
            step = self.steps[step_index]
            if step.continue_on_failure:
                next_step = step_index + 1
                if next_step < len(self.steps):
                    self.current_step = next_step
                    self._dispatch_step(next_step)
                else:
                    self._complete_chain()
            else:
                self._fail_chain(error)
    
    def _create_chain_record(self) -> str:
        """Create chain record for tracking."""
        # For now, just return a generated ID
        # In production, you might store chain state in database
        import uuid
        return str(uuid.uuid4())
    
    def _update_chain_record(self) -> None:
        """Update chain record with current status."""
        try:
            from app.Models.JobBatch import JobBatch
            from config.database import get_database
            
            if not self.name or not self.chain_id:
                return
                
            db = next(get_database())
            
            try:
                # Find or create chain record (using batch table for simplicity)
                chain_record = db.query(JobBatch).filter(JobBatch.name == self.name).first()
                if not chain_record:
                    # Create new chain record
                    chain_record = JobBatch(
                        name=self.name,
                        total_jobs=len(self.steps),
                        pending_jobs=0 if self.status == ChainStatus.COMPLETED else len(self.steps) - self.current_step,
                        failed_jobs=1 if self.status == ChainStatus.FAILED else 0,
                        processed_jobs=self.current_step,
                        created_at=datetime.now(),
                        finished_at=datetime.now() if self.status in [ChainStatus.COMPLETED, ChainStatus.FAILED] else None
                    )
                    db.add(chain_record)
                else:
                    # Update existing record
                    completed_steps = self.current_step
                    chain_record.total_jobs = len(self.steps)
                    chain_record.processed_jobs = completed_steps
                    chain_record.pending_jobs = max(0, len(self.steps) - completed_steps)
                    chain_record.failed_jobs = 1 if self.status == ChainStatus.FAILED else 0
                    chain_record.finished_at = datetime.now() if self.status in [ChainStatus.COMPLETED, ChainStatus.FAILED] else None
                
                db.commit()
                
            except Exception as db_error:
                db.rollback()
                raise db_error
            finally:
                db.close()
                
        except Exception as e:
            # Use proper logging in production
            import logging
            logging.error(f"Error updating chain record for '{self.name}': {str(e)}")


class Chainable:
    """
    Mixin for jobs that can be part of a chain.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._chain_id: Optional[str] = None
        self._chain_step: Optional[int] = None
    
    def chain_id(self) -> Optional[str]:
        """Get the chain ID this job belongs to."""
        return getattr(self, '_chain_id', None)
    
    def chain_step(self) -> Optional[int]:
        """Get the step index in the chain."""
        return getattr(self, '_chain_step', None)
    
    def is_chained(self) -> bool:
        """Check if this job is part of a chain."""
        return self.chain_id() is not None
    
    def notify_chain_step_completed(self, success: bool = True, error: Optional[Exception] = None) -> None:
        """Notify chain that this step completed."""
        if not self.is_chained():
            return
        
        try:
            # In a production implementation, this would use a proper chain registry
            # or message queue to notify the chain coordinator
            chain_id = self.chain_id()
            step_index = self.chain_step()
            
            # For now, use a simple registry pattern
            from app.Jobs.ChainRegistry import ChainRegistry
            registry = ChainRegistry.get_instance()
            chain_instance = registry.get_chain(chain_id)
            
            if chain_instance:
                chain_instance.handle_step_completion(step_index, success, error)
            else:
                # Log missing chain for debugging
                import logging
                logging.warning(f"Chain {chain_id} not found in registry for step {step_index}")
                
        except Exception as e:
            # Don't fail the job if chain notification fails
            import logging
            logging.error(f"Failed to notify chain step completion: {str(e)}")


class ChainableJob(ShouldQueue, Chainable):
    """
    Base class for jobs that support chaining.
    """
    
    def __init__(self) -> None:
        ShouldQueue.__init__(self)
        Chainable.__init__(self)
    
    def handle(self) -> None:
        """Handle the job with chain notification."""
        try:
            self._handle()
            self.notify_chain_step_completed(success=True)
        except Exception as e:
            self.notify_chain_step_completed(success=False, error=e)
            raise
    
    def _handle(self) -> None:
        """
        Override this method for custom job logic in chainable jobs.
        Default implementation calls the regular handle() method if it exists.
        """
        # Try to call the original handle method if it exists and is different from this one
        if hasattr(self, 'handle') and callable(getattr(self, 'handle')):
            original_handle = getattr(self.__class__.__bases__[0], 'handle', None)
            if original_handle and original_handle != self.__class__.handle:
                original_handle(self)
            else:
                # If no custom handle method, this is a placeholder that should be overridden
                pass


class ConditionalChain:
    """
    Advanced chain that supports conditional execution and branching.
    """
    
    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name
        self.conditions: Dict[int, Callable[[Any], bool]] = {}
        self.branches: Dict[int, List[ShouldQueue]] = {}
        self.chain = JobChain(name)
    
    def when(self, condition: Callable[[Any], bool]) -> ConditionalChain:
        """Add condition for the next job."""
        step_index = len(self.chain.steps)
        self.conditions[step_index] = condition
        return self
    
    def branch(self, jobs: List[ShouldQueue]) -> ConditionalChain:
        """Add branch jobs for conditional execution."""
        step_index = len(self.chain.steps) - 1
        self.branches[step_index] = jobs
        return self
    
    def then(self, job: ShouldQueue, name: Optional[str] = None, delay: int = 0) -> ConditionalChain:
        """Add job to chain with conditional support."""
        self.chain.add(job, name, delay)
        return self


class ParallelChain:
    """
    Chain that can execute jobs in parallel at certain steps.
    """
    
    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name
        self.steps: List[Union[ShouldQueue, List[ShouldQueue]]] = []
    
    def add(self, job: ShouldQueue) -> ParallelChain:
        """Add single job to chain."""
        self.steps.append(job)
        return self
    
    def add_parallel(self, jobs: List[ShouldQueue]) -> ParallelChain:
        """Add parallel jobs to chain."""
        self.steps.append(jobs)
        return self
    
    def dispatch(self, queue: Optional[str] = None) -> List[str]:
        """Dispatch parallel chain."""
        from app.Jobs.Batch import batch
        job_ids = []
        
        for step in self.steps:
            if isinstance(step, list):
                # Parallel execution
                batch_id = batch(step).name(f"{self.name}-Parallel").dispatch(queue)
                job_ids.append(batch_id)
            else:
                # Sequential execution
                from app.Services.QueueService import QueueService
                from config.database import get_database
                db = next(get_database())
                queue_service = QueueService(db)
                job_id = queue_service.push(step, queue)
                job_ids.append(job_id)
        
        return job_ids


def chain(jobs: List[ShouldQueue], name: Optional[str] = None) -> JobChain:
    """
    Create a new job chain.
    
    Usage:
        chain([
            ProcessOrderJob(order_id),
            SendEmailJob(email, subject, body),
            UpdateInventoryJob(product_id)
        ]).name("Order Processing").dispatch()
    """
    job_chain = JobChain(name)
    for job in jobs:
        job_chain.add(job)
    return job_chain