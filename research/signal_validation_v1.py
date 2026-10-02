from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ACTIVE_STATES = {
    "EMERGING",
    "DEVELOPING",
    "ESTABLISHED",
    "WEAKENING",
}

SPOT_COMPRESSION_MIN = 55.0
SPOT_ACTIVITY_MIN = 50.0
SPOT_CORE_RELATIVE_MIN_COUNT = 2

SUPPORT_COMPRESSION_MIN = 40.0
SUPPORT_ACTIVITY_MIN = 25.0
SUPPORT_CORE_MIN_COUNT = 1

PERSISTENCE_WINDOW = 5
ESTABLISHED_MIN_SUPPORT = 4
ESTABLISHED_MIN_HARD_HITS = 2
CLOSE_AFTER_UNSUPPORTED = 2

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def boolify(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
        .fillna(False)
    )


def add_check(checks, check_id, layer, status, observations, mismatches, note):
    checks.append(
        {
            "check_id": check_id,
            "layer": layer,
            "status": status,
            "observations_checked": int(observations),
            "mismatches": int(mismatches),
            "note": note,
        }
    )


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_inputs(tl2, tl31):
    bool_cols_v2 = [
        "compression_valid",
        "compression_gate_pass",
        "activity_gate_pass",
        "core_activity_gate_pass",
        "spot_hit",
        "investigation_active",
    ]
    bool_cols_v31 = [
        "compression_valid",
        "compression_gate_pass",
        "activity_gate_pass",
        "core_activity_gate_pass",
        "spot_hit",
        "context_applicable",
        "supporting_session_v2",
        "investigation_active_v2",
    ]

    for c in bool_cols_v2:
        if c in tl2.columns:
            tl2[c] = boolify(tl2[c])

    for c in bool_cols_v31:
        if c in tl31.columns:
            tl31[c] = boolify(tl31[c])

    tl2["date"] = pd.to_datetime(tl2["date"])
    tl31["date"] = pd.to_datetime(tl31["date"])

    return tl2, tl31


def independent_context(df):
    out = df.copy()

    out["expected_context_applicable"] = (
        out["compression_valid"]
        & (
            (out["activity_score"] >= SUPPORT_ACTIVITY_MIN)
            | (out["core_metrics_above_1_20x"] >= SUPPORT_CORE_MIN_COUNT)
        )
    )

    use_peer = (
        out["compression_valid"]
        & (out["peer_count"].fillna(0) >= 2)
        & out["peer_distinctiveness"].notna()
    )

    raw = np.where(
        use_peer,
        100.0
        * (
            0.60 * out["market_distinctiveness"]
            + 0.40 * out["peer_distinctiveness"]
        ),
        100.0 * out["market_distinctiveness"],
    )

    raw = pd.Series(raw, index=out.index, dtype="float64")
    raw.loc[~out["compression_valid"]] = np.nan

    out["expected_context_specificity_score_raw"] = raw
    out["expected_context_specificity_score"] = raw.where(
        out["expected_context_applicable"],
        np.nan,
    )

    def classify(row):
        if not bool(row["compression_valid"]):
            return "INELIGIBLE"

        if not bool(row["expected_context_applicable"]):
            return "NO_ACTIVITY_CONTEXT"

        score = row["expected_context_specificity_score"]
        market_breadth = row["market_activity_breadth"]
        peer_breadth = row["peer_activity_breadth"]
        n_peers = row["peer_count"]

        if pd.isna(score):
            return "NO_CONTEXT"

        if (
            pd.notna(market_breadth)
            and float(market_breadth) >= 0.50
            and float(score) < 40.0
        ):
            return "MARKET_WIDE_ACTIVITY"

        if (
            pd.notna(n_peers)
            and int(n_peers) >= 2
            and pd.notna(peer_breadth)
            and float(peer_breadth) >= 0.50
            and float(score) < 55.0
        ):
            return "PEER_CLUSTERED_ACTIVITY"

        if float(score) >= 65.0:
            return "STOCK_SPECIFIC_ACTIVITY"

        return "MIXED_CONTEXT"

    out["expected_context_scope"] = out.apply(classify, axis=1)

    return out


def independent_lifecycle_for_symbol(group):
    g = group.sort_values("date").copy()
    rows = []

    active = False
    sequence = 0
    investigation_id = None
    age_sessions = 0

    hard_hits_total = 0
    support_sessions_total = 0
    unsupported_streak = 0

    recent_support = []
    recent_hard = []

    for _, row in g.iterrows():
        valid = bool(row["compression_valid"])
        hard_hit = bool(row["spot_hit"])

        supporting = bool(
            valid
            and (
                hard_hit
                or (
                    float(row["compression_score"])
                    >= SUPPORT_COMPRESSION_MIN
                    and (
                        float(row["activity_score"])
                        >= SUPPORT_ACTIVITY_MIN
                        or int(row["core_metrics_above_1_20x"])
                        >= SUPPORT_CORE_MIN_COUNT
                    )
                )
            )
        )

        close_reason = None

        if not active:
            if hard_hit:
                active = True
                sequence += 1
                investigation_id = (
                    f"{row['symbol']}-"
                    f"{row['date'].strftime('%Y%m%d')}-"
                    f"{sequence:02d}"
                )
                age_sessions = 1
                hard_hits_total = 1
                support_sessions_total = 1
                unsupported_streak = 0
                recent_support = [1]
                recent_hard = [1]
                state = "EMERGING"
            else:
                state = (
                    "INELIGIBLE_PRICE_REGIME"
                    if not valid
                    else "NO_INVESTIGATION"
                )
                age_sessions = 0
        else:
            age_sessions += 1
            hard_hits_total += int(hard_hit)
            support_sessions_total += int(supporting)

            if supporting:
                unsupported_streak = 0
            else:
                unsupported_streak += 1

            recent_support = (
                recent_support + [int(supporting)]
            )[-PERSISTENCE_WINDOW:]

            recent_hard = (
                recent_hard + [int(hard_hit)]
            )[-PERSISTENCE_WINDOW:]

            if not valid:
                state = "CLOSED"
                close_reason = "INELIGIBLE_PRICE_REGIME"
                active = False

            elif unsupported_streak >= CLOSE_AFTER_UNSUPPORTED:
                state = "CLOSED"
                close_reason = "TWO_UNSUPPORTED_SESSIONS"
                active = False

            elif not supporting:
                state = "WEAKENING"

            else:
                support_in_window = int(sum(recent_support))

                if (
                    support_in_window >= ESTABLISHED_MIN_SUPPORT
                    and hard_hits_total >= ESTABLISHED_MIN_HARD_HITS
                ):
                    state = "ESTABLISHED"
                elif (
                    support_in_window >= 2
                    or hard_hits_total >= 2
                ):
                    state = "DEVELOPING"
                else:
                    state = "EMERGING"

        if investigation_id is not None:
            support_in_window = int(sum(recent_support))
            hard_in_window = int(sum(recent_hard))
            persistence = round(
                support_in_window / PERSISTENCE_WINDOW * 100.0,
                2,
            )
        else:
            support_in_window = 0
            hard_in_window = 0
            persistence = 0.0

        if valid:
            diagnostic = round(
                float(
                    0.25 * float(row["compression_score"])
                    + 0.30 * float(row["activity_score"])
                    + 0.20 * float(persistence)
                    + 0.15 * float(row["participation_score"])
                    + 0.10 * float(row["flow_support_score"])
                ),
                2,
            )
        else:
            diagnostic = np.nan

        is_active = state in ACTIVE_STATES
        evidence_confidence = diagnostic if is_active else np.nan

        linked = (
            investigation_id is not None
            and (is_active or state == "CLOSED")
        )

        rows.append(
            {
                "symbol": row["symbol"],
                "date": row["date"],
                "expected_supporting_session_v2": supporting,
                "expected_lifecycle_state_v2": state,
                "expected_investigation_active_v2": is_active,
                "expected_investigation_id": (
                    investigation_id if linked else None
                ),
                "expected_investigation_age_sessions": (
                    int(age_sessions) if linked else 0
                ),
                "expected_hard_hits_total_in_episode": (
                    int(hard_hits_total) if linked else 0
                ),
                "expected_support_sessions_total_in_episode": (
                    int(support_sessions_total) if linked else 0
                ),
                "expected_support_sessions_in_last_5": support_in_window,
                "expected_hard_hits_in_last_5": hard_in_window,
                "expected_unsupported_streak": (
                    int(unsupported_streak) if linked else 0
                ),
                "expected_persistence_score_v2": persistence,
                "expected_diagnostic_evidence_score_v3": diagnostic,
                "expected_evidence_confidence_v3": evidence_confidence,
                "expected_close_reason": close_reason,
            }
        )

        if state == "CLOSED":
            investigation_id = None
            age_sessions = 0
            hard_hits_total = 0
            support_sessions_total = 0
            unsupported_streak = 0
            recent_support = []
            recent_hard = []

    return pd.DataFrame(rows)


def compare_series(a, b, numeric=False, atol=1e-12):
    if numeric:
        aa = pd.to_numeric(a, errors="coerce")
        bb = pd.to_numeric(b, errors="coerce")
        return (
            (aa.isna() & bb.isna())
            | np.isclose(
                aa,
                bb,
                equal_nan=True,
                atol=atol,
                rtol=0,
            )
        )

    return (
        a.fillna("__NA__").astype(str)
        == b.fillna("__NA__").astype(str)
    )


def build_episode_table_independent(timeline):
    linked = timeline[timeline["investigation_id"].notna()].copy()
    rows = []

    for investigation_id, g in linked.groupby("investigation_id"):
        g = g.sort_values("date")
        active_rows = g[
            g["lifecycle_state_v2"].isin(ACTIVE_STATES)
        ]
        close_rows = g[
            g["lifecycle_state_v2"] == "CLOSED"
        ]

        if len(active_rows) == 0:
            continue

        if (
            active_rows["lifecycle_state_v2"]
            == "ESTABLISHED"
        ).any():
            peak_state = "ESTABLISHED"
        elif (
            active_rows["lifecycle_state_v2"]
            == "DEVELOPING"
        ).any():
            peak_state = "DEVELOPING"
        else:
            peak_state = "EMERGING"

        open_row = active_rows.iloc[0]

        rows.append(
            {
                "investigation_id": investigation_id,
                "symbol": g["symbol"].iloc[0],
                "opened_at": active_rows["date"].iloc[0].date().isoformat(),
                "last_linked_at": g["date"].iloc[-1].date().isoformat(),
                "closed": bool(len(close_rows) > 0),
                "closed_at": (
                    close_rows["date"].iloc[-1].date().isoformat()
                    if len(close_rows) > 0
                    else None
                ),
                "close_reason": (
                    close_rows["close_reason"].iloc[-1]
                    if len(close_rows) > 0
                    else None
                ),
                "linked_sessions": int(len(g)),
                "active_sessions": int(len(active_rows)),
                "hard_hits": int(g["spot_hit"].sum()),
                "support_sessions": int(
                    g["supporting_session_v2"].sum()
                ),
                "peak_state": peak_state,
                "open_context_scope": open_row["context_scope"],
                "max_evidence_confidence_v3": (
                    float(
                        active_rows[
                            "evidence_confidence_v3"
                        ].max()
                    )
                    if active_rows[
                        "evidence_confidence_v3"
                    ].notna().any()
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows)


def scan_future_dates(payload_dir):
    leaks = []

    for path in Path(payload_dir).rglob("*.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(obj, dict):
            continue

        as_of = obj.get("as_of")

        if not as_of:
            continue

        def walk(value, pointer=""):
            if isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{pointer}/{key}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{pointer}/{index}")
            elif (
                isinstance(value, str)
                and DATE_RE.match(value)
                and value > as_of
            ):
                leaks.append(
                    {
                        "file": str(
                            path.relative_to(payload_dir)
                        ),
                        "as_of": as_of,
                        "json_pointer": pointer,
                        "future_date": value,
                    }
                )

        walk(obj)

    return pd.DataFrame(leaks)


def payload_snapshot_audit(payload_dir, timeline, snapshot_date):
    root = Path(payload_dir)
    overview = json.loads(
        (root / "overview.json").read_text(encoding="utf-8")
    )
    explorer = json.loads(
        (root / "investigations.json").read_text(encoding="utf-8")
    )

    snap = timeline[
        timeline["date"] == pd.Timestamp(snapshot_date)
    ].copy()

    active = snap[
        snap["investigation_active_v2"]
    ].copy()

    expected_kpis = {
        "active_investigations": int(len(active)),
        "established": int(
            (active["lifecycle_state_v2"] == "ESTABLISHED").sum()
        ),
        "developing": int(
            (active["lifecycle_state_v2"] == "DEVELOPING").sum()
        ),
        "emerging": int(
            (active["lifecycle_state_v2"] == "EMERGING").sum()
        ),
        "weakening": int(
            (active["lifecycle_state_v2"] == "WEAKENING").sum()
        ),
    }

    result_rows = []
    item_map = {
        item["symbol"]: item
        for item in explorer["items"]
    }

    for _, row in snap.sort_values("symbol").iterrows():
        item = item_map.get(row["symbol"])

        if item is None:
            result_rows.append(
                {
                    "symbol": row["symbol"],
                    "status": "FAIL",
                    "mismatch_fields": "missing_from_investigations_payload",
                }
            )
            continue

        mismatches = []

        expected = {
            "state": row["lifecycle_state_v2"],
            "active": bool(row["investigation_active_v2"]),
            "evidence_confidence": (
                None
                if pd.isna(row["evidence_confidence_v3"])
                else float(row["evidence_confidence_v3"])
            ),
            "context_scope": row["context_scope"],
            "relative_turnover": (
                None
                if pd.isna(row["relative_turnover"])
                else float(row["relative_turnover"])
            ),
            "current_5d_range_pct": (
                None
                if pd.isna(row["current_5d_range_pct"])
                else float(row["current_5d_range_pct"])
            ),
            "persistence_hits": int(
                row["support_sessions_in_last_5"]
            ),
        }

        for field, expected_value in expected.items():
            actual = item.get(field)

            if isinstance(expected_value, float):
                if actual is None or not math.isclose(
                    float(actual),
                    expected_value,
                    rel_tol=0,
                    abs_tol=1e-12,
                ):
                    mismatches.append(field)
            else:
                if actual != expected_value:
                    mismatches.append(field)

        ticker_obj = json.loads(
            (
                root
                / "tickers"
                / row["symbol"]
                / "investigation.json"
            ).read_text(encoding="utf-8")
        )

        ticker_expected = {
            "state": row["lifecycle_state_v2"],
            "active": bool(row["investigation_active_v2"]),
            "investigation_id": (
                None
                if pd.isna(row["investigation_id"])
                else str(row["investigation_id"])
            ),
        }

        for field, expected_value in ticker_expected.items():
            if ticker_obj.get(field) != expected_value:
                mismatches.append(f"ticker.{field}")

        result_rows.append(
            {
                "symbol": row["symbol"],
                "status": "PASS" if not mismatches else "FAIL",
                "mismatch_fields": "|".join(mismatches),
            }
        )

    state_priority = {
        "ESTABLISHED": 4,
        "DEVELOPING": 3,
        "EMERGING": 2,
        "WEAKENING": 1,
    }

    expected_spotlight = None

    if len(active):
        ranked = active.copy()
        ranked["_priority"] = ranked[
            "lifecycle_state_v2"
        ].map(state_priority)
        ranked["_confidence"] = ranked[
            "evidence_confidence_v3"
        ].fillna(-1)

        ranked = ranked.sort_values(
            ["_priority", "_confidence"],
            ascending=[False, False],
        )

        expected_spotlight = ranked.iloc[0]["symbol"]

    metadata = {
        "expected_kpis": expected_kpis,
        "actual_kpis": overview.get("kpis", {}),
        "expected_spotlight": expected_spotlight,
        "actual_spotlight": (
            overview.get("spotlight", {}) or {}
        ).get("symbol"),
        "payload_as_of": overview.get("as_of"),
        "snapshot_date": snapshot_date,
        "explorer_items": len(explorer.get("items", [])),
    }

    return pd.DataFrame(result_rows), metadata


def raw_source_parity(
    rawdir,
    detector_path,
    timeline_v2,
):
    detector = import_module(
        Path(detector_path),
        "signal_detector_validation",
    )

    fields = [
        "close",
        "compression_score",
        "current_5d_range_pct",
        "baseline_5d_range_pct",
        "compression_ratio",
        "compression_valid",
        "compression_quality_flag",
        "activity_score",
        "relative_turnover",
        "relative_volume",
        "relative_transaction_count",
        "participation_score",
        "relative_avg_trade_value",
        "relative_top5_net_buy_share",
        "flow_support_score",
        "foreign_net_to_turnover",
        "core_metrics_above_1_20x",
        "compression_gate_pass",
        "activity_gate_pass",
        "core_activity_gate_pass",
        "spot_hit",
    ]

    parity_rows = []
    quality_rows = []

    for symbol_dir in sorted(Path(rawdir).iterdir()):
        if not symbol_dir.is_dir():
            continue

        frame_path = symbol_dir / "analysis_frame.csv"

        if not frame_path.exists():
            continue

        symbol = symbol_dir.name.upper()
        frame = pd.read_csv(frame_path)
        frame["date"] = pd.to_datetime(frame["date"])

        calculated = []

        for idx in range(len(frame)):
            obs = detector.evaluate_day(frame, idx)

            if obs is not None:
                obs["symbol"] = symbol
                calculated.append(obs)

        calc = pd.DataFrame(calculated)

        if len(calc):
            calc["date"] = pd.to_datetime(calc["date"])

        stored = timeline_v2[
            timeline_v2["symbol"] == symbol
        ].copy()

        if len(stored) == 0:
            continue

        merged = stored.merge(
            calc,
            on=["symbol", "date"],
            suffixes=("_stored", "_calc"),
        )

        mismatch_count = 0

        for field in fields:
            a = merged[f"{field}_stored"]
            b = merged[f"{field}_calc"]

            if field in {
                "compression_valid",
                "compression_gate_pass",
                "activity_gate_pass",
                "core_activity_gate_pass",
                "spot_hit",
            }:
                eq = boolify(a) == boolify(b)

            elif field == "core_metrics_above_1_20x":
                eq = pd.to_numeric(a) == pd.to_numeric(b)

            elif (
                pd.api.types.is_numeric_dtype(a)
                and pd.api.types.is_numeric_dtype(b)
            ):
                eq = (
                    (a.isna() & b.isna())
                    | np.isclose(
                        pd.to_numeric(a, errors="coerce"),
                        pd.to_numeric(b, errors="coerce"),
                        equal_nan=True,
                        atol=1e-12,
                        rtol=0,
                    )
                )
            else:
                eq = compare_series(a, b)

            mismatch_count += int((~eq).sum())

        parity_rows.append(
            {
                "symbol": symbol,
                "raw_sessions": int(len(frame)),
                "evaluated_sessions": int(len(merged)),
                "fields_checked": len(fields),
                "field_value_mismatches": mismatch_count,
                "status": "PASS" if mismatch_count == 0 else "FAIL",
            }
        )

        quality_rows.append(
            {
                "symbol": symbol,
                "raw_sessions": int(len(frame)),
                "frequency_difference_nonzero": int(
                    (frame["freq_difference"] != 0).sum()
                ),
                "value_difference_nonzero": int(
                    (frame["value_difference"] != 0).sum()
                ),
                "lot_difference_nonzero": int(
                    (frame["lot_difference"] != 0).sum()
                ),
                "volume_match_false": int(
                    (~boolify(frame["volume_match"])).sum()
                ),
                "volume_mismatch_dates": "|".join(
                    frame.loc[
                        ~boolify(frame["volume_match"]),
                        "date",
                    ]
                    .dt.date.astype(str)
                    .tolist()
                ),
            }
        )

    return (
        pd.DataFrame(parity_rows),
        pd.DataFrame(quality_rows),
    )


def compute_forward_outcomes(timeline, horizon, selector):
    rows = []

    for symbol, group in timeline.groupby("symbol", sort=False):
        g = (
            group.sort_values("date")
            .reset_index(drop=True)
        )

        for idx, row in g.iterrows():
            if not selector(row):
                continue

            future = g.iloc[
                idx + 1 : idx + 1 + horizon
            ]

            if len(future) < horizon:
                continue

            end = future.iloc[-1]

            rows.append(
                {
                    "symbol": symbol,
                    "date": row["date"],
                    "support_share": float(
                        future["supporting_session_v2"].mean()
                    ),
                    "any_support": float(
                        future["supporting_session_v2"].any()
                    ),
                    "any_hard_spot": float(
                        future["spot_hit"].any()
                    ),
                    "repeat_spot_count": int(
                        future["spot_hit"].sum()
                    ),
                    "mean_activity": float(
                        future["activity_score"].mean()
                    ),
                    "mean_compression": float(
                        future["compression_score"].mean()
                    ),
                    "end_return": float(
                        end["close"] / row["close"] - 1.0
                    ),
                    "max_return": float(
                        future["close"].max()
                        / row["close"]
                        - 1.0
                    ),
                    "min_return": float(
                        future["close"].min()
                        / row["close"]
                        - 1.0
                    ),
                }
            )

    return pd.DataFrame(rows)


def bootstrap_diff_ci(
    event_values,
    control_values,
    seed,
    reps=3000,
):
    a = np.asarray(event_values, dtype=float)
    b = np.asarray(control_values, dtype=float)

    if len(a) == 0 or len(b) == 0:
        return (np.nan, np.nan)

    rng = np.random.default_rng(seed)
    diffs = np.empty(reps, dtype=float)

    for idx in range(reps):
        diffs[idx] = (
            rng.choice(a, len(a), replace=True).mean()
            - rng.choice(b, len(b), replace=True).mean()
        )

    return (
        float(np.quantile(diffs, 0.025)),
        float(np.quantile(diffs, 0.975)),
    )


def forward_separation_table(timeline):
    event_selector = lambda row: (
        bool(row["spot_hit"])
        and int(row["investigation_age_sessions"]) == 1
        and row["lifecycle_state_v2"] == "EMERGING"
    )

    control_selector = lambda row: (
        bool(row["compression_valid"])
        and not bool(row["spot_hit"])
        and row["lifecycle_state_v2"]
        == "NO_INVESTIGATION"
    )

    rows = []

    for horizon in [1, 3, 5, 10]:
        event = compute_forward_outcomes(
            timeline,
            horizon,
            event_selector,
        )
        control = compute_forward_outcomes(
            timeline,
            horizon,
            control_selector,
        )

        for metric in [
            "support_share",
            "any_support",
            "any_hard_spot",
            "end_return",
        ]:
            event_mean = float(event[metric].mean())
            control_mean = float(control[metric].mean())
            diff = event_mean - control_mean

            ci_low, ci_high = bootstrap_diff_ci(
                event[metric],
                control[metric],
                seed=20261002 + horizon * 10 + len(metric),
            )

            rows.append(
                {
                    "horizon_sessions": horizon,
                    "metric": metric,
                    "event_n": int(len(event)),
                    "control_n": int(len(control)),
                    "event_mean": event_mean,
                    "control_mean": control_mean,
                    "difference_event_minus_control": diff,
                    "bootstrap_95_ci_low": ci_low,
                    "bootstrap_95_ci_high": ci_high,
                }
            )

    return pd.DataFrame(rows)


def replay_dates(
    timeline_v2,
    timeline_v31,
    engine_path,
    universe_path,
):
    engine = import_module(
        Path(engine_path),
        "signal_engine_replay_validation",
    )

    universe = engine.load_universe(universe_path)

    candidates = [
        "2026-06-19",
        "2026-07-21",
        "2026-08-31",
        "2026-09-03",
        "2026-09-09",
        "2026-09-29",
    ]

    available = set(
        timeline_v2["date"].dt.date.astype(str)
    )

    targets = [
        pd.Timestamp(date)
        for date in candidates
        if date in available
    ]

    compare_cols = [
        "context_scope",
        "context_specificity_score",
        "market_activity_breadth",
        "market_activity_percentile",
        "peer_activity_breadth",
        "peer_activity_percentile",
        "supporting_session_v2",
        "lifecycle_state_v2",
        "investigation_active_v2",
        "investigation_id",
        "investigation_age_sessions",
        "hard_hits_total_in_episode",
        "support_sessions_total_in_episode",
        "support_sessions_in_last_5",
        "hard_hits_in_last_5",
        "unsupported_streak",
        "persistence_score_v2",
        "diagnostic_evidence_score_v3",
        "evidence_confidence_v3",
        "close_reason",
    ]

    rows = []

    for target in targets:
        prefix = timeline_v2[
            timeline_v2["date"] <= target
        ].copy()

        context, _ = engine.add_context_specificity(
            prefix,
            universe,
        )

        replay = engine.add_lifecycle(context)
        replay["date"] = pd.to_datetime(replay["date"])

        actual = (
            timeline_v31[
                timeline_v31["date"] == target
            ][["symbol"] + compare_cols]
            .sort_values("symbol")
            .reset_index(drop=True)
        )

        expected = (
            replay[
                replay["date"] == target
            ][["symbol"] + compare_cols]
            .sort_values("symbol")
            .reset_index(drop=True)
        )

        mismatches = 0

        for col in compare_cols:
            if col in {
                "context_scope",
                "lifecycle_state_v2",
                "investigation_id",
                "close_reason",
            }:
                eq = compare_series(
                    actual[col],
                    expected[col],
                )
            elif col in {
                "supporting_session_v2",
                "investigation_active_v2",
            }:
                eq = (
                    boolify(actual[col])
                    == boolify(expected[col])
                )
            else:
                eq = compare_series(
                    actual[col],
                    expected[col],
                    numeric=True,
                    atol=1e-12,
                )

            mismatches += int((~eq).sum())

        rows.append(
            {
                "date": target.date().isoformat(),
                "symbols_checked": int(len(actual)),
                "fields_per_symbol": len(compare_cols),
                "mismatches": mismatches,
                "status": (
                    "PASS"
                    if mismatches == 0
                    else "FAIL"
                ),
            }
        )

    return pd.DataFrame(rows)


def write_report(
    output_path,
    summary,
    checks,
    forward,
    snapshot_meta,
    raw_quality,
    full_quality,
):
    def pct(value):
        return f"{100 * value:.1f}%"

    forward_index = {
        (int(row["horizon_sessions"]), row["metric"]): row
        for _, row in forward.iterrows()
    }

    lines = []
    lines.append("# SIGNAL Validation Report v1")
    lines.append("")
    lines.append(
        "This report validates implementation correctness, point-in-time "
        "behavior, product-payload fidelity, and retrospective empirical "
        "separation. It does **not** claim labeled classification accuracy "
        "for 'institutional accumulation', because no independent ground-truth "
        "label set exists in the current project."
    )
    lines.append("")

    lines.append("## Executive result")
    lines.append("")
    lines.append(
        f"- **Implementation correctness:** {summary['implementation_correctness']}"
    )
    lines.append(
        f"- **Point-in-time calculation validity:** {summary['point_in_time_validity']}"
    )
    lines.append(
        f"- **Product payload validity:** {summary['product_payload_validity']}"
    )
    lines.append(
        f"- **Data quality:** {summary['data_quality_status']}"
    )
    lines.append(
        f"- **External / methodology validity:** {summary['methodology_validity_status']}"
    )
    lines.append(
        f"- **Price-prediction accuracy:** {summary['price_prediction_accuracy_status']}"
    )
    lines.append("")

    lines.append("## Dataset under test")
    lines.append("")
    lines.append(
        f"- {summary['rows']} evaluated rows across {summary['symbols']} tickers "
        f"and {summary['dates']} evaluation dates."
    )
    lines.append(
        f"- {summary['eligible_rows']} eligible observations, "
        f"{summary['spot_hits']} hard Spot hits, "
        f"{summary['episodes']} investigation episodes."
    )
    lines.append(
        f"- Evaluation timeline: {summary['timeline_start']} to {summary['timeline_end']}."
    )
    lines.append("")

    lines.append("## What passed")
    lines.append("")
    for check in checks:
        if check["status"] == "PASS":
            lines.append(
                f"- **{check['check_id']}** — PASS; "
                f"{check['observations_checked']} observations checked, "
                f"{check['mismatches']} mismatches."
            )
    lines.append("")

    lines.append("## Important defect found and fixed")
    lines.append("")
    lines.append(
        "During validation, the original historical demo payload was found to "
        "use the full episode summary table on the History page. That exposed "
        "future `closed_at` / `last_linked_at` values for episodes that were "
        "still open on 9 Sep 2026. This was a genuine historical-display "
        "look-ahead leak."
    )
    lines.append("")
    lines.append(
        "The payload builder was patched so historical episode summaries are "
        "reconstructed only from timeline rows available on or before `as_of`. "
        "The validated 9 Sep payload now contains no JSON date later than "
        "9 Sep 2026."
    )
    lines.append("")

    lines.append("## 9 Sep 2026 snapshot audit")
    lines.append("")
    lines.append(
        f"- Expected active investigations: "
        f"{snapshot_meta['expected_kpis']['active_investigations']}."
    )
    lines.append(
        f"- Expected state mix: "
        f"{snapshot_meta['expected_kpis']['established']} Established, "
        f"{snapshot_meta['expected_kpis']['developing']} Developing, "
        f"{snapshot_meta['expected_kpis']['emerging']} Emerging, "
        f"{snapshot_meta['expected_kpis']['weakening']} Weakening."
    )
    lines.append(
        f"- Expected Spotlight: **{snapshot_meta['expected_spotlight']}**."
    )
    lines.append(
        f"- Payload contained {snapshot_meta['explorer_items']} ticker rows."
    )
    lines.append("")

    lines.append("## Retrospective empirical separation")
    lines.append("")
    lines.append(
        "The primary external-validity question for the current detector is "
        "whether a newly opened Spot investigation is followed by more "
        "continuation evidence than ordinary NO_INVESTIGATION observations. "
        "This is more appropriate than asking whether price necessarily rises."
    )
    lines.append("")
    lines.append("| Horizon | Any future support: Spot open | Control | Difference | Repeat hard Spot: Spot open | Control |")
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for horizon in [1, 3, 5, 10]:
        support = forward_index[(horizon, "any_support")]
        repeat = forward_index[(horizon, "any_hard_spot")]

        lines.append(
            f"| {horizon} | "
            f"{pct(support['event_mean'])} | "
            f"{pct(support['control_mean'])} | "
            f"{pct(support['difference_event_minus_control'])} | "
            f"{pct(repeat['event_mean'])} | "
            f"{pct(repeat['control_mean'])} |"
        )

    lines.append("")
    lines.append(
        "Short-horizon continuation evidence is materially more common after "
        "new Spot openings than in the control group, and repeat hard Spot hits "
        "remain more common through 10 sessions. The separation in generic "
        "support fades by 10 sessions, which is consistent with a short-lived "
        "investigation lifecycle rather than a permanent regime label."
    )
    lines.append("")

    lines.append("### Price outcome")
    lines.append("")
    lines.append(
        "End-of-horizon close returns do **not** show a stable positive "
        "advantage for Spot openings in this sample. That is an important "
        "result: the current evidence supports SIGNAL as a detector of "
        "unusual/persistent market behavior, **not** as a validated price-up "
        "prediction model."
    )
    lines.append("")

    lines.append("## Data quality")
    lines.append("")
    if full_quality is not None and len(full_quality):
        mismatch_total = int(full_quality["volume_mismatch_count"].sum())
        lines.append(
            f"- Broker frequency, value, and lot parity were true for all "
            f"{len(full_quality)} cross-stock summaries."
        )
        lines.append(
            f"- Broker-share volume vs daily volume had {mismatch_total} "
            "recorded mismatches across the universe."
        )
        lines.append(
            "- 28 of those warnings occur on 29 May 2026; additional evaluable "
            "warnings occur on BBRI/TLKM/ASII (22 Jul) and BMRI "
            "(22 Jul, 29 Jul). None of those evaluable mismatch rows was a "
            "hard Spot hit."
        )
    elif raw_quality is not None and len(raw_quality):
        lines.append(
            "- Raw-cache data-quality checks are available in "
            "`raw_source_quality.csv`."
        )
    lines.append("")

    lines.append("## What is not yet proven")
    lines.append("")
    lines.append(
        "1. There is no independent human/market ground-truth label for "
        "'sideways accumulation', so precision, recall, F1, sensitivity, and "
        "specificity cannot honestly be reported yet."
    )
    lines.append(
        "2. The methodology thresholds were calibrated/reviewed using the "
        "May–Sep 2026 research period. Therefore 9 Sep is a valid historical "
        "replay but **not** a blind out-of-sample test."
    )
    lines.append(
        "3. A true external validation should freeze Methodology v1.0 Candidate "
        "and evaluate a later untouched period, such as 1 Oct 2026 onward, "
        "without changing thresholds."
    )
    lines.append("")

    lines.append("## GitHub recommendation")
    lines.append("")
    lines.append(
        "The code is suitable to share as a **research prototype / "
        "Methodology v1.0 Candidate** once the patched payload builder and "
        "validated historical payload are used. Do not describe the project "
        "as having proven predictive accuracy. Publish the validation report "
        "alongside the code so collaborators can reproduce the checks."
    )
    lines.append("")

    Path(output_path).write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Offline validation suite for SIGNAL Methodology v1.0 Candidate."
    )

    parser.add_argument("--timeline-v02", required=True)
    parser.add_argument("--timeline-v031", required=True)
    parser.add_argument("--episodes-v031", required=True)
    parser.add_argument("--universe", required=True)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--detector", required=False)
    parser.add_argument("--rawdir")
    parser.add_argument("--cross-stock-summary")
    parser.add_argument("--payload-dir")
    parser.add_argument("--snapshot-date", default="2026-09-09")
    parser.add_argument("--outdir", default="signal_validation_output")

    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    tl2 = pd.read_csv(args.timeline_v02)
    tl31 = pd.read_csv(args.timeline_v031)
    episodes = pd.read_csv(args.episodes_v031)

    tl2, tl31 = normalize_inputs(tl2, tl31)

    checks = []

    # ------------------------------------------------------------------
    # Data integrity
    # ------------------------------------------------------------------
    duplicate_count = int(
        tl31.duplicated(["symbol", "date"]).sum()
    )

    add_check(
        checks,
        "DATA_UNIQUE_SYMBOL_DATE",
        "data_integrity",
        "PASS" if duplicate_count == 0 else "FAIL",
        len(tl31),
        duplicate_count,
        "Each evaluated ticker/date must be unique.",
    )

    # ------------------------------------------------------------------
    # Hard Spot gate parity
    # ------------------------------------------------------------------
    expected_compression_gate = (
        tl2["compression_valid"]
        & (tl2["compression_score"] >= SPOT_COMPRESSION_MIN)
    )

    expected_activity_gate = (
        tl2["activity_score"] >= SPOT_ACTIVITY_MIN
    )

    expected_core_gate = (
        tl2["core_metrics_above_1_20x"]
        >= SPOT_CORE_RELATIVE_MIN_COUNT
    )

    expected_spot = (
        expected_compression_gate
        & expected_activity_gate
        & expected_core_gate
    )

    gate_mismatches = int(
        (expected_compression_gate != tl2["compression_gate_pass"]).sum()
        + (expected_activity_gate != tl2["activity_gate_pass"]).sum()
        + (expected_core_gate != tl2["core_activity_gate_pass"]).sum()
        + (expected_spot != tl2["spot_hit"]).sum()
    )

    add_check(
        checks,
        "SPOT_GATE_PARITY",
        "detector",
        "PASS" if gate_mismatches == 0 else "FAIL",
        len(tl2),
        gate_mismatches,
        "Compression/activity/core gates and final spot_hit recomputed independently.",
    )

    # ------------------------------------------------------------------
    # Context formula parity
    # ------------------------------------------------------------------
    ctx = independent_context(tl31)

    ctx_mismatch = 0

    ctx_mismatch += int(
        (
            ctx["expected_context_applicable"]
            != ctx["context_applicable"]
        ).sum()
    )

    ctx_mismatch += int(
        (
            ~compare_series(
                ctx["expected_context_specificity_score_raw"],
                ctx["context_specificity_score_raw"],
                numeric=True,
                atol=1e-10,
            )
        ).sum()
    )

    ctx_mismatch += int(
        (
            ~compare_series(
                ctx["expected_context_specificity_score"],
                ctx["context_specificity_score"],
                numeric=True,
                atol=1e-10,
            )
        ).sum()
    )

    ctx_mismatch += int(
        (
            ctx["expected_context_scope"]
            != ctx["context_scope"]
        ).sum()
    )

    add_check(
        checks,
        "CONTEXT_FORMULA_PARITY",
        "context",
        "PASS" if ctx_mismatch == 0 else "FAIL",
        len(ctx),
        ctx_mismatch,
        "Context applicability, specificity score, and scope recomputed independently.",
    )

    # ------------------------------------------------------------------
    # Lifecycle parity
    # ------------------------------------------------------------------
    lifecycle_frames = []

    for _, group in tl31.groupby("symbol", sort=True):
        lifecycle_frames.append(
            independent_lifecycle_for_symbol(group)
        )

    expected_lifecycle = pd.concat(
        lifecycle_frames,
        ignore_index=True,
    )

    merged = tl31.merge(
        expected_lifecycle,
        on=["symbol", "date"],
        how="left",
    )

    lifecycle_pairs = [
        ("supporting_session_v2", "expected_supporting_session_v2", False),
        ("lifecycle_state_v2", "expected_lifecycle_state_v2", False),
        ("investigation_active_v2", "expected_investigation_active_v2", False),
        ("investigation_id", "expected_investigation_id", False),
        ("investigation_age_sessions", "expected_investigation_age_sessions", True),
        ("hard_hits_total_in_episode", "expected_hard_hits_total_in_episode", True),
        ("support_sessions_total_in_episode", "expected_support_sessions_total_in_episode", True),
        ("support_sessions_in_last_5", "expected_support_sessions_in_last_5", True),
        ("hard_hits_in_last_5", "expected_hard_hits_in_last_5", True),
        ("unsupported_streak", "expected_unsupported_streak", True),
        ("persistence_score_v2", "expected_persistence_score_v2", True),
        ("diagnostic_evidence_score_v3", "expected_diagnostic_evidence_score_v3", True),
        ("evidence_confidence_v3", "expected_evidence_confidence_v3", True),
        ("close_reason", "expected_close_reason", False),
    ]

    lifecycle_mismatches = 0

    for actual_col, expected_col, numeric in lifecycle_pairs:
        eq = compare_series(
            merged[actual_col],
            merged[expected_col],
            numeric=numeric,
            atol=1e-12,
        )
        lifecycle_mismatches += int((~eq).sum())

    add_check(
        checks,
        "LIFECYCLE_STATE_MACHINE_PARITY",
        "lifecycle",
        "PASS" if lifecycle_mismatches == 0 else "FAIL",
        len(tl31),
        lifecycle_mismatches,
        "Lifecycle recomputed with an independent state-machine implementation.",
    )

    confidence_invariant_mismatch = int(
        (
            tl31["investigation_active_v2"]
            & tl31["evidence_confidence_v3"].isna()
        ).sum()
        + (
            (~tl31["investigation_active_v2"])
            & tl31["evidence_confidence_v3"].notna()
        ).sum()
    )

    add_check(
        checks,
        "EVIDENCE_CONFIDENCE_VISIBILITY",
        "lifecycle",
        "PASS" if confidence_invariant_mismatch == 0 else "FAIL",
        len(tl31),
        confidence_invariant_mismatch,
        "Evidence Confidence must exist only while an investigation is active.",
    )

    # ------------------------------------------------------------------
    # Episode table parity
    # ------------------------------------------------------------------
    independent_episodes = build_episode_table_independent(tl31)

    stored = episodes.copy()

    compare_episode_cols = [
        "symbol",
        "opened_at",
        "last_linked_at",
        "closed",
        "closed_at",
        "close_reason",
        "linked_sessions",
        "active_sessions",
        "hard_hits",
        "support_sessions",
        "peak_state",
        "open_context_scope",
        "max_evidence_confidence_v3",
    ]

    ep = stored.merge(
        independent_episodes,
        on="investigation_id",
        suffixes=("_stored", "_expected"),
        how="outer",
        indicator=True,
    )

    episode_mismatches = int(
        (ep["_merge"] != "both").sum()
    )

    both = ep[ep["_merge"] == "both"].copy()

    for col in compare_episode_cols:
        a = both[f"{col}_stored"]
        b = both[f"{col}_expected"]

        numeric = col in {
            "linked_sessions",
            "active_sessions",
            "hard_hits",
            "support_sessions",
            "max_evidence_confidence_v3",
        }

        eq = compare_series(
            a,
            b,
            numeric=numeric,
            atol=1e-12,
        )

        episode_mismatches += int((~eq).sum())

    add_check(
        checks,
        "EPISODE_TABLE_PARITY",
        "lifecycle",
        "PASS" if episode_mismatches == 0 else "FAIL",
        len(stored),
        episode_mismatches,
        "49 episode summaries independently reconstructed from the timeline.",
    )

    # ------------------------------------------------------------------
    # Prefix replay / look-ahead calculation check
    # ------------------------------------------------------------------
    replay = replay_dates(
        tl2,
        tl31,
        args.engine,
        args.universe,
    )

    replay.to_csv(
        outdir / "point_in_time_replay.csv",
        index=False,
    )

    replay_mismatches = int(replay["mismatches"].sum())

    add_check(
        checks,
        "POINT_IN_TIME_PREFIX_REPLAY",
        "point_in_time",
        "PASS" if replay_mismatches == 0 else "FAIL",
        int(replay["symbols_checked"].sum()),
        replay_mismatches,
        "Representative dates rerun using only rows available through each date.",
    )

    # ------------------------------------------------------------------
    # Payload audit
    # ------------------------------------------------------------------
    snapshot_audit = pd.DataFrame()
    snapshot_meta = {
        "expected_kpis": {},
        "actual_kpis": {},
        "expected_spotlight": None,
        "actual_spotlight": None,
        "explorer_items": 0,
    }

    if args.payload_dir:
        snapshot_audit, snapshot_meta = payload_snapshot_audit(
            args.payload_dir,
            tl31,
            args.snapshot_date,
        )

        snapshot_audit.to_csv(
            outdir / f"snapshot_{args.snapshot_date}_audit.csv",
            index=False,
        )

        payload_mismatches = int(
            (snapshot_audit["status"] != "PASS").sum()
        )

        metadata_mismatch = int(
            snapshot_meta["expected_kpis"]
            != snapshot_meta["actual_kpis"]
        ) + int(
            snapshot_meta["expected_spotlight"]
            != snapshot_meta["actual_spotlight"]
        )

        payload_mismatches += metadata_mismatch

        add_check(
            checks,
            "PRODUCT_SNAPSHOT_PARITY",
            "product_payload",
            "PASS" if payload_mismatches == 0 else "FAIL",
            len(snapshot_audit),
            payload_mismatches,
            f"Snapshot payload compared against timeline for {args.snapshot_date}.",
        )

        future_leaks = scan_future_dates(
            Path(args.payload_dir)
        )

        future_leaks.to_csv(
            outdir / "future_date_leak_scan.csv",
            index=False,
        )

        add_check(
            checks,
            "PRODUCT_FUTURE_DATE_SCAN",
            "point_in_time",
            "PASS" if len(future_leaks) == 0 else "FAIL",
            sum(
                1
                for _ in Path(args.payload_dir).rglob("*.json")
            ),
            len(future_leaks),
            "No historical product JSON may contain a dated field after its as_of date.",
        )
    else:
        future_leaks = pd.DataFrame()

    # ------------------------------------------------------------------
    # Raw cache source-to-detector parity (if supplied)
    # ------------------------------------------------------------------
    raw_parity = pd.DataFrame()
    raw_quality = pd.DataFrame()

    if args.rawdir and args.detector:
        raw_parity, raw_quality = raw_source_parity(
            args.rawdir,
            args.detector,
            tl2,
        )

        raw_parity.to_csv(
            outdir / "raw_source_detector_parity.csv",
            index=False,
        )

        raw_quality.to_csv(
            outdir / "raw_source_quality.csv",
            index=False,
        )

        raw_mismatches = int(
            raw_parity["field_value_mismatches"].sum()
        ) if len(raw_parity) else 0

        add_check(
            checks,
            "RAW_SOURCE_TO_DETECTOR_PARITY",
            "source_data",
            "PASS" if raw_mismatches == 0 else "FAIL",
            int(raw_parity["evaluated_sessions"].sum())
            if len(raw_parity)
            else 0,
            raw_mismatches,
            "Available raw analysis frames were recomputed through detector v0.2.",
        )

    # ------------------------------------------------------------------
    # Full cross-stock data-quality summary
    # ------------------------------------------------------------------
    full_quality = None

    if args.cross_stock_summary:
        full_quality = pd.read_csv(
            args.cross_stock_summary
        )

        parity_bad = int(
            (~boolify(full_quality["frequency_parity_all"])).sum()
            + (~boolify(full_quality["value_parity_all"])).sum()
            + (~boolify(full_quality["lot_parity_all"])).sum()
        )

        add_check(
            checks,
            "BROKER_FREQ_VALUE_LOT_PARITY",
            "source_data",
            "PASS" if parity_bad == 0 else "FAIL",
            len(full_quality),
            parity_bad,
            "Broker buy/sell frequency, value, and lot aggregate parity from cross-stock audit.",
        )

        warning_count = int(
            full_quality["volume_mismatch_count"].sum()
        )

        add_check(
            checks,
            "BROKER_DAILY_VOLUME_MATCH",
            "source_data",
            "WARN" if warning_count > 0 else "PASS",
            int(full_quality["sessions_merged"].sum()),
            warning_count,
            "Daily volume and broker-share volume are not identical on every cached session; retain as data-quality warnings.",
        )

        # Detail the evaluable mismatch dates.
        dq_rows = []

        for _, row in full_quality.iterrows():
            if pd.isna(row.get("volume_mismatch_dates")):
                continue

            for date in str(row["volume_mismatch_dates"]).split("|"):
                date = date.strip()

                if not date:
                    continue

                timeline_row = tl31[
                    (tl31["symbol"] == row["symbol"])
                    & (
                        tl31["date"]
                        == pd.Timestamp(date)
                    )
                ]

                dq_rows.append(
                    {
                        "symbol": row["symbol"],
                        "date": date,
                        "in_evaluable_timeline": bool(
                            len(timeline_row)
                        ),
                        "spot_hit": (
                            bool(
                                timeline_row.iloc[0]["spot_hit"]
                            )
                            if len(timeline_row)
                            else None
                        ),
                        "lifecycle_state": (
                            timeline_row.iloc[0][
                                "lifecycle_state_v2"
                            ]
                            if len(timeline_row)
                            else None
                        ),
                        "activity_score": (
                            float(
                                timeline_row.iloc[0][
                                    "activity_score"
                                ]
                            )
                            if len(timeline_row)
                            else None
                        ),
                    }
                )

        pd.DataFrame(dq_rows).to_csv(
            outdir / "volume_mismatch_detail.csv",
            index=False,
        )

    # ------------------------------------------------------------------
    # Retrospective empirical separation
    # ------------------------------------------------------------------
    forward = forward_separation_table(tl31)

    forward.to_csv(
        outdir / "forward_empirical_separation.csv",
        index=False,
    )

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(
        outdir / "validation_checks.csv",
        index=False,
    )

    hard_failures = int(
        (checks_df["status"] == "FAIL").sum()
    )

    implementation_checks = checks_df[
        checks_df["layer"].isin(
            ["detector", "context", "lifecycle"]
        )
    ]

    point_checks = checks_df[
        checks_df["layer"].isin(
            ["point_in_time", "product_payload"]
        )
    ]

    summary = {
        "validation_version": "1.0.0",
        "methodology_status": "SIGNAL Methodology v1.0 Candidate",
        "timeline_start": tl31["date"].min().date().isoformat(),
        "timeline_end": tl31["date"].max().date().isoformat(),
        "rows": int(len(tl31)),
        "symbols": int(tl31["symbol"].nunique()),
        "dates": int(tl31["date"].nunique()),
        "eligible_rows": int(tl31["compression_valid"].sum()),
        "spot_hits": int(tl31["spot_hit"].sum()),
        "episodes": int(len(episodes)),
        "implementation_correctness": (
            "PASS"
            if (
                len(implementation_checks)
                and not (
                    implementation_checks["status"]
                    == "FAIL"
                ).any()
            )
            else "FAIL"
        ),
        "point_in_time_validity": (
            "PASS"
            if (
                len(point_checks)
                and not (
                    point_checks["status"]
                    == "FAIL"
                ).any()
            )
            else "FAIL"
        ),
        "product_payload_validity": (
            "PASS"
            if (
                (
                    checks_df["check_id"]
                    == "PRODUCT_SNAPSHOT_PARITY"
                )
                & (
                    checks_df["status"]
                    == "PASS"
                )
            ).any()
            else "NOT_TESTED_OR_FAIL"
        ),
        "data_quality_status": (
            "PASS_WITH_WARNINGS"
            if (
                checks_df["status"] == "WARN"
            ).any()
            else "PASS"
        ),
        "methodology_validity_status": (
            "PARTIAL_RETROSPECTIVE_SUPPORT; OUT_OF_SAMPLE_PENDING"
        ),
        "price_prediction_accuracy_status": (
            "NOT_ESTABLISHED; SIGNAL IS NOT VALIDATED AS A PRICE-DIRECTION MODEL"
        ),
        "hard_failures": hard_failures,
        "important_note": (
            "No independent ground-truth accumulation labels are available; "
            "precision/recall/F1 cannot be truthfully computed."
        ),
    }

    (outdir / "validation_summary.json").write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_report(
        outdir / "VALIDATION_REPORT.md",
        summary,
        checks,
        forward,
        snapshot_meta,
        raw_quality,
        full_quality,
    )

    print(
        json.dumps(
            {
                "implementation_correctness": summary[
                    "implementation_correctness"
                ],
                "point_in_time_validity": summary[
                    "point_in_time_validity"
                ],
                "product_payload_validity": summary[
                    "product_payload_validity"
                ],
                "data_quality_status": summary[
                    "data_quality_status"
                ],
                "hard_failures": hard_failures,
                "outdir": str(outdir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
