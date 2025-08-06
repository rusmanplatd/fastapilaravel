from sqlalchemy import Column, String, ForeignKey, Table, DateTime, func
from app.Models import Base

# Association table for direct user permissions (not through roles)
user_permission_table = Table(
    'user_permissions',
    Base.metadata,
    Column('id', String(26), primary_key=True),
    Column('user_id', String(26), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('permission_id', String(26), ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
    Column('assigned_at', DateTime, server_default=func.now(), nullable=False),
    Column('assigned_by', String(26), ForeignKey('users.id'), nullable=True),
    # Add unique constraint to prevent duplicate user-permission pairs
    schema=None
)

# Create index for better query performance
from sqlalchemy import Index
Index('idx_user_permission_user_id', user_permission_table.c.user_id)
Index('idx_user_permission_permission_id', user_permission_table.c.permission_id)
Index('idx_user_permission_unique', user_permission_table.c.user_id, user_permission_table.c.permission_id, unique=True)