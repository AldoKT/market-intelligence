"""Published exchange sessions, distinct from returned ticker coverage."""
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path
from .contracts import digest

class TradingCalendar:
    def __init__(self, snapshot):
        self.snapshot = json.loads(json.dumps(snapshot))
        self.start = date.fromisoformat(snapshot["valid_from"])
        self.end = date.fromisoformat(snapshot["valid_to"])
        if self.start > self.end or not snapshot.get("sources") or not snapshot.get("reviewed_by"):
            raise ValueError("calendar coverage and source review evidence required")
        self.holidays = set(map(date.fromisoformat, snapshot["holidays"]))
        if len(self.holidays) != len(snapshot["holidays"]) or any(not self.start <= d <= self.end or d.weekday() >= 5 for d in self.holidays):
            raise ValueError("duplicate, weekend or out-of-range holiday")
        self.exclusions = {}
        for item in snapshot.get("symbol_exclusions", []):
            if not item.get("source") or not item.get("reason") or not item.get("symbol"):
                raise ValueError("source-backed symbol exclusion required")
            day = date.fromisoformat(item["date"])
            if not self.start <= day <= self.end or day.weekday() >= 5 or day in self.holidays:
                raise ValueError("invalid symbol exclusion date")
            key = (item["symbol"], day)
            if key in self.exclusions:
                raise ValueError("duplicate symbol exclusion")
            self.exclusions[key] = item
        expected = snapshot.get("expected_month_sessions")
        actual = dict(Counter(str(d)[:7] for d in self.sessions(self.start, self.end)))
        if expected is not None and expected != actual:
            raise ValueError("calendar month counts do not match published schedule")

    @classmethod
    def from_file(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def sessions(self, start, end, symbol=None):
        if not self.start <= start <= end <= self.end:
            raise ValueError("requested range outside calendar evidence")
        result = []
        day = start
        while day <= end:
            if day.weekday() < 5 and day not in self.holidays and (symbol, day) not in self.exclusions:
                result.append(day)
            day += timedelta(days=1)
        return result

    def evidence(self):
        return {"snapshot": self.snapshot, "sha256": digest(self.snapshot)}
