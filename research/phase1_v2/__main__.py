"""Offline pilot tools. No execution flag and no API credentials are read."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from .contracts import SYMBOLS
from .calendar import TradingCalendar
from .fetcher import dry_run
from .offline import baselines, import_legacy, inventory, plan
from .storage import Store, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, action="append", default=[])
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, help="reviewed published calendar snapshot; still no spending approval")
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    args.store = args.store.resolve()
    if not (repo / "payloads").is_dir():
        parser.error("repo payloads not found")
    if args.store == repo or args.store in repo.parents or out == repo or out in repo.parents:
        parser.error("store/output must not replace repository root or its parents")
    out.mkdir(parents=True, exist_ok=True)
    store = Store(args.store)
    roots = [repo, *args.cache_root]
    report = inventory(roots, store)
    imports = import_legacy(repo, store)
    calendar = TradingCalendar.from_file(args.calendar) if args.calendar else None
    proposed = plan(store, calendar=calendar)
    validated = plan(store, include_candidates=False, calendar=calendar)
    write_json(out / "cache_inventory.json", report)
    write_json(out / "legacy_imports.json", imports)
    write_json(out / "fetch_plan.json", proposed)
    write_json(out / "validated_only_plan.json", validated)
    write_json(out / "dry_run.json", dry_run(proposed))
    with (out / "requests.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("request_id", "symbol", "endpoint", "start", "end", "expected_credits", "reason"), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(proposed["requests"])
    summary = {"symbols": list(SYMBOLS), "api_requests_executed": 0, "estimated_candidate_credits": proposed["estimated_credits"],
               "estimated_validated_only_credits": validated["estimated_credits"], "inventory_errors": len(report["errors"]),
               "parquet_batches": len(imports), "legacy_sessions": {}, "conflicts": {}, "field_counts": {}}
    daily_rows, _ = store.merged("daily", include_candidates=True)
    summary["analysis_start_eligibility"] = {sym: baselines([r for r in daily_rows if r["symbol"] == sym], "2026-04-01") for sym in SYMBOLS}
    for table in ("daily", "foreign_flow", "broker_activity"):
        rows, conflicts = store.merged(table, include_candidates=True)
        summary["legacy_sessions"][table] = dict(Counter(r["symbol"] for r in rows))
        summary["conflicts"][table] = len(conflicts)
        from .offline import REQUIRED
        summary["field_counts"][table] = {sym: {f: sum(r.get(f) is not None for r in rows if r["symbol"] == sym) for f in REQUIRED[table]} for sym in SYMBOLS}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
