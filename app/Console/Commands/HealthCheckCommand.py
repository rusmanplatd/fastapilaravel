from __future__ import annotations

import asyncio
import time
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from ..Command import Command


class HealthCheckCommand(Command):
    """Perform comprehensive system health checks."""
    
    signature = "health:check {--component=* : Specific components to check} {--timeout=30 : Timeout for each check in seconds} {--export= : Export results to file} {--fix : Attempt to fix detected issues} {--monitoring : Enable continuous monitoring mode}"
    description = "Perform comprehensive system health checks"
    help = "Check system health including dependencies, services, resources, and configuration"
    
    def __init__(self) -> None:
        super().__init__()
        self.health_results: Dict[str, Dict[str, Any]] = {}
        self.failed_checks: List[str] = []
        self.warnings: List[str] = []
    
    async def handle(self) -> None:
        """Execute health checks."""
        components = self.option("component", [])
        timeout = int(self.option("timeout", 30))
        export_file = self.option("export")
        fix_issues = self.option("fix", False)
        monitoring_mode = self.option("monitoring", False)
        
        if monitoring_mode:
            await self._run_continuous_monitoring(timeout)
        else:
            await self._run_single_health_check(components, timeout, fix_issues, export_file)
    
    async def _run_single_health_check(
        self, 
        components: List[str], 
        timeout: int, 
        fix_issues: bool, 
        export_file: Optional[str]
    ) -> None:
        """Run a single comprehensive health check."""
        self.info("🏥 Starting comprehensive health check...")
        
        # Define all available health checks
        all_checks = {
            'system': self._check_system_resources,
            'database': self._check_database_connectivity,
            'cache': self._check_cache_connectivity,
            'storage': self._check_storage_health,
            'dependencies': self._check_python_dependencies,
            'configuration': self._check_configuration_health,
            'services': self._check_external_services,
            'security': self._check_security_status,
            'performance': self._check_performance_metrics,
            'logs': self._check_log_health,
        }
        
        # Filter checks if specific components requested
        if components:
            checks_to_run = {k: v for k, v in all_checks.items() if k in components}
            if not checks_to_run:
                self.error(f"No valid components specified. Available: {', '.join(all_checks.keys())}")
                return
        else:
            checks_to_run = all_checks
        
        self.info(f"Running {len(checks_to_run)} health checks...")
        
        # Run health checks
        progress_bar = self.progress_bar(len(checks_to_run), "Health checks")
        
        for component, check_func in checks_to_run.items():
            progress_bar.set_description(f"Checking {component}")
            
            try:
                result = await asyncio.wait_for(check_func(), timeout=timeout)
                self.health_results[component] = result
                
                if not result['healthy']:
                    self.failed_checks.append(component)
                
                if result.get('warnings'):
                    self.warnings.extend(result['warnings'])
                    
            except asyncio.TimeoutError:
                self.health_results[component] = {
                    'healthy': False,
                    'status': 'timeout',
                    'message': f'Health check timed out after {timeout}s',
                    'timestamp': datetime.now().isoformat()
                }
                self.failed_checks.append(component)
                
            except Exception as e:
                self.health_results[component] = {
                    'healthy': False,
                    'status': 'error',
                    'message': f'Health check failed: {e}',
                    'timestamp': datetime.now().isoformat()
                }
                self.failed_checks.append(component)
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        # Display results
        self._display_health_results()
        
        # Attempt fixes if requested
        if fix_issues and self.failed_checks:
            await self._attempt_fixes()
        
        # Export results if requested
        if export_file:
            await self._export_health_results(export_file)
        
        # Show overall status
        self._show_overall_health_status()
    
    async def _run_continuous_monitoring(self, check_interval: int) -> None:
        """Run continuous health monitoring."""
        self.info(f"🔄 Starting continuous health monitoring (interval: {check_interval}s)")
        self.comment("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                await self._run_single_health_check([], check_interval, False, None)
                
                # Wait for next check
                self.new_line()
                self.comment(f"Next check in {check_interval} seconds...")
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            self.info("🛑 Monitoring stopped by user")
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource utilization."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = getattr(psutil, 'cpu_count', lambda: 1)() or 1
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / 1024 / 1024  # MB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free = disk.free / 1024 / 1024 / 1024  # GB
            
            # Load average (Unix only)
            try:
                load_avg = getattr(psutil, 'getloadavg', lambda: (None, None, None))()
                load_1min, load_5min, load_15min = load_avg
            except AttributeError:
                load_1min = load_5min = load_15min = None
            
            # Determine health status
            issues: List[str] = []
            warnings: List[str] = []
            
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > 75:
                warnings.append(f"Elevated CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > 95:
                issues.append(f"Critical memory usage: {memory_percent:.1f}%")
            elif memory_percent > 85:
                warnings.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > 95:
                issues.append(f"Critical disk usage: {disk_percent:.1f}%")
            elif disk_percent > 85:
                warnings.append(f"High disk usage: {disk_percent:.1f}%")
            
            if load_1min and load_1min > cpu_count * 2:
                issues.append(f"High load average: {load_1min:.2f}")
            elif load_1min and load_1min > cpu_count:
                warnings.append(f"Elevated load average: {load_1min:.2f}")
            
            return {
                'healthy': len(issues) == 0,
                'status': 'critical' if issues else 'warning' if warnings else 'ok',
                'message': '; '.join(issues) if issues else 'System resources normal',
                'warnings': warnings,
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'memory_percent': memory_percent,
                    'memory_available_mb': memory_available,
                    'disk_percent': disk_percent,
                    'disk_free_gb': disk_free,
                    'load_1min': load_1min,
                    'load_5min': load_5min,
                    'load_15min': load_15min,
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'healthy': False,
                'status': 'error',
                'message': 'psutil package required for system monitoring',
                'recommendation': 'Install with: pip install psutil',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'System resource check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            database_url = os.getenv('DATABASE_URL', '')
            
            if not database_url:
                return {
                    'healthy': False,
                    'status': 'error',
                    'message': 'DATABASE_URL not configured',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Parse database URL
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            db_type = parsed.scheme
            
            if db_type == 'sqlite':
                return await self._check_sqlite_health(parsed)
            elif db_type == 'postgresql':
                return await self._check_postgresql_health(parsed)
            elif db_type == 'mysql':
                return await self._check_mysql_health(parsed)
            else:
                return {
                    'healthy': False,
                    'status': 'error',
                    'message': f'Unsupported database type: {db_type}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Database connectivity check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_sqlite_health(self, parsed_url: Any) -> Dict[str, Any]:
        """Check SQLite database health."""
        try:
            import sqlite3
            
            db_path = parsed_url.path
            if not Path(db_path).exists():
                return {
                    'healthy': False,
                    'status': 'error',
                    'message': f'SQLite database file not found: {db_path}',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Test connection and basic query
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            
            # Check file size and permissions
            db_file = Path(db_path)
            file_size = db_file.stat().st_size / 1024 / 1024  # MB
            
            warnings = []
            if file_size > 1000:  # 1GB
                warnings.append(f"Large database file: {file_size:.1f}MB")
            
            return {
                'healthy': True,
                'status': 'ok',
                'message': 'SQLite database accessible',
                'warnings': warnings,
                'metrics': {
                    'database_type': 'sqlite',
                    'file_size_mb': file_size,
                    'file_path': db_path
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'SQLite health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_postgresql_health(self, parsed_url: Any) -> Dict[str, Any]:
        """Check PostgreSQL database health."""
        try:
            import psycopg2  # type: ignore[import-untyped]
            
            # Connect to database
            conn = psycopg2.connect(
                host=parsed_url.hostname,
                port=parsed_url.port or 5432,
                user=parsed_url.username,
                password=parsed_url.password,
                database=parsed_url.path[1:],  # Remove leading /
                connect_timeout=10
            )
            
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1")
            
            # Get database info
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # Check connection count
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            connection_count = cursor.fetchone()[0]
            
            conn.close()
            
            warnings = []
            if connection_count > 80:
                warnings.append(f"High connection count: {connection_count}")
            
            return {
                'healthy': True,
                'status': 'ok',
                'message': 'PostgreSQL database accessible',
                'warnings': warnings,
                'metrics': {
                    'database_type': 'postgresql',
                    'version': version,
                    'connection_count': connection_count
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'healthy': False,
                'status': 'error',
                'message': 'psycopg2 package required for PostgreSQL',
                'recommendation': 'Install with: pip install psycopg2-binary',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'PostgreSQL health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_mysql_health(self, parsed_url: Any) -> Dict[str, Any]:
        """Check MySQL database health."""
        try:
            import pymysql  # type: ignore[import-untyped]
            
            # Connect to database
            conn = pymysql.connect(
                host=parsed_url.hostname,
                port=parsed_url.port or 3306,
                user=parsed_url.username,
                password=parsed_url.password,
                database=parsed_url.path[1:],  # Remove leading /
                connect_timeout=10
            )
            
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1")
            
            # Get database info
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            # Check process list
            cursor.execute("SHOW PROCESSLIST")
            process_count = len(cursor.fetchall())
            
            conn.close()
            
            warnings = []
            if process_count > 80:
                warnings.append(f"High process count: {process_count}")
            
            return {
                'healthy': True,
                'status': 'ok',
                'message': 'MySQL database accessible',
                'warnings': warnings,
                'metrics': {
                    'database_type': 'mysql',
                    'version': version,
                    'process_count': process_count
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'healthy': False,
                'status': 'error',
                'message': 'PyMySQL package required for MySQL',
                'recommendation': 'Install with: pip install PyMySQL',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'MySQL health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_cache_connectivity(self) -> Dict[str, Any]:
        """Check cache system connectivity."""
        try:
            cache_driver = os.getenv('CACHE_DRIVER', 'array')
            
            if cache_driver == 'redis':
                return await self._check_redis_health()
            elif cache_driver in ['array', 'file']:
                return {
                    'healthy': True,
                    'status': 'ok',
                    'message': f'Cache driver {cache_driver} configured',
                    'metrics': {'cache_driver': cache_driver},
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'healthy': False,
                    'status': 'warning',
                    'message': f'Unknown cache driver: {cache_driver}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Cache connectivity check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis cache health."""
        try:
            import redis
            
            host = os.getenv('REDIS_HOST', 'localhost')
            port = int(os.getenv('REDIS_PORT', 6379))
            password = os.getenv('REDIS_PASSWORD')
            
            r = redis.Redis(
                host=host,
                port=port,
                password=password,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # Test connection
            getattr(r, 'ping')()
            
            # Get Redis info
            info = getattr(r, 'info')()
            
            warnings = []
            if info['used_memory'] > info['total_system_memory'] * 0.8:
                warnings.append("High memory usage")
            
            if info['connected_clients'] > 100:
                warnings.append(f"High client count: {info['connected_clients']}")
            
            return {
                'healthy': True,
                'status': 'ok',
                'message': 'Redis accessible',
                'warnings': warnings,
                'metrics': {
                    'redis_version': info['redis_version'],
                    'used_memory_mb': info['used_memory'] / 1024 / 1024,
                    'connected_clients': info['connected_clients'],
                    'uptime_days': info['uptime_in_seconds'] / 86400
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'healthy': False,
                'status': 'error',
                'message': 'redis package required for Redis',
                'recommendation': 'Install with: pip install redis',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Redis health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_storage_health(self) -> Dict[str, Any]:
        """Check storage system health."""
        try:
            storage_dirs = [
                'storage/logs',
                'storage/cache',
                'storage/framework',
                'storage/app',
            ]
            
            issues: List[str] = []
            warnings: List[str] = []
            storage_info = {}
            
            for storage_dir in storage_dirs:
                dir_path = Path(storage_dir)
                
                if not dir_path.exists():
                    issues.append(f"Storage directory missing: {storage_dir}")
                    continue
                
                # Check permissions
                if not os.access(dir_path, os.W_OK):
                    issues.append(f"Storage directory not writable: {storage_dir}")
                
                # Check disk space
                try:
                    import shutil
                    total, used, free = shutil.disk_usage(dir_path)
                    
                    storage_info[storage_dir] = {
                        'total_gb': total / 1024 / 1024 / 1024,
                        'used_gb': used / 1024 / 1024 / 1024,
                        'free_gb': free / 1024 / 1024 / 1024,
                        'used_percent': (used / total) * 100
                    }
                    
                    if (used / total) > 0.95:
                        issues.append(f"Storage almost full: {storage_dir}")
                    elif (used / total) > 0.85:
                        warnings.append(f"Storage filling up: {storage_dir}")
                
                except Exception:
                    warnings.append(f"Could not check disk usage for: {storage_dir}")
            
            return {
                'healthy': len(issues) == 0,
                'status': 'error' if issues else 'warning' if warnings else 'ok',
                'message': '; '.join(issues) if issues else 'Storage healthy',
                'warnings': warnings,
                'metrics': storage_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Storage health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_python_dependencies(self) -> Dict[str, Any]:
        """Check Python dependencies health."""
        try:
            import pkg_resources  # type: ignore[import-untyped]
            import subprocess
            
            # Get installed packages
            installed_packages = {pkg.project_name.lower(): pkg.version 
                                for pkg in pkg_resources.working_set}
            
            # Check for critical packages
            critical_packages = [
                'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic'
            ]
            
            missing_critical = []
            for package in critical_packages:
                if package not in installed_packages:
                    missing_critical.append(package)
            
            # Check for security vulnerabilities (if safety is installed)
            security_issues: List[str] = []
            try:
                result = subprocess.run(
                    ['safety', 'check', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    import json
                    safety_data = json.loads(result.stdout)
                    security_issues = safety_data
                
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                pass  # Safety not installed or other issue
            
            warnings = []
            if security_issues:
                warnings.append(f"Found {len(security_issues)} security vulnerabilities")
            
            return {
                'healthy': len(missing_critical) == 0,
                'status': 'error' if missing_critical else 'warning' if warnings else 'ok',
                'message': f'Missing critical packages: {", ".join(missing_critical)}' if missing_critical else 'Dependencies OK',
                'warnings': warnings,
                'metrics': {
                    'total_packages': len(installed_packages),
                    'missing_critical': missing_critical,
                    'security_vulnerabilities': len(security_issues)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Dependencies check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_configuration_health(self) -> Dict[str, Any]:
        """Check configuration health."""
        try:
            issues: List[str] = []
            warnings: List[str] = []
            
            # Check essential environment variables
            essential_vars = ['APP_KEY', 'APP_ENV', 'DATABASE_URL']
            
            for var in essential_vars:
                if not os.getenv(var):
                    issues.append(f"Missing environment variable: {var}")
            
            # Check for insecure configurations
            app_env = os.getenv('APP_ENV', 'development')
            app_debug = os.getenv('APP_DEBUG', 'false').lower() == 'true'
            
            if app_env == 'production' and app_debug:
                issues.append("Debug mode enabled in production")
            
            # Check file permissions
            sensitive_files = ['.env', 'config/']
            for file_pattern in sensitive_files:
                file_path = Path(file_pattern)
                if file_path.exists():
                    try:
                        import stat
                        file_stat = file_path.stat()
                        mode = file_stat.st_mode
                        
                        if mode & stat.S_IROTH:
                            warnings.append(f"File world-readable: {file_pattern}")
                        if mode & stat.S_IWOTH:
                            issues.append(f"File world-writable: {file_pattern}")
                    except Exception:
                        pass
            
            return {
                'healthy': len(issues) == 0,
                'status': 'error' if issues else 'warning' if warnings else 'ok',
                'message': '; '.join(issues) if issues else 'Configuration healthy',
                'warnings': warnings,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Configuration check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity."""
        try:
            import aiohttp  # type: ignore[import-not-found]
            
            services_to_check = []
            
            # Add email service if configured
            mail_host = os.getenv('MAIL_HOST')
            if mail_host:
                services_to_check.append({
                    'name': 'Mail Server',
                    'host': mail_host,
                    'port': int(os.getenv('MAIL_PORT', 587)),
                    'type': 'smtp'
                })
            
            if not services_to_check:
                return {
                    'healthy': True,
                    'status': 'ok',
                    'message': 'No external services configured',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check each service
            results = {}
            for service in services_to_check:
                try:
                    if service['type'] == 'smtp':
                        # Simple socket connection test
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(10)
                        result = sock.connect_ex((service['host'], service['port']))
                        sock.close()
                        
                        results[service['name']] = result == 0
                    else:
                        results[service['name']] = False
                        
                except Exception:
                    results[service['name']] = False
            
            failed_services: list[str] = [str(name) for name, status in results.items() if not status]
            
            return {
                'healthy': len(failed_services) == 0,
                'status': 'error' if failed_services else 'ok',
                'message': f'Failed services: {", ".join(failed_services)}' if failed_services else 'External services accessible',
                'metrics': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'External services check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_security_status(self) -> Dict[str, Any]:
        """Check security configuration status."""
        try:
            issues: List[str] = []
            warnings: List[str] = []
            
            # Check for security headers configuration
            # This would check your middleware/security setup
            
            # Check for HTTPS configuration
            app_url = os.getenv('APP_URL', '')
            if app_url and not app_url.startswith('https://'):
                warnings.append("Application URL not using HTTPS")
            
            # Check for secure session configuration
            # This would check session security settings
            
            return {
                'healthy': len(issues) == 0,
                'status': 'error' if issues else 'warning' if warnings else 'ok',
                'message': '; '.join(issues) if issues else 'Security configuration OK',
                'warnings': warnings,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Security check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check performance metrics."""
        try:
            # This would integrate with your application's metrics system
            # For now, provide basic system performance indicators
            
            return {
                'healthy': True,
                'status': 'ok',
                'message': 'Performance metrics not implemented',
                'metrics': {
                    'note': 'Implement application-specific performance monitoring'
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Performance metrics check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_log_health(self) -> Dict[str, Any]:
        """Check log system health."""
        try:
            log_dirs = ['storage/logs', 'logs']
            issues: List[str] = []
            warnings: List[str] = []
            log_info = {}
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    # Check log directory size
                    total_size = sum(f.stat().st_size for f in log_path.rglob('*') if f.is_file())
                    total_size_mb = total_size / 1024 / 1024
                    
                    log_info[log_dir] = {
                        'total_size_mb': total_size_mb,
                        'file_count': len(list(log_path.rglob('*.log')))
                    }
                    
                    if total_size_mb > 1000:  # 1GB
                        warnings.append(f"Large log directory: {log_dir} ({total_size_mb:.1f}MB)")
                    
                    # Check if logs are being written recently
                    recent_logs = [f for f in log_path.rglob('*.log') 
                                 if f.stat().st_mtime > time.time() - 86400]  # Last 24 hours
                    
                    if not recent_logs and log_info[log_dir]['file_count'] > 0:
                        warnings.append(f"No recent log activity in {log_dir}")
            
            if not any(Path(d).exists() for d in log_dirs):
                issues.append("No log directories found")
            
            return {
                'healthy': len(issues) == 0,
                'status': 'error' if issues else 'warning' if warnings else 'ok',
                'message': '; '.join(issues) if issues else 'Log system healthy',
                'warnings': warnings,
                'metrics': log_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'message': f'Log health check failed: {e}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _attempt_fixes(self) -> None:
        """Attempt to fix detected issues automatically."""
        self.info("🔧 Attempting to fix detected issues...")
        
        fixed_count = 0
        
        for component in self.failed_checks:
            result = self.health_results[component]
            
            if component == 'storage' and 'Storage directory missing' in result['message']:
                # Create missing storage directories
                storage_dirs = ['storage/logs', 'storage/cache', 'storage/framework', 'storage/app']
                for storage_dir in storage_dirs:
                    dir_path = Path(storage_dir)
                    if not dir_path.exists():
                        try:
                            dir_path.mkdir(parents=True, exist_ok=True)
                            self.comment(f"Created directory: {storage_dir}")
                            fixed_count += 1
                        except Exception as e:
                            self.warn(f"Could not create {storage_dir}: {e}")
            
            elif component == 'configuration' and 'world-writable' in result.get('message', ''):
                # Fix file permissions
                try:
                    import stat
                    sensitive_files = ['.env', 'config/']
                    
                    for file_pattern in sensitive_files:
                        file_path = Path(file_pattern)
                        if file_path.exists():
                            if file_path.is_file():
                                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
                                self.comment(f"Fixed permissions: {file_pattern}")
                                fixed_count += 1
                
                except Exception as e:
                    self.warn(f"Could not fix file permissions: {e}")
        
        if fixed_count > 0:
            self.info(f"✅ Fixed {fixed_count} issues")
        else:
            self.warn("No issues could be automatically fixed")
    
    def _display_health_results(self) -> None:
        """Display health check results."""
        self.new_line()
        self.info("🏥 Health Check Results")
        self.line("=" * 60)
        
        # Sort results by status (failed first)
        sorted_results = sorted(
            self.health_results.items(),
            key=lambda x: (x[1]['healthy'], x[1]['status'])
        )
        
        for component, result in sorted_results:
            status = result['status']
            healthy = result['healthy']
            
            # Choose icon based on status
            if healthy:
                icon = "✅"
            elif status == 'critical':
                icon = "🔴"
            elif status == 'error':
                icon = "❌"
            elif status == 'warning':
                icon = "⚠️"
            else:
                icon = "❓"
            
            self.line(f"{icon} {component.title()}: {result['message']}")
            
            # Show warnings if any
            if result.get('warnings'):
                for warning in result['warnings']:
                    self.line(f"    ⚠️  {warning}")
            
            # Show key metrics if available
            if result.get('metrics'):
                metrics = result['metrics']
                if component == 'system' and 'cpu_percent' in metrics:
                    self.line(f"    📊 CPU: {metrics['cpu_percent']:.1f}%, "
                             f"Memory: {metrics['memory_percent']:.1f}%, "
                             f"Disk: {metrics['disk_percent']:.1f}%")
                elif component == 'database' and 'database_type' in metrics:
                    self.line(f"    🗄️  Type: {metrics['database_type']}")
                elif component == 'cache' and 'redis_version' in metrics:
                    self.line(f"    📦 Redis {metrics['redis_version']}, "
                             f"Memory: {metrics['used_memory_mb']:.1f}MB")
    
    async def _export_health_results(self, export_file: str) -> None:
        """Export health results to file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'overall_health': len(self.failed_checks) == 0,
                'failed_checks': self.failed_checks,
                'warnings_count': len(self.warnings),
                'results': self.health_results
            }
            
            export_path.write_text(json.dumps(export_data, indent=2, default=str))
            self.info(f"✅ Health check results exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export health results: {e}")
    
    def _show_overall_health_status(self) -> None:
        """Show overall health status summary."""
        self.new_line()
        total_checks = len(self.health_results)
        failed_count = len(self.failed_checks)
        warning_count = len(self.warnings)
        passed_count = total_checks - failed_count
        
        if failed_count == 0:
            self.info("🎉 Overall Health Status: HEALTHY")
            self.line(f"✅ {passed_count}/{total_checks} checks passed")
        else:
            self.error("🚨 Overall Health Status: UNHEALTHY")
            self.line(f"❌ {failed_count}/{total_checks} checks failed")
            self.line(f"✅ {passed_count}/{total_checks} checks passed")
        
        if warning_count > 0:
            self.warn(f"⚠️  {warning_count} warnings detected")
        
        self.new_line()
        
        if failed_count > 0:
            self.comment("Run with --fix to attempt automatic fixes")
            self.comment("Critical issues should be addressed immediately")
        
        self.comment("Use --monitoring for continuous health monitoring")
        self.comment("Use --export to save detailed results")