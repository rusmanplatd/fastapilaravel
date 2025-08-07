from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from typing_extensions import Annotated

from app.Http.Controllers import get_current_user
from app.Http.Schemas import UserResponse, UpdateProfileRequest
from app.Models import User
from app.Services import AuthService
from config import get_database

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/me", response_model=dict)
async def get_current_user_profile(current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, Any]:
    user_response = UserResponse.model_validate(current_user)
    return {
        "success": True,
        "message": "User profile retrieved successfully",
        "data": user_response,
        "status_code": 200
    }


@user_router.put("/me", response_model=dict)
async def update_current_user_profile(
    profile_data: UpdateProfileRequest,
    db: Annotated[Session, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict[str, Any]:
    auth_service = AuthService(db)
    
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.email is not None:
        update_data["email"] = profile_data.email
    
    success, message, updated_user = auth_service.update_profile(current_user, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": message
            }
        )
    
    user_response = UserResponse.model_validate(updated_user)
    return {
        "success": True,
        "message": message,
        "data": user_response,
        "status_code": 200
    }


@user_router.delete("/me", response_model=dict)
async def deactivate_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict[str, Any]:
    try:
        current_user.is_active = False
        db.commit()
        db.refresh(current_user)
        
        return {
            "success": True,
            "message": "User account deactivated successfully",
            "data": None,
            "status_code": 200
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Failed to deactivate account: {str(e)}"
            }
        )


@user_router.get("/profile/{user_id}", response_model=dict)
async def get_user_profile_by_id(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict[str, Any]:
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "User not found"
            }
        )
    
    # Return only public information
    public_user_data = {
        "id": user.id,
        "name": user.name,
        "is_verified": user.is_verified,
        "created_at": user.created_at
    }
    
    return {
        "success": True,
        "message": "User profile retrieved successfully",
        "data": public_user_data,
        "status_code": 200
    }