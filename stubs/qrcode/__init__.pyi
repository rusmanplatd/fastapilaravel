from __future__ import annotations

from typing import Any, Dict, Optional, Union
from io import BytesIO

# Stub for PIL Image to avoid import issues
class Image:
    def save(self, fp: Union[str, BytesIO], format: Optional[str] = None) -> None: ...
    def convert(self, mode: str) -> Image: ...
    def to_string(self, encoding: str = 'unicode') -> str: ...


class constants:
    ERROR_CORRECT_L: int = 1
    ERROR_CORRECT_M: int = 0
    ERROR_CORRECT_Q: int = 3
    ERROR_CORRECT_H: int = 2


class QRCode:
    def __init__(
        self,
        version: Optional[int] = None,
        error_correction: int = 1,
        box_size: int = 10,
        border: int = 4,
        image_factory: Optional[Any] = None,
        mask_pattern: Optional[int] = None
    ) -> None: ...
    
    def add_data(self, data: Union[str, bytes]) -> None: ...
    def make(self, fit: bool = True) -> None: ...
    def make_image(
        self, 
        fill_color: str = "black", 
        back_color: str = "white",
        image_factory: Optional[Any] = None,
        module_drawer: Optional[Any] = None,
        color_mask: Optional[Any] = None,
        **kwargs: Any
    ) -> Image: ...


def make(data: Union[str, bytes], **kwargs: Any) -> Image: ...