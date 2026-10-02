
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import (
    payload_not_found_handler,
    value_error_handler,
)
from .repository import PayloadNotFoundError
from .routers import (
    investigations,
    methodology,
    meta,
    overview,
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SIGNAL API",
        description=(
            "Read-only application layer for SIGNAL "
            "Market Intelligence product payloads."
        ),
        version="1.0.0-candidate",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.add_exception_handler(
        PayloadNotFoundError,
        payload_not_found_handler,
    )

    app.add_exception_handler(
        ValueError,
        value_error_handler,
    )

    app.include_router(meta.router)
    app.include_router(overview.router)
    app.include_router(
        investigations.router
    )
    app.include_router(
        methodology.router
    )

    return app


app = create_app()
