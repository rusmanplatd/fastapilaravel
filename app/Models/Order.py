from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.types import Numeric, Enum
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func
from app.Models.BaseModel import BaseModel
import enum

class OrderStatus(enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(BaseModel):
    """Order model for broadcasting authorization."""
    
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)  # type: ignore[assignment]
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_number = Column(String(100), unique=True, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=func.now())  # type: ignore[assignment]
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # type: ignore[assignment]
    
    # Relationships
    user = relationship("User", back_populates="orders")
    
    def is_owned_by(self, user_id: int) -> bool:
        """Check if order belongs to the given user."""
        return self.user_id == user_id
    
    @classmethod
    def find(cls, order_id: int) -> Optional['Order']:  # type: ignore[override]
        """Find order by ID."""
        from app.Foundation.Application import app
        db = app().make('db')
        
        return db.query(cls).filter(cls.id == order_id).first()  # type: ignore[has-type]