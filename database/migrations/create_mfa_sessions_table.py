from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from enum import Enum

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class MFASessionStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class MFASession(BaseModel):
    __tablename__ = "mfa_sessions"
    
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[MFASessionStatus] = mapped_column(SQLEnum(MFASessionStatus), default=MFASessionStatus.PENDING)
    method_used: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # totp, webauthn, sms, backup
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mfa_sessions")