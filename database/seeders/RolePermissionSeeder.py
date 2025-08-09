"""
Role Permission Seeder
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from .SeederManager import Seeder

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

class RolePermissionSeeder(Seeder):
    """Seed roles and permissions"""
    
    def run(self, db: Session) -> None:
        """Run the seeder"""
        pass