from __future__ import annotations

import pyotp
import secrets
import base64
import hashlib
from typing import Tuple, List, Dict, Any, Optional, cast
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import qrcode
import qrcode.image.svg
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SquareGradiantColorMask
import io

from app.Models import User, UserMFASettings
from app.Services.BaseService import BaseService
from app.Services.MFAAuditService import MFAAuditService
from app.Services.MFARateLimitService import MFARateLimitService
from database.migrations.create_mfa_attempts_table import MFAAttemptType, MFAAttemptStatus


class EnhancedTOTPService(BaseService):
    """Enhanced TOTP service with improved security, QR codes, and validation"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.audit_service = MFAAuditService(db)
        self.rate_limit_service = MFARateLimitService(db)
        
        # TOTP Configuration
        self.secret_length = 32  # 160 bits of entropy
        self.interval = 30  # 30 second intervals
        self.digits = 6  # 6 digit codes
        self.algorithm = 'SHA1'  # Most compatible
        self.window = 2  # Allow ±2 time steps (±60 seconds)
        
        # Backup codes configuration
        self.backup_code_length = 8  # 8 character backup codes
        self.backup_code_count = 10  # 10 backup codes
        
        # QR code configuration
        self.qr_version = 1  # Auto-size
        self.qr_error_correct = qrcode.constants.ERROR_CORRECT_M
        self.qr_box_size = 10
        self.qr_border = 4
    
    def generate_secret(self, user: User) -> str:
        """Generate a cryptographically secure TOTP secret"""
        # Use user-specific salt for additional entropy
        salt = f"{user.id}:{user.email}:{datetime.utcnow().isoformat()}"
        
        # Generate base secret
        secret_bytes = secrets.token_bytes(self.secret_length)
        
        # Add user-specific entropy
        salted_secret = hashlib.pbkdf2_hmac(
            'sha256', 
            secret_bytes, 
            salt.encode('utf-8'), 
            100000,  # 100k iterations
            self.secret_length
        )
        
        # Convert to base32 (required for TOTP)
        return base64.b32encode(salted_secret).decode('utf-8')
    
    def get_provisioning_uri(
        self, 
        user: User, 
        secret: str, 
        issuer: str = "FastAPI Laravel"
    ) -> str:
        """Generate enhanced provisioning URI for QR code"""
        totp = pyotp.TOTP(
            secret,
            digits=self.digits,
            digest=self.algorithm.lower(),
            interval=self.interval
        )
        
        return cast(str, totp.provisioning_uri(
            name=user.email,
            issuer_name=issuer,
            image="https://your-domain.com/logo.png"  # Optional logo URL
        ))
    
    def generate_styled_qr_code(
        self, 
        provisioning_uri: str,
        style: str = "default"
    ) -> str:
        """Generate styled QR code image as base64 string"""
        qr = qrcode.QRCode(
            version=self.qr_version,
            error_correction=self.qr_error_correct,
            box_size=self.qr_box_size,
            border=self.qr_border,
        )
        
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        if style == "styled":
            # Create styled QR code with rounded modules and gradient
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                color_mask=SquareGradiantColorMask(
                    back_color=(255, 255, 255),
                    center_color=(0, 100, 200),
                    edge_color=(0, 50, 100)
                )
            )
        elif style == "svg":
            # Generate SVG QR code (scalable)
            img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        else:
            # Default black and white
            img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        img_buffer = io.BytesIO()
        
        if style == "svg":
            img_str = img.to_string(encoding='unicode')
            return f"data:image/svg+xml;charset=utf-8,{img_str}"
        else:
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
    
    def generate_qr_code_with_logo(
        self, 
        provisioning_uri: str,
        logo_data: Optional[bytes] = None
    ) -> str:
        """Generate QR code with embedded logo"""
        from PIL import Image, ImageDraw
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for logo
            box_size=10,
            border=4,
        )
        
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        # Add logo if provided
        if logo_data:
            try:
                logo = Image.open(io.BytesIO(logo_data))
                
                # Calculate logo size (10% of QR code)
                qr_width, qr_height = qr_img.size
                logo_size = min(qr_width, qr_height) // 10
                
                # Resize logo
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Create circular mask for logo
                mask = Image.new('L', (logo_size, logo_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, logo_size, logo_size), fill=255)
                
                # Apply mask to logo
                logo.putalpha(mask)
                
                # Paste logo in center
                pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
                qr_img.paste(logo, pos, logo)
                
            except Exception:
                pass  # Continue without logo if there's an error
        
        # Convert to base64
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token_with_drift_detection(
        self, 
        secret: str, 
        token: str, 
        window: Optional[int] = None
    ) -> Tuple[bool, int]:
        """Verify TOTP token and detect time drift"""
        if window is None:
            window = self.window
        
        totp = pyotp.TOTP(
            secret,
            digits=self.digits,
            digest=self.algorithm.lower(),
            interval=self.interval
        )
        
        # Check current time window first
        if totp.verify(token, window=0):
            return True, 0  # No drift
        
        # Check with drift detection
        for i in range(1, window + 1):
            # Check future windows (client clock ahead)
            if totp.verify(token, window=0, for_time=datetime.utcnow().timestamp() + (i * self.interval)):
                return True, i  # Positive drift
            
            # Check past windows (client clock behind)
            if totp.verify(token, window=0, for_time=datetime.utcnow().timestamp() - (i * self.interval)):
                return True, -i  # Negative drift
        
        return False, 0
    
    def generate_backup_codes_enhanced(self, count: Optional[int] = None) -> List[str]:
        """Generate enhanced backup codes with better entropy"""
        if count is None:
            count = self.backup_code_count
        
        backup_codes = []
        charset = "ABCDEFGHJKMNPQRSTVWXYZ23456789"  # Exclude ambiguous characters
        
        for _ in range(count):
            # Generate backup code with format: XXXX-XXXX
            part1 = ''.join(secrets.choice(charset) for _ in range(4))
            part2 = ''.join(secrets.choice(charset) for _ in range(4))
            backup_codes.append(f"{part1}-{part2}")
        
        return backup_codes
    
    def setup_totp_enhanced(
        self, 
        user: User, 
        issuer: str = "FastAPI Laravel",
        qr_style: str = "default",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Enhanced TOTP setup with better security and options"""
        try:
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.TOTP, ip_address=ip_address, user_agent=user_agent
            )
            if not rate_check[0]:
                return False, rate_check[1], {}
            
            # Check if user already has TOTP enabled
            if user.mfa_settings and user.mfa_settings.totp_enabled:
                return False, "TOTP is already enabled for this user", {}
            
            # Generate secret and backup codes
            secret = self.generate_secret(user)
            backup_codes = self.generate_backup_codes_enhanced()
            provisioning_uri = self.get_provisioning_uri(user, secret, issuer)
            
            # Generate QR code based on style preference
            if qr_style == "styled":
                qr_code = self.generate_styled_qr_code(provisioning_uri, "styled")
            elif qr_style == "svg":
                qr_code = self.generate_styled_qr_code(provisioning_uri, "svg")
            else:
                qr_code = self.generate_styled_qr_code(provisioning_uri, "default")
            
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
            
            # Log setup initiation
            self.audit_service.log_setup_initiated(
                user, "totp", ip_address=ip_address, user_agent=user_agent
            )
            
            return True, "TOTP setup initiated", {
                "qr_code": qr_code,
                "qr_code_svg": self.generate_styled_qr_code(provisioning_uri, "svg"),
                "provisioning_uri": provisioning_uri,
                "backup_codes": backup_codes,
                "secret": secret,  # Remove in production
                "manual_entry": {
                    "issuer": issuer,
                    "account": user.email,
                    "secret": secret,
                    "algorithm": self.algorithm,
                    "digits": self.digits,
                    "period": self.interval
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to setup TOTP: {str(e)}", {}
    
    def verify_and_enable_totp_enhanced(
        self, 
        user: User, 
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Enhanced TOTP verification with drift detection and security logging"""
        try:
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.TOTP, ip_address=ip_address, user_agent=user_agent
            )
            if not rate_check[0]:
                return False, rate_check[1], None
            
            if not user.mfa_settings or not user.mfa_settings.totp_secret:
                return False, "TOTP setup not found. Please setup TOTP first.", None
            
            # Verify the token with drift detection
            verified, drift = self.verify_token_with_drift_detection(
                user.mfa_settings.totp_secret, token
            )
            
            if not verified:
                # Record failed attempt
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.TOTP, MFAAttemptStatus.FAILED,
                    ip_address=ip_address, user_agent=user_agent,
                    failure_reason="Invalid TOTP token"
                )
                
                # Log failed verification
                self.audit_service.log_event(
                    "SETUP_FAILED", user=user, mfa_method="totp",
                    error_message="Invalid TOTP token during setup",
                    ip_address=ip_address
                )
                
                return False, "Invalid TOTP token", None
            
            # Enable TOTP
            user.mfa_settings.totp_enabled = True
            
            # Record successful attempt
            self.rate_limit_service.record_attempt(
                user, MFAAttemptType.TOTP, MFAAttemptStatus.SUCCESS,
                ip_address=ip_address, user_agent=user_agent
            )
            
            self.db.commit()
            
            # Log successful setup
            self.audit_service.log_setup_completed(
                user, "totp", ip_address=ip_address, user_agent=user_agent,
                details={
                    "time_drift": drift,
                    "backup_codes_generated": True
                }
            )
            
            # Return drift information for client adjustment
            setup_info = {
                "time_drift_seconds": drift * self.interval,
                "server_time": datetime.utcnow().isoformat(),
                "backup_codes_count": len(user.mfa_settings.totp_backup_tokens.split(",")) if user.mfa_settings.totp_backup_tokens else 0
            }
            
            return True, "TOTP enabled successfully", setup_info
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to enable TOTP: {str(e)}", None
    
    def verify_totp_for_login_enhanced(
        self, 
        user: User, 
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Enhanced TOTP verification for login with detailed logging"""
        try:
            # Check rate limiting
            rate_check = self.rate_limit_service.check_rate_limit(
                user, MFAAttemptType.TOTP, ip_address=ip_address,
                user_agent=user_agent, device_fingerprint=device_fingerprint
            )
            if not rate_check[0]:
                return False, rate_check[1], None
            
            if not user.mfa_settings or not user.mfa_settings.totp_enabled:
                return False, "TOTP is not enabled for this user", None
            
            if not user.mfa_settings.totp_secret:
                return False, "TOTP secret not found", None
            
            # Check if it's a backup code first
            if self._verify_backup_code_enhanced(user, token):
                # Record successful backup code usage
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.BACKUP_CODE, MFAAttemptStatus.SUCCESS,
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                
                # Log backup code usage (higher risk)
                self.audit_service.log_backup_code_used(
                    user, ip_address=ip_address, user_agent=user_agent
                )
                
                user.mfa_settings.last_used_at = datetime.utcnow()
                self.db.commit()
                
                return True, "Backup code verified", {"method": "backup_code"}
            
            # Verify TOTP token with drift detection
            verified, drift = self.verify_token_with_drift_detection(
                user.mfa_settings.totp_secret, token
            )
            
            if verified:
                # Record successful attempt
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.TOTP, MFAAttemptStatus.SUCCESS,
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                
                # Log successful verification
                self.audit_service.log_verification_success(
                    user, "totp", ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                
                user.mfa_settings.last_used_at = datetime.utcnow()
                self.db.commit()
                
                verification_info = {
                    "method": "totp",
                    "time_drift_seconds": drift * self.interval,
                    "requires_clock_sync": abs(drift) > 1
                }
                
                return True, "TOTP token verified", verification_info
            else:
                # Record failed attempt
                self.rate_limit_service.record_attempt(
                    user, MFAAttemptType.TOTP, MFAAttemptStatus.FAILED,
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint,
                    failure_reason="Invalid TOTP token"
                )
                
                # Log failed verification
                self.audit_service.log_verification_failed(
                    user, "totp", "Invalid TOTP token",
                    ip_address=ip_address, user_agent=user_agent,
                    device_fingerprint=device_fingerprint
                )
                
                return False, "Invalid TOTP token or backup code", None
            
        except Exception as e:
            return False, f"Failed to verify TOTP: {str(e)}", None
    
    def _verify_backup_code_enhanced(self, user: User, code: str) -> bool:
        """Enhanced backup code verification with usage tracking"""
        if not user.mfa_settings or not user.mfa_settings.totp_backup_tokens:
            return False
        
        backup_codes = user.mfa_settings.totp_backup_tokens.split(",")
        code_upper = code.upper().replace("-", "").replace(" ", "")  # Normalize input
        
        # Check against normalized backup codes
        for i, backup_code in enumerate(backup_codes):
            normalized_backup = backup_code.upper().replace("-", "").replace(" ", "")
            if code_upper == normalized_backup:
                # Remove the used backup code
                backup_codes.pop(i)
                user.mfa_settings.totp_backup_tokens = ",".join(backup_codes)
                
                # If running low on backup codes, log a warning
                if len(backup_codes) <= 2:
                    self.audit_service.log_event(
                        "LOW_BACKUP_CODES", user=user, mfa_method="totp",
                        details={"remaining_codes": len(backup_codes)}
                    )
                
                return True
        
        return False
    
    def get_totp_status_enhanced(self, user: User) -> Dict[str, Any]:
        """Get enhanced TOTP status and statistics"""
        if not user.mfa_settings:
            return {
                "enabled": False,
                "setup_required": True,
                "backup_codes_available": 0
            }
        
        # Count remaining backup codes
        backup_codes_count = 0
        if user.mfa_settings.totp_backup_tokens:
            backup_codes_count = len(user.mfa_settings.totp_backup_tokens.split(","))
        
        return {
            "enabled": user.mfa_settings.totp_enabled,
            "setup_required": not user.mfa_settings.totp_enabled,
            "backup_codes_available": backup_codes_count,
            "backup_codes_low": backup_codes_count <= 2,
            "last_used": user.mfa_settings.last_used_at,
            "configuration": {
                "algorithm": self.algorithm,
                "digits": self.digits,
                "interval": self.interval,
                "window": self.window
            }
        }