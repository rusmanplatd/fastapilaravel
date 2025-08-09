from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta
import asyncio
import subprocess
from pathlib import Path

try:
    from croniter import croniter  # type: ignore[import-untyped]
except ImportError:
    # Fallback cron parsing for basic functionality
    class croniter:  # type: ignore[no-redef]
        def __init__(self, cron_expr: str, base_time: datetime) -> None:
            self.cron_expr = cron_expr
            self.base_time = base_time
        
        def get_next(self, ret_type: Any = datetime) -> datetime:
            # Simple fallback - just add 1 minute
            return self.base_time + timedelta(minutes=1)
        
        def get_prev(self, ret_type: Any = datetime) -> datetime:
            # Simple fallback - subtract 1 minute  
            return self.base_time - timedelta(minutes=1)


class Event:
    """Represents a scheduled event."""
    
    def __init__(self, command: Union[str, Callable[..., Any]], arguments: Optional[List[str]] = None) -> None:
        self.command = command
        self.arguments = arguments or []
        self.cron_expression = "* * * * *"  # Default: every minute
        self.timezone: Optional[str] = None
        self._description = ""
        self.mutex: Optional[str] = None
        self._without_overlapping = False
        self._run_in_background = False
        self._on_one_server = False
        self.filters: List[Callable[[], bool]] = []
        self.rejects: List[Callable[[], bool]] = []
        self.before_callbacks: List[Callable[[], Any]] = []
        self.after_callbacks: List[Callable[[], Any]] = []
        self.output_file: Optional[str] = None
        self.append_output = False
        self._email_output_to: List[str] = []
        self._email_output_on_failure: List[str] = []
        self._prevent_overlapping_finish_time: Optional[datetime] = None
    
    def cron(self, expression: str) -> 'Event':
        """Set the cron expression."""
        self.cron_expression = expression
        return self
    
    def every_minute(self) -> 'Event':
        """Run every minute."""
        return self.cron("* * * * *")
    
    def every_five_minutes(self) -> 'Event':
        """Run every five minutes."""
        return self.cron("*/5 * * * *")
    
    def every_ten_minutes(self) -> 'Event':
        """Run every ten minutes."""
        return self.cron("*/10 * * * *")
    
    def every_fifteen_minutes(self) -> 'Event':
        """Run every fifteen minutes."""
        return self.cron("*/15 * * * *")
    
    def every_thirty_minutes(self) -> 'Event':
        """Run every thirty minutes."""
        return self.cron("0,30 * * * *")
    
    def hourly(self) -> 'Event':
        """Run hourly."""
        return self.cron("0 * * * *")
    
    def hourly_at(self, minute: int) -> 'Event':
        """Run hourly at a specific minute."""
        return self.cron(f"{minute} * * * *")
    
    def daily(self) -> 'Event':
        """Run daily at midnight."""
        return self.cron("0 0 * * *")
    
    def daily_at(self, time: str) -> 'Event':
        """Run daily at a specific time (HH:MM)."""
        hour, minute = time.split(":")
        return self.cron(f"{minute} {hour} * * *")
    
    def twice_daily(self, first_hour: int = 1, second_hour: int = 13) -> 'Event':
        """Run twice daily."""
        return self.cron(f"0 {first_hour},{second_hour} * * *")
    
    def weekly(self) -> 'Event':
        """Run weekly on Sunday at midnight."""
        return self.cron("0 0 * * 0")
    
    def weekly_on(self, day: int, time: str = "0:00") -> 'Event':
        """Run weekly on a specific day and time."""
        hour, minute = time.split(":")
        return self.cron(f"{minute} {hour} * * {day}")
    
    def monthly(self) -> 'Event':
        """Run monthly on the first day at midnight."""
        return self.cron("0 0 1 * *")
    
    def monthly_on(self, day: int, time: str = "0:00") -> 'Event':
        """Run monthly on a specific day and time."""
        hour, minute = time.split(":")
        return self.cron(f"{minute} {hour} {day} * *")
    
    def yearly(self) -> 'Event':
        """Run yearly on January 1st at midnight."""
        return self.cron("0 0 1 1 *")
    
    def days(self, *days: int) -> 'Event':
        """Run on specific days of the week."""
        day_str = ",".join(str(d) for d in days)
        return self.cron(f"{self._get_minute()} {self._get_hour()} * * {day_str}")
    
    def weekdays(self) -> 'Event':
        """Run on weekdays (Monday to Friday)."""
        return self.days(1, 2, 3, 4, 5)
    
    def weekends(self) -> 'Event':
        """Run on weekends (Saturday and Sunday)."""
        return self.days(0, 6)
    
    def sundays(self) -> 'Event':
        """Run on Sundays."""
        return self.days(0)
    
    def mondays(self) -> 'Event':
        """Run on Mondays."""
        return self.days(1)
    
    def tuesdays(self) -> 'Event':
        """Run on Tuesdays."""
        return self.days(2)
    
    def wednesdays(self) -> 'Event':
        """Run on Wednesdays."""
        return self.days(3)
    
    def thursdays(self) -> 'Event':
        """Run on Thursdays."""
        return self.days(4)
    
    def fridays(self) -> 'Event':
        """Run on Fridays."""
        return self.days(5)
    
    def saturdays(self) -> 'Event':
        """Run on Saturdays."""
        return self.days(6)
    
    def between(self, start_time: str, end_time: str) -> 'Event':
        """Run between specific times."""
        def time_filter() -> bool:
            now = datetime.now().time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            
            if start <= end:
                return start <= now <= end
            else:  # Crosses midnight
                return now >= start or now <= end
        
        return self.when(time_filter)
    
    def unlessBetween(self, start_time: str, end_time: str) -> 'Event':
        """Skip execution between specific times."""
        def time_filter() -> bool:
            now = datetime.now().time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            
            if start <= end:
                return not (start <= now <= end)
            else:  # Crosses midnight
                return not (now >= start or now <= end)
        
        return self.when(time_filter)
    
    def when(self, callback: Callable[[], bool]) -> 'Event':
        """Add a filter condition."""
        self.filters.append(callback)
        return self
    
    def skip(self, callback: Callable[[], bool]) -> 'Event':
        """Add a rejection condition."""
        self.rejects.append(callback)
        return self
    
    def name(self, description: str) -> 'Event':
        """Set a description for the event."""
        self._description = description
        return self
    
    def description(self, description: str) -> 'Event':
        """Set a description for the event."""
        return self.name(description)
    
    def without_overlapping(self, expires_at: int = 1440) -> 'Event':
        """Prevent overlapping executions."""
        self._without_overlapping = True
        self.mutex = f"laravel_scheduled_command_{hash(str(self.command))}"
        return self
    
    def on_one_server(self) -> 'Event':
        """Run on only one server."""
        self._on_one_server = True
        return self
    
    def run_in_background(self) -> 'Event':
        """Run in background."""
        self._run_in_background = True
        return self
    
    def before(self, callback: Callable[[], Any]) -> 'Event':
        """Add a callback to run before the event."""
        self.before_callbacks.append(callback)
        return self
    
    def after(self, callback: Callable[[], Any]) -> 'Event':
        """Add a callback to run after the event."""
        self.after_callbacks.append(callback)
        return self
    
    def ping_before(self, url: str) -> 'Event':
        """Ping a URL before running."""
        def ping() -> None:
            import requests
            try:
                requests.get(url, timeout=30)
            except Exception:
                pass
        
        return self.before(ping)
    
    def then_ping(self, url: str) -> 'Event':
        """Ping a URL after running."""
        def ping() -> None:
            import requests
            try:
                requests.get(url, timeout=30)
            except Exception:
                pass
        
        return self.after(ping)
    
    def send_output_to(self, location: str, append: bool = False) -> 'Event':
        """Send output to a file."""
        self.output_file = location
        self.append_output = append
        return self
    
    def append_output_to(self, location: str) -> 'Event':
        """Append output to a file."""
        return self.send_output_to(location, True)
    
    def email_output_to(self, *addresses: str) -> 'Event':
        """Email output to addresses."""
        self._email_output_to.extend(addresses)
        return self
    
    def email_output_on_failure(self, *addresses: str) -> 'Event':
        """Email output on failure to addresses."""
        self._email_output_on_failure.extend(addresses)
        return self
    
    def is_due(self, now: Optional[datetime] = None) -> bool:
        """Check if the event is due to run."""
        if now is None:
            now = datetime.now()
        
        # Check if it's time according to cron
        cron = croniter(self.cron_expression, now)
        next_run = cron.get_prev(datetime)
        time_diff = (now - next_run).total_seconds()
        
        # Must be within the last minute to be considered due
        if time_diff > 60:
            return False
        
        # Check filters
        for filter_func in self.filters:
            if not filter_func():
                return False
        
        # Check rejects
        for reject_func in self.rejects:
            if reject_func():
                return False
        
        # Check for overlapping prevention
        if self._without_overlapping and self._is_running():
            return False
        
        return True
    
    def next_run_date(self, now: Optional[datetime] = None) -> datetime:
        """Get the next run date."""
        if now is None:
            now = datetime.now()
        
        cron = croniter(self.cron_expression, now)
        next_time = cron.get_next(return_type=datetime)
        # croniter.get_next with return_type=datetime should return datetime directly
        if isinstance(next_time, datetime):
            return next_time
        elif isinstance(next_time, (int, float)):
            return datetime.fromtimestamp(next_time)
        else:
            # Fallback to current time if unable to parse
            return datetime.now()
    
    async def run(self) -> int:
        """Execute the event."""
        # Run before callbacks
        for callback in self.before_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
        
        exit_code = 0
        
        try:
            if callable(self.command):
                # Callable command
                if asyncio.iscoroutinefunction(self.command):
                    await self.command()
                else:
                    self.command()
            else:
                # String command (shell command or Artisan command)
                if self.command.startswith("python"):
                    # Shell command
                    process = await asyncio.create_subprocess_shell(
                        f"{self.command} {' '.join(self.arguments)}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    exit_code = process.returncode or 0
                    
                    # Handle output
                    if self.output_file:
                        mode = "a" if self.append_output else "w"
                        with open(self.output_file, mode) as f:
                            f.write(stdout.decode())
                            if stderr:
                                f.write(stderr.decode())
                else:
                    # Artisan command
                    from ..Kernel import artisan
                    exit_code = await artisan.call(self.command, {
                        arg: True if arg.startswith("--") else arg 
                        for arg in self.arguments
                    })
        
        except Exception as e:
            exit_code = 1
            print(f"Scheduled command failed: {e}")
        
        finally:
            # Run after callbacks
            for callback in self.after_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
        
        return exit_code
    
    def _get_minute(self) -> str:
        """Extract minute from cron expression."""
        return self.cron_expression.split()[0]
    
    def _get_hour(self) -> str:
        """Extract hour from cron expression."""
        return self.cron_expression.split()[1]
    
    def _is_running(self) -> bool:
        """Check if the command is currently running."""
        # Simple implementation - in production you'd use a more robust mutex
        if not self.mutex:
            return False
        
        mutex_file = f"/tmp/{self.mutex}.lock"
        if Path(mutex_file).exists():
            # Check if the process is still running
            try:
                with open(mutex_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Check if process exists
                try:
                    import psutil
                    return psutil.pid_exists(pid)
                except ImportError:
                    # Fallback: check if pid exists using os
                    import os
                    try:
                        os.kill(pid, 0)
                        return True
                    except OSError:
                        return False
            except Exception:
                # Remove stale lock file
                Path(mutex_file).unlink(missing_ok=True)
        
        return False


class Schedule:
    """The schedule class manages all scheduled events."""
    
    def __init__(self) -> None:
        self.events: List[Event] = []
        self.mutex_resolver: Optional[Callable[[str], Any]] = None
    
    def command(self, command: str, arguments: Optional[List[str]] = None) -> Event:
        """Schedule an Artisan command."""
        event = Event(command, arguments or [])
        self.events.append(event)
        return event
    
    def exec(self, command: str, arguments: Optional[List[str]] = None) -> Event:
        """Schedule a shell command."""
        event = Event(f"python {command}", arguments or [])
        self.events.append(event)
        return event
    
    def call(self, callback: Callable[..., Any], arguments: Optional[List[str]] = None) -> Event:
        """Schedule a callable."""
        event = Event(callback, arguments or [])
        self.events.append(event)
        return event
    
    def due_events(self, now: Optional[datetime] = None) -> List[Event]:
        """Get all events that are due to run."""
        if now is None:
            now = datetime.now()
        
        return [event for event in self.events if event.is_due(now)]
    
    async def run(self, now: Optional[datetime] = None) -> List[int]:
        """Run all due events."""
        due_events = self.due_events(now)
        results = []
        
        for event in due_events:
            try:
                result = await event.run()
                results.append(result)
            except Exception as e:
                print(f"Error running scheduled event: {e}")
                results.append(1)
        
        return results


# Global schedule instance
schedule = Schedule()