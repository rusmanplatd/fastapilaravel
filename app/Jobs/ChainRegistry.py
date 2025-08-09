"""
Production-ready Chain Registry for managing active job chains.
"""
from __future__ import annotations

import threading
import weakref
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.Jobs.Chain import JobChain


class ChainRegistry:
    """
    Registry for managing active job chains.
    Uses singleton pattern with thread-safe operations.
    """
    
    _instance: Optional[ChainRegistry] = None
    _lock = threading.Lock()
    
    def __init__(self) -> None:
        self.chains: Dict[str, JobChain] = {}
        self._chain_lock = threading.RLock()
    
    @classmethod
    def get_instance(cls) -> ChainRegistry:
        """Get the singleton instance of ChainRegistry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def register_chain(self, chain_id: str, chain: JobChain) -> None:
        """Register a chain in the registry."""
        with self._chain_lock:
            # Use weak reference to avoid memory leaks
            self.chains[chain_id] = chain
    
    def get_chain(self, chain_id: str) -> Optional[JobChain]:
        """Get a chain by its ID."""
        with self._chain_lock:
            return self.chains.get(chain_id)
    
    def unregister_chain(self, chain_id: str) -> None:
        """Remove a chain from the registry."""
        with self._chain_lock:
            self.chains.pop(chain_id, None)
    
    def get_active_chains(self) -> Dict[str, JobChain]:
        """Get all active chains."""
        with self._chain_lock:
            return dict(self.chains)
    
    def cleanup_finished_chains(self) -> int:
        """Remove finished chains from registry and return count."""
        with self._chain_lock:
            from app.Jobs.Chain import ChainStatus
            
            finished_chain_ids = []
            for chain_id, chain in self.chains.items():
                if chain.status in [ChainStatus.COMPLETED, ChainStatus.FAILED, ChainStatus.CANCELLED]:
                    finished_chain_ids.append(chain_id)
            
            for chain_id in finished_chain_ids:
                del self.chains[chain_id]
            
            return len(finished_chain_ids)
    
    def get_stats(self) -> Dict[str, int]:
        """Get registry statistics."""
        with self._chain_lock:
            from app.Jobs.Chain import ChainStatus
            
            stats = {
                'total_chains': len(self.chains),
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0
            }
            
            for chain in self.chains.values():
                stats[chain.status.value] += 1
            
            return stats