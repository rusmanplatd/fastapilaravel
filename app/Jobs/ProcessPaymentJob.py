from __future__ import annotations

from typing import Any
from app.Jobs.Job import Job


class ProcessPaymentJob(Job):
    """
    Asynchronous job for processing payment transactions.
    """
    
    def __init__(self, payment_id: int, amount: float, currency: str = "USD") -> None:
        """Initialize the job with payment data."""
        super().__init__()
        
        # Store job data
        self.payment_id = payment_id
        self.amount = amount
        self.currency = currency
        
        # Set job options
        self.options.queue = "payments"  # Queue name
        self.options.delay = 0  # Delay in seconds
        self.options.timeout = 120  # Timeout in seconds (longer for payments)
        self.options.max_attempts = 3  # Maximum attempts
    
    def handle(self) -> None:
        """Execute the payment processing."""
        print(f"Processing payment {self.payment_id} for {self.amount} {self.currency}")
        
        try:
            # Simulate payment gateway API call
            import time
            import random
            
            # Simulate processing time
            time.sleep(2)
            
            # Simulate random success/failure for demo
            if random.random() > 0.1:  # 90% success rate
                self._process_successful_payment()
            else:
                raise Exception("Payment gateway timeout")
                
        except Exception as e:
            print(f"Payment {self.payment_id} failed: {e}")
            raise  # Re-raise to trigger failure handling
    
    def _process_successful_payment(self) -> None:
        """Handle successful payment processing."""
        # Update payment status in database
        # Send confirmation email
        # Update user account balance
        print(f"Payment {self.payment_id} processed successfully")
    
    def serialize(self) -> dict[str, Any]:
        """Serialize job data for storage."""
        data = super().serialize()
        data["data"] = {
            "payment_id": self.payment_id,
            "amount": self.amount,
            "currency": self.currency
        }
        return data
    
    def failed(self, exception: Exception) -> None:
        """Handle job failure."""
        # Clean up resources, send notifications, etc.
        print(f"Job failed: {exception}")
    
    def __repr__(self) -> str:
        """String representation of the job."""
        return f"ProcessPaymentJob()"
