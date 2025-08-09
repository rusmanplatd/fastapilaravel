"""
Blade Template Analytics and Performance Monitoring
Provides comprehensive analytics, performance tracking, and optimization insights
"""
from __future__ import annotations

import time
import threading
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set, Tuple, Generator
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from contextlib import contextmanager
import psutil
import sys
import traceback
import weakref


@dataclass
class RenderMetrics:
    """Metrics for a single template render"""
    template_name: str
    render_time: float
    memory_usage: int
    context_size: int
    output_size: int
    cache_hit: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    dependencies: Set[str] = field(default_factory=set)
    compilation_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['dependencies'] = list(self.dependencies)
        return data


@dataclass
class TemplateStats:
    """Aggregated statistics for a template"""
    template_name: str
    total_renders: int = 0
    total_render_time: float = 0.0
    min_render_time: float = float('inf')
    max_render_time: float = 0.0
    avg_render_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    last_rendered: Optional[datetime] = None
    popularity_score: float = 0.0
    memory_usage_avg: float = 0.0
    output_size_avg: float = 0.0
    
    def update_with_metrics(self, metrics: RenderMetrics) -> None:
        """Update stats with new render metrics"""
        self.total_renders += 1
        self.total_render_time += metrics.render_time
        self.min_render_time = min(self.min_render_time, metrics.render_time)
        self.max_render_time = max(self.max_render_time, metrics.render_time)
        self.avg_render_time = self.total_render_time / self.total_renders
        
        if metrics.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        if metrics.error:
            self.errors += 1
        
        self.last_rendered = metrics.timestamp
        
        # Update averages
        self.memory_usage_avg = (
            (self.memory_usage_avg * (self.total_renders - 1) + metrics.memory_usage) 
            / self.total_renders
        )
        
        self.output_size_avg = (
            (self.output_size_avg * (self.total_renders - 1) + metrics.output_size)
            / self.total_renders
        )
        
        # Calculate popularity score (renders per hour in last 24h)
        now = datetime.now()
        if self.last_rendered:
            hours_since_last = (now - self.last_rendered).total_seconds() / 3600
            if hours_since_last <= 24:
                self.popularity_score = self.total_renders / max(hours_since_last, 1)


class PerformanceProfiler:
    """Performance profiler for template operations"""
    
    def __init__(self) -> None:
        self.active_profiles: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def profile_operation(self, operation_name: str, template_name: str = '') -> Generator[None, None, None]:
        """Context manager for profiling operations"""
        profile_key = f"{template_name}:{operation_name}"
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss
            
            with self._lock:
                self.active_profiles[profile_key] = {
                    'operation': operation_name,
                    'template': template_name,
                    'duration': end_time - start_time,
                    'memory_delta': end_memory - start_memory,
                    'timestamp': datetime.now()
                }
    
    def get_profile_data(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get profile data for analysis"""
        with self._lock:
            if operation_name:
                return {k: v for k, v in self.active_profiles.items() 
                       if v['operation'] == operation_name}
            return dict(self.active_profiles)
    
    def clear_profiles(self) -> None:
        """Clear all profile data"""
        with self._lock:
            self.active_profiles.clear()


class ErrorTracker:
    """Tracks and analyzes template errors"""
    
    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors: deque[Dict[str, Any]] = deque(maxlen=max_errors)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def record_error(self, template_name: str, error: Exception, 
                    context: Optional[Dict[str, Any]] = None) -> None:
        """Record a template error"""
        with self._lock:
            error_data = {
                'template_name': template_name,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now(),
                'context_keys': list(context.keys()) if context else []
            }
            
            self.errors.append(error_data)
            self.error_counts[template_name] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            total_errors = len(self.errors)
            if total_errors == 0:
                return {'total_errors': 0}
            
            # Error frequency analysis
            recent_errors = [e for e in self.errors 
                           if (datetime.now() - e['timestamp']).total_seconds() < 3600]
            
            error_types: Dict[str, int] = defaultdict(int)
            for error in self.errors:
                error_types[error['error_type']] += 1
            
            return {
                'total_errors': total_errors,
                'recent_errors_1h': len(recent_errors),
                'most_common_errors': dict(sorted(error_types.items(), 
                                                key=lambda x: x[1], reverse=True)[:10]),
                'templates_with_errors': dict(sorted(self.error_counts.items(),
                                                   key=lambda x: x[1], reverse=True)[:10])
            }
    
    def get_errors_for_template(self, template_name: str) -> List[Dict[str, Any]]:
        """Get errors for a specific template"""
        with self._lock:
            return [error for error in self.errors 
                   if error['template_name'] == template_name]


class ResourceMonitor:
    """Monitors system resources during template operations"""
    
    def __init__(self) -> None:
        self.cpu_samples: deque[Dict[str, Any]] = deque(maxlen=100)
        self.memory_samples: deque[Dict[str, Any]] = deque(maxlen=100)
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """Start resource monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_loop() -> None:
            while self.monitoring:
                try:
                    process = psutil.Process()
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    
                    with self._lock:
                        self.cpu_samples.append({
                            'timestamp': datetime.now(),
                            'cpu_percent': cpu_percent
                        })
                        
                        self.memory_samples.append({
                            'timestamp': datetime.now(),
                            'memory_rss': memory_info.rss,
                            'memory_vms': memory_info.vms
                        })
                    
                    time.sleep(interval)
                except Exception:
                    pass  # Ignore monitoring errors
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics"""
        with self._lock:
            if not self.cpu_samples or not self.memory_samples:
                return {}
            
            cpu_values = [s['cpu_percent'] for s in self.cpu_samples]
            memory_values = [s['memory_rss'] for s in self.memory_samples]
            
            return {
                'cpu': {
                    'avg': statistics.mean(cpu_values),
                    'max': max(cpu_values),
                    'min': min(cpu_values),
                    'current': cpu_values[-1] if cpu_values else 0
                },
                'memory': {
                    'avg_mb': statistics.mean(memory_values) / (1024 * 1024),
                    'max_mb': max(memory_values) / (1024 * 1024),
                    'min_mb': min(memory_values) / (1024 * 1024),
                    'current_mb': memory_values[-1] / (1024 * 1024) if memory_values else 0
                },
                'sample_count': len(self.cpu_samples)
            }


class DependencyAnalyzer:
    """Analyzes template dependencies and relationships"""
    
    def __init__(self) -> None:
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.usage_graph: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()
    
    def record_dependency(self, template: str, dependency: str) -> None:
        """Record a template dependency"""
        with self._lock:
            self.dependency_graph[template].add(dependency)
            self.usage_graph[dependency].add(template)
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependency patterns"""
        with self._lock:
            # Find most included templates
            most_included = sorted(
                [(dep, len(users)) for dep, users in self.usage_graph.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
            
            # Find templates with most dependencies
            most_dependent = sorted(
                [(template, len(deps)) for template, deps in self.dependency_graph.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
            
            # Calculate dependency depth
            def get_dependency_depth(template: str, visited: Optional[Set[str]] = None) -> int:
                if visited is None:
                    visited = set()
                
                if template in visited:
                    return 0  # Circular dependency
                
                visited.add(template)
                dependencies = self.dependency_graph.get(template, set())
                
                if not dependencies:
                    return 0
                
                max_depth = 0
                for dep in dependencies:
                    depth = get_dependency_depth(dep, visited.copy())
                    max_depth = max(max_depth, depth)
                
                return max_depth + 1
            
            depth_analysis = {}
            for template in self.dependency_graph:
                depth_analysis[template] = get_dependency_depth(template)
            
            return {
                'total_templates': len(self.dependency_graph),
                'total_dependencies': sum(len(deps) for deps in self.dependency_graph.values()),
                'most_included': most_included,
                'most_dependent': most_dependent,
                'dependency_depths': depth_analysis,
                'avg_dependencies_per_template': (
                    sum(len(deps) for deps in self.dependency_graph.values()) / 
                    max(len(self.dependency_graph), 1)
                )
            }


class BladeAnalytics:
    """Main analytics system for Blade templates"""
    
    def __init__(self, storage_path: str = 'storage/analytics'):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.profiler = PerformanceProfiler()
        self.error_tracker = ErrorTracker()
        self.resource_monitor = ResourceMonitor()
        self.dependency_analyzer = DependencyAnalyzer()
        
        # Data storage
        self.render_history: deque[RenderMetrics] = deque(maxlen=10000)
        self.template_stats: Dict[str, TemplateStats] = {}
        
        # Configuration
        self.enabled = True
        self.detailed_profiling = False
        
        # Threading
        self._lock = threading.RLock()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Load existing data
        self._load_analytics_data()
    
    def record_render(self, template_name: str, render_time: float, 
                     context: Dict[str, Any], output: str,
                     cache_hit: bool = False, error: Optional[Exception] = None,
                     dependencies: Optional[Set[str]] = None) -> None:
        """Record a template render event"""
        if not self.enabled:
            return
        
        try:
            with self._lock:
                # Calculate metrics
                memory_info = psutil.Process().memory_info()
                context_size = sys.getsizeof(json.dumps(context, default=str))
                output_size = len(output.encode('utf-8'))
                
                metrics = RenderMetrics(
                    template_name=template_name,
                    render_time=render_time,
                    memory_usage=memory_info.rss,
                    context_size=context_size,
                    output_size=output_size,
                    cache_hit=cache_hit,
                    error=str(error) if error else None,
                    dependencies=dependencies or set()
                )
                
                # Record in history
                self.render_history.append(metrics)
                
                # Update template stats
                if template_name not in self.template_stats:
                    self.template_stats[template_name] = TemplateStats(template_name)
                
                self.template_stats[template_name].update_with_metrics(metrics)
                
                # Record error if present
                if error:
                    self.error_tracker.record_error(template_name, error, context)
                
                # Record dependencies
                if dependencies:
                    for dep in dependencies:
                        self.dependency_analyzer.record_dependency(template_name, dep)
        
        except Exception:
            pass  # Don't let analytics break the application
    
    def get_performance_report(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if time_range is None:
            time_range = timedelta(hours=24)
        
        with self._lock:
            cutoff_time = datetime.now() - time_range
            recent_renders = [
                r for r in self.render_history 
                if r.timestamp >= cutoff_time
            ]
            
            if not recent_renders:
                return {'error': 'No render data in specified time range'}
            
            # Overall statistics
            total_renders = len(recent_renders)
            total_render_time = sum(r.render_time for r in recent_renders)
            avg_render_time = total_render_time / total_renders
            
            render_times = [r.render_time for r in recent_renders]
            p50_render_time = statistics.median(render_times)
            p95_render_time = statistics.quantiles(render_times, n=20)[18]  # 95th percentile
            p99_render_time = statistics.quantiles(render_times, n=100)[98]  # 99th percentile
            
            # Template-specific stats
            template_performance = {}
            for template_name, stats in self.template_stats.items():
                template_performance[template_name] = {
                    'total_renders': stats.total_renders,
                    'avg_render_time': stats.avg_render_time,
                    'min_render_time': stats.min_render_time,
                    'max_render_time': stats.max_render_time,
                    'cache_hit_rate': (stats.cache_hits / max(stats.total_renders, 1)) * 100,
                    'error_rate': (stats.errors / max(stats.total_renders, 1)) * 100,
                    'popularity_score': stats.popularity_score,
                    'avg_memory_usage_mb': stats.memory_usage_avg / (1024 * 1024),
                    'avg_output_size_kb': stats.output_size_avg / 1024
                }
            
            # Top performing templates
            fastest_templates = sorted(
                template_performance.items(),
                key=lambda x: x[1]['avg_render_time']
            )[:10]
            
            slowest_templates = sorted(
                template_performance.items(),
                key=lambda x: x[1]['avg_render_time'],
                reverse=True
            )[:10]
            
            most_popular = sorted(
                template_performance.items(),
                key=lambda x: x[1]['popularity_score'],
                reverse=True
            )[:10]
            
            return {
                'time_range': str(time_range),
                'summary': {
                    'total_renders': total_renders,
                    'avg_render_time_ms': avg_render_time * 1000,
                    'p50_render_time_ms': p50_render_time * 1000,
                    'p95_render_time_ms': p95_render_time * 1000,
                    'p99_render_time_ms': p99_render_time * 1000,
                    'total_templates': len(self.template_stats),
                    'cache_hit_rate': sum(1 for r in recent_renders if r.cache_hit) / total_renders * 100
                },
                'template_performance': template_performance,
                'top_performers': {
                    'fastest': fastest_templates,
                    'slowest': slowest_templates,
                    'most_popular': most_popular
                },
                'resource_usage': self.resource_monitor.get_resource_stats(),
                'error_stats': self.error_tracker.get_error_stats(),
                'dependency_analysis': self.dependency_analyzer.analyze_dependencies()
            }
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Generate optimization suggestions"""
        suggestions = []
        
        with self._lock:
            # Find slow templates
            for template_name, stats in self.template_stats.items():
                if stats.avg_render_time > 0.1:  # > 100ms
                    suggestions.append({
                        'type': 'performance',
                        'template': template_name,
                        'issue': 'Slow rendering',
                        'detail': f'Average render time: {stats.avg_render_time*1000:.1f}ms',
                        'suggestions': [
                            'Consider caching this template',
                            'Review complex logic in template',
                            'Check for expensive computations',
                            'Optimize database queries in context'
                        ]
                    })
            
            # Find templates with low cache hit rates
            for template_name, stats in self.template_stats.items():
                if stats.total_renders > 10:  # Only for frequently used templates
                    cache_hit_rate = stats.cache_hits / stats.total_renders
                    if cache_hit_rate < 0.5:  # < 50% cache hit rate
                        suggestions.append({
                            'type': 'caching',
                            'template': template_name,
                            'issue': 'Low cache hit rate',
                            'detail': f'Cache hit rate: {cache_hit_rate*100:.1f}%',
                            'suggestions': [
                                'Review cache invalidation strategy',
                                'Consider longer cache TTL',
                                'Check for dynamic content that prevents caching'
                            ]
                        })
            
            # Find templates with high error rates
            for template_name, stats in self.template_stats.items():
                if stats.total_renders > 5:  # Only for templates with some usage
                    error_rate = stats.errors / stats.total_renders
                    if error_rate > 0.05:  # > 5% error rate
                        suggestions.append({
                            'type': 'reliability',
                            'template': template_name,
                            'issue': 'High error rate',
                            'detail': f'Error rate: {error_rate*100:.1f}%',
                            'suggestions': [
                                'Add null checks for variables',
                                'Provide default values',
                                'Add error handling directives',
                                'Review template logic'
                            ]
                        })
            
            # Memory usage suggestions
            resource_stats = self.resource_monitor.get_resource_stats()
            if resource_stats and resource_stats.get('memory', {}).get('avg_mb', 0) > 500:
                suggestions.append({
                    'type': 'memory',
                    'template': 'system',
                    'issue': 'High memory usage',
                    'detail': f'Average memory: {resource_stats["memory"]["avg_mb"]:.1f}MB',
                    'suggestions': [
                        'Enable template caching to reduce recompilation',
                        'Optimize context data size',
                        'Review memory-intensive templates',
                        'Consider template streaming for large outputs'
                    ]
                })
        
        return suggestions
    
    def export_analytics_data(self, format: str = 'json') -> str:
        """Export analytics data"""
        with self._lock:
            data = {
                'export_timestamp': datetime.now().isoformat(),
                'template_stats': {k: asdict(v) for k, v in self.template_stats.items()},
                'recent_renders': [r.to_dict() for r in list(self.render_history)[-1000:]],
                'error_stats': self.error_tracker.get_error_stats(),
                'resource_stats': self.resource_monitor.get_resource_stats(),
                'dependency_analysis': self.dependency_analyzer.analyze_dependencies()
            }
            
            if format == 'json':
                return json.dumps(data, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    def _load_analytics_data(self) -> None:
        """Load existing analytics data"""
        data_file = self.storage_path / 'analytics.json'
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                # Restore template stats
                for template_name, stats_data in data.get('template_stats', {}).items():
                    stats = TemplateStats(template_name)
                    for key, value in stats_data.items():
                        if hasattr(stats, key):
                            if key == 'last_rendered' and value:
                                setattr(stats, key, datetime.fromisoformat(value))
                            else:
                                setattr(stats, key, value)
                    self.template_stats[template_name] = stats
                
            except Exception:
                pass  # Ignore loading errors
    
    def _save_analytics_data(self) -> None:
        """Save analytics data to disk"""
        data_file = self.storage_path / 'analytics.json'
        try:
            with self._lock:
                data = {
                    'template_stats': {k: asdict(v) for k, v in self.template_stats.items()},
                    'last_saved': datetime.now().isoformat()
                }
                
                with open(data_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                    
        except Exception:
            pass  # Ignore saving errors
    
    def clear_analytics(self) -> None:
        """Clear all analytics data"""
        with self._lock:
            self.render_history.clear()
            self.template_stats.clear()
            self.profiler.clear_profiles()
            self.error_tracker.errors.clear()
            self.error_tracker.error_counts.clear()
    
    def shutdown(self) -> None:
        """Shutdown analytics system"""
        self.resource_monitor.stop_monitoring()
        self._save_analytics_data()


# Context manager for render analytics
@contextmanager
def track_render(analytics: BladeAnalytics, template_name: str, 
                context: Dict[str, Any], dependencies: Optional[Set[str]] = None) -> Generator[None, None, None]:
    """Context manager to track template rendering"""
    start_time = time.perf_counter()
    error = None
    output = ''
    
    try:
        yield
    except Exception as e:
        error = e
        raise
    finally:
        end_time = time.perf_counter()
        render_time = end_time - start_time
        
        analytics.record_render(
            template_name=template_name,
            render_time=render_time,
            context=context,
            output=output,
            error=error,
            dependencies=dependencies or set()
        )