from __future__ import annotations

from typing import TYPE_CHECKING
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI


def add_cors_middleware(app: FastAPI) -> None:
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )