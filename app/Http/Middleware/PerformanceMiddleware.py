from __future__ import annotations

import logging
import time
# import psutil  # Optional dependency - install with: pip install psutil
try:
    import psutil
except ImportError:
    psutil = None
import os
from typing import Optional, Dict, Any, List, Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp
import json


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Advanced performance monitoring middleware with detailed metrics."""
    
    def __init__(
        self, 
        app: ASGIApp, 
        log_slow_requests: bool = True,
        slow_request_threshold: float = 1.0,
        monitor_memory: bool = True,
        monitor_cpu: bool = True,
        track_database_queries: bool = True
    ) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_slow_requests = log_slow_requests
        self.slow_request_threshold = slow_request_threshold
        self.monitor_memory = monitor_memory
        self.monitor_cpu = monitor_cpu
        self.track_database_queries = track_database_queries
        
        # Performance tracking storage
        self._request_metrics: List[Dict[str, Any]] = []
        self._max_stored_metrics = 1000
        
        # CPU and memory tracking
        self._process = psutil.Process()
    
    async def dispatch(self, request: StarletteRequest, call_next: Callable[[StarletteRequest], Awaitable[StarletteResponse]]) -> StarletteResponse:
        """Enhanced middleware dispatch with comprehensive performance monitoring."""
        start_time = time.time()
        start_cpu_time = time.process_time()
        
        # Capture initial system metrics
        initial_memory = self._get_memory_usage() if self.monitor_memory else None
        initial_cpu_percent = self._get_cpu_percent() if self.monitor_cpu else None
        
        # Initialize database query tracking
        if self.track_database_queries:
            request.state.db_query_count = 0
            request.state.db_query_time = 0.0
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            end_time = time.time()
            end_cpu_time = time.process_time()
            
            duration = end_time - start_time
            cpu_time = end_cpu_time - start_cpu_time
            
            # Capture final system metrics
            final_memory = self._get_memory_usage() if self.monitor_memory else None
            final_cpu_percent = self._get_cpu_percent() if self.monitor_cpu else None
            
            # Create performance metrics
            metrics = self._create_metrics(
                request, response, duration, cpu_time,
                initial_memory, final_memory,
                initial_cpu_percent, final_cpu_percent
            )
            
            # Store metrics
            self._store_metrics(metrics)
            
            # Log performance data
            self._log_performance(metrics)
            
            # Add performance headers
            self._add_performance_headers(response, metrics)
            
            return response
            
        except Exception as e:
            # Log error with performance context
            duration = time.time() - start_time
            cpu_time = time.process_time() - start_cpu_time
            
            self._log_error_performance(request, e, duration, cpu_time)
            raise
    
    def _create_metrics(
        self, 
        request: StarletteRequest, 
        response: StarletteResponse,
        duration: float,
        cpu_time: float,
        initial_memory: Optional[Dict[str, float]],
        final_memory: Optional[Dict[str, float]],
        initial_cpu_percent: Optional[float],
        final_cpu_percent: Optional[float]
    ) -> Dict[str, Any]:
        """Create comprehensive performance metrics."""
        metrics = {
            # Request info
            "timestamp": time.time(),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            
            # Timing metrics
            "duration_seconds": round(duration, 4),
            "duration_ms": round(duration * 1000, 2),
            "cpu_time_seconds": round(cpu_time, 4),
            "cpu_time_ms": round(cpu_time * 1000, 2),
            
            # Performance classification
            "is_slow": duration > self.slow_request_threshold,
            "performance_class": self._classify_performance(duration),
            
            # Client info
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "content_length": response.headers.get("content-length", 0),
        }
        
        # Memory metrics
        if self.monitor_memory and initial_memory and final_memory:
            metrics["memory"] = {
                "initial_rss_mb": initial_memory["rss"],
                "final_rss_mb": final_memory["rss"],
                "memory_delta_mb": round(final_memory["rss"] - initial_memory["rss"], 2),
                "initial_vms_mb": initial_memory["vms"],
                "final_vms_mb": final_memory["vms"],
                "memory_percent": final_memory["percent"]
            }
        
        # CPU metrics
        if self.monitor_cpu:
            if initial_cpu_percent is not None and final_cpu_percent is not None:
                metrics["cpu"] = {
                    "initial_percent": initial_cpu_percent,
                    "final_percent": final_cpu_percent,
                    "cpu_delta": round(final_cpu_percent - initial_cpu_percent, 2),
                    "cpu_efficiency": round(cpu_time / duration * 100, 2) if duration > 0 else 0
                }
        
        # Database query metrics
        if self.track_database_queries and hasattr(request.state, 'db_query_count'):
            metrics["database"] = {
                "query_count": getattr(request.state, 'db_query_count', 0),
                "query_time_seconds": round(getattr(request.state, 'db_query_time', 0.0), 4),
                "queries_per_second": (
                    round(getattr(request.state, 'db_query_count', 0) / duration, 2) 
                    if duration > 0 else 0
                )
            }
        
        return metrics
    
    def _classify_performance(self, duration: float) -> str:
        """Classify request performance level."""
        if duration < 0.1:
            return "excellent"
        elif duration < 0.5:
            return "good"
        elif duration < 1.0:
            return "acceptable"
        elif duration < 3.0:
            return "slow"
        else:
            return "very_slow"
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage metrics."""
        memory_info = self._process.memory_info()
        # Calculate memory percentage manually using system memory
        system_memory = psutil.virtual_memory()
        memory_percent = (memory_info.rss / system_memory.total) * 100
        
        return {
            "rss": round(memory_info.rss / 1024 / 1024, 2),  # MB
            "vms": round(memory_info.vms / 1024 / 1024, 2),  # MB
            "percent": round(memory_percent, 2)
        }
    
    def _get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return round(float(self._process.cpu_percent()), 2)
        except Exception:
            return 0.0
    
    def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store performance metrics for analysis."""
        self._request_metrics.append(metrics)
        
        # Keep only the most recent metrics to prevent memory bloat
        if len(self._request_metrics) > self._max_stored_metrics:
            self._request_metrics = self._request_metrics[-self._max_stored_metrics:]
    
    def _log_performance(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics with appropriate level."""
        duration = metrics["duration_seconds"]
        
        if metrics["is_slow"] and self.log_slow_requests:
            self.logger.warning("Slow request detected", extra=metrics)
        else:
            self.logger.info("Request performance", extra=metrics)
    
    def _log_error_performance(
        self, 
        request: StarletteRequest, 
        exception: Exception, 
        duration: float,
        cpu_time: float
    ) -> None:
        """Log error with performance context."""
        self.logger.error("Request failed with performance context", extra={
            "method": request.method,
            "path": str(request.url.path),
            "duration_seconds": round(duration, 4),
            "cpu_time_seconds": round(cpu_time, 4),
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "client_ip": self._get_client_ip(request)
        }, exc_info=True)
    
    def _add_performance_headers(self, response: StarletteResponse, metrics: Dict[str, Any]) -> None:
        """Add performance headers to response."""
        response.headers["X-Response-Time"] = f"{metrics['duration_ms']}ms"
        response.headers["X-CPU-Time"] = f"{metrics['cpu_time_ms']}ms"
        response.headers["X-Performance-Class"] = metrics["performance_class"]
        
        if "database" in metrics:
            response.headers["X-DB-Query-Count"] = str(metrics["database"]["query_count"])
            response.headers["X-DB-Query-Time"] = f"{metrics['database']['query_time_seconds']}s"
    
    def _get_client_ip(self, request: StarletteRequest) -> str:
        """Get client IP address with proxy support."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the stored metrics."""
        if not self._request_metrics:
            return {"message": "No metrics available"}
        
        durations = [m["duration_seconds"] for m in self._request_metrics]
        
        return {
            "total_requests": len(self._request_metrics),
            "avg_duration_ms": round(sum(durations) / len(durations) * 1000, 2),
            "min_duration_ms": round(min(durations) * 1000, 2),
            "max_duration_ms": round(max(durations) * 1000, 2),
            "slow_requests": sum(1 for m in self._request_metrics if m["is_slow"]),
            "slow_request_percentage": round(
                sum(1 for m in self._request_metrics if m["is_slow"]) / len(self._request_metrics) * 100, 2
            ),
            "performance_classes": self._get_performance_class_distribution(),
            "top_slow_endpoints": self._get_top_slow_endpoints(),
            "memory_stats": self._get_memory_stats() if self.monitor_memory else None,
            "database_stats": self._get_database_stats() if self.track_database_queries else None
        }
    
    def _get_performance_class_distribution(self) -> Dict[str, int]:
        """Get distribution of performance classes."""
        distribution: Dict[str, int] = {}
        for metric in self._request_metrics:
            perf_class = metric["performance_class"]
            distribution[perf_class] = distribution.get(perf_class, 0) + 1
        return distribution
    
    def _get_top_slow_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top slowest endpoints."""
        endpoint_times: Dict[str, List[float]] = {}
        
        for metric in self._request_metrics:
            key = f"{metric['method']} {metric['path']}"
            if key not in endpoint_times:
                endpoint_times[key] = []
            endpoint_times[key].append(metric["duration_seconds"])
        
        endpoint_averages: List[Dict[str, Any]] = [
            {
                "endpoint": endpoint,
                "avg_duration_ms": round(sum(times) / len(times) * 1000, 2),
                "max_duration_ms": round(max(times) * 1000, 2),
                "request_count": len(times)
            }
            for endpoint, times in endpoint_times.items()
        ]
        
        def get_avg_duration(x: Dict[str, Any]) -> float:
            avg = x["avg_duration_ms"]
            return float(avg) if avg is not None else 0.0
            
        return sorted(endpoint_averages, key=get_avg_duration, reverse=True)[:limit]
    
    def _get_memory_stats(self) -> Optional[Dict[str, Any]]:
        """Get memory usage statistics."""
        memory_metrics = [m for m in self._request_metrics if "memory" in m]
        if not memory_metrics:
            return None
        
        memory_deltas = [m["memory"]["memory_delta_mb"] for m in memory_metrics]
        
        return {
            "avg_memory_delta_mb": round(sum(memory_deltas) / len(memory_deltas), 2),
            "max_memory_delta_mb": round(max(memory_deltas), 2),
            "min_memory_delta_mb": round(min(memory_deltas), 2),
            "current_memory_percent": self._get_memory_usage()["percent"]
        }
    
    def _get_database_stats(self) -> Optional[Dict[str, Any]]:
        """Get database query statistics."""
        db_metrics = [m for m in self._request_metrics if "database" in m]
        if not db_metrics:
            return None
        
        query_counts = [m["database"]["query_count"] for m in db_metrics]
        query_times = [m["database"]["query_time_seconds"] for m in db_metrics]
        
        return {
            "avg_queries_per_request": round(sum(query_counts) / len(query_counts), 2),
            "max_queries_per_request": max(query_counts),
            "avg_query_time_seconds": round(sum(query_times) / len(query_times), 4),
            "max_query_time_seconds": round(max(query_times), 4),
            "total_db_time_seconds": round(sum(query_times), 4)
        }


class DatabaseQueryTracker:
    """Helper class for tracking database queries within requests."""
    
    @staticmethod
    def track_query(request: StarletteRequest, query_time: float) -> None:
        """Track a database query execution."""
        if hasattr(request.state, 'db_query_count'):
            request.state.db_query_count += 1
            request.state.db_query_time += query_time
    
    @staticmethod
    def get_query_stats(request: StarletteRequest) -> Dict[str, Any]:
        """Get current query statistics for the request."""
        return {
            "query_count": getattr(request.state, 'db_query_count', 0),
            "query_time": getattr(request.state, 'db_query_time', 0.0)
        }


# Global instance for easy access
db_query_tracker = DatabaseQueryTracker()