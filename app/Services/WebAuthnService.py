from __future__ import annotations

import base64
import json
import hashlib
from typing import Tuple, List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from webauthn import generate_registration_options, verify_registration_response
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import (
    UserVerificationRequirement, AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment
)
try:
    from webauthn.helpers.structs import RegistrationCredential, AuthenticationCredential, ResidentKeyRequirement
except ImportError:
    # Fallback for different webauthn versions  
    RegistrationCredential = Any  # type: ignore[assignment,misc]
    AuthenticationCredential = Any  # type: ignore[assignment,misc]
    ResidentKeyRequirement = Any  # type: ignore[assignment,misc]
try:
    from webauthn.helpers.cose import COSEAlgorithmIdentifier
except ImportError:
    # Fallback for different webauthn versions
    COSEAlgorithmIdentifier = Any  # type: ignore[assignment,misc]
from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse

from app.Models import User, WebAuthnCredential, UserMFASettings
from app.Services.BaseService import BaseService
from app.Services.MFAAuditService import MFAAuditService
from app.Services.MFARateLimitService import MFARateLimitService
from app.Models.MFAAttempt import MFAAttemptType, MFAAttemptStatus
from app.Models.MFAAuditLog import MFAAuditEvent
from config.settings import settings


class WebAuthnService(BaseService):
    """Enhanced WebAuthn service with attestation, device management, and security features"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.rp_id: str = getattr(settings, 'WEBAUTHN_RP_ID', 'localhost')
        self.rp_name: str = getattr(settings, 'WEBAUTHN_RP_NAME', 'FastAPI Laravel')
        self.origin: str = getattr(settings, 'WEBAUTHN_ORIGIN', 'http://localhost:8000')
        self.audit_service = MFAAuditService(db)
        self.rate_limit_service = MFARateLimitService(db)
        
        # Trusted attestation root certificates (in production, load from config)
        self.trusted_attestation_roots: List[bytes] = []
        
        # Known authenticator AAGUIDs and their metadata
        self.authenticator_metadata: Dict[str, Dict[str, Any]] = {
            "f8a011f3-8c0a-4d15-8006-17111f9edc7d": {
                "name": "YubiKey 5 Series",
                "icon": "🔑",
                "vendor": "Yubico",
                "trust_level": "high"
            },
            "08987058-cadc-4b81-b6e1-30de50dcbe96": {
                "name": "Touch ID",
                "icon": "👆",
                "vendor": "Apple",
                "trust_level": "high"
            },
            "00000000-0000-0000-0000-000000000000": {
                "name": "Platform Authenticator",
                "icon": "📱",
                "vendor": "Unknown",
                "trust_level": "medium"
            }
        }
    
    def generate_registration_options(
        self, 
        user: User,
        authenticator_attachment: Optional[str] = None,
        require_resident_key: bool = False,
        user_verification: str = "preferred"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Generate registration options with security preferences"""
        try:
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.WEBAUTHN
            )
            if not rate_check[0]:
                return False, rate_check[1], {}
            
            # Get existing credentials to exclude
            existing_credentials: List[Dict[str, Any]] = []
            for credential in user.webauthn_credentials:
                cred_id: Union[str, bytes] = credential.credential_id
                if isinstance(cred_id, str):
                    cred_id_bytes = cred_id.encode('latin-1')
                else:
                    cred_id_bytes = cred_id
                existing_credentials.append({
                    "id": cred_id_bytes,
                    "type": "public-key"
                })
            
            # Configure authenticator selection criteria if enhanced parameters are provided
            if any([authenticator_attachment, require_resident_key, user_verification != "preferred"]):
                authenticator_selection = AuthenticatorSelectionCriteria(
                    authenticator_attachment=AuthenticatorAttachment(authenticator_attachment) if authenticator_attachment else None,
                    require_resident_key=require_resident_key,
                    # resident_key=ResidentKeyRequirement.REQUIRED if require_resident_key else ResidentKeyRequirement.DISCOURAGED,  # Commented due to version compatibility
                    user_verification=UserVerificationRequirement(user_verification)
                )
                
                options = generate_registration_options(
                    rp_id=self.rp_id,
                    rp_name=self.rp_name,
                    user_id=user.id.encode('utf-8'),
                    user_name=user.email,
                    user_display_name=user.name,
                    exclude_credentials=existing_credentials,
                    supported_pub_key_algs=[
                        COSEAlgorithmIdentifier.ECDSA_SHA_256,  # type: ignore[attr-defined]
                        COSEAlgorithmIdentifier.EDDSA,  # type: ignore[attr-defined]
                        COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,  # type: ignore[attr-defined]
                        COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256,  # type: ignore[attr-defined]
                    ],
                    authenticator_selection=authenticator_selection,
                    attestation=AttestationConveyancePreference.DIRECT,  # Request attestation
                    timeout=300000,  # 5 minutes
                )
                
                # Enhanced options with security metadata
                enhanced_options = {
                    "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8'),
                    "rp": {
                        "name": options.rp.name,
                        "id": options.rp.id,
                    },
                    "user": {
                        "id": base64.urlsafe_b64encode(options.user.id).decode('utf-8'),
                        "name": options.user.name,
                        "displayName": options.user.display_name,
                    },
                    "pubKeyCredParams": [
                        {"alg": alg.value, "type": "public-key"} 
                        for alg in options.supported_pub_key_algs
                    ],
                    "timeout": options.timeout,
                    "excludeCredentials": [
                        {
                            "id": base64.urlsafe_b64encode(cred["id"] if isinstance(cred["id"], bytes) else str(cred["id"]).encode('latin-1')).decode('utf-8'),
                            "type": cred["type"]
                        } for cred in existing_credentials
                    ],
                    "authenticatorSelection": {
                        "authenticatorAttachment": authenticator_selection.authenticator_attachment.value if authenticator_selection.authenticator_attachment else None,
                        "requireResidentKey": authenticator_selection.require_resident_key,
                        "residentKey": getattr(getattr(authenticator_selection, 'resident_key', None), 'value', None) if hasattr(authenticator_selection, 'resident_key') and getattr(authenticator_selection, 'resident_key') is not None else None,
                        "userVerification": authenticator_selection.user_verification.value
                    },
                    "attestation": options.attestation.value if options.attestation else None,
                    "extensions": {
                        "credProps": True,  # Request credential properties
                        "largeBlob": {"support": "preferred"}  # Support for large blob storage
                    }
                }
            else:
                # Use basic options for backward compatibility
                options = generate_registration_options(
                    rp_id=self.rp_id,
                    rp_name=self.rp_name,
                    user_id=user.id.encode('utf-8'),
                    user_name=user.email,
                    user_display_name=user.name,
                    exclude_credentials=existing_credentials,
                    supported_pub_key_algs=[
                        COSEAlgorithmIdentifier.ECDSA_SHA_256,  # type: ignore[attr-defined]
                        COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,  # type: ignore[attr-defined]
                    ],
                    user_verification=UserVerificationRequirement.PREFERRED,
                    attestation=AttestationConveyancePreference.NONE,
                )
                
                enhanced_options = {
                    "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8'),
                    "rp": {"id": options.rp.id, "name": options.rp.name},
                    "user": {
                        "id": base64.urlsafe_b64encode(options.user.id).decode('utf-8'),
                        "name": options.user.name,
                        "displayName": options.user.display_name
                    },
                    "pubKeyCredParams": [{"alg": alg, "type": "public-key"} for alg in getattr(options, 'pub_key_cred_params', [])],
                    "timeout": getattr(options, 'timeout', 60000),
                    "excludeCredentials": [],
                    "authenticatorSelection": {
                        "userVerification": getattr(options, 'user_verification', "preferred")
                    },
                    "attestation": options.attestation.value if options.attestation else "none"
                }
            
            # Log registration initiation
            self.audit_service.log_setup_initiated(user, "webauthn")
            
            return True, "Registration options generated", {
                "options": enhanced_options,
                "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8'),
                "metadata": {
                    "existing_credentials": len(existing_credentials),
                    "supported_authenticators": list(self.authenticator_metadata.keys())
                }
            }
            
        except Exception as e:
            return False, f"Failed to generate registration options: {str(e)}", {}
    
    def verify_registration(
        self, 
        user: User, 
        credential: Dict[str, Any], 
        challenge: str, 
        credential_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify WebAuthn registration with attestation and security"""
        try:
            
            # Create RegistrationCredential from the client response
            registration_credential = RegistrationCredential.parse_raw(json.dumps(credential))  # type: ignore[attr-defined]
            
            # Record attempt for rate limiting
            self.rate_limit_service.record_attempt(
                user, MFAAttemptType.WEBAUTHN, MFAAttemptStatus.FAILED,
                ip_address=ip_address, user_agent=user_agent, 
                device_fingerprint=device_fingerprint
            )
            
            verification = verify_registration_response(
                credential=registration_credential,
                expected_challenge=challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                require_user_verification=True,
            )
            
            if not getattr(verification, 'verified', True):
                self.audit_service.log_event(
                    MFAAuditEvent.SETUP_FAILED, user=user, mfa_method="webauthn",
                    error_message="Registration verification failed"
                )
                return False, "Registration verification failed", None
            
            # Check if credential already exists
            credential_id_str = verification.credential_id.decode('latin-1')
            existing_cred = self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.credential_id == credential_id_str
            ).first()
            
            if existing_cred:
                return False, "Credential already registered", None
            
            # Extract device information from attestation
            device_info = self._extract_device_info(verification)
            
            # Validate attestation if present
            attestation_valid = self._validate_attestation(verification)
            
            # Save the credential with enhanced metadata
            webauthn_credential = WebAuthnCredential(
                user_id=user.id,
                credential_id=credential_id_str,
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
            
            # Record successful attempt
            self.rate_limit_service.record_attempt(
                user, MFAAttemptType.WEBAUTHN, MFAAttemptStatus.SUCCESS,
                ip_address=ip_address, user_agent=user_agent,
                device_fingerprint=device_fingerprint
            )
            
            self.db.commit()
            
            # Log successful registration
            self.audit_service.log_device_registered(
                user, credential_name, device_info.get("type", "unknown"),
                ip_address=ip_address, user_agent=user_agent,
                device_fingerprint=device_fingerprint
            )
            
            return True, "WebAuthn credential registered successfully", {
                "credential_id": webauthn_credential.id,
                "device_info": device_info,
                "attestation_valid": attestation_valid
            }
            
        except InvalidRegistrationResponse as e:
            self.audit_service.log_event(
                MFAAuditEvent.SETUP_FAILED, user=user, mfa_method="webauthn",
                error_message=f"Invalid registration response: {str(e)}"
            )
            return False, f"Invalid registration response: {str(e)}", None
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify registration: {str(e)}", None
    
    def generate_authentication_options(
        self, 
        user: Optional[User] = None,
        user_verification: str = "preferred"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Generate authentication options"""
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
                user_verification=UserVerificationRequirement(user_verification),
                timeout=300000,  # 5 minutes
            )
            
            enhanced_options = {
                "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8'),
                "timeout": options.timeout,
                "rpId": options.rp_id,
                "allowCredentials": [
                    {
                        "id": base64.urlsafe_b64encode(cred["id"] if isinstance(cred["id"], bytes) else str(cred["id"]).encode('latin-1')).decode('utf-8'),
                        "type": cred["type"],
                        "transports": ["usb", "nfc", "ble", "internal"]  # All possible transports
                    } for cred in (allowed_credentials or [])
                ],
                "userVerification": options.user_verification.value,
                "extensions": {
                    "largeBlob": {"read": True},  # Try to read large blob
                    "credProps": True
                }
            }
            
            return True, "Authentication options generated", {
                "options": enhanced_options,
                "challenge": base64.urlsafe_b64encode(options.challenge).decode('utf-8'),
                "metadata": {
                    "available_credentials": len(allowed_credentials) if allowed_credentials else 0
                }
            }
            
        except Exception as e:
            return False, f"Failed to generate authentication options: {str(e)}", {}
    
    def verify_authentication(
        self, 
        user: User, 
        credential: Dict[str, Any], 
        challenge: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify WebAuthn authentication with security checks"""
        try:
            # Check rate limiting first
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.WEBAUTHN, ip_address=ip_address,
                user_agent=user_agent, device_fingerprint=device_fingerprint
            )
            if not rate_check[0]:
                return False, rate_check[1], None
            
            
            # Create AuthenticationCredential from the client response
            auth_credential = AuthenticationCredential.parse_raw(json.dumps(credential))  # type: ignore[attr-defined]
            
            # Find the credential in database
            raw_id = auth_credential.raw_id.decode('latin-1') if hasattr(auth_credential.raw_id, 'decode') else str(auth_credential.raw_id)
            db_credential = self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.credential_id == raw_id
            ).first()
            
            if not db_credential:
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.WEBAUTHN, MFAAttemptStatus.FAILED,
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint,
                    failure_reason="Credential not found"
                )
                
                self.audit_service.log_verification_failed(
                    user, "webauthn", "Credential not found",
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                return False, "Credential not found", None
            
            # Verify the authentication
            verification = verify_authentication_response(
                credential=auth_credential,
                expected_challenge=challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64.b64decode(db_credential.public_key),
                credential_current_sign_count=db_credential.sign_count,
                require_user_verification=True,
            )
            
            if not getattr(verification, 'verified', True):
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.WEBAUTHN, MFAAttemptStatus.FAILED,
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint,
                    failure_reason="Authentication verification failed"
                )
                
                self.audit_service.log_verification_failed(
                    user, "webauthn", "Authentication verification failed",
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                return False, "Authentication verification failed", None
            
            # Check for sign count anomalies (potential credential cloning)
            if verification.new_sign_count <= db_credential.sign_count and db_credential.sign_count > 0:
                self.audit_service.log_verification_failed(
                    user, "webauthn", "Sign count anomaly detected",
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                return False, "Authentication anomaly detected", None
            
            # Update sign count and last used
            old_sign_count = db_credential.sign_count
            db_credential.sign_count = verification.new_sign_count
            db_credential.last_used_at = datetime.utcnow()
            
            if user.mfa_settings:
                user.mfa_settings.last_used_at = datetime.utcnow()
            
            # Record successful attempt
            self.rate_limit_service.record_attempt(
                user, MFAAttemptType.WEBAUTHN, MFAAttemptStatus.SUCCESS,
                ip_address=ip_address, user_agent=user_agent,
                device_fingerprint=device_fingerprint
            )
            
            self.db.commit()
            
            # Log successful authentication
            self.audit_service.log_verification_success(
                user, "webauthn", ip_address=ip_address,
                user_agent=user_agent, device_fingerprint=device_fingerprint
            )
            
            # Get device metadata
            device_metadata = self._get_device_metadata(db_credential)
            
            return True, "WebAuthn authentication successful", {
                "credential_name": db_credential.name,
                "sign_count_increment": verification.new_sign_count - old_sign_count,
                "device_metadata": device_metadata
            }
            
        except InvalidAuthenticationResponse as e:
            self.rate_limit_service.record_attempt(
                user, MFAAttemptType.WEBAUTHN, MFAAttemptStatus.FAILED,
                ip_address=ip_address, user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                failure_reason=f"Invalid auth response: {str(e)}"
            )
            return False, f"Invalid authentication response: {str(e)}", None
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify authentication: {str(e)}", None
    
    def get_user_credentials(self, user: User) -> List[Dict[str, Any]]:
        """Get credential information with metadata"""
        credentials = []
        for cred in user.webauthn_credentials:
            device_metadata = self._get_device_metadata(cred)
            
            credential_data: Dict[str, Any] = {
                "id": cred.id,
                "name": cred.name,
                "credential_id": cred.credential_id,
                "last_used_at": cred.last_used_at,
                "created_at": cred.created_at
            }
            
            # Add enhanced metadata if available
            if hasattr(cred, 'sign_count'):
                credential_data.update({
                    "sign_count": cred.sign_count,
                    "aaguid": cred.aaguid,
                    "device_metadata": device_metadata,
                    "usage_stats": self._get_credential_usage_stats(cred)
                })
            
            credentials.append(credential_data)
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
    
    def _extract_device_info(self, verification: Any) -> Dict[str, Any]:
        """Extract device information from attestation"""
        device_info = {
            "type": "unknown",
            "vendor": "unknown", 
            "model": "unknown",
            "trust_level": "medium"
        }
        
        if verification.aaguid:
            aaguid_hex = verification.aaguid.hex()
            if aaguid_hex in self.authenticator_metadata:
                metadata = self.authenticator_metadata[aaguid_hex]
                device_info.update({
                    "type": metadata["name"],
                    "vendor": metadata["vendor"],
                    "trust_level": metadata["trust_level"],
                    "icon": metadata["icon"]
                })
        
        return device_info
    
    def _validate_attestation(self, verification: Any) -> bool:
        """Validate attestation statement (simplified implementation)"""
        # In production, implement full attestation validation
        # This includes verifying attestation certificates against trusted roots
        return True  # Placeholder
    
    def _get_device_metadata(self, credential: WebAuthnCredential) -> Dict[str, Any]:  # type: ignore[no-any-unimported]
        """Get metadata for a stored credential"""
        metadata = {
            "type": "Unknown Device",
            "vendor": "Unknown", 
            "icon": "🔑",
            "trust_level": "medium"
        }
        
        if credential.aaguid and credential.aaguid in self.authenticator_metadata:
            metadata.update(self.authenticator_metadata[credential.aaguid])
        
        return metadata
    
    def _get_credential_usage_stats(self, credential: WebAuthnCredential) -> Dict[str, Any]:  # type: ignore[no-any-unimported]
        """Get usage statistics for a credential"""
        # Count recent usage
        # recent_usage = 0  # Placeholder for real implementation
        
        return {
            "total_uses": credential.sign_count,
            "recent_uses_30d": 0,  # Placeholder - implement with audit logs
            "last_used": credential.last_used_at,
            "risk_score": self._calculate_credential_risk_score(credential)
        }
    
    def _calculate_credential_risk_score(self, credential: WebAuthnCredential) -> int:  # type: ignore[no-any-unimported]
        """Calculate risk score for credential (0-100)"""
        score = 10  # Base score
        
        # Age factor
        if credential.created_at:
            age_days = (datetime.utcnow() - credential.created_at).days
            if age_days > 365:
                score += 5  # Older credentials slightly riskier
        
        # Usage pattern
        if credential.last_used_at:
            days_since_use = (datetime.utcnow() - credential.last_used_at).days
            if days_since_use > 90:
                score += 10  # Unused credentials are riskier
        
        # Device trust level
        if credential.aaguid and credential.aaguid in self.authenticator_metadata:
            trust_level = self.authenticator_metadata[credential.aaguid]["trust_level"]
            if trust_level == "low":
                score += 20
            elif trust_level == "medium":
                score += 10
            # high trust adds no penalty
        
        return min(score, 100)