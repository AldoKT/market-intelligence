
from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from .repository import PayloadRepository


@lru_cache(maxsize=1)
def get_repository() -> PayloadRepository:
    settings = get_settings()
    return PayloadRepository(
        settings.payload_dir
    )
