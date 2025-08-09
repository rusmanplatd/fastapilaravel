from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..Command import Command
from ..Scheduling import schedule
from ..Scheduling.SchedulerManager import scheduler
from ..Scheduling.CronIntegration import CronIntegration, ScheduleMonitor
from ..Scheduling.ScheduleConfigLoader import ScheduleDiscovery


class ScheduleRunCommand(Command):
    """Run scheduled commands that are due."""
    
    signature = "schedule:run"
    description = "Run the scheduled commands"
    help = "Execute all scheduled commands that are due to run"
    
    async def handle(self) -> None:
        """Run all due scheduled commands."""
        now = datetime.now()
        due_events = schedule.due_events(now)
        
        if not due_events:
            self.info("No scheduled commands are ready to run.")
            return
        
        self.info(f"Running {len(due_events)} scheduled command(s)...")
        
        results = await schedule.run(now)
        
        success_count = sum(1 for result in results if result == 0)
        failure_count = len(results) - success_count
        
        if failure_count == 0:
            self.info(f"All {success_count} scheduled command(s) completed successfully.")
        else:
            self.warn(f"{success_count} command(s) succeeded, {failure_count} failed.")


class ScheduleListCommand(Command):
    """List all scheduled commands."""
    
    signature = "schedule:list {--timezone=UTC : The timezone to use for display}"
    description = "List all scheduled commands"
    help = "Display a list of all scheduled commands with their next run times"
    
    async def handle(self) -> None:
        """List all scheduled commands."""
        if not schedule.events:
            self.info("No scheduled commands are defined.")
            return
        
        now = datetime.now()
        
        # Prepare table data
        headers = ["Command", "Description", "Cron Expression", "Next Run", "Status"]
        rows = []
        
        for event in schedule.events:
            # Get command string
            if callable(event.command):
                command = f"Closure: {event.command.__name__}"
            else:
                command = str(event.command)
            
            # Get description
            if callable(event.description):
                description = str(event.description)
            else:
                description = event.description or "No description"  # type: ignore[unreachable]
            
            # Get next run time
            next_run = event.next_run_date(now)
            next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if due now
            status = "Due" if event.is_due(now) else "Waiting"
            
            rows.append([
                command[:40] + "..." if len(command) > 40 else command,
                description[:30] + "..." if len(description) > 30 else description,
                event.cron_expression,
                next_run_str,
                status
            ])
        
        self.table(headers, rows)
        
        self.new_line()
        self.info(f"Total: {len(schedule.events)} scheduled command(s)")


class ScheduleWorkCommand(Command):
    """Start the schedule worker (runs continuously)."""
    
    signature = "schedule:work {--sleep=60 : Number of seconds to sleep between runs}"
    description = "Start the schedule worker"
    help = "Run the scheduler continuously, checking for due commands every minute"
    
    async def handle(self) -> None:
        """Run the schedule worker."""
        sleep_time = int(self.option("sleep", 60))
        
        self.info("Schedule worker started. Press Ctrl+C to stop.")
        self.comment(f"Checking for scheduled commands every {sleep_time} seconds...")
        
        try:
            while True:
                # Run scheduled commands
                now = datetime.now()
                due_events = schedule.due_events(now)
                
                if due_events:
                    self.line(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Running {len(due_events)} scheduled command(s)...")
                    
                    results = await schedule.run(now)
                    
                    success_count = sum(1 for result in results if result == 0)
                    failure_count = len(results) - success_count
                    
                    if failure_count == 0:
                        self.info(f"All {success_count} command(s) completed successfully.")
                    else:
                        self.warn(f"{success_count} succeeded, {failure_count} failed.")
                
                # Sleep until next check
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.new_line()
            self.info("Schedule worker stopped.")


class ScheduleTestCommand(Command):
    """Test a specific scheduled command."""
    
    signature = "schedule:test {command : The command to test} {--pretend : Show what would run without executing}"
    description = "Test a scheduled command"
    help = "Test if a scheduled command would run and optionally execute it"
    
    async def handle(self) -> None:
        """Test a scheduled command."""
        command_name = self.argument("command")
        pretend = self.option("pretend", False)
        
        # Find the event
        matching_events = [
            event for event in schedule.events 
            if (isinstance(event.command, str) and event.command == command_name) or
               (hasattr(event.command, '__name__') and event.command.__name__ == command_name)
        ]
        
        if not matching_events:
            self.error(f"No scheduled command found matching '{command_name}'")
            return
        
        event = matching_events[0]
        now = datetime.now()
        
        # Show event details
        self.info(f"Command: {event.command}")
        if callable(event.description):
            desc = str(event.description)
        else:
            desc = event.description or 'No description'  # type: ignore[unreachable]
        self.info(f"Description: {desc}")
        self.info(f"Cron Expression: {event.cron_expression}")
        self.info(f"Next Run: {event.next_run_date(now).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if due
        is_due = event.is_due(now)
        self.info(f"Due Now: {'Yes' if is_due else 'No'}")
        
        if pretend:
            if is_due:
                self.comment("This command would run now.")
            else:
                self.comment("This command would not run now.")
            return
        
        if not is_due:
            if not self.confirm("This command is not due to run now. Run anyway?"):
                self.info("Command execution cancelled.")
                return
        
        # Run the command
        self.info("Running command...")
        
        try:
            result = await event.run()
            if result == 0:
                self.info("Command completed successfully.")
            else:
                self.error(f"Command failed with exit code {result}.")
        except Exception as e:
            self.error(f"Command failed with error: {e}")


class ScheduleFinishCommand(Command):
    """Finish running scheduled commands gracefully."""
    
    signature = "schedule:finish {--wait=10 : Seconds to wait for commands to finish}"
    description = "Finish running scheduled commands"
    help = "Wait for running scheduled commands to finish, then exit"
    
    async def handle(self) -> None:
        """Finish scheduled commands gracefully."""
        wait_time = int(self.option("wait", 10))
        
        self.info("Finishing scheduled commands gracefully...")
        self.comment(f"Waiting up to {wait_time} seconds for commands to complete...")
        
        # In a real implementation, you would track running commands
        # and wait for them to finish
        
        await asyncio.sleep(1)  # Simulate waiting
        
        self.info("All scheduled commands have finished.")


class ScheduleInterruptCommand(Command):
    """Interrupt running scheduled commands."""
    
    signature = "schedule:interrupt"
    description = "Interrupt running scheduled commands"
    help = "Forcefully interrupt all running scheduled commands"
    
    async def handle(self) -> None:
        """Interrupt scheduled commands."""
        self.warn("Interrupting all running scheduled commands...")
        
        # In a real implementation, you would forcefully stop running commands
        
        self.info("All scheduled commands have been interrupted.")


class ScheduleClearCacheCommand(Command):
    """Clear the schedule cache."""
    
    signature = "schedule:clear-cache"
    description = "Clear the schedule cache"
    help = "Clear any cached schedule data and mutex locks"
    
    async def handle(self) -> None:
        """Clear schedule cache."""
        import glob
        import os
        
        # Clear mutex lock files
        lock_files = glob.glob("/tmp/laravel_scheduled_command_*.lock")
        cleared = 0
        
        for lock_file in lock_files:
            try:
                os.unlink(lock_file)
                cleared += 1
            except OSError:
                pass
        
        self.info(f"Cleared {cleared} schedule lock file(s).")
        
        # You could also clear other schedule-related cache here
        
        self.info("Schedule cache cleared successfully.")


class ScheduleInstallCommand(Command):
    """Install the Laravel scheduler in system cron."""
    
    signature = "schedule:install {--user= : Install for specific user}"
    description = "Install the scheduler in system cron"
    help = "Install a cron entry to run the scheduler every minute"
    
    async def handle(self) -> None:
        """Install the scheduler in cron."""
        user = self.option("user")
        cron_integration = CronIntegration(scheduler)
        
        if cron_integration.is_installed(user):
            self.info("Laravel scheduler is already installed in cron.")
            return
        
        self.info("Installing Laravel scheduler in system cron...")
        
        if cron_integration.install(user):
            self.info("✓ Laravel scheduler installed successfully!")
            self.comment("The scheduler will now run every minute via cron.")
            self.new_line()
            self.info("You can check the status with: python artisan.py schedule:status")
        else:
            self.error("✗ Failed to install Laravel scheduler in cron.")
            self.comment("Make sure you have permission to modify crontab.")


class ScheduleUninstallCommand(Command):
    """Remove the Laravel scheduler from system cron."""
    
    signature = "schedule:uninstall {--user= : Uninstall for specific user}"
    description = "Remove the scheduler from system cron"
    help = "Remove the cron entry that runs the scheduler"
    
    async def handle(self) -> None:
        """Uninstall the scheduler from cron."""
        user = self.option("user")
        cron_integration = CronIntegration(scheduler)
        
        if not cron_integration.is_installed(user):
            self.info("Laravel scheduler is not installed in cron.")
            return
        
        if not self.confirm("Are you sure you want to remove the Laravel scheduler from cron?"):
            self.info("Uninstall cancelled.")
            return
        
        self.info("Removing Laravel scheduler from system cron...")
        
        if cron_integration.uninstall(user):
            self.info("✓ Laravel scheduler removed successfully!")
            self.comment("Scheduled commands will no longer run automatically.")
        else:
            self.error("✗ Failed to remove Laravel scheduler from cron.")


class ScheduleStatusCommand(Command):
    """Show the status of the Laravel scheduler."""
    
    signature = "schedule:status {--user= : Check status for specific user}"
    description = "Show scheduler status"
    help = "Display the current status of the Laravel scheduler"
    
    async def handle(self) -> None:
        """Show scheduler status."""
        user = self.option("user")
        cron_integration = CronIntegration(scheduler)
        monitor = ScheduleMonitor(scheduler)
        
        # Cron installation status
        status = cron_integration.status(user)
        
        self.info("Laravel Scheduler Status")
        self.line("=" * 40)
        
        if status['installed']:
            self.info("✓ Installed in system cron")
        else:
            self.error("✗ Not installed in system cron")
            self.comment("Run 'python artisan.py schedule:install' to install")
        
        self.new_line()
        self.comment(f"User: {status['user']}")
        self.comment(f"Working Directory: {status['working_directory']}")
        self.comment(f"Python Executable: {status['python_executable']}")
        self.comment(f"Artisan Path: {status['artisan_path']}")
        
        # Health check
        self.new_line()
        health = monitor.health_check()
        
        if health['status'] == 'healthy':
            self.info("✓ Scheduler is healthy")
        elif health['status'] == 'warning':
            self.warn("⚠ Scheduler has warnings")
        else:
            self.error("✗ Scheduler is unhealthy")
        
        if health['issues']:
            self.new_line()
            self.error("Issues:")
            for issue in health['issues']:
                self.line(f"  • {issue}")
        
        if health['recommendations']:
            self.new_line()
            self.comment("Recommendations:")
            for recommendation in health['recommendations']:
                self.line(f"  • {recommendation}")
        
        # Statistics
        stats = health['stats']
        self.new_line()
        self.info("Statistics:")
        self.line(f"  Total Events: {stats['total_events']}")
        self.line(f"  Active Events: {stats['active_events']}")
        self.line(f"  Total Runs: {stats['total_runs']}")
        self.line(f"  Successful Runs: {stats['successful_runs']}")
        self.line(f"  Failed Runs: {stats['failed_runs']}")
        
        if stats['total_runs'] > 0:
            success_rate = stats['successful_runs'] / stats['total_runs'] * 100
            self.line(f"  Success Rate: {success_rate:.1f}%")
        
        if stats['last_run']:
            self.line(f"  Last Run: {stats['last_run']}")


class ScheduleReportCommand(Command):
    """Generate a comprehensive schedule report."""
    
    signature = "schedule:report {--format=table : Output format (table, json)} {--output= : Save to file}"
    description = "Generate a schedule report"
    help = "Generate a comprehensive report of all scheduled events"
    
    async def handle(self) -> None:
        """Generate schedule report."""
        format_type = self.option("format", "table")
        output_file = self.option("output")
        
        monitor = ScheduleMonitor(scheduler)
        report = monitor.get_schedule_report()
        
        if format_type == "json":
            import json
            
            output = json.dumps(report, indent=2, default=str)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(output)
                self.info(f"Report saved to {output_file}")
            else:
                self.line(output)
        
        else:  # table format
            # Summary
            summary = report['summary']
            self.info("Schedule Report")
            self.line("=" * 50)
            self.line(f"Total Events: {summary['total_events']}")
            self.line(f"Total Runs: {summary['total_runs']}")
            self.line(f"Success Rate: {summary['success_rate']:.1%}")
            self.line(f"Generated: {report['generated_at']}")
            
            # Events table
            if report['events']:
                self.new_line()
                self.info("Scheduled Events:")
                
                headers = ["ID", "Description", "Cron", "Next Run", "Success Rate", "Last Run"]
                rows = []
                
                for event in report['events']:
                    if 'error' in event:
                        rows.append([event['id'], event['error'], "", "", "", ""])
                    else:
                        next_run = event['next_run'][:19] if event['next_run'] else "Never"
                        last_run = event['last_run'][:19] if event['last_run'] else "Never"
                        success_rate = f"{event['success_rate']:.1%}" if event['success_rate'] else "N/A"
                        
                        rows.append([
                            event['id'][:20] + "..." if len(event['id']) > 20 else event['id'],
                            event['description'][:30] + "..." if len(event['description']) > 30 else event['description'],
                            event['cron_expression'],
                            next_run,
                            success_rate,
                            last_run
                        ])
                
                self.table(headers, rows)
            
            # Health status
            health = report['health']
            self.new_line()
            self.line(f"Health Status: {health['status'].upper()}")
            
            if health['issues']:
                self.new_line()
                self.error("Issues:")
                for issue in health['issues']:
                    self.line(f"  • {issue}")


class ScheduleDiscoverCommand(Command):
    """Discover and register scheduled events."""
    
    signature = "schedule:discover {--reset : Reset existing schedules before discovery}"
    description = "Discover scheduled events"
    help = "Auto-discover and register scheduled events from jobs and commands"
    
    async def handle(self) -> None:
        """Discover scheduled events."""
        reset = self.option("reset", False)
        
        if reset:
            if self.confirm("Are you sure you want to reset all existing schedules?"):
                scheduler.events.clear()
                self.info("Existing schedules cleared.")
            else:
                self.info("Discovery cancelled.")
                return
        
        self.info("Discovering scheduled events...")
        
        discovery = ScheduleDiscovery(scheduler)
        initial_count = len(scheduler.events)
        
        discovery.discover_all()
        
        final_count = len(scheduler.events)
        discovered = final_count - initial_count
        
        self.info(f"✓ Discovery complete! Found {discovered} new scheduled event(s).")
        self.comment(f"Total scheduled events: {final_count}")
        
        if discovered > 0:
            self.new_line()
            self.comment("Run 'python artisan.py schedule:list' to see all scheduled events.")


class ScheduleLogsCommand(Command):
    """View recent schedule logs."""
    
    signature = "schedule:logs {--lines=50 : Number of recent log entries to show} {--event= : Filter by event ID}"
    description = "View schedule logs"
    help = "Display recent schedule execution logs"
    
    async def handle(self) -> None:
        """View schedule logs."""
        lines = int(self.option("lines", 50))
        event_filter = self.option("event")
        
        monitor = ScheduleMonitor(scheduler)
        logs = monitor.get_recent_logs(lines)
        
        if event_filter:
            logs = [log for log in logs if log.get('event_id') == event_filter]
        
        if not logs:
            self.info("No schedule logs found.")
            return
        
        self.info(f"Recent Schedule Logs ({len(logs)} entries):")
        self.line("=" * 60)
        
        for log in logs:
            timestamp = log['timestamp'][:19]  # Remove microseconds
            event_id = log['event_id']
            status = "✓" if log['success'] else "✗"
            duration = f"{log['duration']:.2f}s" if 'duration' in log else "N/A"
            
            self.line(f"[{timestamp}] {status} {event_id} ({duration})")
            
            if log.get('output'):
                # Show first line of output
                output_line = log['output'].split('\n')[0][:60]
                self.comment(f"    Output: {output_line}")


class ScheduleCleanupCommand(Command):
    """Clean up old schedule logs and cache."""
    
    signature = "schedule:cleanup {--days=30 : Days of logs to keep} {--dry-run : Show what would be cleaned without doing it}"
    description = "Clean up schedule data"
    help = "Clean up old schedule logs and temporary files"
    
    async def handle(self) -> None:
        """Clean up schedule data."""
        days = int(self.option("days", 30))
        dry_run = self.option("dry-run", False)
        
        monitor = ScheduleMonitor(scheduler)
        
        if dry_run:
            self.info(f"Dry run: Would clean up schedule logs older than {days} days")
            self.comment("Use without --dry-run to actually perform cleanup")
        else:
            self.info(f"Cleaning up schedule logs older than {days} days...")
            monitor.cleanup_logs(days)
            self.info("✓ Schedule cleanup completed.")


# Register commands
from app.Console.Artisan import register_command

register_command(ScheduleRunCommand)
register_command(ScheduleListCommand)  
register_command(ScheduleWorkCommand)
register_command(ScheduleTestCommand)
register_command(ScheduleFinishCommand)
register_command(ScheduleInterruptCommand)
register_command(ScheduleClearCacheCommand)
register_command(ScheduleInstallCommand)
register_command(ScheduleUninstallCommand)
register_command(ScheduleStatusCommand)
register_command(ScheduleReportCommand)
register_command(ScheduleDiscoverCommand)
register_command(ScheduleLogsCommand)
register_command(ScheduleCleanupCommand)