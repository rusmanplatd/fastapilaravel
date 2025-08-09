from __future__ import annotations

"""
Laravel Sanctum routes for SPA authentication and API token management.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.Sanctum import (
    Sanctum,
    require_sanctum_auth,
    require_abilities,
    optional_sanctum_auth,
    auth_sanctum,
    abilities,
)


# Router for Sanctum endpoints
router = APIRouter(prefix="/api/v1/auth", tags=["sanctum"])


# Request/Response models
class TokenCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Token name")
    abilities: List[str] = Field(default=['*'], description="Token abilities")
    expires_in_days: Optional[int] = Field(default=None, description="Token expiration in days")


class TokenResponse(BaseModel):
    id: int
    name: str
    abilities: List[str]
    plain_text_token: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    current_token: Optional[Dict[str, Any]] = None


class TokensListResponse(BaseModel):
    tokens: List[TokenResponse]
    total: int


# Authentication endpoints

@router.get("/user", response_model=UserResponse)
async def get_current_user(user=Depends(require_sanctum_auth)):
    """
    Get the currently authenticated user.
    
    Requires: Valid Sanctum token
    """
    current_token = None
    if hasattr(user, 'current_access_token') and user.current_access_token():
        token = user.current_access_token()
        current_token = {
            'id': token.id,
            'name': token.name,
            'abilities': token.get_abilities(),
            'last_used_at': token.last_used_at.isoformat() if token.last_used_at else None,
        }
    
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        current_token=current_token
    )


# Token management endpoints

@router.post("/tokens", response_model=TokenResponse)
@auth_sanctum
async def create_token(
    request: TokenCreateRequest,
    user,  # Injected by @auth_sanctum decorator
) -> TokenResponse:
    """
    Create a new personal access token.
    
    Requires: Valid Sanctum token with 'create-tokens' ability
    """
    # Check if user can create tokens
    if not user.token_can('create-tokens') and not user.token_can('*'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not have permission to create tokens"
        )
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Create the token
    new_token = user.create_token(
        name=request.name,
        abilities=request.abilities,
        expires_at=expires_at
    )
    
    return TokenResponse(
        id=new_token.access_token.id,
        name=new_token.access_token.name,
        abilities=new_token.access_token.get_abilities(),
        plain_text_token=new_token.plain_text_token,
        expires_at=new_token.access_token.expires_at.isoformat() if new_token.access_token.expires_at else None,
        created_at=new_token.access_token.created_at.isoformat() if new_token.access_token.created_at else None,
    )


@router.get("/tokens", response_model=TokensListResponse)
@abilities('view-tokens')  # Requires 'view-tokens' ability
async def list_tokens(user) -> TokensListResponse:
    """
    List all personal access tokens for the authenticated user.
    
    Requires: Valid Sanctum token with 'view-tokens' ability
    """
    tokens = user.tokens()
    
    token_responses = []
    for token in tokens:
        token_responses.append(TokenResponse(
            id=token.id,
            name=token.name,
            abilities=token.get_abilities(),
            expires_at=token.expires_at.isoformat() if token.expires_at else None,
            created_at=token.created_at.isoformat() if token.created_at else None,
        ))
    
    return TokensListResponse(
        tokens=token_responses,
        total=len(token_responses)
    )


@router.delete("/tokens/{token_id}")
@abilities('delete-tokens')  # Requires 'delete-tokens' ability
async def revoke_token(token_id: int, user) -> Dict[str, str]:
    """
    Revoke a specific personal access token.
    
    Requires: Valid Sanctum token with 'delete-tokens' ability
    """
    success = user.revoke_token(token_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found or could not be revoked"
        )
    
    return {"message": "Token revoked successfully"}


@router.delete("/tokens/current")
async def revoke_current_token(user=Depends(require_sanctum_auth)) -> Dict[str, str]:
    """
    Revoke the current access token.
    
    Requires: Valid Sanctum token
    """
    success = user.revoke_current_token()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not revoke current token"
        )
    
    return {"message": "Current token revoked successfully"}


@router.delete("/tokens")
@abilities('delete-tokens')  # Requires 'delete-tokens' ability  
async def revoke_all_tokens(user) -> Dict[str, Any]:
    """
    Revoke all personal access tokens for the authenticated user.
    
    Requires: Valid Sanctum token with 'delete-tokens' ability
    """
    revoked_count = user.revoke_all_tokens()
    
    return {
        "message": "All tokens revoked successfully",
        "revoked_count": revoked_count
    }


# Ability check endpoints

@router.get("/abilities")
async def get_token_abilities(user=Depends(require_sanctum_auth)) -> Dict[str, List[str]]:
    """
    Get the abilities of the current token.
    
    Requires: Valid Sanctum token
    """
    abilities = user.get_token_abilities()
    
    return {"abilities": abilities}


@router.post("/abilities/check")
async def check_abilities(
    abilities_to_check: List[str],
    user=Depends(require_sanctum_auth)
) -> Dict[str, Dict[str, bool]]:
    """
    Check if the current token has specific abilities.
    
    Requires: Valid Sanctum token
    """
    results = {}
    
    for ability in abilities_to_check:
        results[ability] = user.token_can(ability)
    
    return {"abilities": results}


# Protected resource examples

@router.get("/protected/basic")
async def basic_protected_route(user=Depends(require_sanctum_auth)) -> Dict[str, Any]:
    """
    Basic protected route - requires any valid token.
    
    Requires: Valid Sanctum token
    """
    return {
        "message": "Access granted to protected resource",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/protected/read-only")
async def read_only_protected_route(user=Depends(require_abilities('read'))) -> Dict[str, str]:
    """
    Read-only protected route - requires 'read' ability.
    
    Requires: Valid Sanctum token with 'read' ability
    """
    return {
        "message": "Access granted to read-only resource",
        "data": "Some read-only data here..."
    }


@router.post("/protected/write")
async def write_protected_route(
    data: Dict[str, Any],
    user=Depends(require_abilities('write'))
) -> Dict[str, str]:
    """
    Write protected route - requires 'write' ability.
    
    Requires: Valid Sanctum token with 'write' ability
    """
    return {
        "message": "Data written successfully",
        "received_data": data,
        "written_by": user.name
    }


@router.delete("/protected/admin")
async def admin_protected_route(user=Depends(require_abilities('admin'))) -> Dict[str, str]:
    """
    Admin protected route - requires 'admin' ability.
    
    Requires: Valid Sanctum token with 'admin' ability
    """
    return {
        "message": "Access granted to admin resource",
        "admin": user.name
    }


# Optional authentication example

@router.get("/optional")
async def optional_auth_route(user=Depends(optional_sanctum_auth)) -> Dict[str, Any]:
    """
    Route with optional authentication.
    
    Works with or without authentication, but provides different data.
    """
    if user:
        return {
            "message": "Authenticated access",
            "user": {
                "id": user.id,
                "name": user.name,
            },
            "authenticated": True
        }
    else:
        return {
            "message": "Anonymous access",
            "authenticated": False
        }


# Statistics endpoint

@router.get("/stats")
@abilities('admin')  # Requires admin ability
async def get_sanctum_stats(user) -> Dict[str, Any]:
    """
    Get Sanctum statistics and configuration.
    
    Requires: Valid Sanctum token with 'admin' ability
    """
    stats = await Sanctum.get_token_stats()
    config = Sanctum.get_config()
    
    return {
        "stats": stats,
        "config": {
            "prefix": config.get('prefix'),
            "header": config.get('header'),
            "spa_token_name": config.get('spa_token_name'),
        },
        "requested_by": user.name,
        "timestamp": datetime.utcnow().isoformat()
    }