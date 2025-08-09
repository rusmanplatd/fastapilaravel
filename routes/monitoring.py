"""
Enhanced Monitoring Dashboard Routes
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing_extensions import Annotated
from sqlalchemy.orm import Session

from app.Http.Controllers import get_current_user
from app.Http.Middleware import (
    get_middleware_stats, 
    health_checker,
    middleware_manager
)
from app.Routing import route_manager
from app.Auth import auth_manager
from app.Policies.Policy import gate
from app.Models.User import User
from config.database import get_database
from config.features import (
    get_config, 
    feature_enabled, 
    get_all_feature_flags,
    get_security_config
)
from app.Jobs.ChainMonitor import get_chain_monitor, HealthStatus
from app.Jobs.ChainRegistry import ChainRegistry
from app.Jobs.RetryManager import get_retry_manager
from app.Jobs.MetricsCollector import get_metrics_collector
from app.Jobs.ChainVisualizer import get_chain_visualizer, VisualizationType
from app.Jobs.JobPersistence import get_persistence_manager, PersistenceConfig

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@router.get("/dashboard")
async def monitoring_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    """
    Enhanced monitoring dashboard with comprehensive system metrics.
    Only accessible by admin users.
    """
    # Check authorization
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    return {
        "success": True,
        "message": "Monitoring dashboard data",
        "data": {
            "system_overview": {
                "environment": "development",  # Would come from settings
                "features_enabled": sum(1 for enabled in get_all_feature_flags().values() if enabled),
                "total_features": len(get_all_feature_flags()),
                "uptime": "N/A",  # Would calculate actual uptime
                "version": "1.0.0"
            },
            "middleware_stats": get_middleware_stats(),
            "route_stats": route_manager.route_metrics.get_all_stats(),
            "feature_flags": get_all_feature_flags(),
            "auth_stats": {
                "default_guard": auth_manager.get_default_guard(),
                "registered_guards": len(auth_manager._guards),
                "active_sessions": 0  # Would track actual sessions
            }
        }
    }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    """
    middleware_health = health_checker.check_middleware_health()
    
    # Check database health
    db_healthy = True  # Would implement actual DB health check
    
    # Check external services
    external_services = {
        "redis": "healthy",     # Would check actual Redis connection
        "database": "healthy" if db_healthy else "unhealthy",
        "email": "healthy"      # Would check email service
    }
    
    overall_status = "healthy"
    issues = []
    
    # Determine overall status
    if middleware_health["overall_status"] != "healthy":
        overall_status = "degraded"
        issues.extend(middleware_health["issues"])
    
    if not db_healthy:
        overall_status = "unhealthy"
        issues.append("Database connection failed")
    
    return {
        "status": overall_status,
        "timestamp": "2025-08-10T12:00:00Z",  # Would use actual timestamp
        "checks": {
            "middleware": middleware_health,
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "response_time_ms": 5  # Would measure actual response time
            },
            "external_services": external_services
        },
        "issues": issues,
        "recommendations": middleware_health.get("recommendations", [])
    }

@router.get("/metrics")
async def system_metrics(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    System performance metrics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    route_metrics = route_manager.route_metrics.get_all_stats()
    top_routes = route_manager.route_metrics.get_top_routes("access_count", 10)
    slow_routes = route_manager.route_metrics.get_top_routes("avg_response_time", 5)
    
    return {
        "success": True,
        "data": {
            "performance": {
                "total_routes": len(route_manager.routes),
                "total_requests": sum(stats.get("access_count", 0) for stats in route_metrics.values()),
                "avg_response_time": sum(stats.get("avg_response_time", 0) for stats in route_metrics.values()) / max(len(route_metrics), 1),
                "slow_requests": sum(1 for stats in route_metrics.values() if stats.get("avg_response_time", 0) > 1.0)
            },
            "routes": {
                "total": len(route_manager.routes),
                "top_accessed": top_routes,
                "slowest": slow_routes,
                "metrics": route_metrics
            },
            "middleware": get_middleware_stats(),
            "memory": {
                "usage_mb": 0,      # Would get actual memory usage
                "peak_usage_mb": 0  # Would track peak usage
            },
            "errors": {
                "total_errors": 0,  # Would track actual errors
                "error_rate": 0.0   # Would calculate actual error rate
            }
        }
    }

@router.get("/routes")
async def route_analysis(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Detailed route analysis and validation.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    route_map = route_manager.generate_route_map()
    route_issues = route_manager.validate_routes()
    
    # Categorize issues by severity
    critical_issues = [issue for issue in route_issues if issue.get('severity') == 'critical']
    warnings = [issue for issue in route_issues if issue.get('severity') == 'warning']
    info_items = [issue for issue in route_issues if issue.get('severity') == 'info']
    
    return {
        "success": True,
        "data": {
            "summary": {
                "total_routes": len(route_manager.routes),
                "auth_required_routes": len(route_manager.get_routes_requiring_auth()),
                "deprecated_routes": len(route_manager.get_deprecated_routes()),
                "critical_issues": len(critical_issues),
                "warnings": len(warnings),
                "info_items": len(info_items)
            },
            "routes": route_map["routes"],
            "middleware_groups": route_map["middleware_groups"],
            "issues": {
                "critical": critical_issues,
                "warnings": warnings,
                "info": info_items
            },
            "performance": route_map.get("metrics", {})
        }
    }

@router.get("/security")
async def security_overview(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Security configuration and status overview.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    security_config = get_security_config()
    
    return {
        "success": True,
        "data": {
            "authentication": {
                "mfa_enabled": feature_enabled("mfa_enforcement"),
                "impersonation_allowed": feature_enabled("impersonation"),
                "rate_limiting": feature_enabled("rate_limiting"),
                "default_guard": auth_manager.get_default_guard()
            },
            "password_policy": security_config["password_policy"],
            "session_security": security_config["session_security"],
            "rate_limiting": security_config["rate_limiting"],
            "security_headers": {
                "cors_enabled": True,
                "csrf_protection": True,
                "content_security_policy": True
            },
            "recent_security_events": [
                # Would fetch actual security events from logs
                {
                    "type": "failed_login",
                    "count": 0,
                    "last_occurrence": None
                },
                {
                    "type": "successful_login", 
                    "count": 0,
                    "last_occurrence": None
                }
            ]
        }
    }

@router.get("/features")
async def feature_status(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Feature flags and configuration status.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    config = get_config("development")  # Would detect actual environment
    
    return {
        "success": True,
        "data": {
            "feature_flags": get_all_feature_flags(),
            "configuration": {
                "middleware": {
                    "enabled": feature_enabled("enhanced_middleware"),
                    "manager_enabled": config["middleware"]["manager_enabled"],
                    "development_mode": config["middleware"]["development_mode"]
                },
                "routing": {
                    "auto_discovery": config["routing"].auto_discovery,
                    "route_caching": config["routing"].route_caching,
                    "metrics_tracking": config["routing"].metrics_tracking
                },
                "policies": {
                    "cache_enabled": config["policies"].cache_enabled,
                    "track_usage": config["policies"].track_usage,
                    "rate_limiting": config["policies"].rate_limiting
                },
                "monitoring": {
                    "performance_tracking": config["monitoring"].performance_tracking,
                    "dashboard_enabled": config["monitoring"].dashboard_enabled
                }
            }
        }
    }

@router.post("/features/{feature_name}/toggle")
async def toggle_feature(
    feature_name: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Toggle a feature flag (admin only).
    """
    if not current_user.has_role('super_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required."
        )
    
    from config.features import set_feature_flag, FEATURE_FLAGS
    
    if feature_name not in FEATURE_FLAGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{feature_name}' not found"
        )
    
    current_status = FEATURE_FLAGS[feature_name]
    new_status = not current_status
    set_feature_flag(feature_name, new_status)
    
    return {
        "success": True,
        "message": f"Feature '{feature_name}' {'enabled' if new_status else 'disabled'}",
        "data": {
            "feature": feature_name,
            "previous_status": current_status,
            "new_status": new_status
        }
    }

@router.get("/logs")
async def system_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    level: str = "info",
    limit: int = 100
) -> Dict[str, Any]:
    """
    Recent system logs (placeholder - would integrate with actual logging).
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    # Placeholder log entries - would integrate with actual logging system
    logs = [
        {
            "timestamp": "2025-08-10T12:00:00Z",
            "level": "INFO",
            "module": "app.Http.Middleware.PerformanceMiddleware",
            "message": "Request processed in 0.15s",
            "metadata": {"path": "/api/v1/users", "method": "GET", "status": 200}
        },
        {
            "timestamp": "2025-08-10T11:59:30Z", 
            "level": "WARN",
            "module": "app.Policies.UserPolicy",
            "message": "Policy cache size exceeded threshold",
            "metadata": {"cache_size": 1050, "threshold": 1000}
        }
    ]
    
    return {
        "success": True,
        "data": {
            "logs": logs[:limit],
            "total": len(logs),
            "level": level,
            "available_levels": ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]
        }
    }


@router.get("/chains/health")
async def chain_health_check() -> Dict[str, Any]:
    """
    Job chain health check endpoint.
    
    Returns:
        dict: Chain system health information
    """
    monitor = get_chain_monitor()
    health_data = monitor.get_current_health()
    
    status_map = {
        HealthStatus.HEALTHY.value: "healthy",
        HealthStatus.WARNING.value: "warning", 
        HealthStatus.CRITICAL.value: "unhealthy",
        HealthStatus.UNKNOWN.value: "unknown"
    }
    
    return {
        "status": status_map.get(health_data["overall_status"], "unknown"),
        "timestamp": health_data["timestamp"],
        "checks": health_data["checks"],
        "summary": health_data["summary"]
    }


@router.get("/chains/stats")
async def get_chain_statistics(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get comprehensive job chain statistics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    registry = ChainRegistry.get_instance()
    monitor = get_chain_monitor()
    
    chain_stats = registry.get_stats()
    system_stats = monitor.get_system_stats()
    
    return {
        "success": True,
        "data": {
            "chains": chain_stats,
            "monitoring": {
                "is_running": monitor.is_running,
                "check_interval": monitor.check_interval,
                "total_alerts": len(monitor.get_alerts())
            },
            "alerts": {
                "total": len(monitor.get_alerts()),
                "unacknowledged": len(monitor.get_alerts(acknowledged=False)),
                "critical": len([a for a in monitor.get_alerts() if a['level'] == 'CRITICAL']),
                "warning": len([a for a in monitor.get_alerts() if a['level'] == 'WARNING'])
            }
        }
    }


@router.get("/chains/{chain_id}/metrics")
async def get_chain_metrics(
    chain_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    hours: int = 24
) -> Dict[str, Any]:
    """
    Get metrics for a specific job chain.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    monitor = get_chain_monitor()
    metrics = monitor.get_chain_metrics(chain_id, hours)
    
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metrics found for chain {chain_id}"
        )
    
    # Convert dataclass to dict for JSON serialization
    metrics_data = []
    for m in metrics:
        metrics_data.append({
            "chain_id": m.chain_id,
            "name": m.name,
            "status": m.status.value,
            "started_at": m.started_at.isoformat(),
            "updated_at": m.updated_at.isoformat(),
            "total_steps": m.total_steps,
            "completed_steps": m.completed_steps,
            "failed_steps": m.failed_steps,
            "average_step_duration": m.average_step_duration,
            "estimated_completion": m.estimated_completion.isoformat() if m.estimated_completion else None,
            "error_rate": m.error_rate,
            "retry_count": m.retry_count,
            "memory_usage": m.memory_usage,
            "cpu_usage": m.cpu_usage
        })
    
    return {
        "success": True,
        "data": {
            "chain_id": chain_id,
            "metrics": metrics_data,
            "period_hours": hours
        }
    }


@router.get("/chains/alerts")
async def get_chain_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    acknowledged: bool = False,
    level: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get job chain alerts.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    monitor = get_chain_monitor()
    alerts = monitor.get_alerts(acknowledged=acknowledged)
    
    # Filter by level if specified
    if level:
        alerts = [alert for alert in alerts if alert['level'] == level]
    
    # Apply limit
    alerts = alerts[-limit:]
    
    return {
        "success": True,
        "data": {
            "alerts": alerts,
            "total": len(alerts),
            "filters": {
                "acknowledged": acknowledged,
                "level": level,
                "limit": limit
            }
        }
    }


@router.post("/chains/alerts/{alert_id}/acknowledge")
async def acknowledge_chain_alert(
    alert_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Acknowledge a chain alert.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    monitor = get_chain_monitor()
    success = monitor.acknowledge_alert(alert_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    return {
        "success": True,
        "message": f"Alert {alert_id} acknowledged successfully",
        "data": {
            "alert_id": alert_id,
            "acknowledged_by": current_user.id,
            "acknowledged_at": "2025-08-15T12:00:00Z"  # Would use actual timestamp
        }
    }


@router.get("/chains/active")
async def get_active_chains(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get information about currently active job chains.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    registry = ChainRegistry.get_instance()
    active_chains = registry.get_active_chains()
    
    chains_info = []
    for chain_id, chain in active_chains.items():
        chains_info.append({
            "chain_id": chain_id,
            "name": chain.name,
            "status": chain.status.value,
            "total_steps": len(chain.steps),
            "current_step": chain.current_step,
            "progress_percent": (chain.current_step / len(chain.steps) * 100) if chain.steps else 0
        })
    
    return {
        "success": True,
        "data": {
            "total_active": len(active_chains),
            "chains": chains_info,
            "summary": registry.get_stats()
        }
    }


@router.post("/chains/monitoring/start")
async def start_chain_monitoring(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Start the chain monitoring system.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    monitor = get_chain_monitor()
    
    if monitor.is_running:
        return {
            "success": True,
            "message": "Chain monitoring is already running",
            "data": {"status": "already_running"}
        }
    
    monitor.start_monitoring()
    
    return {
        "success": True,
        "message": "Chain monitoring started successfully",
        "data": {
            "status": "started",
            "check_interval": monitor.check_interval,
            "started_by": current_user.id
        }
    }


@router.post("/chains/monitoring/stop")
async def stop_chain_monitoring(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Stop the chain monitoring system.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    monitor = get_chain_monitor()
    
    if not monitor.is_running:
        return {
            "success": True,
            "message": "Chain monitoring is not running",
            "data": {"status": "not_running"}
        }
    
    monitor.stop_monitoring()
    
    return {
        "success": True,
        "message": "Chain monitoring stopped successfully",
        "data": {
            "status": "stopped",
            "stopped_by": current_user.id
        }
    }


@router.get("/retry/stats")
async def get_retry_statistics(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get job retry statistics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    retry_manager = get_retry_manager()
    stats = retry_manager.get_stats()
    
    return {
        "success": True,
        "data": {
            "retry_stats": stats,
            "timestamp": "2025-08-15T12:00:00Z"  # Would use actual timestamp
        }
    }


@router.get("/retry/jobs")
async def get_retry_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    exhausted_only: bool = False
) -> Dict[str, Any]:
    """
    Get information about jobs with retry attempts.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    retry_manager = get_retry_manager()
    all_retry_info = retry_manager.get_all_retry_info()
    
    # Filter if requested
    if exhausted_only:
        retry_info = {k: v for k, v in all_retry_info.items() if v.is_exhausted}
    else:
        retry_info = all_retry_info
    
    # Convert to serializable format
    jobs_data = []
    for job_id, info in retry_info.items():
        jobs_data.append({
            "job_id": job_id,
            "max_retries": info.max_retries,
            "current_attempt": info.current_attempt,
            "is_exhausted": info.is_exhausted,
            "created_at": info.created_at.isoformat(),
            "next_retry_at": info.next_retry_at.isoformat() if info.next_retry_at else None,
            "last_error": str(info.last_error) if info.last_error else None,
            "attempts_count": len(info.attempts),
            "backoff_strategy": info.backoff_config.strategy.value
        })
    
    return {
        "success": True,
        "data": {
            "jobs": jobs_data,
            "total": len(jobs_data),
            "filters": {
                "exhausted_only": exhausted_only
            }
        }
    }


@router.get("/retry/jobs/{job_id}")
async def get_retry_job_details(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get detailed retry information for a specific job.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    retry_manager = get_retry_manager()
    retry_info = retry_manager.get_retry_info(job_id)
    
    if not retry_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No retry information found for job {job_id}"
        )
    
    # Convert attempts to serializable format
    attempts_data = []
    for attempt in retry_info.attempts:
        attempts_data.append({
            "attempt_number": attempt.attempt_number,
            "timestamp": attempt.timestamp.isoformat(),
            "delay_seconds": attempt.delay_seconds,
            "error_message": attempt.error_message,
            "error_type": attempt.error_type,
            "metadata": attempt.metadata
        })
    
    return {
        "success": True,
        "data": {
            "job_id": job_id,
            "max_retries": retry_info.max_retries,
            "current_attempt": retry_info.current_attempt,
            "is_exhausted": retry_info.is_exhausted,
            "created_at": retry_info.created_at.isoformat(),
            "next_retry_at": retry_info.next_retry_at.isoformat() if retry_info.next_retry_at else None,
            "last_error": str(retry_info.last_error) if retry_info.last_error else None,
            "backoff_config": {
                "strategy": retry_info.backoff_config.strategy.value,
                "base_delay": retry_info.backoff_config.base_delay,
                "max_delay": retry_info.backoff_config.max_delay,
                "multiplier": retry_info.backoff_config.multiplier,
                "jitter": retry_info.backoff_config.jitter
            },
            "attempts": attempts_data
        }
    }


@router.delete("/retry/jobs/{job_id}")
async def clear_retry_record(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Clear retry record for a specific job.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    retry_manager = get_retry_manager()
    success = retry_manager.clear_retry_record(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No retry record found for job {job_id}"
        )
    
    return {
        "success": True,
        "message": f"Retry record cleared for job {job_id}",
        "data": {
            "job_id": job_id,
            "cleared_by": current_user.id
        }
    }


@router.get("/metrics/jobs")
async def get_job_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    hours: int = 24,
    queue_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive job execution metrics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    
    if queue_name:
        metrics_data = metrics_collector.get_queue_metrics(queue_name, hours)
    else:
        metrics_data = metrics_collector.get_overall_metrics(hours)
    
    return {
        "success": True,
        "data": {
            "metrics": metrics_data,
            "period_hours": hours,
            "queue_filter": queue_name,
            "collector_stats": metrics_collector.get_stats()
        }
    }


@router.get("/metrics/counters")
async def get_metric_counters(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get current counter metrics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    counters = metrics_collector.get_current_counters()
    
    return {
        "success": True,
        "data": {
            "counters": counters,
            "timestamp": "2025-08-15T12:00:00Z"  # Would use actual timestamp
        }
    }


@router.get("/metrics/gauges")
async def get_metric_gauges(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get current gauge metrics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    gauges = metrics_collector.get_current_gauges()
    
    return {
        "success": True,
        "data": {
            "gauges": gauges,
            "timestamp": "2025-08-15T12:00:00Z"  # Would use actual timestamp
        }
    }


@router.get("/metrics/histograms/{histogram_name}")
async def get_histogram_stats(
    histogram_name: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get statistics for a specific histogram.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    stats = metrics_collector.get_histogram_stats(histogram_name)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Histogram {histogram_name} not found or has no data"
        )
    
    return {
        "success": True,
        "data": {
            "histogram_name": histogram_name,
            "statistics": stats,
            "timestamp": "2025-08-15T12:00:00Z"  # Would use actual timestamp
        }
    }


@router.get("/metrics/jobs/{job_id}")
async def get_job_specific_metrics(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get metrics for a specific job.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    job_metrics = metrics_collector.get_job_metrics(job_id)
    
    if not job_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metrics found for job {job_id}"
        )
    
    # Convert to serializable format
    metrics_data = {
        "job_id": job_metrics.job_id,
        "job_type": job_metrics.job_type,
        "queue_name": job_metrics.queue_name,
        "queued_at": job_metrics.queued_at.isoformat(),
        "started_at": job_metrics.started_at.isoformat() if job_metrics.started_at else None,
        "completed_at": job_metrics.completed_at.isoformat() if job_metrics.completed_at else None,
        "processing_duration": job_metrics.processing_duration,
        "total_duration": job_metrics.total_duration,
        "queue_wait_time": job_metrics.queue_wait_time,
        "phase": job_metrics.phase.value,
        "success": job_metrics.success,
        "retry_count": job_metrics.retry_count,
        "error_message": job_metrics.error_message,
        "error_type": job_metrics.error_type,
        "peak_memory_mb": job_metrics.peak_memory_mb,
        "cpu_usage_percent": job_metrics.cpu_usage_percent,
        "io_operations": job_metrics.io_operations,
        "records_processed": job_metrics.records_processed,
        "bytes_processed": job_metrics.bytes_processed,
        "custom_metrics": job_metrics.custom_metrics,
        "tags": job_metrics.tags,
        "metadata": job_metrics.metadata
    }
    
    return {
        "success": True,
        "data": {
            "job_metrics": metrics_data
        }
    }


# Job Chain Visualization Endpoints

@router.get("/visualization/chains")
async def list_visualizable_chains(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get list of chains available for visualization.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    registry = ChainRegistry.get_instance()
    active_chains = registry.get_active_chains()
    
    chains_info = []
    for chain_id, chain in active_chains.items():
        chains_info.append({
            "chain_id": chain_id,
            "name": chain.name,
            "status": chain.status.value,
            "total_steps": len(chain.steps),
            "current_step": chain.current_step,
            "visualization_types": [vtype.value for vtype in VisualizationType]
        })
    
    return {
        "success": True,
        "data": {
            "chains": chains_info,
            "total_chains": len(chains_info)
        }
    }


@router.get("/visualization/chains/{chain_id}")
async def visualize_chain(
    chain_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    viz_type: str = "flow_diagram",
    export_format: str = "json"
) -> Union[Dict[str, Any], Any]:
    """
    Create and export a visualization for a job chain.
    
    Args:
        chain_id: ID of the chain to visualize
        viz_type: Type of visualization (flow_diagram, timeline, execution_trace, performance_heatmap)
        export_format: Export format (json, mermaid, html)
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    # Validate visualization type
    try:
        visualization_type = VisualizationType(viz_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid visualization type. Must be one of: {[vt.value for vt in VisualizationType]}"
        )
    
    visualizer = get_chain_visualizer()
    viz_data = visualizer.visualize_chain(chain_id, visualization_type)
    
    if not viz_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain {chain_id} not found"
        )
    
    # Export in requested format
    try:
        exported_data = visualizer.export_visualization(viz_data, export_format)
        
        if export_format.lower() == "html":
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=exported_data)
        elif export_format.lower() == "mermaid":
            return {
                "success": True,
                "data": {
                    "chain_id": chain_id,
                    "visualization_type": viz_type,
                    "format": export_format,
                    "diagram": exported_data,
                    "metadata": viz_data.metadata
                }
            }
        else:  # JSON format
            return {
                "success": True,
                "data": {
                    "chain_id": chain_id,
                    "visualization_type": viz_type,
                    "format": export_format,
                    "visualization": viz_data.to_dict() if export_format == "json" else exported_data
                }
            }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/visualization/chains/{chain_id}/debug")
async def get_chain_debug_info(
    chain_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get comprehensive debugging information for a chain.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    visualizer = get_chain_visualizer()
    debug_info = visualizer.get_chain_debug_info(chain_id)
    
    if "error" in debug_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=debug_info["error"]
        )
    
    return {
        "success": True,
        "data": {
            "chain_id": chain_id,
            "debug_info": debug_info
        }
    }


@router.get("/visualization/cache")
async def list_cached_visualizations(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    List all cached visualizations.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    visualizer = get_chain_visualizer()
    cached_viz_ids = visualizer.get_cached_visualizations()
    
    cached_visualizations = []
    for viz_id in cached_viz_ids:
        viz_data = visualizer.get_visualization(viz_id)
        if viz_data:
            cached_visualizations.append({
                "id": viz_id,
                "title": viz_data.title,
                "type": viz_data.type.value,
                "chain_id": viz_data.metadata.get("chain_id"),
                "timestamp": viz_data.timestamp.isoformat()
            })
    
    return {
        "success": True,
        "data": {
            "cached_visualizations": cached_visualizations,
            "total_cached": len(cached_visualizations)
        }
    }


@router.get("/visualization/cache/{viz_id}")
async def get_cached_visualization(
    viz_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    export_format: str = "json"
) -> Union[Dict[str, Any], Any]:
    """
    Get a specific cached visualization.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    visualizer = get_chain_visualizer()
    viz_data = visualizer.get_visualization(viz_id)
    
    if not viz_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visualization {viz_id} not found in cache"
        )
    
    # Export in requested format
    try:
        exported_data = visualizer.export_visualization(viz_data, export_format)
        
        if export_format.lower() == "html":
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=exported_data)
        else:
            return {
                "success": True,
                "data": {
                    "visualization_id": viz_id,
                    "format": export_format,
                    "visualization": viz_data.to_dict() if export_format == "json" else exported_data
                }
            }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/visualization/cache")
async def clear_visualization_cache(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Clear all cached visualizations.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    visualizer = get_chain_visualizer()
    cleared_count = visualizer.clear_cache()
    
    return {
        "success": True,
        "data": {
            "cleared_count": cleared_count,
            "message": f"Cleared {cleared_count} cached visualizations"
        }
    }


@router.get("/visualization/performance/{chain_id}")
async def get_chain_performance_analysis(
    chain_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get detailed performance analysis for a chain.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    registry = ChainRegistry.get_instance()
    chain = registry.get_chain(chain_id)
    
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain {chain_id} not found"
        )
    
    visualizer = get_chain_visualizer()
    performance_analysis = visualizer._analyze_chain_performance(chain)
    
    return {
        "success": True,
        "data": {
            "chain_id": chain_id,
            "performance_analysis": performance_analysis
        }
    }


# Job Persistence and Recovery Endpoints

@router.get("/persistence/stats")
async def get_persistence_stats(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get job persistence system statistics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    persistence_manager = get_persistence_manager()
    stats = persistence_manager.get_persistence_stats()
    
    return {
        "success": True,
        "data": stats
    }


@router.get("/persistence/failed-jobs")
async def get_failed_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 100,
    queue_name: Optional[str] = None,
    job_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get failed jobs that can be recovered.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    persistence_manager = get_persistence_manager()
    failed_jobs = persistence_manager.get_failed_jobs(
        limit=limit,
        queue_name=queue_name,
        job_type=job_type
    )
    
    jobs_data = []
    for job in failed_jobs:
        jobs_data.append({
            "id": job.id,
            "job_id": job.job_id,
            "job_type": job.job_type,
            "queue_name": job.queue_name,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "created_at": job.created_at.isoformat() if hasattr(job.created_at, 'isoformat') else str(job.created_at),
            "failed_at": job.failed_at.isoformat() if job.failed_at and hasattr(job.failed_at, 'isoformat') else str(job.failed_at) if job.failed_at else None,
            "error_message": job.error_message,
            "error_type": job.error_type,
            "recovery_attempts": job.recovery_attempts,
            "last_recovery_at": job.last_recovery_at.isoformat() if job.last_recovery_at and hasattr(job.last_recovery_at, 'isoformat') else str(job.last_recovery_at) if job.last_recovery_at else None,
            "chain_id": job.chain_id,
            "chain_step": job.chain_step
        })
    
    return {
        "success": True,
        "data": {
            "failed_jobs": jobs_data,
            "total_count": len(jobs_data),
            "filters": {
                "limit": limit,
                "queue_name": queue_name,
                "job_type": job_type
            }
        }
    }


@router.get("/persistence/recoverable-jobs")
async def get_recoverable_jobs(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Get jobs that are eligible for recovery.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    persistence_manager = get_persistence_manager()
    recoverable_jobs = persistence_manager.get_recoverable_jobs()
    
    jobs_data = []
    for job in recoverable_jobs:
        jobs_data.append({
            "id": job.id,
            "job_id": job.job_id,
            "job_type": job.job_type,
            "queue_name": job.queue_name,
            "failed_at": job.failed_at.isoformat() if job.failed_at and hasattr(job.failed_at, 'isoformat') else str(job.failed_at) if job.failed_at else None,
            "recovery_attempts": job.recovery_attempts,
            "max_recovery_attempts": 3,  # From config
            "error_type": job.error_type,
            "chain_id": job.chain_id
        })
    
    return {
        "success": True,
        "data": {
            "recoverable_jobs": jobs_data,
            "total_count": len(jobs_data)
        }
    }


@router.post("/persistence/recover/{job_id}")
async def recover_single_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Recover a specific failed job.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    persistence_manager = get_persistence_manager()
    success = persistence_manager.recover_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to recover job {job_id}. Check logs for details."
        )
    
    return {
        "success": True,
        "data": {
            "job_id": job_id,
            "message": f"Job {job_id} queued for recovery",
            "recovered_by": current_user.id
        }
    }


@router.post("/persistence/recover-batch")
async def recover_failed_jobs_batch(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 10,
    queue_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recover multiple failed jobs in batch.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    persistence_manager = get_persistence_manager()
    results = persistence_manager.recover_failed_jobs(
        limit=limit,
        queue_name=queue_name
    )
    
    return {
        "success": True,
        "data": {
            "recovery_results": results,
            "initiated_by": current_user.id
        }
    }


@router.delete("/persistence/cleanup")
async def cleanup_old_persistence_records(
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = 30
) -> Dict[str, Any]:
    """
    Clean up old persistence records.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    persistence_manager = get_persistence_manager()
    deleted_count = persistence_manager.cleanup_old_records(days=days)
    
    return {
        "success": True,
        "data": {
            "deleted_records": deleted_count,
            "retention_days": days,
            "cleaned_by": current_user.id
        }
    }


@router.get("/metrics/performance")
async def get_performance_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    hours: int = 24
) -> Dict[str, Any]:
    """
    Get performance-focused metrics summary.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    overall_metrics = metrics_collector.get_overall_metrics(hours)
    
    # Get specific performance histograms
    processing_time_stats = metrics_collector.get_histogram_stats("jobs.processing_duration.default")
    queue_wait_stats = metrics_collector.get_histogram_stats("jobs.queue_wait_time.default")
    
    return {
        "success": True,
        "data": {
            "period_hours": hours,
            "throughput": {
                "jobs_per_second": overall_metrics.get("jobs_per_second", 0),
                "jobs_per_minute": overall_metrics.get("jobs_per_minute", 0),
                "total_jobs": overall_metrics.get("job_count", 0)
            },
            "latency": {
                "avg_processing_time": overall_metrics.get("avg_processing_duration", 0),
                "p95_processing_time": overall_metrics.get("p95_processing_duration", 0),
                "p99_processing_time": overall_metrics.get("p99_processing_duration", 0),
                "avg_queue_wait": overall_metrics.get("avg_queue_wait_time", 0),
                "p95_queue_wait": overall_metrics.get("p95_queue_wait_time", 0)
            },
            "reliability": {
                "success_rate": overall_metrics.get("success_rate", 0),
                "error_rate": overall_metrics.get("error_rate", 0),
                "retry_rate": overall_metrics.get("retry_rate", 0)
            },
            "resource_usage": {
                "avg_memory_mb": overall_metrics.get("avg_memory_usage", 0),
                "peak_memory_mb": overall_metrics.get("peak_memory_usage", 0),
                "avg_cpu_percent": overall_metrics.get("avg_cpu_usage", 0)
            },
            "histogram_details": {
                "processing_time": processing_time_stats,
                "queue_wait_time": queue_wait_stats
            }
        }
    }


@router.delete("/metrics/cleanup")
async def cleanup_old_metrics(
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    Manually trigger cleanup of old metrics.
    """
    if not current_user.has_role('admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    metrics_collector = get_metrics_collector()
    cleaned_count = metrics_collector.cleanup_old_metrics()
    
    return {
        "success": True,
        "message": f"Cleaned up {cleaned_count} old metric records",
        "data": {
            "cleaned_records": cleaned_count,
            "triggered_by": current_user.id
        }
    }


# Register routes with the enhanced route manager
def register_monitoring_routes() -> None:
    """Register monitoring routes with the route manager."""
    route_manager.register_route(
        name="monitoring.dashboard",
        path="/monitoring/dashboard",
        method="GET",
        handler=monitoring_dashboard,
        tags=["monitoring", "admin"],
        auth_required=True,
        permissions=["admin"],
        cache_ttl=60
    )
    
    route_manager.register_route(
        name="monitoring.health",
        path="/monitoring/health", 
        method="GET",
        handler=health_check,
        tags=["monitoring", "health"],
        auth_required=False,
        cache_ttl=30
    )
    
    route_manager.register_route(
        name="monitoring.metrics",
        path="/monitoring/metrics",
        method="GET",
        handler=system_metrics,
        tags=["monitoring", "admin"],
        auth_required=True,
        permissions=["admin"]
    )

# Register the routes
register_monitoring_routes()