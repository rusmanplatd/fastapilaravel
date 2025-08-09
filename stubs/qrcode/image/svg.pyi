from __future__ import annotations

from typing import Any
from .import BaseImage


class SvgImage(BaseImage):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class SvgPathImage(BaseImage):  
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class SvgFragmentImage(BaseImage):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...