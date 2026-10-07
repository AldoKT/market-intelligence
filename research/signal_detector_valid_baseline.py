"""Experimental activity-only baseline. Original price/volume calendar is retained."""
from research.signal_detector_v0_2 import *
def evaluate_day(df, idx, activity_history):
    """
    Computes only per-session observable/derived evidence.
    Investigation state and persistence are added separately.
    """
    minimum_idx = BASELINE + RANGE_WINDOW - 1

    if idx < minimum_idx:
        return None

    current = df.iloc[idx]
    baseline = activity_history
    volume_baseline = df.iloc[idx - BASELINE : idx]

    compression = compression_score(df, idx)

    metric_results = {}

    for metric in [
        "turnover_idr",
        "volume",
        "transaction_count",
    ]:
        s, ratio, z = positive_anomaly_score(
            current[metric],
            (volume_baseline if metric == "volume" else baseline)[metric].to_numpy(),
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
