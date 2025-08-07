from __future__ import annotations

from typing import Union
from typing_extensions import Annotated
from fastapi import APIRouter, Depends
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.Http.Controllers.MFAController import MFAController
from app.Http.Controllers.WebAuthnController import WebAuthnController
from app.Http.Controllers.AuthController import AuthController
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Models.User import User
from app.Http.Schemas import (
    MFAStatusResponse, TOTPSetupRequest, TOTPSetupResponse, TOTPVerifyRequest,
    TOTPDisableRequest, BackupCodesRegenerateRequest, BackupCodesResponse,
    MFARequireRequest, DisableAllMFARequest, SuccessResponse, ErrorResponse,
    MFASessionCreateResponse, MFAVerifyTOTPRequest, MFAVerifyWebAuthnRequest,
    MFAVerifySMSRequest, MFAVerifyResponse, WebAuthnRegistrationOptionsResponse,
    WebAuthnRegisterRequest, WebAuthnAuthenticationOptionsResponse,
    WebAuthnCredentialsResponse, WebAuthnDeleteRequest, MFACompletedLoginResponse
)
from config.database import get_db

router = APIRouter(prefix="/api/v1/mfa", tags=["Multi-Factor Authentication"])

# Initialize controllers
mfa_controller = MFAController()
webauthn_controller = WebAuthnController()
auth_controller = AuthController()

# MFA Status and Management
@router.get("/status", response_model=MFAStatusResponse)
def get_mfa_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> MFAStatusResponse:
    """Get current MFA status for authenticated user"""
    return mfa_controller.get_mfa_status(db, current_user)

@router.post("/require", response_model=Union[SuccessResponse, ErrorResponse])
def require_mfa(
    request_data: MFARequireRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Enable or disable MFA requirement for user"""
    return mfa_controller.require_mfa(request_data, db, current_user)

@router.post("/disable-all", response_model=Union[SuccessResponse, ErrorResponse])
def disable_all_mfa(
    request_data: DisableAllMFARequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Disable all MFA methods for user"""
    return mfa_controller.disable_all_mfa(request_data, db, current_user)

# TOTP (Time-based One-Time Password) Routes
@router.post("/totp/setup", response_model=Union[TOTPSetupResponse, ErrorResponse])
def setup_totp(
    request_data: TOTPSetupRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[TOTPSetupResponse, ErrorResponse]:
    """Setup TOTP authentication"""
    return mfa_controller.setup_totp(request_data, db, current_user)

@router.post("/totp/verify", response_model=Union[SuccessResponse, ErrorResponse])
def verify_totp_setup(
    request_data: TOTPVerifyRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Verify and enable TOTP"""
    return mfa_controller.verify_totp_setup(request_data, db, current_user)

@router.post("/totp/disable", response_model=Union[SuccessResponse, ErrorResponse])
def disable_totp(
    request_data: TOTPDisableRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Disable TOTP authentication"""
    return mfa_controller.disable_totp(request_data, db, current_user)

@router.post("/totp/regenerate-backup-codes", response_model=Union[BackupCodesResponse, ErrorResponse])
def regenerate_backup_codes(
    request_data: BackupCodesRegenerateRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[BackupCodesResponse, ErrorResponse]:
    """Regenerate TOTP backup codes"""
    return mfa_controller.regenerate_backup_codes(request_data, db, current_user)

# WebAuthn Routes  
@router.get("/webauthn/registration-options", response_model=Union[WebAuthnRegistrationOptionsResponse, ErrorResponse])
def get_webauthn_registration_options(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[WebAuthnRegistrationOptionsResponse, ErrorResponse]:
    """Get WebAuthn registration options"""
    return webauthn_controller.get_registration_options(db, current_user)

@router.post("/webauthn/register", response_model=Union[SuccessResponse, ErrorResponse])
def register_webauthn_credential(
    request_data: WebAuthnRegisterRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Register WebAuthn credential"""
    return webauthn_controller.register_credential(request_data, db, current_user)

@router.get("/webauthn/authentication-options", response_model=Union[WebAuthnAuthenticationOptionsResponse, ErrorResponse])
def get_webauthn_authentication_options(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[WebAuthnAuthenticationOptionsResponse, ErrorResponse]:
    """Get WebAuthn authentication options"""
    return webauthn_controller.get_authentication_options(db, current_user)

@router.get("/webauthn/credentials", response_model=WebAuthnCredentialsResponse)
def get_webauthn_credentials(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> WebAuthnCredentialsResponse:
    """Get user's WebAuthn credentials"""
    return webauthn_controller.get_user_credentials(db, current_user)

@router.delete("/webauthn/credential", response_model=Union[SuccessResponse, ErrorResponse])
def delete_webauthn_credential(
    request_data: WebAuthnDeleteRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Delete WebAuthn credential"""
    return webauthn_controller.delete_credential(request_data, db, current_user)

@router.post("/webauthn/disable", response_model=Union[SuccessResponse, ErrorResponse])
def disable_webauthn(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[SuccessResponse, ErrorResponse]:
    """Disable WebAuthn authentication"""
    return webauthn_controller.disable_webauthn(db, current_user)

# MFA Session and Verification Routes (for login flow)
@router.post("/session/create", response_model=Union[MFASessionCreateResponse, ErrorResponse])
def create_mfa_session(
    request: Request, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> Union[MFASessionCreateResponse, ErrorResponse]:
    """Create MFA session for authentication"""
    return mfa_controller.create_mfa_session(request, db, current_user)

@router.post("/session/verify/totp", response_model=MFAVerifyResponse)
def verify_mfa_totp(
    request_data: MFAVerifyTOTPRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> MFAVerifyResponse:
    """Verify MFA using TOTP"""
    return mfa_controller.verify_mfa_totp(request_data, db)

@router.post("/session/verify/webauthn", response_model=MFAVerifyResponse)
def verify_mfa_webauthn(
    request_data: MFAVerifyWebAuthnRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> MFAVerifyResponse:
    """Verify MFA using WebAuthn"""
    return mfa_controller.verify_mfa_webauthn(request_data, db)

@router.post("/session/verify/sms", response_model=MFAVerifyResponse)
def verify_mfa_sms(
    request_data: MFAVerifySMSRequest, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(verify_token)]
) -> MFAVerifyResponse:
    """Verify MFA using SMS"""
    return mfa_controller.verify_mfa_sms(request_data, db)

@router.post("/complete/{session_token}", response_model=MFACompletedLoginResponse)
def complete_mfa_login(
    session_token: str, 
    db: Annotated[Session, Depends(get_db)]
) -> MFACompletedLoginResponse:
    """Complete MFA login process"""
    return auth_controller.complete_mfa_login(session_token, db)