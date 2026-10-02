
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    payload_dir: Path
    cors_origins: list[str]


def get_settings() -> Settings:
    payload_dir = Path(
        os.getenv(
            "SIGNAL_PAYLOAD_DIR",
            "signal_product_payloads_v1_demo",
        )
    )

    raw_origins = os.getenv(
        "SIGNAL_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )

    cors_origins = [
        x.strip()
        for x in raw_origins.split(",")
        if x.strip()
    ]

    return Settings(
        payload_dir=payload_dir,
        cors_origins=cors_origins,
    )
