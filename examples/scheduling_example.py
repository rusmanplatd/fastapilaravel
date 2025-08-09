"""
Laravel-style Job Scheduling Example for FastAPI Laravel

This example demonstrates comprehensive job scheduling using the enhanced
scheduler system with decorators, configuration, and various scheduling patterns.
"""

from __future__ import annotations

from datetime import datetime
import asyncio
from typing import Any, Dict, List

# Scheduling imports
from app.Console.Scheduling.SchedulerManager import scheduler
from app.Console.Scheduling.ScheduleConfigLoader import (
    scheduled, every_minute, every_five_minutes, hourly, daily, weekly,
    environments, without_overlapping, on_one_server
)

# Job imports
from app.Jobs.Job import Job


# Example 1: Basic scheduled jobs using decorators
@daily(time='8:00')
@environments('production', 'staging')
class DailyReportJob(Job):
    """Generate and send daily reports."""
    
    def __init__(self, report_type: str = 'summary'):
        super().__init__()
        self.report_type = report_type
        self.options.queue = 'reports'
    
    def handle(self) -> None:
        """Generate daily report."""
        print(f"Generating {self.report_type} report for {datetime.now().date()}")
        # Report generation logic would go here
        

@hourly(minute=30)
@without_overlapping()
class CacheWarmupJob(Job):
    """Warm up application cache."""
    
    def __init__(self):
        super().__init__()
        self.options.queue = 'maintenance'
    
    def handle(self) -> None:
        """Warm up cache."""
        print("Warming up application cache...")
        # Cache warming logic would go here


@every_five_minutes()
@environments('production')
class HealthCheckJob(Job):
    """Perform application health checks."""
    
    def __init__(self):
        super().__init__()
        self.options.queue = 'monitoring'
    
    def handle(self) -> None:
        """Check application health."""
        print("Performing health check...")
        # Health check logic would go here


@weekly(day=1, time='2:00')  # Monday at 2 AM
@on_one_server()
class WeeklyMaintenanceJob(Job):
    """Perform weekly maintenance tasks."""
    
    def __init__(self):
        super().__init__()
        self.options.queue = 'maintenance'
    
    def handle(self) -> None:
        """Perform weekly maintenance."""
        print("Starting weekly maintenance...")
        # Maintenance logic would go here


# Example 2: Complex scheduled job with custom configuration
@scheduled(
    cron='0 */6 * * *',  # Every 6 hours
    description='Sync data with external API',
    environments=['production'],
    without_overlapping=True,
    max_attempts=3,
    retry_after=15,
    email_on_failure=['admin@example.com']
)
class ExternalDataSyncJob(Job):
    """Sync data with external API."""
    
    def __init__(self, api_endpoint: str, batch_size: int = 100):
        super().__init__()
        self.api_endpoint = api_endpoint
        self.batch_size = batch_size
        self.options.queue = 'external-sync'
    
    def handle(self) -> None:
        """Sync external data."""
        print(f"Syncing data from {self.api_endpoint} (batch size: {self.batch_size})")
        # API sync logic would go here


# Example 3: Programmatic scheduling without decorators
class CustomAnalyticsJob(Job):
    """Process analytics data."""
    
    def __init__(self, date_range: str = 'yesterday'):
        super().__init__()
        self.date_range = date_range
        self.options.queue = 'analytics'
    
    def handle(self) -> None:
        """Process analytics."""
        print(f"Processing analytics for {self.date_range}")
        # Analytics processing logic would go here


def setup_custom_schedules() -> None:
    """Set up custom schedules programmatically."""
    
    # Schedule analytics job with complex timing
    scheduler.job(CustomAnalyticsJob, 'last_week') \
        .weekly_on(1, '5:00') \
        .description('Process weekly analytics') \
        .without_overlapping() \
        .environments('production') \
        .email_output_on_failure('analytics@example.com')
    
    # Schedule with conditional execution
    scheduler.job(CustomAnalyticsJob, 'yesterday') \
        .daily_at('6:00') \
        .description('Process daily analytics') \
        .when(lambda: should_process_analytics()) \
        .unless_between('23:00', '2:00')  # Skip during backup window
    
    # Schedule with multiple environment constraints
    scheduler.job(CustomAnalyticsJob, 'hourly') \
        .hourly() \
        .description('Process hourly analytics') \
        .between('8:00', '18:00') \
        .weekdays() \
        .environments('production', 'staging')


# Example 4: Command scheduling with the new system
def setup_command_schedules() -> None:
    """Set up command-based schedules."""
    
    # Artisan command scheduling
    scheduler.command('queue:work') \
        .every_minute() \
        .description('Process queue jobs') \
        .without_overlapping() \
        .run_in_background()
    
    scheduler.command('cache:clear') \
        .daily_at('3:00') \
        .description('Clear application cache') \
        .environments('production')
    
    # Shell command scheduling
    scheduler.exec('find /tmp -name "*.tmp" -delete') \
        .hourly() \
        .description('Clean temporary files') \
        .send_output_to('storage/logs/cleanup.log')
    
    # Command with webhooks
    scheduler.command('backup:database') \
        .daily_at('1:00') \
        .description('Daily database backup') \
        .ping_before('https://healthchecks.io/ping/backup-start') \
        .then_ping('https://healthchecks.io/ping/backup-success') \
        .email_output_on_failure('backup@example.com')


# Example 5: Callable function scheduling
def cleanup_temp_files() -> None:
    """Clean up temporary files."""
    import os
    import glob
    
    temp_patterns = [
        '/tmp/app-*',
        'storage/tmp/*',
        'storage/cache/temp/*'
    ]
    
    cleaned = 0
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    cleaned += 1
            except OSError:
                pass
    
    print(f"Cleaned {cleaned} temporary files")


async def update_search_index() -> None:
    """Update search index asynchronously."""
    print("Updating search index...")
    await asyncio.sleep(1)  # Simulate async work
    print("Search index updated")


def setup_callable_schedules() -> None:
    """Set up callable-based schedules."""
    
    # Synchronous callable
    scheduler.call(cleanup_temp_files) \
        .every_thirty_minutes() \
        .description('Clean temporary files') \
        .send_output_to('storage/logs/cleanup.log')
    
    # Asynchronous callable
    scheduler.call(update_search_index) \
        .every_fifteen_minutes() \
        .description('Update search index') \
        .between('8:00', '20:00') \
        .weekdays()
    
    # Lambda function
    scheduler.call(lambda: print(f"Heartbeat at {datetime.now()}")) \
        .every_minute() \
        .description('Application heartbeat') \
        .send_output_to('storage/logs/heartbeat.log')


# Example 6: Conditional scheduling helpers
def should_process_analytics() -> bool:
    """Check if analytics should be processed."""
    # Skip on weekends in development
    if not is_production():
        return datetime.now().weekday() < 5
    return True


def is_production() -> bool:
    """Check if running in production."""
    import os
    return os.getenv('APP_ENV', 'development') == 'production'


def is_maintenance_window() -> bool:
    """Check if we're in maintenance window."""
    hour = datetime.now().hour
    return 2 <= hour <= 4  # 2 AM - 4 AM


# Example 7: Schedule with before/after hooks
def log_job_start() -> None:
    """Log job start."""
    print(f"[{datetime.now()}] Starting scheduled job...")


def log_job_end() -> None:
    """Log job end."""
    print(f"[{datetime.now()}] Scheduled job completed.")


def setup_hooks_example() -> None:
    """Set up schedules with hooks."""
    
    scheduler.command('heavy:processing') \
        .daily_at('2:30') \
        .description('Heavy data processing') \
        .before(log_job_start) \
        .after(log_job_end) \
        .without_overlapping() \
        .max_attempts(2)


# Example 8: Environment-specific configuration
def setup_environment_schedules() -> None:
    """Set up environment-specific schedules."""
    
    if is_production():
        # Production-only schedules
        scheduler.command('monitor:performance') \
            .every_minute() \
            .description('Monitor performance metrics') \
            .without_overlapping()
        
        scheduler.command('security:scan') \
            .daily_at('4:00') \
            .description('Security vulnerability scan') \
            .email_output_on_failure('security@example.com')
        
        scheduler.command('logs:archive') \
            .weekly_on(0, '5:00') \
            .description('Archive old log files') \
            .send_output_to('storage/logs/archive.log')
    
    else:
        # Development/staging schedules
        scheduler.command('dev:reset-cache') \
            .every_thirty_minutes() \
            .description('Reset development cache')
        
        scheduler.command('test:seed-data') \
            .daily_at('7:00') \
            .description('Seed test data') \
            .environments('development', 'testing')


# Example 9: Complex scheduling patterns
def setup_complex_schedules() -> None:
    """Set up complex scheduling patterns."""
    
    # Business hours only
    scheduler.command('process:orders') \
        .every_five_minutes() \
        .description('Process new orders') \
        .between('9:00', '17:00') \
        .weekdays() \
        .without_overlapping()
    
    # Maintenance window scheduling
    scheduler.command('maintenance:optimize-db') \
        .daily_at('3:00') \
        .description('Optimize database') \
        .unless_between('8:00', '18:00') \
        .when(lambda: not is_maintenance_window()) \
        .on_one_server()
    
    # Seasonal scheduling
    def is_holiday_season() -> bool:
        month = datetime.now().month
        return month in [11, 12]  # November, December
    
    scheduler.command('marketing:holiday-emails') \
        .daily_at('10:00') \
        .description('Send holiday marketing emails') \
        .when(is_holiday_season) \
        .environments('production')


# Example 10: Monitoring and health checks
def setup_monitoring_schedules() -> None:
    """Set up monitoring and health check schedules."""
    
    # Health check with external monitoring
    scheduler.command('health:check') \
        .every_five_minutes() \
        .description('Application health check') \
        .ping_before('https://healthchecks.io/ping/app-health-start') \
        .then_ping('https://healthchecks.io/ping/app-health-success') \
        .email_output_on_failure('ops@example.com')
    
    # Disk space monitoring
    def check_disk_space() -> None:
        import shutil
        total, used, free = shutil.disk_usage('/')
        usage_percent = (used / total) * 100
        
        if usage_percent > 80:
            print(f"WARNING: Disk usage at {usage_percent:.1f}%")
        else:
            print(f"Disk usage: {usage_percent:.1f}%")
    
    scheduler.call(check_disk_space) \
        .every_fifteen_minutes() \
        .description('Monitor disk space') \
        .send_output_to('storage/logs/disk-monitoring.log')
    
    # Memory monitoring
    def check_memory_usage() -> None:
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                print(f"WARNING: Memory usage at {memory.percent}%")
            else:
                print(f"Memory usage: {memory.percent}%")
        except ImportError:
            print("psutil not available for memory monitoring")
    
    scheduler.call(check_memory_usage) \
        .every_ten_minutes() \
        .description('Monitor memory usage') \
        .send_output_to('storage/logs/memory-monitoring.log')


# Main setup function
def setup_all_schedules() -> None:
    """Set up all example schedules."""
    setup_custom_schedules()
    setup_command_schedules()
    setup_callable_schedules()
    setup_hooks_example()
    setup_environment_schedules()
    setup_complex_schedules()
    setup_monitoring_schedules()


if __name__ == "__main__":
    # Example of running the scheduler
    import asyncio
    
    # Set up all schedules
    setup_all_schedules()
    
    # Show scheduled events
    print("Scheduled Events:")
    print("=" * 50)
    
    for event_id, event in scheduler.events.items():
        print(f"ID: {event_id}")
        print(f"Description: {event.description}")
        print(f"Cron: {event.cron_expression}")
        print(f"Environments: {event.environments or 'any'}")
        print("-" * 30)
    
    # Run due events (example)
    async def run_scheduler():
        """Example of running the scheduler."""
        print("\nRunning due events...")
        results = await scheduler.run_due_events()
        print(f"Ran {results['ran']} events")
        
        for result in results['results']:
            status = "✓" if result['success'] else "✗"
            print(f"{status} {result['event_id']}")
    
    # Run the example
    asyncio.run(run_scheduler())