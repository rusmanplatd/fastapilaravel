from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, func, event, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.Utils.ULIDUtils import generate_ulid, ULID

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    
    id: Mapped[ULID] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    # Audit columns for tracking who created/updated the record
    created_by: Mapped[Optional[ULID]] = mapped_column(String(26), ForeignKey("users.id"), nullable=True)  # type: ignore[arg-type]
    updated_by: Mapped[Optional[ULID]] = mapped_column(String(26), ForeignKey("users.id"), nullable=True)  # type: ignore[arg-type]
    
    # Audit relationships
    created_by_user: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[created_by], post_update=True
    )
    updated_by_user: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[updated_by], post_update=True
    )
    
    def __init__(self, **kwargs: Any) -> None:
        if 'id' not in kwargs:
            kwargs['id'] = generate_ulid()
        super().__init__(**kwargs)


    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Event listener to generate ULID for new instances
@event.listens_for(BaseModel, 'before_insert', propagate=True)
def generate_ulid_before_insert(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Generate ULID for new instances if not provided."""
    del mapper, connection  # Unused parameters required by SQLAlchemy
    if not target.id:
        target.id = generate_ulid()