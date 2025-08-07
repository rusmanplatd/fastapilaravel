from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class UserMFASettings(BaseModel):
    __tablename__ = "user_mfa_settings"
    
    user_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    totp_enabled: Mapped[bool] = mapped_column(default=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(nullable=True)
    totp_backup_tokens: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array of backup codes
    webauthn_enabled: Mapped[bool] = mapped_column(default=False)
    sms_enabled: Mapped[bool] = mapped_column(default=False)
    sms_phone_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_required: Mapped[bool] = mapped_column(default=False)  # Force MFA for this user
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mfa_settings")