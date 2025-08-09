from __future__ import annotations

import time
import random
from typing import Dict, Any, List

from app.Jobs.Job import Job, JobRetryException, JobFailedException


class ProcessImageJob(Job):
    """
    Example job for processing images.
    Demonstrates job retry logic and failure handling.
    """
    
    def __init__(self, image_path: str, operations: List[str]) -> None:
        super().__init__()
        self.image_path = image_path
        self.operations = operations
        
        # Configure job options
        self.options.queue = "images"
        self.options.max_attempts = 3
        self.options.timeout = 300  # 5 minutes
        self.options.priority = 5  # Higher priority than default
        self.options.tags = ["image", "processing"]
    
    def handle(self) -> None:
        """Process the image."""
        print(f"Processing image: {self.image_path}")
        print(f"Operations: {', '.join(self.operations)}")
        
        # Simulate processing time
        processing_time = random.randint(5, 15)
        print(f"Processing will take {processing_time} seconds...")
        
        for i in range(processing_time):
            time.sleep(1)
            
            # Simulate random failures for demonstration
            if random.random() < 0.1:  # 10% chance of failure
                if self.attempts < 2:
                    # Retry with exponential backoff
                    delay = 60 * (2 ** (self.attempts - 1))  # 1min, 2min, etc.
                    raise JobRetryException(f"Network timeout during processing", delay)
                else:
                    # Permanent failure after max attempts
                    raise JobFailedException("Image processing failed after maximum attempts")
            
            print(f"Processing... {((i + 1) / processing_time * 100):.0f}% complete")
        
        print(f"Image {self.image_path} processed successfully!")
        
        # Here you would actually process the image:
        # - Resize, crop, apply filters, etc.
        # - Save processed versions
        # - Update database records
        # - Generate thumbnails
    
    def failed(self, exception: Exception) -> None:
        """Handle image processing failure."""
        print(f"Image processing failed for {self.image_path}: {str(exception)}")
        
        # Could clean up temporary files, send notifications, etc.
        print("Cleaning up temporary files...")
    
    def get_display_name(self) -> str:
        """Custom display name for the job."""
        return f"Process image: {self.image_path}"
    
    def get_tags(self) -> List[str]:
        """Dynamic tags based on operations."""
        tags = ["image", "processing"]
        tags.extend(self.operations)
        return tags
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job data for storage."""
        data = super().serialize()
        data["data"] = {
            "image_path": self.image_path,
            "operations": self.operations
        }
        return data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ProcessImageJob:
        """Deserialize job from stored data."""
        job_data = data.get("data", {})
        job = cls(
            image_path=job_data["image_path"],
            operations=job_data["operations"]
        )
        
        # Restore options
        if "options" in data:
            options_data = data["options"]
            job.options.queue = options_data.get("queue", "images")
            job.options.max_attempts = options_data.get("max_attempts", 3)
            job.options.timeout = options_data.get("timeout", 300)
            job.options.priority = options_data.get("priority", 5)
        
        return job