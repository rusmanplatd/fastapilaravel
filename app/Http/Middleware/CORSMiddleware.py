from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware


def add_cors_middleware(app):
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )