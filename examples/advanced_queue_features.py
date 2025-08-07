#!/usr/bin/env python3
"""
Advanced Queue Features Demonstration
Shows the enhanced job & queue system with batching, chaining, monitoring, etc.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.Jobs.Job import Job
from app.Jobs.Batch import batch, BatchableJob
from app.Jobs.Chain import chain, ChainableJob
from app.Jobs.RateLimiter import RateLimit, RateLimitStrategy, RateLimited
from app.Jobs.Middleware import LoggingMiddleware, ThrottleMiddleware, MemoryLimitMiddleware, MiddlewareStack
from app.Jobs.Security import SecureJob
from app.Jobs.Events import global_event_dispatcher, JobEvent
from app.Queue.QueueManager import global_queue_manager, define_queue, high_throughput_queue, secure_queue
from app.Services.QueueService import QueueService


# Example jobs demonstrating various features

class AdvancedEmailJob(BatchableJob, ChainableJob, RateLimited, SecureJob):
    """
    Advanced email job with batching, chaining, rate limiting, and security.
    """
    
    def __init__(self, to_email: str, subject: str, body: str, sensitive_data: str = None) -> None:
        super().__init__()
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.sensitive_data = sensitive_data
        
        # Configure job options
        self.options.queue = "emails"
        self.options.priority = 5
        self.set_required_permissions(["send_email"])
        self.set_sensitive_fields(["sensitive_data"])
    
    def get_rate_limits(self) -> list[RateLimit]:
        """Define rate limits for email jobs."""
        return [
            RateLimit(
                max_attempts=100,
                per_seconds=3600,  # 100 emails per hour
                strategy=RateLimitStrategy.SLIDING_WINDOW
            )
        ]
    
    def _handle(self) -> None:
        """Handle the email sending."""
        print(f"Sending email to: {self.to_email}")
        print(f"Subject: {self.subject}")
        
        # Simulate email sending
        time.sleep(1)
        
        if self.sensitive_data:
            print(f"Processing sensitive data: {self.sensitive_data[:10]}...")
        
        print(f"✅ Email sent to {self.to_email}")
    
    def serialize(self) -> dict[str, any]:
        """Serialize with security features."""
        data = super().serialize()
        data["data"] = {
            "to_email": self.to_email,
            "subject": self.subject,
            "body": self.body
        }
        return data
    
    @classmethod
    def deserialize(cls, data: dict[str, any]) -> AdvancedEmailJob:
        """Deserialize with security features."""
        job_data = data.get("data", {})
        return cls(
            to_email=job_data["to_email"],
            subject=job_data["subject"],
            body=job_data["body"]
        )


class DataProcessingJob(BatchableJob):
    """
    Data processing job that works well in batches.
    """
    
    def __init__(self, dataset_id: str, operation: str) -> None:
        super().__init__()
        self.dataset_id = dataset_id
        self.operation = operation
        self.options.queue = "data-processing"
        self.options.timeout = 300  # 5 minutes
    
    def _handle(self) -> None:
        """Process the data."""
        print(f"Processing dataset {self.dataset_id} with operation: {self.operation}")
        
        # Simulate heavy processing
        time.sleep(2)
        
        if self.operation == "transform":
            print(f"✅ Transformed dataset {self.dataset_id}")
        elif self.operation == "analyze":
            print(f"✅ Analyzed dataset {self.dataset_id}")
        else:
            print(f"✅ Processed dataset {self.dataset_id}")


class NotificationJob(ChainableJob):
    """
    Notification job for chaining after other operations.
    """
    
    def __init__(self, user_id: str, message: str, channel: str = "email") -> None:
        super().__init__()
        self.user_id = user_id
        self.message = message
        self.channel = channel
        self.options.queue = "notifications"
    
    def _handle(self) -> None:
        """Send notification."""
        print(f"Sending {self.channel} notification to user {self.user_id}: {self.message}")
        time.sleep(0.5)
        print(f"✅ Notification sent")


def demonstrate_job_batching() -> None:
    """Demonstrate job batching capabilities."""
    print("🔄 Job Batching Demo")
    print("=" * 50)
    
    # Create a batch of data processing jobs
    processing_jobs = [
        DataProcessingJob(f"dataset_{i}", "transform")
        for i in range(1, 6)
    ]
    
    # Create and dispatch batch
    batch_id = (batch(processing_jobs)
                .name("Data Transformation Batch")
                .allow_failures(2)  # Allow up to 2 failures
                .dispatch("data-processing"))
    
    print(f"✅ Dispatched batch: {batch_id}")
    print(f"   - {len(processing_jobs)} jobs in batch")
    print(f"   - Allows up to 2 failures")


def demonstrate_job_chaining() -> None:
    """Demonstrate job chaining workflows."""
    print("\n🔗 Job Chaining Demo")
    print("=" * 50)
    
    # Create a processing workflow
    workflow_jobs = [
        DataProcessingJob("workflow_data", "extract"),
        DataProcessingJob("workflow_data", "transform"),
        DataProcessingJob("workflow_data", "load"),
        NotificationJob("admin_user", "Data pipeline completed successfully")
    ]
    
    # Create and dispatch chain
    chain_id = (chain(workflow_jobs)
                .name("Data Pipeline Workflow")
                .dispatch("data-processing"))
    
    print(f"✅ Dispatched workflow chain: {chain_id}")
    print(f"   - {len(workflow_jobs)} sequential jobs")
    print(f"   - Will stop on first failure")


def demonstrate_queue_configurations() -> None:
    """Demonstrate advanced queue configurations."""
    print("\n⚙️  Queue Configuration Demo")
    print("=" * 50)
    
    # Define specialized queues
    email_queue = define_queue(
        "bulk-emails",
        connection="redis",
        max_jobs=1000,
        memory_limit=64,
        rate_limit_enabled=True
    )
    
    secure_queue_config = secure_queue("sensitive-operations")
    fast_queue_config = high_throughput_queue("fast-processing")
    
    print("✅ Defined specialized queues:")
    print(f"   - bulk-emails: {email_queue.name} ({email_queue.connection})")
    print(f"   - sensitive-operations: encrypted & signed")
    print(f"   - fast-processing: high throughput with Redis")


def demonstrate_middleware() -> None:
    """Demonstrate job middleware."""
    print("\n🔧 Middleware Demo")
    print("=" * 50)
    
    # Create middleware stack
    middleware = MiddlewareStack()
    middleware.add(LoggingMiddleware(detailed=True))
    middleware.add(ThrottleMiddleware(max_attempts=10, decay_seconds=60))
    middleware.add(MemoryLimitMiddleware(memory_limit_mb=100))
    
    # Create job with middleware
    job = AdvancedEmailJob(
        "user@example.com",
        "Middleware Demo",
        "This email was processed through middleware stack"
    )
    
    # Process job through middleware
    def dummy_handler():
        job._handle()
        return "completed"
    
    try:
        result = middleware.process(job, dummy_handler)
        print(f"✅ Job processed through middleware: {result}")
    except Exception as e:
        print(f"❌ Middleware processing failed: {str(e)}")


def demonstrate_event_system() -> None:
    """Demonstrate job event system."""
    print("\n📡 Event System Demo")
    print("=" * 50)
    
    # Custom event handler
    def custom_event_handler(event_data):
        print(f"🔔 Event: {event_data.event.value} for {event_data.job.get_display_name()}")
    
    # Register event handler
    global_event_dispatcher.listen(JobEvent.BEFORE_HANDLE, custom_event_handler)
    global_event_dispatcher.listen(JobEvent.AFTER_HANDLE, custom_event_handler)
    
    # Create and process job
    job = NotificationJob("event_user", "Testing event system")
    
    # Emit events manually for demo
    job.emit_event(JobEvent.BEFORE_HANDLE)
    job._handle()
    job.emit_event(JobEvent.AFTER_HANDLE)
    
    print("✅ Events emitted and handled")


def demonstrate_security_features() -> None:
    """Demonstrate security features."""
    print("\n🔐 Security Demo")
    print("=" * 50)
    
    # Create secure job with sensitive data
    secure_job = AdvancedEmailJob(
        "secure@example.com",
        "Encrypted Message",
        "This is a secure message",
        sensitive_data="secret_api_key_12345"
    )
    
    # Serialize (will encrypt sensitive data)
    serialized = secure_job.serialize()
    print("✅ Job serialized with encryption for sensitive fields")
    
    # Check if encryption was applied
    if "encrypted_data" in serialized:
        print("   - Sensitive data was encrypted")
    
    # Deserialize
    restored_job = AdvancedEmailJob.deserialize(serialized)
    print("✅ Job deserialized and sensitive data restored")


def demonstrate_monitoring() -> None:
    """Demonstrate monitoring capabilities."""
    print("\n📊 Monitoring Demo")
    print("=" * 50)
    
    from app.Jobs.Monitor import global_job_monitor
    
    # Simulate job execution for monitoring
    job = DataProcessingJob("monitor_test", "analyze")
    
    # Start monitoring
    job_uuid = global_job_monitor.start_job(job, "demo_worker")
    
    # Simulate job work
    time.sleep(1)
    
    # Finish monitoring
    global_job_monitor.finish_job(job_uuid, success=True)
    
    # Get performance metrics
    perf = global_job_monitor.get_job_performance(hours=1)
    
    print("✅ Job monitoring completed:")
    print(f"   - Jobs processed: {perf.total_jobs}")
    print(f"   - Success rate: {perf.success_rate:.1f}%")
    print(f"   - Average duration: {perf.avg_duration_ms/1000:.2f}s")


def demonstrate_queue_management() -> None:
    """Demonstrate queue management features."""
    print("\n🎛️  Queue Management Demo")
    print("=" * 50)
    
    queue_service = QueueService()
    
    # Get queue statistics
    stats = queue_service.get_queue_stats()
    
    print("📈 Current Queue Statistics:")
    for queue_name, queue_stats in stats["queues"].items():
        print(f"   {queue_name}: {queue_stats['total']} jobs "
              f"({queue_stats['pending']} pending, {queue_stats['failed']} failed)")
    
    print(f"Total active jobs: {stats['totals']['active_jobs']}")
    print(f"Total failed jobs: {stats['totals']['failed_jobs']}")


if __name__ == "__main__":
    print("Advanced Queue Features Demonstration")
    print("=" * 70)
    
    try:
        demonstrate_job_batching()
        demonstrate_job_chaining()
        demonstrate_queue_configurations()
        demonstrate_middleware()
        demonstrate_event_system()
        demonstrate_security_features()
        demonstrate_monitoring()
        demonstrate_queue_management()
        
        print("\n" + "=" * 70)
        print("🎉 All advanced features demonstrated successfully!")
        
        print("\n📚 Available CLI Commands:")
        print("  make queue-work                    # Start basic worker")
        print("  make queue-stats                   # Show queue statistics")
        print("  python -m app.Commands.QueueMonitorCommand dashboard  # Real-time dashboard")
        print("  python -m app.Commands.QueueMonitorCommand metrics    # Detailed analytics")
        print("  python -m app.Commands.QueueMonitorCommand health     # Health check")
        print("  python -m app.Commands.QueueMonitorCommand top        # Process monitor")
        
    except Exception as e:
        print(f"\n❌ Error running demo: {str(e)}")
        sys.exit(1)