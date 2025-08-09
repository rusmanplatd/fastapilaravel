from __future__ import annotations

import sys
import logging
import argparse
from typing import Optional

from app.Queue.Worker import QueueWorker, WorkerOptions


def setup_logging(level: str = "INFO") -> None:
    """Setup logging for queue worker."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('storage/logs/queue.log', mode='a')
        ]
    )


def queue_work_command() -> None:
    """Command to start a queue worker."""
    parser = argparse.ArgumentParser(description='Start a queue worker')
    
    parser.add_argument('--queue', default='default', help='Queue to process')
    parser.add_argument('--connection', default='default', help='Database connection')
    parser.add_argument('--name', default='default', help='Worker name')
    parser.add_argument('--delay', type=int, default=0, help='Delay when no jobs (seconds)')
    parser.add_argument('--sleep', type=int, default=3, help='Sleep duration when idle (seconds)')
    parser.add_argument('--timeout', type=int, default=60, help='Job timeout (seconds)')
    parser.add_argument('--max-jobs', type=int, default=0, help='Maximum jobs to process (0 = unlimited)')
    parser.add_argument('--max-time', type=int, default=0, help='Maximum time to run (0 = unlimited)')
    parser.add_argument('--memory', type=int, default=128, help='Memory limit (MB)')
    parser.add_argument('--rest', type=int, default=0, help='Microseconds to rest between jobs')
    parser.add_argument('--force', action='store_true', help='Force worker to run')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create worker options
    options = WorkerOptions(
        name=args.name,
        connection=args.connection,
        queue=args.queue,
        delay=args.delay,
        sleep=args.sleep,
        max_jobs=args.max_jobs,
        max_time=args.max_time,
        memory_limit=args.memory,
        timeout=args.timeout,
        rest=args.rest,
        force=args.force
    )
    
    # Start worker
    worker = QueueWorker(options)
    
    try:
        print(f"Starting queue worker '{args.name}' on queue '{args.queue}'...")
        print("Press Ctrl+C to stop the worker gracefully")
        worker.work()
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
    except Exception as e:
        print(f"Worker error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    queue_work_command()