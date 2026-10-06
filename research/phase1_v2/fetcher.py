"""Dry-run by default. Paid execution is an explicit, separately approved action."""
from datetime import date, datetime, timedelta
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from .contracts import SYMBOLS, api_rows, digest, now, symbol, unwrap
from .storage import Store, exclusive, write_json
from .calendar import TradingCalendar

class ApprovalRequired(ValueError):
    pass

def validate_plan(plan):
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    if plan.get("plan_sha256") != digest(body):
        raise ValueError("plan hash changed; re-review required")
    if plan.get("schema_version") != 1 or plan.get("symbols") != list(SYMBOLS):
        raise ValueError("unsupported pilot plan")
    if (plan.get("analysis_start"), plan.get("end"), plan.get("warmup_sessions")) != ("2026-04-01", "2026-09-30", 24):
        raise ValueError("pilot analysis contract changed")
    envelope_start = date.fromisoformat(plan["fetch_start"])
    envelope_end = date.fromisoformat(plan["end"])
    if envelope_start > date.fromisoformat(plan["analysis_start"]):
        raise ValueError("invalid warmup envelope")
    evidence = plan.get("calendar_evidence")
    calendar = None
    if isinstance(evidence, dict):
        if evidence.get("sha256") != digest(evidence["snapshot"]):
            raise ValueError("calendar snapshot hash changed")
        calendar = TradingCalendar(evidence["snapshot"])
        analysis_start = date.fromisoformat(plan["analysis_start"])
        for sym in SYMBOLS:
            warmup = len(calendar.sessions(envelope_start, analysis_start - timedelta(days=1), sym))
            if warmup < 24:
                raise ValueError("calendar envelope has fewer than 24 preceding sessions")
            if plan.get("expected_warmup_sessions", {}).get(sym) != warmup:
                raise ValueError("warmup count differs from calendar evidence")
            expected = len(calendar.sessions(analysis_start, envelope_end, sym))
            if plan.get("expected_analysis_sessions", {}).get(sym) != expected:
                raise ValueError("analysis count differs from calendar evidence")
    seen, seen_urls = set(), set()
    for request in plan["requests"]:
        if request.get("expected_credits") != 1:
            raise ValueError("unsupported credit estimate")
        canonical = {k: v for k, v in request.items() if k != "request_id"}
        if request.get("request_id") != digest(canonical) or request["request_id"] in seen:
            raise ValueError("invalid or duplicate request ID")
        seen.add(request["request_id"])
        url = request_url(request)
        if url in seen_urls:
            raise ValueError("duplicate endpoint/date request")
        seen_urls.add(url)
        match = re.fullmatch(r"/v2/(daily|foreign-flow|broker-summary)/(ANTM|INCO|BBCA)/", request["endpoint"])
        if match:
            endpoint, sym = match.groups()
            if request.get("symbol") != sym:
                raise ValueError("request symbol mismatch")
            start, end = date.fromisoformat(request["start"]), date.fromisoformat(request["end"])
            limit = 14 if endpoint == "broker-summary" else 90
            if not envelope_start <= start <= end <= envelope_end or (end - start).days + 1 > limit:
                raise ValueError("request window outside approved limits")
            targets = list(map(date.fromisoformat, request.get("target_dates", [])))
            if not targets or len(set(targets)) != len(targets) or any(not start <= d <= end for d in targets):
                raise ValueError("invalid or absent target dates")
            if calendar is not None and not set(targets) <= set(calendar.sessions(start, end, sym)):
                raise ValueError("target date is not a scheduled ticker session")
            if set(request) - {"symbol", "endpoint", "start", "end", "expected_credits", "target_dates", "reason", "request_id"}:
                raise ValueError("unexpected request fields")
        elif request["endpoint"] != "/v2/brokers/" or set(request) - {"endpoint", "expected_credits", "reason", "request_id"}:
            raise ValueError("endpoint not allowed")
    if plan["estimated_credits"] != len(plan["requests"]):
        raise ValueError("credit total mismatch")
    return plan

def request_url(request):
    base = "https://api.sectors.app" + request["endpoint"]
    return base + ("?" + urlencode({"start": request["start"], "end": request["end"]}) if "start" in request else "")

def dry_run(plan):
    validate_plan(plan)
    return {"mode": "dry_run", "plan_sha256": plan["plan_sha256"], "estimated_credits": plan["estimated_credits"],
            "requests_executed": 0, "approval_required": True,
            "unresolved": [field for field in ("calendar_reviewed", "legacy_sources_reviewed", "broker_completeness_reviewed") if not plan.get(field)],
            "requests": [{"request_id": r["request_id"], "url": request_url(r), "expected_credits": 1} for r in plan["requests"]]}

def authorize(plan, approval, chosen_ids, ledger):
    validate_plan(plan)
    if plan.get("coverage_basis") != "validated_only":
        raise ApprovalRequired("candidate proposals cannot execute; promote reviewed sources and regenerate validated-only plan")
    if not all(plan.get(f) is True for f in ("calendar_reviewed", "legacy_sources_reviewed", "broker_completeness_reviewed")) or not plan.get("calendar_evidence"):
        raise ApprovalRequired("calendar, legacy sources and broker inventory review required")
    if not isinstance(plan["calendar_evidence"], dict):
        raise ApprovalRequired("hashed calendar snapshot required for execution")
    if approval.get("plan_sha256") != plan["plan_sha256"]:
        raise ApprovalRequired("approval does not match exact plan")
    for field in ("reviewer", "approved_at", "evidence"):
        if not isinstance(approval.get(field), str) or not approval[field].strip():
            raise ApprovalRequired(f"human approval evidence required: {field}")
    try:
        stamp = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ApprovalRequired("invalid approval timestamp") from error
    if stamp.tzinfo is None or stamp > now():
        raise ApprovalRequired("approval timestamp must be known and not in the future")
    maximum = approval.get("max_credits")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise ApprovalRequired("positive integer credit ceiling required")
    if not chosen_ids or len(chosen_ids) != len(set(chosen_ids)):
        raise ValueError("select unique request IDs")
    requests = {r["request_id"]: r for r in plan["requests"]}
    allowed = approval.get("request_ids")
    if not isinstance(allowed, list) or len(allowed) != len(set(allowed)) or not set(allowed) <= set(requests):
        raise ApprovalRequired("approval must name exact existing requests")
    if not set(chosen_ids) <= set(allowed):
        raise ApprovalRequired("selected requests not approved")
    if any(a["request_id"] in chosen_ids for a in ledger):
        raise ApprovalRequired("request already attempted; no automatic retry")
    if any(a["status"] in ("attempting", "unknown", "failed", "quarantined") for a in ledger):
        raise ApprovalRequired("unresolved previous attempt requires human reconciliation")
    spent = sum(a["reserved_credits"] for a in ledger)
    if spent + len(chosen_ids) > maximum:
        raise ApprovalRequired("credit ceiling would be exceeded")
    if approval.get("remaining_fetches_approved") is not True:
        if len(chosen_ids) != 1 or chosen_ids[0] != approval.get("pilot_request_id"):
            raise ApprovalRequired("Gate C requires one explicitly selected pilot request")
        if ledger:
            raise ApprovalRequired("pilot already attempted; Gate C review required")
    else:
        pilot = approval.get("pilot_request_id")
        if not approval.get("pilot_review_evidence") or not any(a["request_id"] == pilot and a["status"] == "validated" for a in ledger):
            raise ApprovalRequired("successful pilot and explicit Gate C review required")
    return [requests[r] for r in chosen_ids]

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def sectors_transport(request, api_key):
    """Single attempt, fixed HTTPS origin, no redirects or automatic retries."""
    if not api_key:
        raise ValueError("API key required")
    req = Request(request_url(request), headers={"Authorization": api_key, "Accept": "application/json"})
    try:
        with build_opener(NoRedirect).open(req, timeout=30) as response:
            return response.read()
    except HTTPError as error:
        # Preserve server error bodies too; their shapes will be quarantined.
        return error.read()

def execute(plan, approval, chosen_ids, store, *, transport):
    """Transport is injected; this function is never called by dry-run."""
    ledger_path = store.root / "attempts.json"
    with exclusive(store.root / ".fetch.lock"):
        ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []
        requests = authorize(plan, approval, chosen_ids, ledger)
        results = []
        for request in requests:
            attempt = {"request_id": request["request_id"], "request": request, "plan_sha256": plan["plan_sha256"],
                       "approval_sha256": digest(approval), "status": "attempting", "started_at": str(now()),
                       "reserved_credits": 1, "reported_credits": None}
            ledger.append(attempt)
            write_json(ledger_path, ledger)  # reserve before crossing the network boundary
            try:
                raw = transport(request)
                if not isinstance(raw, bytes):
                    raise ValueError("transport must return original response bytes")
                attempt["response_sha256"] = store.save_source(raw)  # before parse/normalization
                body = json.loads(raw)
                unwrapped = unwrap(body)
                if isinstance(unwrapped, dict) and unwrapped.get("symbol") and request.get("symbol") and symbol(unwrapped["symbol"]) != request["symbol"]:
                    raise ValueError("response symbol mismatch")
                endpoint = request["endpoint"].split("/")[2]
                table, rows = api_rows(endpoint, body, request.get("symbol"))
                manifest = store.ingest(table, rows, source_bytes=raw, source_endpoint=request["endpoint"],
                                        retrieved_at=str(now()), provenance="api", request=request)
                attempt.update(status="quarantined" if manifest["failures"] else "validated", batch_id=manifest["batch_id"], finished_at=str(now()))
                results.append(manifest)
            except Exception as error:
                # A timeout may already have consumed credit; never retry automatically.
                attempt.update(status="quarantined" if attempt.get("response_sha256") else "unknown", error_type=type(error).__name__, finished_at=str(now()))
                write_json(ledger_path, ledger)
                raise
            write_json(ledger_path, ledger)
            if attempt["status"] != "validated":
                break
        return results
