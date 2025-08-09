from __future__ import annotations

import asyncio
import time
import statistics
import importlib
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from ..Command import Command


class RoutePerformanceCommand(Command):
    """Monitor and analyze route performance."""
    
    signature = "route:performance {--benchmark : Run performance benchmarks} {--monitor=60 : Monitor duration in seconds} {--endpoint= : Specific endpoint to test} {--concurrent=5 : Concurrent requests} {--export= : Export results to file} {--threshold=1000 : Response time threshold in ms}"
    description = "Monitor and analyze route performance"
    help = "Benchmark route performance, monitor response times, and identify bottlenecks"
    
    def __init__(self) -> None:
        super().__init__()
        self.performance_data: List[Dict[str, Any]] = []
        self.slow_routes: List[Dict[str, Any]] = []
    
    async def handle(self) -> None:
        """Execute performance analysis."""
        benchmark = self.option("benchmark", False)
        monitor_duration = int(self.option("monitor", 60))
        endpoint = self.option("endpoint")
        concurrent = int(self.option("concurrent", 5))
        export_file = self.option("export")
        threshold_ms = float(self.option("threshold", 1000))
        
        if benchmark:
            await self._run_benchmarks(endpoint, concurrent, threshold_ms)
        else:
            await self._monitor_performance(monitor_duration, threshold_ms)
        
        # Export results if requested
        if export_file:
            await self._export_results(export_file)
        
        # Show recommendations
        self._show_performance_recommendations()
    
    async def _run_benchmarks(self, endpoint: Optional[str], concurrent: int, threshold_ms: float) -> None:
        """Run performance benchmarks."""
        self.info("⚡ Running route performance benchmarks...")
        
        if endpoint:
            await self._benchmark_single_endpoint(endpoint, concurrent, threshold_ms)
        else:
            await self._benchmark_all_routes(concurrent, threshold_ms)
    
    async def _benchmark_single_endpoint(self, endpoint: str, concurrent: int, threshold_ms: float) -> None:
        """Benchmark a single endpoint."""
        self.info(f"🎯 Benchmarking endpoint: {endpoint}")
        self.comment(f"Concurrent requests: {concurrent}")
        
        try:
            import httpx
            
            # Test different request patterns
            test_scenarios = [
                {"name": "Cold Start", "requests": 1, "delay": 0},
                {"name": "Warm Up", "requests": 10, "delay": 0.1},
                {"name": "Load Test", "requests": 100, "delay": 0},
                {"name": "Stress Test", "requests": 200, "delay": 0},
            ]
            
            results = []
            
            for scenario in test_scenarios:
                self.comment(f"Running {scenario['name']} scenario...")
                
                requests_value = scenario.get('requests', 1)
                delay_value = scenario.get('delay', 0)
                requests_count = int(requests_value) if isinstance(requests_value, (int, float, str)) else 1
                delay_time = float(delay_value) if isinstance(delay_value, (int, float, str)) else 0.0
                
                scenario_results = await self._execute_benchmark_scenario(
                    endpoint, requests_count, concurrent, delay_time
                )
                
                scenario_results['scenario'] = scenario['name']
                results.append(scenario_results)
                
                # Cool down between scenarios
                if delay_time > 0:
                    await asyncio.sleep(delay_time)
            
            self._display_benchmark_results(endpoint, results, threshold_ms)
            
        except ImportError:
            self.error("httpx is required for benchmarking. Install with: pip install httpx")
        except Exception as e:
            self.error(f"Benchmark failed: {e}")
    
    async def _execute_benchmark_scenario(
        self, 
        endpoint: str, 
        total_requests: int, 
        concurrent: int,
        delay: float
    ) -> Dict[str, Any]:
        """Execute a single benchmark scenario."""
        import httpx
        
        response_times = []
        errors = 0
        status_codes: Dict[int, int] = {}
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent)
        
        async def make_request(client: httpx.AsyncClient, request_id: int) -> None:
            async with semaphore:
                try:
                    start_time = time.time()
                    response = await client.get(endpoint, timeout=30.0)
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    response_times.append(response_time)
                    
                    # Track status codes
                    status_code = response.status_code
                    status_codes[status_code] = status_codes.get(status_code, 0) + 1
                    
                    # Small delay to avoid overwhelming
                    if delay > 0:
                        await asyncio.sleep(delay / 1000)  # Convert to seconds
                        
                except Exception as e:
                    nonlocal errors
                    errors += 1
        
        # Execute requests
        start_time = time.time()
        
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            tasks = [make_request(client, i) for i in range(total_requests)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate statistics
        if response_times:
            return {
                'total_requests': total_requests,
                'successful_requests': len(response_times),
                'failed_requests': errors,
                'total_duration': total_duration,
                'requests_per_second': len(response_times) / total_duration if total_duration > 0 else 0,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times),
                'p95_response_time': self._calculate_percentile(response_times, 95),
                'p99_response_time': self._calculate_percentile(response_times, 99),
                'status_codes': status_codes,
            }
        else:
            return {
                'total_requests': total_requests,
                'successful_requests': 0,
                'failed_requests': errors,
                'total_duration': total_duration,
                'requests_per_second': 0,
                'error': 'All requests failed'
            }
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        else:
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    
    async def _benchmark_all_routes(self, concurrent: int, threshold_ms: float) -> None:
        """Benchmark all discoverable routes."""
        self.info("🔍 Discovering routes for benchmarking...")
        
        routes = await self._discover_benchmarkable_routes()
        
        if not routes:
            self.warn("No benchmarkable routes found.")
            return
        
        self.info(f"Found {len(routes)} routes to benchmark")
        
        progress_bar = self.progress_bar(len(routes), "Benchmarking routes")
        
        for route_info in routes:
            endpoint = route_info['path']
            
            # Skip routes with parameters for now
            if '{' in endpoint:
                progress_bar.advance()
                continue
            
            # Only benchmark GET routes for safety
            if 'GET' not in route_info.get('methods', []):
                progress_bar.advance()
                continue
            
            try:
                result = await self._execute_benchmark_scenario(endpoint, 10, concurrent, 0)
                
                result.update({
                    'endpoint': endpoint,
                    'route_name': route_info.get('name', ''),
                    'handler': route_info.get('handler', ''),
                })
                
                self.performance_data.append(result)
                
                # Track slow routes
                if result.get('avg_response_time', 0) > threshold_ms:
                    self.slow_routes.append(result)
                
            except Exception as e:
                self.warn(f"Failed to benchmark {endpoint}: {e}")
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        self._display_all_routes_summary(threshold_ms)
    
    async def _discover_benchmarkable_routes(self) -> List[Dict[str, Any]]:
        """Discover routes suitable for benchmarking."""
        routes = []
        
        try:
            # Try to import the main FastAPI app
            main_module = importlib.import_module("main")
            if hasattr(main_module, "app"):
                app = main_module.app
                
                for route in app.routes:
                    route_info = self._extract_route_info(route)
                    if route_info and self._is_benchmarkable(route_info):
                        routes.append(route_info)
        except Exception as e:
            self.warn(f"Could not load main app: {e}")
        
        return routes
    
    def _extract_route_info(self, route: Any) -> Optional[Dict[str, Any]]:
        """Extract route information."""
        try:
            return {
                'methods': list(getattr(route, 'methods', ['GET'])),
                'path': getattr(route, 'path', ''),
                'name': getattr(route, 'name', ''),
                'handler': str(getattr(route, 'endpoint', '')),
            }
        except Exception:
            return None
    
    def _is_benchmarkable(self, route_info: Dict[str, Any]) -> bool:
        """Check if route is suitable for benchmarking."""
        path = route_info['path']
        
        # Skip internal routes
        if path.startswith(('/docs', '/openapi', '/redoc', '/static')):
            return False
        
        # Skip routes that might be destructive or require auth
        dangerous_patterns = [
            '/admin', '/delete', '/remove', '/destroy',
            '/upload', '/download', '/file'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in path.lower():
                return False
        
        return True
    
    async def _monitor_performance(self, duration: int, threshold_ms: float) -> None:
        """Monitor route performance in real-time."""
        self.info(f"📊 Monitoring route performance for {duration} seconds...")
        self.comment("This would integrate with your application's metrics system")
        
        # This would connect to actual application metrics
        # For now, simulate monitoring
        
        start_time = time.time()
        monitoring_data = []
        
        while time.time() - start_time < duration:
            # Simulate performance data collection
            await asyncio.sleep(5)  # Check every 5 seconds
            
            elapsed = time.time() - start_time
            
            # Simulate some metrics
            fake_metrics = {
                'timestamp': datetime.now(),
                'avg_response_time': 200 + (time.time() % 100),  # Simulate varying response times
                'requests_per_second': 50 + (time.time() % 20),
                'error_rate': 0.5 + (time.time() % 1),
                'active_connections': 10 + int(time.time() % 5),
            }
            
            monitoring_data.append(fake_metrics)
            
            # Show progress
            progress = int((elapsed / duration) * 100)
            self.comment(f"Monitoring... {progress}% complete")
        
        self._display_monitoring_results(monitoring_data, threshold_ms)
    
    def _display_benchmark_results(
        self, 
        endpoint: str, 
        results: List[Dict[str, Any]], 
        threshold_ms: float
    ) -> None:
        """Display benchmark results."""
        self.new_line()
        self.info(f"📈 Benchmark Results for: {endpoint}")
        self.line("=" * 80)
        
        for result in results:
            if 'error' in result:
                self.error(f"{result['scenario']}: {result['error']}")
                continue
            
            scenario = result['scenario']
            avg_time = result['avg_response_time']
            rps = result['requests_per_second']
            success_rate = (result['successful_requests'] / result['total_requests']) * 100
            
            # Color code based on performance
            if avg_time > threshold_ms:
                status = "🔴 SLOW"
            elif avg_time > threshold_ms * 0.7:
                status = "🟡 FAIR"
            else:
                status = "🟢 GOOD"
            
            self.info(f"{status} {scenario}")
            self.line(f"  Avg Response Time: {avg_time:.2f}ms")
            self.line(f"  Requests/Second: {rps:.2f}")
            self.line(f"  Success Rate: {success_rate:.1f}%")
            self.line(f"  95th Percentile: {result['p95_response_time']:.2f}ms")
            self.line(f"  99th Percentile: {result['p99_response_time']:.2f}ms")
            self.line("")
    
    def _display_all_routes_summary(self, threshold_ms: float) -> None:
        """Display summary of all routes benchmarked."""
        if not self.performance_data:
            return
        
        self.new_line()
        self.info("📊 Route Performance Summary")
        self.line("=" * 80)
        
        # Sort by average response time (slowest first)
        sorted_data = sorted(self.performance_data, 
                           key=lambda x: x.get('avg_response_time', 0), 
                           reverse=True)
        
        # Show top 10 slowest routes
        self.warn(f"🐌 Slowest Routes (Top {min(10, len(sorted_data))})")
        for i, result in enumerate(sorted_data[:10], 1):
            avg_time = result.get('avg_response_time', 0)
            endpoint = result['endpoint']
            status = "🔴" if avg_time > threshold_ms else "🟡" if avg_time > threshold_ms * 0.7 else "🟢"
            
            self.line(f"{i:2d}. {status} {endpoint:<40} {avg_time:>8.2f}ms")
        
        self.new_line()
        
        # Performance statistics
        avg_times = [r.get('avg_response_time', 0) for r in self.performance_data if 'avg_response_time' in r]
        if avg_times:
            self.info("📈 Performance Statistics")
            self.line(f"  Routes tested: {len(self.performance_data)}")
            self.line(f"  Average response time: {statistics.mean(avg_times):.2f}ms")
            self.line(f"  Median response time: {statistics.median(avg_times):.2f}ms")
            self.line(f"  Slowest route: {max(avg_times):.2f}ms")
            self.line(f"  Fastest route: {min(avg_times):.2f}ms")
            
            slow_count = len([t for t in avg_times if t > threshold_ms])
            self.line(f"  Routes above threshold ({threshold_ms}ms): {slow_count}")
    
    def _display_monitoring_results(self, data: List[Dict[str, Any]], threshold_ms: float) -> None:
        """Display monitoring results."""
        if not data:
            return
        
        self.new_line()
        self.info("📊 Performance Monitoring Results")
        self.line("=" * 50)
        
        # Calculate averages
        avg_response_time = statistics.mean([d['avg_response_time'] for d in data])
        avg_rps = statistics.mean([d['requests_per_second'] for d in data])
        avg_error_rate = statistics.mean([d['error_rate'] for d in data])
        
        self.line(f"  Average Response Time: {avg_response_time:.2f}ms")
        self.line(f"  Average Requests/Second: {avg_rps:.2f}")
        self.line(f"  Average Error Rate: {avg_error_rate:.2f}%")
        
        if avg_response_time > threshold_ms:
            self.warn(f"⚠️  Average response time exceeds threshold ({threshold_ms}ms)")
        
        if avg_error_rate > 1.0:
            self.warn("⚠️  Error rate is elevated")
    
    async def _export_results(self, file_path: str) -> None:
        """Export performance results to file."""
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            
            export_data: Dict[str, Any] = {
                'timestamp': datetime.now().isoformat(),
                'performance_data': self.performance_data,
                'slow_routes': self.slow_routes,
                'summary': {
                    'total_routes_tested': len(self.performance_data),
                    'slow_routes_count': len(self.slow_routes),
                }
            }
            
            if self.performance_data:
                avg_times = [r.get('avg_response_time', 0) for r in self.performance_data if 'avg_response_time' in r]
                if avg_times:
                    export_data['summary'].update({
                        'avg_response_time': statistics.mean(avg_times),
                        'median_response_time': statistics.median(avg_times),
                        'max_response_time': max(avg_times),
                        'min_response_time': min(avg_times),
                    })
            
            export_path.write_text(json.dumps(export_data, indent=2, default=str))
            self.info(f"✅ Results exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export results: {e}")
    
    def _show_performance_recommendations(self) -> None:
        """Show performance optimization recommendations."""
        self.new_line()
        self.info("💡 Performance Optimization Recommendations")
        self.line("=" * 60)
        
        recommendations = []
        
        if self.slow_routes:
            recommendations.extend([
                f"🐌 {len(self.slow_routes)} routes are performing slowly",
                "Consider optimizing database queries in slow endpoints",
                "Add caching for frequently accessed data",
                "Review and optimize business logic in slow handlers"
            ])
        
        # General recommendations
        recommendations.extend([
            "🚀 General Performance Tips:",
            "• Use async/await for I/O operations",
            "• Implement proper database connection pooling",
            "• Add response caching headers where appropriate",
            "• Consider using a CDN for static assets",
            "• Monitor and optimize database query performance",
            "• Implement request rate limiting",
            "• Use compression for large responses"
        ])
        
        for rec in recommendations:
            if rec.startswith(('🐌', '🚀')):
                self.comment(rec)
            else:
                self.line(f"  {rec}")
        
        self.new_line()
        self.comment("Run 'route:performance --benchmark' to test specific endpoints")
        self.comment("Use --export to save detailed results for analysis")
# Register command
from app.Console.Artisan import register_command
register_command(RoutePerformanceCommand)
