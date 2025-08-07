from __future__ import annotations

import json
import time
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime, timezone, timedelta

from app.Jobs.Job import ShouldQueue

if TYPE_CHECKING:
    import redis


class RedisQueueDriver:
    """
    Redis-based queue driver for high-performance job processing.
    Supports delayed jobs, priorities, and reliable processing.
    """
    
    def __init__(
        self,
        connection_params: Optional[Dict[str, Any]] = None,
        key_prefix: str = "queue:"
    ) -> None:
        self.connection_params = connection_params or {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "decode_responses": True
        }
        self.key_prefix = key_prefix
        self._redis: Optional[redis.Redis] = None
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis connection."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(**self.connection_params)
            except ImportError:
                raise ImportError("Redis package not installed. Install with: pip install redis")
        
        return self._redis
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to queue."""
        job_id = self._generate_job_id()
        job_data = self._serialize_job(job, job_id)
        
        # Handle delayed jobs
        if job.options.delay > 0:
            score = time.time() + job.options.delay
            self.redis.zadd(f"{self.key_prefix}delayed", {job_id: score})
        else:
            # Use priority for scoring (higher priority = lower score for correct ordering)
            priority_score = -job.options.priority
            self.redis.zadd(f"{self.key_prefix}{queue}", {job_id: priority_score})
        
        # Store job data
        self.redis.hset(f"{self.key_prefix}jobs", job_id, json.dumps(job_data))
        
        return job_id
    
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Pop job from queue with blocking."""
        # First, move any delayed jobs that are ready
        self._move_delayed_jobs()
        
        # Pop job with priority (lowest score first)
        result = self.redis.bzpopmin(f"{self.key_prefix}{queue}", timeout=timeout)
        
        if not result:
            return None
        
        queue_name, job_id, score = result
        
        # Get job data
        job_data_json = self.redis.hget(f"{self.key_prefix}jobs", job_id)
        if not job_data_json:
            return None
        
        job_data = json.loads(job_data_json)
        
        # Mark job as reserved
        self._reserve_job(job_id, job_data)
        
        return job_data  # type: ignore[no-any-return]
    
    def reserve_job(self, job_id: str, worker_id: str, timeout: int = 3600) -> bool:
        """Reserve a job for processing."""
        return self._reserve_job(job_id, {"worker_id": worker_id}, timeout)
    
    def release_job(self, job_id: str, delay: int = 0) -> bool:
        """Release reserved job back to queue."""
        job_data_json = self.redis.hget(f"{self.key_prefix}jobs", job_id)
        if not job_data_json:
            return False
        
        job_data = json.loads(job_data_json)
        
        # Remove from reserved set
        self.redis.srem(f"{self.key_prefix}reserved", job_id)
        self.redis.hdel(f"{self.key_prefix}reserved_data", job_id)
        
        # Re-queue job
        queue = job_data.get("queue", "default")
        priority_score = -job_data.get("priority", 0)
        
        if delay > 0:
            score = time.time() + delay
            self.redis.zadd(f"{self.key_prefix}delayed", {job_id: score})
        else:
            self.redis.zadd(f"{self.key_prefix}{queue}", {job_id: priority_score})
        
        return True
    
    def complete_job(self, job_id: str) -> bool:
        """Mark job as completed and remove from system."""
        # Remove from reserved
        self.redis.srem(f"{self.key_prefix}reserved", job_id)
        self.redis.hdel(f"{self.key_prefix}reserved_data", job_id)
        
        # Remove job data
        self.redis.hdel(f"{self.key_prefix}jobs", job_id)
        
        return True
    
    def fail_job(self, job_id: str, error: str) -> bool:
        """Move job to failed jobs."""
        job_data_json = self.redis.hget(f"{self.key_prefix}jobs", job_id)
        if not job_data_json:
            return False
        
        job_data = json.loads(job_data_json)
        job_data["failed_at"] = datetime.now(timezone.utc).isoformat()
        job_data["error"] = error
        
        # Move to failed jobs
        self.redis.hset(f"{self.key_prefix}failed", job_id, json.dumps(job_data))
        
        # Remove from other locations
        self.redis.srem(f"{self.key_prefix}reserved", job_id)
        self.redis.hdel(f"{self.key_prefix}reserved_data", job_id)
        self.redis.hdel(f"{self.key_prefix}jobs", job_id)
        
        return True
    
    def get_queue_size(self, queue: str = "default") -> int:
        """Get number of jobs in queue."""
        return self.redis.zcard(f"{self.key_prefix}{queue}")  # type: ignore[no-any-return]
    
    def get_delayed_count(self) -> int:
        """Get number of delayed jobs."""
        return self.redis.zcard(f"{self.key_prefix}delayed")  # type: ignore[no-any-return]
    
    def get_reserved_count(self) -> int:
        """Get number of reserved jobs."""
        return self.redis.scard(f"{self.key_prefix}reserved")  # type: ignore[no-any-return]
    
    def get_failed_count(self) -> int:
        """Get number of failed jobs."""
        return self.redis.hlen(f"{self.key_prefix}failed")  # type: ignore[no-any-return]
    
    def clear_queue(self, queue: str = "default") -> int:
        """Clear all jobs from queue."""
        # Get all job IDs in queue
        job_ids = self.redis.zrange(f"{self.key_prefix}{queue}", 0, -1)
        
        # Remove job data
        if job_ids:
            self.redis.hdel(f"{self.key_prefix}jobs", *job_ids)
        
        # Clear queue
        count = self.redis.zcard(f"{self.key_prefix}{queue}")
        self.redis.delete(f"{self.key_prefix}{queue}")
        
        return count  # type: ignore[no-any-return]
    
    def clear_failed_jobs(self) -> int:
        """Clear all failed jobs."""
        count = self.redis.hlen(f"{self.key_prefix}failed")
        self.redis.delete(f"{self.key_prefix}failed")
        return count  # type: ignore[no-any-return]
    
    def retry_failed_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        failed_data_json = self.redis.hget(f"{self.key_prefix}failed", job_id)
        if not failed_data_json:
            return False
        
        job_data = json.loads(failed_data_json)
        
        # Remove failed info
        if "failed_at" in job_data:
            del job_data["failed_at"]
        if "error" in job_data:
            del job_data["error"]
        
        # Re-queue job
        queue = job_data.get("queue", "default")
        priority_score = -job_data.get("priority", 0)
        
        self.redis.zadd(f"{self.key_prefix}{queue}", {job_id: priority_score})
        self.redis.hset(f"{self.key_prefix}jobs", job_id, json.dumps(job_data))
        
        # Remove from failed
        self.redis.hdel(f"{self.key_prefix}failed", job_id)
        
        return True
    
    def get_failed_jobs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get failed jobs."""
        failed_jobs = []
        
        # Get all failed job IDs
        job_ids = list(self.redis.hkeys(f"{self.key_prefix}failed"))
        
        # Apply pagination
        paginated_ids = job_ids[offset:offset + limit]
        
        for job_id in paginated_ids:
            job_data_json = self.redis.hget(f"{self.key_prefix}failed", job_id)
            if job_data_json:
                job_data = json.loads(job_data_json)
                job_data["id"] = job_id
                failed_jobs.append(job_data)
        
        return failed_jobs
    
    def release_expired_reservations(self, timeout: int = 3600) -> int:
        """Release jobs reserved longer than timeout."""
        cutoff = time.time() - timeout
        released_count = 0
        
        # Get all reserved jobs
        reserved_jobs = self.redis.smembers(f"{self.key_prefix}reserved")
        
        for job_id in reserved_jobs:
            reserved_data_json = self.redis.hget(f"{self.key_prefix}reserved_data", job_id)
            if not reserved_data_json:
                continue
            
            reserved_data = json.loads(reserved_data_json)
            reserved_at = reserved_data.get("reserved_at", 0)
            
            if reserved_at < cutoff:
                # Release expired reservation
                if self.release_job(job_id):
                    released_count += 1
        
        return released_count
    
    def _serialize_job(self, job: ShouldQueue, job_id: str) -> Dict[str, Any]:
        """Serialize job for Redis storage."""
        job_data = job.serialize()
        job_data.update({
            "id": job_id,
            "queue": job.options.queue,
            "priority": job.options.priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0
        })
        return job_data
    
    def _reserve_job(self, job_id: str, extra_data: Optional[Dict[str, Any]] = None, timeout: int = 3600) -> bool:
        """Mark job as reserved."""
        reserved_data = {
            "reserved_at": time.time(),
            "timeout": timeout,
            **(extra_data or {})
        }
        
        self.redis.sadd(f"{self.key_prefix}reserved", job_id)
        self.redis.hset(f"{self.key_prefix}reserved_data", job_id, json.dumps(reserved_data))
        
        return True
    
    def _move_delayed_jobs(self) -> int:
        """Move delayed jobs that are ready to their queues."""
        now = time.time()
        moved_count = 0
        
        # Get jobs ready to be moved
        ready_jobs = self.redis.zrangebyscore(
            f"{self.key_prefix}delayed",
            min=0,
            max=now,
            withscores=True
        )
        
        for job_id, score in ready_jobs:
            # Get job data to determine target queue
            job_data_json = self.redis.hget(f"{self.key_prefix}jobs", job_id)
            if job_data_json:
                job_data = json.loads(job_data_json)
                queue = job_data.get("queue", "default")
                priority_score = -job_data.get("priority", 0)
                
                # Move to target queue
                self.redis.zadd(f"{self.key_prefix}{queue}", {job_id: priority_score})
                
                # Remove from delayed
                self.redis.zrem(f"{self.key_prefix}delayed", job_id)
                
                moved_count += 1
        
        return moved_count
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        import uuid
        return str(uuid.uuid4())
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        # Get all queue names
        queue_keys = self.redis.keys(f"{self.key_prefix}*")
        queues = {}
        
        for key in queue_keys:
            if key.startswith(f"{self.key_prefix}") and not key.endswith(("delayed", "reserved", "failed", "jobs", "reserved_data")):
                queue_name = key.replace(self.key_prefix, "")
                queues[queue_name] = self.redis.zcard(key)
        
        return {
            "queues": queues,
            "delayed": self.get_delayed_count(),
            "reserved": self.get_reserved_count(),
            "failed": self.get_failed_count(),
            "total_jobs": sum(queues.values())
        }