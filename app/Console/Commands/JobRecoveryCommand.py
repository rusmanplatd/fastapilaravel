"""
Job Recovery and Persistence Management Command
"""
from __future__ import annotations

import json
from typing import Dict, Any, Optional

from app.Console.Command import Command
from app.Jobs.JobPersistence import get_persistence_manager, PersistenceConfig, RecoveryStrategy


class JobRecoveryCommand(Command):
    """
    Manage job recovery and persistence operations.
    
    Usage:
        python manage.py job:recovery [options]
    """
    
    signature = "job:recovery {--list} {--stats} {--recover=} {--recover-all} {--cleanup=} {--config} {--limit=10} {--queue=}"
    description = "Manage job recovery and persistence operations"
    
    def __init__(self):
        super().__init__()
        self.persistence_manager = get_persistence_manager()
    
    def handle(self) -> None:
        """Handle the command execution."""
        
        if self.option('stats'):
            self.show_persistence_stats()
            return
        
        if self.option('config'):
            self.show_persistence_config()
            return
        
        if self.option('list'):
            self.list_failed_jobs()
            return
        
        recover_job_id = self.option('recover')
        if recover_job_id:
            self.recover_single_job(recover_job_id)
            return
        
        if self.option('recover-all'):
            self.recover_all_jobs()
            return
        
        cleanup_days = self.option('cleanup')
        if cleanup_days:
            self.cleanup_old_records(int(cleanup_days))
            return
        
        # Default: show help
        self.show_recovery_help()
    
    def show_persistence_stats(self) -> None:
        """Show persistence system statistics."""
        self.info("Job Persistence Statistics:")
        self.line("")
        
        try:
            stats = self.persistence_manager.get_persistence_stats()
            
            # Job statistics
            job_stats = stats.get("jobs", {})
            self.info(f"Jobs: {job_stats.get('total', 0)} total")
            
            job_status_counts = job_stats.get("by_status", {})
            for status, count in job_status_counts.items():
                color = self._get_status_color(status)
                self.line(f"  • <fg={color}>{status.title()}</>: {count}")
            
            # Chain statistics
            chain_stats = stats.get("chains", {})
            if chain_stats.get("total", 0) > 0:
                self.line("")
                self.info(f"Chains: {chain_stats.get('total', 0)} total")
                
                chain_status_counts = chain_stats.get("by_status", {})
                for status, count in chain_status_counts.items():
                    color = self._get_status_color(status)
                    self.line(f"  • <fg={color}>{status.title()}</>: {count}")
            
            # System info
            system_info = stats.get("system", {})
            self.line("")
            self.info("System Configuration:")
            self.line(f"  • Auto Recovery: {'Enabled' if system_info.get('auto_recovery_enabled') else 'Disabled'}")
            self.line(f"  • Recovery Strategy: {system_info.get('recovery_strategy', 'Unknown')}")
            self.line(f"  • Retention Days: {system_info.get('retention_days', 'Unknown')}")
            self.line(f"  • Max Recovery Attempts: {system_info.get('max_recovery_attempts', 'Unknown')}")
            self.line(f"  • Recovery In Progress: {system_info.get('recovery_in_progress', 0)}")
        
        except Exception as e:
            self.error(f"Failed to get persistence statistics: {str(e)}")
    
    def show_persistence_config(self) -> None:
        """Show current persistence configuration."""
        self.info("Job Persistence Configuration:")
        self.line("")
        
        config = self.persistence_manager.config
        
        config_data = [
            ["Method", config.method.value],
            ["Recovery Strategy", config.recovery_strategy.value],
            ["Retention Days", str(config.retention_days)],
            ["Compression", "Enabled" if config.compression_enabled else "Disabled"],
            ["Encryption", "Enabled" if config.encryption_enabled else "Disabled"],
            ["Backup", "Enabled" if config.backup_enabled else "Disabled"],
            ["Auto Recovery", "Enabled" if config.auto_recovery_enabled else "Disabled"],
            ["Recovery Delay", f"{config.recovery_delay_seconds}s"],
            ["Max Recovery Attempts", str(config.max_recovery_attempts)]
        ]
        
        self.table(["Setting", "Value"], config_data)
    
    def list_failed_jobs(self) -> None:
        """List failed jobs available for recovery."""
        self.info("Failed Jobs Available for Recovery:")
        self.line("")
        
        try:
            limit = int(self.option('limit', 10))
            queue_name = self.option('queue')
            
            failed_jobs = self.persistence_manager.get_failed_jobs(
                limit=limit,
                queue_name=queue_name
            )
            
            if not failed_jobs:
                self.comment("No failed jobs found")
                return
            
            headers = ["Job ID", "Type", "Queue", "Failed At", "Attempts", "Error Type"]
            rows = []
            
            for job in failed_jobs:
                job_id_short = job.job_id[:12] + "..." if len(job.job_id) > 15 else job.job_id
                failed_time = job.failed_at.strftime("%Y-%m-%d %H:%M") if job.failed_at else "Unknown"
                
                rows.append([
                    job_id_short,
                    job.job_type,
                    job.queue_name,
                    failed_time,
                    f"{job.recovery_attempts}/{job.max_attempts}",
                    job.error_type or "Unknown"
                ])
            
            self.table(headers, rows)
            
            self.line("")
            self.comment(f"Showing {len(failed_jobs)} failed jobs")
            if queue_name:
                self.comment(f"Filtered by queue: {queue_name}")
            
            # Show recoverable jobs count
            recoverable_jobs = self.persistence_manager.get_recoverable_jobs()
            recoverable_count = len(recoverable_jobs)
            if recoverable_count > 0:
                self.info(f"{recoverable_count} jobs are eligible for immediate recovery")
            else:
                self.comment("No jobs are currently eligible for recovery")
        
        except Exception as e:
            self.error(f"Failed to list failed jobs: {str(e)}")
    
    def recover_single_job(self, job_id: str) -> None:
        """Recover a specific job."""
        self.info(f"Attempting to recover job: {job_id}")
        
        try:
            success = self.persistence_manager.recover_job(job_id)
            
            if success:
                self.info(f"<fg=green>✓</> Job {job_id} has been queued for recovery")
            else:
                self.error(f"✗ Failed to recover job {job_id}")
                self.comment("Check logs for detailed error information")
        
        except Exception as e:
            self.error(f"Error recovering job {job_id}: {str(e)}")
    
    def recover_all_jobs(self) -> None:
        """Recover all eligible failed jobs."""
        limit = int(self.option('limit', 10))
        queue_name = self.option('queue')
        
        self.info(f"Attempting to recover up to {limit} failed jobs...")
        if queue_name:
            self.comment(f"Limited to queue: {queue_name}")
        
        try:
            # First, show what will be recovered
            recoverable_jobs = self.persistence_manager.get_recoverable_jobs()
            
            if queue_name:
                recoverable_jobs = [
                    job for job in recoverable_jobs 
                    if job.queue_name == queue_name
                ]
            
            if not recoverable_jobs:
                self.comment("No jobs are eligible for recovery")
                return
            
            if limit:
                recoverable_jobs = recoverable_jobs[:limit]
            
            self.comment(f"Found {len(recoverable_jobs)} jobs eligible for recovery")
            
            # Ask for confirmation
            if not self.confirm(f"Proceed to recover {len(recoverable_jobs)} jobs?"):
                self.comment("Recovery cancelled")
                return
            
            # Perform recovery
            results = self.persistence_manager.recover_failed_jobs(
                limit=limit,
                queue_name=queue_name
            )
            
            # Show results
            self.line("")
            self.info("Recovery Results:")
            self.line(f"  • <fg=green>Successful</>: {results['successful']}")
            self.line(f"  • <fg=red>Failed</>: {results['failed']}")
            self.line(f"  • <fg=blue>Total Attempted</>: {results['attempted']}")
            
            if results.get('errors'):
                self.line("")
                self.warn("Errors encountered:")
                for error in results['errors'][:5]:  # Show first 5 errors
                    self.line(f"  • {error}")
                
                if len(results['errors']) > 5:
                    self.comment(f"... and {len(results['errors']) - 5} more errors")
        
        except Exception as e:
            self.error(f"Error during batch recovery: {str(e)}")
    
    def cleanup_old_records(self, days: int) -> None:
        """Clean up old persistence records."""
        self.info(f"Cleaning up persistence records older than {days} days...")
        
        if not self.confirm(f"This will permanently delete completed job records older than {days} days. Continue?"):
            self.comment("Cleanup cancelled")
            return
        
        try:
            deleted_count = self.persistence_manager.cleanup_old_records(days=days)
            
            if deleted_count > 0:
                self.info(f"<fg=green>✓</> Successfully cleaned up {deleted_count} old records")
            else:
                self.comment("No old records found to clean up")
        
        except Exception as e:
            self.error(f"Error during cleanup: {str(e)}")
    
    def show_recovery_help(self) -> None:
        """Show help information for recovery command."""
        self.info("Job Recovery Management")
        self.line("")
        
        self.comment("Available commands:")
        self.line("  <fg=yellow>--stats</>           Show persistence system statistics")
        self.line("  <fg=yellow>--config</>          Show current persistence configuration")
        self.line("  <fg=yellow>--list</>            List failed jobs available for recovery")
        self.line("  <fg=yellow>--recover=ID</>      Recover a specific job by ID")
        self.line("  <fg=yellow>--recover-all</>     Recover all eligible failed jobs")
        self.line("  <fg=yellow>--cleanup=DAYS</>    Clean up old records (default: 30 days)")
        self.line("")
        
        self.comment("Options:")
        self.line("  <fg=yellow>--limit=N</>         Limit number of jobs to process (default: 10)")
        self.line("  <fg=yellow>--queue=NAME</>      Filter by specific queue name")
        self.line("")
        
        self.comment("Examples:")
        self.line("  python manage.py job:recovery --stats")
        self.line("  python manage.py job:recovery --list --limit=20")
        self.line("  python manage.py job:recovery --recover-all --queue=emails")
        self.line("  python manage.py job:recovery --cleanup=7")
    
    def _get_status_color(self, status: str) -> str:
        """Get color for status display."""
        color_map = {
            "completed": "green",
            "failed": "red",
            "persisted": "blue",
            "recovering": "yellow",
            "recovered": "green"
        }
        return color_map.get(status.lower(), "gray")


# Register the command
def register_command():
    return JobRecoveryCommand()