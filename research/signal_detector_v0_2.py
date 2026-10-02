
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


METHODOLOGY_VERSION = "0.2.0"

BASELINE = 20
RANGE_WINDOW = 5
PERSISTENCE_WINDOW = 5

# Frozen from v0.1.1 while we expand cross-stock validation.
MIN_COMPRESSION_SCORE = 55.0
MIN_ACTIVITY_SCORE = 50.0
MIN_CORE_RELATIVE = 1.20
MIN_CORE_RELATIVE_COUNT = 2

ACTIVE_STATES = {
    "EMERGING",
    "DEVELOPING",
    "ESTABLISHED",
    "WEAKENING",
}


def interp_score(x, knots):
    xs = [k[0] for k in knots]
    ys = [k[1] for k in knots]
    return float(np.interp(x, xs, ys, left=ys[0], right=ys[-1]))


def robust_z(x, hist):
    hist = np.asarray(hist, dtype=float)
    hist = hist[np.isfinite(hist)]

    if len(hist) == 0 or not np.isfinite(x):
        return 0.0

    med = float(np.median(hist))
    mad = float(np.median(np.abs(hist - med)))

    if mad <= 1e-12:
        return 0.0

    return float(0.6745 * (x - med) / mad)


def positive_anomaly_score(x, hist):
    """
    Upward-anomaly score for turnover, volume, transaction count,
    average trade value, and broker concentration.

    Returns:
        score 0..100
        relative ratio to 20-session median
        robust z-score
    """
    hist = np.asarray(hist, dtype=float)
    hist = hist[np.isfinite(hist)]

    if len(hist) == 0 or not np.isfinite(x):
        return 0.0, np.nan, 0.0

    med = float(np.median(hist))

    if med <= 1e-12:
        ratio = np.nan
    else:
        ratio = float(x / med)

    z = robust_z(x, hist)

    if np.isfinite(ratio):
        ratio_score = interp_score(
            ratio,
            [
                (0.0, 0.0),
                (1.00, 0.0),
                (1.15, 20.0),
                (1.30, 40.0),
                (1.50, 65.0),
                (2.00, 100.0),
            ],
        )
    else:
        ratio_score = 0.0

    z_score = interp_score(
        z,
        [
            (-99.0, 0.0),
            (0.00, 0.0),
            (0.75, 20.0),
            (1.50, 50.0),
            (2.50, 80.0),
            (4.00, 100.0),
        ],
    )

    score = 0.60 * ratio_score + 0.40 * z_score
    return float(score), ratio, float(z)


def rolling_range_pct(df, idx, window=RANGE_WINDOW):
    w = df.iloc[idx - window + 1 : idx + 1]
    median_close = float(w["close"].median())

    if median_close <= 0:
        return np.nan

    return float(
        (w["high"].max() - w["low"].min())
        / median_close
    )


def compression_score(df, idx):
    """
    Current 5-session price range versus the stock's own prior
    distribution of 5-session ranges.

    A zero historical baseline is treated as an ineligible price regime,
    not as perfect compression.
    """
    current = rolling_range_pct(df, idx)

    historical = np.asarray(
        [
            rolling_range_pct(df, j)
            for j in range(idx - BASELINE, idx)
        ],
        dtype=float,
    )
    historical = historical[np.isfinite(historical)]

    if (
        not np.isfinite(current)
        or len(historical) == 0
    ):
        return {
            "score": 0.0,
            "current_5d_range_pct": None,
            "baseline_5d_range_pct": None,
            "compression_ratio": None,
            "robust_z": None,
            "valid": False,
            "quality_flag": "INVALID_RANGE_DATA",
        }

    med = float(np.median(historical))

    if med <= 1e-12:
        return {
            "score": 0.0,
            "current_5d_range_pct": float(current * 100),
            "baseline_5d_range_pct": float(med * 100),
            "compression_ratio": None,
            "robust_z": None,
            "valid": False,
            "quality_flag": "ZERO_RANGE_BASELINE",
        }

    ratio = float(current / med)
    z = robust_z(current, historical)

    ratio_score = interp_score(
        ratio,
        [
            (0.00, 100.0),
            (0.50, 100.0),
            (0.65, 80.0),
            (0.80, 60.0),
            (0.95, 35.0),
            (1.10, 10.0),
            (1.25, 0.0),
            (5.00, 0.0),
        ],
    )

    z_score = interp_score(
        z,
        [
            (-5.00, 100.0),
            (-2.50, 100.0),
            (-1.50, 75.0),
            (-0.75, 50.0),
            (0.00, 20.0),
            (0.75, 0.0),
            (5.00, 0.0),
        ],
    )

    score = 0.70 * ratio_score + 0.30 * z_score

    return {
        "score": float(score),
        "current_5d_range_pct": float(current * 100),
        "baseline_5d_range_pct": float(med * 100),
        "compression_ratio": ratio,
        "robust_z": float(z),
        "valid": True,
        "quality_flag": None,
    }


def build_broker_features(broker_json_path):
    with open(broker_json_path, "r", encoding="utf-8") as f:
        sessions = json.load(f)

    rows = []

    for session in sessions:
        brokers = session.get("summary", [])
        total_buy = sum((b.get("bval") or 0) for b in brokers)

        positive_nets = sorted(
            [max((b.get("nval") or 0), 0) for b in brokers],
            reverse=True,
        )

        if total_buy > 0:
            top5_net_buy_share = (
                sum(positive_nets[:5]) / total_buy
            )

            buy_hhi = sum(
                ((b.get("bval") or 0) / total_buy) ** 2
                for b in brokers
            )
        else:
            top5_net_buy_share = np.nan
            buy_hhi = np.nan

        rows.append(
            {
                "date": session["date"],
                "top5_net_buy_share": top5_net_buy_share,
                "buy_hhi": buy_hhi,
            }
        )

    out = pd.DataFrame(rows)

    if len(out):
        out["date"] = pd.to_datetime(out["date"])

    return out


def build_foreign_flow(foreign_json_path):
    with open(foreign_json_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    body = obj.get("body", obj)
    data = body.get("data", [])

    out = pd.DataFrame(data)

    if len(out) == 0:
        return pd.DataFrame(
            columns=[
                "date",
                "net_foreign_inflow",
                "foreign_buy_idr",
                "foreign_sell_idr",
                "foreign_share",
            ]
        )

    out["date"] = pd.to_datetime(out["date"])
    return out


def foreign_flow_support(row):
    """
    Supporting/contradicting context only.
    50 is neutral; it is NOT a probability.
    """
    net = row.get("net_foreign_inflow", np.nan)
    turnover = row.get("turnover_idr", np.nan)

    if (
        pd.isna(net)
        or pd.isna(turnover)
        or turnover == 0
    ):
        return 50.0, None

    ratio = float(net / turnover)

    score = interp_score(
        ratio,
        [
            (-1.00, 0.0),
            (-0.30, 0.0),
            (-0.10, 25.0),
            (0.00, 50.0),
            (0.10, 70.0),
            (0.30, 100.0),
            (1.00, 100.0),
        ],
    )

    return float(score), ratio


def evaluate_day(df, idx):
    """
    Computes only per-session observable/derived evidence.
    Investigation state and persistence are added separately.
    """
    minimum_idx = BASELINE + RANGE_WINDOW - 1

    if idx < minimum_idx:
        return None

    current = df.iloc[idx]
    baseline = df.iloc[idx - BASELINE : idx]

    compression = compression_score(df, idx)

    metric_results = {}

    for metric in [
        "turnover_idr",
        "volume",
        "transaction_count",
    ]:
        s, ratio, z = positive_anomaly_score(
            current[metric],
            baseline[metric].to_numpy(),
        )

        metric_results[metric] = {
            "score": s,
            "relative": ratio,
            "robust_z": z,
        }

    activity_score = (
        0.40 * metric_results["turnover_idr"]["score"]
        + 0.30 * metric_results["volume"]["score"]
        + 0.30 * metric_results["transaction_count"]["score"]
    )

    avg_ticket_score, avg_ticket_relative, _ = (
        positive_anomaly_score(
            current["avg_trade_value_idr"],
            baseline["avg_trade_value_idr"].to_numpy(),
        )
    )

    if (
        "top5_net_buy_share" in df.columns
        and not pd.isna(
            current.get("top5_net_buy_share", np.nan)
        )
    ):
        conc_hist = (
            baseline["top5_net_buy_share"]
            .dropna()
            .to_numpy()
        )

        conc_score, conc_relative, _ = (
            positive_anomaly_score(
                current["top5_net_buy_share"],
                conc_hist,
            )
        )

        participation_score = (
            0.60 * avg_ticket_score
            + 0.40 * conc_score
        )
    else:
        conc_relative = None
        participation_score = avg_ticket_score

    flow_score, foreign_net_to_turnover = (
        foreign_flow_support(current)
    )

    core_relatives = [
        metric_results["turnover_idr"]["relative"],
        metric_results["volume"]["relative"],
        metric_results["transaction_count"]["relative"],
    ]

    core_above_threshold = sum(
        (
            np.isfinite(x)
            and x >= MIN_CORE_RELATIVE
        )
        for x in core_relatives
    )

    compression_valid = bool(
        compression.get("valid", True)
    )

    compression_gate = bool(
        compression_valid
        and compression["score"]
        >= MIN_COMPRESSION_SCORE
    )

    activity_gate = bool(
        activity_score >= MIN_ACTIVITY_SCORE
    )

    core_activity_gate = bool(
        core_above_threshold
        >= MIN_CORE_RELATIVE_COUNT
    )

    spot_hit = bool(
        compression_gate
        and activity_gate
        and core_activity_gate
    )

    return {
        "date": current["date"].date().isoformat(),
        "close": float(current["close"]),

        "compression_score": round(
            compression["score"], 2
        ),
        "current_5d_range_pct": (
            round(
                compression["current_5d_range_pct"],
                4,
            )
            if compression["current_5d_range_pct"]
            is not None
            else None
        ),
        "baseline_5d_range_pct": (
            round(
                compression["baseline_5d_range_pct"],
                4,
            )
            if compression["baseline_5d_range_pct"]
            is not None
            else None
        ),
        "compression_ratio": (
            round(
                compression["compression_ratio"],
                4,
            )
            if compression["compression_ratio"]
            is not None
            else None
        ),
        "compression_valid": compression_valid,
        "compression_quality_flag": (
            compression.get("quality_flag")
        ),

        "activity_score": round(
            float(activity_score), 2
        ),
        "relative_turnover": (
            round(
                metric_results[
                    "turnover_idr"
                ]["relative"],
                4,
            )
            if np.isfinite(
                metric_results[
                    "turnover_idr"
                ]["relative"]
            )
            else None
        ),
        "relative_volume": (
            round(
                metric_results[
                    "volume"
                ]["relative"],
                4,
            )
            if np.isfinite(
                metric_results[
                    "volume"
                ]["relative"]
            )
            else None
        ),
        "relative_transaction_count": (
            round(
                metric_results[
                    "transaction_count"
                ]["relative"],
                4,
            )
            if np.isfinite(
                metric_results[
                    "transaction_count"
                ]["relative"]
            )
            else None
        ),

        "participation_score": round(
            float(participation_score), 2
        ),
        "relative_avg_trade_value": (
            round(avg_ticket_relative, 4)
            if np.isfinite(avg_ticket_relative)
            else None
        ),
        "relative_top5_net_buy_share": (
            round(conc_relative, 4)
            if (
                conc_relative is not None
                and np.isfinite(conc_relative)
            )
            else None
        ),

        "flow_support_score": round(
            float(flow_score), 2
        ),
        "foreign_net_to_turnover": (
            round(
                foreign_net_to_turnover,
                4,
            )
            if foreign_net_to_turnover
            is not None
            else None
        ),

        "core_metrics_above_1_20x": int(
            core_above_threshold
        ),

        # Explicit hard-gate diagnostics.
        "compression_gate_pass": compression_gate,
        "activity_gate_pass": activity_gate,
        "core_activity_gate_pass": core_activity_gate,

        "spot_hit": spot_hit,
    }


def state_from_history(timeline):
    """
    Persistence semantics remain frozen from v0.1.1:
    count hard spot hits in the most recent 5 observations.
    """
    if len(timeline) == 0:
        return "INSUFFICIENT_DATA", 0

    recent = timeline[-PERSISTENCE_WINDOW:]

    # Invalid price regimes do not count as hits.
    hits = sum(
        bool(x.get("spot_hit", False))
        for x in recent
    )

    current = recent[-1]

    if not current.get("compression_valid", True):
        return "INELIGIBLE_PRICE_REGIME", hits

    current_hit = bool(
        current.get("spot_hit", False)
    )

    if current_hit:
        if hits >= 4:
            state = "ESTABLISHED"
        elif hits >= 2:
            state = "DEVELOPING"
        else:
            state = "EMERGING"
    else:
        state = (
            "WEAKENING"
            if hits > 0
            else "NO_INVESTIGATION"
        )

    return state, hits


def diagnostic_evidence_score(
    observation,
    persistence_score,
):
    """
    Calculated for every eligible observation.

    This is an internal/diagnostic composite score and MUST NOT be
    presented as the probability that an investigation is true or that
    price will rise.
    """
    if not observation.get(
        "compression_valid", True
    ):
        return None

    score = (
        0.25 * observation["compression_score"]
        + 0.30 * observation["activity_score"]
        + 0.20 * persistence_score
        + 0.15 * observation["participation_score"]
        + 0.10 * observation["flow_support_score"]
    )

    return round(float(score), 2)


def enrich_timeline(timeline, symbol=None):
    """
    v0.2 semantic separation:

    diagnostic_evidence_score:
        computed for every eligible observation.

    evidence_confidence:
        surfaced only while an Investigation is active
        (Emerging, Developing, Established, Weakening).

    Thus a NO_INVESTIGATION row can never display a user-facing
    Evidence Confidence merely because secondary evidence is strong.
    """
    enriched = []

    for idx, item in enumerate(timeline):
        current_history = enriched + [dict(item)]

        state, persistence_hits = (
            state_from_history(current_history)
        )

        persistence_score = (
            persistence_hits
            / PERSISTENCE_WINDOW
            * 100.0
        )

        diagnostic_score = (
            diagnostic_evidence_score(
                item,
                persistence_score,
            )
        )

        investigation_active = (
            state in ACTIVE_STATES
        )

        evidence_confidence = (
            diagnostic_score
            if investigation_active
            else None
        )

        row = dict(item)

        if symbol is not None:
            row["symbol"] = symbol

        row["state"] = state
        row["investigation_active"] = (
            investigation_active
        )
        row["persistence_hits"] = int(
            persistence_hits
        )
        row["persistence_window"] = (
            PERSISTENCE_WINDOW
        )
        row["persistence_score"] = round(
            persistence_score, 2
        )

        row["diagnostic_evidence_score"] = (
            diagnostic_score
        )
        row["evidence_confidence"] = (
            evidence_confidence
        )

        enriched.append(row)

    return enriched


def build_evidence(latest):
    supporting = []
    contradicting = []

    if not latest.get(
        "compression_valid", True
    ):
        contradicting.append(
            "Price compression could not be scored "
            "because the historical 5-session range "
            "baseline was zero or invalid."
        )
    elif latest["compression_gate_pass"]:
        supporting.append(
            f"Price range is compressed: "
            f"{latest['current_5d_range_pct']:.2f}% "
            f"vs "
            f"{latest['baseline_5d_range_pct']:.2f}% "
            f"baseline."
        )
    else:
        contradicting.append(
            f"Price compression gate failed: "
            f"{latest['compression_score']:.1f}/100 "
            f"< {MIN_COMPRESSION_SCORE:.0f}."
        )

    if latest["relative_turnover"] is not None:
        if latest["relative_turnover"] >= MIN_CORE_RELATIVE:
            supporting.append(
                f"Turnover is "
                f"{latest['relative_turnover']:.2f}x "
                f"its 20-session median."
            )
        else:
            contradicting.append(
                f"Turnover is only "
                f"{latest['relative_turnover']:.2f}x "
                f"its 20-session median."
            )

    if (
        latest["relative_volume"] is not None
        and latest["relative_volume"]
        >= MIN_CORE_RELATIVE
    ):
        supporting.append(
            f"Volume is "
            f"{latest['relative_volume']:.2f}x "
            f"its 20-session median."
        )

    if (
        latest[
            "relative_transaction_count"
        ] is not None
        and latest[
            "relative_transaction_count"
        ] >= MIN_CORE_RELATIVE
    ):
        supporting.append(
            f"Transaction count is "
            f"{latest['relative_transaction_count']:.2f}x "
            f"its 20-session median."
        )

    if (
        latest["relative_avg_trade_value"]
        is not None
        and latest[
            "relative_avg_trade_value"
        ] >= 1.20
    ):
        supporting.append(
            f"Average trade value increased to "
            f"{latest['relative_avg_trade_value']:.2f}x "
            f"baseline."
        )

    foreign_ratio = latest.get(
        "foreign_net_to_turnover"
    )

    if (
        foreign_ratio is not None
        and foreign_ratio > 0
    ):
        supporting.append(
            f"Foreign net flow was positive at "
            f"{foreign_ratio:.1%} of turnover."
        )
    elif foreign_ratio is not None:
        contradicting.append(
            f"Foreign net flow was negative at "
            f"{foreign_ratio:.1%} of turnover."
        )

    return supporting, contradicting


def run_detector(
    daily_csv,
    broker_json=None,
    foreign_json=None,
    symbol="UNKNOWN",
):
    df = pd.read_csv(daily_csv)

    df["date"] = pd.to_datetime(df["date"])
    df = (
        df.sort_values("date")
        .reset_index(drop=True)
    )

    required = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "transaction_count",
        "turnover_idr",
        "avg_trade_value_idr",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if broker_json:
        broker_df = build_broker_features(
            broker_json
        )
        df = df.merge(
            broker_df,
            on="date",
            how="left",
        )

    if foreign_json:
        foreign_df = build_foreign_flow(
            foreign_json
        )
        df = df.merge(
            foreign_df,
            on="date",
            how="left",
        )

    raw_timeline = []

    for idx in range(len(df)):
        result = evaluate_day(df, idx)

        if result is not None:
            raw_timeline.append(result)

    if len(raw_timeline) == 0:
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "symbol": symbol,
            "state": "INSUFFICIENT_DATA",
            "message": (
                f"Need at least "
                f"{BASELINE + RANGE_WINDOW} sessions "
                f"to produce the first comparable "
                f"observation."
            ),
            "timeline": [],
        }

    timeline = enrich_timeline(
        raw_timeline,
        symbol=symbol,
    )

    latest = timeline[-1]

    supporting, contradicting = (
        build_evidence(latest)
    )

    result = {
        "methodology_version": METHODOLOGY_VERSION,
        "symbol": symbol,
        "as_of": latest["date"],

        "state": latest["state"],
        "investigation_active": (
            latest["investigation_active"]
        ),
        "spot_hit": latest["spot_hit"],

        "gate_status": {
            "compression_pass": (
                latest[
                    "compression_gate_pass"
                ]
            ),
            "activity_pass": (
                latest["activity_gate_pass"]
            ),
            "core_activity_pass": (
                latest[
                    "core_activity_gate_pass"
                ]
            ),
        },

        "scores": {
            "price_compression": (
                latest["compression_score"]
            ),
            "activity_anomaly": (
                latest["activity_score"]
            ),
            "persistence": (
                latest["persistence_score"]
            ),
            "participation_structure": (
                latest["participation_score"]
            ),
            "flow_support": (
                latest["flow_support_score"]
            ),

            # Internal score: exists for every eligible observation.
            "diagnostic_evidence_score": (
                latest[
                    "diagnostic_evidence_score"
                ]
            ),

            # User-facing only while investigation is active.
            "evidence_confidence": (
                latest["evidence_confidence"]
            ),
        },

        "persistence": {
            "hits": int(
                latest["persistence_hits"]
            ),
            "window": PERSISTENCE_WINDOW,
            "basis": "hard_spot_hits",
        },

        "metrics": {
            "current_5d_range_pct": (
                latest[
                    "current_5d_range_pct"
                ]
            ),
            "baseline_5d_range_pct": (
                latest[
                    "baseline_5d_range_pct"
                ]
            ),
            "compression_ratio": (
                latest["compression_ratio"]
            ),
            "compression_valid": (
                latest["compression_valid"]
            ),
            "compression_quality_flag": (
                latest[
                    "compression_quality_flag"
                ]
            ),

            "relative_turnover": (
                latest["relative_turnover"]
            ),
            "relative_volume": (
                latest["relative_volume"]
            ),
            "relative_transaction_count": (
                latest[
                    "relative_transaction_count"
                ]
            ),
            "relative_avg_trade_value": (
                latest[
                    "relative_avg_trade_value"
                ]
            ),
            "relative_top5_net_buy_share": (
                latest[
                    "relative_top5_net_buy_share"
                ]
            ),
            "foreign_net_to_turnover": (
                latest[
                    "foreign_net_to_turnover"
                ]
            ),
        },

        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting,

        "semantics": {
            "diagnostic_evidence_score": (
                "Internal composite evidence score "
                "calculated for every eligible observation."
            ),
            "evidence_confidence": (
                "User-facing strength of current evidence "
                "only after an Investigation has opened. "
                "It is not a forecast probability."
            ),
        },

        "interpretation_guardrail": (
            "SIGNAL identifies unusual market-behavior "
            "investigations. Scores are not probabilities "
            "of future price direction and are not buy/sell "
            "recommendations."
        ),

        "timeline": timeline,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "SIGNAL Sideways Accumulation Watch "
            "detector v0.2"
        )
    )

    parser.add_argument("--daily", required=True)
    parser.add_argument("--brokers")
    parser.add_argument("--foreign")
    parser.add_argument(
        "--symbol",
        default="UNKNOWN",
    )
    parser.add_argument(
        "--outdir",
        default="signal_detector_output_v0_2",
    )

    args = parser.parse_args()

    result = run_detector(
        daily_csv=args.daily,
        broker_json=args.brokers,
        foreign_json=args.foreign,
        symbol=args.symbol,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        outdir / "latest_investigation_v0_2.json"
    )
    timeline_path = (
        outdir / "detector_timeline_v0_2.csv"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    pd.DataFrame(
        result.get("timeline", [])
    ).to_csv(
        timeline_path,
        index=False,
    )

    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k != "timeline"
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("Saved:")
    print(json_path)
    print(timeline_path)


if __name__ == "__main__":
    main()
