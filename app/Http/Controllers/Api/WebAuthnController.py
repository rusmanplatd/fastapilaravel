from __future__ import annotations

from typing import Dict, Union, Any
from typing_extensions import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Middleware import verify_token
from app.Http.Schemas import (
    WebAuthnRegistrationOptionsResponse, WebAuthnRegisterRequest,
    WebAuthnAuthenticationOptionsResponse, WebAuthnCredentialsResponse,
    WebAuthnCredentialResponse, WebAuthnDeleteRequest,
    SuccessResponse, ErrorResponse
)
from app.Models import User
from app.Services import WebAuthnService
from config.database import get_db


class WebAuthnController(BaseController):
    
    def __init__(self) -> None:
        super().__init__()
    
    def get_registration_options(
        self,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> WebAuthnRegistrationOptionsResponse | ErrorResponse:
        """Get WebAuthn registration options for credential registration"""
        try:
            webauthn_service = WebAuthnService(db)
            success, message, data = webauthn_service.generate_registration_options(current_user)
            
            if not success:
                return ErrorResponse(message=message)
            
            # Convert options to dict for JSON serialization
            options_dict = {
                "challenge": data["challenge"],
                "rp": {
                    "name": data["options"].rp.name,
                    "id": data["options"].rp.id,
                },
                "user": {
                    "id": data["options"].user.id.decode('utf-8'),
                    "name": data["options"].user.name,
                    "displayName": data["options"].user.display_name,
                },
                "pubKeyCredParams": [
                    {"alg": alg.value, "type": "public-key"} 
                    for alg in data["options"].supported_pub_key_algs
                ],
                "timeout": data["options"].timeout,
                "excludeCredentials": data["options"].exclude_credentials or [],
                "authenticatorSelection": {
                    "authenticatorAttachment": data["options"].authenticator_selection.authenticator_attachment.value if data["options"].authenticator_selection and data["options"].authenticator_selection.authenticator_attachment else None,
                    "requireResidentKey": data["options"].authenticator_selection.require_resident_key if data["options"].authenticator_selection else False,
                    "userVerification": data["options"].authenticator_selection.user_verification.value if data["options"].authenticator_selection else "preferred"
                },
                "attestation": data["options"].attestation.value if data["options"].attestation else "none"
            }
            
            return WebAuthnRegistrationOptionsResponse(
                options=options_dict,
                challenge=data["challenge"]
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get registration options: {str(e)}"
            )
    
    def register_credential(
        self,
        request_data: WebAuthnRegisterRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Register a new WebAuthn credential"""
        try:
            webauthn_service = WebAuthnService(db)
            success, message, credential_data = webauthn_service.verify_registration(
                current_user,
                request_data.credential,
                request_data.challenge,
                request_data.name
            )
            
            if not success:
                return ErrorResponse(message=message)
            
            return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register credential: {str(e)}"
            )
    
    def get_authentication_options(
        self,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> WebAuthnAuthenticationOptionsResponse | ErrorResponse:
        """Get WebAuthn authentication options"""
        try:
            webauthn_service = WebAuthnService(db)
            success, message, data = webauthn_service.generate_authentication_options(current_user)
            
            if not success:
                return ErrorResponse(message=message)
            
            # Convert options to dict for JSON serialization
            options_dict = {
                "challenge": data["challenge"],
                "timeout": data["options"].timeout,
                "rpId": data["options"].rp_id,
                "allowCredentials": [
                    {
                        "id": cred["id"],
                        "type": cred["type"]
                    } for cred in (data["options"].allow_credentials or [])
                ],
                "userVerification": data["options"].user_verification.value if data["options"].user_verification else "preferred"
            }
            
            return WebAuthnAuthenticationOptionsResponse(
                options=options_dict,
                challenge=data["challenge"]
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get authentication options: {str(e)}"
            )
    
    def get_user_credentials(
        self,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> WebAuthnCredentialsResponse:
        """Get all WebAuthn credentials for current user"""
        try:
            webauthn_service = WebAuthnService(db)
            credentials_data = webauthn_service.get_user_credentials(current_user)
            
            credentials = [
                WebAuthnCredentialResponse(**cred_data)
                for cred_data in credentials_data
            ]
            
            return WebAuthnCredentialsResponse(credentials=credentials)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get credentials: {str(e)}"
            )
    
    def delete_credential(
        self,
        request_data: WebAuthnDeleteRequest,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Delete a WebAuthn credential"""
        try:
            webauthn_service = WebAuthnService(db)
            success, message = webauthn_service.delete_credential(
                current_user,
                request_data.credential_id
            )
            
            if not success:
                return ErrorResponse(message=message)
            
            return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete credential: {str(e)}"
            )
    
    def disable_webauthn(
        self,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(verify_token)]
    ) -> SuccessResponse | ErrorResponse:
        """Disable WebAuthn authentication (delete all credentials)"""
        try:
            webauthn_service = WebAuthnService(db)
            success, message = webauthn_service.disable_webauthn(current_user)
            
            if not success:
                return ErrorResponse(message=message)
            
            return SuccessResponse(message=message)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to disable WebAuthn: {str(e)}"
            )