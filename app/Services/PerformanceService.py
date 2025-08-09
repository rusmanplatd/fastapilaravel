from __future__ import annotations

import time
import asyncio
import psutil
import logging
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from functools import wraps
from collections import defaultdict, deque
import threading
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session
from sqlalchemy import event, Engine
from fastapi import Request, Response

from app.Services.CacheService import get_cache_manager
from app.Services.LoggingService import get_logger, LogContext

T = TypeVar('T')


@dataclass
class QueryMetrics:
    """Metrics for database queries."""
    query: str
    duration: float
    timestamp: datetime
    parameters: Optional[Dict[str, Any]] = None
    rows_affected: Optional[int] = None
    connection_info: Optional[Dict[str, Any]] = None


@dataclass
class RequestMetrics:
    """Metrics for HTTP requests."""
    method: str
    path: str
    status_code: int
    duration: float
    timestamp: datetime
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_usage: float
    active_connections: int
    request_rate: float


class PerformanceMonitor:
    """
    Performance monitoring service for tracking application metrics.
    
    Monitors:
    - Database query performance
    - HTTP request performance
    - System resource usage
    - Memory and CPU utilization
    - Slow query detection
    """
    
    def __init__(self, cache_manager: Optional[Any] = None) -> None:
        self.cache = cache_manager or get_cache_manager()
        self.logger = get_logger()
        
        # Metrics storage
        self.query_metrics: deque[QueryMetrics] = deque(maxlen=1000)
        self.request_metrics: deque[RequestMetrics] = deque(maxlen=1000)
        self.system_metrics: deque[SystemMetrics] = deque(maxlen=100)
        
        # Configuration
        self.slow_query_threshold = 1.0  # seconds
        self.slow_request_threshold = 5.0  # seconds
        self.monitoring_enabled = True
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'total_requests': 0,
            'slow_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Start background monitoring
        self._start_system_monitoring()
    
    def enable_query_monitoring(self, engine: Engine) -> None:
        """Enable SQLAlchemy query monitoring."""
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn: Any, cursor: Any, statement: Any, parameters: Any, context: Any, executemany: Any) -> None:
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn: Any, cursor: Any, statement: Any, parameters: Any, context: Any, executemany: Any) -> None:
            duration = time.time() - context._query_start_time
            
            if self.monitoring_enabled:
                self.record_query_metrics(QueryMetrics(
                    query=statement,
                    duration=duration,
                    timestamp=datetime.utcnow(),
                    parameters=parameters,
                    connection_info={
                        'database': conn.info.get('database_name'),
                        'user': conn.info.get('username'),
                    }
                ))
    
    def record_query_metrics(self, metrics: QueryMetrics) -> None:
        """Record database query metrics."""
        with self._lock:
            self.query_metrics.append(metrics)
            self.stats['total_queries'] += 1
            
            if metrics.duration > self.slow_query_threshold:
                self.stats['slow_queries'] += 1
                context = LogContext()
                context.extra = {'query': metrics.query[:200], 'duration': metrics.duration}
                self.logger.warning(
                    f"Slow query detected: {metrics.duration:.3f}s",
                    context=context
                )
    
    def record_request_metrics(self, metrics: RequestMetrics) -> None:
        """Record HTTP request metrics."""
        with self._lock:
            self.request_metrics.append(metrics)
            self.stats['total_requests'] += 1
            
            if metrics.duration > self.slow_request_threshold:
                self.stats['slow_requests'] += 1
                context = LogContext()
                context.extra = {
                    'method': metrics.method,
                    'path': metrics.path,
                    'duration': metrics.duration,
                    'status_code': metrics.status_code
                }
                self.logger.warning(
                    f"Slow request detected: {metrics.method} {metrics.path} - {metrics.duration:.3f}s",
                    context=context
                )
    
    def record_system_metrics(self) -> None:
        """Record current system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available=memory.available,
                disk_usage=disk.percent,
                active_connections=len(psutil.net_connections()),  # type: ignore[attr-defined]
                request_rate=self._calculate_request_rate()
            )
            
            with self._lock:
                self.system_metrics.append(metrics)
            
            # Log critical resource usage
            if cpu_percent > 90:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 90:
                self.logger.warning(f"High memory usage: {memory.percent}%")
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def _calculate_request_rate(self) -> float:
        """Calculate requests per second over the last minute."""
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        recent_requests = [
            r for r in self.request_metrics
            if r.timestamp > one_minute_ago
        ]
        
        return len(recent_requests) / 60.0
    
    def _start_system_monitoring(self) -> None:
        """Start background system monitoring."""
        def monitor_loop() -> None:
            while self.monitoring_enabled:
                try:
                    self.record_system_metrics()
                    time.sleep(60)  # Record every minute
                except Exception as e:
                    self.logger.error(f"System monitoring error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        with self._lock:
            recent_queries = list(self.query_metrics)[-100:]  # Last 100 queries
            recent_requests = list(self.request_metrics)[-100:]  # Last 100 requests
            recent_system = list(self.system_metrics)[-10:]  # Last 10 system snapshots
        
        avg_query_time = sum(q.duration for q in recent_queries) / len(recent_queries) if recent_queries else 0
        avg_request_time = sum(r.duration for r in recent_requests) / len(recent_requests) if recent_requests else 0
        
        current_system = recent_system[-1] if recent_system else None
        
        return {
            'database': {
                'total_queries': self.stats['total_queries'],
                'slow_queries': self.stats['slow_queries'],
                'avg_query_time': avg_query_time,
                'slow_query_percentage': (self.stats['slow_queries'] / max(1, self.stats['total_queries'])) * 100,
            },
            'requests': {
                'total_requests': self.stats['total_requests'],
                'slow_requests': self.stats['slow_requests'],
                'avg_request_time': avg_request_time,
                'slow_request_percentage': (self.stats['slow_requests'] / max(1, self.stats['total_requests'])) * 100,
                'request_rate': current_system.request_rate if current_system else 0,
            },
            'system': {
                'cpu_percent': current_system.cpu_percent if current_system else 0,
                'memory_percent': current_system.memory_percent if current_system else 0,
                'disk_usage': current_system.disk_usage if current_system else 0,
                'active_connections': current_system.active_connections if current_system else 0,
            },
            'cache': {
                'hits': self.stats['cache_hits'],
                'misses': self.stats['cache_misses'],
                'hit_rate': (self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100,
            }
        }


class QueryOptimizer:
    """Query optimization service for improving database performance."""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.logger = get_logger()
        self.cache = get_cache_manager()
        
        # Query analysis
        self.query_patterns: Dict[str, int] = defaultdict(int)
        self.optimization_suggestions: List[Dict[str, Any]] = []
    
    def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze query patterns for optimization opportunities."""
        analysis: Dict[str, Any] = {
            'most_frequent_queries': [],
            'slowest_queries': [],
            'optimization_suggestions': [],
        }
        
        with self.monitor._lock:
            queries = list(self.monitor.query_metrics)
        
        # Find most frequent queries
        query_frequency: defaultdict[str, int] = defaultdict(int)
        query_times = defaultdict(list)
        
        for metric in queries:
            # Normalize query (remove parameters)
            normalized_query = self._normalize_query(metric.query)
            query_frequency[normalized_query] += 1
            query_times[normalized_query].append(metric.duration)
        
        # Most frequent queries
        frequent_queries = sorted(
            query_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        analysis['most_frequent_queries'] = [
            {
                'query': query[:200],
                'count': count,
                'avg_time': sum(query_times[query]) / len(query_times[query])
            }
            for query, count in frequent_queries
        ]
        
        # Slowest queries
        slow_queries = sorted(queries, key=lambda x: x.duration, reverse=True)[:10]
        analysis['slowest_queries'] = [
            {
                'query': q.query[:200],
                'duration': q.duration,
                'timestamp': q.timestamp.isoformat()
            }
            for q in slow_queries
        ]
        
        # Generate optimization suggestions
        analysis['optimization_suggestions'] = self._generate_optimization_suggestions(
            frequent_queries, query_times
        )
        
        return analysis
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing parameters and formatting."""
        # Simple normalization - replace parameters with placeholders
        import re
        
        # Remove string literals
        normalized = re.sub(r"'[^']*'", "'?'", query)
        
        # Remove numeric literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized.lower()
    
    def _generate_optimization_suggestions(
        self,
        frequent_queries: List[tuple],
        query_times: Dict[str, List[float]]
    ) -> List[Dict[str, Any]]:
        """Generate optimization suggestions based on query analysis."""
        suggestions = []
        
        for query, count in frequent_queries:
            avg_time = sum(query_times[query]) / len(query_times[query])
            
            # Suggest caching for frequently accessed queries
            if count > 50 and avg_time > 0.1:
                suggestions.append({
                    'type': 'caching',
                    'query': query[:100],
                    'reason': f'Executed {count} times with avg duration {avg_time:.3f}s',
                    'suggestion': 'Consider caching this query result',
                    'priority': 'high' if avg_time > 1.0 else 'medium'
                })
            
            # Suggest indexing for slow queries
            if avg_time > 1.0:
                suggestions.append({
                    'type': 'indexing',
                    'query': query[:100],
                    'reason': f'Average duration {avg_time:.3f}s',
                    'suggestion': 'Consider adding database indexes',
                    'priority': 'high'
                })
            
            # Suggest query rewriting for complex queries
            if 'join' in query.lower() and avg_time > 0.5:
                suggestions.append({
                    'type': 'query_optimization',
                    'query': query[:100],
                    'reason': f'Complex join query with {avg_time:.3f}s duration',
                    'suggestion': 'Consider optimizing JOIN operations or breaking into smaller queries',
                    'priority': 'medium'
                })
        
        return suggestions


class PerformanceMiddleware:
    """Middleware for automatic performance monitoring."""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.logger = get_logger()
    
    async def __call__(self, request: Request, call_next: Any) -> Any:
        """Process request with performance monitoring."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate metrics
            duration = time.time() - start_time
            end_memory = self._get_memory_usage()
            
            # Record request metrics
            metrics = RequestMetrics(
                method=request.method,  # type: ignore[attr-defined]
                path=str(request.url.path),  # type: ignore[attr-defined]
                status_code=response.status_code,
                duration=duration,
                timestamp=datetime.utcnow(),
                memory_usage=end_memory - start_memory,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get('User-Agent', '')
            )
            
            self.monitor.record_request_metrics(metrics)
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            response.headers["X-Memory-Usage"] = f"{metrics.memory_usage:.2f}MB"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failed request
            metrics = RequestMetrics(
                method=request.method,  # type: ignore[attr-defined]
                path=str(request.url.path),  # type: ignore[attr-defined]
                status_code=500,
                duration=duration,
                timestamp=datetime.utcnow(),
                ip_address=self._get_client_ip(request)
            )
            
            self.monitor.record_request_metrics(metrics)
            raise
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import os
            import psutil
            process = psutil.Process(os.getpid())
            return float(process.memory_info().rss / 1024 / 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        return request.client.host if request.client else "unknown"


def performance_timer(name: Optional[str] = None) -> Any:
    """Decorator for timing function execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            logger = get_logger()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                function_name = name or f"{func.__module__}.{func.__name__}"
                
                logger.debug(
                    f"Function {function_name} executed in {duration:.3f}s",
                    context=LogContext(extra={'function': function_name, 'duration': duration})
                )
                
                return result  # type: ignore
                
            except Exception as e:
                duration = time.time() - start_time
                function_name = name or f"{func.__module__}.{func.__name__}"
                
                logger.error(
                    f"Function {function_name} failed after {duration:.3f}s: {e}",
                    context=LogContext(extra={'function': function_name, 'duration': duration, 'error': str(e)})
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            logger = get_logger()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                function_name = name or f"{func.__module__}.{func.__name__}"
                
                logger.debug(
                    f"Function {function_name} executed in {duration:.3f}s",
                    context=LogContext(extra={'function': function_name, 'duration': duration})
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                function_name = name or f"{func.__module__}.{func.__name__}"
                
                logger.error(
                    f"Function {function_name} failed after {duration:.3f}s: {e}",
                    context=LogContext(extra={'function': function_name, 'duration': duration, 'error': str(e)})
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore[return-value]
    
    return decorator


@asynccontextmanager
async def performance_context(name: str) -> Any:
    """Context manager for timing code blocks."""
    start_time = time.time()
    logger = get_logger()
    
    try:
        yield
        duration = time.time() - start_time
        logger.debug(
            f"Performance context '{name}' completed in {duration:.3f}s",
            context=LogContext(extra={'context': name, 'duration': duration})
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Performance context '{name}' failed after {duration:.3f}s: {e}",
            context=LogContext(extra={'context': name, 'duration': duration, 'error': str(e)})
        )
        raise


class PerformanceService:
    """Main service for performance monitoring and optimization."""
    
    def __init__(self) -> None:
        self.monitor = PerformanceMonitor()
        self.optimizer = QueryOptimizer(self.monitor)
        self.middleware = PerformanceMiddleware(self.monitor)
        self.logger = get_logger()
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure performance monitoring."""
        self.monitor.slow_query_threshold = config.get('slow_query_threshold', 1.0)
        self.monitor.slow_request_threshold = config.get('slow_request_threshold', 5.0)
        self.monitor.monitoring_enabled = config.get('monitoring_enabled', True)
        
        self.logger.info(
            "Performance monitoring configured",
            context=LogContext(extra={
                'slow_query_threshold': self.monitor.slow_query_threshold,
                'slow_request_threshold': self.monitor.slow_request_threshold,
                'monitoring_enabled': self.monitor.monitoring_enabled
            })
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        metrics_summary = self.monitor.get_metrics_summary()
        query_analysis = self.optimizer.analyze_query_patterns()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': metrics_summary,
            'query_analysis': query_analysis,
            'recommendations': self._generate_recommendations(metrics_summary, query_analysis)
        }
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, Any],
        query_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate performance recommendations."""
        recommendations = []
        
        # Database recommendations
        if metrics['database']['slow_query_percentage'] > 10:
            recommendations.append({
                'category': 'database',
                'priority': 'high',
                'issue': f"{metrics['database']['slow_query_percentage']:.1f}% of queries are slow",
                'recommendation': 'Review slow queries and consider adding indexes or optimizing queries'
            })
        
        # Request performance recommendations
        if metrics['requests']['slow_request_percentage'] > 5:
            recommendations.append({
                'category': 'requests',
                'priority': 'high',
                'issue': f"{metrics['requests']['slow_request_percentage']:.1f}% of requests are slow",
                'recommendation': 'Profile slow endpoints and optimize processing logic'
            })
        
        # System resource recommendations
        if metrics['system']['cpu_percent'] > 80:
            recommendations.append({
                'category': 'system',
                'priority': 'critical',
                'issue': f"High CPU usage: {metrics['system']['cpu_percent']:.1f}%",
                'recommendation': 'Consider scaling horizontally or optimizing CPU-intensive operations'
            })
        
        if metrics['system']['memory_percent'] > 85:
            recommendations.append({
                'category': 'system',
                'priority': 'critical',
                'issue': f"High memory usage: {metrics['system']['memory_percent']:.1f}%",
                'recommendation': 'Review memory usage patterns and consider increasing available memory'
            })
        
        # Cache recommendations
        if metrics['cache']['hit_rate'] < 70:
            recommendations.append({
                'category': 'cache',
                'priority': 'medium',
                'issue': f"Low cache hit rate: {metrics['cache']['hit_rate']:.1f}%",
                'recommendation': 'Review caching strategy and increase cache coverage for frequently accessed data'
            })
        
        return recommendations


# Global performance service instance
_performance_service: Optional[PerformanceService] = None


def get_performance_service() -> PerformanceService:
    """Get the global performance service instance."""
    global _performance_service
    if _performance_service is None:
        _performance_service = PerformanceService()
    return _performance_service