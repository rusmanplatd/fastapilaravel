from __future__ import annotations

from fastapi import APIRouter
from typing import Dict, Any

web_router = APIRouter()


@web_router.get("/")
async def welcome() -> Dict[str, Any]:
    return {"message": "Welcome to FastAPI with Laravel Structure"}


@web_router.get("/about")
async def about() -> Dict[str, Any]:
    return {
        "application": "FastAPI Laravel Style",
        "version": "1.0.0",
        "description": "A FastAPI application structured like Laravel"
    }