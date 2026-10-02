
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_repository
from ..repository import PayloadRepository


router = APIRouter(
    prefix="/api",
    tags=["overview"],
)


@router.get("/overview")
def get_overview(
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.overview()
