from __future__ import annotations

import json
import statistics
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from sqlalchemy.sql import desc, asc
from collections import defaultdict

from app.Models import User, Role
from app.Services.BaseService import BaseService
from app.Models.MFAAuditLog import MFAAuditLog, MFAAuditEvent
from app.Models.MFAAttempt import MFAAttempt, MFAAttemptStatus, MFAAttemptType


class MFAAnalyticsService(BaseService):
    """Comprehensive MFA analytics and reporting service"""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def generate_mfa_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive MFA dashboard data"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            dashboard = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "overview": self._get_overview_stats(),
                "adoption": self._get_adoption_stats(),
                "security": self._get_security_stats(start_date, end_date),
                "usage": self._get_usage_stats(start_date, end_date),
                "performance": self._get_performance_stats(start_date, end_date),
                "trends": self._get_trend_analysis(start_date, end_date),
                "top_events": self._get_top_events(start_date, end_date),
                "risk_analysis": self._get_risk_analysis(start_date, end_date),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return dashboard
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_overview_stats(self) -> Dict[str, Any]:
        """Get MFA overview statistics"""
        try:
            total_users = self.db.query(User).count()
            
            # Count users with MFA enabled
            mfa_enabled_users = self.db.query(User).join(
                User.mfa_settings
            ).filter(
                or_(
                    User.mfa_settings.has(totp_enabled=True),
                    User.mfa_settings.has(webauthn_enabled=True),
                    User.mfa_settings.has(sms_enabled=True)
                )
            ).count() if total_users > 0 else 0
            
            # Count users with MFA required
            mfa_required_users = self.db.query(User).join(
                User.mfa_settings
            ).filter(
                User.mfa_settings.has(is_required=True)
            ).count() if total_users > 0 else 0
            
            # Count WebAuthn credentials
            webauthn_creds = self.db.query(User).join(User.webauthn_credentials).count()
            
            # Calculate percentages
            mfa_adoption_rate = (mfa_enabled_users / total_users * 100) if total_users > 0 else 0
            mfa_compliance_rate = (mfa_required_users / total_users * 100) if total_users > 0 else 0
            
            return {
                "total_users": total_users,
                "mfa_enabled_users": mfa_enabled_users,
                "mfa_required_users": mfa_required_users,
                "mfa_adoption_rate": round(mfa_adoption_rate, 2),
                "mfa_compliance_rate": round(mfa_compliance_rate, 2),
                "webauthn_credentials": webauthn_creds,
                "health_score": self._calculate_health_score(
                    mfa_adoption_rate, mfa_compliance_rate
                )
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_adoption_stats(self) -> Dict[str, Any]:
        """Get MFA adoption statistics by method"""
        try:
            adoption: Dict[str, Any] = {
                "by_method": {},
                "by_role": {},
                "by_registration_date": {},
                "method_combinations": {}
            }
            
            # Count by method
            from app.Models.UserMFASettings import UserMFASettings
            
            totp_count = self.db.query(UserMFASettings).filter(
                UserMFASettings.totp_enabled == True
            ).count()
            
            webauthn_count = self.db.query(UserMFASettings).filter(
                UserMFASettings.webauthn_enabled == True
            ).count()
            
            sms_count = self.db.query(UserMFASettings).filter(
                UserMFASettings.sms_enabled == True
            ).count()
            
            adoption["by_method"] = {
                "totp": totp_count,
                "webauthn": webauthn_count,
                "sms": sms_count,
                "none": self.db.query(User).count() - max(totp_count, webauthn_count, sms_count)
            }
            
            # Count by role
            roles = self.db.query(Role).all()
            for role in roles:
                users_with_role = len(role.users)
                mfa_users_in_role = 0
                
                for user in role.users:
                    if user.has_mfa_enabled():
                        mfa_users_in_role += 1
                
                adoption["by_role"][role.name] = {
                    "total_users": users_with_role,
                    "mfa_enabled": mfa_users_in_role,
                    "adoption_rate": (mfa_users_in_role / users_with_role * 100) if users_with_role > 0 else 0
                }
            
            # Method combinations
            combo_counts: Dict[str, int] = defaultdict(int)
            users_with_mfa = self.db.query(User).join(User.mfa_settings).filter(
                or_(
                    User.mfa_settings.has(totp_enabled=True),
                    User.mfa_settings.has(webauthn_enabled=True),
                    User.mfa_settings.has(sms_enabled=True)
                )
            ).all()
            
            for user in users_with_mfa:
                methods = user.get_enabled_mfa_methods()
                combo_key = "+".join(sorted(methods))
                combo_counts[combo_key] += 1
            
            adoption["method_combinations"] = dict(combo_counts)
            
            return adoption
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_security_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get security-related MFA statistics"""
        try:
            security = {
                "failed_attempts": 0,
                "successful_attempts": 0,
                "blocked_attempts": 0,
                "backup_codes_used": 0,
                "high_risk_events": 0,
                "security_incidents": [],
                "attack_patterns": {},
                "success_rate": 0
            }
            
            # Count attempt types
            failed_attempts = self.db.query(MFAAttempt).filter(
                and_(
                    MFAAttempt.status == MFAAttemptStatus.FAILED,
                    MFAAttempt.created_at >= start_date,
                    MFAAttempt.created_at <= end_date
                )
            ).count()
            
            successful_attempts = self.db.query(MFAAttempt).filter(
                and_(
                    MFAAttempt.status == MFAAttemptStatus.SUCCESS,
                    MFAAttempt.created_at >= start_date,
                    MFAAttempt.created_at <= end_date
                )
            ).count()
            
            blocked_attempts = self.db.query(MFAAttempt).filter(
                and_(
                    MFAAttempt.status == MFAAttemptStatus.BLOCKED,
                    MFAAttempt.created_at >= start_date,
                    MFAAttempt.created_at <= end_date
                )
            ).count()
            
            # Count high-risk events
            high_risk_events = self.db.query(MFAAuditLog).filter(
                and_(
                    MFAAuditLog.risk_score >= 70,
                    MFAAuditLog.created_at >= start_date,
                    MFAAuditLog.created_at <= end_date
                )
            ).count()
            
            # Count backup code usage
            backup_codes_used = self.db.query(MFAAuditLog).filter(
                and_(
                    MFAAuditLog.event == MFAAuditEvent.BACKUP_CODE_USED.value,
                    MFAAuditLog.created_at >= start_date,
                    MFAAuditLog.created_at <= end_date
                )
            ).count()
            
            # Calculate success rate
            total_attempts = failed_attempts + successful_attempts + blocked_attempts
            success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 100
            
            # Analyze attack patterns
            attack_patterns = self._analyze_attack_patterns(start_date, end_date)
            
            security.update({
                "failed_attempts": failed_attempts,
                "successful_attempts": successful_attempts,
                "blocked_attempts": blocked_attempts,
                "backup_codes_used": backup_codes_used,
                "high_risk_events": high_risk_events,
                "success_rate": round(success_rate, 2),
                "attack_patterns": attack_patterns
            })
            
            return security
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_usage_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get MFA usage statistics"""
        try:
            usage: Dict[str, Any] = {
                "daily_verifications": {},
                "method_usage": {},
                "peak_hours": {},
                "user_activity": {},
                "geographic_distribution": {},
                "device_types": {}
            }
            
            # Daily verification counts
            daily_verifications = {}
            current_date = start_date.date()
            while current_date <= end_date.date():
                day_start = datetime.combine(current_date, datetime.min.time())
                day_end = day_start + timedelta(days=1)
                
                count = self.db.query(MFAAttempt).filter(
                    and_(                        MFAAttempt.status == MFAAttemptStatus.SUCCESS,
                        MFAAttempt.created_at >= day_start,
                        MFAAttempt.created_at < day_end
                    )
                ).count()
                
                daily_verifications[current_date.isoformat()] = count
                current_date += timedelta(days=1)
            
            usage["daily_verifications"] = daily_verifications
            
            # Method usage
            method_usage = {}
            for attempt_type in MFAAttemptType:
                count = self.db.query(MFAAttempt).filter(
                    and_(                        MFAAttempt.attempt_type == attempt_type,
                        MFAAttempt.status == MFAAttemptStatus.SUCCESS,
                        MFAAttempt.created_at >= start_date,
                        MFAAttempt.created_at <= end_date
                    )
                ).count()
                method_usage[attempt_type.value] = count
            
            usage["method_usage"] = method_usage
            
            # Peak hours analysis
            peak_hours = {}
            for hour in range(24):
                count = self.db.query(MFAAttempt).filter(
                    and_(                        MFAAttempt.status == MFAAttemptStatus.SUCCESS,
                        func.extract('hour', MFAAttempt.created_at) == hour,
                        MFAAttempt.created_at >= start_date,
                        MFAAttempt.created_at <= end_date
                    )
                ).count()
                peak_hours[f"{hour:02d}:00"] = count
            
            usage["peak_hours"] = peak_hours
            
            return usage
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_performance_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get MFA performance statistics"""
        try:
            performance: Dict[str, Any] = {
                "average_setup_time": None,
                "method_reliability": {},
                "user_satisfaction_score": None,
                "support_tickets": 0,
                "setup_completion_rate": None
            }
            
            # Setup completion rate (initiated vs completed)
            setup_initiated = self.db.query(MFAAuditLog).filter(
                and_(
                    MFAAuditLog.event == MFAAuditEvent.SETUP_INITIATED.value,
                    MFAAuditLog.created_at >= start_date,
                    MFAAuditLog.created_at <= end_date
                )
            ).count()
            
            setup_completed = self.db.query(MFAAuditLog).filter(
                and_(
                    MFAAuditLog.event == MFAAuditEvent.SETUP_COMPLETED.value,
                    MFAAuditLog.created_at >= start_date,
                    MFAAuditLog.created_at <= end_date
                )
            ).count()
            
            completion_rate = (setup_completed / setup_initiated * 100) if setup_initiated > 0 else 0
            performance["setup_completion_rate"] = round(completion_rate, 2)
            
            # Method reliability (success rate by method)
            method_reliability = {}
            for method in MFAAttemptType:
                total_attempts = self.db.query(MFAAttempt).filter(
                    and_(                        MFAAttempt.attempt_type == method,
                        MFAAttempt.created_at >= start_date,
                        MFAAttempt.created_at <= end_date
                    )
                ).count()
                
                successful_attempts = self.db.query(MFAAttempt).filter(
                    and_(                        MFAAttempt.attempt_type == method,
                        MFAAttempt.status == MFAAttemptStatus.SUCCESS,
                        MFAAttempt.created_at >= start_date,
                        MFAAttempt.created_at <= end_date
                    )
                ).count()
                
                reliability = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
                method_reliability[method.value] = {
                    "success_rate": round(reliability, 2),
                    "total_attempts": total_attempts,
                    "successful_attempts": successful_attempts
                }
            
            performance["method_reliability"] = method_reliability
            
            return performance
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_trend_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze MFA trends over time"""
        try:
            trends: Dict[str, Any] = {
                "adoption_trend": {},
                "security_trend": {},
                "usage_trend": {},
                "predictions": {}
            }
            
            # Weekly adoption trend
            weeks = []
            current_week = start_date
            while current_week <= end_date:
                week_end = min(current_week + timedelta(weeks=1), end_date)
                
                # Count new MFA setups in this week
                new_setups = self.db.query(MFAAuditLog).filter(
                    and_(                        MFAAuditLog.event == MFAAuditEvent.SETUP_COMPLETED.value,
                        MFAAuditLog.created_at >= current_week,
                        MFAAuditLog.created_at <= week_end
                    )
                ).count()
                
                week_key = current_week.strftime("%Y-W%U")
                trends["adoption_trend"][week_key] = new_setups
                weeks.append(new_setups)
                
                current_week = week_end
            
            # Calculate trend direction
            if len(weeks) >= 2:
                recent_avg = statistics.mean(weeks[-2:]) if len(weeks) >= 2 else weeks[-1]
                earlier_avg = statistics.mean(weeks[:2]) if len(weeks) >= 2 else weeks[0]
                
                trend_direction = "increasing" if recent_avg > earlier_avg else "decreasing"
                trends["predictions"]["adoption_direction"] = trend_direction
            
            return trends
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_top_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get top MFA events for the period"""
        try:
            # Get most frequent events
            event_counts = self.db.query(
                MFAAuditLog.event,
                func.count(MFAAuditLog.id).label('count')
            ).filter(
                MFAAuditLog.created_at >= start_date,
                MFAAuditLog.created_at <= end_date
            ).group_by(MFAAuditLog.event).order_by(desc('count')).limit(10).all()
            
            return [
                {"event": event, "count": count}
                for event, count in event_counts
            ]
            
        except Exception as e:
            return []
    
    def _get_risk_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze MFA-related risks"""
        try:
            risk_analysis: Dict[str, Any] = {
                "risk_distribution": {},
                "top_risk_factors": {},
                "risk_trend": {},
                "mitigation_effectiveness": {}
            }
            
            # Risk score distribution
            risk_ranges = [
                ("Low (0-30)", 0, 30),
                ("Medium (31-50)", 31, 50),
                ("High (51-70)", 51, 70),
                ("Critical (71-100)", 71, 100)
            ]
            
            for range_name, min_score, max_score in risk_ranges:
                count = self.db.query(MFAAuditLog).filter(
                    and_(                        MFAAuditLog.risk_score >= min_score,
                        MFAAuditLog.risk_score <= max_score,
                        MFAAuditLog.created_at >= start_date,
                        MFAAuditLog.created_at <= end_date
                    )
                ).count()
                
                risk_analysis["risk_distribution"][range_name] = count
            
            # Top risk factors
            risk_factors: Dict[str, int] = {}
            logs_with_factors = self.db.query(MFAAuditLog).filter(
                and_(
                    MFAAuditLog.risk_factors.is_not(None),
                    MFAAuditLog.created_at >= start_date,
                    MFAAuditLog.created_at <= end_date
                )
            ).all()
            
            for log in logs_with_factors:
                if log.risk_factors:
                    try:
                        factors = json.loads(log.risk_factors)
                        for factor in factors:
                            risk_factors[factor] = risk_factors.get(factor, 0) + 1
                    except Exception:
                        continue
            
            # Sort by frequency
            sorted_factors = sorted(risk_factors.items(), key=lambda x: x[1], reverse=True)
            risk_analysis["top_risk_factors"] = dict(sorted_factors[:10])
            
            return risk_analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_attack_patterns(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze potential attack patterns"""
        try:
            patterns = {
                "brute_force_attempts": 0,
                "distributed_attacks": 0,
                "suspicious_ips": [],
                "timing_patterns": {}
            }
            
            # Find IPs with many failed attempts (potential brute force)
            ip_failures = self.db.query(
                MFAAttempt.ip_address,
                func.count(MFAAttempt.id).label('failure_count')
            ).filter(
                MFAAttempt.status == MFAAttemptStatus.FAILED,
                MFAAttempt.ip_address.is_not(None),
                MFAAttempt.created_at >= start_date,
                MFAAttempt.created_at <= end_date
            ).group_by(MFAAttempt.ip_address).having(
                func.count(MFAAttempt.id) > 10
            ).all()
            
            patterns["brute_force_attempts"] = len(ip_failures)
            patterns["suspicious_ips"] = [
                {"ip": ip, "failures": count}
                for ip, count in ip_failures
            ]
            
            return patterns
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_health_score(self, adoption_rate: float, compliance_rate: float) -> int:
        """Calculate overall MFA health score (0-100)"""
        try:
            # Weight adoption and compliance equally
            base_score = (adoption_rate + compliance_rate) / 2
            
            # Apply bonuses/penalties
            if adoption_rate > 90:
                base_score += 5  # Bonus for high adoption
            elif adoption_rate < 50:
                base_score -= 10  # Penalty for low adoption
            
            if compliance_rate > 95:
                base_score += 5  # Bonus for high compliance
            elif compliance_rate < 70:
                base_score -= 10  # Penalty for low compliance
            
            # Ensure score is between 0 and 100
            return max(0, min(100, int(base_score)))
            
        except Exception:
            return 50  # Default score if calculation fails
    
    def generate_executive_summary(self, days: int = 30) -> Dict[str, Any]:
        """Generate executive summary report"""
        try:
            dashboard = self.generate_mfa_dashboard(days)
            
            summary = {
                "title": f"MFA Executive Summary - Last {days} Days",
                "generated_at": datetime.utcnow().isoformat(),
                "key_metrics": {
                    "mfa_adoption_rate": dashboard["overview"]["mfa_adoption_rate"],
                    "security_incidents": len(dashboard["security"].get("security_incidents", [])),
                    "health_score": dashboard["overview"]["health_score"],
                    "failed_attempts": dashboard["security"]["failed_attempts"]
                },
                "recommendations": self._generate_recommendations(dashboard),
                "risk_assessment": self._assess_overall_risk(dashboard),
                "action_items": self._generate_action_items(dashboard)
            }
            
            return summary
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_recommendations(self, dashboard: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on dashboard data"""
        recommendations = []
        
        try:
            adoption_rate = dashboard["overview"]["mfa_adoption_rate"]
            success_rate = dashboard["security"]["success_rate"]
            high_risk_events = dashboard["security"]["high_risk_events"]
            
            if adoption_rate < 70:
                recommendations.append("Increase MFA adoption through user education and incentives")
            
            if success_rate < 95:
                recommendations.append("Investigate and improve MFA reliability issues")
            
            if high_risk_events > 10:
                recommendations.append("Review high-risk events and strengthen security policies")
            
            # Method-specific recommendations
            method_usage = dashboard["usage"]["method_usage"]
            sms_usage = method_usage.get("sms", 0)
            total_usage = sum(method_usage.values()) if method_usage.values() else 1
            
            if sms_usage / total_usage > 0.3:  # More than 30% SMS usage
                recommendations.append("Encourage migration from SMS to more secure methods (TOTP/WebAuthn)")
            
            return recommendations
            
        except Exception:
            return ["Unable to generate recommendations due to data issues"]
    
    def _assess_overall_risk(self, dashboard: Dict[str, Any]) -> str:
        """Assess overall MFA risk level"""
        try:
            health_score = dashboard["overview"]["health_score"]
            
            if health_score >= 80:
                return "Low - MFA implementation is strong"
            elif health_score >= 60:
                return "Medium - Some areas need attention"
            elif health_score >= 40:
                return "High - Significant improvements needed"
            else:
                return "Critical - Immediate action required"
                
        except Exception:
            return "Unknown - Unable to assess risk"
    
    def _generate_action_items(self, dashboard: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prioritized action items"""
        action_items = []
        
        try:
            adoption_rate = dashboard["overview"]["mfa_adoption_rate"]
            failed_attempts = dashboard["security"]["failed_attempts"]
            
            if adoption_rate < 50:
                action_items.append({
                    "priority": "High",
                    "item": "Launch MFA adoption campaign",
                    "timeline": "2 weeks",
                    "owner": "Security Team"
                })
            
            if failed_attempts > 100:
                action_items.append({
                    "priority": "Medium",
                    "item": "Investigate high failure rates",
                    "timeline": "1 week",
                    "owner": "IT Operations"
                })
            
            return action_items
            
        except Exception:
            return []