from sqlalchemy import Column, Integer, ForeignKey, Table, DateTime, func
from app.Models import Base

# Association table for many-to-many relationship between users and roles
user_role_table = Table(
    'user_roles',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
    Column('assigned_at', DateTime, server_default=func.now(), nullable=False),
    Column('assigned_by', Integer, ForeignKey('users.id'), nullable=True),
    # Add unique constraint to prevent duplicate user-role pairs
    schema=None
)

# Create index for better query performance
from sqlalchemy import Index
Index('idx_user_role_user_id', user_role_table.c.user_id)
Index('idx_user_role_role_id', user_role_table.c.role_id)
Index('idx_user_role_unique', user_role_table.c.user_id, user_role_table.c.role_id, unique=True)