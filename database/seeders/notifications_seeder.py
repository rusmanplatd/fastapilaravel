from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database.migrations.create_users_table import User
from app.Notifications.Examples.WelcomeNotification import WelcomeNotification
from app.Notifications.Examples.OrderShippedNotification import OrderShippedNotification
from app.Notifications.Examples.SystemMaintenanceNotification import SystemMaintenanceNotification
from app.Notifications.Examples.SecurityAlertNotification import SecurityAlertNotification
from app.Notifications.Examples.MarketingCampaignNotification import MarketingCampaignNotification
from app.Notifications.Examples.TaskAssignmentNotification import TaskAssignmentNotification


def seed_example_notifications(db: Session) -> None:
    """Seed example notifications for testing purposes."""
    print("Seeding example notifications...")
    
    # Get the first user for examples
    user = db.query(User).first()
    if not user:
        print("No users found. Please run user seeder first.")
        return
    
    # Send a welcome notification
    welcome_notification = WelcomeNotification(user.name)
    user.notify(welcome_notification, db)
    print(f"✓ Sent welcome notification to {user.email}")
    
    # Send an order shipped notification
    order_notification = OrderShippedNotification(
        order_id="ORD-12345",
        tracking_number="1Z999AA1234567890",
        delivery_date="December 15, 2024"
    )
    user.notify(order_notification, db)
    print(f"✓ Sent order shipped notification to {user.email}")
    
    # Send a system maintenance notification
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=2)
    maintenance_notification = SystemMaintenanceNotification(
        start_time=start_time,
        end_time=end_time,
        description="We will be upgrading our servers to improve performance and security."
    )
    user.notify(maintenance_notification, db)
    print(f"✓ Sent system maintenance notification to {user.email}")
    
    print("Example notifications seeded successfully!")


if __name__ == "__main__":
    from config.database import SessionLocal
    
    db = SessionLocal()
    try:
        seed_example_notifications(db)
    finally:
        db.close()