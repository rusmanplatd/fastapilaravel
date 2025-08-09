from __future__ import annotations

import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.sql import desc

from app.Models import User
from app.Services.BaseService import BaseService
from app.Models.MFAAuditLog import MFAAuditLog, MFAAuditEvent


class MFAAuditService(BaseService):
    """Comprehensive audit logging service for MFA events"""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def log_event(
        self,
        event: MFAAuditEvent,
        user: Optional[User] = None,
        mfa_method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        session_id: Optional[str] = None,
        admin_user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        risk_factors: Optional[List[str]] = None
    ) -> bool:
        """Log MFA audit event"""
        try:
            # Calculate risk score based on various factors
            risk_score = self._calculate_risk_score(
                event, user, ip_address, user_agent, device_fingerprint, risk_factors
            )
            
            audit_log = MFAAuditLog(
                user_id=user.id if user else None,
                event=event.value,
                mfa_method=mfa_method,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                session_id=session_id,
                admin_user_id=admin_user_id,
                details=details,
                error_message=error_message,
                risk_score=risk_score,
                risk_factors=json.dumps(risk_factors) if risk_factors else None
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
            # Check if we need to alert on high-risk events
            if risk_score and risk_score >= 80:
                self._handle_high_risk_event(audit_log)
            
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def log_setup_initiated(
        self, 
        user: User, 
        mfa_method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Log MFA setup initiation"""
        return self.log_event(
            MFAAuditEvent.SETUP_INITIATED,
            user=user,
            mfa_method=mfa_method,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"setup_method": mfa_method}
        )
    
    def log_setup_completed(
        self,
        user: User,
        mfa_method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log successful MFA setup completion"""
        return self.log_event(
            MFAAuditEvent.SETUP_COMPLETED,
            user=user,
            mfa_method=mfa_method,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
    
    def log_verification_success(
        self,
        user: User,
        mfa_method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Log successful MFA verification"""
        # Check for suspicious success patterns
        risk_factors = []
        
        # Check for unusual location/device
        if self._is_new_location(user, ip_address):
            risk_factors.append("new_location")
        
        if self._is_new_device(user, device_fingerprint):
            risk_factors.append("new_device")
        
        # Check for time-based anomalies
        if self._is_unusual_time(user):
            risk_factors.append("unusual_time")
        
        return self.log_event(
            MFAAuditEvent.VERIFICATION_SUCCESS,
            user=user,
            mfa_method=mfa_method,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            session_id=session_id,
            risk_factors=risk_factors
        )
    
    def log_verification_failed(
        self,
        user: User,
        mfa_method: str,
        failure_reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Log failed MFA verification"""
        # Check for brute force patterns
        risk_factors = []
        
        recent_failures = self._count_recent_failures(user, timedelta(minutes=10))
        if recent_failures >= 5:
            risk_factors.append("repeated_failures")
        
        # Check for distributed attack patterns
        if self._is_distributed_attack(user, ip_address):
            risk_factors.append("distributed_attack")
        
        return self.log_event(
            MFAAuditEvent.VERIFICATION_FAILED,
            user=user,
            mfa_method=mfa_method,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            session_id=session_id,
            error_message=failure_reason,
            risk_factors=risk_factors
        )
    
    def log_device_registered(
        self,
        user: User,
        device_name: str,
        device_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> bool:
        """Log new device registration"""
        return self.log_event(
            MFAAuditEvent.DEVICE_REGISTERED,
            user=user,
            mfa_method="webauthn",
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            details={
                "device_name": device_name,
                "device_type": device_type
            }
        )
    
    def log_backup_code_used(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Log backup code usage"""
        # Backup code usage should be flagged as higher risk
        risk_factors = ["backup_code_usage"]
        
        return self.log_event(
            MFAAuditEvent.BACKUP_CODE_USED,
            user=user,
            mfa_method="backup_code",
            ip_address=ip_address,
            user_agent=user_agent,
            risk_factors=risk_factors
        )
    
    def log_admin_bypass(
        self,
        user: User,
        admin_user_id: str,
        reason: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """Log admin MFA bypass"""
        return self.log_event(
            MFAAuditEvent.ADMIN_BYPASS,
            user=user,
            admin_user_id=admin_user_id,
            ip_address=ip_address,
            details={"bypass_reason": reason},
            risk_factors=["admin_bypass"]
        )
    
    def get_user_audit_history(
        self,
        user: User,
        days: int = 30,
        event_types: Optional[List[MFAAuditEvent]] = None
    ) -> List[Dict[str, Any]]:
        """Get audit history for a user"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(MFAAuditLog).filter(
                and_(                    MFAAuditLog.user_id == user.id,
                    MFAAuditLog.created_at >= since_date
                )
            )
            
            if event_types:
                event_values = [event.value for event in event_types]
                query = query.filter(MFAAuditLog.event.in_(event_values))
            
            logs = query.order_by(desc(MFAAuditLog.created_at)).limit(100).all()
            
            return [
                {
                    "id": log.id,
                    "event": log.event,
                    "mfa_method": log.mfa_method,
                    "timestamp": log.created_at,
                    "ip_address": log.ip_address,
                    "risk_score": log.risk_score,
                    "details": log.details,
                    "error_message": log.error_message
                }
                for log in logs
            ]
            
        except Exception:
            return []
    
    def get_security_summary(self, user: User, days: int = 30) -> Dict[str, Any]:
        """Get security summary for user"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Count different event types
            events = self.db.query(MFAAuditLog).filter(
                and_(                    MFAAuditLog.user_id == user.id,
                    MFAAuditLog.created_at >= since_date
                )
            ).all()
            
            event_counts: Dict[str, int] = {}
            high_risk_events = 0
            unique_ips = set()
            unique_devices = set()
            
            for event in events:
                event_counts[event.event] = event_counts.get(event.event, 0) + 1
                
                if event.risk_score and event.risk_score >= 70:
                    high_risk_events += 1
                
                if event.ip_address:
                    unique_ips.add(event.ip_address)
                
                if event.device_fingerprint:
                    unique_devices.add(event.device_fingerprint)
            
            return {
                "total_events": len(events),
                "event_counts": event_counts,
                "high_risk_events": high_risk_events,
                "unique_ips": len(unique_ips),
                "unique_devices": len(unique_devices),
                "most_recent_activity": events[0].created_at if events else None
            }
            
        except Exception:
            return {}
    
    def _calculate_risk_score(
        self,
        event: MFAAuditEvent,
        user: Optional[User],
        ip_address: Optional[str],
        user_agent: Optional[str],
        device_fingerprint: Optional[str],
        risk_factors: Optional[List[str]]
    ) -> int:
        """Calculate risk score (0-100) for an event"""
        score = 0
        
        # Base scores by event type
        base_scores = {
            MFAAuditEvent.SETUP_INITIATED: 20,
            MFAAuditEvent.SETUP_COMPLETED: 15,
            MFAAuditEvent.VERIFICATION_SUCCESS: 5,
            MFAAuditEvent.VERIFICATION_FAILED: 30,
            MFAAuditEvent.DEVICE_REGISTERED: 25,
            MFAAuditEvent.BACKUP_CODE_USED: 40,
            MFAAuditEvent.MFA_DISABLED: 60,
            MFAAuditEvent.ADMIN_BYPASS: 70,
            MFAAuditEvent.RATE_LIMITED: 50
        }
        
        score = base_scores.get(event, 10)
        
        # Add risk factor scores
        if risk_factors:
            risk_factor_scores = {
                "new_location": 15,
                "new_device": 10,
                "unusual_time": 5,
                "repeated_failures": 20,
                "distributed_attack": 30,
                "backup_code_usage": 15,
                "admin_bypass": 25
            }
            
            for factor in risk_factors:
                score += risk_factor_scores.get(factor, 5)
        
        # Cap at 100
        return min(score, 100)
    
    def _is_new_location(self, user: User, ip_address: Optional[str]) -> bool:
        """Check if IP address is new for this user"""
        if not ip_address:
            return False
            
        # Check if we've seen this IP for this user in the last 30 days
        recent_date = datetime.utcnow() - timedelta(days=30)
        existing = self.db.query(MFAAuditLog).filter(
            MFAAuditLog.user_id == user.id,
            MFAAuditLog.ip_address == ip_address,
            MFAAuditLog.created_at >= recent_date
        ).first()
        
        return existing is None
    
    def _is_new_device(self, user: User, device_fingerprint: Optional[str]) -> bool:
        """Check if device fingerprint is new for this user"""
        if not device_fingerprint:
            return False
            
        recent_date = datetime.utcnow() - timedelta(days=30)
        existing = self.db.query(MFAAuditLog).filter(
            MFAAuditLog.user_id == user.id,
            MFAAuditLog.device_fingerprint == device_fingerprint,
            MFAAuditLog.created_at >= recent_date
        ).first()
        
        return existing is None
    
    def _is_unusual_time(self, user: User) -> bool:
        """Check if current time is unusual for this user"""
        # Simple heuristic: check if outside normal business hours
        current_hour = datetime.utcnow().hour
        return current_hour < 6 or current_hour > 22
    
    def _count_recent_failures(self, user: User, time_window: timedelta) -> int:
        """Count recent verification failures for user"""
        since_date = datetime.utcnow() - time_window
        return self.db.query(MFAAuditLog).filter(
            MFAAuditLog.user_id == user.id,
            MFAAuditLog.event == MFAAuditEvent.VERIFICATION_FAILED.value,
            MFAAuditLog.created_at >= since_date
        ).count()
    
    def _is_distributed_attack(self, user: User, ip_address: Optional[str]) -> bool:
        """Check for distributed attack patterns"""
        if not ip_address:
            return False
            
        # Check if multiple IPs are failing for this user recently
        recent_date = datetime.utcnow() - timedelta(hours=1)
        failed_ips = self.db.query(MFAAuditLog.ip_address).filter(
            MFAAuditLog.user_id == user.id,
            MFAAuditLog.event == MFAAuditEvent.VERIFICATION_FAILED.value,
            MFAAuditLog.created_at >= recent_date,
            MFAAuditLog.ip_address.is_not(None)
        ).distinct().all()
        
        return len(failed_ips) >= 3  # 3+ different IPs in past hour
    
    def _handle_high_risk_event(self, audit_log: MFAAuditLog) -> None:
        """Handle high-risk events (alerts, notifications, etc.)"""
        # This could trigger:
        # - Email alerts to security team
        # - Slack notifications
        # - Automated response actions
        # - Log to external SIEM system
        pass
    
    def cleanup_old_logs(self, days_to_keep: int = 365) -> int:
        """Clean up old audit logs"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted_count = self.db.query(MFAAuditLog).filter(
                MFAAuditLog.created_at < cutoff_date
            ).delete()
            
            self.db.commit()
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            return 0