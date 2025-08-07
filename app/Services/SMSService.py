from __future__ import annotations

import secrets
import re
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.Models import User, UserMFASettings, MFACode
from app.Services.BaseService import BaseService
from app.Services.MFAAuditService import MFAAuditService
from app.Services.MFARateLimitService import MFARateLimitService
from database.migrations.create_mfa_codes_table import MFACodeType, MFACode as MFACodeModel
from database.migrations.create_mfa_attempts_table import MFAAttemptType, MFAAttemptStatus
from config.settings import settings

# Optional Twilio import (install with: pip install twilio)
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None
    TwilioRestException = Exception


class SMSService(BaseService):
    """SMS MFA service with Twilio integration and security features"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.audit_service = MFAAuditService(db)
        self.rate_limit_service = MFARateLimitService(db)
        
        # Twilio configuration
        self.twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.twilio_phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        # Initialize Twilio client if available and configured
        self.twilio_client = None
        if TWILIO_AVAILABLE and self.twilio_account_sid and self.twilio_auth_token:
            try:
                self.twilio_client = TwilioClient(
                    self.twilio_account_sid, 
                    self.twilio_auth_token
                )
            except Exception:
                self.twilio_client = None
        
        # SMS configuration
        self.code_length = 6
        self.code_expiry_minutes = 5
        self.max_attempts_per_phone = 5
        self.max_codes_per_hour = 10
    
    def setup_sms_mfa(
        self, 
        user: User, 
        phone_number: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Setup SMS MFA for user"""
        try:
            # Validate and normalize phone number
            normalized_phone = self._normalize_phone_number(phone_number)
            if not normalized_phone:
                return False, "Invalid phone number format", None
            
            # Check if phone number is already used by another user
            existing_user = self.db.query(UserMFASettings).filter(
                UserMFASettings.sms_phone_number == normalized_phone,
                UserMFASettings.user_id != user.id
            ).first()
            
            if existing_user:
                return False, "Phone number already registered to another account", None
            
            # Generate verification code
            success, message, verification_code = self._generate_sms_code(
                user, normalized_phone, ip_address, user_agent
            )
            
            if not success:
                return False, message, None
            
            # Send verification code
            send_success, send_message = self._send_sms_code(
                normalized_phone, verification_code, "SMS MFA Setup"
            )
            
            if not send_success:
                return False, f"Failed to send SMS: {send_message}", None
            
            # Log setup initiation
            self.audit_service.log_setup_initiated(
                user, "sms", ip_address=ip_address, user_agent=user_agent
            )
            
            return True, "SMS verification code sent", verification_code
            
        except Exception as e:
            return False, f"Failed to setup SMS MFA: {str(e)}", None
    
    def verify_sms_setup(
        self,
        user: User,
        phone_number: str,
        verification_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify SMS setup and enable SMS MFA"""
        try:
            # Normalize phone number
            normalized_phone = self._normalize_phone_number(phone_number)
            if not normalized_phone:
                return False, "Invalid phone number format"
            
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.SMS, ip_address=ip_address, user_agent=user_agent
            )
            if not rate_check[0]:
                return False, rate_check[1]
            
            # Find and verify the code
            success, message = self._verify_sms_code(
                user, verification_code, MFACodeType.SMS
            )
            
            if not success:
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.SMS, MFAAttemptStatus.FAILED,
                    ip_address=ip_address, user_agent=user_agent,
                    failure_reason=message
                )
                
                self.audit_service.log_event(
                    "SETUP_FAILED", user=user, mfa_method="sms",
                    error_message=message, ip_address=ip_address
                )
                return False, message
            
            # Enable SMS MFA
            if not user.mfa_settings:
                mfa_settings = UserMFASettings(
                    user_id=user.id,
                    sms_enabled=True,
                    sms_phone_number=normalized_phone
                )
                self.db.add(mfa_settings)
            else:
                user.mfa_settings.sms_enabled = True
                user.mfa_settings.sms_phone_number = normalized_phone
            
            # Record successful attempt
            self.rate_limit_service.record_attempt(
                user, MFAAttemptType.SMS, MFAAttemptStatus.SUCCESS,
                ip_address=ip_address, user_agent=user_agent
            )
            
            self.db.commit()
            
            # Log successful setup
            self.audit_service.log_setup_completed(
                user, "sms", ip_address=ip_address, user_agent=user_agent,
                details={"phone_number": self._mask_phone_number(normalized_phone)}
            )
            
            return True, "SMS MFA enabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify SMS setup: {str(e)}"
    
    def send_sms_code_for_login(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Send SMS code for MFA verification during login"""
        try:
            if not user.mfa_settings or not user.mfa_settings.sms_enabled:
                return False, "SMS MFA is not enabled for this user", None
            
            if not user.mfa_settings.sms_phone_number:
                return False, "No phone number configured for SMS MFA", None
            
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.SMS, ip_address=ip_address, user_agent=user_agent
            )
            if not rate_check[0]:
                return False, rate_check[1], None
            
            # Generate and send code
            success, message, code = self._generate_sms_code(
                user, user.mfa_settings.sms_phone_number, ip_address, user_agent
            )
            
            if not success:
                return False, message, None
            
            send_success, send_message = self._send_sms_code(
                user.mfa_settings.sms_phone_number, code, "MFA Verification"
            )
            
            if not send_success:
                return False, f"Failed to send SMS: {send_message}", None
            
            masked_phone = self._mask_phone_number(user.mfa_settings.sms_phone_number)
            return True, f"SMS code sent to {masked_phone}", code
            
        except Exception as e:
            return False, f"Failed to send SMS code: {str(e)}", None
    
    def verify_sms_code_for_login(
        self,
        user: User,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify SMS code for MFA login"""
        try:
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.SMS, ip_address=ip_address, user_agent=user_agent
            )
            if not rate_check[0]:
                return False, rate_check[1]
            
            # Verify the code
            success, message = self._verify_sms_code(user, code, MFACodeType.SMS)
            
            if success:
                # Record successful attempt
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.SMS, MFAAttemptStatus.SUCCESS,
                    ip_address=ip_address, user_agent=user_agent
                )
                
                # Update last used time
                if user.mfa_settings:
                    user.mfa_settings.last_used_at = datetime.utcnow()
                
                self.db.commit()
                
                # Log successful verification
                self.audit_service.log_verification_success(
                    user, "sms", ip_address=ip_address, user_agent=user_agent
                )
                
                return True, "SMS code verified successfully"
            else:
                # Record failed attempt
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.SMS, MFAAttemptStatus.FAILED,
                    ip_address=ip_address, user_agent=user_agent,
                    failure_reason=message
                )
                
                # Log failed verification
                self.audit_service.log_verification_failed(
                    user, "sms", message, ip_address=ip_address, user_agent=user_agent
                )
                
                return False, message
                
        except Exception as e:
            return False, f"Failed to verify SMS code: {str(e)}"
    
    def disable_sms_mfa(
        self,
        user: User,
        verification_code: Optional[str] = None,
        admin_user_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Disable SMS MFA for user"""
        try:
            if not user.mfa_settings:
                return True, "SMS MFA was not enabled"
            
            # If not admin bypass, require verification
            if not admin_user_id and verification_code:
                success, message = self._verify_sms_code(user, verification_code, MFACodeType.SMS)
                if not success:
                    return False, f"Verification failed: {message}"
            
            # Store old phone for logging
            old_phone = user.mfa_settings.sms_phone_number
            
            # Disable SMS MFA
            user.mfa_settings.sms_enabled = False
            user.mfa_settings.sms_phone_number = None
            
            # Clean up any pending SMS codes
            self.db.query(MFACodeModel).filter(
                MFACodeModel.user_id == user.id,
                MFACodeModel.code_type == MFACodeType.SMS,
                MFACodeModel.used == False
            ).delete()
            
            self.db.commit()
            
            # Log the disable action
            if admin_user_id:
                self.audit_service.log_admin_bypass(
                    user, admin_user_id, "SMS MFA disabled by admin"
                )
            else:
                self.audit_service.log_event(
                    "MFA_DISABLED", user=user, mfa_method="sms",
                    details={"phone_number": self._mask_phone_number(old_phone) if old_phone else None}
                )
            
            return True, "SMS MFA disabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to disable SMS MFA: {str(e)}"
    
    def _generate_sms_code(
        self,
        user: User,
        phone_number: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Generate SMS verification code"""
        try:
            # Check hourly limit for this phone number
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_codes = self.db.query(MFACodeModel).filter(
                MFACodeModel.code_type == MFACodeType.SMS,
                MFACodeModel.created_at >= hour_ago
            ).count()
            
            if recent_codes >= self.max_codes_per_hour:
                return False, "Hourly SMS limit reached. Please wait.", None
            
            # Generate secure random code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(self.code_length)])
            
            # Store code in database
            expires_at = datetime.utcnow() + timedelta(minutes=self.code_expiry_minutes)
            
            mfa_code = MFACodeModel(
                user_id=user.id,
                code=code,
                code_type=MFACodeType.SMS,
                expires_at=expires_at,
                used=False
            )
            
            self.db.add(mfa_code)
            self.db.commit()
            
            return True, "SMS code generated", code
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to generate SMS code: {str(e)}", None
    
    def _verify_sms_code(
        self,
        user: User,
        code: str,
        code_type: MFACodeType
    ) -> Tuple[bool, str]:
        """Verify SMS code"""
        try:
            # Find valid, unused code
            valid_code = self.db.query(MFACodeModel).filter(
                MFACodeModel.user_id == user.id,
                MFACodeModel.code == code,
                MFACodeModel.code_type == code_type,
                MFACodeModel.used == False,
                MFACodeModel.expires_at > datetime.utcnow()
            ).first()
            
            if not valid_code:
                return False, "Invalid or expired SMS code"
            
            # Mark code as used
            valid_code.used = True
            self.db.commit()
            
            return True, "SMS code verified"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to verify SMS code: {str(e)}"
    
    def _send_sms_code(
        self,
        phone_number: str,
        code: str,
        purpose: str
    ) -> Tuple[bool, str]:
        """Send SMS code using Twilio"""
        if not self.twilio_client:
            # In development/testing, just return success with the code
            if getattr(settings, 'DEBUG', False):
                return True, f"[DEBUG] SMS code: {code}"
            return False, "SMS service not configured"
        
        try:
            message_body = f"Your {purpose} code is: {code}. This code expires in {self.code_expiry_minutes} minutes."
            
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=self.twilio_phone_number,
                to=phone_number
            )
            
            return True, f"SMS sent successfully (SID: {message.sid})"
            
        except Exception as e:
            if isinstance(e, TwilioRestException):
                return False, f"Twilio error: {e.msg}"
            return False, f"Failed to send SMS: {str(e)}"
    
    def _normalize_phone_number(self, phone_number: str) -> Optional[str]:
        """Normalize phone number to E.164 format"""
        # Remove all non-digits
        digits_only = re.sub(r'[^\d]', '', phone_number)
        
        # Basic validation
        if len(digits_only) < 10 or len(digits_only) > 15:
            return None
        
        # Add country code if missing (assuming US +1)
        if len(digits_only) == 10:
            digits_only = '1' + digits_only
        
        # Add + prefix
        return '+' + digits_only
    
    def _mask_phone_number(self, phone_number: str) -> str:
        """Mask phone number for display"""
        if not phone_number:
            return ""
        
        if len(phone_number) >= 4:
            return phone_number[:-4] + '****'
        return '****'
    
    def get_sms_status(self, user: User) -> Dict[str, Any]:
        """Get SMS MFA status and statistics"""
        if not user.mfa_settings:
            return {
                "enabled": False,
                "phone_number": None,
                "setup_required": True
            }
        
        # Count recent SMS codes
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_codes = self.db.query(MFACodeModel).filter(
            MFACodeModel.user_id == user.id,
            MFACodeModel.code_type == MFACodeType.SMS,
            MFACodeModel.created_at >= hour_ago
        ).count()
        
        return {
            "enabled": user.mfa_settings.sms_enabled,
            "phone_number": self._mask_phone_number(user.mfa_settings.sms_phone_number) if user.mfa_settings.sms_phone_number else None,
            "setup_required": not user.mfa_settings.sms_enabled,
            "recent_codes_sent": recent_codes,
            "hourly_limit": self.max_codes_per_hour,
            "last_used": user.mfa_settings.last_used_at
        }