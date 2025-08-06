from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime
from sqlalchemy import String, DateTime, func, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.Utils.ULIDUtils import generate_ulid, ULID


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    
    id: Mapped[ULID] = mapped_column(String(26), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
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
    if not target.id:
        target.id = generate_ulid()