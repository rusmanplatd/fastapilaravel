from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from app.Models.User import User


class UserMFASettings(BaseModel):
    __tablename__ = "user_mfa_settings"
    
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # type: ignore[arg-type]
    totp_secret: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # type: ignore[arg-type]
    totp_backup_tokens: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # type: ignore[arg-type]
    webauthn_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # type: ignore[arg-type]
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # type: ignore[arg-type]
    sms_phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # type: ignore[arg-type]
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)  # type: ignore[arg-type]
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # type: ignore[arg-type]
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="mfa_settings")


__all__ = ["UserMFASettings"]