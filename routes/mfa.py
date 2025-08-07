from __future__ import annotations

from typing import Union
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.Http.Controllers.MFAController import MFAController
from app.Http.Controllers.WebAuthnController import WebAuthnController
from app.Http.Controllers.AuthController import AuthController
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
def get_mfa_status(db: Session = Depends(get_db)) -> MFAStatusResponse:
    """Get current MFA status for authenticated user"""
    return mfa_controller.get_mfa_status(db=db)

@router.post("/require", response_model=Union[SuccessResponse, ErrorResponse])
def require_mfa(request_data: MFARequireRequest, db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Enable or disable MFA requirement for user"""
    return mfa_controller.require_mfa(request_data, db=db)

@router.post("/disable-all", response_model=Union[SuccessResponse, ErrorResponse])
def disable_all_mfa(request_data: DisableAllMFARequest, db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Disable all MFA methods for user"""
    return mfa_controller.disable_all_mfa(request_data, db=db)

# TOTP (Time-based One-Time Password) Routes
@router.post("/totp/setup", response_model=Union[TOTPSetupResponse, ErrorResponse])
def setup_totp(request_data: TOTPSetupRequest, db: Session = Depends(get_db)) -> Union[TOTPSetupResponse, ErrorResponse]:
    """Setup TOTP authentication"""
    return mfa_controller.setup_totp(request_data, db=db)

@router.post("/totp/verify", response_model=Union[SuccessResponse, ErrorResponse])
def verify_totp_setup(request_data: TOTPVerifyRequest, db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Verify and enable TOTP"""
    return mfa_controller.verify_totp_setup(request_data, db=db)

@router.post("/totp/disable", response_model=Union[SuccessResponse, ErrorResponse])
def disable_totp(request_data: TOTPDisableRequest, db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Disable TOTP authentication"""
    return mfa_controller.disable_totp(request_data, db=db)

@router.post("/totp/regenerate-backup-codes", response_model=Union[BackupCodesResponse, ErrorResponse])
def regenerate_backup_codes(request_data: BackupCodesRegenerateRequest, db: Session = Depends(get_db)) -> Union[BackupCodesResponse, ErrorResponse]:
    """Regenerate TOTP backup codes"""
    return mfa_controller.regenerate_backup_codes(request_data, db=db)

# WebAuthn Routes
@router.get("/webauthn/registration-options", response_model=Union[WebAuthnRegistrationOptionsResponse, ErrorResponse])
def get_webauthn_registration_options(db: Session = Depends(get_db)) -> Union[WebAuthnRegistrationOptionsResponse, ErrorResponse]:
    """Get WebAuthn registration options"""
    return webauthn_controller.get_registration_options(db=db)

@router.post("/webauthn/register", response_model=Union[SuccessResponse, ErrorResponse])
def register_webauthn_credential(request_data: WebAuthnRegisterRequest, db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Register WebAuthn credential"""
    return webauthn_controller.register_credential(request_data, db=db)

@router.get("/webauthn/authentication-options", response_model=Union[WebAuthnAuthenticationOptionsResponse, ErrorResponse])
def get_webauthn_authentication_options(db: Session = Depends(get_db)) -> Union[WebAuthnAuthenticationOptionsResponse, ErrorResponse]:
    """Get WebAuthn authentication options"""
    return webauthn_controller.get_authentication_options(db=db)

@router.get("/webauthn/credentials", response_model=WebAuthnCredentialsResponse)
def get_webauthn_credentials(db: Session = Depends(get_db)) -> WebAuthnCredentialsResponse:
    """Get user's WebAuthn credentials"""
    return webauthn_controller.get_user_credentials(db=db)

@router.delete("/webauthn/credential", response_model=Union[SuccessResponse, ErrorResponse])
def delete_webauthn_credential(request_data: WebAuthnDeleteRequest, db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Delete WebAuthn credential"""
    return webauthn_controller.delete_credential(request_data, db=db)

@router.post("/webauthn/disable", response_model=Union[SuccessResponse, ErrorResponse])
def disable_webauthn(db: Session = Depends(get_db)) -> Union[SuccessResponse, ErrorResponse]:
    """Disable WebAuthn authentication"""
    return webauthn_controller.disable_webauthn(db=db)

# MFA Session and Verification Routes (for login flow)
@router.post("/session/create", response_model=Union[MFASessionCreateResponse, ErrorResponse])
def create_mfa_session(request: Request, db: Session = Depends(get_db)) -> Union[MFASessionCreateResponse, ErrorResponse]:
    """Create MFA session for authentication"""
    return mfa_controller.create_mfa_session(request, db=db)

@router.post("/session/verify/totp", response_model=MFAVerifyResponse)
def verify_mfa_totp(request_data: MFAVerifyTOTPRequest, db: Session = Depends(get_db)) -> MFAVerifyResponse:
    """Verify MFA using TOTP"""
    return mfa_controller.verify_mfa_totp(request_data, db=db)

@router.post("/session/verify/webauthn", response_model=MFAVerifyResponse)
def verify_mfa_webauthn(request_data: MFAVerifyWebAuthnRequest, db: Session = Depends(get_db)) -> MFAVerifyResponse:
    """Verify MFA using WebAuthn"""
    return mfa_controller.verify_mfa_webauthn(request_data, db=db)

@router.post("/session/verify/sms", response_model=MFAVerifyResponse)
def verify_mfa_sms(request_data: MFAVerifySMSRequest, db: Session = Depends(get_db)) -> MFAVerifyResponse:
    """Verify MFA using SMS"""
    return mfa_controller.verify_mfa_sms(request_data, db=db)

@router.post("/login/complete/{session_token}", response_model=MFACompletedLoginResponse)
def complete_mfa_login(session_token: str, db: Session = Depends(get_db)) -> MFACompletedLoginResponse:
    """Complete login after MFA verification"""
    return auth_controller.complete_mfa_login(session_token, db=db)