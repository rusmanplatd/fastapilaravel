from __future__ import annotations

from typing import Any
from PIL import Image


class BaseImage:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    
    def save(self, stream: Any, **kwargs: Any) -> None: ...