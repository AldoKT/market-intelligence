"""Offline regression tests: data loss, coverage and credit boundary invariants."""
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pyarrow.parquet as pq
from .contracts import api_rows, digest, prepare
from .calendar import TradingCalendar
from .fetcher import ApprovalRequired, authorize, dry_run, execute, validate_plan
from .offline import baselines, inventory, plan, reconcile
from .storage import Store, exclusive

def daily(close=10, **extra):
    return {"symbol": "ANTM", "date": "2026-04-01", "open": 10, "high": 100, "low": 0,
            "close": close, "volume_shares": 1000, "market_cap_idr": 10000, **extra}

def rehash(body):
    body.pop("plan_sha256", None)
    body["plan_sha256"] = digest(body)
    return body

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "raw")

    def ingest(self, rows, raw=b"one", provenance="legacy_candidate", table="daily"):
        return self.store.ingest(table, rows, source_bytes=raw, provenance=provenance)

    def test_explicit_arrow_types_and_unknown_retrieval(self):
        info = self.ingest([daily()])
        p = self.store.root / "batches" / "daily" / (info["batch_id"] + ".parquet")
        table = pq.read_table(p)
        self.assertEqual(str(table.schema.field("date").type), "date32[day]")
        self.assertEqual(str(table.schema.field("volume_shares").type), "int64")
        self.assertIsNone(table.to_pylist()[0]["retrieved_at"])
        self.assertEqual(self.store.rows("daily"), [])
        self.assertEqual(len(self.store.rows("daily", True)), 1)

    def test_idempotent_import_and_exact_duplicate(self):
        a = self.ingest([daily(), daily()])
        b = self.ingest([daily(), daily()])
        self.assertEqual(a["batch_id"], b["batch_id"])
        self.assertEqual(a["accepted_rows"], 1)

    def test_partial_nulls_do_not_overwrite(self):
        self.ingest([daily()])
        self.ingest([daily(close=None)], b"two")
        rows, conflicts = self.store.merged("daily", True)
        self.assertEqual(rows[0]["close"], 10)
        self.assertEqual(conflicts, [])
        self.assertEqual(len(rows[0]["revisions"]), 2)

    def test_conflict_blocks_and_decision_invalidates(self):
        self.ingest([daily()])
        self.ingest([daily(close=11)], b"two")
        rows, conflicts = self.store.merged("daily", True)
        self.assertIsNone(rows[0]["close"])
        self.assertIn("close", rows[0]["blocked_fields"])
        self.assertEqual(len(conflicts), 1)
        self.store.resolve("daily", ["ANTM", "2026-04-01"], "close", 11, reviewer="human", evidence="source checked")
        self.assertEqual(self.store.merged("daily", True)[0][0]["close"], 11)
        self.ingest([daily(close=12)], b"three")
        self.assertIsNone(self.store.merged("daily", True)[0][0]["close"])

    def test_bad_batch_preserved_and_quarantined(self):
        for name, row in (("ohlc", daily(low=20)), ("negative", daily(volume_shares=-1)),
                          ("fractional", daily(volume_shares=1.1)), ("nan", daily(close=float("nan")))):
            info = self.ingest([daily(), row], name.encode())
            self.assertEqual(info["status"], "quarantined")
            self.assertTrue(info["failures"])
            self.assertTrue((self.store.root / "sources" / (info["source_sha256"] + ".blob")).exists())
        self.assertEqual(self.store.rows("daily", True), [])

    def test_cross_revision_merge_is_validated(self):
        self.ingest([daily(high=None, low=None, open=110, close=None)])
        self.ingest([daily(high=100, open=None, close=None)], b"two")
        rows, _ = self.store.merged("daily", True)
        self.assertIn("row_validation_error", rows[0])
        self.assertIsNone(rows[0]["open"])

    def test_explicit_legacy_promotion_and_export(self):
        info = self.ingest([daily()])
        with self.assertRaises(ValueError):
            self.store.promote_legacy("daily", info["batch_id"], reviewer="", evidence="")
        self.store.promote_legacy("daily", info["batch_id"], reviewer="human", evidence="source comparison complete")
        self.assertEqual(self.store.rows("daily")[0]["validation_status"], "validated_legacy")
        output = self.root / "daily.parquet"
        self.assertEqual(self.store.export("daily", output)["rows"], 1)
        self.assertEqual(pq.read_table(output).to_pylist()[0]["close"], 10)

    def test_api_wrong_symbol_or_date_is_quarantined(self):
        request = {"symbol": "ANTM", "start": "2026-04-01", "end": "2026-04-01"}
        for row in (daily(symbol="INCO"), daily(date="2026-04-02")):
            info = self.store.ingest("daily", [row], source_bytes=str(row).encode(), provenance="api", request=request)
            self.assertEqual(info["status"], "quarantined")

    def test_foreign_null_is_not_zero_and_identity(self):
        _, rows = api_rows("foreign-flow", {"symbol": "ANTM.JK", "data": [{"date": "2026-04-01", "net_foreign_inflow": 1, "foreign_share": 0.1}]})
        self.assertIsNone(rows[0]["foreign_buy_idr"])
        prepare("foreign_flow", rows[0])
        with self.assertRaises(ValueError):
            prepare("foreign_flow", {**rows[0], "foreign_buy_idr": 10, "foreign_sell_idr": 5})

    def test_broker_split_and_integer_lots(self):
        _, rows = api_rows("broker-summary", {"symbol": "ANTM.JK", "data": [{"date": "2026-04-01", "summary": [
            {"broker_code": "AA", "bval": 100, "sval": 50, "nval": 50, "blot": 2, "slot": 1, "nlot": 1,
             "bfreq": 2, "sfreq": 1, "f_bval": 20, "f_bavg_per_share": 0.5}]}]})
        self.assertEqual(rows[0]["f_bavg_per_share"], 0.5)
        self.assertEqual(rows[0]["buy_lots"], 2)
        with self.assertRaises(ValueError):
            prepare("broker_activity", {**rows[0], "f_bval": 101})

    def test_recursive_inventory_and_no_inferred_broker_coverage(self):
        cache = self.root / "cache" / "nested" / "ANTM"
        cache.mkdir(parents=True)
        (cache / "daily.json").write_text(json.dumps([{"symbol": "ANTM", "date": "2026-04-01", "close": 10, "volume": 100}]))
        (cache / "broker-summary.json").write_text(json.dumps({"symbol": "ANTM", "data": [{"date": "2026-04-01", "summary": [{"broker_code": "AA", "bval": 10}]}]}))
        (cache / "broken.json").write_text("{")
        report = inventory([self.root / "cache"], self.store)
        self.assertEqual(report["recognised_pilot_rows"], 2)
        self.assertEqual(len(report["errors"]), 1)
        broker = [r for r in plan(self.store)["requests"] if r["endpoint"] == "/v2/broker-summary/ANTM/"]
        self.assertTrue(any("2026-04-01" in r["target_dates"] for r in broker))

    def test_reviewed_broker_session_is_reused_until_revision_changes(self):
        broker = {"symbol": "ANTM", "date": "2026-04-01", "broker_code": "AA",
                  "buy_value_idr": 100, "sell_value_idr": 100, "net_value_idr": 0,
                  "buy_lots": 10, "sell_lots": 10, "net_lots": 0, "buy_frequency": 1, "sell_frequency": 1}
        self.ingest([broker], provenance="api", table="broker_activity")
        self.store.attest_broker_coverage("ANTM", "2026-04-01", reviewer="TEST HUMAN", evidence="all brokers source checked")
        requests = [r for r in plan(self.store)["requests"] if r["endpoint"] == "/v2/broker-summary/ANTM/"]
        self.assertFalse(any("2026-04-01" in r["target_dates"] for r in requests))
        self.ingest([{**broker, "buy_lots": 20, "sell_lots": 20}], b"revision", provenance="api", table="broker_activity")
        self.assertEqual(self.store.broker_complete_dates(), set())

    def test_baseline_requires_warmup_and_excludes_current(self):
        rows = [{"symbol": "ANTM", "date": date(2026, 2, 1) + timedelta(days=i), "volume_shares": i} for i in range(25)]
        end = rows[-1]["date"]
        rows[-1]["volume_shares"] = 999999
        result = baselines(rows, end)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["volume_shares"], 13.5)
        self.assertFalse(baselines(rows[1:], end)["eligible"])
        self.assertFalse(baselines(rows[:-1], end)["eligible"])
        with self.assertRaises(ValueError):
            baselines(rows + [rows[0]], end)

    def test_reconcile_uses_one_side_and_flags_mismatch(self):
        key = ("ANTM", date(2026, 4, 1))
        rows = [{"symbol": key[0], "date": key[1], "buy_value_idr": 100, "sell_value_idr": 100,
                 "buy_lots": 10, "sell_lots": 10, "buy_frequency": 2, "sell_frequency": 2}]
        result = reconcile([daily(date=key[1])], rows, {key})[0]
        self.assertEqual(result["turnover_idr"], 100)
        self.assertEqual(result["avg_trade_value_idr"], 50)
        self.assertFalse(result["flags"])
        self.assertNotIn("turnover_idr", reconcile([daily(date=key[1], volume_shares=500)], rows, {key})[0])
        self.assertNotIn("turnover_idr", reconcile([], rows, set())[0])

    def test_market_scope_mismatch_blocks_derivation(self):
        key = ("ANTM", date(2026, 4, 1))
        rows = [{"symbol": key[0], "date": key[1], "buy_value_idr": 100, "sell_value_idr": 100,
                 "buy_lots": 10, "sell_lots": 10, "buy_frequency": 2, "sell_frequency": 2, "market_scope": "regular"}]
        report = reconcile([daily(date=key[1], market_scope="all")], rows, {key})[0]
        self.assertNotIn("turnover_idr", report)
        self.assertIn("daily/broker market scope mismatch", report["flags"])

class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "raw")
        self.calendar = TradingCalendar.from_file(Path(__file__).with_name("idx_calendar_2026.json"))
        full = plan(self.store, include_candidates=False, calendar=self.calendar)
        full["requests"] = full["requests"][:2]
        full.update(estimated_credits=2, calendar_reviewed=True,
                    legacy_sources_reviewed=True, broker_completeness_reviewed=True)
        self.plan = rehash(full)
        ids = [r["request_id"] for r in full["requests"]]
        self.approval = {"plan_sha256": full["plan_sha256"], "request_ids": ids, "max_credits": 2,
                         "reviewer": "TEST HUMAN", "approved_at": "2026-01-01T00:00:00+00:00", "evidence": "TEST ONLY",
                         "pilot_request_id": ids[0], "remaining_fetches_approved": False}
        self.ids = ids

    def response(self, request):
        self.assertTrue((self.store.root / "attempts.json").exists())
        return json.dumps([{"symbol": request["symbol"], "date": request["start"], "close": 10, "open": 10,
                            "high": 11, "low": 9, "volume": 100, "market_cap": 10000}]).encode()

    def test_dry_run_never_calls_transport(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network forbidden")):
            result = dry_run(self.plan)
        self.assertEqual(result["requests_executed"], 0)
        self.assertFalse((self.store.root / "attempts.json").exists())

    def test_missing_approval_or_unreviewed_plan_blocks_network(self):
        for approval in ({}, {**self.approval, "max_credits": 0}, {**self.approval, "reviewer": ""}):
            with self.assertRaises(ApprovalRequired):
                execute(self.plan, approval, [self.ids[0]], self.store, transport=lambda _: self.fail("network called"))
        self.plan["calendar_reviewed"] = False
        rehash(self.plan)
        with self.assertRaises(ApprovalRequired):
            authorize(self.plan, self.approval, [self.ids[0]], [])

    def test_candidate_coverage_cannot_execute_even_with_approval(self):
        self.plan["coverage_basis"] = "candidate_proposal"
        rehash(self.plan)
        self.approval["plan_sha256"] = self.plan["plan_sha256"]
        with self.assertRaises(ApprovalRequired):
            execute(self.plan, self.approval, [self.ids[0]], self.store, transport=lambda _: self.fail("network called"))

    def test_hash_change_and_allowlist(self):
        self.plan["requests"][0]["end"] = "2026-09-30"
        with self.assertRaises(ValueError):
            validate_plan(self.plan)
        request = self.plan["requests"][0]
        request["endpoint"] = "https://evil.test/"
        request["request_id"] = digest({k: v for k, v in request.items() if k != "request_id"})
        rehash(self.plan)
        with self.assertRaises(ValueError):
            validate_plan(self.plan)

    def test_approved_pilot_saves_raw_and_stops_before_rest(self):
        with self.assertRaises(ApprovalRequired):
            authorize(self.plan, self.approval, self.ids, [])
        manifests = execute(self.plan, self.approval, [self.ids[0]], self.store, transport=self.response)
        self.assertEqual(len(manifests), 1)
        ledger = json.loads((self.store.root / "attempts.json").read_text())
        self.assertEqual(ledger[0]["status"], "validated")
        self.assertIsNone(ledger[0]["reported_credits"])
        with self.assertRaises(ApprovalRequired):
            execute(self.plan, self.approval, [self.ids[1]], self.store, transport=lambda _: self.fail("network called"))
        after = {**self.approval, "remaining_fetches_approved": True, "pilot_review_evidence": "test response reviewed"}
        self.assertEqual(len(execute(self.plan, after, [self.ids[1]], self.store, transport=self.response)), 1)

    def test_ambiguous_timeout_reserves_credit_no_retry(self):
        def timeout(_):
            raise TimeoutError("simulated")
        with self.assertRaises(TimeoutError):
            execute(self.plan, self.approval, [self.ids[0]], self.store, transport=timeout)
        ledger = json.loads((self.store.root / "attempts.json").read_text())
        self.assertEqual(ledger[0]["status"], "unknown")
        self.assertEqual(ledger[0]["reserved_credits"], 1)
        with self.assertRaises(ApprovalRequired):
            execute(self.plan, self.approval, [self.ids[0]], self.store, transport=lambda _: self.fail("retried"))

    def test_raw_malformed_response_retained_and_blocked(self):
        raw = b"not JSON"
        with self.assertRaises(ValueError):
            execute(self.plan, self.approval, [self.ids[0]], self.store, transport=lambda _: raw)
        ledger = json.loads((self.store.root / "attempts.json").read_text())
        self.assertEqual(ledger[0]["status"], "quarantined")
        self.assertTrue((self.store.root / "sources" / (ledger[0]["response_sha256"] + ".blob")).exists())

    def test_global_budget_counts_prior_attempts(self):
        ledger = [{"request_id": self.ids[0], "status": "validated", "reserved_credits": 1}]
        after = {**self.approval, "max_credits": 1, "remaining_fetches_approved": True, "pilot_review_evidence": "reviewed"}
        with self.assertRaises(ApprovalRequired):
            authorize(self.plan, after, [self.ids[1]], ledger)

    def test_lock_prevents_concurrent_fetch(self):
        with exclusive(self.store.root / ".fetch.lock"):
            with self.assertRaises(FileExistsError):
                execute(self.plan, self.approval, [self.ids[0]], self.store, transport=lambda _: self.fail("network called"))

class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.calendar = TradingCalendar.from_file(Path(__file__).with_name("idx_calendar_2026.json"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "raw")

    def test_published_sessions_and_minimum_warmup(self):
        self.assertEqual(len(self.calendar.sessions(date(2026, 4, 1), date(2026, 9, 30))), 121)
        prior = self.calendar.sessions(date(2026, 2, 1), date(2026, 3, 31))
        self.assertEqual(len(prior), 35)
        self.assertEqual(prior[-24], date(2026, 2, 19))
        self.assertNotIn(date(2026, 6, 16), self.calendar.sessions(date(2026, 6, 1), date(2026, 6, 30)))

    def test_calendar_plan_has_70_requests_and_no_coverage_holes(self):
        result = plan(self.store, calendar=self.calendar, include_candidates=False)
        self.assertEqual(result["estimated_credits"], 70)
        expected = set(map(str, self.calendar.sessions(date(2026, 2, 1), date(2026, 9, 30))))
        for symbol in ("ANTM", "INCO", "BBCA"):
            for endpoint in ("daily", "foreign-flow", "broker-summary"):
                requests = [r for r in result["requests"] if r["endpoint"] == f"/v2/{endpoint}/{symbol}/"]
                actual = [d for r in requests for d in r["target_dates"]]
                self.assertEqual(set(actual), expected)
                self.assertEqual(len(actual), len(expected))
        validate_plan(result)

    def test_calendar_evidence_and_month_counts_fail_closed(self):
        changed = dict(self.calendar.snapshot)
        changed["holidays"] = [*changed["holidays"], "2026-02-02"]
        with self.assertRaises(ValueError):
            TradingCalendar(changed)
        result = plan(self.store, calendar=self.calendar)
        result["calendar_evidence"]["snapshot"]["reviewed_by"] = "changed"
        rehash(result)
        with self.assertRaises(ValueError):
            validate_plan(result)

    def test_short_warmup_envelope_cannot_execute(self):
        result = plan(self.store, start=date(2026, 3, 1), calendar=self.calendar)
        with self.assertRaises(ValueError):
            validate_plan(result)

    def test_holiday_target_is_rejected_even_with_rehashed_plan(self):
        result = plan(self.store, calendar=self.calendar)
        request = result["requests"][0]
        request["target_dates"].append("2026-02-16")
        request["request_id"] = digest({k: v for k, v in request.items() if k != "request_id"})
        rehash(result)
        with self.assertRaises(ValueError):
            validate_plan(result)

    def test_symbol_exclusion_requires_evidence_and_changes_targets(self):
        snapshot = dict(self.calendar.snapshot)
        snapshot["symbol_exclusions"] = [{"symbol": "ANTM", "date": "2026-02-02", "reason": "TEST suspension", "source": "TEST only"}]
        changed = TradingCalendar(snapshot)
        result = plan(self.store, calendar=changed)
        self.assertFalse(any("2026-02-02" in r.get("target_dates", []) for r in result["requests"] if r.get("symbol") == "ANTM"))
        self.assertTrue(any("2026-02-02" in r.get("target_dates", []) for r in result["requests"] if r.get("symbol") == "INCO"))
        snapshot["symbol_exclusions"][0]["source"] = ""
        with self.assertRaises(ValueError):
            TradingCalendar(snapshot)

if __name__ == "__main__":
    unittest.main()
