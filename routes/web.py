from fastapi import APIRouter

web_router = APIRouter()


@web_router.get("/")
async def welcome():
    return {"message": "Welcome to FastAPI with Laravel Structure"}


@web_router.get("/about")
async def about():
    return {
        "application": "FastAPI Laravel Style",
        "version": "1.0.0",
        "description": "A FastAPI application structured like Laravel"
    }