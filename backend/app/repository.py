
from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any


class PayloadNotFoundError(FileNotFoundError):
    pass


class PayloadRepository:
    """
    Read-only JSON repository for SIGNAL product payloads.

    Files are cached by (path, mtime_ns), so repeated API requests do not
    repeatedly parse unchanged JSON while local rebuilds are picked up
    automatically.
    """

    def __init__(self, payload_dir: Path):
        self.payload_dir = Path(payload_dir)
        self._cache: dict[Path, tuple[int, Any]] = {}
        self._lock = RLock()

    def _safe_symbol(self, symbol: str) -> str:
        clean = symbol.upper().strip()

        if not clean:
            raise ValueError("Ticker symbol cannot be empty.")

        allowed = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        )

        if any(ch not in allowed for ch in clean):
            raise ValueError("Ticker symbol contains invalid characters.")

        return clean

    def _read_json_from_root(self, path: Path, root: Path, error_label: str) -> Any:
        path = path.resolve()
        root = root.resolve()

        if root != path and root not in path.parents:
            raise ValueError(f"Attempted to read outside {error_label} directory.")

        if not path.exists():
            raise PayloadNotFoundError(str(path))

        stat = path.stat()
        mtime = stat.st_mtime_ns

        with self._lock:
            cached = self._cache.get(path)

            if cached and cached[0] == mtime:
                return cached[1]

            data = json.loads(
                path.read_text(encoding="utf-8")
            )

            self._cache[path] = (mtime, data)
            return data

    def _read_json(self, path: Path) -> Any:
        return self._read_json_from_root(
            path,
            self.payload_dir,
            "payload",
        )

    def _read_research_json(self, path: Path) -> Any:
        research_root = Path(__file__).resolve().parent / "data"
        return self._read_json_from_root(
            path,
            research_root,
            "research-data",
        )

    def manifest(self) -> dict[str, Any]:
        return self._read_json(
            self.payload_dir / "manifest.json"
        )

    def overview(self) -> dict[str, Any]:
        return self._read_json(
            self.payload_dir / "overview.json"
        )

    def investigations(self) -> dict[str, Any]:
        return self._read_json(
            self.payload_dir / "investigations.json"
        )

    def methodology(self) -> dict[str, Any]:
        return self._read_json(
            self.payload_dir / "methodology.json"
        )

    def reaction_validation(self) -> dict[str, Any]:
        # Research-layer validation is intentionally stored outside the
        # point-in-time product payloads. This prevents historical snapshots
        # from containing post-snapshot outcome information.
        return self._read_research_json(
            Path(__file__).resolve().parent
            / "data"
            / "reaction_validation.json"
        )

    def ticker_payload(
        self,
        symbol: str,
        filename: str,
    ) -> dict[str, Any]:
        symbol = self._safe_symbol(symbol)

        allowed = {
            "investigation.json",
            "summary.json",
            "activity.json",
            "context.json",
            "history.json",
        }

        if filename not in allowed:
            raise ValueError("Unsupported ticker payload.")

        return self._read_json(
            self.payload_dir
            / "tickers"
            / symbol
            / filename
        )

    def investigation(self, symbol: str) -> dict[str, Any]:
        return self.ticker_payload(
            symbol,
            "investigation.json",
        )

    def summary(self, symbol: str) -> dict[str, Any]:
        return self.ticker_payload(
            symbol,
            "summary.json",
        )

    def activity(self, symbol: str) -> dict[str, Any]:
        return self.ticker_payload(
            symbol,
            "activity.json",
        )

    def context(self, symbol: str) -> dict[str, Any]:
        return self.ticker_payload(
            symbol,
            "context.json",
        )

    def history(self, symbol: str) -> dict[str, Any]:
        return self.ticker_payload(
            symbol,
            "history.json",
        )
