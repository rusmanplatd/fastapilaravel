from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from app.Utils.ULIDUtils import ULID, is_valid_ulid
from jose import JWTError, jwt
from config.settings import settings


class JWTUtils:
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            if payload.get("type") != token_type:
                return None
                
            user_id_raw = payload.get("sub")
            if user_id_raw is None:
                return None
            
            # ULID validation
            if not is_valid_ulid(user_id_raw):
                return None
            
            user_id: ULID = str(user_id_raw)
                
            return {"user_id": user_id, "payload": payload}
        except JWTError:
            return None
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def create_reset_password_token(user_id: ULID) -> str:
        data: Dict[str, Any] = {"sub": str(user_id), "type": "reset_password"}
        expire = datetime.utcnow() + timedelta(hours=1)
        data.update({"exp": expire})
        return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def verify_reset_password_token(token: str) -> Optional[ULID]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "reset_password":
                return None
            user_id = payload.get("sub")
            return str(user_id) if user_id and is_valid_ulid(user_id) else None
        except (JWTError, ValueError):
            return None