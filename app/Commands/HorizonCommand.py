from __future__ import annotations

import asyncio
import signal
import sys
from typing import Optional, Any
from app.Console.Command import Command
from app.Horizon import Horizon


class HorizonCommand(Command):
    """
    Laravel Horizon-style queue monitoring command.
    
    Starts the Horizon queue dashboard and monitoring system.
    """
    
    signature = 'horizon'
    description = 'Start Laravel Horizon queue monitoring and dashboard'
    
    def __init__(self) -> None:
        super().__init__()
        self.should_stop = False
    
    async def handle(self) -> None:
        """Start Horizon monitoring system."""
        self.info("Starting Laravel Horizon...")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Start Horizon
            await Horizon.start()
            
            self.info("✅ Horizon started successfully")
            self.info("📊 Dashboard available at: http://localhost:8000/horizon")
            self.line("")
            self.line("Press Ctrl+C to stop Horizon")
            
            # Keep running until signal received
            while not self.should_stop:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.error(f"Failed to start Horizon: {e}")
            sys.exit(1)
        finally:
            await self._shutdown()
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        self.line("")
        self.info("Received shutdown signal, stopping Horizon...")
        self.should_stop = True
    
    async def _shutdown(self) -> None:
        """Gracefully shutdown Horizon."""
        try:
            await Horizon.stop()
            self.info("✅ Horizon stopped successfully")
        except Exception as e:
            self.error(f"Error stopping Horizon: {e}")


class HorizonWorkCommand(Command):
    """Start Horizon worker processes."""
    
    signature = 'horizon:work {--queue=default} {--timeout=60} {--memory=128} {--sleep=3}'
    description = 'Start Horizon queue worker processes'
    
    async def handle(self) -> None:
        """Start queue workers."""
        queue = self.option('queue', 'default')
        timeout = int(self.option('timeout', '60'))
        memory = int(self.option('memory', '128'))
        sleep = int(self.option('sleep', '3'))
        
        self.info(f"Starting Horizon worker for queue: {queue}")
        self.info(f"Timeout: {timeout}s, Memory: {memory}MB, Sleep: {sleep}s")
        
        # This would start actual worker processes
        # For now, just show the configuration
        self.line("")
        self.info("Worker configuration:")
        self.line(f"  Queue: {queue}")
        self.line(f"  Timeout: {timeout} seconds")
        self.line(f"  Memory limit: {memory} MB")
        self.line(f"  Sleep: {sleep} seconds")


class HorizonPauseCommand(Command):
    """Pause Horizon queue processing."""
    
    signature = 'horizon:pause {supervisor?}'
    description = 'Pause Horizon queue processing'
    
    async def handle(self) -> None:
        """Pause queue processing."""
        supervisor = self.argument('supervisor')
        
        if supervisor:
            self.info(f"Pausing supervisor: {supervisor}")
            await Horizon.pause(supervisor)
            self.info(f"✅ Supervisor {supervisor} paused")
        else:
            self.info("Pausing all supervisors...")
            await Horizon.pause()
            self.info("✅ All supervisors paused")


class HorizonContinueCommand(Command):
    """Continue Horizon queue processing after pause."""
    
    signature = 'horizon:continue {supervisor?}'
    description = 'Continue Horizon queue processing'
    
    async def handle(self) -> None:
        """Continue queue processing."""
        supervisor = self.argument('supervisor')
        
        if supervisor:
            self.info(f"Continuing supervisor: {supervisor}")
            await Horizon.continue_processing(supervisor)
            self.info(f"✅ Supervisor {supervisor} continued")
        else:
            self.info("Continuing all supervisors...")
            await Horizon.continue_processing()
            self.info("✅ All supervisors continued")


class HorizonStatusCommand(Command):
    """Show Horizon status and statistics."""
    
    signature = 'horizon:status'
    description = 'Show Horizon queue status and statistics'
    
    async def handle(self) -> None:
        """Show Horizon status."""
        self.info("Horizon Status")
        self.line("=" * 50)
        
        try:
            stats = await Horizon.get_stats()
            overview = stats.get('overview', {})
            
            # Overview
            self.line(f"Status: {overview.get('status', 'Unknown')}")
            self.line(f"Supervisors: {overview.get('total_supervisors', 0)}")
            self.line(f"Active Workers: {overview.get('active_workers', 0)}")
            self.line(f"Jobs Processed: {overview.get('total_jobs_processed', 0)}")
            
            # Supervisors
            supervisors = stats.get('supervisors', [])
            if supervisors:
                self.line("")
                self.info("Supervisors:")
                for supervisor in supervisors:
                    status = supervisor.get('status', 'unknown')
                    processes = supervisor.get('processes', 0)
                    supervisor_queues = ', '.join(supervisor.get('queues', []))
                    self.line(f"  {supervisor['name']}: {status} ({processes} processes) - {supervisor_queues}")
            
            # Queues
            queues = stats.get('queues', {})
            if queues:
                self.line("")
                self.info("Queues:")
                for queue_name, queue_data in queues.items():
                    pending = queue_data.get('pending_jobs', 0)
                    processing = queue_data.get('processing_jobs', 0)
                    self.line(f"  {queue_name}: {pending} pending, {processing} processing")
            
        except Exception as e:
            self.error(f"Failed to get Horizon status: {e}")
            sys.exit(1)


class HorizonListCommand(Command):
    """List all Horizon supervisors and workers."""
    
    signature = 'horizon:list'
    description = 'List all Horizon supervisors and workers'
    
    async def handle(self) -> None:
        """List supervisors and workers."""
        try:
            stats = await Horizon.get_stats()
            
            # Supervisors
            supervisors = stats.get('supervisors', [])
            self.info("Supervisors:")
            self.line("-" * 60)
            
            if supervisors:
                for supervisor in supervisors:
                    name = supervisor.get('name', 'Unknown')
                    status = supervisor.get('status', 'unknown')
                    processes = supervisor.get('processes', 0)
                    queues = ', '.join(supervisor.get('queues', []))
                    
                    self.line(f"{name:<15} {status:<10} {processes} processes  {queues}")
            else:
                self.line("No supervisors found")
            
            # Workers
            workers = stats.get('workers', [])
            self.line("")
            self.info("Workers:")
            self.line("-" * 80)
            
            if workers:
                for worker in workers:
                    worker_id = worker.get('id', 'Unknown')[:20]
                    supervisor = worker.get('supervisor', 'Unknown')
                    status = worker.get('status', 'unknown')
                    jobs = worker.get('jobs_processed', 0)
                    
                    self.line(f"{worker_id:<20} {supervisor:<12} {status:<10} {jobs} jobs")
            else:
                self.line("No workers found")
                
        except Exception as e:
            self.error(f"Failed to list Horizon components: {e}")
            sys.exit(1)