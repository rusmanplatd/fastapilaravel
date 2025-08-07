from __future__ import annotations

import base64
import json
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from webauthn import generate_registration_options, verify_registration_response
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import (
    RegistrationCredential, AuthenticationCredential,
    UserVerificationRequirement, AttestationConveyancePreference
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

from app.Models import User, WebAuthnCredential, UserMFASettings
from app.Services.BaseService import BaseService
from config.settings import settings


class WebAuthnService(BaseService):
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.rp_id = getattr(settings, 'WEBAUTHN_RP_ID', 'localhost')
        self.rp_name = getattr(settings, 'WEBAUTHN_RP_NAME', 'FastAPI Laravel')
        self.origin = getattr(settings, 'WEBAUTHN_ORIGIN', 'http://localhost:8000')
    
    def generate_registration_options(self, user: User) -> Tuple[bool, str, Dict[str, Any]]:
        """Generate registration options for WebAuthn credential registration"""
        try:
            # Get existing credentials to exclude
            existing_credentials = []
            for credential in user.webauthn_credentials:
                existing_credentials.append({
                    "id": credential.credential_id,
                    "type": "public-key"
                })
            
            options = generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=user.id.encode('utf-8'),
                user_name=user.email,
                user_display_name=user.name,
                exclude_credentials=existing_credentials,
                supported_pub_key_algs=[
                    COSEAlgorithmIdentifier.ECDSA_SHA_256,
                    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
                ],
                user_verification=UserVerificationRequirement.PREFERRED,
                attestation=AttestationConveyancePreference.NONE,
            )
            
            # Store challenge in session/cache (simplified - use proper session management in production)
            challenge_key = f"webauthn_challenge_{user.id}"
            
            return True, "Registration options generated", {
                "options": options,
                "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8')
            }
            
        except Exception as e:
            return False, f"Failed to generate registration options: {str(e)}", {}
    
    def verify_registration(self, user: User, credential: Dict[str, Any], challenge: str, credential_name: str) -> Tuple[bool, str]:
        """Verify WebAuthn registration response"""
        try:
            challenge_bytes = base64.urlsafe_b64decode(challenge.encode('utf-8'))
            
            # Create RegistrationCredential from the client response
            registration_credential = RegistrationCredential.parse_raw(json.dumps(credential))
            
            verification = verify_registration_response(
                credential=registration_credential,
                expected_challenge=challenge_bytes,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
            )
            
            if not verification.verified:
                return False, "Registration verification failed"
            
            # Check if credential already exists
            existing_cred = self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.credential_id == verification.credential_id.decode('latin-1')
            ).first()
            
            if existing_cred:
                return False, "Credential already registered"
            
            # Save the credential
            webauthn_credential = WebAuthnCredential(
                user_id=user.id,
                credential_id=verification.credential_id.decode('latin-1'),
                public_key=base64.b64encode(verification.credential_public_key).decode('utf-8'),
                sign_count=verification.sign_count,
                name=credential_name,
                aaguid=verification.aaguid.hex() if verification.aaguid else None
            )
            
            self.db.add(webauthn_credential)
            
            # Enable WebAuthn in MFA settings
            if not user.mfa_settings:
                mfa_settings = UserMFASettings(
                    user_id=user.id,
                    webauthn_enabled=True
                )
                self.db.add(mfa_settings)
            else:
                user.mfa_settings.webauthn_enabled = True
            
            self.db.commit()
            
            return True, "WebAuthn credential registered successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify registration: {str(e)}"
    
    def generate_authentication_options(self, user: Optional[User] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Generate authentication options for WebAuthn authentication"""
        try:
            # Get user's credentials if user is specified
            allowed_credentials = []
            if user:
                for credential in user.webauthn_credentials:
                    allowed_credentials.append({
                        "id": credential.credential_id.encode('latin-1'),
                        "type": "public-key"
                    })
            
            options = generate_authentication_options(
                rp_id=self.rp_id,
                allow_credentials=allowed_credentials if allowed_credentials else None,
                user_verification=UserVerificationRequirement.PREFERRED,
            )
            
            return True, "Authentication options generated", {
                "options": options,
                "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8')
            }
            
        except Exception as e:
            return False, f"Failed to generate authentication options: {str(e)}", {}
    
    def verify_authentication(self, user: User, credential: Dict[str, Any], challenge: str) -> Tuple[bool, str]:
        """Verify WebAuthn authentication response"""
        try:
            challenge_bytes = base64.urlsafe_b64decode(challenge.encode('utf-8'))
            
            # Create AuthenticationCredential from the client response
            auth_credential = AuthenticationCredential.parse_raw(json.dumps(credential))
            
            # Find the credential in database
            db_credential = self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.credential_id == auth_credential.raw_id.decode('latin-1')
            ).first()
            
            if not db_credential:
                return False, "Credential not found"
            
            # Verify the authentication
            verification = verify_authentication_response(
                credential=auth_credential,
                expected_challenge=challenge_bytes,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64.b64decode(db_credential.public_key),
                credential_current_sign_count=db_credential.sign_count,
            )
            
            if not verification.verified:
                return False, "Authentication verification failed"
            
            # Update sign count and last used
            db_credential.sign_count = verification.new_sign_count
            db_credential.last_used_at = datetime.utcnow()
            
            if user.mfa_settings:
                user.mfa_settings.last_used_at = datetime.utcnow()
            
            self.db.commit()
            
            return True, "WebAuthn authentication successful"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify authentication: {str(e)}"
    
    def get_user_credentials(self, user: User) -> List[Dict[str, Any]]:
        """Get all WebAuthn credentials for a user"""
        credentials = []
        for cred in user.webauthn_credentials:
            credentials.append({
                "id": cred.id,
                "name": cred.name,
                "credential_id": cred.credential_id,
                "last_used_at": cred.last_used_at,
                "created_at": cred.created_at
            })
        return credentials
    
    def delete_credential(self, user: User, credential_id: str) -> Tuple[bool, str]:
        """Delete a WebAuthn credential"""
        try:
            credential = self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.id == credential_id
            ).first()
            
            if not credential:
                return False, "Credential not found"
            
            self.db.delete(credential)
            
            # Check if this was the last WebAuthn credential
            remaining_credentials = self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.id != credential_id
            ).count()
            
            # If no more WebAuthn credentials, disable WebAuthn
            if remaining_credentials == 0 and user.mfa_settings:
                user.mfa_settings.webauthn_enabled = False
            
            self.db.commit()
            
            return True, "WebAuthn credential deleted successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to delete credential: {str(e)}"
    
    def disable_webauthn(self, user: User) -> Tuple[bool, str]:
        """Disable WebAuthn for user (delete all credentials)"""
        try:
            # Delete all WebAuthn credentials
            self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id
            ).delete()
            
            # Disable WebAuthn in MFA settings
            if user.mfa_settings:
                user.mfa_settings.webauthn_enabled = False
            
            self.db.commit()
            
            return True, "WebAuthn disabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to disable WebAuthn: {str(e)}"