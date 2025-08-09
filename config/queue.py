from __future__ import annotations

import os
from typing import Dict, Any, Optional


# Queue Configuration
# Similar to Laravel's queue.php config

QUEUE_CONFIG: Dict[str, Any] = {
    # Default queue connection
    "default": os.getenv("QUEUE_CONNECTION", "database"),
    
    # Queue connections
    "connections": {
        "database": {
            "driver": "database",
            "table": "jobs",
            "queue": "default",
            "retry_after": 3600,  # 1 hour
            "after_commit": False,
        },
        
        # Future: Redis connection (when implemented)
        "redis": {
            "driver": "redis",
            "connection": "default",
            "queue": "default",
            "retry_after": 3600,
            "block_for": None,
            "after_commit": False,
        },
        
        # Synchronous connection (immediate execution)
        "sync": {
            "driver": "sync",
        },
    },
    
    # Worker configuration
    "worker": {
        "default_memory_limit": 128,  # MB
        "default_timeout": 60,  # seconds
        "default_sleep": 3,  # seconds when no jobs
        "max_jobs": 0,  # 0 = unlimited
        "max_time": 0,  # 0 = unlimited
    },
    
    # Failed job configuration
    "failed": {
        "driver": "database",
        "table": "failed_jobs",
        "prune_hours": 24 * 7,  # 1 week
    },
    
    # Batch job configuration
    "batching": {
        "driver": "database", 
        "table": "job_batches",
    },
    
    # Queue priorities (higher number = higher priority)
    "priorities": {
        "critical": 100,
        "high": 50,
        "normal": 0,
        "low": -50,
    },
    
    # Default job options
    "defaults": {
        "max_attempts": 3,
        "retry_delay": 60,  # seconds
        "timeout": 60,  # seconds
        "delay": 0,  # seconds
    }
}


def get_queue_config(key: Optional[str] = None) -> Any:
    """Get queue configuration value."""
    if key is None:
        return QUEUE_CONFIG
    
    keys = key.split('.')
    value: Any = QUEUE_CONFIG
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    
    return value


def get_connection_config(connection: Optional[str] = None) -> Dict[str, Any]:
    """Get configuration for a specific queue connection."""
    connection = connection or get_queue_config("default")
    return get_queue_config(f"connections.{connection}") or {}


def get_priority_value(priority_name: str) -> int:
    """Get numeric priority value from priority name."""
    priorities = get_queue_config("priorities") or {}
    return int(priorities.get(priority_name, 0))