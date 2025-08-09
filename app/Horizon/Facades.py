from __future__ import annotations

from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .HorizonManager import HorizonManager
    from .Dashboard import HorizonDashboard

# Global manager instance
_manager: Optional[HorizonManager] = None
_dashboard: Optional[HorizonDashboard] = None


class Horizon:
    """
    Horizon facade similar to Laravel's Horizon facade.
    
    Provides static-like access to the HorizonManager instance
    for queue monitoring and management.
    """
    
    @classmethod
    def _get_manager(cls) -> HorizonManager:
        """Get the global HorizonManager instance."""
        global _manager
        if _manager is None:
            from .HorizonManager import HorizonManager
            _manager = HorizonManager()
        return _manager
    
    @classmethod
    def _get_dashboard(cls) -> HorizonDashboard:
        """Get the global HorizonDashboard instance.""" 
        global _dashboard
        if _dashboard is None:
            from .Dashboard import HorizonDashboard
            _dashboard = HorizonDashboard(cls._get_manager())
        return _dashboard
    
    @classmethod
    async def start(cls) -> None:
        """Start Horizon queue monitoring and workers."""
        await cls._get_manager().start()
    
    @classmethod
    async def stop(cls) -> None:
        """Stop Horizon and all worker processes."""
        await cls._get_manager().stop()
    
    @classmethod
    async def pause(cls, supervisor: Optional[str] = None) -> None:
        """Pause all workers or specific supervisor."""
        await cls._get_manager().pause(supervisor)
    
    @classmethod
    async def continue_processing(cls, supervisor: Optional[str] = None) -> None:
        """Continue processing after pause."""
        await cls._get_manager().continue_processing(supervisor)
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        return await cls._get_manager().get_dashboard_stats()
    
    @classmethod
    async def get_supervisors(cls) -> List[Dict[str, Any]]:
        """Get supervisor information."""
        stats = await cls.get_stats()
        result = stats.get('supervisors', [])
        return result if isinstance(result, list) else []
    
    @classmethod
    async def get_queues(cls) -> Dict[str, Any]:
        """Get queue information."""
        stats = await cls.get_stats()
        result = stats.get('queues', {})
        return result if isinstance(result, dict) else {}
    
    @classmethod
    async def get_workers(cls) -> List[Dict[str, Any]]:
        """Get worker information."""
        stats = await cls.get_stats()
        result = stats.get('workers', [])
        return result if isinstance(result, list) else []
    
    @classmethod
    async def get_jobs(cls) -> Dict[str, Any]:
        """Get job statistics."""
        stats = await cls.get_stats()
        result = stats.get('jobs', {})
        return result if isinstance(result, dict) else {}
    
    @classmethod
    async def get_metrics(cls) -> Dict[str, Any]:
        """Get system metrics."""
        stats = await cls.get_stats()
        result = stats.get('metrics', {})
        return result if isinstance(result, dict) else {}
    
    @classmethod
    def dashboard(cls) -> HorizonDashboard:
        """Get the dashboard instance."""
        return cls._get_dashboard()
    
    @classmethod
    def set_redis_url(cls, redis_url: str) -> None:
        """Set Redis URL for Horizon."""
        global _manager
        from .HorizonManager import HorizonManager
        _manager = HorizonManager(redis_url)
    
    @classmethod
    def is_running(cls) -> bool:
        """Check if Horizon is currently running."""
        return cls._get_manager().is_running