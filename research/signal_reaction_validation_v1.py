from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


HORIZONS = (1, 3, 5, 10)
REACTION_THRESHOLDS = (0.02, 0.03, 0.05)


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


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{100.0 * float(value):.{digits}f}%"


def load_timeline(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])

    for col in (
        "compression_valid",
        "spot_hit",
        "supporting_session_v2",
        "investigation_active_v2",
    ):
        if col in df.columns:
            df[col] = boolify(df[col])

    return df.sort_values(["symbol", "date"]).reset_index(drop=True)


def build_symbol_groups(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        symbol: group.sort_values("date").reset_index(drop=True)
        for symbol, group in df.groupby("symbol", sort=False)
    }


def first_touch_from_close(
    closes: np.ndarray,
    entry: float,
    threshold: float,
) -> tuple[int, int, int]:
    up_idx = np.flatnonzero(closes >= entry * (1.0 + threshold))
    down_idx = np.flatnonzero(closes <= entry * (1.0 - threshold))

    first_up = int(up_idx[0]) if len(up_idx) else None
    first_down = int(down_idx[0]) if len(down_idx) else None

    if first_up is None and first_down is None:
        race = 0
    elif first_down is None or (
        first_up is not None and first_up < first_down
    ):
        race = 1
    elif first_up is None or first_down < first_up:
        race = -1
    else:
        race = 0

    return (
        int(race == 1),
        int(race == -1),
        int(race != 0),
    )


def compute_close_outcome(
    row: pd.Series,
    horizon: int,
    groups: dict[str, pd.DataFrame],
) -> dict | None:
    group = groups[row["symbol"]]
    matches = group.index[group["date"].eq(row["date"])]

    if len(matches) != 1:
        return None

    idx = int(matches[0])
    future = group.iloc[idx + 1 : idx + 1 + horizon]

    if len(future) < horizon:
        return None

    entry = float(row["close"])
    closes = future["close"].astype(float).to_numpy()

    hist = group.iloc[max(0, idx - 4) : idx + 1]
    five_close_upper = (
        float(hist["close"].max())
        if len(hist) >= 5
        else np.nan
    )

    breakout = np.nan
    time_to_breakout = np.nan
    followthrough_next = np.nan

    if not pd.isna(five_close_upper):
        above = closes > five_close_upper
        breakout = float(above.any())

        if above.any():
            first_idx = int(np.argmax(above))
            time_to_breakout = first_idx + 1

            if first_idx + 1 < len(closes):
                followthrough_next = float(
                    closes[first_idx + 1] > five_close_upper
                )

    out = {
        "entry_close": entry,
        "end_return": float(closes[-1] / entry - 1.0),
        "mfe_close": float(closes.max() / entry - 1.0),
        "mae_close": float(closes.min() / entry - 1.0),
        "positive_end": float(closes[-1] > entry),
        "breakout_5d_close": breakout,
        "time_to_breakout_sessions": time_to_breakout,
        "followthrough_next": followthrough_next,
        "five_close_upper": five_close_upper,
    }

    for threshold in REACTION_THRESHOLDS:
        label = int(round(threshold * 100))

        out[f"hit_up_{label}"] = float(
            closes.max() >= entry * (1.0 + threshold)
        )
        out[f"hit_down_{label}"] = float(
            closes.min() <= entry * (1.0 - threshold)
        )

        up_first, down_first, resolved = first_touch_from_close(
            closes,
            entry,
            threshold,
        )

        out[f"up_before_down_{label}"] = float(up_first)
        out[f"down_before_up_{label}"] = float(down_first)
        out[f"race_resolved_{label}"] = float(resolved)

    return out


def build_anchors(timeline: pd.DataFrame) -> pd.DataFrame:
    rows = []

    linked = timeline[timeline["investigation_id"].notna()].copy()

    for investigation_id, group in linked.groupby("investigation_id"):
        group = group.sort_values("date")

        opening = group[group["investigation_age_sessions"] == 1]

        if len(opening):
            row = opening.iloc[0]
            rows.append(
                {
                    "anchor_type": "SPOT_OPEN",
                    "investigation_id": investigation_id,
                    **row.to_dict(),
                }
            )

        for state in ("DEVELOPING", "ESTABLISHED"):
            hit = group[group["lifecycle_state_v2"] == state]

            if len(hit):
                row = hit.iloc[0]
                rows.append(
                    {
                        "anchor_type": f"{state}_FIRST",
                        "investigation_id": investigation_id,
                        **row.to_dict(),
                    }
                )

    return pd.DataFrame(rows)


def eligible_controls(
    timeline: pd.DataFrame,
    event_row: pd.Series,
    peer_only: bool = False,
) -> pd.DataFrame:
    controls = timeline[
        timeline["date"].eq(event_row["date"])
        & timeline["compression_valid"]
        & ~timeline["spot_hit"]
        & timeline["lifecycle_state_v2"].eq("NO_INVESTIGATION")
        & ~timeline["symbol"].eq(event_row["symbol"])
    ].copy()

    if peer_only:
        peer = controls[
            controls["peer_group"].eq(event_row["peer_group"])
        ]

        # Avoid a single-ticker pseudo-control.
        if len(peer) >= 2:
            return peer

    return controls


def summarize_control_outcomes(
    controls: pd.DataFrame,
    horizon: int,
    groups: dict[str, pd.DataFrame],
) -> tuple[int, dict]:
    outcomes = []

    for _, row in controls.iterrows():
        outcome = compute_close_outcome(row, horizon, groups)
        if outcome is not None:
            outcomes.append(outcome)

    if not outcomes:
        return 0, {}

    frame = pd.DataFrame(outcomes)

    return len(frame), {
        col: float(frame[col].mean(skipna=True))
        for col in frame.columns
        if pd.api.types.is_numeric_dtype(frame[col])
    }


def create_event_detail(
    timeline: pd.DataFrame,
    anchors: pd.DataFrame,
) -> pd.DataFrame:
    groups = build_symbol_groups(timeline)
    rows = []

    for _, event in anchors.iterrows():
        for horizon in HORIZONS:
            outcome = compute_close_outcome(
                event,
                horizon,
                groups,
            )

            if outcome is None:
                continue

            market_controls = eligible_controls(
                timeline,
                event,
                peer_only=False,
            )

            peer_controls = eligible_controls(
                timeline,
                event,
                peer_only=True,
            )

            market_n, market = summarize_control_outcomes(
                market_controls,
                horizon,
                groups,
            )

            peer_n, peer = summarize_control_outcomes(
                peer_controls,
                horizon,
                groups,
            )

            row = {
                "anchor_type": event["anchor_type"],
                "investigation_id": event["investigation_id"],
                "symbol": event["symbol"],
                "date": event["date"],
                "peer_group": event["peer_group"],
                "state_at_anchor": event["lifecycle_state_v2"],
                "evidence_confidence": event.get(
                    "evidence_confidence_v3",
                    np.nan,
                ),
                "context_scope": event.get(
                    "context_scope",
                    None,
                ),
                "horizon_sessions": horizon,
                **outcome,
                "market_control_n": market_n,
                "peer_control_n": peer_n,
            }

            for key, value in market.items():
                row[f"market_control_{key}"] = value

            for key, value in peer.items():
                row[f"peer_control_{key}"] = value

            rows.append(row)

    return pd.DataFrame(rows)


def cluster_bootstrap_diff(
    frame: pd.DataFrame,
    metric: str,
    control_prefix: str,
    reps: int,
    seed: int,
) -> tuple[float, float, float, int]:
    control_col = f"{control_prefix}_{metric}"

    work = frame[
        ["date", metric, control_col]
    ].dropna().copy()

    if len(work) == 0:
        return np.nan, np.nan, np.nan, 0

    work["diff"] = work[metric] - work[control_col]

    clusters = {
        date: group["diff"].to_numpy(dtype=float)
        for date, group in work.groupby("date")
    }

    keys = list(clusters)

    rng = np.random.default_rng(seed)
    boot = np.empty(reps, dtype=float)

    for idx in range(reps):
        sampled = rng.choice(keys, size=len(keys), replace=True)
        values = np.concatenate(
            [clusters[key] for key in sampled]
        )
        boot[idx] = float(np.mean(values))

    return (
        float(work["diff"].mean()),
        float(np.quantile(boot, 0.025)),
        float(np.quantile(boot, 0.975)),
        len(keys),
    )


def summarize_reactions(
    detail: pd.DataFrame,
    bootstrap_reps: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [
        "end_return",
        "positive_end",
        "mfe_close",
        "mae_close",
        "breakout_5d_close",
        "followthrough_next",
        "hit_up_2",
        "hit_up_3",
        "hit_up_5",
        "hit_down_2",
        "hit_down_3",
        "hit_down_5",
        "up_before_down_2",
        "up_before_down_3",
        "up_before_down_5",
    ]

    summary_rows = []
    bootstrap_rows = []

    for (anchor, horizon), group in detail.groupby(
        ["anchor_type", "horizon_sessions"]
    ):
        row = {
            "anchor_type": anchor,
            "horizon_sessions": int(horizon),
            "event_n": int(len(group)),
            "unique_event_dates": int(group["date"].nunique()),
        }

        for metric in metrics:
            row[f"{metric}_event"] = float(
                group[metric].mean(skipna=True)
            )

            for control_name in (
                "market_control",
                "peer_control",
            ):
                control_col = f"{control_name}_{metric}"

                if control_col in group.columns:
                    row[f"{metric}_{control_name}"] = float(
                        group[control_col].mean(skipna=True)
                    )
                    row[
                        f"{metric}_{control_name}_diff"
                    ] = (
                        row[f"{metric}_event"]
                        - row[f"{metric}_{control_name}"]
                    )

        summary_rows.append(row)

        # Inferential table uses same-date market controls as primary
        # comparator. Bootstrap is clustered by event date.
        for metric in metrics:
            control_col = f"market_control_{metric}"

            if control_col not in group.columns:
                continue

            diff, low, high, clusters = cluster_bootstrap_diff(
                group,
                metric,
                "market_control",
                reps=bootstrap_reps,
                seed=20261002
                + int(horizon) * 100
                + sum(ord(ch) for ch in metric),
            )

            bootstrap_rows.append(
                {
                    "anchor_type": anchor,
                    "horizon_sessions": int(horizon),
                    "metric": metric,
                    "event_n": int(
                        group[[metric, control_col]]
                        .dropna()
                        .shape[0]
                    ),
                    "date_clusters": clusters,
                    "matched_difference": diff,
                    "cluster_bootstrap_95_ci_low": low,
                    "cluster_bootstrap_95_ci_high": high,
                    "ci_excludes_zero": bool(
                        pd.notna(low)
                        and pd.notna(high)
                        and (
                            (low > 0 and high > 0)
                            or (low < 0 and high < 0)
                        )
                    ),
                }
            )

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(bootstrap_rows),
    )


def add_first_touch_conditional(
    summary: pd.DataFrame,
) -> pd.DataFrame:
    out = summary.copy()

    for threshold in (2, 3, 5):
        for side in ("event", "market_control", "peer_control"):
            up = f"up_before_down_{threshold}_{side}"
            down = f"down_before_up_{threshold}_{side}"

            if up in out.columns and down in out.columns:
                denom = out[up] + out[down]

                out[
                    f"positive_share_among_resolved_{threshold}_{side}"
                ] = np.where(
                    denom > 0,
                    out[up] / denom,
                    np.nan,
                )

    return out


def load_raw_ohlc_zip(
    raw_zip: str | Path,
) -> dict[str, pd.DataFrame]:
    result = {}

    with zipfile.ZipFile(raw_zip, "r") as archive:
        paths = [
            name
            for name in archive.namelist()
            if name.endswith("/analysis_frame.csv")
        ]

        for name in paths:
            symbol = Path(name).parent.name.upper()
            frame = pd.read_csv(
                io.BytesIO(archive.read(name))
            )
            frame["date"] = pd.to_datetime(frame["date"])
            result[symbol] = (
                frame.sort_values("date")
                .reset_index(drop=True)
            )

    return result


def compute_ohlc_outcome(
    raw: pd.DataFrame,
    date: pd.Timestamp,
    horizon: int,
) -> dict | None:
    matches = raw.index[raw["date"].eq(date)]

    if len(matches) != 1:
        return None

    idx = int(matches[0])
    future = raw.iloc[idx + 1 : idx + 1 + horizon]

    if len(future) < horizon:
        return None

    entry = float(raw.iloc[idx]["close"])
    highs = future["high"].astype(float).to_numpy()
    lows = future["low"].astype(float).to_numpy()

    hist = raw.iloc[max(0, idx - 4) : idx + 1]

    prior_high = (
        float(hist["high"].max())
        if len(hist) >= 5
        else np.nan
    )

    return {
        "entry_close": entry,
        "mfe_high": float(highs.max() / entry - 1.0),
        "mae_low": float(lows.min() / entry - 1.0),
        "breakout_5d_high": (
            float((highs > prior_high).any())
            if not pd.isna(prior_high)
            else np.nan
        ),
        "five_day_high": prior_high,
    }


def create_ohlc_subset(
    anchors: pd.DataFrame,
    raw_zip: str | Path | None,
) -> pd.DataFrame:
    if not raw_zip:
        return pd.DataFrame()

    raw_groups = load_raw_ohlc_zip(raw_zip)
    rows = []

    opening = anchors[
        anchors["anchor_type"].eq("SPOT_OPEN")
    ]

    for _, event in opening.iterrows():
        symbol = event["symbol"]

        if symbol not in raw_groups:
            continue

        for horizon in HORIZONS:
            outcome = compute_ohlc_outcome(
                raw_groups[symbol],
                pd.Timestamp(event["date"]),
                horizon,
            )

            if outcome is None:
                continue

            rows.append(
                {
                    "investigation_id": event["investigation_id"],
                    "symbol": symbol,
                    "date": event["date"],
                    "horizon_sessions": horizon,
                    **outcome,
                }
            )

    return pd.DataFrame(rows)


def build_assessment(
    summary: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> dict:
    spot = summary[
        summary["anchor_type"].eq("SPOT_OPEN")
    ].copy()

    boot = bootstrap[
        bootstrap["anchor_type"].eq("SPOT_OPEN")
    ].copy()

    directional_evidence = []

    for horizon in HORIZONS:
        row = spot[
            spot["horizon_sessions"].eq(horizon)
        ]

        if len(row) == 0:
            continue

        r = row.iloc[0]

        directional_evidence.append(
            {
                "horizon_sessions": horizon,
                "event_n": int(r["event_n"]),
                "positive_end_rate": float(
                    r["positive_end_event"]
                ),
                "market_control_positive_end_rate": float(
                    r["positive_end_market_control"]
                ),
                "end_return": float(
                    r["end_return_event"]
                ),
                "market_control_end_return": float(
                    r["end_return_market_control"]
                ),
                "mfe_close": float(
                    r["mfe_close_event"]
                ),
                "market_control_mfe_close": float(
                    r["mfe_close_market_control"]
                ),
                "mae_close": float(
                    r["mae_close_event"]
                ),
                "market_control_mae_close": float(
                    r["mae_close_market_control"]
                ),
                "hit_up_2_rate": float(
                    r["hit_up_2_event"]
                ),
                "market_control_hit_up_2_rate": float(
                    r["hit_up_2_market_control"]
                ),
                "breakout_rate": float(
                    r["breakout_5d_close_event"]
                ),
                "market_control_breakout_rate": float(
                    r["breakout_5d_close_market_control"]
                ),
            }
        )

    significant_positive = boot[
        boot["ci_excludes_zero"]
        & (boot["matched_difference"] > 0)
        & boot["metric"].isin(
            [
                "end_return",
                "positive_end",
                "mfe_close",
                "mae_close",
                "breakout_5d_close",
                "hit_up_2",
                "hit_up_3",
                "hit_up_5",
                "up_before_down_2",
                "up_before_down_3",
                "up_before_down_5",
            ]
        )
    ]

    significant_negative = boot[
        boot["ci_excludes_zero"]
        & (boot["matched_difference"] < 0)
    ]

    return {
        "primary_event_definition": (
            "First session of each investigation episode (SPOT_OPEN); "
            "one anchor per episode prevents repeated hard hits from "
            "over-weighting persistent episodes."
        ),
        "primary_control_definition": (
            "Same-date eligible NO_INVESTIGATION observations, excluding "
            "the event ticker. This controls for broad market-day effects."
        ),
        "full_universe_price_measurement": (
            "Close-to-close because the derived 28-ticker timeline retained "
            "daily close but not daily high/low. MFE/MAE in the full-universe "
            "test are therefore close-based proxies."
        ),
        "status": (
            "TENTATIVE_DIRECTIONAL_INFORMATION; "
            "NOT YET ROBUST FOR A <=5 SESSION CLAIM"
        ),
        "interpretation": (
            "SPOT_OPEN shows a generally favorable direction versus same-date "
            "controls in several reaction metrics, especially by 5-10 sessions. "
            "However most <=5-session date-cluster bootstrap intervals still "
            "cross zero. The current retrospective sample is therefore "
            "suggestive, not sufficient to claim reliable short-horizon "
            "price-direction prediction."
        ),
        "significant_positive_findings": (
            significant_positive[
                [
                    "horizon_sessions",
                    "metric",
                    "matched_difference",
                    "cluster_bootstrap_95_ci_low",
                    "cluster_bootstrap_95_ci_high",
                ]
            ].to_dict("records")
        ),
        "significant_negative_findings": (
            significant_negative[
                [
                    "horizon_sessions",
                    "metric",
                    "matched_difference",
                    "cluster_bootstrap_95_ci_low",
                    "cluster_bootstrap_95_ci_high",
                ]
            ].to_dict("records")
        ),
        "directional_evidence": directional_evidence,
    }


def write_report(
    path: str | Path,
    timeline: pd.DataFrame,
    anchors: pd.DataFrame,
    summary: pd.DataFrame,
    bootstrap: pd.DataFrame,
    ohlc_subset: pd.DataFrame,
    assessment: dict,
) -> None:
    spot = summary[
        summary["anchor_type"].eq("SPOT_OPEN")
    ].sort_values("horizon_sessions")

    developing = summary[
        summary["anchor_type"].eq("DEVELOPING_FIRST")
    ].sort_values("horizon_sessions")

    established = summary[
        summary["anchor_type"].eq("ESTABLISHED_FIRST")
    ].sort_values("horizon_sessions")

    lines = [
        "# SIGNAL Reaction Validation v1",
        "",
        "## Question",
        "",
        "Does a SIGNAL investigation help identify stocks that subsequently "
        "show more favorable price reaction than comparable stocks that were "
        "not under investigation on the same market date?",
        "",
        "This study does not alter Detector v1.0 Candidate thresholds. It is "
        "a validation layer placed after the frozen detector.",
        "",
        "## Design",
        "",
        f"- Evaluated timeline: {timeline['date'].min().date()} to "
        f"{timeline['date'].max().date()}.",
        f"- Universe: {timeline['symbol'].nunique()} tickers.",
        f"- Investigation episodes / SPOT_OPEN anchors: "
        f"{int((anchors['anchor_type'] == 'SPOT_OPEN').sum())}.",
        f"- First DEVELOPING anchors: "
        f"{int((anchors['anchor_type'] == 'DEVELOPING_FIRST').sum())}.",
        f"- First ESTABLISHED anchors: "
        f"{int((anchors['anchor_type'] == 'ESTABLISHED_FIRST').sum())}.",
        "- Horizons: +1, +3, +5, +10 trading sessions.",
        "- Primary controls: eligible NO_INVESTIGATION stocks on the same "
        "market date.",
        "- Confidence intervals: bootstrap of matched event-minus-control "
        "differences, clustered by event date.",
        "",
        "## Primary result — SPOT_OPEN",
        "",
        "| Horizon | Positive close | Control | +2% reached | Control | "
        "5D-close breakout | Control | Mean end return | Control |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for _, row in spot.iterrows():
        lines.append(
            f"| {int(row['horizon_sessions'])} | "
            f"{fmt_pct(row['positive_end_event'])} | "
            f"{fmt_pct(row['positive_end_market_control'])} | "
            f"{fmt_pct(row['hit_up_2_event'])} | "
            f"{fmt_pct(row['hit_up_2_market_control'])} | "
            f"{fmt_pct(row['breakout_5d_close_event'])} | "
            f"{fmt_pct(row['breakout_5d_close_market_control'])} | "
            f"{fmt_pct(row['end_return_event'], 2)} | "
            f"{fmt_pct(row['end_return_market_control'], 2)} |"
        )

    lines.extend(
        [
            "",
            "The direction is generally favorable by +5 and +10 sessions: "
            "SPOT_OPEN has higher positive-close rate, higher +2% reaction "
            "rate, and higher 5-session closing-range breakout rate than "
            "same-date controls. The effect is modest rather than dominant.",
            "",
            "## Favorable excursion vs adverse excursion",
            "",
            "| Horizon | Close-MFE SIGNAL | Control | Close-MAE SIGNAL | Control |",
            "|---:|---:|---:|---:|---:|",
        ]
    )

    for _, row in spot.iterrows():
        lines.append(
            f"| {int(row['horizon_sessions'])} | "
            f"{fmt_pct(row['mfe_close_event'], 2)} | "
            f"{fmt_pct(row['mfe_close_market_control'], 2)} | "
            f"{fmt_pct(row['mae_close_event'], 2)} | "
            f"{fmt_pct(row['mae_close_market_control'], 2)} |"
        )

    lines.extend(
        [
            "",
            "A less-negative MAE is favorable. On the current retrospective "
            "sample, SPOT_OPEN generally has slightly larger favorable "
            "excursion and less-severe adverse close excursion than same-date "
            "controls at the longer horizons.",
            "",
            "## First-touch test",
            "",
            "The first-touch test asks whether +X% is reached before -X% "
            "within the horizon. This is closer to a directional reaction "
            "question than fixed-horizon return alone.",
            "",
            "| Horizon | +2 before -2 | Control | +3 before -3 | Control | "
            "+5 before -5 | Control |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for _, row in spot.iterrows():
        lines.append(
            f"| {int(row['horizon_sessions'])} | "
            f"{fmt_pct(row['up_before_down_2_event'])} | "
            f"{fmt_pct(row['up_before_down_2_market_control'])} | "
            f"{fmt_pct(row['up_before_down_3_event'])} | "
            f"{fmt_pct(row['up_before_down_3_market_control'])} | "
            f"{fmt_pct(row['up_before_down_5_event'])} | "
            f"{fmt_pct(row['up_before_down_5_market_control'])} |"
        )

    sig = bootstrap[
        bootstrap["anchor_type"].eq("SPOT_OPEN")
        & bootstrap["ci_excludes_zero"]
    ].sort_values(["horizon_sessions", "metric"])

    lines.extend(
        [
            "",
            "## Bootstrap evidence",
            "",
            "Most +1 to +5 session matched differences have 95% intervals "
            "that still cross zero. Therefore the data do not justify a "
            "strong <=1-week directional-accuracy claim yet.",
            "",
        ]
    )

    if len(sig):
        lines.append(
            "The SPOT_OPEN differences whose date-cluster bootstrap interval "
            "does not cross zero are:"
        )
        lines.append("")

        for _, row in sig.iterrows():
            lines.append(
                f"- +{int(row['horizon_sessions'])} sessions, "
                f"`{row['metric']}`: difference "
                f"{row['matched_difference']:.4f}, 95% CI "
                f"[{row['cluster_bootstrap_95_ci_low']:.4f}, "
                f"{row['cluster_bootstrap_95_ci_high']:.4f}]."
            )
    else:
        lines.append(
            "No tested SPOT_OPEN metric has a date-cluster bootstrap interval "
            "that excludes zero."
        )

    lines.extend(
        [
            "",
            "## Lifecycle-state transitions",
            "",
            f"- DEVELOPING has {len(developing) and int(developing.iloc[0]['event_n']) or 0} "
            "first-transition anchors.",
            f"- ESTABLISHED has only "
            f"{len(established) and int(established.iloc[0]['event_n']) or 0} "
            "first-transition anchors.",
            "",
            "The DEVELOPING results are mixed across horizons. ESTABLISHED "
            "has only three episodes, which is far too small for a reliable "
            "directional conclusion. Therefore state escalation must not yet "
            "be marketed as monotonic price-prediction confidence.",
            "",
            "## OHLC subset",
            "",
        ]
    )

    if len(ohlc_subset):
        lines.extend(
            [
                f"Raw OHLC was available in the retained cache for "
                f"{ohlc_subset['symbol'].nunique()} tickers and "
                f"{ohlc_subset['investigation_id'].nunique()} SPOT_OPEN "
                "episodes. This subset was used to calculate true intraday "
                "high-based MFE and low-based MAE.",
                "",
                "This subset is useful as a calculation cross-check, but it "
                "is too small to replace the 28-ticker close-based analysis.",
                "",
            ]
        )
    else:
        lines.append(
            "No raw OHLC subset was supplied. Full-universe MFE/MAE therefore "
            "remain close-based proxies."
        )
        lines.append("")

    lines.extend(
        [
            "## Conclusion",
            "",
            f"**Status: {assessment['status']}**",
            "",
            assessment["interpretation"],
            "",
            "The correct product claim at this stage is:",
            "",
            "> SIGNAL identifies unusual compressed-activity setups that show "
            "some favorable subsequent reaction characteristics versus "
            "same-date controls in retrospective data. Reliable short-horizon "
            "directional prediction has not yet been established.",
            "",
            "The next decisive test is out-of-sample: freeze Methodology v1.0 "
            "Candidate and evaluate untouched data from 1 Oct 2026 onward "
            "without changing thresholds.",
        ]
    )

    Path(path).write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Reaction Validation v1 for SIGNAL."
    )

    parser.add_argument(
        "--timeline",
        required=True,
        help="cross_stock_timeline_v0_3_1 CSV",
    )

    parser.add_argument(
        "--raw-zip",
        help="Optional raw.zip containing */analysis_frame.csv files",
    )

    parser.add_argument(
        "--outdir",
        default="signal_reaction_validation_v1_output",
    )

    parser.add_argument(
        "--bootstrap-reps",
        type=int,
        default=5000,
    )

    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    timeline = load_timeline(args.timeline)
    anchors = build_anchors(timeline)

    detail = create_event_detail(
        timeline,
        anchors,
    )

    summary, bootstrap = summarize_reactions(
        detail,
        bootstrap_reps=args.bootstrap_reps,
    )

    summary = add_first_touch_conditional(summary)

    ohlc_subset = create_ohlc_subset(
        anchors,
        args.raw_zip,
    )

    assessment = build_assessment(
        summary,
        bootstrap,
    )

    anchors.to_csv(
        outdir / "reaction_anchors.csv",
        index=False,
    )

    detail.to_csv(
        outdir / "reaction_event_detail.csv",
        index=False,
    )

    summary.to_csv(
        outdir / "reaction_metric_summary.csv",
        index=False,
    )

    bootstrap.to_csv(
        outdir / "directional_information_bootstrap.csv",
        index=False,
    )

    ohlc_subset.to_csv(
        outdir / "ohlc_subset_reaction.csv",
        index=False,
    )

    (outdir / "reaction_validation_summary.json").write_text(
        json.dumps(
            assessment,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    write_report(
        outdir / "REACTION_VALIDATION_REPORT.md",
        timeline,
        anchors,
        summary,
        bootstrap,
        ohlc_subset,
        assessment,
    )

    print(
        json.dumps(
            {
                "status": assessment["status"],
                "spot_open_anchors": int(
                    (anchors["anchor_type"] == "SPOT_OPEN").sum()
                ),
                "developing_first_anchors": int(
                    (
                        anchors["anchor_type"]
                        == "DEVELOPING_FIRST"
                    ).sum()
                ),
                "established_first_anchors": int(
                    (
                        anchors["anchor_type"]
                        == "ESTABLISHED_FIRST"
                    ).sum()
                ),
                "ohlc_subset_episodes": int(
                    ohlc_subset["investigation_id"].nunique()
                )
                if len(ohlc_subset)
                else 0,
                "outdir": str(outdir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
