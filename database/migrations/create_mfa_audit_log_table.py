from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from enum import Enum

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class MFAAuditEvent(str, Enum):
    SETUP_INITIATED = "setup_initiated"
    SETUP_COMPLETED = "setup_completed"
    SETUP_FAILED = "setup_failed"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILED = "verification_failed"
    DEVICE_REGISTERED = "device_registered"
    DEVICE_REMOVED = "device_removed"
    BACKUP_CODE_USED = "backup_code_used"
    BACKUP_CODES_REGENERATED = "backup_codes_regenerated"
    MFA_DISABLED = "mfa_disabled"
    MFA_REQUIRED = "mfa_required"
    RATE_LIMITED = "rate_limited"
    ADMIN_BYPASS = "admin_bypass"
    RECOVERY_USED = "recovery_used"


class MFAAuditLog(BaseModel):
    __tablename__ = "mfa_audit_logs"
    
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mfa_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    admin_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Event details
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Risk assessment
    risk_score: Mapped[Optional[int]] = mapped_column(nullable=True)  # 0-100
    risk_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Relationships
    user: Mapped[Optional[User]] = relationship("User", foreign_keys=[user_id], back_populates="mfa_audit_logs")
    admin_user: Mapped[Optional[User]] = relationship("User", foreign_keys=[admin_user_id])