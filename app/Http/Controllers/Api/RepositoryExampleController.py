from __future__ import annotations

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.Http.Controllers.BaseController import BaseController
from app.Contracts.Repository.UserRepositoryInterface import UserRepositoryInterface
from app.Models.User import User
from app.Database.Connections.Connection import get_db
from app.Http.Resources.UserResource import UserResource


class RepositoryExampleController(BaseController):
    """
    Controller demonstrating Repository Pattern usage in FastAPI endpoints.
    
    This controller shows how to use repositories with dependency injection
    in real FastAPI route handlers.
    """
    
    def __init__(self, user_repository: UserRepositoryInterface) -> None:
        super().__init__()
        self.user_repository = user_repository


# Create router and controller factory
router = APIRouter(prefix="/api/v1/repository-examples", tags=["Repository Examples"])


def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryInterface:
    """Dependency provider for UserRepository."""
    from app.Repository.UserRepository import UserRepository
    return UserRepository(db)


@router.get("/users", response_model=List[Dict[str, Any]])
async def get_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=100),
    active_only: bool = Query(False),
    verified_only: bool = Query(False),
    search: str = Query(None),
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> List[Dict[str, Any]]:
    """
    Get paginated users with filtering options.
    
    Demonstrates repository query building and pagination.
    """
    
    # Start with base query
    query_repo = user_repo.fresh_query()
    
    # Apply filters
    if active_only:
        query_repo = query_repo.where('is_active', '=', True)
    
    if verified_only:
        query_repo = query_repo.where('is_verified', '=', True)
    
    if search:
        query_repo = query_repo.where('name', 'ilike', f'%{search}%')
    
    # Get paginated results
    result = query_repo.paginate(page=page, per_page=per_page)
    
    # Transform users using resource
    users_data = [UserResource.make(user).serialize() for user in result['data']]
    
    return {
        'data': users_data,
        'pagination': result['pagination']
    }


@router.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_user(
    user_id: int,
    with_roles: bool = Query(False),
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Get a single user by ID.
    
    Demonstrates repository find operations and relationship loading.
    """
    
    if with_roles:
        # Load user with relationships
        user = (user_repo
               .with_relations(['roles', 'permissions'])
               .where('id', '=', user_id)
               .first())
    else:
        user = user_repo.find(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResource.make(user).serialize()


@router.get("/users/email/{email}", response_model=Dict[str, Any])
async def get_user_by_email(
    email: str,
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Find user by email address.
    
    Demonstrates custom repository methods.
    """
    
    user = user_repo.find_by_email(email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResource.make(user).serialize()


@router.get("/users/role/{role_name}", response_model=List[Dict[str, Any]])
async def get_users_by_role(
    role_name: str,
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> List[Dict[str, Any]]:
    """
    Get users with a specific role.
    
    Demonstrates relationship-based queries.
    """
    
    users = user_repo.find_users_with_role(role_name)
    
    return [UserResource.make(user).serialize() for user in users]


@router.get("/stats", response_model=Dict[str, Any])
async def get_user_statistics(
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Get comprehensive user statistics.
    
    Demonstrates repository analytics methods.
    """
    
    return user_repo.get_user_statistics()


@router.post("/users", response_model=Dict[str, Any])
async def create_user(
    user_data: Dict[str, Any],
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Create a new user.
    
    Demonstrates repository creation operations.
    """
    
    # Basic validation
    required_fields = ['name', 'email']
    for field in required_fields:
        if field not in user_data:
            raise HTTPException(
                status_code=400, 
                detail=f"Field '{field}' is required"
            )
    
    # Check if email already exists
    existing_user = user_repo.find_by_email(user_data['email'])
    if existing_user:
        raise HTTPException(
            status_code=409, 
            detail="Email already exists"
        )
    
    # Set defaults
    user_data.setdefault('is_active', True)
    user_data.setdefault('is_verified', False)
    
    # Create user
    user = user_repo.create(user_data)
    
    return {
        'message': 'User created successfully',
        'user': UserResource.make(user).serialize()
    }


@router.put("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(
    user_id: int,
    user_data: Dict[str, Any],
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Update an existing user.
    
    Demonstrates repository update operations.
    """
    
    # Check if user exists
    user = user_repo.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user
    updated_user = user_repo.update(user_id, user_data)
    
    return {
        'message': 'User updated successfully',
        'user': UserResource.make(updated_user).serialize()
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, str]:
    """
    Delete a user.
    
    Demonstrates repository deletion operations.
    """
    
    success = user_repo.delete(user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {'message': 'User deleted successfully'}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Activate a user account.
    
    Demonstrates custom repository methods.
    """
    
    try:
        user = user_repo.activate_user(user_id)
        return {
            'message': 'User activated successfully',
            'user': UserResource.make(user).serialize()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/verify")
async def verify_user(
    user_id: int,
    user_repo: UserRepositoryInterface = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Verify a user account.
    
    Demonstrates custom repository methods.
    """
    
    try:
        user = user_repo.verify_user(user_id)
        return {
            'message': 'User verified successfully',
            'user': UserResource.make(user).serialize()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))