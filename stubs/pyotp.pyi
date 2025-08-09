from __future__ import annotations

from typing import Optional, Any


class TOTP:
    def __init__(self, s: str, digits: int = 6, digest: Any = None, name: Optional[str] = None, issuer: Optional[str] = None) -> None: ...
    
    def verify(self, token: str, valid_window: int = 1, window: Optional[int] = None) -> bool: ...
    def now(self) -> str: ...
    def provisioning_uri(
        self, 
        name: Optional[str] = None, 
        issuer_name: Optional[str] = None, 
        image: Optional[str] = None
    ) -> str: ...


def random_base32(length: int = 16) -> str: ...