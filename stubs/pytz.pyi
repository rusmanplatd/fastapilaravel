"""Type stubs for pytz"""
from typing import Any, Dict, Optional
from datetime import datetime, tzinfo
from abc import ABCMeta

class BaseTzInfo(tzinfo, metaclass=ABCMeta):
    def __init__(self) -> None: ...

class UTC(BaseTzInfo):
    def utcoffset(self, dt: Optional[datetime]) -> Any: ...
    def tzname(self, dt: Optional[datetime]) -> str: ...
    def dst(self, dt: Optional[datetime]) -> Any: ...

utc: UTC

timezone: Dict[str, BaseTzInfo]

def timezone_at(lat: float, lng: float) -> str: ...