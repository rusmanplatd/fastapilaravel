from __future__ import annotations

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from typing_extensions import TypedDict

class DailyStatsDict(TypedDict):
    count: int
    total_duration: float
    failures: int
    cpu_usage: List[float]
    memory_usage: List[float]
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json


@dataclass
class PerformanceMetric:
    """Performance metric for migration execution."""
    migration_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    cpu_usage: Optional[List[float]] = None
    memory_usage: Optional[List[int]] = None
    disk_io: Optional[Dict[str, int]] = None
    database_queries: int = 0
    rows_affected: Optional[int] = None
    status: str = "running"  # running, completed, failed
    error_message: Optional[str] = None


class MigrationMonitor:
    """Monitors migration performance and resource usage."""
    
    def __init__(self, log_file: str = "storage/logs/migration_performance.log") -> None:
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.current_metrics: Dict[str, PerformanceMetric] = {}
        self.monitoring_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
    
    def start_monitoring(self, migration_name: str) -> None:
        """Start monitoring a migration's performance."""
        metric = PerformanceMetric(
            migration_name=migration_name,
            start_time=datetime.now(),
            cpu_usage=[],
            memory_usage=[],
            disk_io={}
        )
        
        self.current_metrics[migration_name] = metric
        
        # Start monitoring thread
        stop_event = threading.Event()
        self._stop_events[migration_name] = stop_event
        
        monitor_thread = threading.Thread(
            target=self._monitor_resources,
            args=(migration_name, stop_event),
            daemon=True
        )
        monitor_thread.start()
        self.monitoring_threads[migration_name] = monitor_thread
    
    def stop_monitoring(self, migration_name: str, status: str = "completed", error: Optional[str] = None) -> PerformanceMetric:
        """Stop monitoring and finalize metrics."""
        if migration_name not in self.current_metrics:
            raise ValueError(f"No monitoring started for migration: {migration_name}")
        
        # Stop the monitoring thread
        if migration_name in self.stop_monitoring:
            self._stop_events[migration_name].set()
            
            # Wait for thread to finish
            if migration_name in self.monitoring_threads:
                self.monitoring_threads[migration_name].join(timeout=1.0)
                del self.monitoring_threads[migration_name]
            
            del self._stop_events[migration_name]
        
        # Finalize metrics
        metric = self.current_metrics[migration_name]
        metric.end_time = datetime.now()
        metric.duration = (metric.end_time - metric.start_time).total_seconds()
        metric.status = status
        metric.error_message = error
        
        # Log the metrics
        self._log_performance(metric)
        
        # Clean up
        del self.current_metrics[migration_name]
        
        return metric
    
    def _monitor_resources(self, migration_name: str, stop_event: threading.Event) -> None:
        """Monitor system resources during migration."""
        metric = self.current_metrics[migration_name]
        
        # Get initial disk I/O stats
        try:
            disk_io_start = psutil.disk_io_counters()  # type: ignore[attr-defined]
            initial_disk_read = disk_io_start.read_bytes if disk_io_start else 0
            initial_disk_write = disk_io_start.write_bytes if disk_io_start else 0
        except Exception:
            initial_disk_read = initial_disk_write = 0
        
        while not stop_event.wait(1.0):  # Sample every second
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1.0)
                if metric.cpu_usage is not None:
                    metric.cpu_usage.append(cpu_percent)
                
                # Memory usage (in MB)
                memory = psutil.virtual_memory()
                if metric.memory_usage is not None:
                    metric.memory_usage.append(memory.used // (1024 * 1024))
                
            except Exception as e:
                print(f"Error monitoring resources for {migration_name}: {e}")
        
        # Final disk I/O calculation
        try:
            disk_io_end = psutil.disk_io_counters()  # type: ignore[attr-defined]
            if disk_io_end:
                metric.disk_io = {
                    "read_bytes": disk_io_end.read_bytes - initial_disk_read,
                    "write_bytes": disk_io_end.write_bytes - initial_disk_write
                }
        except Exception:
            metric.disk_io = {"read_bytes": 0, "write_bytes": 0}
    
    def _log_performance(self, metric: PerformanceMetric) -> None:
        """Log performance metrics to file."""
        log_entry = {
            "timestamp": metric.start_time.isoformat(),
            "migration_name": metric.migration_name,
            "duration": metric.duration,
            "status": metric.status,
            "cpu_usage": {
                "avg": sum(metric.cpu_usage) / len(metric.cpu_usage) if metric.cpu_usage else 0,
                "max": max(metric.cpu_usage) if metric.cpu_usage else 0,
                "min": min(metric.cpu_usage) if metric.cpu_usage else 0
            },
            "memory_usage": {
                "avg": sum(metric.memory_usage) / len(metric.memory_usage) if metric.memory_usage else 0,
                "max": max(metric.memory_usage) if metric.memory_usage else 0,
                "min": min(metric.memory_usage) if metric.memory_usage else 0
            },
            "disk_io": metric.disk_io or {},
            "database_queries": metric.database_queries,
            "rows_affected": metric.rows_affected,
            "error": metric.error_message
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def get_historical_metrics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical performance metrics."""
        if not self.log_file.exists():
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        metrics = []
        
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry['timestamp'])
                    
                    if entry_date >= cutoff_date:
                        metrics.append(entry)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        return metrics
    
    def generate_performance_report(self, migration_name: Optional[str] = None, days: int = 7) -> str:
        """Generate performance report."""
        metrics = self.get_historical_metrics(days)
        
        if migration_name:
            metrics = [m for m in metrics if m['migration_name'] == migration_name]
        
        if not metrics:
            return "No performance data available."
        
        report = f"Migration Performance Report (Last {days} days)\n"
        report += "=" * 60 + "\n\n"
        
        # Summary statistics
        total_migrations = len(metrics)
        successful_migrations = len([m for m in metrics if m['status'] == 'completed'])
        failed_migrations = len([m for m in metrics if m['status'] == 'failed'])
        
        report += f"Total Migrations: {total_migrations}\n"
        report += f"Successful: {successful_migrations}\n"
        report += f"Failed: {failed_migrations}\n"
        report += f"Success Rate: {(successful_migrations/total_migrations)*100:.1f}%\n\n"
        
        # Performance statistics
        durations = [m['duration'] for m in metrics if m['duration']]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            report += f"Average Duration: {avg_duration:.2f} seconds\n"
            report += f"Max Duration: {max_duration:.2f} seconds\n"
            report += f"Min Duration: {min_duration:.2f} seconds\n\n"
        
        # Resource usage statistics
        cpu_averages = [m['cpu_usage']['avg'] for m in metrics if 'cpu_usage' in m]
        if cpu_averages:
            avg_cpu = sum(cpu_averages) / len(cpu_averages)
            report += f"Average CPU Usage: {avg_cpu:.1f}%\n"
        
        memory_averages = [m['memory_usage']['avg'] for m in metrics if 'memory_usage' in m]
        if memory_averages:
            avg_memory = sum(memory_averages) / len(memory_averages)
            report += f"Average Memory Usage: {avg_memory:.0f} MB\n\n"
        
        # Slowest migrations
        if durations:
            sorted_metrics = sorted(metrics, key=lambda m: m.get('duration', 0), reverse=True)
            report += "Slowest Migrations:\n"
            report += "-" * 30 + "\n"
            
            for i, metric in enumerate(sorted_metrics[:5], 1):
                duration = metric.get('duration', 0)
                report += f"{i:2}. {metric['migration_name']:<30} {duration:6.2f}s\n"
        
        return report
    
    def analyze_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        metrics = self.get_historical_metrics(days)
        
        if not metrics:
            return {"error": "No data available"}
        
        # Group by date
        daily_stats: Dict[str, DailyStatsDict] = {}
        for metric in metrics:
            date = metric['timestamp'][:10]  # Extract date part
            
            if date not in daily_stats:
                daily_stats[date] = DailyStatsDict(
                    count=0,
                    total_duration=0.0,
                    failures=0,
                    cpu_usage=[],
                    memory_usage=[]
                )
            
            stats = daily_stats[date]
            stats["count"] += 1
            duration = metric.get("duration")
            if isinstance(duration, (int, float)):
                stats["total_duration"] += duration
            
            if metric["status"] == "failed":
                stats["failures"] += 1
            
            if "cpu_usage" in metric and isinstance(metric["cpu_usage"], dict):
                cpu_avg = metric["cpu_usage"].get("avg")
                if isinstance(cpu_avg, (int, float)):
                    stats["cpu_usage"].append(cpu_avg)
            
            if "memory_usage" in metric and isinstance(metric["memory_usage"], dict):
                memory_avg = metric["memory_usage"].get("avg")
                if isinstance(memory_avg, (int, float)):
                    stats["memory_usage"].append(memory_avg)
        
        # Calculate trends
        analysis = {
            "total_days": len(daily_stats),
            "daily_averages": {},
            "trends": {}
        }
        
        for date, stats in daily_stats.items():
            avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
            failure_rate = (stats["failures"] / stats["count"]) * 100 if stats["count"] > 0 else 0
            avg_cpu = sum(stats["cpu_usage"]) / len(stats["cpu_usage"]) if stats["cpu_usage"] else 0
            avg_memory = sum(stats["memory_usage"]) / len(stats["memory_usage"]) if stats["memory_usage"] else 0
            
            analysis["daily_averages"][date] = {
                "migrations": stats["count"],
                "avg_duration": avg_duration,
                "failure_rate": failure_rate,
                "avg_cpu": avg_cpu,
                "avg_memory": avg_memory
            }
        
        return analysis
    
    def identify_performance_issues(self, migration_name: str) -> List[str]:
        """Identify potential performance issues for a migration."""
        metrics = self.get_historical_metrics()
        migration_metrics = [m for m in metrics if m['migration_name'] == migration_name]
        
        if not migration_metrics:
            return ["No historical data available for this migration"]
        
        issues = []
        latest_metric = max(migration_metrics, key=lambda m: m['timestamp'])
        
        # Check duration
        if latest_metric.get('duration', 0) > 60:  # More than 1 minute
            issues.append("Migration takes longer than 1 minute to execute")
        
        # Check CPU usage
        cpu_avg = latest_metric.get('cpu_usage', {}).get('avg', 0)
        if cpu_avg > 80:
            issues.append(f"High CPU usage detected: {cpu_avg:.1f}%")
        
        # Check memory usage
        memory_max = latest_metric.get('memory_usage', {}).get('max', 0)
        if memory_max > 1024:  # More than 1GB
            issues.append(f"High memory usage detected: {memory_max:.0f} MB")
        
        # Check failure rate
        failed_runs = len([m for m in migration_metrics if m['status'] == 'failed'])
        failure_rate = (failed_runs / len(migration_metrics)) * 100
        if failure_rate > 10:
            issues.append(f"High failure rate: {failure_rate:.1f}%")
        
        # Check consistency
        durations = [m['duration'] for m in migration_metrics if m.get('duration')]
        if len(durations) > 1:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            
            if max_duration > avg_duration * 3:
                issues.append("Inconsistent execution times detected")
        
        return issues if issues else ["No performance issues detected"]
    
    def cleanup_old_logs(self, days: int = 90) -> None:
        """Clean up old performance logs."""
        if not self.log_file.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        temp_file = self.log_file.with_suffix('.tmp')
        
        with open(self.log_file, 'r') as input_file, open(temp_file, 'w') as output_file:
            for line in input_file:
                try:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry['timestamp'])
                    
                    if entry_date >= cutoff_date:
                        output_file.write(line)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        temp_file.replace(self.log_file)


class MigrationProfiler:
    """Profiles individual migration operations."""
    
    def __init__(self) -> None:
        self.operation_times: Dict[str, List[float]] = {}
        self.current_operation: Optional[str] = None
        self.operation_start: Optional[float] = None
    
    def start_operation(self, operation_name: str) -> None:
        """Start profiling an operation."""
        self.current_operation = operation_name
        self.operation_start = time.time()
    
    def end_operation(self) -> None:
        """End profiling current operation."""
        if self.current_operation and self.operation_start:
            duration = time.time() - self.operation_start
            
            if self.current_operation not in self.operation_times:
                self.operation_times[self.current_operation] = []
            
            self.operation_times[self.current_operation].append(duration)
            
            self.current_operation = None
            self.operation_start = None
    
    def get_profile_report(self) -> str:
        """Get profiling report."""
        if not self.operation_times:
            return "No profiling data available."
        
        report = "Migration Profiling Report\n"
        report += "=" * 40 + "\n\n"
        
        total_time = sum(sum(times) for times in self.operation_times.values())
        
        for operation, times in sorted(self.operation_times.items()):
            avg_time = sum(times) / len(times)
            max_time = max(times)
            operation_total = sum(times)
            percentage = (operation_total / total_time) * 100
            
            report += f"{operation:<25} {avg_time:8.4f}s avg, {max_time:8.4f}s max, {percentage:5.1f}%\n"
        
        return report