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
    
    user_id: Mapped[str] = mapped_column(String(26), ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    credential_id: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    public_key: Mapped[str] = mapped_column(nullable=False)  # Base64 encoded public key
    sign_count: Mapped[int] = mapped_column(default=0)
    name: Mapped[str] = mapped_column(nullable=False)  # User-friendly name for the device
    aaguid: Mapped[Optional[str]] = mapped_column(nullable=True)  # Authenticator AAGUID
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="webauthn_credentials")