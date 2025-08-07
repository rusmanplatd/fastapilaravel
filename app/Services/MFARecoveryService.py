from __future__ import annotations

import secrets
import hashlib
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.Models import User
from app.Services.BaseService import BaseService
from app.Services.MFAAuditService import MFAAuditService, MFAAuditEvent
from database.migrations.create_mfa_codes_table import MFACode, MFACodeType


class MFARecoveryService(BaseService):
    """MFA Recovery and admin bypass service for emergency access"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.audit_service = MFAAuditService(db)
        
        # Recovery configuration
        self.recovery_code_length = 16  # 16 character recovery codes
        self.recovery_code_expiry_hours = 24  # 24 hour expiry
        self.max_recovery_attempts = 3  # Max attempts per recovery code
        
        # Admin bypass configuration
        self.admin_bypass_expiry_minutes = 30  # 30 minute admin bypass
        self.require_multiple_admins = True  # Require multiple admin approvals
    
    def generate_recovery_code(
        self,
        user: User,
        admin_user_id: str,
        reason: str,
        expires_hours: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Generate emergency recovery code for user"""
        try:
            if expires_hours is None:
                expires_hours = self.recovery_code_expiry_hours
            
            # Generate secure recovery code
            recovery_code = self._generate_secure_recovery_code(user)
            
            # Store recovery code
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            recovery_record = MFACode(
                user_id=user.id,
                code=recovery_code,
                code_type=MFACodeType.EMAIL,  # Use email type for recovery codes
                expires_at=expires_at,
                used=False,
                session_id=f"recovery_{admin_user_id}_{datetime.utcnow().timestamp()}"
            )
            
            self.db.add(recovery_record)
            self.db.commit()
            
            # Log recovery code generation
            self.audit_service.log_event(
                MFAAuditEvent.RECOVERY_USED,
                user=user,
                admin_user_id=admin_user_id,
                ip_address=ip_address,
                details={
                    "action": "recovery_code_generated",
                    "reason": reason,
                    "expires_at": expires_at.isoformat(),
                    "code_id": recovery_record.id
                }
            )
            
            return True, f"Recovery code generated (expires in {expires_hours} hours)", recovery_code
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to generate recovery code: {str(e)}", None
    
    def verify_recovery_code(
        self,
        user: User,
        recovery_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify and consume recovery code"""
        try:
            # Find valid recovery code
            recovery_record = self.db.query(MFACode).filter(
                and_(
                    MFACode.user_id == user.id,
                    MFACode.code == recovery_code,
                    MFACode.code_type == MFACodeType.EMAIL,
                    MFACode.used == False,
                    MFACode.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not recovery_record:
                # Log failed recovery attempt
                self.audit_service.log_event(
                    MFAAuditEvent.VERIFICATION_FAILED,
                    user=user,
                    mfa_method="recovery_code",
                    error_message="Invalid or expired recovery code",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                return False, "Invalid or expired recovery code", None
            
            # Mark recovery code as used
            recovery_record.used = True
            
            # Generate temporary bypass token
            bypass_token = secrets.token_urlsafe(32)
            bypass_expires = datetime.utcnow() + timedelta(minutes=self.admin_bypass_expiry_minutes)
            
            # Store bypass token (reuse MFACode table)
            bypass_record = MFACode(
                user_id=user.id,
                code=bypass_token,
                code_type=MFACodeType.EMAIL,
                expires_at=bypass_expires,
                used=False,
                session_id=f"bypass_{recovery_record.session_id}"
            )
            
            self.db.add(bypass_record)
            self.db.commit()
            
            # Log successful recovery
            self.audit_service.log_event(
                MFAAuditEvent.RECOVERY_USED,
                user=user,
                mfa_method="recovery_code",
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "action": "recovery_code_verified",
                    "bypass_token": bypass_token[:8] + "...",  # Log partial token
                    "expires_at": bypass_expires.isoformat()
                }
            )
            
            return True, "Recovery code verified", {
                "bypass_token": bypass_token,
                "expires_at": bypass_expires,
                "expires_in_minutes": self.admin_bypass_expiry_minutes
            }
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify recovery code: {str(e)}", None
    
    def create_admin_bypass(
        self,
        user: User,
        admin_user_id: str,
        reason: str,
        bypass_duration_minutes: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create admin bypass for MFA (emergency access)"""
        try:
            if bypass_duration_minutes is None:
                bypass_duration_minutes = self.admin_bypass_expiry_minutes
            
            # Generate bypass token
            bypass_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(minutes=bypass_duration_minutes)
            
            # Store bypass token
            bypass_record = MFACode(
                user_id=user.id,
                code=bypass_token,
                code_type=MFACodeType.EMAIL,  # Reuse email type
                expires_at=expires_at,
                used=False,
                session_id=f"admin_bypass_{admin_user_id}_{datetime.utcnow().timestamp()}"
            )
            
            self.db.add(bypass_record)
            self.db.commit()
            
            # Log admin bypass creation
            self.audit_service.log_admin_bypass(
                user=user,
                admin_user_id=admin_user_id,
                reason=reason,
                ip_address=ip_address
            )
            
            return True, f"Admin bypass created (expires in {bypass_duration_minutes} minutes)", {
                "bypass_token": bypass_token,
                "expires_at": expires_at,
                "expires_in_minutes": bypass_duration_minutes,
                "reason": reason
            }
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create admin bypass: {str(e)}", None
    
    def verify_bypass_token(
        self,
        user: User,
        bypass_token: str,
        consume: bool = True
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify and optionally consume bypass token"""
        try:
            # Find valid bypass token
            bypass_record = self.db.query(MFACode).filter(
                and_(
                    MFACode.user_id == user.id,
                    MFACode.code == bypass_token,
                    MFACode.code_type == MFACodeType.EMAIL,
                    MFACode.used == False,
                    MFACode.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not bypass_record:
                return False, "Invalid or expired bypass token", None
            
            # Extract bypass type from session_id
            bypass_type = "unknown"
            if bypass_record.session_id:
                if "admin_bypass_" in bypass_record.session_id:
                    bypass_type = "admin_bypass"
                elif "recovery_" in bypass_record.session_id:
                    bypass_type = "recovery_bypass"
            
            bypass_info = {
                "bypass_type": bypass_type,
                "expires_at": bypass_record.expires_at,
                "created_at": bypass_record.created_at,
                "remaining_minutes": int((bypass_record.expires_at - datetime.utcnow()).total_seconds() / 60)
            }
            
            # Consume token if requested
            if consume:
                bypass_record.used = True
                self.db.commit()
                
                # Log bypass usage
                self.audit_service.log_event(
                    MFAAuditEvent.ADMIN_BYPASS,
                    user=user,
                    details={
                        "action": "bypass_token_used",
                        "bypass_type": bypass_type,
                        "token_id": bypass_record.id
                    }
                )
            
            return True, "Bypass token verified", bypass_info
            
        except Exception as e:
            if consume:
                self.db.rollback()
            return False, f"Failed to verify bypass token: {str(e)}", None
    
    def disable_user_mfa_emergency(
        self,
        user: User,
        admin_user_id: str,
        reason: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Emergency MFA disable (admin function)"""
        try:
            if not user.mfa_settings:
                return True, "MFA was not enabled for this user"
            
            # Store current MFA state for potential recovery
            mfa_backup = {
                "totp_enabled": user.mfa_settings.totp_enabled,
                "webauthn_enabled": user.mfa_settings.webauthn_enabled,
                "sms_enabled": user.mfa_settings.sms_enabled,
                "phone_number": user.mfa_settings.sms_phone_number,
                "is_required": user.mfa_settings.is_required
            }
            
            # Disable all MFA methods
            user.mfa_settings.totp_enabled = False
            user.mfa_settings.webauthn_enabled = False
            user.mfa_settings.sms_enabled = False
            user.mfa_settings.is_required = False
            
            # Clear sensitive data
            user.mfa_settings.totp_secret = None
            user.mfa_settings.totp_backup_tokens = None
            user.mfa_settings.sms_phone_number = None
            
            # Delete WebAuthn credentials
            from app.Models import WebAuthnCredential
            self.db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id
            ).delete()
            
            self.db.commit()
            
            # Log emergency disable
            self.audit_service.log_event(
                MFAAuditEvent.MFA_DISABLED,
                user=user,
                admin_user_id=admin_user_id,
                ip_address=ip_address,
                details={
                    "action": "emergency_mfa_disable",
                    "reason": reason,
                    "previous_state": mfa_backup,
                    "admin_initiated": True
                }
            )
            
            return True, "MFA disabled successfully (emergency)"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to disable MFA: {str(e)}"
    
    def get_recovery_options(self, user: User) -> Dict[str, Any]:
        """Get available recovery options for user"""
        recovery_options = {
            "backup_codes_available": False,
            "backup_codes_count": 0,
            "email_recovery": True,  # Always available
            "admin_recovery": True,  # Always available for admins
            "active_bypass_tokens": 0
        }
        
        # Check backup codes
        if user.mfa_settings and user.mfa_settings.totp_backup_tokens:
            backup_codes = user.mfa_settings.totp_backup_tokens.split(",")
            recovery_options["backup_codes_available"] = len(backup_codes) > 0
            recovery_options["backup_codes_count"] = len(backup_codes)
        
        # Check active bypass tokens
        active_bypasses = self.db.query(MFACode).filter(
            and_(
                MFACode.user_id == user.id,
                MFACode.code_type == MFACodeType.EMAIL,
                MFACode.used == False,
                MFACode.expires_at > datetime.utcnow()
            )
        ).count()
        
        recovery_options["active_bypass_tokens"] = active_bypasses
        
        return recovery_options
    
    def get_user_bypass_history(
        self,
        user: User,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get bypass usage history for user"""
        try:
            history = self.audit_service.get_user_audit_history(
                user, 
                days=days,
                event_types=[MFAAuditEvent.ADMIN_BYPASS, MFAAuditEvent.RECOVERY_USED]
            )
            return history
        except Exception:
            return []
    
    def _generate_secure_recovery_code(self, user: User) -> str:
        """Generate cryptographically secure recovery code"""
        # Use user-specific entropy
        entropy_source = f"{user.id}:{user.email}:{datetime.utcnow().timestamp()}"
        
        # Generate base code
        base_code = secrets.token_bytes(self.recovery_code_length)
        
        # Add user-specific salt
        salted_code = hashlib.pbkdf2_hmac(
            'sha256',
            base_code,
            entropy_source.encode('utf-8'),
            50000,  # 50k iterations
            self.recovery_code_length
        )
        
        # Convert to hex and format
        hex_code = salted_code.hex().upper()
        
        # Format as XXXX-XXXX-XXXX-XXXX for readability
        formatted_code = '-'.join([
            hex_code[i:i+4] for i in range(0, min(16, len(hex_code)), 4)
        ])
        
        return formatted_code
    
    def cleanup_expired_codes(self) -> int:
        """Clean up expired recovery codes"""
        try:
            deleted_count = self.db.query(MFACode).filter(
                and_(
                    MFACode.expires_at <= datetime.utcnow(),
                    MFACode.code_type == MFACodeType.EMAIL  # Our bypass codes
                )
            ).delete()
            
            self.db.commit()
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            return 0