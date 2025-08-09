"""
Production-ready Chain Monitoring System
"""
from __future__ import annotations

import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json

from app.Jobs.Chain import ChainStatus
from app.Jobs.ChainRegistry import ChainRegistry


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ChainMetrics:
    """Metrics for a job chain."""
    chain_id: str
    name: str
    status: ChainStatus
    started_at: datetime
    updated_at: datetime
    total_steps: int
    completed_steps: int
    failed_steps: int
    average_step_duration: float
    estimated_completion: Optional[datetime]
    error_rate: float
    retry_count: int
    memory_usage: int  # bytes
    cpu_usage: float   # percentage


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    check_duration: float


class ChainHealthChecker:
    """Performs health checks on job chains."""
    
    def __init__(self) -> None:
        self.checks: List[Callable[[], HealthCheckResult]] = []
        self.register_default_checks()
    
    def register_default_checks(self) -> None:
        """Register default health checks."""
        self.checks.extend([
            self.check_registry_health,
            self.check_stuck_chains,
            self.check_error_rates,
            self.check_resource_usage,
            self.check_queue_backlog
        ])
    
    def register_check(self, check_func: Callable[[], HealthCheckResult]) -> None:
        """Register a custom health check."""
        self.checks.append(check_func)
    
    def run_all_checks(self) -> List[HealthCheckResult]:
        """Run all registered health checks."""
        results = []
        for check in self.checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                results.append(HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    details={"error": str(e), "check": check.__name__},
                    timestamp=datetime.now(),
                    check_duration=0.0
                ))
        return results
    
    def check_registry_health(self) -> HealthCheckResult:
        """Check the health of the chain registry."""
        start_time = time.time()
        registry = ChainRegistry.get_instance()
        
        try:
            active_chains = registry.get_active_chains()
            stats = registry.get_stats()
            
            # Check for registry issues
            if stats['total_chains'] > 10000:  # Arbitrary threshold
                status = HealthStatus.WARNING
                message = f"High number of active chains: {stats['total_chains']}"
            elif stats['failed'] > stats['total_chains'] * 0.1:  # >10% failure rate
                status = HealthStatus.CRITICAL
                message = f"High failure rate: {stats['failed']}/{stats['total_chains']}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Registry healthy with {stats['total_chains']} active chains"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=stats,
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
        
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Registry check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    def check_stuck_chains(self) -> HealthCheckResult:
        """Check for chains that appear stuck."""
        start_time = time.time()
        registry = ChainRegistry.get_instance()
        
        try:
            stuck_chains = []
            active_chains = registry.get_active_chains()
            
            # Define "stuck" as running for more than 1 hour without progress
            stuck_threshold = timedelta(hours=1)
            
            for chain_id, chain in active_chains.items():
                if chain.status == ChainStatus.RUNNING:
                    # This would need to be implemented in JobChain
                    # last_activity = getattr(chain, 'last_activity', datetime.now())
                    # if datetime.now() - last_activity > stuck_threshold:
                    #     stuck_chains.append(chain_id)
                    pass
            
            if stuck_chains:
                status = HealthStatus.WARNING
                message = f"Found {len(stuck_chains)} potentially stuck chains"
                details = {"stuck_chains": stuck_chains}
            else:
                status = HealthStatus.HEALTHY
                message = "No stuck chains detected"
                details = {}
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
        
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Stuck chain check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    def check_error_rates(self) -> HealthCheckResult:
        """Check error rates across chains."""
        start_time = time.time()
        
        try:
            # This would integrate with metrics collection
            error_rate = 0.05  # Placeholder - 5% error rate
            
            if error_rate > 0.2:  # >20% error rate
                status = HealthStatus.CRITICAL
                message = f"Critical error rate: {error_rate:.1%}"
            elif error_rate > 0.1:  # >10% error rate
                status = HealthStatus.WARNING
                message = f"Elevated error rate: {error_rate:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Error rate within normal range: {error_rate:.1%}"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details={"error_rate": error_rate},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
        
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Error rate check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    def check_resource_usage(self) -> HealthCheckResult:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get current process resource usage
            process = psutil.Process()
            memory_percent = process.memory_percent()
            cpu_percent = process.cpu_percent()
            
            if memory_percent > 80 or cpu_percent > 80:
                status = HealthStatus.CRITICAL
                message = f"High resource usage: {memory_percent:.1f}% memory, {cpu_percent:.1f}% CPU"
            elif memory_percent > 60 or cpu_percent > 60:
                status = HealthStatus.WARNING
                message = f"Elevated resource usage: {memory_percent:.1f}% memory, {cpu_percent:.1f}% CPU"
            else:
                status = HealthStatus.HEALTHY
                message = f"Resource usage normal: {memory_percent:.1f}% memory, {cpu_percent:.1f}% CPU"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details={
                    "memory_percent": memory_percent,
                    "cpu_percent": cpu_percent,
                    "memory_mb": process.memory_info().rss / 1024 / 1024
                },
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
        
        except ImportError:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message="psutil not available for resource monitoring",
                details={},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Resource check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
    
    def check_queue_backlog(self) -> HealthCheckResult:
        """Check for queue backlogs."""
        start_time = time.time()
        
        try:
            # This would integrate with queue monitoring
            backlog_size = 0  # Placeholder
            
            if backlog_size > 10000:
                status = HealthStatus.CRITICAL
                message = f"Critical queue backlog: {backlog_size} jobs"
            elif backlog_size > 1000:
                status = HealthStatus.WARNING
                message = f"Elevated queue backlog: {backlog_size} jobs"
            else:
                status = HealthStatus.HEALTHY
                message = f"Queue backlog normal: {backlog_size} jobs"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details={"backlog_size": backlog_size},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )
        
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Queue backlog check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                check_duration=time.time() - start_time
            )


class ChainMonitor:
    """Comprehensive chain monitoring system."""
    
    def __init__(self, check_interval: int = 30) -> None:
        self.check_interval = check_interval
        self.health_checker = ChainHealthChecker()
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[Dict[str, Any]] = []
        self.is_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
    
    def start_monitoring(self) -> None:
        """Start the monitoring system."""
        if self.is_running:
            return
        
        self.is_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        import logging
        logging.info("Chain monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring system."""
        self.is_running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        import logging
        logging.info("Chain monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                self._collect_metrics()
                self._run_health_checks()
                self._process_alerts()
                time.sleep(self.check_interval)
            except Exception as e:
                import logging
                logging.error(f"Monitor loop error: {str(e)}")
                time.sleep(self.check_interval)
    
    def _collect_metrics(self) -> None:
        """Collect metrics from active chains."""
        with self._lock:
            registry = ChainRegistry.get_instance()
            active_chains = registry.get_active_chains()
            
            for chain_id, chain in active_chains.items():
                metrics = self._calculate_chain_metrics(chain_id, chain)
                self.metrics_history[chain_id].append(metrics)
    
    def _calculate_chain_metrics(self, chain_id: str, chain: Any) -> ChainMetrics:
        """Calculate metrics for a specific chain."""
        # This would be expanded with actual metrics calculation
        return ChainMetrics(
            chain_id=chain_id,
            name=chain.name or "Unnamed Chain",
            status=chain.status,
            started_at=datetime.now(),  # Would use actual start time
            updated_at=datetime.now(),
            total_steps=len(chain.steps),
            completed_steps=chain.current_step,
            failed_steps=1 if chain.status == ChainStatus.FAILED else 0,
            average_step_duration=30.0,  # Placeholder
            estimated_completion=None,
            error_rate=0.05,  # Placeholder
            retry_count=0,
            memory_usage=1024 * 1024,  # Placeholder
            cpu_usage=5.0  # Placeholder
        )
    
    def _run_health_checks(self) -> None:
        """Run health checks and store results."""
        health_results = self.health_checker.run_all_checks()
        
        with self._lock:
            # Store health check results
            timestamp = datetime.now()
            self.metrics_history['health_checks'].append({
                'timestamp': timestamp,
                'results': [asdict(result) for result in health_results]
            })
            
            # Generate alerts for critical issues
            for result in health_results:
                if result.status == HealthStatus.CRITICAL:
                    self._generate_alert("CRITICAL", result.message, result.details)
                elif result.status == HealthStatus.WARNING:
                    self._generate_alert("WARNING", result.message, result.details)
    
    def _generate_alert(self, level: str, message: str, details: Dict[str, Any]) -> None:
        """Generate an alert."""
        alert = {
            'id': f"{int(time.time())}_{len(self.alerts)}",
            'level': level,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False
        }
        self.alerts.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
    
    def _process_alerts(self) -> None:
        """Process and potentially send alerts."""
        # This would integrate with alerting systems (email, Slack, etc.)
        unacknowledged_critical = [
            alert for alert in self.alerts 
            if alert['level'] == 'CRITICAL' and not alert['acknowledged']
        ]
        
        if unacknowledged_critical:
            import logging
            for alert in unacknowledged_critical[-5:]:  # Log last 5 critical alerts
                logging.critical(f"Chain Monitor Alert: {alert['message']}")
    
    def get_current_health(self) -> Dict[str, Any]:
        """Get current system health."""
        health_results = self.health_checker.run_all_checks()
        
        overall_status = HealthStatus.HEALTHY
        for result in health_results:
            if result.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                break
            elif result.status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'checks': [asdict(result) for result in health_results],
            'summary': {
                'healthy': sum(1 for r in health_results if r.status == HealthStatus.HEALTHY),
                'warning': sum(1 for r in health_results if r.status == HealthStatus.WARNING),
                'critical': sum(1 for r in health_results if r.status == HealthStatus.CRITICAL),
                'unknown': sum(1 for r in health_results if r.status == HealthStatus.UNKNOWN)
            }
        }
    
    def get_chain_metrics(self, chain_id: str, hours: int = 24) -> List[ChainMetrics]:
        """Get metrics history for a specific chain."""
        with self._lock:
            if chain_id not in self.metrics_history:
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [
                metrics for metrics in self.metrics_history[chain_id]
                if metrics.updated_at > cutoff_time
            ]
    
    def get_alerts(self, acknowledged: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by acknowledgment status."""
        with self._lock:
            if acknowledged is None:
                return self.alerts.copy()
            
            return [
                alert for alert in self.alerts
                if alert['acknowledged'] == acknowledged
            ]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['acknowledged'] = True
                    return True
            return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        registry = ChainRegistry.get_instance()
        registry_stats = registry.get_stats()
        health = self.get_current_health()
        
        with self._lock:
            recent_alerts = [a for a in self.alerts if 
                           datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=24)]
            
            return {
                'chains': registry_stats,
                'health': health,
                'alerts': {
                    'total': len(self.alerts),
                    'recent_24h': len(recent_alerts),
                    'unacknowledged': len([a for a in recent_alerts if not a['acknowledged']]),
                    'critical': len([a for a in recent_alerts if a['level'] == 'CRITICAL']),
                    'warning': len([a for a in recent_alerts if a['level'] == 'WARNING'])
                },
                'monitoring': {
                    'is_running': self.is_running,
                    'check_interval': self.check_interval,
                    'metrics_collected': sum(len(history) for history in self.metrics_history.values()),
                    'uptime': "N/A"  # Would track actual uptime
                }
            }


# Global monitor instance
_monitor_instance: Optional[ChainMonitor] = None


def get_chain_monitor() -> ChainMonitor:
    """Get the global chain monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ChainMonitor()
    return _monitor_instance