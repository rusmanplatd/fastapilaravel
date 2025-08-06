from sqlalchemy import Column, Integer, ForeignKey, Table
from app.Models import Base

# Association table for many-to-many relationship between roles and permissions
role_permission_table = Table(
    'role_permissions',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
    # Add unique constraint to prevent duplicate role-permission pairs
    schema=None
)

# Create index for better query performance
from sqlalchemy import Index
Index('idx_role_permission_role_id', role_permission_table.c.role_id)
Index('idx_role_permission_permission_id', role_permission_table.c.permission_id)
Index('idx_role_permission_unique', role_permission_table.c.role_id, role_permission_table.c.permission_id, unique=True)