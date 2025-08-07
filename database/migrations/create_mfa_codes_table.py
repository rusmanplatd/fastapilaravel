from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from enum import Enum

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class MFACodeType(str, Enum):
    TOTP = "totp"
    SMS = "sms"
    BACKUP = "backup"
    EMAIL = "email"


class MFACode(BaseModel):
    __tablename__ = "mfa_codes"
    
    user_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    code: Mapped[str] = mapped_column(nullable=False, index=True)
    code_type: Mapped[MFACodeType] = mapped_column(SQLEnum(MFACodeType), nullable=False)
    used: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(nullable=True)  # For temporary session tracking
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mfa_codes")