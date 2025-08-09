from __future__ import annotations

from typing import Dict, Any
from typing_extensions import Annotated
from fastapi import Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Middleware import verify_token
from app.Http.Schemas import (
    MFAStatusResponse, TOTPSetupRequest, TOTPSetupResponse, TOTPVerifyRequest,
    TOTPDisableRequest, BackupCodesRegenerateRequest, BackupCodesResponse,
    MFARequireRequest, DisableAllMFARequest, SuccessResponse, ErrorResponse,
    MFASessionCreateResponse, MFAVerifyTOTPRequest, MFAVerifyWebAuthnRequest,
    MFAVerifySMSRequest, MFAVerifyResponse
)
from app.Models import User
from app.Services import MFAService, TOTPService
from config.database import get_db


class MFAController(BaseController):
    
    def __init__(self) -> None:
        super().__init__()
    
    def get_mfa_status(
        self,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> MFAStatusResponse:
        """Get current MFA status for user"""
        try:
            mfa_service = MFAService(db)
            status_data = mfa_service.get_mfa_status(current_user)
            
            return MFAStatusResponse(**status_data)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get MFA status: {str(e)}"
            )
    
    def setup_totp(
        self,
        request_data: TOTPSetupRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> TOTPSetupResponse | ErrorResponse:
        """Setup TOTP authentication for user"""
        try:
            totp_service = TOTPService(db)
            issuer = request_data.issuer or "FastAPI Laravel"
            success, message, data = totp_service.setup_totp(current_user, issuer)
            
            if not success:
                return ErrorResponse(message=message)
            
            return TOTPSetupResponse(**data)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to setup TOTP: {str(e)}"
            )
    
    def verify_totp_setup(
        self,
        request_data: TOTPVerifyRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Verify TOTP setup and enable TOTP"""
        try:
            totp_service = TOTPService(db)
            success, message, setup_info = totp_service.verify_and_enable_totp(current_user, request_data.token)
            
            if not success:
                return ErrorResponse(message=message)
            
            # Return setup info if available
            if setup_info:
                return SuccessResponse(message=message, **setup_info)
            else:
                return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify TOTP setup: {str(e)}"
            )
    
    def disable_totp(
        self,
        request_data: TOTPDisableRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Disable TOTP authentication"""
        try:
            totp_service = TOTPService(db)
            success, message = totp_service.disable_totp(current_user, request_data.token)
            
            if not success:
                return ErrorResponse(message=message)
            
            return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to disable TOTP: {str(e)}"
            )
    
    def regenerate_backup_codes(
        self,
        request_data: BackupCodesRegenerateRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> BackupCodesResponse | ErrorResponse:
        """Regenerate TOTP backup codes"""
        try:
            totp_service = TOTPService(db)
            success, message, backup_codes = totp_service.regenerate_backup_codes(
                current_user, request_data.totp_token
            )
            
            if not success:
                return ErrorResponse(message=message)
            
            return BackupCodesResponse(backup_codes=backup_codes)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to regenerate backup codes: {str(e)}"
            )
    
    def require_mfa(
        self,
        request_data: MFARequireRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Enable or disable MFA requirement for user"""
        try:
            mfa_service = MFAService(db)
            
            if request_data.required:
                success, message = mfa_service.require_mfa(current_user)
            else:
                success, message = mfa_service.remove_mfa_requirement(current_user)
            
            if not success:
                return ErrorResponse(message=message)
            
            return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update MFA requirement: {str(e)}"
            )
    
    def disable_all_mfa(
        self,
        request_data: DisableAllMFARequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Disable all MFA methods for user"""
        try:
            mfa_service = MFAService(db)
            success, message = mfa_service.disable_all_mfa(
                current_user, 
                request_data.verification_method, 
                request_data.verification_data
            )
            
            if not success:
                return ErrorResponse(message=message)
            
            return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to disable MFA: {str(e)}"
            )
    
    def create_mfa_session(
        self,
        request: Request,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> MFASessionCreateResponse | ErrorResponse:
        """Create MFA session for authentication"""
        try:
            mfa_service = MFAService(db)
            
            # Get client info
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
            success, message, session_token = mfa_service.create_mfa_session(
                current_user, ip_address, user_agent
            )
            
            if not success or session_token is None:
                return ErrorResponse(message=message)
            
            available_methods = mfa_service.get_available_mfa_methods(current_user)
            
            return MFASessionCreateResponse(
                session_token=session_token,
                expires_in=600,  # 10 minutes
                available_methods=available_methods
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create MFA session: {str(e)}"
            )
    
    def verify_mfa_totp(
        self,
        request_data: MFAVerifyTOTPRequest,
        db: Annotated[Session, Depends(get_db)]
    ) -> MFAVerifyResponse:
        """Verify MFA using TOTP"""
        try:
            mfa_service = MFAService(db)
            success, message = mfa_service.verify_mfa_with_totp(
                request_data.session_token,
                request_data.totp_code
            )
            
            return MFAVerifyResponse(
                success=success,
                message=message,
                session_verified=success
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify TOTP: {str(e)}"
            )
    
    def verify_mfa_webauthn(
        self,
        request_data: MFAVerifyWebAuthnRequest,
        db: Annotated[Session, Depends(get_db)]
    ) -> MFAVerifyResponse:
        """Verify MFA using WebAuthn"""
        try:
            mfa_service = MFAService(db)
            success, message = mfa_service.verify_mfa_with_webauthn(
                request_data.session_token,
                request_data.credential,
                request_data.challenge
            )
            
            return MFAVerifyResponse(
                success=success,
                message=message,
                session_verified=success
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify WebAuthn: {str(e)}"
            )
    
    def verify_mfa_sms(
        self,
        request_data: MFAVerifySMSRequest,
        db: Annotated[Session, Depends(get_db)]
    ) -> MFAVerifyResponse:
        """Verify MFA using SMS"""
        try:
            mfa_service = MFAService(db)
            success, message = mfa_service.verify_mfa_with_sms(
                request_data.session_token,
                request_data.sms_code
            )
            
            return MFAVerifyResponse(
                success=success,
                message=message,
                session_verified=success
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify SMS: {str(e)}"
            )