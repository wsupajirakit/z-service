"""CORS (plan item B5).

Production serves the UI and the API from one origin, so no CORS is needed and none is
enabled. Local development with a Vite dev server on another port lists its origins in
env ZS_CORS_ORIGINS (comma-separated), e.g. http://localhost:5173,http://localhost:6600;
config.SecuritySettings refuses a wildcard.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zservice.security import config as security_config


def allowed_origins() -> list[str]:
    return list(security_config.get_settings().cors_origins)


def add_cors(app: FastAPI) -> None:
    origins = allowed_origins()
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-ZS-CSRF"],
    )
