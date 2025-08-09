#!/usr/bin/env python3
"""
Laravel Telescope Usage Examples

This script demonstrates how to use the Laravel Telescope implementation
for debugging and monitoring FastAPI applications.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

# Import Telescope components
from app.Telescope import Telescope
from app.Telescope.Middleware import add_telescope_middleware
from routes.telescope import router as telescope_router


async def basic_telescope_usage():
    """Basic Telescope usage examples."""
    
    print("=== Laravel Telescope Usage Examples ===\n")
    
    # 1. Initialize Telescope
    print("1. Initializing Telescope...")
    await Telescope.initialize('redis://localhost:6379/0')
    print("   ✓ Telescope initialized with Redis")
    print("   ✓ Watchers enabled: request, query, exception, job, cache, redis, mail, notification")
    
    # 2. Record different types of entries
    print("\n2. Recording different entry types...")
    
    # Record a database query
    Telescope.record_query(
        "SELECT * FROM users WHERE id = %s",
        [1],
        duration=15.5,
        connection_name='default'
    )
    print("   ✓ Database query recorded")
    
    # Record a cache operation
    Telescope.record_cache_hit('user:1', {'name': 'John', 'email': 'john@example.com'})
    print("   ✓ Cache hit recorded")
    
    # Record a job dispatch
    Telescope.record_job_dispatched(
        'job_123',
        'SendEmailJob',
        'emails',
        {'to': 'user@example.com', 'subject': 'Welcome'}
    )
    print("   ✓ Job dispatch recorded")
    
    # Record a Redis command
    Telescope.record_redis_command('GET', ['user:1'], duration=2.1)
    print("   ✓ Redis command recorded")
    
    # 3. Get statistics
    print("\n3. Getting Telescope statistics...")
    stats = await Telescope.get_statistics()
    print(f"   Total entries: {stats.get('total_entries', 0)}")
    print(f"   Recording: {stats.get('recording', False)}")
    print(f"   Watchers: {', '.join(stats.get('watchers', []))}")


async def exception_monitoring_example():
    """Example of exception monitoring with Telescope."""
    
    print("\n=== Exception Monitoring Example ===\n")
    
    # 1. Record a handled exception
    print("1. Recording handled exception...")
    try:
        # Simulate an error
        result = 1 / 0
    except ZeroDivisionError as e:
        Telescope.record_exception(
            e,
            context={'operation': 'division', 'values': [1, 0]},
            handled=True
        )
        print("   ✓ Handled exception recorded")
    
    # 2. Record an unhandled exception (simulated)
    print("\n2. Recording unhandled exception...")
    try:
        # Simulate an unhandled error
        raise ValueError("Invalid configuration value")
    except ValueError as e:
        Telescope.record_exception(
            e,
            context={'config_key': 'database_url', 'config_value': 'invalid'},
            handled=False
        )
        print("   ✓ Unhandled exception recorded")


async def request_monitoring_example():
    """Example of HTTP request monitoring."""
    
    print("\n=== Request Monitoring Example ===\n")
    
    # Simulate recording an HTTP request (normally done by middleware)
    print("1. Simulating HTTP request monitoring...")
    
    # This would normally be captured by TelescopeMiddleware
    # Here we'll show what the data would look like
    request_data = {
        'method': 'POST',
        'uri': '/api/v1/users',
        'headers': {'Content-Type': 'application/json'},
        'payload': {'name': 'John Doe', 'email': 'john@example.com'},
        'duration': 145.2,  # milliseconds
        'memory': 12 * 1024 * 1024,  # bytes
        'response_status': 201
    }
    
    print(f"   Request: {request_data['method']} {request_data['uri']}")
    print(f"   Duration: {request_data['duration']}ms")
    print(f"   Status: {request_data['response_status']}")
    print("   ✓ Request data captured")


async def job_monitoring_example():
    """Example of job monitoring with Telescope."""
    
    print("\n=== Job Monitoring Example ===\n")
    
    # 1. Record job lifecycle
    print("1. Recording job lifecycle...")
    
    job_id = 'job_456'
    job_class = 'ProcessImageJob'
    queue = 'images'
    
    # Job dispatched
    Telescope.record_job_dispatched(
        job_id, job_class, queue,
        {'image_path': '/uploads/image.jpg', 'size': '1920x1080'}
    )
    print("   ✓ Job dispatched")
    
    # Simulate processing time
    await asyncio.sleep(0.1)
    
    # Job completed
    Telescope.record_job_completed(
        job_id, job_class, queue,
        duration=2.5
    )
    print("   ✓ Job completed")
    
    # 2. Record job failure
    print("\n2. Recording job failure...")
    
    failed_job_id = 'job_789'
    Telescope.record_job_failed(
        failed_job_id, 'SendNotificationJob', 'notifications',
        exception="ConnectionError: Could not connect to notification service"
    )
    print("   ✓ Job failure recorded")


def fastapi_integration_example():
    """Example of integrating Telescope with FastAPI."""
    
    print("\n=== FastAPI Integration Example ===\n")
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for Telescope."""
        # Initialize Telescope on startup
        print("🔭 Initializing Telescope...")
        await Telescope.initialize()
        Telescope.start_recording()
        
        yield
        
        # Cleanup on shutdown
        print("🔭 Shutting down Telescope...")
        Telescope.stop_recording()
    
    # Create FastAPI app with Telescope
    app = FastAPI(
        title="FastAPI with Telescope",
        lifespan=lifespan
    )
    
    # Add Telescope middleware
    add_telescope_middleware(app)
    
    # Include Telescope routes
    app.include_router(telescope_router)
    
    # Example routes that will be monitored
    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        """Get user by ID - monitored by Telescope."""
        # Simulate database query (would be recorded by QueryWatcher)
        Telescope.record_query(
            "SELECT * FROM users WHERE id = %s",
            [user_id],
            duration=12.3
        )
        
        if user_id == 999:
            # Simulate an exception (would be recorded by ExceptionWatcher)
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"id": user_id, "name": f"User {user_id}"}
    
    @app.post("/send-email")
    async def send_email(email_data: dict):
        """Send email - monitored by Telescope."""
        # Simulate email sending (would be recorded by MailWatcher)
        Telescope.record_mail_sent(
            'WelcomeEmail',
            [email_data.get('to', 'user@example.com')],
            subject=email_data.get('subject', 'Welcome'),
            success=True
        )
        
        return {"message": "Email sent successfully"}
    
    print("   FastAPI app configured with Telescope:")
    print("   - Dashboard: GET /telescope")
    print("   - Middleware: Request/Response monitoring")
    print("   - Routes: /users/{id}, /send-email")
    
    return app


async def watcher_management_example():
    """Example of managing Telescope watchers."""
    
    print("\n=== Watcher Management Example ===\n")
    
    # 1. List available watchers
    print("1. Available watchers...")
    stats = await Telescope.get_statistics()
    watchers = stats.get('watchers', [])
    print(f"   Watchers: {', '.join(watchers)}")
    
    # 2. Disable specific watchers
    print("\n2. Managing watchers...")
    Telescope.disable_watcher('cache')
    print("   ✓ Cache watcher disabled")
    
    Telescope.disable_watcher('redis')
    print("   ✓ Redis watcher disabled")
    
    # 3. Re-enable watchers
    Telescope.enable_watcher('cache')
    print("   ✓ Cache watcher enabled")
    
    # 4. Control recording
    print("\n3. Controlling recording...")
    Telescope.pause()
    print("   ✓ Recording paused")
    
    # This won't be recorded
    Telescope.record_cache_hit('ignored:key', 'value')
    
    Telescope.resume()
    print("   ✓ Recording resumed")
    
    # This will be recorded
    Telescope.record_cache_hit('recorded:key', 'value')
    print("   ✓ Cache operation recorded after resume")


async def data_retrieval_example():
    """Example of retrieving data from Telescope."""
    
    print("\n=== Data Retrieval Example ===\n")
    
    # 1. Get all entries
    print("1. Retrieving entries...")
    entries = await Telescope.get_entries(limit=10)
    print(f"   Retrieved {len(entries)} entries")
    
    # 2. Filter by type
    print("\n2. Filtering entries by type...")
    query_entries = await Telescope.get_entries(type_filter='query', limit=5)
    print(f"   Query entries: {len(query_entries)}")
    
    exception_entries = await Telescope.get_entries(type_filter='exception', limit=5)
    print(f"   Exception entries: {len(exception_entries)}")
    
    # 3. Get statistics
    print("\n3. Getting detailed statistics...")
    stats = await Telescope.get_statistics()
    
    entries_by_type = stats.get('entries_by_type', {})
    for entry_type, count in entries_by_type.items():
        print(f"   {entry_type}: {count}")
    
    # 4. Clear old entries
    print("\n4. Cleaning up entries...")
    count = await Telescope.clear_entries()
    print(f"   ✓ Cleared {count} entries")


def configuration_example():
    """Example of configuring Telescope."""
    
    print("\n=== Configuration Example ===\n")
    
    config_example = """
# Telescope Configuration Example

# Initialize with custom Redis URL
await Telescope.initialize('redis://localhost:6379/1')

# Control recording
Telescope.start_recording()  # Enable recording
Telescope.stop_recording()   # Disable recording
Telescope.pause()            # Alias for stop_recording
Telescope.resume()           # Alias for start_recording

# Manage watchers
Telescope.disable_watcher('cache')     # Disable cache monitoring
Telescope.enable_watcher('cache')      # Enable cache monitoring

# Configure watchers with ignore patterns
cache_watcher = Telescope.get_watcher('cache')
if cache_watcher:
    cache_watcher.ignore('session:', 'temp:', 'debug:')

# Environment variables for configuration
TELESCOPE_REDIS_URL=redis://localhost:6379/0
TELESCOPE_RETENTION_HOURS=24
TELESCOPE_ENABLED=true
"""
    
    print("Configuration options:")
    print(config_example)


def dashboard_features_example():
    """Example of Telescope dashboard features."""
    
    print("\n=== Dashboard Features Example ===\n")
    
    print("Telescope Dashboard Features:")
    print("1. 📊 Real-time Monitoring")
    print("   - HTTP requests and responses")
    print("   - Database queries with timing")
    print("   - Exceptions with stack traces")
    print("   - Job processing and failures")
    
    print("\n2. 🔍 Debugging Tools")
    print("   - Request/response inspection")
    print("   - Query analysis and optimization")
    print("   - Exception tracking and grouping")
    print("   - Performance profiling")
    
    print("\n3. 📈 Performance Insights")
    print("   - Slow query detection")
    print("   - Memory usage tracking")
    print("   - Request duration analysis")
    print("   - Cache hit/miss ratios")
    
    print("\n4. 🎛️ Management Controls")
    print("   - Enable/disable watchers")
    print("   - Pause/resume recording")
    print("   - Clear old entries")
    print("   - Export debugging data")
    
    print("\n5. 🔄 Real-time Updates")
    print("   - Live entry streaming")
    print("   - Automatic refresh")
    print("   - Interactive filtering")


async def main():
    """Run all Telescope examples."""
    await basic_telescope_usage()
    await exception_monitoring_example()
    await request_monitoring_example()
    await job_monitoring_example()
    fastapi_integration_example()
    await watcher_management_example()
    await data_retrieval_example()
    configuration_example()
    dashboard_features_example()
    
    print("\n=== Summary ===")
    print("✅ Laravel Telescope implementation complete!")
    print("📚 Features implemented:")
    print("   - Request/Response monitoring with middleware")
    print("   - Database query tracking and analysis")
    print("   - Exception capturing with stack traces")
    print("   - Job lifecycle monitoring")
    print("   - Cache operation tracking")
    print("   - Redis command monitoring")
    print("   - Email sending tracking")
    print("   - Notification monitoring")
    print("   - Command execution tracking")
    print("   - Real-time dashboard with filtering")
    print("   - Watcher management and configuration")
    print("   - Data retention and cleanup")
    print("   - Performance profiling")
    
    print("\n🔭 Ready to debug your FastAPI application!")


if __name__ == "__main__":
    asyncio.run(main())