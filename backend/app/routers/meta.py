
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_repository
from ..repository import PayloadRepository


router = APIRouter(
    prefix="/api",
    tags=["meta"],
)


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SIGNAL API",
    }


@router.get("/manifest")
def manifest(
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.manifest()
