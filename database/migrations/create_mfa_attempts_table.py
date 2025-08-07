from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from enum import Enum

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class MFAAttemptStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed" 
    BLOCKED = "blocked"
    EXPIRED = "expired"


class MFAAttemptType(str, Enum):
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    SMS = "sms"
    BACKUP_CODE = "backup_code"


class MFAAttempt(BaseModel):
    __tablename__ = "mfa_attempts"
    
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    attempt_type: Mapped[MFAAttemptType] = mapped_column(SQLEnum(MFAAttemptType), nullable=False)
    status: Mapped[MFAAttemptStatus] = mapped_column(SQLEnum(MFAAttemptStatus), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Rate limiting fields
    attempts_count: Mapped[int] = mapped_column(Integer, default=1)
    blocked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mfa_attempts")