from __future__ import annotations

import secrets
import json
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.Models import User, UserMFASettings, MFACode, MFASession, MFACodeType, MFASessionStatus
from app.Services.BaseService import BaseService
from app.Services.TOTPService import TOTPService
from app.Services.WebAuthnService import WebAuthnService


class MFAService(BaseService):
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.totp_service = TOTPService(db)
        self.webauthn_service = WebAuthnService(db)
    
    def get_mfa_status(self, user: User) -> Dict[str, Any]:
        """Get comprehensive MFA status for user"""
        if not user.mfa_settings:
            return {
                "mfa_enabled": False,
                "mfa_required": False,
                "methods": {
                    "totp": {"enabled": False, "setup": False},
                    "webauthn": {"enabled": False, "credentials_count": 0},
                    "sms": {"enabled": False, "phone_number": None}
                }
            }
        
        settings = user.mfa_settings
        return {
            "mfa_enabled": user.has_mfa_enabled(),
            "mfa_required": settings.is_required,
            "methods": {
                "totp": {
                    "enabled": settings.totp_enabled,
                    "setup": settings.totp_secret is not None
                },
                "webauthn": {
                    "enabled": settings.webauthn_enabled,
                    "credentials_count": len(user.webauthn_credentials)
                },
                "sms": {
                    "enabled": settings.sms_enabled,
                    "phone_number": settings.sms_phone_number
                }
            }
        }
    
    def require_mfa(self, user: User) -> Tuple[bool, str]:
        """Enable MFA requirement for user"""
        try:
            if not user.mfa_settings:
                mfa_settings = UserMFASettings(
                    user_id=user.id,
                    is_required=True
                )
                self.db.add(mfa_settings)
            else:
                user.mfa_settings.is_required = True
            
            self.db.commit()
            return True, "MFA requirement enabled"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to require MFA: {str(e)}"
    
    def remove_mfa_requirement(self, user: User) -> Tuple[bool, str]:
        """Remove MFA requirement for user"""
        try:
            if user.mfa_settings:
                user.mfa_settings.is_required = False
                self.db.commit()
                return True, "MFA requirement removed"
            
            return True, "MFA requirement was not set"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to remove MFA requirement: {str(e)}"
    
    def create_mfa_session(self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Create an MFA session for authentication"""
        try:
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            
            # Create MFA session
            mfa_session = MFASession(
                user_id=user.id,
                session_token=session_token,
                status=MFASessionStatus.PENDING,
                expires_at=datetime.utcnow() + timedelta(minutes=10),  # 10 minute expiry
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(mfa_session)
            self.db.commit()
            
            return True, "MFA session created", session_token
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create MFA session: {str(e)}", None
    
    def get_mfa_session(self, session_token: str) -> Optional[MFASession]:
        """Get MFA session by token"""
        return self.db.query(MFASession).filter(
            MFASession.session_token == session_token,
            MFASession.expires_at > datetime.utcnow()
        ).first()
    
    def verify_mfa_with_totp(self, session_token: str, totp_code: str) -> Tuple[bool, str]:
        """Verify MFA using TOTP"""
        try:
            session = self.get_mfa_session(session_token)
            if not session:
                return False, "Invalid or expired MFA session"
            
            if session.status != MFASessionStatus.PENDING:
                return False, "MFA session is not pending"
            
            user = session.user
            success, message = self.totp_service.verify_totp_for_login(user, totp_code)
            
            if success:
                session.status = MFASessionStatus.VERIFIED
                session.method_used = "totp"
                session.verified_at = datetime.utcnow()
                self.db.commit()
                return True, "TOTP verification successful"
            else:
                session.status = MFASessionStatus.FAILED
                self.db.commit()
                return False, message
                
        except Exception as e:
            return False, f"Failed to verify TOTP: {str(e)}"
    
    def verify_mfa_with_webauthn(self, session_token: str, credential: Dict[str, Any], challenge: str) -> Tuple[bool, str]:
        """Verify MFA using WebAuthn"""
        try:
            session = self.get_mfa_session(session_token)
            if not session:
                return False, "Invalid or expired MFA session"
            
            if session.status != MFASessionStatus.PENDING:
                return False, "MFA session is not pending"
            
            user = session.user
            success, message = self.webauthn_service.verify_authentication(user, credential, challenge)
            
            if success:
                session.status = MFASessionStatus.VERIFIED
                session.method_used = "webauthn"
                session.verified_at = datetime.utcnow()
                self.db.commit()
                return True, "WebAuthn verification successful"
            else:
                session.status = MFASessionStatus.FAILED
                self.db.commit()
                return False, message
                
        except Exception as e:
            return False, f"Failed to verify WebAuthn: {str(e)}"
    
    def verify_mfa_with_sms(self, session_token: str, sms_code: str) -> Tuple[bool, str]:
        """Verify MFA using SMS (placeholder - implement SMS service)"""
        try:
            session = self.get_mfa_session(session_token)
            if not session:
                return False, "Invalid or expired MFA session"
            
            if session.status != MFASessionStatus.PENDING:
                return False, "MFA session is not pending"
            
            # Find the most recent SMS code for this user
            latest_code = self.db.query(MFACode).filter(
                MFACode.user_id == session.user_id,
                MFACode.code_type == MFACodeType.SMS,
                MFACode.used == False,
                MFACode.expires_at > datetime.utcnow()
            ).order_by(MFACode.created_at.desc()).first()
            
            if not latest_code or latest_code.code != sms_code:
                return False, "Invalid or expired SMS code"
            
            # Mark code as used
            latest_code.used = True
            session.verified_at = datetime.utcnow()
            session.status = MFASessionStatus.VERIFIED
            self.db.commit()
            
            return True, "SMS code verified successfully"
                
        except Exception as e:
            return False, f"Failed to verify SMS: {str(e)}"
    
    def generate_sms_code(self, user: User) -> Tuple[bool, str]:
        """Generate and send SMS code (placeholder)"""
        try:
            if not user.mfa_settings or not user.mfa_settings.sms_enabled:
                return False, "SMS MFA is not enabled for this user"
            
            if not user.mfa_settings.sms_phone_number:
                return False, "No phone number configured for SMS MFA"
            
            # Generate 6-digit code
            code = str(secrets.randbelow(1000000)).zfill(6)
            
            # Store code in database
            mfa_code = MFACode(
                user_id=user.id,
                code=code,
                code_type=MFACodeType.SMS,
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            )
            
            self.db.add(mfa_code)
            self.db.commit()
            
            # In production, integrate with SMS service like Twilio:
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # message = client.messages.create(
            #     body=f"Your MFA code is: {code}",
            #     from_='+1234567890',
            #     to=user.mfa_settings.sms_phone_number
            # )
            
            # For development, log the code (remove in production)
            import logging
            logging.info(f"SMS MFA code for user {user.id}: {code}")
            
            return True, "SMS code sent successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to generate SMS code: {str(e)}"
    
    def setup_sms_mfa(self, user: User, phone_number: str, verification_code: str) -> Tuple[bool, str]:
        """Setup SMS MFA (placeholder)"""
        try:
            # In production, verify phone number first:
            # Send verification code to phone_number and validate verification_code
            # This is a simplified setup for development
            if not phone_number or len(phone_number) < 10:
                return False, "Invalid phone number format"
            
            # Basic phone number validation
            import re
            if not re.match(r'^\+?[1-9]\d{1,14}$', phone_number.replace('-', '').replace(' ', '')):
                return False, "Invalid phone number format"
            
            if not user.mfa_settings:
                mfa_settings = UserMFASettings(
                    user_id=user.id,
                    sms_enabled=True,
                    sms_phone_number=phone_number
                )
                self.db.add(mfa_settings)
            else:
                user.mfa_settings.sms_enabled = True
                user.mfa_settings.sms_phone_number = phone_number
            
            self.db.commit()
            return True, "SMS MFA enabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to setup SMS MFA: {str(e)}"
    
    def disable_sms_mfa(self, user: User) -> Tuple[bool, str]:
        """Disable SMS MFA"""
        try:
            if user.mfa_settings:
                user.mfa_settings.sms_enabled = False
                user.mfa_settings.sms_phone_number = None
                self.db.commit()
                return True, "SMS MFA disabled successfully"
            
            return True, "SMS MFA was not enabled"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to disable SMS MFA: {str(e)}"
    
    def disable_all_mfa(self, user: User, verification_method: str, verification_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Disable all MFA methods for user"""
        try:
            # Verify user identity before disabling all MFA
            verified = False
            
            if verification_method == "totp" and "token" in verification_data:
                success, _ = self.totp_service.verify_totp_for_login(user, verification_data["token"])
                verified = success
            elif verification_method == "webauthn" and "credential" in verification_data and "challenge" in verification_data:
                success, _ = self.webauthn_service.verify_authentication(
                    user, verification_data["credential"], verification_data["challenge"]
                )
                verified = success
            elif verification_method == "password" and "password" in verification_data:
                verified = user.verify_password(verification_data["password"])
            
            if not verified:
                return False, "Verification failed"
            
            # Disable all MFA methods
            if user.mfa_settings:
                # Disable TOTP
                user.mfa_settings.totp_enabled = False
                user.mfa_settings.totp_secret = None
                user.mfa_settings.totp_backup_tokens = None
                
                # Disable WebAuthn
                self.webauthn_service.disable_webauthn(user)
                
                # Disable SMS
                user.mfa_settings.sms_enabled = False
                user.mfa_settings.sms_phone_number = None
                user.mfa_settings.is_required = False
            
            self.db.commit()
            return True, "All MFA methods disabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to disable MFA: {str(e)}"
    
    def get_available_mfa_methods(self, user: User) -> List[str]:
        """Get list of available MFA methods for user"""
        if not user.mfa_settings:
            return []
        
        methods = []
        if user.mfa_settings.totp_enabled:
            methods.append("totp")
        if user.mfa_settings.webauthn_enabled:
            methods.append("webauthn")
        if user.mfa_settings.sms_enabled:
            methods.append("sms")
        
        return methods
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired MFA sessions"""
        try:
            expired_count = self.db.query(MFASession).filter(
                MFASession.expires_at <= datetime.utcnow()
            ).delete()
            
            self.db.commit()
            return expired_count
            
        except Exception as e:
            self.db.rollback()
            return 0