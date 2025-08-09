from __future__ import annotations

from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, select
from app.Models.BaseModel import BaseModel

# Association table for chat room members
chat_room_members = Table(
    'chat_room_members',
    BaseModel.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('chat_room_id', Integer, ForeignKey('chat_rooms.id'), primary_key=True),
    Column('joined_at', DateTime, default=func.now()),
    Column('is_admin', Boolean, default=False)
)

class ChatRoom(BaseModel):
    """Chat room model for broadcasting authorization."""
    
    __tablename__ = 'chat_rooms'
    
    id = Column(Integer, primary_key=True)  # type: ignore[assignment]
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    is_private = Column(Boolean, default=False)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=func.now())  # type: ignore[assignment]
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # type: ignore[assignment]
    
    # Relationships
    created_by = relationship("User", foreign_keys="ChatRoom.created_by_user_id")
    members = relationship("User", secondary="chat_room_members")
    
    def is_member(self, user_id: int) -> bool:
        """Check if user is a member of this chat room."""
        return any(member.id == user_id for member in self.members)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin of this chat room."""
        from app.Foundation.Application import app
        db = app().resolve('db')  # type: ignore[attr-defined]
        
        result = db.execute(
            select(chat_room_members).where(  # type: ignore[call-overload]
                chat_room_members.c.user_id == user_id,
                chat_room_members.c.chat_room_id == self.id,  # type: ignore
                chat_room_members.c.is_admin == True
            )
        ).first()
        
        return result is not None
    
    def can_join(self, user_id: int) -> bool:
        """Check if user can join this chat room."""
        if not self.is_private:
            return True
        
        return self.is_member(user_id) or self.created_by_user_id == user_id
    
    @classmethod
    def find(cls, room_id: int) -> Optional['ChatRoom']:  # type: ignore[override]
        """Find chat room by ID."""
        from app.Foundation.Application import app
        db = app().resolve('db')  # type: ignore[attr-defined]
        
        return db.query(cls).filter(cls.id == room_id).first()  # type: ignore[has-type]