
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


METHODOLOGY_VERSION = "1.0-candidate"
HYPOTHESIS = "Sideways Accumulation Watch"

ACTIVE_STATES = {"EMERGING", "DEVELOPING", "ESTABLISHED", "WEAKENING"}
STATE_PRIORITY = {
    "ESTABLISHED": 4,
    "DEVELOPING": 3,
    "EMERGING": 2,
    "WEAKENING": 1,
    "CLOSED": 0,
    "NO_INVESTIGATION": 0,
    "INELIGIBLE_PRICE_REGIME": -1,
}


def py(v):
    if pd.isna(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat()
    return v


def as_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() == "true"


def f(row, key):
    v = row.get(key)
    return None if pd.isna(v) else float(v)


def i(row, key):
    v = row.get(key)
    return 0 if pd.isna(v) else int(v)


def s(row, key):
    v = row.get(key)
    return None if pd.isna(v) else str(v)


def load_inputs(args):
    timeline = pd.read_csv(args.timeline)
    episodes = pd.read_csv(args.episodes)
    market = pd.read_csv(args.market_context)
    methodology = json.loads(Path(args.methodology).read_text(encoding="utf-8"))

    timeline["date"] = pd.to_datetime(timeline["date"])
    for c in [
        "compression_valid",
        "compression_gate_pass",
        "activity_gate_pass",
        "core_activity_gate_pass",
        "spot_hit",
        "context_applicable",
        "supporting_session_v2",
        "investigation_active_v2",
    ]:
        if c in timeline.columns:
            timeline[c] = timeline[c].map(as_bool)

    for c in ["opened_at", "closed_at", "last_linked_at"]:
        if c in episodes.columns:
            episodes[c] = pd.to_datetime(episodes[c], errors="coerce")

    market["date"] = pd.to_datetime(market["date"])

    return timeline, episodes, market, methodology


def resolve_as_of(timeline, requested):
    max_date = timeline["date"].max()
    if requested:
        dt = pd.Timestamp(requested)
        if dt > max_date:
            dt = max_date
    else:
        dt = max_date
    return dt


def actual_activity_lookup(rawdir: Optional[str], symbol: str):
    if not rawdir:
        return None

    candidates = [
        Path(rawdir) / symbol / "analysis_frame_v0_2.csv",
        Path(rawdir) / symbol / "analysis_frame.csv",
    ]

    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            return df

    return None


def identity(row):
    return {
        "symbol": str(row["symbol"]),
        "company_name": None,
        "peer_group": s(row, "peer_group"),
    }


def gate_status(row):
    return {
        "compression_pass": bool(row.get("compression_gate_pass", False)),
        "activity_pass": bool(row.get("activity_gate_pass", False)),
        "core_activity_pass": bool(row.get("core_activity_gate_pass", False)),
        "spot_hit": bool(row.get("spot_hit", False)),
    }


def market_metrics(row):
    return {
        "close": f(row, "close"),
        "compression_score": f(row, "compression_score"),
        "current_5d_range_pct": f(row, "current_5d_range_pct"),
        "baseline_5d_range_pct": f(row, "baseline_5d_range_pct"),
        "compression_ratio": f(row, "compression_ratio"),
        "activity_score": f(row, "activity_score"),
        "relative_turnover": f(row, "relative_turnover"),
        "relative_volume": f(row, "relative_volume"),
        "relative_transaction_count": f(row, "relative_transaction_count"),
        "relative_avg_trade_value": f(row, "relative_avg_trade_value"),
        "relative_top5_net_buy_share": f(row, "relative_top5_net_buy_share"),
        "foreign_net_to_turnover": f(row, "foreign_net_to_turnover"),
    }


def context_snapshot(row):
    scope = s(row, "context_scope") or "NO_CONTEXT"
    score = f(row, "context_specificity_score")
    market_breadth = f(row, "market_activity_breadth")
    peer_breadth = f(row, "peer_activity_breadth")
    market_pct = f(row, "market_activity_percentile")
    peer_pct = f(row, "peer_activity_percentile")

    if scope == "STOCK_SPECIFIC_ACTIVITY":
        interpretation = (
            "Activity is relatively unusual for this ticker versus the same-day "
            "market and, where available, its research peer group."
        )
    elif scope == "MARKET_WIDE_ACTIVITY":
        interpretation = (
            "Unusual activity is broad across the same-day universe, so the "
            "ticker-level anomaly is less specific."
        )
    elif scope == "PEER_CLUSTERED_ACTIVITY":
        interpretation = (
            "Activity is shared by multiple names in the research peer group."
        )
    elif scope == "MIXED_CONTEXT":
        interpretation = (
            "The anomaly contains both ticker-specific and broader market/peer components."
        )
    elif scope == "NO_ACTIVITY_CONTEXT":
        interpretation = (
            "No meaningful activity anomaly is present, so Context Specificity is not shown."
        )
    elif scope == "INELIGIBLE":
        interpretation = "The price regime is ineligible for contextual scoring."
    else:
        interpretation = "Context evidence is unavailable or not applicable."

    return {
        "scope": scope,
        "specificity_score": score,
        "market_activity_breadth": market_breadth,
        "market_activity_percentile": market_pct,
        "peer_activity_breadth": peer_breadth,
        "peer_activity_percentile": peer_pct,
        "peer_count": i(row, "peer_count"),
        "peer_context_quality": s(row, "peer_context_quality"),
        "interpretation": interpretation,
    }


def evidence(row):
    supporting = []
    contradicting = []

    def add(target, eid, direction, label, metric, value=None, baseline=None,
            relative=None, score=None, note=""):
        target.append({
            "evidence_id": eid,
            "direction": direction,
            "label": label,
            "metric": metric,
            "value": value,
            "baseline": baseline,
            "relative": relative,
            "score": score,
            "note": note,
        })

    comp = f(row, "compression_score")
    if bool(row.get("compression_gate_pass", False)):
        add(
            supporting, "price_compression", "SUPPORTING",
            "Price Compression", "compression_score",
            score=comp,
            value=f(row, "current_5d_range_pct"),
            baseline=f(row, "baseline_5d_range_pct"),
            relative=f(row, "compression_ratio"),
            note="The hard Spot compression gate is satisfied.",
        )
    elif bool(row.get("supporting_session_v2", False)) and comp is not None and comp >= 40:
        add(
            supporting, "price_compression_soft", "SUPPORTING",
            "Residual Price Compression", "compression_score",
            score=comp,
            value=f(row, "current_5d_range_pct"),
            baseline=f(row, "baseline_5d_range_pct"),
            relative=f(row, "compression_ratio"),
            note="Compression remains sufficient for lifecycle support but not necessarily for a new hard Spot.",
        )
    else:
        add(
            contradicting, "price_compression", "CONTRADICTING",
            "Price Compression", "compression_score",
            score=comp,
            value=f(row, "current_5d_range_pct"),
            baseline=f(row, "baseline_5d_range_pct"),
            relative=f(row, "compression_ratio"),
            note="Compression does not currently support a new hard Spot.",
        )

    act = f(row, "activity_score")
    if bool(row.get("activity_gate_pass", False)):
        add(
            supporting, "activity_anomaly", "SUPPORTING",
            "Activity Anomaly", "activity_score",
            score=act,
            note="The hard Spot activity gate is satisfied.",
        )
    elif act is not None and act >= 25:
        add(
            supporting, "activity_anomaly_soft", "SUPPORTING",
            "Residual Activity", "activity_score",
            score=act,
            note="Activity remains sufficient for lifecycle support but below the hard Spot threshold.",
        )
    else:
        add(
            contradicting, "activity_anomaly", "CONTRADICTING",
            "Activity Anomaly", "activity_score",
            score=act,
            note="Activity is below the current continuation threshold.",
        )

    for key, label in [
        ("relative_turnover", "Relative Turnover"),
        ("relative_volume", "Relative Volume"),
        ("relative_transaction_count", "Relative Transaction Count"),
        ("relative_avg_trade_value", "Relative Avg Trade Value"),
    ]:
        val = f(row, key)
        if val is None:
            continue
        target = supporting if val >= 1.20 else contradicting
        direction = "SUPPORTING" if val >= 1.20 else "CONTRADICTING"
        add(
            target,
            key,
            direction,
            label,
            key,
            relative=val,
            note=(
                "At or above 1.20x the stock's recent baseline."
                if val >= 1.20
                else "Below 1.20x the stock's recent baseline."
            ),
        )

    foreign = f(row, "foreign_net_to_turnover")
    if foreign is not None:
        if foreign > 0:
            add(
                supporting, "foreign_flow", "SUPPORTING",
                "Foreign Flow", "foreign_net_to_turnover",
                relative=foreign,
                note="Foreign net flow is positive, used only as supporting context.",
            )
        elif foreign < 0:
            add(
                contradicting, "foreign_flow", "CONTRADICTING",
                "Foreign Flow", "foreign_net_to_turnover",
                relative=foreign,
                note="Foreign net flow is negative; this is context, not a hard detector gate.",
            )

    return supporting, contradicting


def narrative(row, state):
    opened = s(row, "investigation_opened_at")
    peer = s(row, "peer_group") or "unmapped peer group"
    context = s(row, "context_scope") or "NO_CONTEXT"
    hard_hits = i(row, "hard_hits_total_in_episode")
    support = i(row, "support_sessions_total_in_episode")

    if state in ACTIVE_STATES:
        what = f"{HYPOTHESIS} is active in state {state}."
        why = (
            f"The investigation has accumulated {hard_hits} hard Spot hit(s) and "
            f"{support} supporting session(s) in the current episode."
        )
    elif state == "CLOSED":
        what = f"{HYPOTHESIS} has closed."
        why = "The lifecycle close rule was reached after evidence stopped persisting."
    elif state == "INELIGIBLE_PRICE_REGIME":
        what = "No investigation is evaluated because the current price regime is ineligible."
        why = "The compression baseline cannot be interpreted reliably in this price regime."
    else:
        what = "No active Sideways Accumulation Watch investigation."
        why = "The current session does not satisfy the hard Spot opening gate."

    return {
        "what": what,
        "why": why,
        "when": f"Observation as of {row['date'].date().isoformat()}"
                + (f"; episode opened {opened}." if opened else "."),
        "where": f"Research peer group: {peer}; context scope: {context}.",
        "who": (
            "Participant identity is not inferred. Broker/flow statistics describe "
            "participation structure only."
        ),
        "how": (
            "SIGNAL combines price compression, abnormal trading activity, lifecycle "
            "persistence, participation structure, foreign-flow context, and same-day "
            "market/peer context."
        ),
    }


def look_ahead(row, state):
    comp = f(row, "compression_score")
    act = f(row, "activity_score")
    core = i(row, "core_metrics_above_1_20x")
    support5 = i(row, "support_sessions_in_last_5")
    hard_total = i(row, "hard_hits_total_in_episode")
    unsupported = i(row, "unsupported_streak")

    items = []

    def item(cid, label, status, note):
        items.append({
            "condition_id": cid,
            "label": label,
            "current_status": status,
            "note": note,
        })

    if state in ACTIVE_STATES:
        item(
            "continuation_compression",
            "Compression remains >= 40",
            "MET" if comp is not None and comp >= 40 else "NOT_MET",
            f"Current compression score: {comp}.",
        )
        item(
            "continuation_activity",
            "Activity >= 25 or at least one core metric >= 1.20x",
            "MET" if ((act is not None and act >= 25) or core >= 1) else "NOT_MET",
            f"Activity score: {act}; core metrics >=1.20x: {core}.",
        )
        item(
            "established_support",
            "At least 4 of last 5 sessions support the hypothesis",
            "MET" if support5 >= 4 else "NOT_MET",
            f"Current supporting sessions in last 5: {support5}.",
        )
        item(
            "established_hard_hits",
            "At least 2 hard Spot hits in the episode",
            "MET" if hard_total >= 2 else "NOT_MET",
            f"Current hard hits in episode: {hard_total}.",
        )
        item(
            "closure_watch",
            "Avoid 2 consecutive unsupported sessions",
            "NOT_MET" if unsupported >= 2 else "MET",
            f"Current unsupported streak: {unsupported}.",
        )
    else:
        item(
            "new_spot_compression",
            "Compression Score >= 55",
            "MET" if comp is not None and comp >= 55 else "NOT_MET",
            f"Current compression score: {comp}.",
        )
        item(
            "new_spot_activity",
            "Activity Score >= 50",
            "MET" if act is not None and act >= 50 else "NOT_MET",
            f"Current activity score: {act}.",
        )
        item(
            "new_spot_core",
            "At least 2 core activity metrics >= 1.20x",
            "MET" if core >= 2 else "NOT_MET",
            f"Current core-metric count: {core}.",
        )

    return items


def build_investigation(row):
    state = s(row, "lifecycle_state_v2") or "NO_INVESTIGATION"
    active = bool(row.get("investigation_active_v2", False))
    supporting, contradicting = evidence(row)

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": row["date"].date().isoformat(),
        "investigation_id": s(row, "investigation_id"),
        "identity": identity(row),
        "hypothesis": HYPOTHESIS,
        "state": state,
        "active": active,
        "opened_at": s(row, "investigation_opened_at"),
        "age_sessions": i(row, "investigation_age_sessions"),
        "gates": gate_status(row),
        "confidence": {
            "evidence_confidence": f(row, "evidence_confidence_v3") if active else None,
            "diagnostic_evidence_score": f(row, "diagnostic_evidence_score_v3"),
            "interpretation": (
                "Evidence Confidence is displayed only while an investigation is active. "
                "It is not the probability that price will rise."
            ),
        },
        "persistence": {
            "support_sessions_in_last_5": i(row, "support_sessions_in_last_5"),
            "hard_hits_in_last_5": i(row, "hard_hits_in_last_5"),
            "hard_hits_total_in_episode": i(row, "hard_hits_total_in_episode"),
            "support_sessions_total_in_episode": i(row, "support_sessions_total_in_episode"),
            "unsupported_streak": i(row, "unsupported_streak"),
            "persistence_score": f(row, "persistence_score_v2") or 0.0,
        },
        "metrics": market_metrics(row),
        "context": context_snapshot(row),
        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting,
        "narrative_5w1h": narrative(row, state),
        "look_ahead": look_ahead(row, state),
        "guardrails": [
            "This object describes an investigation, not a buy/sell recommendation.",
            "Evidence Confidence is not a future-return probability.",
            "Participant identity is not inferred from broker or trade-size statistics.",
            "Context peer groups are research groupings, not authoritative exchange classifications.",
        ],
    }


def investigation_list_item(row):
    state = s(row, "lifecycle_state_v2") or "NO_INVESTIGATION"
    return {
        "symbol": str(row["symbol"]),
        "peer_group": s(row, "peer_group"),
        "state": state,
        "active": bool(row.get("investigation_active_v2", False)),
        "evidence_confidence": (
            f(row, "evidence_confidence_v3")
            if bool(row.get("investigation_active_v2", False))
            else None
        ),
        "context_scope": s(row, "context_scope"),
        "context_specificity_score": f(row, "context_specificity_score"),
        "relative_turnover": f(row, "relative_turnover"),
        "current_5d_range_pct": f(row, "current_5d_range_pct"),
        "persistence_hits": i(row, "support_sessions_in_last_5"),
        "persistence_window": 5,
        "opened_at": s(row, "investigation_opened_at"),
        "last_updated": row["date"].date().isoformat(),
    }


def activity_payload(symbol_rows, current_row, rawdir=None):
    actual = actual_activity_lookup(rawdir, str(current_row["symbol"]))
    actual_by_date = {}
    if actual is not None:
        for _, r in actual.iterrows():
            actual_by_date[r["date"].date().isoformat()] = r

    series = []
    start = max(0, len(symbol_rows) - 60)

    for _, row in symbol_rows.iloc[start:].iterrows():
        date_str = row["date"].date().isoformat()
        raw = actual_by_date.get(date_str)

        series.append({
            "date": date_str,
            "close": f(row, "close"),
            "volume": (f(raw, "volume") if raw is not None else None),
            "transaction_count": (f(raw, "transaction_count") if raw is not None else None),
            "turnover_idr": (f(raw, "turnover_idr") if raw is not None else None),
            "avg_trade_value_idr": (f(raw, "avg_trade_value_idr") if raw is not None else None),
            "relative_volume": f(row, "relative_volume"),
            "relative_transaction_count": f(row, "relative_transaction_count"),
            "relative_turnover": f(row, "relative_turnover"),
            "relative_avg_trade_value": f(row, "relative_avg_trade_value"),
            "compression_score": f(row, "compression_score"),
            "activity_score": f(row, "activity_score"),
            "spot_hit": bool(row.get("spot_hit", False)),
            "lifecycle_state": s(row, "lifecycle_state_v2") or "NO_INVESTIGATION",
        })

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": current_row["date"].date().isoformat(),
        "identity": identity(current_row),
        "data_availability": {
            "actual_volume": actual is not None,
            "actual_transaction_count": actual is not None,
            "actual_turnover": actual is not None,
            "actual_avg_trade_value": actual is not None,
            "relative_metrics": True,
        },
        "current": market_metrics(current_row),
        "series": series,
        "guardrail": (
            "Market Activity visualizes trading evidence only. It should not repeat "
            "investigation narrative or imply a price forecast."
        ),
    }


def context_payload(row, market):
    market_row = market[market["date"] == row["date"]]
    daily_market = {}
    if len(market_row):
        mr = market_row.iloc[-1]
        daily_market = {k: py(v) for k, v in mr.to_dict().items() if k != "date"}
        daily_market["date"] = row["date"].date().isoformat()

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": row["date"].date().isoformat(),
        "identity": identity(row),
        "current": context_snapshot(row),
        "daily_market": daily_market,
        "notes": [
            "Context Specificity is descriptive evidence and does not change the hard Spot gate.",
            "A market-wide label means the same-day anomaly is less ticker-specific, not that it is false.",
            "No causal claim is made from market/peer co-movement alone.",
        ],
    }


def history_payload(symbol_rows, current_row):
    """
    Build History strictly from the point-in-time timeline slice.

    IMPORTANT:
    Do not use the full investigation_episodes table here for historical
    snapshots, because that table contains episode outcomes after `as_of`.
    Deriving episode summaries from `symbol_rows` guarantees that every field
    is observable on or before the requested snapshot date.
    """
    events = []
    prev_state = None

    for _, row in symbol_rows.iterrows():
        state = s(row, "lifecycle_state_v2") or "NO_INVESTIGATION"
        inv = s(row, "investigation_id")
        date = row["date"].date().isoformat()

        if bool(row.get("spot_hit", False)):
            events.append({
                "date": date,
                "event_type": "SPOT_HIT",
                "state": state,
                "investigation_id": inv,
                "note": "Hard Spot gate satisfied.",
            })

        if state != prev_state:
            events.append({
                "date": date,
                "event_type": (
                    "INVESTIGATION_OPENED"
                    if state == "EMERGING"
                    else "INVESTIGATION_CLOSED"
                    if state == "CLOSED"
                    else "STATE_CHANGE"
                ),
                "state": state,
                "investigation_id": inv,
                "note": f"Lifecycle state changed to {state}.",
            })
        prev_state = state

    eps = []
    linked = symbol_rows[symbol_rows["investigation_id"].notna()].copy()

    for investigation_id, g in linked.groupby("investigation_id", sort=False):
        g = g.sort_values("date")

        active_rows = g[g["lifecycle_state_v2"].isin(ACTIVE_STATES)]
        close_rows = g[g["lifecycle_state_v2"] == "CLOSED"]

        if len(active_rows) == 0:
            continue

        if (active_rows["lifecycle_state_v2"] == "ESTABLISHED").any():
            peak_state = "ESTABLISHED"
        elif (active_rows["lifecycle_state_v2"] == "DEVELOPING").any():
            peak_state = "DEVELOPING"
        else:
            peak_state = "EMERGING"

        open_row = active_rows.iloc[0]

        eps.append({
            "investigation_id": str(investigation_id),
            "opened_at": active_rows["date"].iloc[0].date().isoformat(),
            "last_linked_at": g["date"].iloc[-1].date().isoformat(),
            "closed": bool(len(close_rows) > 0),
            "closed_at": (
                close_rows["date"].iloc[-1].date().isoformat()
                if len(close_rows) > 0
                else None
            ),
            "close_reason": (
                str(close_rows["close_reason"].iloc[-1])
                if len(close_rows) > 0
                and pd.notna(close_rows["close_reason"].iloc[-1])
                else None
            ),
            "active_sessions": int(len(active_rows)),
            "hard_hits": int(g["spot_hit"].sum()),
            "support_sessions": int(g["supporting_session_v2"].sum()),
            "peak_state": peak_state,
            "open_context_scope": (
                None
                if pd.isna(open_row.get("context_scope"))
                else str(open_row.get("context_scope"))
            ),
            "max_evidence_confidence": (
                float(active_rows["evidence_confidence_v3"].max())
                if active_rows["evidence_confidence_v3"].notna().any()
                else None
            ),
        })

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": current_row["date"].date().isoformat(),
        "identity": identity(current_row),
        "events": events,
        "episodes": eps,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--timeline", required=True)
    p.add_argument("--episodes", required=True)
    p.add_argument("--market-context", required=True)
    p.add_argument("--methodology", required=True)
    p.add_argument("--as-of")
    p.add_argument("--rawdir")
    p.add_argument("--outdir", default="signal_product_payloads_v1")
    args = p.parse_args()

    timeline, episodes, market, methodology = load_inputs(args)
    as_of = resolve_as_of(timeline, args.as_of)

    snap = timeline[timeline["date"] <= as_of].copy()
    if len(snap) == 0:
        raise ValueError("No timeline rows exist on or before the requested as-of date.")

    as_of_actual = snap["date"].max()
    current_rows = (
        snap[snap["date"] == as_of_actual]
        .sort_values("symbol")
        .reset_index(drop=True)
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ticker_root = outdir / "tickers"
    ticker_root.mkdir(exist_ok=True)

    items = [investigation_list_item(r) for _, r in current_rows.iterrows()]
    active_items = [x for x in items if x["active"]]

    active_items.sort(
        key=lambda x: (
            STATE_PRIORITY.get(x["state"], 0),
            x["evidence_confidence"] if x["evidence_confidence"] is not None else -1,
        ),
        reverse=True,
    )

    spotlight = active_items[0] if active_items else None

    recent_changes = []
    for _, row in current_rows.iterrows():
        state = s(row, "lifecycle_state_v2")
        if state in {"EMERGING", "DEVELOPING", "ESTABLISHED", "WEAKENING", "CLOSED"}:
            recent_changes.append({
                "symbol": str(row["symbol"]),
                "state": state,
                "investigation_id": s(row, "investigation_id"),
                "date": as_of_actual.date().isoformat(),
            })

    overview = {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": as_of_actual.date().isoformat(),
        "headline": (
            f"{len(active_items)} active investigation"
            + ("" if len(active_items) == 1 else "s")
            + " detected after market close"
        ),
        "kpis": {
            "active_investigations": len(active_items),
            "established": sum(x["state"] == "ESTABLISHED" for x in active_items),
            "developing": sum(x["state"] == "DEVELOPING" for x in active_items),
            "emerging": sum(x["state"] == "EMERGING" for x in active_items),
            "weakening": sum(x["state"] == "WEAKENING" for x in active_items),
        },
        "spotlight": spotlight,
        "active_investigations": active_items,
        "recent_changes": recent_changes,
    }

    explorer = {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": as_of_actual.date().isoformat(),
        "items": sorted(
            items,
            key=lambda x: (
                x["active"],
                STATE_PRIORITY.get(x["state"], 0),
                x["evidence_confidence"] if x["evidence_confidence"] is not None else -1,
            ),
            reverse=True,
        ),
        "filters": {
            "state": sorted({x["state"] for x in items}),
            "peer_group": sorted({x["peer_group"] for x in items if x["peer_group"]}),
            "context_scope": sorted({x["context_scope"] for x in items if x["context_scope"]}),
        },
    }

    (outdir / "overview.json").write_text(json.dumps(overview, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "investigations.json").write_text(json.dumps(explorer, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "methodology.json").write_text(json.dumps(methodology, indent=2, ensure_ascii=False), encoding="utf-8")

    # Per-ticker pages.
    for _, current in current_rows.iterrows():
        symbol = str(current["symbol"])
        symbol_dir = ticker_root / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)

        symbol_rows = snap[snap["symbol"] == symbol].copy().sort_values("date")
        investigation_obj = build_investigation(current)
        summary = {
            "methodology_version": METHODOLOGY_VERSION,
            "as_of": as_of_actual.date().isoformat(),
            "investigation": investigation_obj,
        }

        activity = activity_payload(symbol_rows, current, args.rawdir)
        context = context_payload(current, market)
        history = history_payload(symbol_rows, current)

        for filename, obj in [
            ("investigation.json", investigation_obj),
            ("summary.json", summary),
            ("activity.json", activity),
            ("context.json", context),
            ("history.json", history),
        ]:
            (symbol_dir / filename).write_text(
                json.dumps(obj, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    manifest = {
        "methodology_version": METHODOLOGY_VERSION,
        "as_of": as_of_actual.date().isoformat(),
        "symbols": sorted(current_rows["symbol"].astype(str).tolist()),
        "files": {
            "overview": "overview.json",
            "investigations": "investigations.json",
            "methodology": "methodology.json",
            "ticker_template": "tickers/{SYMBOL}/{investigation,summary,activity,context,history}.json",
        },
        "raw_market_activity_enrichment": bool(args.rawdir),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({
        "as_of": as_of_actual.date().isoformat(),
        "symbols": len(current_rows),
        "active_investigations": len(active_items),
        "spotlight": spotlight["symbol"] if spotlight else None,
        "outdir": str(outdir),
    }, indent=2))


if __name__ == "__main__":
    main()
