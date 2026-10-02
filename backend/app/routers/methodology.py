
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_repository
from ..repository import PayloadRepository


router = APIRouter(
    prefix="/api",
    tags=["methodology"],
)


@router.get("/methodology")
def get_methodology(
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.methodology()


@router.get("/reaction-validation")
def get_reaction_validation(
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.reaction_validation()
