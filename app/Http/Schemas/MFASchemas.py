from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class MFAMethod(str, Enum):
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    SMS = "sms"


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    mfa_required: bool
    methods: Dict[str, Any]


class TOTPSetupRequest(BaseModel):
    issuer: Optional[str] = Field(default="FastAPI Laravel", max_length=50)


class TOTPSetupResponse(BaseModel):
    qr_code: str
    provisioning_uri: str
    backup_codes: List[str]
    secret: Optional[str] = None  # Remove in production


class TOTPVerifyRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)
    
    @validator('token')
    def token_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('Token must be numeric')
        return v


class TOTPDisableRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)
    
    @validator('token')
    def token_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('Token must be numeric')
        return v


class BackupCodesRegenerateRequest(BaseModel):
    totp_token: str = Field(..., min_length=6, max_length=6)
    
    @validator('totp_token')
    def token_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('Token must be numeric')
        return v


class BackupCodesResponse(BaseModel):
    backup_codes: List[str]


class WebAuthnRegistrationOptionsResponse(BaseModel):
    options: Dict[str, Any]
    challenge: str


class WebAuthnRegisterRequest(BaseModel):
    credential: Dict[str, Any]
    challenge: str
    name: str = Field(..., min_length=1, max_length=100)


class WebAuthnAuthenticationOptionsResponse(BaseModel):
    options: Dict[str, Any]
    challenge: str


class WebAuthnCredentialResponse(BaseModel):
    id: str
    name: str
    credential_id: str
    last_used_at: Optional[datetime]
    created_at: datetime


class WebAuthnCredentialsResponse(BaseModel):
    credentials: List[WebAuthnCredentialResponse]


class WebAuthnDeleteRequest(BaseModel):
    credential_id: str


class SMSSetupRequest(BaseModel):
    phone_number: str = Field(..., pattern=r'^\+?1?\d{9,15}$')
    verification_code: str = Field(..., min_length=6, max_length=6)


class SMSCodeRequest(BaseModel):
    pass  # No fields needed - will generate code for current user


class MFASessionCreateResponse(BaseModel):
    session_token: str
    expires_in: int  # seconds
    available_methods: List[str]


class MFAVerifyTOTPRequest(BaseModel):
    session_token: str
    totp_code: str = Field(..., min_length=6, max_length=6)
    
    @validator('totp_code')
    def token_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('TOTP code must be numeric')
        return v


class MFAVerifyWebAuthnRequest(BaseModel):
    session_token: str
    credential: Dict[str, Any]
    challenge: str


class MFAVerifySMSRequest(BaseModel):
    session_token: str
    sms_code: str = Field(..., min_length=6, max_length=6)
    
    @validator('sms_code')
    def token_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('SMS code must be numeric')
        return v


class MFAVerifyResponse(BaseModel):
    success: bool
    message: str
    session_verified: Optional[bool] = None


class MFARequireRequest(BaseModel):
    required: bool


class DisableAllMFARequest(BaseModel):
    verification_method: str = Field(..., pattern=r'^(totp|webauthn|password)$')
    verification_data: Dict[str, Any]


class MFALoginChallengeResponse(BaseModel):
    requires_mfa: bool
    session_token: Optional[str] = None
    available_methods: Optional[List[str]] = None
    user_id: Optional[str] = None


class MFACompletedLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None