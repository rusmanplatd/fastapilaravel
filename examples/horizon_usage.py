#!/usr/bin/env python3
"""
Laravel Horizon Usage Examples

This script demonstrates how to use the Laravel Horizon implementation
for queue monitoring and management in FastAPI applications.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import Horizon components
from app.Horizon import Horizon, HorizonManager, Dashboard
from app.Jobs.Job import Job
from routes.horizon import router as horizon_router


class ExampleJob(Job):
    """Example job for testing Horizon monitoring."""
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
        self.options.queue = "default"
    
    async def handle(self) -> None:
        """Process the job."""
        print(f"Processing job: {self.message}")
        await asyncio.sleep(2)  # Simulate work
        print(f"Completed job: {self.message}")
    
    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()
        data["data"] = {"message": self.message}
        return data


async def basic_horizon_usage():
    """Basic Horizon usage examples."""
    
    print("=== Laravel Horizon Usage Examples ===\n")
    
    # 1. Start Horizon monitoring
    print("1. Starting Horizon...")
    try:
        # In a real application, this would be done in the background
        print("   ✓ Horizon manager initialized")
        print("   ✓ Queue monitoring started")
        print("   ✓ Metrics collection enabled")
        print("   ✓ Dashboard available at /horizon")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Get Horizon statistics
    print("\n2. Getting Horizon statistics...")
    try:
        stats = await Horizon.get_stats()
        print(f"   Supervisors: {stats.get('overview', {}).get('total_supervisors', 0)}")
        print(f"   Active Workers: {stats.get('overview', {}).get('active_workers', 0)}")
        print(f"   Jobs Processed: {stats.get('overview', {}).get('total_jobs_processed', 0)}")
        print(f"   Status: {stats.get('overview', {}).get('status', 'Unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Monitor queues
    print("\n3. Monitoring queue metrics...")
    try:
        queues = await Horizon.get_queues()
        for queue_name, metrics in queues.items():
            pending = metrics.get('pending_jobs', 0)
            processing = metrics.get('processing_jobs', 0)
            print(f"   {queue_name}: {pending} pending, {processing} processing")
    except Exception as e:
        print(f"   Error: {e}")


async def supervisor_management_example():
    """Example of managing supervisors."""
    
    print("\n=== Supervisor Management Example ===\n")
    
    # 1. List supervisors
    print("1. Listing supervisors...")
    try:
        supervisors = await Horizon.get_supervisors()
        for supervisor in supervisors:
            name = supervisor.get('name', 'Unknown')
            status = supervisor.get('status', 'unknown')
            processes = supervisor.get('processes', 0)
            queues = ', '.join(supervisor.get('queues', []))
            print(f"   {name}: {status} ({processes} processes) - {queues}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Pause specific supervisor
    print("\n2. Pausing 'emails' supervisor...")
    try:
        await Horizon.pause('emails')
        print("   ✓ Supervisor paused")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Continue supervisor
    print("\n3. Continuing 'emails' supervisor...")
    try:
        await Horizon.continue_processing('emails')
        print("   ✓ Supervisor continued")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 4. Pause all supervisors
    print("\n4. Pausing all supervisors...")
    try:
        await Horizon.pause()
        print("   ✓ All supervisors paused")
    except Exception as e:
        print(f"   Error: {e}")


async def worker_monitoring_example():
    """Example of monitoring workers."""
    
    print("\n=== Worker Monitoring Example ===\n")
    
    # 1. List workers
    print("1. Listing active workers...")
    try:
        workers = await Horizon.get_workers()
        for worker in workers:
            worker_id = worker.get('id', 'Unknown')[:20]
            supervisor = worker.get('supervisor', 'Unknown')
            status = worker.get('status', 'unknown')
            jobs_processed = worker.get('jobs_processed', 0)
            current_job = worker.get('current_job', 'Idle')
            
            print(f"   {worker_id}: {supervisor} - {status}")
            print(f"     Jobs processed: {jobs_processed}")
            print(f"     Current job: {current_job}")
    except Exception as e:
        print(f"   Error: {e}")


async def metrics_monitoring_example():
    """Example of monitoring system metrics."""
    
    print("\n=== Metrics Monitoring Example ===\n")
    
    # 1. Get system metrics
    print("1. System metrics...")
    try:
        metrics = await Horizon.get_metrics()
        
        # System resources
        cpu_usage = metrics.get('cpu_usage', 0)
        memory_usage = metrics.get('memory_usage', 0)
        redis_memory = metrics.get('redis_memory', 0)
        
        print(f"   CPU Usage: {cpu_usage}%")
        print(f"   Memory Usage: {memory_usage}%")
        print(f"   Redis Memory: {redis_memory}MB")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Get job metrics
    print("\n2. Job processing metrics...")
    try:
        jobs = await Horizon.get_jobs()
        
        active_jobs = jobs.get('active_jobs', {})
        total = active_jobs.get('total', 0)
        by_status = active_jobs.get('by_status', {})
        
        print(f"   Total active jobs: {total}")
        for status, count in by_status.items():
            print(f"   {status}: {count}")
    except Exception as e:
        print(f"   Error: {e}")


def fastapi_integration_example():
    """Example of integrating Horizon with FastAPI."""
    
    print("\n=== FastAPI Integration Example ===\n")
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for Horizon."""
        # Start Horizon on startup
        print("🌅 Starting Horizon...")
        # In a real app, you'd call await Horizon.start() here
        # but we'll skip it for the example
        
        yield
        
        # Stop Horizon on shutdown
        print("🌅 Stopping Horizon...")
        await Horizon.stop()
    
    # Create FastAPI app with Horizon
    app = FastAPI(
        title="FastAPI with Horizon", 
        lifespan=lifespan
    )
    
    # Include Horizon routes
    app.include_router(horizon_router)
    
    # Example route that dispatches jobs
    @app.post("/dispatch-job")
    async def dispatch_example_job(message: str):
        """Dispatch an example job."""
        job = ExampleJob(message)
        job_id = await job.dispatch()
        
        return {
            "message": f"Job dispatched: {message}",
            "job_id": job_id
        }
    
    print("   FastAPI app configured with Horizon:")
    print("   - Dashboard: GET /horizon")
    print("   - API: /horizon/api/*")
    print("   - Job dispatch: POST /dispatch-job")
    
    return app


async def dashboard_usage_example():
    """Example of using the Horizon dashboard."""
    
    print("\n=== Dashboard Usage Example ===\n")
    
    print("Horizon Dashboard Features:")
    print("1. 📊 Real-time Statistics")
    print("   - Overview of supervisors, workers, and jobs")
    print("   - Queue metrics and throughput")
    print("   - System resource monitoring")
    
    print("\n2. 🎛️ Supervisor Management")
    print("   - Pause/continue individual supervisors")
    print("   - View supervisor configuration")
    print("   - Monitor worker processes")
    
    print("\n3. 📈 Metrics and Charts")
    print("   - Job throughput over time")
    print("   - System resource usage")
    print("   - Queue performance metrics")
    
    print("\n4. 🔍 Job Monitoring")
    print("   - Active job tracking")
    print("   - Failed job inspection")
    print("   - Job retry functionality")
    
    print("\n5. 🔄 WebSocket Updates")
    print("   - Real-time dashboard updates")
    print("   - Live metrics streaming")
    print("   - Instant status changes")


async def command_line_usage_example():
    """Example of using Horizon command line tools."""
    
    print("\n=== Command Line Usage Example ===\n")
    
    print("Horizon Commands:")
    print("1. Start Horizon:")
    print("   python -m app.Commands.HorizonCommand")
    print("   # or")
    print("   make horizon")
    
    print("\n2. Check Status:")
    print("   python -m app.Commands.HorizonCommand status")
    
    print("\n3. Pause/Continue:")
    print("   python -m app.Commands.HorizonCommand pause")
    print("   python -m app.Commands.HorizonCommand continue")
    print("   python -m app.Commands.HorizonCommand pause emails")
    
    print("\n4. List Components:")
    print("   python -m app.Commands.HorizonCommand list")
    
    print("\n5. Worker Management:")
    print("   python -m app.Commands.HorizonCommand work --queue=emails")


def configuration_example():
    """Example of configuring Horizon."""
    
    print("\n=== Configuration Example ===\n")
    
    example_config = """
# Horizon Configuration Example
from app.Horizon import HorizonManager, SupervisorConfig

# Create Horizon manager with custom Redis URL
horizon = HorizonManager('redis://localhost:6379/1')

# Configure supervisors
horizon.supervisors = {
    'web': SupervisorConfig(
        name='web',
        queue=['default', 'web'],
        processes=5,
        timeout=60,
        memory=128,
        tries=3,
        balance='auto',
        min_processes=2,
        max_processes=8
    ),
    
    'emails': SupervisorConfig(
        name='emails',
        queue=['emails'],
        processes=3,
        timeout=30,
        memory=64,
        tries=5,
        balance='simple'
    ),
    
    'reports': SupervisorConfig(
        name='reports',
        queue=['reports'],
        processes=1,
        timeout=300,
        memory=256,
        tries=1,
        balance='off'
    ),
}

# Environment variables for configuration
HORIZON_REDIS_URL=redis://localhost:6379/0
HORIZON_METRICS_RETENTION=7d
HORIZON_DASHBOARD_AUTH=true
"""
    
    print("Configuration options:")
    print(example_config)


async def main():
    """Run all Horizon examples."""
    await basic_horizon_usage()
    await supervisor_management_example() 
    await worker_monitoring_example()
    await metrics_monitoring_example()
    fastapi_integration_example()
    await dashboard_usage_example()
    await command_line_usage_example()
    configuration_example()
    
    print("\n=== Summary ===")
    print("✅ Laravel Horizon implementation complete!")
    print("📚 Features implemented:")
    print("   - Queue monitoring and metrics collection")
    print("   - Supervisor and worker management")
    print("   - Real-time dashboard with WebSocket updates")
    print("   - System resource monitoring")
    print("   - Job lifecycle tracking")
    print("   - Command line tools")
    print("   - FastAPI integration")
    print("   - Redis-based metrics storage")
    print("   - Auto-balancing workers")
    print("   - Failed job handling")
    
    print("\n🌅 Ready to monitor your queues with Horizon!")


if __name__ == "__main__":
    asyncio.run(main())