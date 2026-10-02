
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_api_contract(tmp_path, monkeypatch):
    payload = tmp_path / "payload"
    ticker = payload / "tickers" / "ANTM"

    ticker.mkdir(parents=True)

    (payload / "manifest.json").write_text(
        json.dumps(
            {
                "methodology_version": "1.0-candidate",
                "as_of": "2026-09-09",
                "symbols": ["ANTM"],
                "files": {},
                "raw_market_activity_enrichment": False,
            }
        )
    )

    (payload / "overview.json").write_text(
        json.dumps(
            {
                "methodology_version": "1.0-candidate",
                "as_of": "2026-09-09",
                "headline": "1 active investigation detected after market close",
                "kpis": {},
                "spotlight": {"symbol": "ANTM"},
                "active_investigations": [{"symbol": "ANTM"}],
                "recent_changes": [],
            }
        )
    )

    (payload / "investigations.json").write_text(
        json.dumps(
            {
                "methodology_version": "1.0-candidate",
                "as_of": "2026-09-09",
                "items": [
                    {
                        "symbol": "ANTM",
                        "state": "EMERGING",
                        "active": True,
                        "peer_group": "basic_materials",
                        "context_scope": "MARKET_WIDE_ACTIVITY",
                    }
                ],
                "filters": {},
            }
        )
    )

    (payload / "methodology.json").write_text(
        json.dumps({"candidate_name": "SIGNAL Methodology v1.0 Candidate"})
    )

    for name in [
        "investigation.json",
        "summary.json",
        "activity.json",
        "context.json",
        "history.json",
    ]:
        (ticker / name).write_text(
            json.dumps({"symbol": "ANTM", "file": name})
        )

    monkeypatch.setenv(
        "SIGNAL_PAYLOAD_DIR",
        str(payload),
    )

    from app.dependencies import get_repository
    get_repository.cache_clear()

    from app.main import create_app

    client = TestClient(create_app())

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/overview").status_code == 200

    response = client.get(
        "/api/investigations",
        params={"active": "true"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    assert (
        client.get(
            "/api/investigations/ANTM"
        ).status_code
        == 200
    )

    assert (
        client.get(
            "/api/investigations/ZZZZ"
        ).status_code
        == 404
    )
