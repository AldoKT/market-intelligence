"""Explicit Arrow contracts, validation and response adapters."""
from datetime import date, datetime, timezone
import hashlib
import json
import math
import pyarrow as pa

SYMBOLS = ("ANTM", "INCO", "BBCA")
DAILY_MAP = {"open": "open", "high": "high", "low": "low", "close": "close",
             "volume": "volume_shares", "market_cap": "market_cap_idr"}
FLOW_MAP = {"net_foreign_inflow": "net_foreign_inflow_idr", "foreign_share": "foreign_share",
            "foreign_buy_idr": "foreign_buy_idr", "foreign_sell_idr": "foreign_sell_idr"}
BROKER_MAP = {"bval": "buy_value_idr", "sval": "sell_value_idr", "nval": "net_value_idr",
              "blot": "buy_lots", "slot": "sell_lots", "nlot": "net_lots",
              "bfreq": "buy_frequency", "sfreq": "sell_frequency",
              "bavg_per_share": "buy_avg_per_share", "savg_per_share": "sell_avg_per_share",
              "navg_per_share": "net_avg_per_share"}
for prefix in ("f_b", "f_s"):
    for suffix in ("val", "lot", "freq", "avg_per_share"):
        BROKER_MAP[prefix + suffix] = prefix + suffix
for field in ("d_bavg_per_share", "d_savg_per_share"):
    BROKER_MAP[field] = field

KEYS = {"daily": ("symbol", "date"), "foreign_flow": ("symbol", "date"),
        "broker_activity": ("symbol", "date", "broker_code"),
        "broker_registry": ("broker_code",), "company_snapshot": ("symbol", "snapshot_id"),
        "news": ("source", "timestamp", "title", "content_id"),
        "corporate_events": ("symbol", "event_type", "event_date", "source_id")}
META = {"source_file": pa.string(), "source_endpoint": pa.string(), "source_sha256": pa.string(),
        "imported_at": pa.timestamp("us", tz="UTC"), "retrieved_at": pa.timestamp("us", tz="UTC"),
        "retrieved_at_original": pa.string(), "validation_status": pa.string(),
        "provenance": pa.string(), "market_scope": pa.string(), "batch_id": pa.string()}
FIELDS = {
    "daily": {"symbol": pa.string(), "date": pa.date32(), **{v: (pa.int64() if k == "volume" else pa.float64()) for k, v in DAILY_MAP.items()}},
    "foreign_flow": {"symbol": pa.string(), "date": pa.date32(), **{v: pa.float64() for v in FLOW_MAP.values()}},
    "broker_activity": {"symbol": pa.string(), "date": pa.date32(), "broker_code": pa.string(),
                        **{v: (pa.int64() if k.endswith(("lot", "freq")) else pa.float64()) for k, v in BROKER_MAP.items()}},
    "broker_registry": {"broker_code": pa.string(), "name": pa.string(), "origin": pa.string(), "cohort": pa.string(), "license_type": pa.string()},
    "company_snapshot": {"symbol": pa.string(), "snapshot_id": pa.string(), "sections": pa.string(), "source_as_of": pa.string(), "attributes": pa.string()},
    "news": {"source": pa.string(), "timestamp": pa.string(), "title": pa.string(), "content_id": pa.string(), "symbols": pa.list_(pa.string()), "body": pa.string(), "tags": pa.list_(pa.string())},
    "corporate_events": {"symbol": pa.string(), "event_type": pa.string(), "event_date": pa.date32(), "source_id": pa.string(), "announced_at": pa.string(), "details": pa.string()},
}
SCHEMAS = {name: pa.schema({**fields, **META}) for name, fields in FIELDS.items()}

def now():
    return datetime.now(timezone.utc)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode()).hexdigest()

def symbol(value):
    return str(value).upper().removesuffix(".JK")

def aware_time(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None

def prepare(table, row):
    result = {field: row.get(field) for field in SCHEMAS[table].names}
    for field, dtype in FIELDS[table].items():
        value = result[field]
        if value is None:
            continue
        if pa.types.is_date32(dtype):
            result[field] = date.fromisoformat(str(value)) if not isinstance(value, date) else value
        elif pa.types.is_integer(dtype) or pa.types.is_floating(dtype):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field}: finite numeric value required")
            if pa.types.is_integer(dtype):
                if int(value) != value or not -(2**63) <= value < 2**63:
                    raise ValueError(f"{field}: exact int64 required")
                result[field] = int(value)
            else:
                result[field] = float(value)
    for key in KEYS[table]:
        if result[key] is None or result[key] == "":
            raise ValueError(f"missing key: {key}")
    for field in ("open", "high", "low", "close", "volume_shares", "market_cap_idr", "foreign_buy_idr", "foreign_sell_idr",
                  "buy_value_idr", "sell_value_idr", "buy_lots", "sell_lots", "buy_frequency", "sell_frequency",
                  "f_bval", "f_sval", "f_blot", "f_slot", "f_bfreq", "f_sfreq"):
        if result.get(field) is not None and result[field] < 0:
            raise ValueError(f"{field}: negative gross value")
    if table == "daily":
        lo, hi = result.get("low"), result.get("high")
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("low exceeds high")
        for field in ("open", "close"):
            value = result.get(field)
            if value is not None and ((lo is not None and value < lo) or (hi is not None and value > hi)):
                raise ValueError(f"{field}: outside OHLC bounds")
    if table == "foreign_flow":
        if result.get("foreign_share") is not None and not 0 <= result["foreign_share"] <= 1:
            raise ValueError("foreign_share outside [0,1]")
        identities = [("foreign_buy_idr", "foreign_sell_idr", "net_foreign_inflow_idr")]
    elif table == "broker_activity":
        identities = [("buy_value_idr", "sell_value_idr", "net_value_idr"), ("buy_lots", "sell_lots", "net_lots")]
        for foreign, total in (("f_bval", "buy_value_idr"), ("f_sval", "sell_value_idr"), ("f_blot", "buy_lots"), ("f_slot", "sell_lots"), ("f_bfreq", "buy_frequency"), ("f_sfreq", "sell_frequency")):
            if result.get(foreign) is not None and result.get(total) is not None and result[foreign] > result[total]:
                raise ValueError(f"{foreign} exceeds total")
    else:
        identities = []
    for buy, sell, net in identities:
        if all(result.get(k) is not None for k in (buy, sell, net)) and not math.isclose(result[buy] - result[sell], result[net], rel_tol=1e-9, abs_tol=0.01):
            raise ValueError(f"net identity fails: {net}")
    return result

def unwrap(body):
    return body.get("body", body) if isinstance(body, dict) else body

def api_rows(endpoint, payload, requested_symbol=None):
    """Normalize documented response shapes; absent values remain null."""
    payload = unwrap(payload)
    if endpoint == "daily":
        if not isinstance(payload, list):
            raise ValueError("daily response must be a list")
        return "daily", [{"symbol": symbol(p.get("symbol", requested_symbol)), "date": p["date"], "market_scope": p.get("market_scope"), **{v: p.get(k) for k, v in DAILY_MAP.items()}} for p in payload]
    if endpoint in ("foreign-flow", "broker-summary"):
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("response must contain data list")
        sym = symbol(payload.get("symbol", requested_symbol))
        if endpoint == "foreign-flow":
            return "foreign_flow", [{"symbol": sym, "date": p["date"], "market_scope": p.get("market_scope", payload.get("market_scope")), **{v: p.get(k) for k, v in FLOW_MAP.items()}} for p in payload["data"]]
        rows = []
        for session in payload["data"]:
            if not isinstance(session.get("summary"), list):
                raise ValueError("broker session must contain summary list")
            for p in session["summary"]:
                rows.append({"symbol": sym, "date": session["date"], "broker_code": p["broker_code"], "market_scope": p.get("market_scope", session.get("market_scope", payload.get("market_scope"))), **{v: p.get(k) for k, v in BROKER_MAP.items()}})
        return "broker_activity", rows
    if endpoint == "brokers":
        if not isinstance(payload, list):
            raise ValueError("registry response must be a list")
        return "broker_registry", [{"broker_code": p["code"], "name": p.get("name"),
            "origin": ("foreign" if p["is_foreign"] else "domestic") if isinstance(p.get("is_foreign"), bool) else None,
            "cohort": p.get("cohort"), "license_type": p.get("license_type")} for p in payload]
    raise ValueError("unsupported endpoint")
