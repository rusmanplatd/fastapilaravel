from __future__ import annotations

"""
Laravel-style Authorization Example for FastAPI Laravel

This example demonstrates how to use the authorization system
with Gates, Policies, and Middleware.
"""

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Authorization imports
from app.Auth.Gate import gate_instance, authorize_route, for_user
from app.Policies.PostPolicy import PostPolicy
from app.Http.Middleware.AuthorizationMiddleware import (
    AuthorizationMiddleware, 
    authorize, 
    require_abilities, 
    require_roles, 
    admin_only,
    authorize_resource
)
from app.Models.Post import Post
from app.Models.User import User

# Create FastAPI app
app = FastAPI(
    title="FastAPI Laravel - Authorization Example",
    description="Demonstrates Laravel-style authorization with Gates and Policies",
    version="1.0.0"
)

# Add authorization middleware
app.add_middleware(AuthorizationMiddleware)

# Register policies with the gate
gate_instance.policy(Post, PostPolicy)

# Define custom abilities
gate_instance.define('view_dashboard', lambda user: user and user.is_admin)
gate_instance.define('manage_users', lambda user: user and user.can('manage_users'))

# Example routes with different authorization patterns


@app.get("/dashboard")
@require_abilities("view_dashboard")
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """
    Dashboard route requiring specific ability.
    Only users with 'view_dashboard' ability can access.
    """
    return {
        "message": "Welcome to the admin dashboard",
        "user": current_user.name,
        "stats": {
            "total_posts": 150,
            "total_users": 25,
            "total_comments": 89
        }
    }


@app.get("/admin/users")
@admin_only()
async def admin_users(request: Request, current_user: User = Depends(get_current_user)):
    """
    Admin-only route using role-based authorization.
    """
    return {
        "message": "Admin users management",
        "users": [
            {"id": 1, "name": "John Doe", "role": "admin"},
            {"id": 2, "name": "Jane Smith", "role": "user"}
        ]
    }


@app.post("/posts")
@authorize(abilities=["create_posts"])
async def create_post(
    request: Request,
    post_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create post with authorization check.
    Uses gate to verify 'create_posts' ability.
    """
    # The middleware already checked the ability, so we can proceed
    
    # Additional business logic authorization using policy
    if not gate_instance.allows('create', user=current_user):
        raise HTTPException(status_code=403, detail="Cannot create posts")
    
    # Create the post
    post = Post(
        title=post_data['title'],
        content=post_data['content'],
        author_id=current_user.id
    )
    db.add(post)
    db.commit()
    
    return {
        "message": "Post created successfully",
        "post": {
            "id": post.id,
            "title": post.title,
            "author": current_user.name
        }
    }


@app.get("/posts/{post_id}")
@authorize_resource(Post, ability="view", param="post_id")
async def view_post(
    post_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View post with resource-based authorization.
    The middleware automatically loads the post and checks the 'view' ability.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    
    return {
        "post": {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "is_published": post.is_published,
            "author_id": post.author_id
        }
    }


@app.put("/posts/{post_id}")
async def update_post(
    post_id: str,
    post_data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update post with manual authorization check.
    Demonstrates using the gate directly in the controller.
    """
    # Load the post
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization using gate
    gate_instance.authorize('update', post, user=current_user)
    
    # Update the post
    for key, value in post_data.items():
        if hasattr(post, key):
            setattr(post, key, value)
    
    db.commit()
    
    return {
        "message": "Post updated successfully",
        "post": {
            "id": post.id,
            "title": post.title,
            "updated_by": current_user.name
        }
    }


@app.put("/posts/{post_id}/publish")
async def publish_post(
    post_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Publish post with custom ability authorization.
    Uses the PostPolicy.publish method.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user can publish this post
    if not gate_instance.allows('publish', post, user=current_user):
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to publish this post"
        )
    
    # Publish the post
    post.publish()
    db.commit()
    
    return {
        "message": "Post published successfully",
        "post": {
            "id": post.id,
            "title": post.title,
            "is_published": post.is_published,
            "published_at": post.published_at.isoformat()
        }
    }


@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete post with gate authorization.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Use gate for authorization
    gate_instance.authorize('delete', post, user=current_user)
    
    db.delete(post)
    db.commit()
    
    return {"message": "Post deleted successfully"}


# Example of using user-specific gate
@app.get("/my-abilities")
async def my_abilities(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Show what abilities the current user has.
    Demonstrates using user-specific gate.
    """
    user_gate = for_user(current_user)
    
    abilities_to_check = [
        'create_posts',
        'edit_posts', 
        'delete_posts',
        'publish_posts',
        'view_dashboard',
        'manage_users'
    ]
    
    abilities = {}
    for ability in abilities_to_check:
        abilities[ability] = user_gate.allows(ability)
    
    return {
        "user": current_user.name,
        "abilities": abilities
    }


# Example of checking multiple abilities
@app.get("/content-management")
async def content_management(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Content management page requiring multiple abilities.
    """
    user_gate = for_user(current_user)
    
    # Check if user has any content management abilities
    if not user_gate.any(['create_posts', 'edit_posts', 'delete_posts']):
        raise HTTPException(
            status_code=403, 
            detail="You don't have any content management permissions"
        )
    
    # Get posts the user can manage
    manageable_posts = []
    
    # This would typically be a database query
    # For demo purposes, we'll simulate some posts
    sample_posts = [
        Post(id=1, title="Post 1", author_id=current_user.id),
        Post(id=2, title="Post 2", author_id=999),  # Different author
    ]
    
    for post in sample_posts:
        post_abilities = {
            'can_view': user_gate.allows('view', post),
            'can_edit': user_gate.allows('update', post),
            'can_delete': user_gate.allows('delete', post),
            'can_publish': user_gate.allows('publish', post)
        }
        
        manageable_posts.append({
            'id': post.id,
            'title': post.title,
            'abilities': post_abilities
        })
    
    return {
        "message": "Content management dashboard",
        "posts": manageable_posts
    }


# Authorization with before/after hooks example
@app.post("/posts/{post_id}/comments")
async def create_comment(
    post_id: str,
    comment_data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create comment with policy-based authorization.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user can comment on this post
    if not gate_instance.allows('comment', post, user=current_user):
        raise HTTPException(
            status_code=403,
            detail="You cannot comment on this post"
        )
    
    # Create comment (simplified)
    comment = {
        "id": "comment_123",
        "content": comment_data['content'],
        "author_id": current_user.id,
        "post_id": post.id
    }
    
    return {
        "message": "Comment created successfully",
        "comment": comment
    }


# Policy inspection endpoint
@app.get("/posts/{post_id}/policy-check")
async def check_post_policy(
    post_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check all policy methods for a post.
    Useful for debugging and understanding permissions.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    user_gate = for_user(current_user)
    
    # Check all standard abilities
    abilities = [
        'view', 'update', 'delete', 'restore', 'forceDelete',
        'publish', 'unpublish', 'feature', 'viewStats', 'comment', 'like'
    ]
    
    policy_results = {}
    for ability in abilities:
        try:
            response = gate_instance.inspect(ability, post, user=current_user)
            policy_results[ability] = {
                'allowed': response.allowed,
                'message': response.message
            }
        except Exception as e:
            policy_results[ability] = {
                'allowed': False,
                'message': str(e)
            }
    
    return {
        "post": {
            "id": post.id,
            "title": post.title,
            "author_id": post.author_id,
            "is_published": post.is_published
        },
        "user": {
            "id": current_user.id,
            "name": current_user.name
        },
        "policy_results": policy_results
    }


# Error handling for authorization
@app.exception_handler(HTTPException)
async def authorization_exception_handler(request: Request, exc: HTTPException):
    """
    Custom error handler for authorization failures.
    """
    if exc.status_code == 403:
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "AUTHORIZATION_FAILED",
                "suggestions": [
                    "Contact an administrator if you believe you should have access",
                    "Check your user permissions",
                    "Ensure you're logged in with the correct account"
                ]
            }
        )
    
    # Let other exceptions be handled normally
    raise exc


# Dependency functions (these would be in your actual app)
def get_current_user() -> User:
    """Get the current authenticated user (placeholder)."""
    # This would integrate with your authentication system
    return User(id=1, name="John Doe", email="john@example.com")


def get_db() -> Session:
    """Get database session (placeholder)."""
    # This would return your actual database session
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)