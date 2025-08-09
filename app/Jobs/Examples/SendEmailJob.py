from __future__ import annotations

import time
from typing import Dict, Any

from app.Jobs.Job import Job


class SendEmailJob(Job):
    """
    Example job for sending emails.
    Demonstrates a simple job with parameters.
    """
    
    def __init__(self, to_email: str, subject: str, body: str) -> None:
        super().__init__()
        self.to_email = to_email
        self.subject = subject
        self.body = body
        
        # Configure job options
        self.options.queue = "emails"
        self.options.max_attempts = 5
        self.options.timeout = 120  # 2 minutes
        self.options.tags = ["email", "notification"]
    
    def handle(self) -> None:
        """Send the email."""
        print(f"Sending email to: {self.to_email}")
        print(f"Subject: {self.subject}")
        print(f"Body: {self.body[:100]}...")
        
        # Simulate email sending delay
        time.sleep(2)
        
        # Here you would integrate with your email service
        # For example: SendGrid, AWS SES, etc.
        print(f"Email sent successfully to {self.to_email}")
    
    def failed(self, exception: Exception) -> None:
        """Handle email sending failure."""
        print(f"Failed to send email to {self.to_email}: {str(exception)}")
        
        # Here you could log to a monitoring service,
        # send admin notification, etc.
    
    def get_display_name(self) -> str:
        """Custom display name for the job."""
        return f"Send email to {self.to_email}"
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job data for storage."""
        data = super().serialize()
        data["data"] = {
            "to_email": self.to_email,
            "subject": self.subject,
            "body": self.body
        }
        return data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> SendEmailJob:
        """Deserialize job from stored data."""
        job_data = data.get("data", {})
        job = cls(
            to_email=job_data["to_email"],
            subject=job_data["subject"],
            body=job_data["body"]
        )
        
        # Restore options
        if "options" in data:
            options_data = data["options"]
            job.options.queue = options_data.get("queue", "emails")
            job.options.max_attempts = options_data.get("max_attempts", 5)
            job.options.timeout = options_data.get("timeout", 120)
            job.options.tags = options_data.get("tags", ["email", "notification"])
        
        return job