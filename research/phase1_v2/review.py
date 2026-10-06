"""Read-only technical review; never auto-promotes legacy source claims."""
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from .contracts import DAILY_MAP, FLOW_MAP, SYMBOLS, prepare
from .offline import REQUIRED

def legacy_review(repo, store, calendar):
    repo = Path(repo)
    reference_path = repo / "research" / "data" / "cross_stock_timeline_v0_3_1.csv"
    reference = {}
    if reference_path.exists():
        with reference_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("symbol") in SYMBOLS and row.get("close"):
                    reference[(row["symbol"], row["date"])] = float(row["close"])
    evidence_files = [reference_path, repo / "research" / "enrich_demo_market_data_v2_3.py",
                      repo / "validation" / "raw_source_quality.csv", repo / "validation" / "raw_source_detector_parity.csv"]
    evidence = [{"file": str(p.relative_to(repo)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in evidence_files if p.exists()]
    symbols = {}
    for sym in SYMBOLS:
        points, sources, failures = {}, [], []
        for path in sorted((repo / "payloads").glob(f"*/tickers/{sym}/activity.json")):
            raw = path.read_bytes()
            body = json.loads(raw)
            source = {"file": str(path.relative_to(repo)), "sha256": hashlib.sha256(raw).hexdigest(), "source_note": body.get("source_note"), "as_of": body.get("as_of")}
            sources.append(source)
            if body.get("identity", {}).get("symbol") != sym:
                failures.append({"source": source["file"], "reason": "identity mismatch"})
            file_dates = set()
            for p in body.get("series", []):
                day = date.fromisoformat(p["date"])
                if p["date"] in file_dates:
                    failures.append({"source": source["file"], "date": p["date"], "reason": "duplicate session"})
                file_dates.add(p["date"])
                if day > date.fromisoformat(body["as_of"]):
                    failures.append({"date": p["date"], "reason": "future date relative to snapshot"})
                if day not in calendar.sessions(calendar.start, calendar.end, sym):
                    failures.append({"date": p["date"], "reason": "off published calendar"})
                for table, mapping in (("daily", DAILY_MAP), ("foreign_flow", FLOW_MAP)):
                    try:
                        prepare(table, {"symbol": sym, "date": day, **{v: p.get(k) for k, v in mapping.items()}})
                    except ValueError as error:
                        failures.append({"date": p["date"], "table": table, "reason": str(error)})
                known = points.setdefault(p["date"], {})
                for field in (*DAILY_MAP, *FLOW_MAP, "turnover_idr", "transaction_count", "avg_trade_value_idr"):
                    value = p.get(field)
                    if value is not None:
                        if known.get(field) is not None and known[field] != value:
                            failures.append({"date": p["date"], "field": field, "reason": "snapshot value disagreement"})
                        else:
                            known[field] = value
        close_checks, activity_checks = 0, 0
        for day, p in points.items():
            expected = reference.get((sym, day))
            if expected is not None and p.get("close") is not None:
                close_checks += 1
                if not math.isclose(p["close"], expected, rel_tol=0, abs_tol=1e-8):
                    failures.append({"date": day, "reason": "stored timeline close disagreement"})
            if all(p.get(k) is not None for k in ("turnover_idr", "transaction_count", "avg_trade_value_idr")):
                activity_checks += 1
                if p["transaction_count"] <= 0 or not math.isclose(p["turnover_idr"] / p["transaction_count"], p["avg_trade_value_idr"], rel_tol=1e-10, abs_tol=0.01):
                    failures.append({"date": day, "reason": "average trade value identity mismatch"})
        span = calendar.sessions(date.fromisoformat(min(points)), date.fromisoformat(max(points)), sym) if points else []
        symbols[sym] = {"unique_sessions": len(points), "sources": sources, "checks": {"timeline_close": close_checks, "activity_identity": activity_checks},
                        "missing_in_legacy_span": [str(d) for d in span if str(d) not in points], "failures": failures,
                        "field_counts": {field: sum(p.get(field) is not None for p in points.values()) for field in (*DAILY_MAP, *FLOW_MAP)},
                        "structural_status": "PASS" if not failures else "FAIL", "source_status": "PARTIAL_PROVENANCE_RAW_RESPONSE_UNAVAILABLE", "promotion": "NOT_PROMOTED"}
    return {"review_type": "agent_technical_review_not_spending_approval", "symbols": symbols, "evidence": evidence,
            "decision": "Preserve legacy as candidates/reference. Prior raw-detector parity reports do not independently certify every exported OHLC/foreign field. No auto-promotion.",
            "api_requests_executed": 0}
