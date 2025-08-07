from __future__ import annotations

import pyotp
import secrets
from typing import Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from app.Models import User, UserMFASettings
from app.Services.BaseService import BaseService
import qrcode
import io
import base64


class TOTPService(BaseService):
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret for the user"""
        return pyotp.random_base32()
    
    def get_provisioning_uri(self, user: User, secret: str, issuer: str = "FastAPI Laravel") -> str:
        """Generate provisioning URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.email,
            issuer_name=issuer
        )
    
    def generate_qr_code(self, provisioning_uri: str) -> str:
        """Generate QR code image as base64 string"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, window=window)
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for recovery"""
        backup_codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            backup_codes.append(code)
        return backup_codes
    
    def setup_totp(self, user: User, issuer: str = "FastAPI Laravel") -> Tuple[bool, str, Dict[str, Any]]:
        """Setup TOTP for user and return QR code data"""
        try:
            # Check if user already has TOTP enabled
            if user.mfa_settings and user.mfa_settings.totp_enabled:
                return False, "TOTP is already enabled for this user", {}
            
            # Generate secret and backup codes
            secret = self.generate_secret()
            backup_codes = self.generate_backup_codes()
            provisioning_uri = self.get_provisioning_uri(user, secret, issuer)
            qr_code = self.generate_qr_code(provisioning_uri)
            
            # Create or update MFA settings (but don't enable yet - wait for verification)
            if not user.mfa_settings:
                mfa_settings = UserMFASettings(
                    user_id=user.id,
                    totp_secret=secret,
                    totp_backup_tokens=",".join(backup_codes)
                )
                self.db.add(mfa_settings)
            else:
                user.mfa_settings.totp_secret = secret
                user.mfa_settings.totp_backup_tokens = ",".join(backup_codes)
            
            self.db.commit()
            
            return True, "TOTP setup initiated", {
                "qr_code": qr_code,
                "provisioning_uri": provisioning_uri,
                "backup_codes": backup_codes,
                "secret": secret  # Only return for testing - remove in production
            }
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to setup TOTP: {str(e)}", {}
    
    def verify_and_enable_totp(self, user: User, token: str) -> Tuple[bool, str]:
        """Verify TOTP token and enable TOTP for user"""
        try:
            if not user.mfa_settings or not user.mfa_settings.totp_secret:
                return False, "TOTP setup not found. Please setup TOTP first."
            
            # Verify the token
            if not self.verify_token(user.mfa_settings.totp_secret, token):
                return False, "Invalid TOTP token"
            
            # Enable TOTP
            user.mfa_settings.totp_enabled = True
            self.db.commit()
            
            return True, "TOTP enabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to enable TOTP: {str(e)}"
    
    def verify_totp_for_login(self, user: User, token: str) -> Tuple[bool, str]:
        """Verify TOTP token during login"""
        try:
            if not user.mfa_settings or not user.mfa_settings.totp_enabled:
                return False, "TOTP is not enabled for this user"
            
            if not user.mfa_settings.totp_secret:
                return False, "TOTP secret not found"
            
            # Check if it's a backup code first
            if self._verify_backup_code(user, token):
                return True, "Backup code verified"
            
            # Verify TOTP token
            if self.verify_token(user.mfa_settings.totp_secret, token):
                user.mfa_settings.last_used_at = datetime.utcnow()
                self.db.commit()
                return True, "TOTP token verified"
            
            return False, "Invalid TOTP token or backup code"
            
        except Exception as e:
            return False, f"Failed to verify TOTP: {str(e)}"
    
    def disable_totp(self, user: User, token: str) -> Tuple[bool, str]:
        """Disable TOTP for user"""
        try:
            if not user.mfa_settings or not user.mfa_settings.totp_enabled:
                return False, "TOTP is not enabled for this user"
            
            # Verify token before disabling
            if not self.verify_token(user.mfa_settings.totp_secret, token):
                return False, "Invalid TOTP token"
            
            # Disable TOTP
            user.mfa_settings.totp_enabled = False
            user.mfa_settings.totp_secret = None
            user.mfa_settings.totp_backup_tokens = None
            
            self.db.commit()
            
            return True, "TOTP disabled successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to disable TOTP: {str(e)}"
    
    def regenerate_backup_codes(self, user: User, totp_token: str) -> Tuple[bool, str, List[str]]:
        """Regenerate backup codes"""
        try:
            if not user.mfa_settings or not user.mfa_settings.totp_enabled:
                return False, "TOTP is not enabled for this user", []
            
            # Verify TOTP token
            if not self.verify_token(user.mfa_settings.totp_secret, totp_token):
                return False, "Invalid TOTP token", []
            
            # Generate new backup codes
            backup_codes = self.generate_backup_codes()
            user.mfa_settings.totp_backup_tokens = ",".join(backup_codes)
            
            self.db.commit()
            
            return True, "Backup codes regenerated successfully", backup_codes
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to regenerate backup codes: {str(e)}", []
    
    def _verify_backup_code(self, user: User, code: str) -> bool:
        """Verify and consume a backup code"""
        if not user.mfa_settings or not user.mfa_settings.totp_backup_tokens:
            return False
        
        backup_codes = user.mfa_settings.totp_backup_tokens.split(",")
        code_upper = code.upper()
        
        if code_upper in backup_codes:
            # Remove the used backup code
            backup_codes.remove(code_upper)
            user.mfa_settings.totp_backup_tokens = ",".join(backup_codes)
            return True
        
        return False