from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Union, cast
from app.Utils.ULIDUtils import ULID, is_valid_ulid
from app.Types.JsonTypes import JsonValue, JsonObject, JWTPayload
from jose import JWTError, jwt
from config.settings import settings


class JWTUtils:
    """JWT token utilities."""
    
    @staticmethod
    def create_access_token(data: JsonObject, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": int(expire.timestamp()), "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return str(encoded_jwt)
    
    @staticmethod
    def create_refresh_token(data: JsonObject) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": int(expire.timestamp()), "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return str(encoded_jwt)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[JsonObject]:
        try:
            payload: JsonObject = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            if payload.get("type") != token_type:
                return None
                
            user_id_raw = payload.get("sub")
            if user_id_raw is None:
                return None
            
            # Convert to string and validate ULID
            if not isinstance(user_id_raw, str):
                return None
            if not is_valid_ulid(user_id_raw):
                return None
            
            user_id: ULID = str(user_id_raw)
                
            return {"user_id": user_id, "payload": payload}
        except JWTError:
            return None
    
    @staticmethod
    def decode_token(token: str) -> Optional[JWTPayload]:
        try:
            payload: JWTPayload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def create_reset_password_token(user_id: ULID) -> str:
        data: JsonObject = {"sub": str(user_id), "type": "reset_password"}
        expire = datetime.utcnow() + timedelta(hours=1)
        data.update({"exp": int(expire.timestamp())})
        return str(jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM))
    
    @staticmethod
    def verify_reset_password_token(token: str) -> Optional[ULID]:
        try:
            payload = cast(Dict[str, Union[str, int, None]], jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]))
            token_type = payload.get("type")
            if token_type != "reset_password":
                return None
            user_id_raw = payload.get("sub")
            if isinstance(user_id_raw, str) and is_valid_ulid(user_id_raw):
                return user_id_raw
            return None
        except (JWTError, ValueError):
            return None


class JWTManager:
    """JWT Manager class for token operations."""
    
    @staticmethod
    def decode_token(token: str) -> Optional[JsonObject]:
        """Decode and verify a JWT token."""
        return JWTUtils.decode_token(token)
    
    @staticmethod
    def create_access_token(data: JsonObject, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token."""
        return JWTUtils.create_access_token(data, expires_delta)
    
    @staticmethod
    def create_refresh_token(data: JsonObject) -> str:
        """Create refresh token."""
        return JWTUtils.create_refresh_token(data)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[JsonObject]:
        """Verify a token."""
        return JWTUtils.verify_token(token, token_type)