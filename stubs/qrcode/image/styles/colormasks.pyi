from __future__ import annotations

from typing import Any, Tuple


class ColorMask:
    def __init__(self) -> None: ...


class SolidFillColorMask(ColorMask):
    def __init__(self, front_color: Tuple[int, int, int] = (0, 0, 0)) -> None: ...


class SquareGradiantColorMask(ColorMask):
    def __init__(
        self, 
        back_color: Tuple[int, int, int] = (255, 255, 255),
        center_color: Tuple[int, int, int] = (0, 0, 0),
        edge_color: Tuple[int, int, int] = (0, 0, 0),
        **kwargs: Any
    ) -> None: ...


class RadialGradiantColorMask(ColorMask):
    def __init__(self, *args: Any) -> None: ...