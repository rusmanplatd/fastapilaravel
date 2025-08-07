from __future__ import annotations

import hashlib
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.Models import User
from app.Services.BaseService import BaseService
from database.migrations.create_mfa_attempts_table import MFAAttempt, MFAAttemptStatus, MFAAttemptType


class MFARateLimitService(BaseService):
    """Advanced rate limiting service for MFA attempts"""
    
    # Rate limiting configuration
    MAX_ATTEMPTS_PER_MINUTE = 5
    MAX_ATTEMPTS_PER_HOUR = 20
    MAX_ATTEMPTS_PER_DAY = 100
    PROGRESSIVE_DELAY_BASE = 2  # seconds
    MAX_PROGRESSIVE_DELAY = 300  # 5 minutes
    BLOCK_DURATION_MINUTES = 15
    ESCALATION_THRESHOLD = 10  # attempts before escalation
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def check_rate_limit(
        self, 
        user: User, 
        attempt_type: MFAAttemptType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Check if user/IP is rate limited
        Returns: (is_allowed, message, retry_after_seconds)
        """
        try:
            now = datetime.utcnow()
            
            # Check if user is currently blocked
            blocked_attempt = self.db.query(MFAAttempt).filter(
                and_(
                    MFAAttempt.user_id == user.id,
                    MFAAttempt.blocked_until.is_not(None),
                    MFAAttempt.blocked_until > now
                )
            ).first()
            
            if blocked_attempt:
                retry_after = int((blocked_attempt.blocked_until - now).total_seconds())
                return False, f"Account temporarily blocked. Try again in {retry_after} seconds", retry_after
            
            # Check attempts in different time windows
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Count recent attempts by user
            minute_attempts = self._count_failed_attempts(user.id, minute_ago)
            hour_attempts = self._count_failed_attempts(user.id, hour_ago)
            day_attempts = self._count_failed_attempts(user.id, day_ago)
            
            # Count recent attempts by IP (if provided)
            ip_minute_attempts = 0
            ip_hour_attempts = 0
            if ip_address:
                ip_minute_attempts = self._count_failed_attempts_by_ip(ip_address, minute_ago)
                ip_hour_attempts = self._count_failed_attempts_by_ip(ip_address, hour_ago)
            
            # Check various rate limits
            if minute_attempts >= self.MAX_ATTEMPTS_PER_MINUTE:
                return False, "Too many attempts. Please wait a minute before trying again.", 60
            
            if ip_minute_attempts >= self.MAX_ATTEMPTS_PER_MINUTE * 2:  # More lenient for IP
                return False, "Too many attempts from this IP. Please wait.", 60
            
            if hour_attempts >= self.MAX_ATTEMPTS_PER_HOUR:
                return False, "Hourly attempt limit exceeded. Please wait an hour.", 3600
            
            if ip_hour_attempts >= self.MAX_ATTEMPTS_PER_HOUR * 3:
                return False, "Too many attempts from this IP this hour.", 3600
            
            if day_attempts >= self.MAX_ATTEMPTS_PER_DAY:
                return False, "Daily attempt limit exceeded. Please contact support.", 86400
            
            # Check for suspicious patterns
            device_attempts = 0
            if device_fingerprint:
                device_attempts = self._count_failed_attempts_by_device(device_fingerprint, hour_ago)
                if device_attempts >= 30:  # Device-based limit
                    return False, "Too many attempts from this device.", 3600
            
            # Calculate progressive delay based on recent failures
            progressive_delay = self._calculate_progressive_delay(user.id)
            if progressive_delay > 0:
                return False, f"Please wait {progressive_delay} seconds before next attempt.", progressive_delay
            
            return True, "Rate limit check passed", None
            
        except Exception as e:
            # Fail-safe: if rate limiting service fails, allow the attempt but log it
            return True, f"Rate limiting error: {str(e)}", None
    
    def record_attempt(
        self,
        user: User,
        attempt_type: MFAAttemptType,
        status: MFAAttemptStatus,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Record MFA attempt for rate limiting and monitoring"""
        try:
            # Check if we need to block the user
            blocked_until = None
            if status == MFAAttemptStatus.FAILED:
                recent_failures = self._count_failed_attempts(user.id, datetime.utcnow() - timedelta(minutes=10))
                if recent_failures >= self.ESCALATION_THRESHOLD:
                    blocked_until = datetime.utcnow() + timedelta(minutes=self.BLOCK_DURATION_MINUTES)
            
            attempt = MFAAttempt(
                user_id=user.id,
                attempt_type=attempt_type,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=failure_reason,
                device_fingerprint=device_fingerprint,
                session_id=session_id,
                blocked_until=blocked_until
            )
            
            self.db.add(attempt)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def _count_failed_attempts(self, user_id: str, since: datetime) -> int:
        """Count failed MFA attempts for user since given time"""
        return self.db.query(MFAAttempt).filter(
            and_(
                MFAAttempt.user_id == user_id,
                MFAAttempt.status == MFAAttemptStatus.FAILED,
                MFAAttempt.created_at >= since
            )
        ).count()
    
    def _count_failed_attempts_by_ip(self, ip_address: str, since: datetime) -> int:
        """Count failed MFA attempts from IP since given time"""
        return self.db.query(MFAAttempt).filter(
            and_(
                MFAAttempt.ip_address == ip_address,
                MFAAttempt.status == MFAAttemptStatus.FAILED,
                MFAAttempt.created_at >= since
            )
        ).count()
    
    def _count_failed_attempts_by_device(self, device_fingerprint: str, since: datetime) -> int:
        """Count failed MFA attempts from device since given time"""
        return self.db.query(MFAAttempt).filter(
            and_(
                MFAAttempt.device_fingerprint == device_fingerprint,
                MFAAttempt.status == MFAAttemptStatus.FAILED,
                MFAAttempt.created_at >= since
            )
        ).count()
    
    def _calculate_progressive_delay(self, user_id: str) -> int:
        """Calculate progressive delay based on recent consecutive failures"""
        recent_time = datetime.utcnow() - timedelta(minutes=5)
        
        # Get recent attempts in chronological order
        recent_attempts = self.db.query(MFAAttempt).filter(
            and_(
                MFAAttempt.user_id == user_id,
                MFAAttempt.created_at >= recent_time
            )
        ).order_by(MFAAttempt.created_at.desc()).limit(10).all()
        
        # Count consecutive failures from most recent
        consecutive_failures = 0
        for attempt in recent_attempts:
            if attempt.status == MFAAttemptStatus.FAILED:
                consecutive_failures += 1
            else:
                break
        
        if consecutive_failures >= 3:
            # Exponential backoff: 2^failures seconds, capped at MAX_PROGRESSIVE_DELAY
            delay = min(self.PROGRESSIVE_DELAY_BASE ** consecutive_failures, self.MAX_PROGRESSIVE_DELAY)
            
            # Check if enough time has passed since last attempt
            if recent_attempts:
                last_attempt = recent_attempts[0]
                time_since_last = (datetime.utcnow() - last_attempt.created_at).total_seconds()
                remaining_delay = max(0, delay - int(time_since_last))
                return remaining_delay
        
        return 0
    
    def get_rate_limit_status(self, user: User) -> Dict[str, Any]:
        """Get detailed rate limiting status for user"""
        now = datetime.utcnow()
        
        # Time windows
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count attempts in different windows
        minute_attempts = self._count_failed_attempts(user.id, minute_ago)
        hour_attempts = self._count_failed_attempts(user.id, hour_ago)
        day_attempts = self._count_failed_attempts(user.id, day_ago)
        
        # Check if blocked
        blocked_attempt = self.db.query(MFAAttempt).filter(
            and_(
                MFAAttempt.user_id == user.id,
                MFAAttempt.blocked_until.is_not(None),
                MFAAttempt.blocked_until > now
            )
        ).first()
        
        blocked_until = None
        if blocked_attempt:
            blocked_until = blocked_attempt.blocked_until
        
        return {
            "attempts_last_minute": minute_attempts,
            "attempts_last_hour": hour_attempts,
            "attempts_last_day": day_attempts,
            "max_attempts_per_minute": self.MAX_ATTEMPTS_PER_MINUTE,
            "max_attempts_per_hour": self.MAX_ATTEMPTS_PER_HOUR,
            "max_attempts_per_day": self.MAX_ATTEMPTS_PER_DAY,
            "is_blocked": blocked_until is not None,
            "blocked_until": blocked_until,
            "progressive_delay": self._calculate_progressive_delay(user.id)
        }
    
    def unblock_user(self, user: User, admin_user_id: Optional[str] = None) -> bool:
        """Manually unblock a user (admin function)"""
        try:
            # Remove all blocks for this user
            blocked_attempts = self.db.query(MFAAttempt).filter(
                and_(
                    MFAAttempt.user_id == user.id,
                    MFAAttempt.blocked_until.is_not(None),
                    MFAAttempt.blocked_until > datetime.utcnow()
                )
            ).all()
            
            for attempt in blocked_attempts:
                attempt.blocked_until = None
            
            # Record admin bypass
            self.record_attempt(
                user,
                MFAAttemptType.TOTP,  # Placeholder type
                MFAAttemptStatus.SUCCESS,
                failure_reason="Admin unblock"
            )
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def cleanup_old_attempts(self, days_to_keep: int = 90) -> int:
        """Clean up old MFA attempts (for maintenance)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted_count = self.db.query(MFAAttempt).filter(
                MFAAttempt.created_at < cutoff_date
            ).delete()
            
            self.db.commit()
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            return 0