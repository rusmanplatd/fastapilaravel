from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
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
    
    user_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    session_token: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    status: Mapped[MFASessionStatus] = mapped_column(SQLEnum(MFASessionStatus), default=MFASessionStatus.PENDING)
    method_used: Mapped[Optional[str]] = mapped_column(nullable=True)  # totp, webauthn, sms, backup
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mfa_sessions")