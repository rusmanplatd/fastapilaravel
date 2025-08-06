from fastapi import FastAPI
from routes import api_router, web_router
from app.Http.Middleware import add_cors_middleware
from config import create_tables, settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

add_cors_middleware(app)

app.include_router(web_router)
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    create_tables()
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} started!")


@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=settings.DEBUG
    )