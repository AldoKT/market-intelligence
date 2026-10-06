"""Recursive cache inventory, legacy import and a provisional gap plan."""
from collections import Counter
from datetime import date, timedelta
import json
import fnmatch
from pathlib import Path
import pyarrow.parquet as pq
from .contracts import DAILY_MAP, FLOW_MAP, KEYS, SYMBOLS, api_rows, digest, symbol, unwrap
from .storage import Store, write_json

SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "rework_phase1_v2"}
REQUIRED = {"daily": tuple(DAILY_MAP.values()), "foreign_flow": ("net_foreign_inflow_idr", "foreign_share"),
            "broker_activity": ("buy_value_idr", "sell_value_idr", "net_value_idr", "buy_lots", "sell_lots", "net_lots", "buy_frequency", "sell_frequency")}

def cached_shape(body, path):
    value = unwrap(body)
    endpoint = str(body.get("endpoint", body.get("url", ""))) if isinstance(body, dict) else ""
    endpoint += " " + path.name
    sym = next((s for s in SYMBOLS if s in path.parts or s in path.name.upper()), None)
    if isinstance(value, dict) and isinstance(value.get("data"), list):
        data = value["data"]
        if "broker" in endpoint or (data and "summary" in data[0]):
            return api_rows("broker-summary", value, sym)
        if "foreign" in endpoint or (data and "net_foreign_inflow" in data[0]):
            return api_rows("foreign-flow", value, sym)
    if isinstance(value, list) and value:
        if "summary" in value[0]:
            return api_rows("broker-summary", {"symbol": sym, "data": value}, sym) if sym else None
        if all(k in value[0] for k in ("date", "close", "volume")):
            return api_rows("daily", value, sym)
        if "code" in value[0] and "name" in value[0]:
            return api_rows("brokers", value)
    return None

def inventory(roots, store):
    """Explicit roots only; unreadable entries are retained as unresolved."""
    entries, errors, seen = [], [], set()
    for root in roots:
        root = Path(root).resolve()
        if not root.exists():
            errors.append({"path": str(root), "error": "root not found"})
            continue
        # walk allows recording traversal errors; no secrets or network reads.
        import os
        def onerror(error):
            errors.append({"path": error.filename, "error": str(error)})
        for folder, dirs, files in os.walk(root, onerror=onerror):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for name in files:
                if any(fnmatch.fnmatch(name.lower(), pattern) for pattern in ("secrets.*", "secret.*", "api_key*", "apikey*", "credentials*", "service-account*")):
                    continue
                path = Path(folder) / name
                if path.suffix.lower() not in (".json", ".parquet", ".csv", ".zip") or path.resolve() in seen:
                    continue
                seen.add(path.resolve())
                entry = {"path": str(path), "kind": path.suffix.lower(), "recognized": False}
                try:
                    entry["bytes"] = path.stat().st_size
                    if path.suffix.lower() == ".json":
                        raw = path.read_bytes()
                        body = json.loads(raw)
                        shape = cached_shape(body, path)
                        if shape:
                            table, rows = shape
                            rows = [r for r in rows if table == "broker_registry" or r.get("symbol") in SYMBOLS]
                            entry.update(recognized=True, table=table, pilot_rows=len(rows))
                            if rows:
                                manifest = store.ingest(table, rows, source_bytes=raw, source_file=str(path), provenance="cache_candidate")
                                entry["batch_id"] = manifest["batch_id"]
                                entry["status"] = manifest["status"]
                    elif path.suffix.lower() == ".parquet":
                        parquet = pq.read_table(path)
                        table = path.stem.replace("-", "_")
                        from .contracts import FIELDS
                        if table in FIELDS and all(k in parquet.column_names for k in KEYS[table]):
                            rows = [r for r in parquet.to_pylist() if table == "broker_registry" or r.get("symbol") in SYMBOLS]
                            entry.update(recognized=True, table=table, pilot_rows=len(rows))
                            if rows:
                                manifest = store.ingest(table, rows, source_bytes=path.read_bytes(), source_file=str(path), provenance="cache_candidate")
                                entry.update(batch_id=manifest["batch_id"], status=manifest["status"])
                    else:
                        entry["review_required"] = "CSV/archive is reference only; explicit source adapter required before reuse"
                except (OSError, ValueError, KeyError, TypeError) as error:
                    entry["error"] = str(error)
                    errors.append({"path": str(path), "error": str(error)})
                entries.append(entry)
    return {"roots": [str(Path(r).resolve()) for r in roots], "files": entries,
            "errors": errors, "recognised_pilot_rows": sum(e.get("pilot_rows", 0) for e in entries),
            "coverage_status": "unresolved" if errors or any(e.get("review_required") for e in entries) else "candidate_only"}

def import_legacy(repo, store):
    report = []
    for snapshot in sorted((Path(repo) / "payloads").iterdir()):
        for sym in SYMBOLS:
            folder = snapshot / "tickers" / sym
            path = folder / "activity.json"
            if not path.exists():
                continue
            raw = path.read_bytes()
            points = json.loads(raw).get("series", [])
            for table, mapping in (("daily", DAILY_MAP), ("foreign_flow", FLOW_MAP)):
                rows = [{"symbol": sym, "date": p["date"], **{v: p.get(k) for k, v in mapping.items()}} for p in points]
                report.append(store.ingest(table, rows, source_bytes=raw, source_file=str(path)))
            context_path = folder / "context.json"
            if not context_path.exists():
                continue
            context_raw = context_path.read_bytes()
            context = json.loads(context_raw)
            news = []
            for item in context.get("relevant_news", []):
                news.append({"source": item.get("source"), "timestamp": item.get("timestamp"),
                             "title": item.get("title"), "content_id": digest(item),
                             "symbols": item.get("symbols") or [sym], "body": item.get("body"), "tags": item.get("tags")})
            events = [{"symbol": sym, "event_type": p.get("type") or "unknown", "event_date": p.get("date"),
                       "source_id": p.get("source_id") or digest(p), "announced_at": p.get("announced_at"),
                       "details": json.dumps(p, sort_keys=True)} for p in context.get("corporate_events", [])]
            for table, rows in (("news", news), ("corporate_events", events)):
                if rows:
                    report.append(store.ingest(table, rows, source_bytes=context_raw, source_file=str(context_path)))
    return report

def plan(store, *, start=date(2026, 2, 1), analysis_start=date(2026, 4, 1), end=date(2026, 9, 30), include_candidates=True, calendar=None):
    if not start <= analysis_start <= end:
        raise ValueError("invalid date envelope")
    requests, coverage, conflicts = [], {}, []
    for table in REQUIRED:
        rows, found_conflicts = store.merged(table, include_candidates)
        coverage[table] = {(r["symbol"], r["date"]): r for r in rows} if table != "broker_activity" else {}
        conflicts.extend(found_conflicts)
    # Broker completeness is not inferred from the mere existence of a few rows.
    complete_broker_dates = store.broker_complete_dates()
    for sym in SYMBOLS:
        target_sessions = set(calendar.sessions(start, end, sym)) if calendar is not None else None
        for endpoint, table, size in (("daily", "daily", 90), ("foreign-flow", "foreign_flow", 90), ("broker-summary", "broker_activity", 14)):
            missing = []
            day = start
            while day <= end:
                row = coverage[table].get((sym, day), {})
                missing_row = any(row.get(f) is None for f in REQUIRED[table])
                if table == "broker_activity" and (sym, day) in complete_broker_dates:
                    missing_row = False
                if (day in target_sessions if target_sessions is not None else day.weekday() < 5) and missing_row:
                    missing.append(day)
                day += timedelta(days=1)
            while missing:
                begin = missing[0]
                stop = min(begin + timedelta(days=size - 1), end)
                targets = [d for d in missing if d <= stop]
                # Trim trailing days with no missing target; the next window is
                # still anchored to the next missing session, not the last end.
                stop = targets[-1]
                req = {"symbol": sym, "endpoint": f"/v2/{endpoint}/{sym}/", "start": str(begin), "end": str(stop),
                       "expected_credits": 1, "target_dates": [str(d) for d in targets],
                       "reason": "raw broker completeness unresolved" if table == "broker_activity" else ("required field missing or conflicted" if include_candidates else "required field lacks validated source evidence")}
                req["request_id"] = digest(req)
                requests.append(req)
                missing = [d for d in missing if d > stop]
    registry, registry_conflicts = store.merged("broker_registry", include_candidates)
    if not registry or any(r["blocked_fields"] for r in registry):
        req = {"endpoint": "/v2/brokers/", "expected_credits": 1, "reason": "registry absent or conflicted"}
        req["request_id"] = digest(req)
        requests.append(req)
    body = {"schema_version": 1, "symbols": list(SYMBOLS), "analysis_start": str(analysis_start), "fetch_start": str(start), "end": str(end),
            "warmup_sessions": 24, "calendar_reviewed": calendar is not None,
            "calendar_evidence": calendar.evidence() if calendar is not None else None,
            "legacy_sources_reviewed": False, "broker_completeness_reviewed": False,
            "coverage_basis": "candidate_proposal" if include_candidates else "validated_only",
            "foreign_gross_policy": "optional; net/share required; gross missing remains null",
            "scope": "core pilot; context requests excluded", "conflicts": conflicts,
            "requests": requests, "estimated_credits": sum(r["expected_credits"] for r in requests),
            "api_requests_executed": 0}
    if calendar is not None:
        body["expected_analysis_sessions"] = {sym: len(calendar.sessions(analysis_start, end, sym)) for sym in SYMBOLS}
        body["expected_warmup_sessions"] = {sym: len(calendar.sessions(start, analysis_start - timedelta(days=1), sym)) for sym in SYMBOLS}
        body["calendar_policy"] = "Published scheduled sessions only; returned gaps and additional closures remain unresolved until source-backed reconciliation"
    return {**body, "plan_sha256": digest(body)}

def baselines(rows, evaluation_date, fields=("volume_shares",)):
    """20 prior sessions, never includes evaluation; no imputed observations."""
    evaluation_date = date.fromisoformat(str(evaluation_date))
    if len({r["symbol"] for r in rows}) > 1:
        raise ValueError("baseline requires a single symbol")
    dates = [r["date"] for r in rows]
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate session dates")
    prior = sorted((r for r in rows if r["date"] < evaluation_date), key=lambda r: r["date"])
    if len(prior) < 24:
        return {"eligible": False, "preceding_sessions": len(prior), "reason": "24 preceding sessions required"}
    current = next((r for r in rows if r["date"] == evaluation_date), None)
    if current is None or any(current.get(f) is None for f in fields):
        return {"eligible": False, "preceding_sessions": len(prior), "reason": "evaluation session/field missing"}
    from statistics import median
    result = {"eligible": True, "preceding_sessions": len(prior), "baseline_sessions": 20}
    for field in fields:
        values = [r.get(field) for r in prior[-20:]]
        result[field] = median(values) if all(v is not None for v in values) else None
        if result[field] is None:
            result["eligible"] = False
    return result

def reconcile(daily_rows, broker_rows, complete_dates):
    """Report one-sided totals; completeness must be attested by source review."""
    daily = {(r["symbol"], r["date"]): r for r in daily_rows}
    groups = {}
    for r in broker_rows:
        groups.setdefault((r["symbol"], r["date"]), []).append(r)
    report = []
    for key, rows in groups.items():
        item = {"symbol": key[0], "date": str(key[1]), "complete": key in complete_dates, "market_scope": None, "scope_status": "unverified", "flags": []}
        scopes = {r.get("market_scope") for r in rows if r.get("market_scope") is not None}
        daily_scope = daily.get(key, {}).get("market_scope")
        if len(scopes) > 1 or any(r.get("scope_conflict") for r in rows) or daily.get(key, {}).get("scope_conflict"):
            item["flags"].append("market scope conflict")
        elif scopes:
            item["market_scope"] = next(iter(scopes))
            if daily_scope is not None:
                if daily_scope != item["market_scope"]:
                    item["flags"].append("daily/broker market scope mismatch")
                else:
                    item["scope_status"] = "matching_source_labels"
        if key not in complete_dates:
            item["flags"].append("broker coverage not attested complete")
            report.append(item)
            continue
        fields = ("buy_value_idr", "sell_value_idr", "buy_frequency", "sell_frequency", "buy_lots", "sell_lots")
        if any(r.get(f) is None for r in rows for f in fields):
            item["flags"].append("broker field missing")
            report.append(item)
            continue
        totals = {f: sum(r[f] for r in rows) for f in fields}
        item["totals"] = totals
        for buy, sell in (("buy_value_idr", "sell_value_idr"), ("buy_frequency", "sell_frequency"), ("buy_lots", "sell_lots")):
            import math
            if not math.isclose(totals[buy], totals[sell], rel_tol=1e-9, abs_tol=0.01):
                item["flags"].append(f"buy/sell mismatch: {buy}")
        shares = totals["buy_lots"] * 100
        if daily.get(key, {}).get("volume_shares") != shares:
            item["flags"].append("daily shares versus broker lots mismatch or unavailable")
        if not item["flags"]:
            item.update(turnover_idr=totals["buy_value_idr"], transaction_count=totals["buy_frequency"], volume_shares=shares)
            frequency = totals["buy_frequency"]
            item["avg_trade_value_idr"] = totals["buy_value_idr"] / frequency if frequency else None
        report.append(item)
    return report
