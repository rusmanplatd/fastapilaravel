from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, Callable, List, Union, ClassVar
from datetime import datetime
from sqlalchemy import String, DateTime, func, event, ForeignKey, and_, or_
from sqlalchemy.sql import Select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Query
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from functools import wraps

from app.Utils.ULIDUtils import generate_ulid, ULID

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    
    # Laravel-style hidden/fillable attributes
    __fillable__: ClassVar[List[str]] = []
    __guarded__: ClassVar[List[str]] = ['id', 'created_at', 'updated_at']
    __hidden__: ClassVar[List[str]] = []
    __visible__: ClassVar[List[str]] = []
    __casts__: ClassVar[Dict[str, str]] = {}
    __dates__: ClassVar[List[str]] = ['created_at', 'updated_at']
    __appends__: ClassVar[List[str]] = []
    
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
        """Convert model to dictionary, respecting hidden/visible attributes."""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        
        # Apply hidden attributes
        if self.__hidden__:
            for attr in self.__hidden__:
                result.pop(attr, None)
        
        # Apply visible attributes (if set, only show these)
        if self.__visible__:
            result = {k: v for k, v in result.items() if k in self.__visible__}
        
        # Add appended attributes
        for attr in self.__appends__:
            if hasattr(self, attr):
                result[attr] = getattr(self, attr)
        
        return result
    
    def fill(self, attributes: Dict[str, Any]) -> BaseModel:
        """Laravel-style mass assignment with fillable/guarded protection."""
        for key, value in attributes.items():
            if self._is_fillable(key):
                setattr(self, key, value)
        return self
    
    def _is_fillable(self, key: str) -> bool:
        """Check if attribute is mass assignable."""
        if self.__fillable__:
            return key in self.__fillable__
        return key not in self.__guarded__
    
    @classmethod
    def scope_where_not_null(cls, query: Select[Any], column: str) -> Select[Any]:
        """Laravel-style scope for non-null values."""
        return query.where(getattr(cls, column).is_not(None))
    
    @classmethod
    def scope_where_null(cls, query: Select[Any], column: str) -> Select[Any]:
        """Laravel-style scope for null values."""
        return query.where(getattr(cls, column).is_(None))
    
    @classmethod
    def scope_where_in(cls, query: Select[Any], column: str, values: List[Any]) -> Select[Any]:
        """Laravel-style scope for IN clause."""
        return query.where(getattr(cls, column).in_(values))
    
    @classmethod
    def scope_where_not_in(cls, query: Select[Any], column: str, values: List[Any]) -> Select[Any]:
        """Laravel-style scope for NOT IN clause."""
        return query.where(~getattr(cls, column).in_(values))
    
    @classmethod
    def scope_where_between(cls, query: Select[Any], column: str, start: Any, end: Any) -> Select[Any]:
        """Laravel-style scope for BETWEEN clause."""
        return query.where(getattr(cls, column).between(start, end))
    
    @classmethod
    def scope_latest(cls, query: Select[Any], column: str = 'created_at') -> Select[Any]:
        """Laravel-style scope for latest records."""
        return query.order_by(getattr(cls, column).desc())
    
    @classmethod
    def scope_oldest(cls, query: Select[Any], column: str = 'created_at') -> Select[Any]:
        """Laravel-style scope for oldest records."""
        return query.order_by(getattr(cls, column).asc())
    
    def fresh(self) -> Optional[BaseModel]:
        """Laravel-style fresh method to reload from database."""
        from sqlalchemy.orm import sessionmaker
        # This would need to be implemented with actual session
        return self
    
    def refresh(self) -> BaseModel:
        """Laravel-style refresh method."""
        # This would need to be implemented with actual session
        return self


# Event listener to generate ULID for new instances
@event.listens_for(BaseModel, 'before_insert', propagate=True)
def generate_ulid_before_insert(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Generate ULID for new instances if not provided."""
    del mapper, connection  # Unused parameters required by SQLAlchemy
    if not target.id:
        target.id = generate_ulid()