from __future__ import annotations

from typing import Any, Dict, Optional, Union

# Stub for PIL Image to avoid import issues
class Image: ...


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
    def make_image(self, fill_color: str = "black", back_color: str = "white") -> Image: ...


def make(data: Union[str, bytes], **kwargs: Any) -> Image: ...