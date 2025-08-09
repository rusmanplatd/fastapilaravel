from __future__ import annotations

"""
Schedule Configuration

This file defines the application's command schedule. It's similar to Laravel's 
app/Console/Kernel.php schedule method.

The schedule is defined using a fluent API similar to Laravel's task scheduler.
Commands can be scheduled using cron expressions or human-readable methods.

Examples:
    # Run a command every minute
    schedule.command('inspire').every_minute()
    
    # Run a command daily at 2:30 AM
    schedule.command('emails:send').daily_at('2:30')
    
    # Run a command on weekdays only
    schedule.command('backup:database').daily_at('1:00').weekdays()
    
    # Run a closure-based task
    schedule.call(lambda: print("Hello World")).every_five_minutes()
    
    # Run with conditions
    schedule.command('heavy:task').daily().when(lambda: is_production())
"""

from datetime import datetime
from .Scheduling import schedule
from .Scheduling.SchedulerManager import scheduler


def define_schedule() -> None:
    """Define the application's command schedule."""
    
    # Load schedules into the enhanced scheduler as well
    _load_enhanced_schedule()


def _load_enhanced_schedule() -> None:
    """Load schedules into the enhanced scheduler manager."""
    
    # Example: Send daily reports
    scheduler.command('reports:daily') \
        .daily_at('8:00') \
        .description('Send daily reports to administrators') \
        .email_output_on_failure('admin@example.com')
    
    schedule.command('reports:daily') \
        .daily_at('8:00') \
        .description('Send daily reports to administrators') \
        .email_output_on_failure('admin@example.com')
    
    # Enhanced scheduler examples with new features
    
    # Basic command scheduling
    scheduler.command('cleanup:temp') \
        .hourly() \
        .description('Clean temporary files and cache') \
        .without_overlapping()
    
    # Database maintenance with output logging
    scheduler.command('backup:database') \
        .daily_at('2:00') \
        .description('Create daily database backup') \
        .send_output_to('storage/logs/backup.log') \
        .email_output_on_failure('backup@example.com') \
        .environments('production', 'staging')
    
    # Queue processing with overlap prevention
    scheduler.command('queue:work') \
        .every_minute() \
        .description('Process queued jobs') \
        .without_overlapping() \
        .run_in_background()
    
    # Weekly maintenance
    scheduler.command('sitemap:generate') \
        .weekly_on(0, '3:00') \
        .description('Generate website sitemap') \
        .environments('production')
    
    # Conditional newsletter sending
    scheduler.command('newsletter:send') \
        .weekly_on(1, '9:00') \
        .description('Send weekly newsletter') \
        .when(lambda: is_first_monday_of_month()) \
        .email_output_to('marketing@example.com')
    
    # Health monitoring during business hours
    scheduler.command('system:health-check') \
        .every_five_minutes() \
        .description('Check system health') \
        .between('9:00', '17:00') \
        .weekdays() \
        .ping_before('https://healthchecks.io/ping/health-start') \
        .then_ping('https://healthchecks.io/ping/health-success')
    
    # Session cleanup
    scheduler.command('sessions:cleanup') \
        .daily_at('4:00') \
        .description('Remove expired user sessions')
    
    # Search index updates with maintenance window
    scheduler.command('search:update-index') \
        .hourly_at(15) \
        .description('Update search index') \
        .when(lambda: not is_maintenance_mode()) \
        .unless_between('2:00', '4:00')  # Skip during backup window
    
    # System monitoring with callable
    def log_system_stats() -> None:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            print(f"System stats - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%")
        except ImportError:
            print("psutil not available, skipping system stats")
    
    scheduler.call(log_system_stats) \
        .every_ten_minutes() \
        .description('Log system statistics') \
        .send_output_to('storage/logs/system-stats.log')
    
    # Cache warming during business hours
    scheduler.call(lambda: print("Warming cache...")) \
        .every_fifteen_minutes() \
        .description('Warm application cache') \
        .between('8:00', '19:00') \
        .weekdays()
    
    # Environment-specific scheduling
    if is_production():
        # Production-only monitoring
        scheduler.command('monitor:performance') \
            .every_minute() \
            .description('Monitor application performance') \
            .without_overlapping()
        
        scheduler.command('security:scan') \
            .daily_at('1:30') \
            .description('Run security vulnerability scan') \
            .email_output_on_failure('security@example.com')
        
        # Log rotation for production
        scheduler.command('logs:rotate') \
            .daily_at('23:30') \
            .description('Rotate application logs') \
            .without_overlapping()
    
    else:
        # Development-only tasks
        scheduler.command('dev:refresh-cache') \
            .hourly() \
            .description('Refresh development cache')
        
        scheduler.command('dev:seed-test-data') \
            .daily_at('6:00') \
            .description('Seed test data for development') \
            .environments('development', 'testing')
    
    # Advanced scheduling examples
    
    # Job retry with backoff
    scheduler.command('api:sync-external') \
        .every_thirty_minutes() \
        .description('Sync with external API') \
        .max_attempts(3) \
        .retry_after(5) \
        .email_output_on_failure('integrations@example.com')
    
    # Multi-step process with hooks
    def before_backup() -> None:
        print("Starting backup process...")
    
    def after_backup() -> None:
        print("Backup process completed")
    
    scheduler.command('backup:full') \
        .weekly_on(0, '1:00') \
        .description('Full system backup') \
        .before(before_backup) \
        .after(after_backup) \
        .environments('production') \
        .without_overlapping()
    
    # Time-constrained processing
    scheduler.command('heavy:processing') \
        .daily_at('3:00') \
        .description('Heavy data processing') \
        .unless_between('8:00', '18:00') \
        .weekdays() \
        .on_one_server() \
        .max_attempts(2)
    




def is_production() -> bool:
    """Check if running in production environment."""
    import os
    return os.getenv('APP_ENV', 'development') == 'production'


def is_maintenance_mode() -> bool:
    """Check if application is in maintenance mode."""
    from pathlib import Path
    return Path('storage/framework/down').exists()


def is_first_monday_of_month() -> bool:
    """Check if today is the first Monday of the month."""
    today = datetime.now()
    
    # Check if it's Monday (weekday 0)
    if today.weekday() != 0:
        return False
    
    # Check if it's in the first week of the month
    return today.day <= 7


# Define the schedule when this module is imported
define_schedule()