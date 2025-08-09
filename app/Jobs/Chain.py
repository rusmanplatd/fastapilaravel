from __future__ import annotations

import json
from typing import List, Dict, Any, Optional, Callable, Union, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from app.Jobs.Job import ShouldQueue
from config.database import get_database

if TYPE_CHECKING:
    from database.migrations.create_jobs_table import Job as JobModel


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
    
    def dispatch(self, queue: Optional[str] = None) -> str:
        """Dispatch the job chain."""
        if not self.steps:
            raise ValueError("Cannot dispatch empty job chain")
        
        self.chain_id = self._create_chain_record()
        self.status = ChainStatus.RUNNING
        
        # Start with first job
        self._dispatch_step(0, queue)
        
        return self.chain_id
    
    def _dispatch_step(self, step_index: int, queue: Optional[str] = None) -> None:
        """Dispatch a specific step in the chain."""
        if step_index >= len(self.steps):
            self._complete_chain()
            return
        
        step = self.steps[step_index]
        
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
        
        if success:
            # Move to next step
            next_step = step_index + 1
            if next_step < len(self.steps):
                self._dispatch_step(next_step)
            else:
                self._complete_chain()
        else:
            # Handle failure
            if step.continue_on_failure:
                # Continue to next step despite failure
                next_step = step_index + 1
                if next_step < len(self.steps):
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
        
        if self.on_success_callback:
            try:
                self.on_success_callback()
            except Exception as e:
                print(f"Chain success callback error: {str(e)}")
    
    def _fail_chain(self, error: Optional[Exception] = None) -> None:
        """Fail the job chain."""
        self.status = ChainStatus.FAILED
        self._update_chain_record()
        
        if self.on_failure_callback and error:
            try:
                self.on_failure_callback(error)
            except Exception as e:
                print(f"Chain failure callback error: {str(e)}")
    
    def _create_chain_record(self) -> str:
        """Create chain record for tracking."""
        # For now, just return a generated ID
        # In production, you might store chain state in database
        import uuid
        return str(uuid.uuid4())
    
    def _update_chain_record(self) -> None:
        """Update chain record with current status."""
        # Implementation would update database record
        pass


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
        
        # In a full implementation, this would look up the chain
        # and call handle_step_completion
        print(f"Chain step {self.chain_step()} {'completed' if success else 'failed'}")


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
        """Override this method instead of handle() for chainable jobs."""
        raise NotImplementedError("Chainable jobs must implement _handle()")


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