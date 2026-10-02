
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


METHODOLOGY_VERSION = "0.3.1"

# ---------------------------------------------------------------------
# v0.3 Context Specificity — provisional research parameters
# ---------------------------------------------------------------------

MARKET_WIDE_BREADTH = 0.50
PEER_CLUSTER_BREADTH = 0.50

STOCK_SPECIFIC_SCORE = 65.0
MARKET_WIDE_MAX_SPECIFICITY = 40.0
PEER_CLUSTER_MAX_SPECIFICITY = 55.0

MIN_PEERS_FOR_WEIGHTED_CONTEXT = 2


# ---------------------------------------------------------------------
# v0.3 Persistence / lifecycle — provisional research parameters
# ---------------------------------------------------------------------

# Hard spot gate remains exactly the v0.2 result in input column `spot_hit`.
# These are deliberately softer continuation thresholds. They CANNOT open
# an investigation; they only decide whether an already-open investigation
# still has meaningful continuity of evidence.
SUPPORT_MIN_COMPRESSION = 40.0
SUPPORT_MIN_ACTIVITY = 25.0
SUPPORT_MIN_CORE_METRICS = 1

PERSISTENCE_WINDOW = 5
ESTABLISHED_MIN_SUPPORT_IN_WINDOW = 4
ESTABLISHED_MIN_HARD_HITS_IN_EPISODE = 2

CLOSE_AFTER_UNSUPPORTED_SESSIONS = 2

ACTIVE_STATES = {
    "EMERGING",
    "DEVELOPING",
    "ESTABLISHED",
    "WEAKENING",
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _bool_series(series):
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
        .fillna(False)
    )


def load_universe(path):
    df = pd.read_csv(path)

    required = {"symbol", "peer_group"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Universe file is missing required columns: {sorted(missing)}"
        )

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )

    return df[["symbol", "peer_group"]].drop_duplicates("symbol")


def empirical_percentile(value, comparison):
    arr = pd.Series(comparison).dropna().astype(float)

    if len(arr) == 0 or pd.isna(value):
        return np.nan

    # Fraction at or below current value. Simple and transparent.
    return float((arr <= float(value)).mean())


# ---------------------------------------------------------------------
# Context Specificity
# ---------------------------------------------------------------------

def add_context_specificity(timeline, universe):
    df = timeline.copy()

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    df["date"] = pd.to_datetime(df["date"])

    df = df.merge(universe, on="symbol", how="left")

    if df["peer_group"].isna().any():
        missing_symbols = sorted(
            df.loc[df["peer_group"].isna(), "symbol"].unique().tolist()
        )
        raise ValueError(
            "No peer_group mapping for: " + ", ".join(missing_symbols)
        )

    df["compression_valid"] = _bool_series(df["compression_valid"])
    df["activity_gate_pass"] = _bool_series(df["activity_gate_pass"])
    df["spot_hit"] = _bool_series(df["spot_hit"])

    # Eligible observations only are allowed to define market/peer context.
    eligible = df[df["compression_valid"]].copy()

    market_rows = []

    for dt, g in eligible.groupby("date", sort=True):
        activity = g["activity_score"].astype(float)

        market_rows.append(
            {
                "date": dt,
                "market_eligible_count": int(len(g)),
                "market_activity_median": float(activity.median()),
                "market_activity_p75": float(activity.quantile(0.75)),
                "market_activity_gate_count": int(
                    g["activity_gate_pass"].sum()
                ),
                "market_activity_breadth": float(
                    g["activity_gate_pass"].mean()
                ),
                "market_spot_hit_count": int(g["spot_hit"].sum()),
                "market_spot_hit_breadth": float(g["spot_hit"].mean()),
            }
        )

    market_daily = pd.DataFrame(market_rows)

    df = df.merge(
        market_daily[
            [
                "date",
                "market_eligible_count",
                "market_activity_median",
                "market_activity_p75",
                "market_activity_gate_count",
                "market_activity_breadth",
                "market_spot_hit_count",
                "market_spot_hit_breadth",
            ]
        ],
        on="date",
        how="left",
    )

    # Row-wise market percentile and peer context.
    market_pct = {}
    peer_count = {}
    peer_median = {}
    peer_breadth = {}
    peer_pct = {}
    peer_quality = {}

    eligible_by_date = {
        dt: g.copy()
        for dt, g in eligible.groupby("date", sort=False)
    }

    for idx, row in df.iterrows():
        if not bool(row["compression_valid"]):
            market_pct[idx] = np.nan
            peer_count[idx] = 0
            peer_median[idx] = np.nan
            peer_breadth[idx] = np.nan
            peer_pct[idx] = np.nan
            peer_quality[idx] = "INELIGIBLE"
            continue

        day = eligible_by_date.get(row["date"])

        if day is None or len(day) == 0:
            market_pct[idx] = np.nan
            peer_count[idx] = 0
            peer_median[idx] = np.nan
            peer_breadth[idx] = np.nan
            peer_pct[idx] = np.nan
            peer_quality[idx] = "NO_CONTEXT"
            continue

        market_pct[idx] = empirical_percentile(
            row["activity_score"],
            day["activity_score"],
        )

        peers = day[
            (day["peer_group"] == row["peer_group"])
            & (day["symbol"] != row["symbol"])
        ]

        n_peers = int(len(peers))
        peer_count[idx] = n_peers

        if n_peers == 0:
            peer_median[idx] = np.nan
            peer_breadth[idx] = np.nan
            peer_pct[idx] = np.nan
            peer_quality[idx] = "NONE"
        else:
            peer_median[idx] = float(peers["activity_score"].median())
            peer_breadth[idx] = float(peers["activity_gate_pass"].mean())
            peer_pct[idx] = empirical_percentile(
                row["activity_score"],
                peers["activity_score"],
            )

            peer_quality[idx] = (
                "GOOD"
                if n_peers >= MIN_PEERS_FOR_WEIGHTED_CONTEXT
                else "THIN"
            )

    df["market_activity_percentile"] = pd.Series(market_pct)
    df["peer_count"] = pd.Series(peer_count).astype("Int64")
    df["peer_activity_median"] = pd.Series(peer_median)
    df["peer_activity_breadth"] = pd.Series(peer_breadth)
    df["peer_activity_percentile"] = pd.Series(peer_pct)
    df["peer_context_quality"] = pd.Series(peer_quality)

    # Distinctiveness rewards being unusual relative to the same day while
    # penalizing days when unusual activity is broad across the universe.
    df["market_distinctiveness"] = (
        df["market_activity_percentile"]
        * (1.0 - df["market_activity_breadth"])
    )

    df["peer_distinctiveness"] = (
        df["peer_activity_percentile"]
        * (1.0 - df["peer_activity_breadth"])
    )

    use_peer = (
        df["compression_valid"]
        & (df["peer_count"].fillna(0) >= MIN_PEERS_FOR_WEIGHTED_CONTEXT)
        & df["peer_distinctiveness"].notna()
    )

    df["context_specificity_score_raw"] = np.where(
        use_peer,
        100.0
        * (
            0.60 * df["market_distinctiveness"]
            + 0.40 * df["peer_distinctiveness"]
        ),
        100.0 * df["market_distinctiveness"],
    )

    # Context Specificity only has user-facing meaning when there is at least
    # some activity evidence to contextualize. Without this guard, a quiet
    # stock can rank highly merely because every other stock is also quiet.
    df["context_applicable"] = (
        df["compression_valid"]
        & (
            (df["activity_score"] >= SUPPORT_MIN_ACTIVITY)
            | (
                df["core_metrics_above_1_20x"]
                >= SUPPORT_MIN_CORE_METRICS
            )
        )
    )

    df["context_specificity_score"] = np.where(
        df["context_applicable"],
        df["context_specificity_score_raw"],
        np.nan,
    )

    df.loc[
        ~df["compression_valid"],
        ["context_specificity_score_raw", "context_specificity_score"],
    ] = np.nan

    def classify_context(row):
        if not bool(row["compression_valid"]):
            return "INELIGIBLE"

        if not bool(row["context_applicable"]):
            return "NO_ACTIVITY_CONTEXT"

        score = row["context_specificity_score"]
        market_breadth = row["market_activity_breadth"]
        p_breadth = row["peer_activity_breadth"]
        n_peers = row["peer_count"]

        if pd.isna(score):
            return "NO_CONTEXT"

        if (
            pd.notna(market_breadth)
            and market_breadth >= MARKET_WIDE_BREADTH
            and score < MARKET_WIDE_MAX_SPECIFICITY
        ):
            return "MARKET_WIDE_ACTIVITY"

        if (
            pd.notna(n_peers)
            and int(n_peers) >= MIN_PEERS_FOR_WEIGHTED_CONTEXT
            and pd.notna(p_breadth)
            and p_breadth >= PEER_CLUSTER_BREADTH
            and score < PEER_CLUSTER_MAX_SPECIFICITY
        ):
            return "PEER_CLUSTERED_ACTIVITY"

        if score >= STOCK_SPECIFIC_SCORE:
            return "STOCK_SPECIFIC_ACTIVITY"

        return "MIXED_CONTEXT"

    df["context_scope"] = df.apply(classify_context, axis=1)

    return df, market_daily


# ---------------------------------------------------------------------
# Persistence v2 + lifecycle
# ---------------------------------------------------------------------

def is_supporting_session(row):
    """
    Soft support may CONTINUE an already-open investigation but can never
    open a new one.

    Support requires moderate price compression plus either:
      - moderate activity anomaly, or
      - at least one core activity metric still >= 1.20x baseline.

    A hard spot hit is always a supporting session.
    """
    if not bool(row["compression_valid"]):
        return False

    if bool(row["spot_hit"]):
        return True

    return bool(
        float(row["compression_score"]) >= SUPPORT_MIN_COMPRESSION
        and (
            float(row["activity_score"]) >= SUPPORT_MIN_ACTIVITY
            or int(row["core_metrics_above_1_20x"])
            >= SUPPORT_MIN_CORE_METRICS
        )
    )


def diagnostic_score_v3(row, persistence_score_v2):
    if not bool(row["compression_valid"]):
        return np.nan

    return float(
        0.25 * float(row["compression_score"])
        + 0.30 * float(row["activity_score"])
        + 0.20 * float(persistence_score_v2)
        + 0.15 * float(row["participation_score"])
        + 0.10 * float(row["flow_support_score"])
    )


def apply_lifecycle_for_symbol(symbol_df):
    g = symbol_df.sort_values("date").copy()

    out_rows = []

    active = False
    sequence = 0

    investigation_id = None
    opened_at = None
    age_sessions = 0

    hard_hits_total = 0
    support_sessions_total = 0
    unsupported_streak = 0

    recent_support = []
    recent_hard = []

    for _, source_row in g.iterrows():
        row = source_row.copy()

        valid = bool(row["compression_valid"])
        hard_hit = bool(row["spot_hit"])
        supporting = is_supporting_session(row)

        close_reason = None

        # -------------------------------------------------------------
        # No active investigation
        # -------------------------------------------------------------
        if not active:
            if hard_hit:
                active = True
                sequence += 1

                opened_at = row["date"]
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

                lifecycle_state = "EMERGING"

            else:
                lifecycle_state = (
                    "INELIGIBLE_PRICE_REGIME"
                    if not valid
                    else "NO_INVESTIGATION"
                )

                age_sessions = 0

        # -------------------------------------------------------------
        # Existing investigation
        # -------------------------------------------------------------
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
                lifecycle_state = "CLOSED"
                close_reason = "INELIGIBLE_PRICE_REGIME"
                active = False

            elif unsupported_streak >= CLOSE_AFTER_UNSUPPORTED_SESSIONS:
                lifecycle_state = "CLOSED"
                close_reason = "TWO_UNSUPPORTED_SESSIONS"
                active = False

            elif not supporting:
                lifecycle_state = "WEAKENING"

            else:
                support_in_window = int(sum(recent_support))

                if (
                    support_in_window
                    >= ESTABLISHED_MIN_SUPPORT_IN_WINDOW
                    and hard_hits_total
                    >= ESTABLISHED_MIN_HARD_HITS_IN_EPISODE
                ):
                    lifecycle_state = "ESTABLISHED"

                elif (
                    support_in_window >= 2
                    or hard_hits_total >= 2
                ):
                    lifecycle_state = "DEVELOPING"

                else:
                    lifecycle_state = "EMERGING"

        # -------------------------------------------------------------
        # Persistence score v2
        # -------------------------------------------------------------
        if investigation_id is not None:
            support_in_window = int(sum(recent_support))
            hard_in_window = int(sum(recent_hard))

            persistence_score_v2 = (
                support_in_window
                / PERSISTENCE_WINDOW
                * 100.0
            )
        else:
            support_in_window = 0
            hard_in_window = 0
            persistence_score_v2 = 0.0

        diag_v3 = diagnostic_score_v3(
            row,
            persistence_score_v2,
        )

        investigation_active = lifecycle_state in ACTIVE_STATES

        # Evidence Confidence is user-facing only while lifecycle is active.
        evidence_confidence_v3 = (
            diag_v3
            if investigation_active and np.isfinite(diag_v3)
            else np.nan
        )

        row["supporting_session_v2"] = bool(supporting)
        row["lifecycle_state_v2"] = lifecycle_state
        row["investigation_active_v2"] = bool(investigation_active)

        # Keep the ID on the CLOSED row so History can link the closure event.
        row["investigation_id"] = (
            investigation_id
            if (
                investigation_id is not None
                and (
                    investigation_active
                    or lifecycle_state == "CLOSED"
                )
            )
            else None
        )

        row["investigation_opened_at"] = (
            opened_at
            if row["investigation_id"] is not None
            else pd.NaT
        )

        row["investigation_age_sessions"] = (
            int(age_sessions)
            if row["investigation_id"] is not None
            else 0
        )

        row["hard_hits_total_in_episode"] = (
            int(hard_hits_total)
            if row["investigation_id"] is not None
            else 0
        )

        row["support_sessions_total_in_episode"] = (
            int(support_sessions_total)
            if row["investigation_id"] is not None
            else 0
        )

        row["support_sessions_in_last_5"] = int(support_in_window)
        row["hard_hits_in_last_5"] = int(hard_in_window)
        row["unsupported_streak"] = (
            int(unsupported_streak)
            if row["investigation_id"] is not None
            else 0
        )

        row["persistence_score_v2"] = round(
            float(persistence_score_v2), 2
        )

        row["diagnostic_evidence_score_v3"] = (
            round(float(diag_v3), 2)
            if np.isfinite(diag_v3)
            else np.nan
        )

        row["evidence_confidence_v3"] = (
            round(float(evidence_confidence_v3), 2)
            if np.isfinite(evidence_confidence_v3)
            else np.nan
        )

        row["close_reason"] = close_reason

        out_rows.append(row)

        # Reset AFTER recording the CLOSED row.
        if lifecycle_state == "CLOSED":
            investigation_id = None
            opened_at = None
            age_sessions = 0

            hard_hits_total = 0
            support_sessions_total = 0
            unsupported_streak = 0

            recent_support = []
            recent_hard = []

    return pd.DataFrame(out_rows)


def add_lifecycle(df):
    frames = []

    for _, g in df.groupby("symbol", sort=True):
        frames.append(apply_lifecycle_for_symbol(g))

    result = pd.concat(frames, ignore_index=True)

    return result.sort_values(["symbol", "date"]).reset_index(drop=True)


# ---------------------------------------------------------------------
# Episode table
# ---------------------------------------------------------------------

def build_episode_table(df):
    linked = df[df["investigation_id"].notna()].copy()

    rows = []

    for investigation_id, g in linked.groupby("investigation_id"):
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

        rows.append(
            {
                "investigation_id": investigation_id,
                "symbol": g["symbol"].iloc[0],
                "peer_group": g["peer_group"].iloc[0],

                "opened_at": open_row["date"].date().isoformat(),
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
                "support_sessions": int(g["supporting_session_v2"].sum()),
                "peak_state": peak_state,

                "open_context_scope": open_row["context_scope"],
                "open_context_specificity_score": (
                    round(
                        float(open_row["context_specificity_score"]),
                        2,
                    )
                    if pd.notna(open_row["context_specificity_score"])
                    else np.nan
                ),
                "open_market_activity_breadth": (
                    round(float(open_row["market_activity_breadth"]), 4)
                    if pd.notna(open_row["market_activity_breadth"])
                    else np.nan
                ),
                "open_peer_activity_breadth": (
                    round(float(open_row["peer_activity_breadth"]), 4)
                    if pd.notna(open_row["peer_activity_breadth"])
                    else np.nan
                ),

                "max_evidence_confidence_v3": (
                    float(active_rows["evidence_confidence_v3"].max())
                    if active_rows["evidence_confidence_v3"].notna().any()
                    else np.nan
                ),
                "max_context_specificity_score": (
                    float(active_rows["context_specificity_score"].max())
                    if active_rows["context_specificity_score"].notna().any()
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["opened_at", "symbol"]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------

def build_summary(df, episodes):
    eligible = df[df["compression_valid"]].copy()

    state_counts = (
        df["lifecycle_state_v2"]
        .value_counts(dropna=False)
        .to_dict()
    )

    context_hits = (
        eligible.loc[eligible["spot_hit"], "context_scope"]
        .value_counts(dropna=False)
        .to_dict()
    )

    return {
        "methodology_version": METHODOLOGY_VERSION,

        "observations": {
            "total_rows": int(len(df)),
            "eligible_rows": int(len(eligible)),
            "ineligible_rows": int((~df["compression_valid"]).sum()),
            "symbols": int(df["symbol"].nunique()),
            "eligible_symbols": int(eligible["symbol"].nunique()),
        },

        "spot_detection": {
            "spot_hits": int(eligible["spot_hit"].sum()),
            "spot_hit_rate": float(eligible["spot_hit"].mean()),
        },

        "lifecycle": {
            "episodes": int(episodes["investigation_id"].nunique())
            if len(episodes)
            else 0,
            "state_counts": {
                str(k): int(v)
                for k, v in state_counts.items()
            },
            "episode_peak_state_counts": (
                {
                    str(k): int(v)
                    for k, v in episodes["peak_state"]
                    .value_counts()
                    .to_dict()
                    .items()
                }
                if len(episodes)
                else {}
            ),
        },

        "context_on_spot_hits": {
            str(k): int(v)
            for k, v in context_hits.items()
        },

        "guardrails": [
            "v0.3 does not change the v0.2 hard Spot gate.",
            "Soft supporting sessions can continue an investigation but can never open one.",
            "Context Specificity is descriptive evidence and is not a buy/sell signal.",
            "Evidence Confidence is shown only while an investigation lifecycle is active.",
            "All v0.3 thresholds remain provisional until reviewed across broader periods/universes.",
        ],
    }


def methodology_payload():
    return {
        "methodology_version": METHODOLOGY_VERSION,

        "context_specificity": {
            "market_activity_breadth": (
                "Share of eligible universe passing the v0.2 activity gate "
                "on the same session."
            ),
            "market_activity_percentile": (
                "Ticker activity-score percentile within the eligible universe "
                "on the same session."
            ),
            "applicability_guard": (
                "User-facing Context Specificity is only shown when the ticker "
                "has meaningful activity evidence: activity_score >= 25 or at "
                "least one core activity metric >= 1.20x baseline. Otherwise "
                "context_scope is NO_ACTIVITY_CONTEXT."
            ),
            "peer_context": (
                "Same calculations within a custom research peer_group, "
                "excluding the ticker itself."
            ),
            "specificity_formula": (
                "If >=2 peers exist: "
                "100 * [0.60 * market_percentile * (1-market_breadth) "
                "+ 0.40 * peer_percentile * (1-peer_breadth)]. "
                "Otherwise market component only."
            ),
            "context_scope_thresholds": {
                "MARKET_WIDE_BREADTH": MARKET_WIDE_BREADTH,
                "PEER_CLUSTER_BREADTH": PEER_CLUSTER_BREADTH,
                "STOCK_SPECIFIC_SCORE": STOCK_SPECIFIC_SCORE,
                "MARKET_WIDE_MAX_SPECIFICITY": MARKET_WIDE_MAX_SPECIFICITY,
                "PEER_CLUSTER_MAX_SPECIFICITY": PEER_CLUSTER_MAX_SPECIFICITY,
            },
        },

        "persistence_v2": {
            "hard_open_condition": "Existing v0.2 spot_hit == True.",
            "supporting_session": {
                "compression_score_min": SUPPORT_MIN_COMPRESSION,
                "and_one_of": {
                    "activity_score_min": SUPPORT_MIN_ACTIVITY,
                    "core_metrics_above_1_20x_min": SUPPORT_MIN_CORE_METRICS,
                },
            },
            "persistence_window": PERSISTENCE_WINDOW,
            "established_requires": {
                "support_sessions_in_last_5_min": (
                    ESTABLISHED_MIN_SUPPORT_IN_WINDOW
                ),
                "hard_hits_in_episode_min": (
                    ESTABLISHED_MIN_HARD_HITS_IN_EPISODE
                ),
            },
        },

        "lifecycle": {
            "EMERGING": "Investigation just opened from a hard spot hit.",
            "DEVELOPING": (
                "Evidence continues: >=2 support sessions in recent window "
                "or >=2 hard hits in the episode."
            ),
            "ESTABLISHED": (
                "At least 4/5 recent sessions support the hypothesis and "
                "the episode contains at least 2 hard spot hits."
            ),
            "WEAKENING": (
                "Current session no longer meets soft support, but this is "
                "the first unsupported session."
            ),
            "CLOSED": (
                "Second consecutive unsupported session, or price regime "
                "becomes ineligible."
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "SIGNAL v0.3 research engine: cross-sectional context specificity, "
            "Persistence v2, and investigation lifecycle."
        )
    )

    parser.add_argument("--timeline", required=True)
    parser.add_argument("--universe", required=True)
    parser.add_argument(
        "--outdir",
        default="signal_v0_3_output",
    )

    args = parser.parse_args()

    timeline = pd.read_csv(args.timeline)
    universe = load_universe(args.universe)

    required = {
        "date",
        "symbol",
        "compression_valid",
        "compression_score",
        "activity_score",
        "participation_score",
        "flow_support_score",
        "core_metrics_above_1_20x",
        "activity_gate_pass",
        "spot_hit",
    }

    missing = required - set(timeline.columns)

    if missing:
        raise ValueError(
            f"Timeline is missing required columns: {sorted(missing)}"
        )

    timeline["date"] = pd.to_datetime(timeline["date"])

    contextual, market_daily = add_context_specificity(
        timeline,
        universe,
    )

    v03 = add_lifecycle(contextual)
    episodes = build_episode_table(v03)
    summary = build_summary(v03, episodes)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    timeline_path = outdir / "cross_stock_timeline_v0_3.csv"
    episodes_path = outdir / "investigation_episodes_v0_3.csv"
    market_path = outdir / "market_context_daily_v0_3.csv"
    summary_path = outdir / "v0_3_summary.json"
    method_path = outdir / "methodology_v0_3.json"

    v03.to_csv(timeline_path, index=False)
    episodes.to_csv(episodes_path, index=False)
    market_daily.to_csv(market_path, index=False)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open(method_path, "w", encoding="utf-8") as f:
        json.dump(methodology_payload(), f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print()
    print("Saved:")
    print(timeline_path)
    print(episodes_path)
    print(market_path)
    print(summary_path)
    print(method_path)


if __name__ == "__main__":
    main()
