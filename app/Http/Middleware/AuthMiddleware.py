from __future__ import annotations

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union
from typing_extensions import Annotated

from app.Utils import JWTUtils


security: HTTPBearer = HTTPBearer()


async def verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> str:
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = JWTUtils.verify_token(token, "access")
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token


class AuthMiddleware:
    
    @staticmethod
    def get_optional_user_from_token(
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
    ) -> Optional[int]:
        if not credentials:
            return None
        
        token_data = JWTUtils.verify_token(credentials.credentials, "access")
        
        if not token_data:
            return None
        
        user_id = token_data.get("user_id")
        return int(user_id) if user_id is not None else None
    
    @staticmethod
    def require_auth(token: Annotated[str, Depends(verify_token)]) -> str:
        return token
    
    @staticmethod
    def optional_auth(
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
    ) -> Optional[str]:
        if not credentials:
            return None
        
        token_data = JWTUtils.verify_token(credentials.credentials, "access")
        
        if not token_data:
            return None
        
        return credentials.credentials