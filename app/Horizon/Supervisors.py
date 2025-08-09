from __future__ import annotations

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class SupervisorStatus(Enum):
    """Supervisor status enumeration."""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SupervisorConfig:
    """Supervisor configuration."""
    name: str
    connection: str = "default"
    queues: Optional[List[str]] = None
    processes: int = 1
    timeout: int = 60
    memory: int = 128
    sleep: int = 3
    max_jobs: int = 0
    
    def __post_init__(self) -> None:
        if self.queues is None:
            self.queues = ["default"]


class Supervisor:
    """Queue supervisor for managing worker processes."""
    
    def __init__(self, config: SupervisorConfig):
        self.config = config
        self.status = SupervisorStatus.STOPPED
        self.workers: List[Dict[str, Any]] = []
        self.stats = {
            'jobs_processed': 0,
            'jobs_failed': 0,
            'started_at': None,
            'last_activity': None
        }
    
    async def start(self) -> None:
        """Start the supervisor."""
        if self.status == SupervisorStatus.RUNNING:
            return
        
        self.status = SupervisorStatus.RUNNING
        # Start worker processes here
        for i in range(self.config.processes):
            worker = {
                'id': f"{self.config.name}-{i}",
                'supervisor': self.config.name,
                'status': 'idle',
                'jobs_processed': 0,
                'started_at': None,
                'current_job': None
            }
            self.workers.append(worker)
    
    async def stop(self) -> None:
        """Stop the supervisor."""
        self.status = SupervisorStatus.STOPPED
        self.workers.clear()
    
    async def pause(self) -> None:
        """Pause the supervisor."""
        if self.status == SupervisorStatus.RUNNING:
            self.status = SupervisorStatus.PAUSED
    
    async def continue_processing(self) -> None:
        """Continue processing after pause."""
        if self.status == SupervisorStatus.PAUSED:
            self.status = SupervisorStatus.RUNNING
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics."""
        return {
            'name': self.config.name,
            'status': self.status.value,
            'processes': len(self.workers),
            'queues': self.config.queues,
            'stats': self.stats,
            'workers': self.workers
        }


class SupervisorManager:
    """Manages multiple queue supervisors."""
    
    def __init__(self) -> None:
        self.supervisors: Dict[str, Supervisor] = {}
        self.default_config = SupervisorConfig(name="default")
    
    def add_supervisor(self, config: SupervisorConfig) -> Supervisor:
        """Add a new supervisor."""
        supervisor = Supervisor(config)
        self.supervisors[config.name] = supervisor
        return supervisor
    
    def get_supervisor(self, name: str) -> Optional[Supervisor]:
        """Get supervisor by name."""
        return self.supervisors.get(name)
    
    async def start_all(self) -> None:
        """Start all supervisors."""
        if not self.supervisors:
            # Create default supervisor
            self.add_supervisor(self.default_config)
        
        for supervisor in self.supervisors.values():
            await supervisor.start()
    
    async def stop_all(self) -> None:
        """Stop all supervisors."""
        for supervisor in self.supervisors.values():
            await supervisor.stop()
    
    async def pause_all(self) -> None:
        """Pause all supervisors."""
        for supervisor in self.supervisors.values():
            await supervisor.pause()
    
    async def continue_all(self) -> None:
        """Continue all supervisors."""
        for supervisor in self.supervisors.values():
            await supervisor.continue_processing()
    
    async def pause(self, name: Optional[str] = None) -> None:
        """Pause specific supervisor or all supervisors."""
        if name:
            supervisor = self.get_supervisor(name)
            if supervisor:
                await supervisor.pause()
        else:
            await self.pause_all()
    
    async def continue_processing(self, name: Optional[str] = None) -> None:
        """Continue specific supervisor or all supervisors."""
        if name:
            supervisor = self.get_supervisor(name)
            if supervisor:
                await supervisor.continue_processing()
        else:
            await self.continue_all()
    
    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all supervisors."""
        return [supervisor.get_stats() for supervisor in self.supervisors.values()]
    
    def get_overview_stats(self) -> Dict[str, Any]:
        """Get overview statistics."""
        total_supervisors = len(self.supervisors)
        active_workers = sum(len(s.workers) for s in self.supervisors.values())
        total_jobs = sum(s.stats['jobs_processed'] or 0 for s in self.supervisors.values())
        
        # Determine overall status
        statuses = [s.status for s in self.supervisors.values()]
        if all(status == SupervisorStatus.RUNNING for status in statuses):
            overall_status = "running"
        elif all(status == SupervisorStatus.STOPPED for status in statuses):
            overall_status = "stopped"
        elif any(status == SupervisorStatus.ERROR for status in statuses):
            overall_status = "error"
        else:
            overall_status = "mixed"
        
        return {
            'status': overall_status,
            'total_supervisors': total_supervisors,
            'active_workers': active_workers,
            'total_jobs_processed': total_jobs
        }