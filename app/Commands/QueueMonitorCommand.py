from __future__ import annotations

import sys
import json
import time
import argparse
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.Services.QueueService import QueueService
from app.Jobs.Monitor import global_job_monitor
from app.Queue.QueueManager import global_queue_manager


def queue_dashboard_command() -> None:
    """Real-time queue monitoring dashboard."""
    parser = argparse.ArgumentParser(description='Queue monitoring dashboard')
    parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds')
    parser.add_argument('--connection', default='default', help='Database connection')
    
    args = parser.parse_args()
    
    try:
        print("Queue Monitoring Dashboard")
        print("=" * 60)
        print("Press Ctrl+C to exit")
        print()
        
        while True:
            # Clear screen (works on most terminals)
            print("\033[2J\033[H", end="")
            
            print(f"Queue Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            queue_service = QueueService(args.connection)
            
            # Overall statistics
            stats = queue_service.get_queue_stats()
            print("📊 OVERVIEW")
            print(f"   Total Active Jobs: {stats['totals']['active_jobs']}")
            print(f"   Failed Jobs: {stats['totals']['failed_jobs']}")
            print()
            
            # Queue breakdown
            print("🔄 QUEUES")
            if stats['queues']:
                for queue_name, queue_stats in stats['queues'].items():
                    status_icon = "🟢" if queue_stats['pending'] > 0 else "⚪"
                    print(f"   {status_icon} {queue_name:15} "
                          f"Pending: {queue_stats['pending']:3} | "
                          f"Reserved: {queue_stats['reserved']:3} | "
                          f"Failed: {queue_stats['failed']:3}")
            else:
                print("   No active queues")
            print()
            
            # Active workers/jobs
            print("👷 ACTIVE JOBS")
            active_jobs = global_job_monitor.get_active_jobs()
            if active_jobs:
                for job in active_jobs[:10]:  # Show top 10
                    runtime = f"{job['runtime_seconds']:.1f}s"
                    print(f"   🔄 {job['job_class']:25} ({runtime:8}) - {job['worker_id']}")
                if len(active_jobs) > 10:
                    print(f"   ... and {len(active_jobs) - 10} more")
            else:
                print("   No active jobs")
            print()
            
            # Performance metrics
            print("📈 PERFORMANCE (Last 24h)")
            perf = global_job_monitor.get_job_performance(hours=24)
            print(f"   Success Rate: {perf.success_rate:.1f}%")
            print(f"   Avg Duration: {perf.avg_duration_ms/1000:.2f}s")
            print(f"   Avg Memory: {perf.avg_memory_mb:.1f}MB")
            print(f"   Total Processed: {perf.total_jobs}")
            print()
            
            # Recent failures
            failed_jobs = queue_service.get_failed_jobs(limit=5)
            if failed_jobs:
                print("❌ RECENT FAILURES")
                for job in failed_jobs:
                    error = job['exception'][:50] + "..." if len(job['exception']) > 50 else job['exception']
                    print(f"   ❌ {job['job_class']:25} - {error}")
                print()
            
            print(f"Next update in {args.refresh}s...")
            time.sleep(args.refresh)
            
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        sys.exit(1)


def queue_metrics_command() -> None:
    """Detailed queue metrics and analytics."""
    parser = argparse.ArgumentParser(description='Queue metrics and analytics')
    parser.add_argument('--hours', type=int, default=24, help='Time window in hours')
    parser.add_argument('--queue', help='Specific queue to analyze')
    parser.add_argument('--job-class', help='Specific job class to analyze')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    
    args = parser.parse_args()
    
    try:
        if args.format == 'json':
            metrics_data: Dict[str, Any] = {}
        
        print(f"Queue Metrics - Last {args.hours} hours")
        print("=" * 50)
        
        # Overall performance
        perf = global_job_monitor.get_job_performance(
            job_class=args.job_class,
            queue=args.queue,
            hours=args.hours
        )
        
        if args.format == 'table':
            print(f"\n📊 OVERALL PERFORMANCE")
            print(f"   Total Jobs: {perf.total_jobs}")
            print(f"   Failed Jobs: {perf.failed_jobs}")
            print(f"   Success Rate: {perf.success_rate:.2f}%")
            print(f"   Average Duration: {perf.avg_duration_ms/1000:.2f}s")
            print(f"   Average Memory: {perf.avg_memory_mb:.2f}MB")
            print(f"   Average Attempts: {perf.avg_attempts:.2f}")
        else:
            metrics_data['overall'] = {
                'total_jobs': perf.total_jobs,
                'failed_jobs': perf.failed_jobs,
                'success_rate': perf.success_rate,
                'avg_duration_ms': perf.avg_duration_ms,
                'avg_memory_mb': perf.avg_memory_mb,
                'avg_attempts': perf.avg_attempts
            }
        
        # Queue breakdown
        queue_metrics = global_job_monitor.get_queue_metrics(hours=args.hours)
        
        if args.format == 'table':
            print(f"\n🔄 QUEUE BREAKDOWN")
            for queue_name, stats in queue_metrics.items():
                print(f"\n   Queue: {queue_name}")
                print(f"     Total: {stats['total_jobs']}")
                print(f"     Completed: {stats['completed_jobs']}")
                print(f"     Failed: {stats['failed_jobs']}")
                print(f"     Success Rate: {stats['success_rate']:.1f}%")
                print(f"     Avg Duration: {stats['avg_duration_ms']/1000:.2f}s")
                print(f"     Avg Memory: {stats['avg_memory_mb']:.2f}MB")
        else:
            metrics_data['queues'] = queue_metrics
        
        # Slow jobs
        slow_jobs = global_job_monitor.get_slow_jobs(threshold_ms=30000, limit=10)
        
        if args.format == 'table':
            if slow_jobs:
                print(f"\n🐌 SLOWEST JOBS")
                for job in slow_jobs:
                    duration = job['duration_seconds']
                    print(f"   {job['job_class']:30} {duration:8.2f}s")
        else:
            metrics_data['slow_jobs'] = slow_jobs
        
        # Memory hungry jobs
        memory_jobs = global_job_monitor.get_memory_hungry_jobs(threshold_mb=100, limit=10)
        
        if args.format == 'table':
            if memory_jobs:
                print(f"\n💾 MEMORY INTENSIVE JOBS")
                for job in memory_jobs:
                    memory = job['memory_peak_mb']
                    print(f"   {job['job_class']:30} {memory:8.1f}MB")
        else:
            metrics_data['memory_jobs'] = memory_jobs
        
        if args.format == 'json':
            print(json.dumps(metrics_data, indent=2, default=str))
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def queue_health_command() -> None:
    """Queue health check and diagnostics."""
    parser = argparse.ArgumentParser(description='Queue health check')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')
    parser.add_argument('--timeout', type=int, default=3600, help='Reserved job timeout')
    
    args = parser.parse_args()
    
    try:
        print("Queue Health Check")
        print("=" * 50)
        
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        issues_found = 0
        
        # Check for stuck jobs
        print("🔍 Checking for stuck jobs...")
        released = queue_service.release_reserved_jobs(args.timeout)
        if released > 0:
            issues_found += 1
            print(f"   ⚠️  Released {released} stuck jobs")
            if args.fix:
                print("   ✅ Fixed: Released stuck jobs")
        else:
            print("   ✅ No stuck jobs found")
        
        # Check queue sizes
        print("\n📏 Checking queue sizes...")
        stats = queue_service.get_queue_stats()
        
        for queue_name, queue_stats in stats['queues'].items():
            total_jobs = queue_stats['total']
            if total_jobs > 10000:  # Threshold for large queues
                issues_found += 1
                print(f"   ⚠️  Queue '{queue_name}' has {total_jobs} jobs (may need attention)")
            elif total_jobs > 1000:
                print(f"   ⚠️  Queue '{queue_name}' has {total_jobs} jobs (monitor closely)")
            else:
                print(f"   ✅ Queue '{queue_name}': {total_jobs} jobs (healthy)")
        
        # Check failed jobs
        print("\n❌ Checking failed jobs...")
        failed_jobs = queue_service.get_failed_jobs(limit=1)
        failed_count = len(failed_jobs)  # This is simplified; in reality you'd get total count
        
        if failed_count > 0:
            issues_found += 1
            print(f"   ⚠️  {failed_count} failed jobs need attention")
            if args.fix:
                # Show option to retry or clear
                print("   💡 Use 'make queue-retry-failed' to retry or 'make queue-clear-failed' to clear")
        else:
            print("   ✅ No failed jobs")
        
        # Check performance metrics
        print("\n📊 Checking performance...")
        perf = global_job_monitor.get_job_performance(hours=1)  # Last hour
        
        if perf.success_rate < 90:
            issues_found += 1
            print(f"   ⚠️  Success rate is low: {perf.success_rate:.1f}%")
        else:
            print(f"   ✅ Success rate: {perf.success_rate:.1f}%")
        
        if perf.avg_duration_ms > 60000:  # > 1 minute average
            issues_found += 1
            print(f"   ⚠️  Average job duration is high: {perf.avg_duration_ms/1000:.1f}s")
        else:
            print(f"   ✅ Average duration: {perf.avg_duration_ms/1000:.1f}s")
        
        # Summary
        print(f"\n📋 HEALTH SUMMARY")
        if issues_found == 0:
            print("   🎉 All systems healthy!")
        else:
            print(f"   ⚠️  {issues_found} issue(s) found")
            if not args.fix:
                print("   💡 Run with --fix to attempt automatic fixes")
        
        sys.exit(0 if issues_found == 0 else 1)
        
    except Exception as e:
        print(f"Health check error: {str(e)}")
        sys.exit(1)


def queue_top_command() -> None:
    """htop-style queue monitoring."""
    parser = argparse.ArgumentParser(description='Real-time queue process monitor')
    parser.add_argument('--refresh', type=int, default=2, help='Refresh interval')
    
    args = parser.parse_args()
    
    try:
        print("Queue Top - Press Ctrl+C to exit")
        
        while True:
            # Clear screen
            print("\033[2J\033[H", end="")
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"Queue Top - {timestamp}")
            print("=" * 80)
            
            # Header
            print(f"{'PID':<8} {'QUEUE':<15} {'JOB CLASS':<25} {'RUNTIME':<10} {'MEMORY':<8} {'STATUS'}")
            print("-" * 80)
            
            # Active jobs
            active_jobs = global_job_monitor.get_active_jobs()
            
            for i, job in enumerate(active_jobs[:20]):  # Top 20
                pid = f"job{i+1:03d}"
                queue = job['job_class'].split('.')[-1] if '.' in job['job_class'] else job['job_class']
                runtime = f"{job['runtime_seconds']:.1f}s"
                
                # Simulate memory (in real implementation, you'd track actual memory)
                memory = "45.2M"  # Placeholder
                status = "RUN"
                
                print(f"{pid:<8} {job.get('queue', 'default'):<15} {queue:<25} {runtime:<10} {memory:<8} {status}")
            
            if not active_jobs:
                print("No active jobs")
            
            print(f"\nRefresh in {args.refresh}s... (Ctrl+C to quit)")
            time.sleep(args.refresh)
            
    except KeyboardInterrupt:
        print("\n\nQueue Top stopped.")


def main() -> None:
    """Main command dispatcher for queue monitoring."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.Commands.QueueMonitorCommand <command>")
        print("")
        print("Available commands:")
        print("  dashboard   - Real-time queue monitoring dashboard")
        print("  metrics     - Detailed queue metrics and analytics")  
        print("  health      - Queue health check and diagnostics")
        print("  top         - htop-style queue process monitor")
        return
    
    command = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove command from argv
    
    if command == 'dashboard':
        queue_dashboard_command()
    elif command == 'metrics':
        queue_metrics_command()
    elif command == 'health':
        queue_health_command()
    elif command == 'top':
        queue_top_command()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()