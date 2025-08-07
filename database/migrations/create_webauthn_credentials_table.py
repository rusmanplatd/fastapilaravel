from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class WebAuthnCredential(BaseModel):
    __tablename__ = "webauthn_credentials"
    
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # Base64 encoded public key
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # User-friendly name for the device
    aaguid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # Authenticator AAGUID
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="webauthn_credentials")