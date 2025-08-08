"""
Example usage of Laravel-style features in FastAPI Laravel.

This file demonstrates how to use the various Laravel-inspired features
that have been implemented in this FastAPI application.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

# Import Laravel-style features
from app.Http.Requests.CreateUserRequest import CreateUserRequest
from app.Http.Resources.UserResource import UserResource
from app.Events.UserRegistered import UserRegistered
from app.Events import dispatch
from app.Mail.WelcomeMail import WelcomeMail
from app.Mail import mail_manager
from app.Support.Collection import collect
from app.Cache import cache_manager
from app.Storage import storage
from app.Policies.UserPolicy import UserPolicy
from app.Policies import gate, can, authorize
from app.RateLimiting import throttle
from app.Broadcasting import broadcast
from app.Support.Pipeline import pipeline
from database.factories.UserFactory import UserFactory
from database.migrations.create_users_table import User
from config.database import get_db

# Router instance
router = APIRouter()


# Example 1: Form Request Validation
@router.post("/users", status_code=201)
async def create_user(
    request: Request,
    create_request: CreateUserRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create user with Laravel-style form request validation."""
    
    # The CreateUserRequest automatically validates and authorizes
    validated_data = create_request.dict()
    
    # Create user (in real app, you'd use a service)
    user = User(**validated_data)
    db.add(user)
    db.commit()
    
    # Dispatch event
    await dispatch(UserRegistered(user))
    
    # Return resource
    return UserResource(user).to_response()


# Example 2: Rate Limiting
@router.get("/limited-endpoint")
@throttle(max_attempts=10, decay_minutes=1)
async def limited_endpoint(request: Request) -> Dict[str, Any]:
    """Endpoint with rate limiting."""
    return {"message": "This endpoint is rate limited"}


# Example 3: Cache Usage
@router.get("/cached-data")
async def get_cached_data() -> Dict[str, Any]:
    """Example of cache usage."""
    
    def expensive_operation() -> Dict[str, Any]:
        # Simulate expensive operation
        import time
        time.sleep(0.1)
        return {"computed_value": 42, "timestamp": time.time()}
    
    # Cache for 5 minutes
    data = cache_manager.remember("expensive_data", 300, expensive_operation)
    return {"data": data}


# Example 4: Storage Usage
@router.post("/upload")
async def upload_file(request: Request) -> Dict[str, Any]:
    """Example file upload with storage."""
    # In real app, you'd handle multipart form data
    content = "Sample file content"
    filename = "example.txt"
    
    # Store file
    success = storage().put(f"uploads/{filename}", content)
    
    if success:
        return {"message": "File uploaded successfully", "path": f"uploads/{filename}"}
    else:
        return {"message": "Upload failed"}


# Example 5: Collections
@router.get("/users/analytics")
async def user_analytics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Example using collections for data processing."""
    
    # Get users (simplified)
    users = db.query(User).all()
    
    # Use Laravel-style collection
    user_collection = collect(users)
    
    analytics = {
        "total_users": user_collection.count(),
        "active_users": user_collection.filter(lambda u: u.is_active).count(),
        "verified_users": user_collection.filter(lambda u: u.is_verified).count(),
        "domains": user_collection.pluck("email").map(lambda email: email.split("@")[1] if "@" in email else "unknown").unique().all(),
        "recent_users": user_collection.sort_by("created_at", reverse=True).take(5).pluck("name").all()
    }
    
    return {"analytics": analytics}


# Example 6: Broadcasting
@router.post("/broadcast")
async def broadcast_event(request: Request) -> Dict[str, Any]:
    """Example broadcasting."""
    
    # Broadcast to channels
    await broadcast(
        channels=["notifications", "admin-channel"],
        event="UserAction",
        data={
            "message": "Something happened!",
            "timestamp": time.time(),
            "user_id": "example_user_id"
        }
    )
    
    return {"message": "Event broadcasted"}


# Example 7: Pipeline Usage
@router.post("/process-data")
async def process_data(request: Request) -> Dict[str, Any]:
    """Example data processing pipeline."""
    
    data = {"value": 10}
    
    def add_ten(data: Dict[str, Any], next_step: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        data["value"] += 10
        return next_step(data)
    
    def multiply_by_two(data: Dict[str, Any], next_step: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        data["value"] *= 2
        return next_step(data)
    
    def add_timestamp(data: Dict[str, Any], next_step: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        data["processed_at"] = time.time()
        return next_step(data)
    
    # Process through pipeline
    result = pipeline(data).through([
        add_ten,
        multiply_by_two,
        add_timestamp
    ]).then_return()
    
    return {"processed_data": result}


# Example 8: Authorization with Policies
@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get user with policy authorization."""
    
    # Get users
    current_user = getattr(request.state, 'user', None)
    target_user = db.query(User).filter(User.id == user_id).first()
    
    if not target_user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check authorization using policy
    if current_user:
        authorize(current_user, "view", target_user)
    
    # Return user resource
    return UserResource(target_user).to_response()


# Example 9: Database Factory Usage (for testing)
def create_test_users() -> Dict[str, Any]:
    """Example factory usage for testing."""
    
    # Create single user
    user = UserFactory().make()
    
    # Create multiple users
    users = UserFactory().times(5).make()
    
    # Create with specific state
    admin = UserFactory().admin().make()
    verified_users = UserFactory().verified().times(3).make()
    
    return {
        "single_user": user.to_dict() if hasattr(user, 'to_dict') else str(user),
        "multiple_users": [u.to_dict() if hasattr(u, 'to_dict') else str(u) for u in users] if isinstance(users, list) else [str(users)],
        "admin": admin.to_dict() if hasattr(admin, 'to_dict') else str(admin),
        "verified_users": [u.to_dict() if hasattr(u, 'to_dict') else str(u) for u in verified_users] if isinstance(verified_users, list) else [str(verified_users)]
    }


# Example 10: Mail Usage
@router.post("/send-welcome-email")
async def send_welcome_email(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Send welcome email using Laravel-style mailable."""
    
    # Get user (simplified)
    user = db.query(User).first()
    if not user:
        return {"message": "No users found"}
    
    # Create and send email
    mail = WelcomeMail(user)
    mail.to(user.email)
    
    # Send immediately
    success = mail_manager.send(mail)
    
    # Or queue for later
    # job_id = mail_manager.queue(mail)
    
    return {"message": "Welcome email sent" if success else "Failed to send email"}


# Register policies
gate.policy(User, UserPolicy)

# Register custom abilities
gate.define("manage_system", lambda user: user.has_role("admin"))
gate.define("view_analytics", lambda user: user.can("view_users") or user.has_role("manager"))

import time