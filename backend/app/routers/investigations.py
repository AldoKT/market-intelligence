
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_repository
from ..repository import PayloadRepository


router = APIRouter(
    prefix="/api/investigations",
    tags=["investigations"],
)


@router.get("")
def list_investigations(
    state: Optional[str] = None,
    peer_group: Optional[str] = None,
    context_scope: Optional[str] = None,
    active: Optional[bool] = None,
    q: Optional[str] = Query(
        default=None,
        description="Ticker search",
    ),
    repo: PayloadRepository = Depends(get_repository),
):
    payload = repo.investigations()

    items = payload.get("items", [])

    def keep(item: dict) -> bool:
        if state and item.get("state") != state:
            return False

        if (
            peer_group
            and item.get("peer_group") != peer_group
        ):
            return False

        if (
            context_scope
            and item.get("context_scope")
            != context_scope
        ):
            return False

        if (
            active is not None
            and bool(item.get("active")) != active
        ):
            return False

        if q:
            needle = q.upper().strip()

            if needle not in str(
                item.get("symbol", "")
            ).upper():
                return False

        return True

    filtered = [
        item
        for item in items
        if keep(item)
    ]

    return {
        **payload,
        "items": filtered,
        "count": len(filtered),
    }


@router.get("/{symbol}")
def get_investigation(
    symbol: str,
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.investigation(symbol)


@router.get("/{symbol}/summary")
def get_summary(
    symbol: str,
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.summary(symbol)


@router.get("/{symbol}/activity")
def get_activity(
    symbol: str,
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.activity(symbol)


@router.get("/{symbol}/context")
def get_context(
    symbol: str,
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.context(symbol)


@router.get("/{symbol}/history")
def get_history(
    symbol: str,
    repo: PayloadRepository = Depends(get_repository),
):
    return repo.history(symbol)
