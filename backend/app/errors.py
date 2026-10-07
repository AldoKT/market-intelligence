
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .repository import PayloadNotFoundError


async def payload_not_found_handler(
    request: Request,
    exc: PayloadNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Requested SIGNAL payload was not found.",
            "path": str(exc),
        },
    )


async def value_error_handler(
    request: Request,
    exc: ValueError,
):
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
        },
    )


async def broker_data_unavailable_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=503, content={
        "detail": "Data broker lokal tidak valid atau belum dapat dibaca. Periksa kembali paket data sebelum melanjutkan."
    })
