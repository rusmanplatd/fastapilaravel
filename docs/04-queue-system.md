# Queue System & Job Processing (Laravel 12 Style)

## Overview

The queue system provides Laravel-style background job processing with comprehensive features including job batching, chaining, rate limiting, and advanced monitoring capabilities.

## Job Classes

### Base Job Structure
**Location:** `app/Jobs/Job.py`

**Key Features:**
- Laravel 12 job states (pending, processing, completed, failed, cancelled, retrying)
- Unique job interfaces (`ShouldBeUnique`, `ShouldBeEncrypted`)
- Automatic serialization/deserialization
- Progress tracking and metrics

**Basic Job Example:**
```python
from app.Jobs.Job import Job

class SendEmailJob(Job):
    def __init__(self, to_email: str, subject: str, body: str):
        super().__init__()
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.queue = "emails"  # Specify queue
        self.delay = 0  # Delay in seconds
        self.max_tries = 3  # Retry attempts
    
    def handle(self) -> None:
        """Execute the job"""
        # Send email logic
        EmailService.send(self.to_email, self.subject, self.body)
    
    def failed(self, exception: Exception) -> None:
        """Handle job failure"""
        logging.error(f"Failed to send email to {self.to_email}: {exception}")
```

### Job Dispatching
```python
from app.Jobs.Examples.SendEmailJob import SendEmailJob

# Basic dispatch
job_id = SendEmailJob.dispatch("user@example.com", "Welcome", "Hello!")

# Dispatch with options
job_id = SendEmailJob("user@example.com", "Welcome", "Hello!") \
    .on_queue("high-priority") \
    .delay_until(60) \
    .with_priority(10) \
    .dispatch()

# Conditional dispatch
SendEmailJob.dispatch_if(user.wants_emails, "user@example.com", "News", "...")
SendEmailJob.dispatch_unless(user.unsubscribed, "user@example.com", "News", "...")

# Immediate execution (bypass queue)
SendEmailJob.dispatch_now("user@example.com", "Welcome", "Hello!")
```

### Unique Jobs
```python
class ProcessUserDataJob(Job, ShouldBeUnique):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
    
    def unique_id(self) -> str:
        return f"process_user_{self.user_id}"
    
    def unique_for(self) -> timedelta:
        return timedelta(hours=1)  # Stay unique for 1 hour
```

### Encrypted Jobs
```python
class ProcessSensitiveDataJob(Job, ShouldBeEncrypted):
    def __init__(self, sensitive_data: str):
        super().__init__()
        self.sensitive_data = sensitive_data
        
    def handle(self) -> None:
        # Job data is automatically encrypted/decrypted
        processed = self.process_data(self.sensitive_data)
```

## Job Batching

### Current Implementation
**Location:** `app/Jobs/Batch.py`

**Features:**
- Progress tracking across multiple jobs
- Failure threshold management  
- Callback hooks (then, catch, finally)
- Atomic batch operations

**Batch Creation:**
```python
from app.Jobs.Batch import batch, BatchableJob

class ProcessDataJob(BatchableJob):
    def __init__(self, data_chunk: List[Any]):
        super().__init__()
        self.data_chunk = data_chunk
    
    def _handle(self):  # Use _handle for batchable jobs
        for item in self.data_chunk:
            self.process_item(item)

# Create and dispatch batch
batch_id = batch([
    ProcessDataJob(chunk1),
    ProcessDataJob(chunk2), 
    ProcessDataJob(chunk3)
]).name("Data Processing Batch") \
  .allow_failures(1) \
  .then(lambda: print("Batch completed successfully")) \
  .catch(lambda e: print(f"Batch failed: {e}")) \
  .finally(lambda: print("Batch finished")) \
  .dispatch()
```

**Batch Monitoring:**
```python
from app.Models.JobBatch import JobBatch

# Get batch status
batch = JobBatch.find(batch_id)
print(f"Progress: {batch.progress()}%")
print(f"Pending: {batch.pending_jobs}")
print(f"Failed: {batch.failed_jobs}")
print(f"Processed: {batch.processed_jobs}")

# Check batch state
if batch.finished():
    print("Batch completed")
elif batch.cancelled():
    print("Batch was cancelled")
```

## Job Chaining

### Current Implementation  
**Location:** `app/Jobs/Chain.py`

**Features:**
- Sequential job execution
- Failure handling with chain breaks
- Chain progress monitoring
- Dynamic chain modification

**Chain Creation:**
```python
from app.Jobs.Chain import chain, ChainableJob

class ExtractDataJob(ChainableJob):
    def _handle(self):
        # Extract data logic
        return {"extracted_data": "..."}

class TransformDataJob(ChainableJob):  
    def _handle(self):
        # Get data from previous job
        previous_result = self.get_previous_result()
        # Transform logic
        return {"transformed_data": "..."}

class LoadDataJob(ChainableJob):
    def _handle(self):
        # Load data logic
        pass

# Create chain
chain_id = chain([
    ExtractDataJob(),
    TransformDataJob(),
    LoadDataJob(),
    NotifyCompletionJob()
]).name("ETL Pipeline") \
  .catch(lambda e: print(f"Chain failed: {e}")) \
  .dispatch()
```

**Chain Monitoring:**
```python
from app.Jobs.ChainMonitor import ChainMonitor

monitor = ChainMonitor(chain_id)
status = monitor.get_status()
print(f"Current step: {status.current_step}")
print(f"Progress: {status.progress}%")
```

## Queue Management

### Queue Configuration
**Location:** `app/Queue/QueueManager.py`

**Queue Types:**
```python
# Database queue (default)
QUEUE_CONFIG = {
    "default": {
        "driver": "database",
        "connection": "default",
        "table": "jobs",
        "queue": "default",
        "retry_after": 3600,
        "max_attempts": 3
    },
    
    # Redis queue
    "redis": {
        "driver": "redis", 
        "connection": "redis_cache",
        "queue": "default",
        "retry_after": 3600,
        "block_for": 0
    }
}
```

**Queue Definitions:**
```python
from app.Queue.QueueManager import define_queue

# High priority queue
define_queue("high-priority", 
    connection="redis",
    max_jobs=1000,
    priority_weight=10,
    rate_limit_enabled=True,
    rate_limit_max=100,
    rate_limit_window=60)

# Email queue with specific settings  
define_queue("emails",
    connection="database", 
    max_attempts=5,
    retry_after=300,
    encryption_enabled=True)
```

### Worker Management
**Location:** `app/Queue/Worker.py`

**Features:**
- Multi-queue processing
- Memory management
- Graceful shutdown
- Health monitoring
- Performance metrics

**Worker Commands:**
```bash
# Start default worker
make queue-work

# Start specific queue worker
make queue-work-emails

# Worker with options
python artisan queue:work --queue=high-priority,default --timeout=60 --memory=256
```

## Rate Limiting

### Current Implementation
**Location:** `app/Jobs/RateLimiter.py`

**Features:**
- Job-level rate limiting
- Queue-level rate limiting
- Multiple limiting strategies
- Redis-backed distributed limiting

**Usage:**
```python
from app.Jobs.RateLimiter import RateLimit, RateLimited

class EmailJob(Job, RateLimited):
    def __init__(self, recipient: str):
        super().__init__()
        self.recipient = recipient
    
    def get_rate_limits(self) -> List[RateLimit]:
        return [
            RateLimit(max_attempts=100, per_seconds=3600),  # 100 emails per hour
            RateLimit(max_attempts=10, per_seconds=60, key=f"user:{self.recipient}")  # 10 per user per minute
        ]
```

**Global Rate Limiting:**
```python
from app.Queue.QueueManager import QueueManager

# Rate limit entire queue
QueueManager.rate_limit("emails", max_jobs=1000, per_seconds=3600)
```

## Job Middleware

### Current Implementation
**Location:** `app/Jobs/Middleware/`

**Available Middleware:**
- `LoggingMiddleware` - Job execution logging
- `TimingMiddleware` - Performance measurement
- `ThrottleMiddleware` - Job throttling
- `RetryMiddleware` - Custom retry logic
- `AuthorizationMiddleware` - Job-level authorization

**Usage:**
```python
from app.Jobs.Middleware import MiddlewareStack, LoggingMiddleware, TimingMiddleware

class ProcessDataJob(Job):
    def __init__(self):
        super().__init__()
        self.middleware = MiddlewareStack()
        self.middleware.add(LoggingMiddleware())
        self.middleware.add(TimingMiddleware())
```

## Advanced Features

### Job Security
**Location:** `app/Jobs/Security.py`

**Features:**
- Job payload encryption
- Digital signature verification
- Permission-based job execution
- Sensitive data handling

**Secure Job Example:**
```python
from app.Jobs.Security import SecureJob

class ProcessPaymentJob(SecureJob):
    def __init__(self, payment_data: Dict[str, Any]):
        super().__init__()
        self.payment_data = payment_data
        self.set_sensitive_fields(["payment_data"])
        self.set_required_permissions(["process_payments"])
    
    def handle(self):
        # Payment data is automatically decrypted
        self.process_payment(self.payment_data)
```

### Job Monitoring & Metrics
**Location:** `app/Jobs/MetricsCollector.py`

**Metrics Collected:**
- Job execution time
- Success/failure rates
- Queue lengths
- Worker performance
- Memory usage

**Usage:**
```python
from app.Jobs.MetricsCollector import JobMetrics

# Get job metrics
metrics = JobMetrics.get_job_metrics("SendEmailJob")
print(f"Average execution time: {metrics.avg_execution_time}")
print(f"Success rate: {metrics.success_rate}")

# Get queue metrics
queue_stats = JobMetrics.get_queue_stats("emails")
print(f"Jobs in queue: {queue_stats.pending}")
print(f"Failed jobs: {queue_stats.failed}")
```

### Horizon Dashboard
**Location:** `app/Horizon/`

**Features:**
- Real-time queue monitoring
- Job metrics and analytics  
- Worker supervision
- Failed job management

**Access:**
```bash
# Start Horizon dashboard
make queue-dashboard

# View at http://localhost:8000/horizon
```

## Queue Commands

### Management Commands
```bash
# Queue Operations
make queue-work                 # Start default worker
make queue-work-emails          # Start emails queue worker  
make queue-stats               # Show queue statistics
make queue-failed              # List failed jobs
make queue-retry-failed        # Retry all failed jobs
make queue-clear               # Clear queue (with confirmation)

# Advanced Commands
make queue-dashboard           # Real-time monitoring dashboard
make queue-metrics            # Detailed analytics & performance
make queue-health             # Health check & diagnostics
make queue-top                # htop-style process monitor
```

### Custom Commands
```python
from app.Console.Command import Command

class QueueStatsCommand(Command):
    signature = "queue:stats {--queue=default}"
    description = "Display queue statistics"
    
    def handle(self):
        queue_name = self.option("queue")
        stats = QueueManager.get_stats(queue_name)
        self.info(f"Queue: {queue_name}")
        self.info(f"Pending: {stats.pending}")
        self.info(f"Processing: {stats.processing}")  
        self.info(f"Failed: {stats.failed}")
```

## Testing

### Job Testing Utilities
**Location:** `app/Testing/`

**Features:**
- Job assertion helpers
- Queue faking
- Batch testing utilities
- Chain testing support

**Testing Example:**
```python
from app.Testing.JobTesting import QueueFake

def test_job_dispatching():
    queue_fake = QueueFake()
    
    # Dispatch job
    SendEmailJob.dispatch("user@example.com", "Test", "Body")
    
    # Assertions
    queue_fake.assert_pushed(SendEmailJob)
    queue_fake.assert_pushed_on("emails", SendEmailJob)
    queue_fake.assert_not_pushed(SendSMSJob)
```

## Improvements

### Performance Optimizations
1. **Parallel processing**: Multi-threaded job execution
2. **Job pooling**: Reuse job instances for better memory usage
3. **Smart batching**: Automatic job batching based on similarity
4. **Connection pooling**: Database connection optimization

### Advanced Features
1. **Job scheduling integration**: Cron-style job scheduling
2. **Distributed processing**: Multi-server job processing
3. **AI-powered optimization**: Machine learning for job routing
4. **Real-time streaming**: WebSocket job status updates

### Developer Experience
1. **Job generators**: Artisan commands for job creation
2. **Debug toolbar integration**: Queue debugging tools
3. **Visual job builder**: GUI for complex job chains
4. **Performance profiling**: Built-in job performance analysis

### Enterprise Features
1. **Multi-tenancy**: Tenant-isolated job processing
2. **Compliance**: Audit trails and data retention policies
3. **Disaster recovery**: Job backup and restore capabilities
4. **High availability**: Failover and redundancy support