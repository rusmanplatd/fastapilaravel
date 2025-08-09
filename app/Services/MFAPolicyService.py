from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, cast
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from enum import Enum

from app.Models import User, Role, Permission
from app.Services.BaseService import BaseService
from app.Services.MFAAuditService import MFAAuditService
from app.Models.MFAAuditLog import MFAAuditEvent


class MFARequirementLevel(str, Enum):
    NONE = "none"
    OPTIONAL = "optional" 
    REQUIRED = "required"
    ENFORCED = "enforced"  # Cannot be disabled by user


class MFARiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MFAPolicyService(BaseService):
    """MFA Policy enforcement and compliance service"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.audit_service = MFAAuditService(db)
        
        # Default policies
        self.default_policies = {
            "global_mfa_required": False,
            "admin_mfa_required": True,
            "high_privilege_mfa_required": True,
            "new_device_mfa_required": True,
            "suspicious_activity_mfa_required": True,
            "password_reset_mfa_required": True,
            "account_changes_mfa_required": True,
            "max_mfa_disable_hours": 24,
            "mfa_setup_grace_period_days": 30,
            "backup_codes_required": True,
            "min_mfa_methods": 1,
            "preferred_mfa_methods": ["totp", "webauthn"],
            "weak_methods": ["sms"],  # SMS is considered weaker
            "compliance_frameworks": ["SOC2", "NIST"]
        }
        
        # Risk-based policies
        self.risk_policies = {
            MFARiskLevel.LOW: {
                "mfa_required": False,
                "allowed_methods": ["totp", "webauthn", "sms"],
                "max_session_hours": 8
            },
            MFARiskLevel.MEDIUM: {
                "mfa_required": True,
                "allowed_methods": ["totp", "webauthn"],
                "max_session_hours": 4
            },
            MFARiskLevel.HIGH: {
                "mfa_required": True,
                "allowed_methods": ["totp", "webauthn"],
                "max_session_hours": 2,
                "require_multiple_methods": True
            },
            MFARiskLevel.CRITICAL: {
                "mfa_required": True,
                "allowed_methods": ["webauthn"],
                "max_session_hours": 1,
                "require_multiple_methods": True,
                "admin_approval_required": True
            }
        }
    
    def evaluate_mfa_requirement(
        self,
        user: User,
        context: Dict[str, Any]
    ) -> Tuple[MFARequirementLevel, str, Dict[str, Any]]:
        """Evaluate MFA requirement for user based on policies and context"""
        try:
            reasons: List[str] = []
            policies_evaluated: List[str] = []
            risk_factors: List[str] = []
            
            evaluation: Dict[str, Any] = {
                "user_id": user.id,
                "timestamp": datetime.utcnow().isoformat(),
                "context": context,
                "policies_evaluated": policies_evaluated,
                "risk_factors": risk_factors,
                "requirement_level": MFARequirementLevel.NONE,
                "reasons": reasons
            }
            
            # Check global policy
            if self.default_policies.get("global_mfa_required", False):
                evaluation["requirement_level"] = MFARequirementLevel.REQUIRED
                reasons.append("Global MFA policy")
                policies_evaluated.append("global_mfa_required")
            
            # Check user roles
            user_roles = [role.name for role in user.roles]
            
            # Admin users
            if any(role in ["admin", "administrator", "super_admin"] for role in user_roles):
                if self.default_policies.get("admin_mfa_required", True):
                    evaluation["requirement_level"] = MFARequirementLevel.ENFORCED
                    reasons.append("Administrator role")
                    policies_evaluated.append("admin_mfa_required")
            
            # High privilege users
            high_privilege_permissions = [
                "user.delete", "role.manage", "permission.manage", 
                "system.admin", "billing.manage"
            ]
            user_permissions = user.get_permission_names()
            
            if any(perm in high_privilege_permissions for perm in user_permissions):
                if self.default_policies.get("high_privilege_mfa_required", True):
                    if evaluation["requirement_level"] != MFARequirementLevel.ENFORCED:
                        evaluation["requirement_level"] = MFARequirementLevel.REQUIRED
                    reasons.append("High privilege permissions")
                    policies_evaluated.append("high_privilege_mfa_required")
            
            # Context-based evaluations
            risk_level = self._calculate_risk_level(user, context)
            risk_policy = self.risk_policies.get(risk_level)
            
            if risk_policy and risk_policy.get("mfa_required", False):
                if risk_level in [MFARiskLevel.HIGH, MFARiskLevel.CRITICAL]:
                    evaluation["requirement_level"] = MFARequirementLevel.ENFORCED
                elif evaluation["requirement_level"] == MFARequirementLevel.NONE:
                    evaluation["requirement_level"] = MFARequirementLevel.REQUIRED
                
                reasons.append(f"Risk level: {risk_level.value}")
                risk_factors.extend(context.get("risk_factors", []))
            
            # New device detection
            if context.get("new_device", False) and self.default_policies.get("new_device_mfa_required", True):
                if evaluation["requirement_level"] == MFARequirementLevel.NONE:
                    evaluation["requirement_level"] = MFARequirementLevel.REQUIRED
                reasons.append("New device detected")
                policies_evaluated.append("new_device_mfa_required")
            
            # Suspicious activity
            if context.get("suspicious_activity", False):
                evaluation["requirement_level"] = MFARequirementLevel.ENFORCED
                reasons.append("Suspicious activity detected")
                risk_factors.append("suspicious_activity")
            
            # Sensitive operations
            sensitive_operations = [
                "password_reset", "email_change", "role_change", 
                "permission_grant", "account_deletion"
            ]
            if context.get("operation") in sensitive_operations:
                if evaluation["requirement_level"] == MFARequirementLevel.NONE:
                    evaluation["requirement_level"] = MFARequirementLevel.REQUIRED
                reasons.append(f"Sensitive operation: {context.get('operation')}")
            
            # Log policy evaluation  
            if evaluation["requirement_level"] != MFARequirementLevel.NONE:
                self.audit_service.log_event(
                    MFAAuditEvent.MFA_REQUIRED,
                    user=user,
                    details=evaluation
                )
            
            return (
                evaluation["requirement_level"],
                "; ".join(evaluation["reasons"]),
                evaluation
            )
            
        except Exception as e:
            return MFARequirementLevel.NONE, f"Policy evaluation error: {str(e)}", {}
    
    def check_mfa_compliance(self, user: User) -> Dict[str, Any]:
        """Check user's MFA compliance against policies"""
        compliance: Dict[str, Any] = {
            "compliant": True,
            "violations": [],
            "recommendations": [],
            "grace_period_expired": False,
            "enforcement_actions": []
        }
        
        try:
            # Check if user has MFA enabled when required
            if user.is_mfa_required() and not user.has_mfa_enabled():
                compliance["compliant"] = False
                compliance["violations"].append("MFA required but not enabled")
                
                # Check grace period
                account_age = (datetime.utcnow() - user.created_at).days
                grace_period = cast(int, self.default_policies.get("mfa_setup_grace_period_days", 30))
                
                if account_age > grace_period:
                    compliance["grace_period_expired"] = True
                    compliance["enforcement_actions"].append("Account access should be restricted")
            
            # Check minimum MFA methods
            if user.has_mfa_enabled():
                enabled_methods = user.get_enabled_mfa_methods()
                min_methods = cast(int, self.default_policies.get("min_mfa_methods", 1))
                
                if len(enabled_methods) < min_methods:
                    compliance["violations"].append(f"Minimum {min_methods} MFA methods required")
                    compliance["compliant"] = False
            
            # Check backup codes
            if self.default_policies.get("backup_codes_required", True):
                if user.mfa_settings and user.mfa_settings.totp_enabled:
                    backup_codes_count = 0
                    if user.mfa_settings.totp_backup_tokens:
                        backup_codes_count = len(user.mfa_settings.totp_backup_tokens.split(","))
                    
                    if backup_codes_count == 0:
                        compliance["violations"].append("Backup codes required")
                        compliance["compliant"] = False
                    elif backup_codes_count <= 2:
                        compliance["recommendations"].append("Generate new backup codes")
            
            # Check weak methods
            if user.has_mfa_enabled():
                enabled_methods = user.get_enabled_mfa_methods()
                weak_methods = cast(List[str], self.default_policies.get("weak_methods", ["sms"]))
                
                using_only_weak = all(method in weak_methods for method in enabled_methods)
                if using_only_weak and len(enabled_methods) > 0:
                    compliance["recommendations"].append("Use stronger MFA methods (TOTP or WebAuthn)")
            
            # Check preferred methods
            preferred_methods = cast(List[str], self.default_policies.get("preferred_mfa_methods", ["totp", "webauthn"]))
            if user.has_mfa_enabled():
                enabled_methods = user.get_enabled_mfa_methods()
                has_preferred = any(method in preferred_methods for method in enabled_methods)
                
                if not has_preferred:
                    compliance["recommendations"].append(f"Enable preferred methods: {', '.join(preferred_methods)}")
            
            # Check for disabled MFA when required
            if user.is_mfa_required() and user.has_mfa_enabled():
                # Check if MFA was recently disabled
                recent_disable = self.audit_service.get_user_audit_history(
                    user, days=1, event_types=[MFAAuditEvent.MFA_DISABLED]
                )
                
                if recent_disable:
                    max_disable_hours = self.default_policies.get("max_mfa_disable_hours", 24)
                    last_disable = recent_disable[0]
                    hours_since_disable = (datetime.utcnow() - last_disable["timestamp"]).total_seconds() / 3600
                    
                    if hours_since_disable > max_disable_hours:
                        compliance["violations"].append("MFA has been disabled too long")
                        compliance["enforcement_actions"].append("Force MFA re-enable")
                        compliance["compliant"] = False
            
            return compliance
            
        except Exception as e:
            compliance["error"] = str(e)
            return compliance
    
    def enforce_mfa_policy(
        self,
        user: User,
        policy_violation: str,
        admin_user_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Enforce MFA policy for non-compliant user"""
        try:
            actions_taken = []
            
            # Force MFA requirement
            if not user.mfa_settings:
                from app.Models import UserMFASettings
                mfa_settings = UserMFASettings(
                    user_id=user.id,
                    is_required=True
                )
                self.db.add(mfa_settings)
            else:
                user.mfa_settings.is_required = True
            
            actions_taken.append("MFA requirement enforced")
            
            # Log enforcement action
            self.audit_service.log_event(
                MFAAuditEvent.MFA_REQUIRED,
                user=user,
                admin_user_id=admin_user_id,
                details={
                    "action": "policy_enforcement",
                    "violation": policy_violation,
                    "actions_taken": actions_taken,
                    "enforced_at": datetime.utcnow().isoformat()
                }
            )
            
            self.db.commit()
            
            return True, f"Policy enforced: {', '.join(actions_taken)}"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to enforce policy: {str(e)}"
    
    def get_compliance_report(
        self,
        role_filter: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate compliance report for users"""
        try:
            report: Dict[str, Any] = {
                "generated_at": datetime.utcnow().isoformat(),
                "period_days": days,
                "total_users": 0,
                "compliant_users": 0,
                "non_compliant_users": 0,
                "grace_period_users": 0,
                "violations_by_type": {},
                "mfa_adoption": {
                    "totp": 0,
                    "webauthn": 0,
                    "sms": 0,
                    "none": 0
                },
                "compliance_by_role": {}
            }
            
            # Query users
            query = self.db.query(User)
            if role_filter:
                query = query.join(User.roles).filter(Role.name.in_(role_filter))
            
            users = query.all()
            report["total_users"] = len(users)
            
            for user in users:
                compliance = self.check_mfa_compliance(user)
                
                # Count compliance
                if compliance["compliant"]:
                    report["compliant_users"] += 1
                else:
                    report["non_compliant_users"] += 1
                
                # Count grace period users
                if compliance.get("grace_period_expired", False):
                    report["grace_period_users"] += 1
                
                # Count violations
                for violation in compliance.get("violations", []):
                    report["violations_by_type"][violation] = report["violations_by_type"].get(violation, 0) + 1
                
                # Count MFA adoption
                if user.has_mfa_enabled():
                    enabled_methods = user.get_enabled_mfa_methods()
                    for method in enabled_methods:
                        if method in report["mfa_adoption"]:
                            report["mfa_adoption"][method] += 1
                else:
                    report["mfa_adoption"]["none"] += 1
                
                # Compliance by role
                for role in user.roles:
                    role_name = role.name
                    if role_name not in report["compliance_by_role"]:
                        report["compliance_by_role"][role_name] = {
                            "total": 0,
                            "compliant": 0,
                            "non_compliant": 0
                        }
                    
                    report["compliance_by_role"][role_name]["total"] += 1
                    if compliance["compliant"]:
                        report["compliance_by_role"][role_name]["compliant"] += 1
                    else:
                        report["compliance_by_role"][role_name]["non_compliant"] += 1
            
            # Calculate percentages
            if report["total_users"] > 0:
                report["compliance_percentage"] = (report["compliant_users"] / report["total_users"]) * 100
            else:
                report["compliance_percentage"] = 100
            
            return report
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_risk_level(self, user: User, context: Dict[str, Any]) -> MFARiskLevel:
        """Calculate risk level based on user and context"""
        risk_score = 0
        
        # Base risk by user role
        user_roles = [role.name for role in user.roles]
        if any(role in ["admin", "administrator", "super_admin"] for role in user_roles):
            risk_score += 30
        elif any(role in ["manager", "supervisor"] for role in user_roles):
            risk_score += 20
        
        # Context-based risk factors
        risk_factors = context.get("risk_factors", [])
        risk_factor_scores = {
            "new_location": 15,
            "new_device": 10,
            "unusual_time": 5,
            "repeated_failures": 20,
            "suspicious_activity": 40,
            "data_access": 15,
            "admin_operation": 25
        }
        
        for factor in risk_factors:
            risk_score += risk_factor_scores.get(factor, 5)
        
        # IP reputation (if available)
        if context.get("suspicious_ip", False):
            risk_score += 25
        
        # Time since last successful auth
        last_auth = context.get("last_auth_time")
        if last_auth:
            hours_since_auth = (datetime.utcnow() - last_auth).total_seconds() / 3600
            if hours_since_auth > 168:  # More than a week
                risk_score += 10
            elif hours_since_auth > 72:  # More than 3 days
                risk_score += 5
        
        # Convert score to risk level
        if risk_score >= 70:
            return MFARiskLevel.CRITICAL
        elif risk_score >= 50:
            return MFARiskLevel.HIGH
        elif risk_score >= 25:
            return MFARiskLevel.MEDIUM
        else:
            return MFARiskLevel.LOW
    
    def update_policy(self, policy_name: str, policy_value: Any, admin_user_id: str) -> Tuple[bool, str]:
        """Update MFA policy (admin function)"""
        try:
            if policy_name not in self.default_policies:
                return False, f"Unknown policy: {policy_name}"
            
            old_value = self.default_policies[policy_name]
            self.default_policies[policy_name] = policy_value
            
            # Log policy change
            self.audit_service.log_event(
                MFAAuditEvent.SETUP_COMPLETED,
                admin_user_id=admin_user_id,
                details={
                    "policy_name": policy_name,
                    "old_value": old_value,
                    "new_value": policy_value,
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            return True, f"Policy '{policy_name}' updated successfully"
            
        except Exception as e:
            return False, f"Failed to update policy: {str(e)}"
    
    def get_current_policies(self) -> Dict[str, Any]:
        """Get current MFA policies"""
        return {
            "default_policies": self.default_policies.copy(),
            "risk_policies": {level.value: policy for level, policy in self.risk_policies.items()},
            "last_updated": datetime.utcnow().isoformat()
        }