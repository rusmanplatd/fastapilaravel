from __future__ import annotations

import sys
import json
import argparse
from typing import Optional

from app.Services.QueueService import QueueService


def queue_stats_command() -> None:
    """Show queue statistics."""
    parser = argparse.ArgumentParser(description='Show queue statistics')
    parser.add_argument('--connection', default='default', help='Database connection')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    try:
        queue_service = QueueService(args.connection)
        stats = queue_service.get_queue_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2, default=str))
        else:
            print("Queue Statistics:")
            print("=" * 50)
            
            for queue_name, queue_stats in stats["queues"].items():
                print(f"\nQueue: {queue_name}")
                print(f"  Pending Jobs: {queue_stats['pending']}")
                print(f"  Delayed Jobs: {queue_stats['delayed']}")
                print(f"  Reserved Jobs: {queue_stats['reserved']}")
                print(f"  Failed Jobs: {queue_stats['failed']}")
                print(f"  Total Active: {queue_stats['total']}")
            
            print(f"\nOverall Totals:")
            print(f"  Active Jobs: {stats['totals']['active_jobs']}")
            print(f"  Failed Jobs: {stats['totals']['failed_jobs']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def queue_clear_command() -> None:
    """Clear jobs from queue."""
    parser = argparse.ArgumentParser(description='Clear jobs from queue')
    parser.add_argument('--queue', default='default', help='Queue to clear')
    parser.add_argument('--connection', default='default', help='Database connection')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    try:
        queue_service = QueueService(args.connection)
        
        if not args.confirm:
            response = input(f"Are you sure you want to clear all jobs from '{args.queue}' queue? [y/N]: ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return
        
        count = queue_service.clear_queue(args.queue)
        print(f"Cleared {count} jobs from '{args.queue}' queue.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def queue_failed_command() -> None:
    """Manage failed jobs."""
    parser = argparse.ArgumentParser(description='Manage failed jobs')
    subparsers = parser.add_subparsers(dest='action', help='Action to perform')
    
    # List failed jobs
    list_parser = subparsers.add_parser('list', help='List failed jobs')
    list_parser.add_argument('--queue', help='Filter by queue')
    list_parser.add_argument('--limit', type=int, default=50, help='Number of jobs to show')
    list_parser.add_argument('--offset', type=int, default=0, help='Offset for pagination')
    list_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Retry failed job
    retry_parser = subparsers.add_parser('retry', help='Retry failed job')
    retry_parser.add_argument('job_id', help='Failed job ID to retry')
    retry_parser.add_argument('--queue', help='Queue to retry job on')
    
    # Retry all failed jobs
    retry_all_parser = subparsers.add_parser('retry-all', help='Retry all failed jobs')
    retry_all_parser.add_argument('--queue', help='Filter by queue')
    retry_all_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    # Delete failed job
    delete_parser = subparsers.add_parser('delete', help='Delete failed job')
    delete_parser.add_argument('job_id', help='Failed job ID to delete')
    delete_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    # Clear all failed jobs
    clear_parser = subparsers.add_parser('clear', help='Clear all failed jobs')
    clear_parser.add_argument('--queue', help='Filter by queue')
    clear_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    parser.add_argument('--connection', default='default', help='Database connection')
    
    args = parser.parse_args()
    
    if not args.action:
        parser.print_help()
        return
    
    try:
        queue_service = QueueService(args.connection)
        
        if args.action == 'list':
            failed_jobs = queue_service.get_failed_jobs(
                limit=args.limit,
                offset=args.offset,
                queue=args.queue
            )
            
            if args.json:
                print(json.dumps(failed_jobs, indent=2, default=str))
            else:
                if not failed_jobs:
                    print("No failed jobs found.")
                    return
                
                print("Failed Jobs:")
                print("=" * 80)
                
                for job in failed_jobs:
                    print(f"ID: {job['id']}")
                    print(f"UUID: {job['uuid']}")
                    print(f"Queue: {job['queue']}")
                    print(f"Job Class: {job['job_class']}")
                    print(f"Failed At: {job['failed_at']}")
                    print(f"Attempts: {job['attempts']}")
                    print(f"Exception: {job['exception'][:100]}...")
                    print("-" * 80)
        
        elif args.action == 'retry':
            new_job_id = queue_service.retry_failed_job(args.job_id, args.queue)
            print(f"Failed job {args.job_id} retried as job {new_job_id}")
        
        elif args.action == 'retry-all':
            if not args.confirm:
                queue_filter = f" in queue '{args.queue}'" if args.queue else ""
                response = input(f"Retry all failed jobs{queue_filter}? [y/N]: ")
                if response.lower() != 'y':
                    print("Operation cancelled.")
                    return
            
            count = queue_service.retry_all_failed_jobs(args.queue)
            print(f"Retried {count} failed jobs.")
        
        elif args.action == 'delete':
            if not args.confirm:
                response = input(f"Delete failed job {args.job_id}? [y/N]: ")
                if response.lower() != 'y':
                    print("Operation cancelled.")
                    return
            
            if queue_service.delete_failed_job(args.job_id):
                print(f"Failed job {args.job_id} deleted.")
            else:
                print(f"Failed job {args.job_id} not found.")
        
        elif args.action == 'clear':
            if not args.confirm:
                queue_filter = f" in queue '{args.queue}'" if args.queue else ""
                response = input(f"Clear all failed jobs{queue_filter}? [y/N]: ")
                if response.lower() != 'y':
                    print("Operation cancelled.")
                    return
            
            count = queue_service.clear_failed_jobs(args.queue)
            print(f"Cleared {count} failed jobs.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def queue_release_command() -> None:
    """Release reserved jobs that have timed out."""
    parser = argparse.ArgumentParser(description='Release timed out reserved jobs')
    parser.add_argument('--timeout', type=int, default=3600, help='Timeout in seconds (default: 1 hour)')
    parser.add_argument('--connection', default='default', help='Database connection')
    
    args = parser.parse_args()
    
    try:
        queue_service = QueueService(args.connection)
        count = queue_service.release_reserved_jobs(args.timeout)
        print(f"Released {count} timed out reserved jobs.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main command dispatcher."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.Commands.QueueManagementCommand <command>")
        print("")
        print("Available commands:")
        print("  stats       - Show queue statistics")
        print("  clear       - Clear jobs from queue")
        print("  failed      - Manage failed jobs")
        print("  release     - Release timed out reserved jobs")
        return
    
    command = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove command from argv
    
    if command == 'stats':
        queue_stats_command()
    elif command == 'clear':
        queue_clear_command()
    elif command == 'failed':
        queue_failed_command()
    elif command == 'release':
        queue_release_command()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()