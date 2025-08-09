from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import subprocess
import tempfile
import os
from pathlib import Path
from datetime import datetime

from .SchedulerManager import SchedulerManager


class CronIntegration:
    """Integration with system cron for Laravel-style scheduling."""
    
    def __init__(self, scheduler: SchedulerManager):
        self.scheduler = scheduler
        self.cron_identifier = "# Laravel FastAPI Schedule"
        self.python_executable = "python"
        self.artisan_path = "artisan.py"
    
    def install(self, user: Optional[str] = None) -> bool:
        """Install the scheduler in the system cron."""
        try:
            # Get current crontab
            current_cron = self._get_current_crontab(user)
            
            # Check if already installed
            if self.cron_identifier in current_cron:
                print("Laravel scheduler is already installed in cron.")
                return True
            
            # Add our schedule entry
            schedule_entry = self._generate_cron_entry()
            new_cron = current_cron.strip() + "\n" + schedule_entry + "\n"
            
            # Install the new crontab
            if self._set_crontab(new_cron, user):
                print("Laravel scheduler installed successfully.")
                return True
            else:
                print("Failed to install Laravel scheduler in cron.")
                return False
        
        except Exception as e:
            print(f"Error installing scheduler: {e}")
            return False
    
    def uninstall(self, user: Optional[str] = None) -> bool:
        """Remove the scheduler from the system cron."""
        try:
            # Get current crontab
            current_cron = self._get_current_crontab(user)
            
            # Remove our entries
            lines = current_cron.split('\n')
            filtered_lines = []
            skip_next = False
            
            for line in lines:
                if self.cron_identifier in line:
                    skip_next = True
                    continue
                
                if skip_next and line.strip().startswith('*'):
                    skip_next = False
                    continue
                
                skip_next = False
                filtered_lines.append(line)
            
            new_cron = '\n'.join(filtered_lines)
            
            # Install the filtered crontab
            if self._set_crontab(new_cron, user):
                print("Laravel scheduler uninstalled successfully.")
                return True
            else:
                print("Failed to uninstall Laravel scheduler from cron.")
                return False
        
        except Exception as e:
            print(f"Error uninstalling scheduler: {e}")
            return False
    
    def is_installed(self, user: Optional[str] = None) -> bool:
        """Check if the scheduler is installed in cron."""
        try:
            current_cron = self._get_current_crontab(user)
            return self.cron_identifier in current_cron
        except Exception:
            return False
    
    def status(self, user: Optional[str] = None) -> Dict[str, Any]:
        """Get the status of the cron integration."""
        return {
            'installed': self.is_installed(user),
            'user': user or 'current',
            'cron_entry': self._generate_cron_entry(),
            'python_executable': self.python_executable,
            'artisan_path': self.artisan_path,
            'working_directory': os.getcwd()
        }
    
    def _get_current_crontab(self, user: Optional[str] = None) -> str:
        """Get the current crontab for the user."""
        try:
            cmd = ['crontab', '-l']
            if user:
                cmd.extend(['-u', user])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            elif "no crontab" in result.stderr.lower():
                return ""
            else:
                raise Exception(f"Failed to read crontab: {result.stderr}")
        
        except FileNotFoundError:
            raise Exception("crontab command not found. Is cron installed?")
    
    def _set_crontab(self, cron_content: str, user: Optional[str] = None) -> bool:
        """Set the crontab for the user."""
        try:
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cron') as f:
                f.write(cron_content)
                temp_file = f.name
            
            try:
                # Install the crontab
                cmd = ['crontab']
                if user:
                    cmd.extend(['-u', user])
                cmd.append(temp_file)
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    return True
                else:
                    print(f"Failed to install crontab: {result.stderr}")
                    return False
            
            finally:
                # Clean up temporary file
                os.unlink(temp_file)
        
        except Exception as e:
            print(f"Error setting crontab: {e}")
            return False
    
    def _generate_cron_entry(self) -> str:
        """Generate the cron entry for the Laravel scheduler."""
        working_dir = os.getcwd()
        
        # Use absolute paths for reliability
        python_path = subprocess.run(['which', self.python_executable], 
                                   capture_output=True, text=True).stdout.strip()
        if not python_path:
            python_path = self.python_executable
        
        artisan_full_path = os.path.join(working_dir, self.artisan_path)
        
        # Generate the cron entry
        entry = f"{self.cron_identifier}\n"
        entry += f"* * * * * cd {working_dir} && {python_path} {artisan_full_path} schedule:run >> /dev/null 2>&1"
        
        return entry


class ScheduleMonitor:
    """Monitor scheduled events and provide health checks."""
    
    def __init__(self, scheduler: SchedulerManager):
        self.scheduler = scheduler
        self.log_path = Path("storage/logs/schedule.log")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the scheduler."""
        health = {
            'status': 'healthy',
            'issues': [],
            'recommendations': [],
            'stats': self.scheduler.get_stats(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Check if cron is installed
        cron_integration = CronIntegration(self.scheduler)
        if not cron_integration.is_installed():
            health['issues'].append("Scheduler is not installed in system cron")
            health['recommendations'].append("Run 'python artisan.py schedule:install' to install")
            health['status'] = 'warning'
        
        # Check for events without recent runs
        now = datetime.now()
        stale_threshold = 3600  # 1 hour
        
        for event in self.scheduler.events.values():
            if event.last_run:
                time_since_run = (now - event.last_run).total_seconds()
                if time_since_run > stale_threshold:
                    health['issues'].append(f"Event {event.id} hasn't run in {time_since_run/3600:.1f} hours")
            else:
                health['issues'].append(f"Event {event.id} has never run")
        
        # Check for high failure rates
        for event in self.scheduler.events.values():
            total_runs = event.success_count + event.failure_count
            if total_runs > 10:  # Only check events that have run enough times
                failure_rate = event.failure_count / total_runs
                if failure_rate > 0.5:  # More than 50% failure rate
                    health['issues'].append(f"Event {event.id} has high failure rate: {failure_rate:.1%}")
                    health['status'] = 'unhealthy'
        
        # Check for overlapping events
        locked_events = [
            event for event in self.scheduler.events.values()
            if event.without_overlapping and self.scheduler._is_event_locked(event)
        ]
        
        if locked_events:
            health['issues'].append(f"{len(locked_events)} events are currently locked (may be running)")
        
        # Provide recommendations
        if not health['issues']:
            health['recommendations'].append("Scheduler is running optimally")
        else:
            if health['status'] == 'warning':
                health['recommendations'].append("Address the issues to improve reliability")
            elif health['status'] == 'unhealthy':
                health['recommendations'].append("Immediate attention required - scheduler may not be working properly")
        
        return health
    
    def get_schedule_report(self) -> Dict[str, Any]:
        """Generate a comprehensive schedule report."""
        events = []
        
        for event in self.scheduler.events.values():
            try:
                from croniter import croniter
                cron = croniter(event.cron_expression, datetime.now())
                next_run = cron.get_next(datetime)
                
                event_info = {
                    'id': event.id,
                    'description': event.description,
                    'command': str(event.command)[:100] + ('...' if len(str(event.command)) > 100 else ''),
                    'cron_expression': event.cron_expression,
                    'next_run': next_run.isoformat() if isinstance(next_run, datetime) else str(next_run),
                    'last_run': event.last_run.isoformat() if event.last_run else None,
                    'success_count': event.success_count,
                    'failure_count': event.failure_count,
                    'success_rate': (
                        event.success_count / (event.success_count + event.failure_count)
                        if (event.success_count + event.failure_count) > 0 else 0
                    ),
                    'without_overlapping': event.without_overlapping,
                    'on_one_server': event.on_one_server,
                    'environments': event.environments,
                    'created_at': event.created_at.isoformat()
                }
                
                events.append(event_info)
            
            except Exception as e:
                events.append({
                    'id': event.id,
                    'error': f"Failed to analyze event: {e}"
                })
        
        # Sort by next run time
        events.sort(key=lambda x: x.get('next_run', ''))
        
        stats = self.scheduler.get_stats()
        
        return {
            'summary': {
                'total_events': len(self.scheduler.events),
                'total_runs': stats['total_runs'],
                'successful_runs': stats['successful_runs'],
                'failed_runs': stats['failed_runs'],
                'success_rate': (
                    stats['successful_runs'] / stats['total_runs']
                    if stats['total_runs'] > 0 else 0
                ),
                'last_run': stats['last_run']
            },
            'events': events,
            'health': self.health_check(),
            'generated_at': datetime.now().isoformat()
        }
    
    def log_event_run(self, event_id: str, success: bool, duration: float, output: str = "") -> None:
        """Log an event run to the schedule log."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_id': event_id,
            'success': success,
            'duration': duration,
            'output': output[:500] if output else ""  # Limit output length
        }
        
        try:
            with open(self.log_path, 'a') as f:
                f.write(f"{json.dumps(log_entry)}\n")
        except Exception as e:
            print(f"Failed to write to schedule log: {e}")
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent schedule logs."""
        logs = []
        
        try:
            if self.log_path.exists():
                with open(self.log_path, 'r') as f:
                    lines = f.readlines()
                
                # Get the last N lines
                recent_lines = lines[-limit:] if len(lines) > limit else lines
                
                for line in recent_lines:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"Failed to read schedule logs: {e}")
        
        return logs
    
    def cleanup_logs(self, days_to_keep: int = 30) -> None:
        """Clean up old schedule logs."""
        if not self.log_path.exists():
            return
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            filtered_lines = []
            for line in lines:
                try:
                    log_entry = json.loads(line.strip())
                    log_date = datetime.fromisoformat(log_entry['timestamp'])
                    
                    if log_date >= cutoff_date:
                        filtered_lines.append(line)
                
                except (json.JSONDecodeError, KeyError, ValueError):
                    # Keep lines that can't be parsed
                    filtered_lines.append(line)
            
            with open(self.log_path, 'w') as f:
                f.writelines(filtered_lines)
            
            print(f"Cleaned up schedule logs older than {days_to_keep} days")
        
        except Exception as e:
            print(f"Failed to cleanup schedule logs: {e}")


import json
from datetime import timedelta