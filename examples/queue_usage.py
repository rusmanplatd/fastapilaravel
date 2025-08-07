#!/usr/bin/env python3
"""
Example usage of the Queue system.
This file demonstrates how to dispatch jobs and work with the queue.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.Jobs.Examples.SendEmailJob import SendEmailJob
from app.Jobs.Examples.ProcessImageJob import ProcessImageJob
from app.Jobs.Examples.SendNotificationJob import SendNotificationJob
from app.Services.QueueService import QueueService


def dispatch_jobs_example() -> None:
    """Example of dispatching various jobs to the queue."""
    print("Dispatching Jobs Example")
    print("=" * 50)
    
    # Dispatch email job
    email_job_id = SendEmailJob.dispatch(
        to_email="user@example.com",
        subject="Welcome to our platform!",
        body="Thanks for signing up. We're excited to have you on board."
    )
    print(f"Dispatched email job: {email_job_id}")
    
    # Dispatch image processing job with delay
    image_job = ProcessImageJob(
        image_path="/uploads/photo123.jpg",
        operations=["resize", "crop", "watermark"]
    ).delay_until(30)  # Delay by 30 seconds
    
    image_job_id = image_job.dispatch()
    print(f"Dispatched delayed image processing job: {image_job_id}")
    
    # Dispatch notification job to high-priority queue
    notification_job = SendNotificationJob(
        user_id="user123",
        notification_type="welcome",
        data={"username": "john_doe"}
    ).on_queue("high-priority").with_priority(10)
    
    notification_job_id = notification_job.dispatch()
    print(f"Dispatched high-priority notification job: {notification_job_id}")
    
    # Dispatch multiple jobs at once
    bulk_jobs = [
        SendEmailJob("user1@example.com", "Monthly Newsletter", "Here's your monthly update..."),
        SendEmailJob("user2@example.com", "Monthly Newsletter", "Here's your monthly update..."),
        SendEmailJob("user3@example.com", "Monthly Newsletter", "Here's your monthly update...")
    ]
    
    queue_service = QueueService()
    bulk_job_ids = queue_service.bulk(bulk_jobs, "newsletters")
    print(f"Dispatched {len(bulk_job_ids)} newsletter jobs: {', '.join(bulk_job_ids)}")


def conditional_dispatch_example() -> None:
    """Example of conditional job dispatching."""
    print("\nConditional Dispatch Example")
    print("=" * 50)
    
    # Dispatch only if condition is met
    user_is_premium = True
    job_id = SendEmailJob.dispatch_if(
        user_is_premium,
        to_email="premium@example.com",
        subject="Premium Feature Available",
        body="Check out this new premium feature!"
    )
    
    if job_id:
        print(f"Premium email job dispatched: {job_id}")
    else:
        print("Premium email not dispatched (user not premium)")
    
    # Dispatch unless condition is met
    maintenance_mode = False
    job_id = ProcessImageJob.dispatch_unless(
        maintenance_mode,
        image_path="/uploads/batch_process.jpg",
        operations=["optimize", "generate_thumbnails"]
    )
    
    if job_id:
        print(f"Image processing job dispatched: {job_id}")
    else:
        print("Image processing not dispatched (maintenance mode)")


def immediate_execution_example() -> None:
    """Example of immediate job execution (no queue)."""
    print("\nImmediate Execution Example")
    print("=" * 50)
    
    # Execute job immediately without queuing
    print("Executing email job immediately...")
    SendEmailJob.dispatch_now(
        to_email="urgent@example.com",
        subject="Urgent Notification",
        body="This needs to be sent immediately!"
    )
    print("Email job completed immediately")


def queue_management_example() -> None:
    """Example of queue management operations."""
    print("\nQueue Management Example")
    print("=" * 50)
    
    queue_service = QueueService()
    
    # Get queue statistics
    stats = queue_service.get_queue_stats()
    print("Queue Statistics:")
    for queue_name, queue_stats in stats["queues"].items():
        print(f"  {queue_name}: {queue_stats['total']} jobs ({queue_stats['pending']} pending)")
    
    # Get jobs from specific queue
    jobs = queue_service.get_jobs("emails", limit=5)
    print(f"\nFirst 5 jobs in 'emails' queue:")
    for job in jobs:
        print(f"  Job {job['id']}: {job['job_class']} (Priority: {job['priority']})")
    
    # Get failed jobs
    failed_jobs = queue_service.get_failed_jobs(limit=3)
    print(f"\nFirst 3 failed jobs:")
    for job in failed_jobs:
        print(f"  Failed Job {job['id']}: {job['job_class']} - {job['exception'][:50]}...")


def job_chaining_example() -> None:
    """Example of job chaining using delay."""
    print("\nJob Chaining Example")
    print("=" * 50)
    
    # Chain jobs with delays to create a workflow
    
    # Step 1: Process image immediately
    process_job_id = ProcessImageJob.dispatch(
        image_path="/uploads/product_photo.jpg",
        operations=["resize", "optimize"]
    )
    print(f"Step 1 - Image processing job: {process_job_id}")
    
    # Step 2: Send notification after 1 minute (assuming processing takes < 1 min)
    notification_job = SendNotificationJob(
        user_id="photographer123",
        notification_type="processing_complete",
        data={"image_path": "/uploads/product_photo.jpg"}
    ).delay_until(60)
    
    notification_job_id = notification_job.dispatch()
    print(f"Step 2 - Delayed notification job: {notification_job_id}")
    
    # Step 3: Send email after 2 minutes
    email_job = SendEmailJob(
        to_email="admin@example.com",
        subject="Image Processing Complete",
        body="The product photo has been processed and user notified."
    ).delay_until(120)
    
    email_job_id = email_job.dispatch()
    print(f"Step 3 - Delayed admin email job: {email_job_id}")


if __name__ == "__main__":
    print("Queue System Usage Examples")
    print("=" * 70)
    
    try:
        dispatch_jobs_example()
        conditional_dispatch_example()
        immediate_execution_example()
        queue_management_example()
        job_chaining_example()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("\nTo process these jobs, run:")
        print("  python -m app.Commands.QueueWorkerCommand --queue default")
        print("  python -m app.Commands.QueueWorkerCommand --queue emails")
        print("  python -m app.Commands.QueueWorkerCommand --queue notifications")
        
    except Exception as e:
        print(f"Error running examples: {str(e)}")
        sys.exit(1)