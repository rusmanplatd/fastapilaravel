from __future__ import annotations

# Import your interfaces here
from .Repository.BaseRepositoryInterface import BaseRepositoryInterface
from .Repository.UserRepositoryInterface import UserRepositoryInterface

__all__: list[str] = [
    'BaseRepositoryInterface',
    'UserRepositoryInterface',
]