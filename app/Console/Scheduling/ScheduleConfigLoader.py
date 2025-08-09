from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Type, Union
import importlib
import json
from pathlib import Path
from datetime import datetime

from .SchedulerManager import SchedulerManager
from app.Jobs.Job import Job


class ScheduleConfigLoader:
    """Load and configure scheduled events from various sources."""
    
    def __init__(self, scheduler: SchedulerManager):
        self.scheduler = scheduler
        self.config_paths = [
            'config/schedule.py',
            'app/Console/schedule.py',
            'routes/schedule.py'
        ]
    
    def load_from_file(self, file_path: str) -> None:
        """Load schedule configuration from a Python file."""
        try:
            # Convert file path to module path
            module_path = file_path.replace('/', '.').replace('.py', '')
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Look for schedule function
            if hasattr(module, 'schedule'):
                schedule_func = getattr(module, 'schedule')
                if callable(schedule_func):
                    schedule_func(self.scheduler)
            
            # Look for individual schedule methods
            for attr_name in dir(module):
                if attr_name.startswith('schedule_'):
                    attr = getattr(module, attr_name)
                    if callable(attr):
                        attr(self.scheduler)
        
        except ImportError as e:
            print(f"Could not import schedule file {file_path}: {e}")
        except Exception as e:
            print(f"Error loading schedule from {file_path}: {e}")
    
    def load_from_config(self, config: Dict[str, Any]) -> None:
        """Load schedule configuration from a dictionary."""
        for event_config in config.get('events', []):
            self._create_event_from_config(event_config)
    
    def load_from_json(self, json_path: str) -> None:
        """Load schedule configuration from a JSON file."""
        try:
            with open(json_path, 'r') as f:
                config = json.load(f)
            self.load_from_config(config)
        except FileNotFoundError:
            print(f"Schedule config file not found: {json_path}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in schedule config: {e}")
    
    def load_default_schedules(self) -> None:
        """Load schedules from default locations."""
        for config_path in self.config_paths:
            if Path(config_path).exists():
                self.load_from_file(config_path)
    
    def _create_event_from_config(self, config: Dict[str, Any]) -> None:
        """Create a scheduled event from configuration."""
        event_type = config.get('type', 'command')
        
        if event_type == 'command':
            builder = self.scheduler.command(
                config['command'],
                config.get('arguments', [])
            )
        elif event_type == 'exec':
            builder = self.scheduler.exec(
                config['command'],
                config.get('arguments', [])
            )
        elif event_type == 'job':
            job_class = self._resolve_job_class(config['job'])
            builder = self.scheduler.job(job_class)
        elif event_type == 'callable':
            callable_func = self._resolve_callable(config['callable'])
            builder = self.scheduler.call(callable_func)
        else:
            raise ValueError(f"Unknown event type: {event_type}")
        
        # Apply schedule configuration
        self._apply_schedule_config(builder, config)
    
    def _apply_schedule_config(self, builder: Any, config: Dict[str, Any]) -> None:
        """Apply configuration to a schedule event builder."""
        # Basic scheduling
        if 'cron' in config:
            builder.cron(config['cron'])
        elif 'frequency' in config:
            frequency = config['frequency']
            if frequency == 'every_minute':
                builder.every_minute()
            elif frequency == 'every_five_minutes':
                builder.every_five_minutes()
            elif frequency == 'every_ten_minutes':
                builder.every_ten_minutes()
            elif frequency == 'every_fifteen_minutes':
                builder.every_fifteen_minutes()
            elif frequency == 'every_thirty_minutes':
                builder.every_thirty_minutes()
            elif frequency == 'hourly':
                builder.hourly()
            elif frequency == 'daily':
                builder.daily()
            elif frequency == 'weekly':
                builder.weekly()
            elif frequency == 'monthly':
                builder.monthly()
            elif frequency == 'yearly':
                builder.yearly()
            elif frequency == 'weekdays':
                builder.weekdays()
            elif frequency == 'weekends':
                builder.weekends()
            elif isinstance(frequency, dict):
                if 'hourly_at' in frequency:
                    builder.hourly_at(frequency['hourly_at'])
                elif 'daily_at' in frequency:
                    builder.daily_at(frequency['daily_at'])
                elif 'weekly_on' in frequency:
                    builder.weekly_on(
                        frequency['weekly_on'].get('day'),
                        frequency['weekly_on'].get('time', '0:00')
                    )
                elif 'monthly_on' in frequency:
                    builder.monthly_on(
                        frequency['monthly_on'].get('day'),
                        frequency['monthly_on'].get('time', '0:00')
                    )
                elif 'twice_daily' in frequency:
                    builder.twice_daily(
                        frequency['twice_daily'].get('first_hour', 1),
                        frequency['twice_daily'].get('second_hour', 13)
                    )
        
        # Configuration options
        if 'description' in config:
            builder.description(config['description'])
        
        if 'environments' in config:
            builder.environments(*config['environments'])
        
        if 'timezone' in config:
            builder.timezone(config['timezone'])
        
        if config.get('without_overlapping'):
            builder.without_overlapping()
        
        if config.get('on_one_server'):
            builder.on_one_server()
        
        if config.get('run_in_background'):
            builder.run_in_background()
        
        # Time constraints
        if 'between' in config:
            between = config['between']
            builder.between(between['start'], between['end'])
        
        if 'unless_between' in config:
            unless_between = config['unless_between']
            builder.unless_between(unless_between['start'], unless_between['end'])
        
        # Output and notifications
        if 'output_file' in config:
            builder.send_output_to(config['output_file'])
        
        if 'email_output_to' in config:
            builder.email_output_to(*config['email_output_to'])
        
        if 'email_on_failure' in config:
            builder.email_output_on_failure(*config['email_on_failure'])
        
        # Webhooks
        if 'ping_before' in config:
            builder.ping_before(config['ping_before'])
        
        if 'then_ping' in config:
            builder.then_ping(config['then_ping'])
        
        # Retry configuration
        if 'retry_after' in config:
            builder.retry_after(config['retry_after'])
        
        if 'max_attempts' in config:
            builder.max_attempts(config['max_attempts'])
    
    def _resolve_job_class(self, job_name: str) -> Type[Job]:
        """Resolve a job class from its name."""
        try:
            # Try to import as module path
            if '.' in job_name:
                module_path, class_name = job_name.rsplit('.', 1)
                module = importlib.import_module(module_path)
                return getattr(module, class_name)
            else:
                # Try common job locations
                for location in ['app.Jobs', 'app.Console.Commands']:
                    try:
                        module = importlib.import_module(f"{location}.{job_name}")
                        return getattr(module, job_name)
                    except ImportError:
                        continue
                
                raise ImportError(f"Could not find job class: {job_name}")
        
        except Exception as e:
            raise ValueError(f"Could not resolve job class {job_name}: {e}")
    
    def _resolve_callable(self, callable_name: str) -> Callable:
        """Resolve a callable from its name."""
        try:
            # Try to import as module path
            if '.' in callable_name:
                module_path, func_name = callable_name.rsplit('.', 1)
                module = importlib.import_module(module_path)
                return getattr(module, func_name)
            else:
                raise ValueError(f"Callable must include module path: {callable_name}")
        
        except Exception as e:
            raise ValueError(f"Could not resolve callable {callable_name}: {e}")


class ScheduleDiscovery:
    """Discover and register scheduled events from various sources."""
    
    def __init__(self, scheduler: SchedulerManager):
        self.scheduler = scheduler
        self.loader = ScheduleConfigLoader(scheduler)
    
    def discover_all(self) -> None:
        """Discover and load all scheduled events."""
        # Load from default configuration files
        self.loader.load_default_schedules()
        
        # Load from JSON configuration
        json_config_path = 'config/schedule.json'
        if Path(json_config_path).exists():
            self.loader.load_from_json(json_config_path)
        
        # Auto-discover from job classes
        self._discover_scheduled_jobs()
        
        # Auto-discover from command classes
        self._discover_scheduled_commands()
    
    def _discover_scheduled_jobs(self) -> None:
        """Auto-discover jobs that should be scheduled."""
        # This would scan for job classes with scheduling attributes
        jobs_dir = Path('app/Jobs')
        if not jobs_dir.exists():
            return
        
        for job_file in jobs_dir.glob('**/*.py'):
            if job_file.name.startswith('_'):
                continue
            
            try:
                # Import the job module
                module_path = str(job_file.relative_to(Path('.'))).replace('/', '.').replace('.py', '')
                module = importlib.import_module(module_path)
                
                # Look for job classes with schedule attributes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    if (isinstance(attr, type) and 
                        issubclass(attr, Job) and 
                        hasattr(attr, '__schedule__')):
                        
                        schedule_config = attr.__schedule__
                        self._create_job_schedule(attr, schedule_config)
            
            except Exception as e:
                print(f"Error discovering jobs in {job_file}: {e}")
    
    def _discover_scheduled_commands(self) -> None:
        """Auto-discover commands that should be scheduled."""
        # This would scan for command classes with scheduling attributes
        commands_dir = Path('app/Console/Commands')
        if not commands_dir.exists():
            return
        
        for command_file in commands_dir.glob('**/*.py'):
            if command_file.name.startswith('_'):
                continue
            
            try:
                # Import the command module
                module_path = str(command_file.relative_to(Path('.'))).replace('/', '.').replace('.py', '')
                module = importlib.import_module(module_path)
                
                # Look for command classes with schedule attributes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    if (hasattr(attr, 'signature') and 
                        hasattr(attr, '__schedule__')):
                        
                        schedule_config = attr.__schedule__
                        command_name = attr.signature
                        self._create_command_schedule(command_name, schedule_config)
            
            except Exception as e:
                print(f"Error discovering commands in {command_file}: {e}")
    
    def _create_job_schedule(self, job_class: Type[Job], schedule_config: Dict[str, Any]) -> None:
        """Create a schedule for a job class."""
        builder = self.scheduler.job(job_class)
        self.loader._apply_schedule_config(builder, schedule_config)
    
    def _create_command_schedule(self, command_name: str, schedule_config: Dict[str, Any]) -> None:
        """Create a schedule for a command."""
        builder = self.scheduler.command(command_name)
        self.loader._apply_schedule_config(builder, schedule_config)


# Schedule decorators for easy job/command scheduling
def scheduled(**schedule_config: Any) -> Callable:
    """Decorator to mark a job or command as scheduled."""
    def decorator(cls: Type) -> Type:
        cls.__schedule__ = schedule_config
        return cls
    return decorator


def every_minute() -> Callable:
    """Decorator to schedule a job/command every minute."""
    return scheduled(frequency='every_minute')


def every_five_minutes() -> Callable:
    """Decorator to schedule a job/command every five minutes."""
    return scheduled(frequency='every_five_minutes')


def every_ten_minutes() -> Callable:
    """Decorator to schedule a job/command every ten minutes."""
    return scheduled(frequency='every_ten_minutes')


def every_fifteen_minutes() -> Callable:
    """Decorator to schedule a job/command every fifteen minutes."""
    return scheduled(frequency='every_fifteen_minutes')


def every_thirty_minutes() -> Callable:
    """Decorator to schedule a job/command every thirty minutes."""
    return scheduled(frequency='every_thirty_minutes')


def hourly(minute: int = 0) -> Callable:
    """Decorator to schedule a job/command hourly."""
    if minute == 0:
        return scheduled(frequency='hourly')
    else:
        return scheduled(frequency={'hourly_at': minute})


def daily(time: str = '0:00') -> Callable:
    """Decorator to schedule a job/command daily."""
    if time == '0:00':
        return scheduled(frequency='daily')
    else:
        return scheduled(frequency={'daily_at': time})


def weekly(day: int = 0, time: str = '0:00') -> Callable:
    """Decorator to schedule a job/command weekly."""
    if day == 0 and time == '0:00':
        return scheduled(frequency='weekly')
    else:
        return scheduled(frequency={'weekly_on': {'day': day, 'time': time}})


def monthly(day: int = 1, time: str = '0:00') -> Callable:
    """Decorator to schedule a job/command monthly."""
    if day == 1 and time == '0:00':
        return scheduled(frequency='monthly')
    else:
        return scheduled(frequency={'monthly_on': {'day': day, 'time': time}})


def weekdays() -> Callable:
    """Decorator to schedule a job/command on weekdays."""
    return scheduled(frequency='weekdays')


def weekends() -> Callable:
    """Decorator to schedule a job/command on weekends."""
    return scheduled(frequency='weekends')


def cron(expression: str) -> Callable:
    """Decorator to schedule a job/command with a custom cron expression."""
    return scheduled(cron=expression)


def environments(*envs: str) -> Callable:
    """Decorator to limit job/command to specific environments."""
    def decorator(cls: Type) -> Type:
        existing_schedule = getattr(cls, '__schedule__', {})
        existing_schedule['environments'] = list(envs)
        cls.__schedule__ = existing_schedule
        return cls
    return decorator


def without_overlapping() -> Callable:
    """Decorator to prevent overlapping executions."""
    def decorator(cls: Type) -> Type:
        existing_schedule = getattr(cls, '__schedule__', {})
        existing_schedule['without_overlapping'] = True
        cls.__schedule__ = existing_schedule
        return cls
    return decorator


def on_one_server() -> Callable:
    """Decorator to run job/command on only one server."""
    def decorator(cls: Type) -> Type:
        existing_schedule = getattr(cls, '__schedule__', {})
        existing_schedule['on_one_server'] = True
        cls.__schedule__ = existing_schedule
        return cls
    return decorator