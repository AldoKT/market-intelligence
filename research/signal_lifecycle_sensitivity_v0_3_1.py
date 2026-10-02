
import argparse
import csv
import json
import math
import statistics
import itertools
from collections import Counter, defaultdict
from pathlib import Path


BASELINE = {
    "support_compression": 40.0,
    "close_after_unsupported": 2,
    "established_support_required": 4,
}

SUPPORT_ACTIVITY = 25.0
SUPPORT_CORE_MIN = 1
PERSISTENCE_WINDOW = 5
ESTABLISHED_MIN_HARD_HITS = 2

COMPRESSION_GRID = [35.0, 40.0, 45.0, 50.0]
CLOSE_GRID = [1, 2, 3]
ESTABLISHED_GRID = [3, 4, 5]

ACTIVE_STATES = {"EMERGING", "DEVELOPING", "ESTABLISHED", "WEAKENING"}


def as_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() == "true"


def as_float(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def as_int(v, default=0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except Exception:
        return default


def load_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["compression_valid"] = as_bool(row.get("compression_valid"))
            row["spot_hit"] = as_bool(row.get("spot_hit"))
            row["compression_score"] = as_float(row.get("compression_score"))
            row["activity_score"] = as_float(row.get("activity_score"))
            row["core_metrics_above_1_20x"] = as_int(
                row.get("core_metrics_above_1_20x")
            )
            rows.append(row)

    rows.sort(key=lambda x: (x["symbol"], x["date"]))
    return rows


def supporting_session(row, support_compression):
    if not row["compression_valid"]:
        return False

    if row["spot_hit"]:
        return True

    return bool(
        row["compression_score"] >= support_compression
        and (
            row["activity_score"] >= SUPPORT_ACTIVITY
            or row["core_metrics_above_1_20x"] >= SUPPORT_CORE_MIN
        )
    )


def simulate_symbol(
    rows,
    support_compression,
    close_after_unsupported,
    established_support_required,
):
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

    output = []

    for source in rows:
        row = dict(source)

        valid = row["compression_valid"]
        hard_hit = row["spot_hit"]
        supporting = supporting_session(row, support_compression)

        close_reason = None

        if not active:
            if hard_hit:
                active = True
                sequence += 1
                opened_at = row["date"]
                investigation_id = (
                    f"{row['symbol']}-{row['date'].replace('-', '')}-{sequence:02d}"
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

            recent_support = (recent_support + [int(supporting)])[-PERSISTENCE_WINDOW:]
            recent_hard = (recent_hard + [int(hard_hit)])[-PERSISTENCE_WINDOW:]

            if not valid:
                state = "CLOSED"
                close_reason = "INELIGIBLE_PRICE_REGIME"
                active = False

            elif unsupported_streak >= close_after_unsupported:
                state = "CLOSED"
                close_reason = f"{close_after_unsupported}_UNSUPPORTED_SESSIONS"
                active = False

            elif not supporting:
                state = "WEAKENING"

            else:
                support_in_window = sum(recent_support)

                if (
                    support_in_window >= established_support_required
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

        support_in_window = sum(recent_support) if investigation_id else 0
        hard_in_window = sum(recent_hard) if investigation_id else 0

        investigation_active = state in ACTIVE_STATES

        row["supporting"] = supporting
        row["state_sim"] = state
        row["active_sim"] = investigation_active
        row["investigation_id_sim"] = (
            investigation_id
            if investigation_id is not None
            and (investigation_active or state == "CLOSED")
            else ""
        )
        row["opened_at_sim"] = opened_at or ""
        row["age_sessions_sim"] = (
            age_sessions if row["investigation_id_sim"] else 0
        )
        row["hard_hits_total_sim"] = (
            hard_hits_total if row["investigation_id_sim"] else 0
        )
        row["support_sessions_total_sim"] = (
            support_sessions_total if row["investigation_id_sim"] else 0
        )
        row["support_in_last5_sim"] = support_in_window
        row["hard_in_last5_sim"] = hard_in_window
        row["unsupported_streak_sim"] = (
            unsupported_streak if row["investigation_id_sim"] else 0
        )
        row["close_reason_sim"] = close_reason or ""

        output.append(row)

        if state == "CLOSED":
            investigation_id = None
            opened_at = None
            age_sessions = 0
            hard_hits_total = 0
            support_sessions_total = 0
            unsupported_streak = 0
            recent_support = []
            recent_hard = []

    return output


def simulate_all(
    all_rows,
    support_compression,
    close_after_unsupported,
    established_support_required,
):
    by_symbol = defaultdict(list)
    for row in all_rows:
        by_symbol[row["symbol"]].append(row)

    output = []
    for symbol in sorted(by_symbol):
        output.extend(
            simulate_symbol(
                by_symbol[symbol],
                support_compression,
                close_after_unsupported,
                established_support_required,
            )
        )

    output.sort(key=lambda x: (x["symbol"], x["date"]))
    return output


def build_episodes(sim_rows):
    linked = defaultdict(list)

    for row in sim_rows:
        inv = row["investigation_id_sim"]
        if inv:
            linked[inv].append(row)

    episodes = []

    for inv, rows in linked.items():
        rows.sort(key=lambda x: x["date"])
        active_rows = [r for r in rows if r["state_sim"] in ACTIVE_STATES]
        if not active_rows:
            continue

        states = {r["state_sim"] for r in active_rows}

        if "ESTABLISHED" in states:
            peak = "ESTABLISHED"
        elif "DEVELOPING" in states:
            peak = "DEVELOPING"
        else:
            peak = "EMERGING"

        episodes.append(
            {
                "investigation_id": inv,
                "symbol": rows[0]["symbol"],
                "opened_at": active_rows[0]["date"],
                "last_linked_at": rows[-1]["date"],
                "active_sessions": len(active_rows),
                "linked_sessions": len(rows),
                "hard_hits": sum(int(r["spot_hit"]) for r in rows),
                "support_sessions": sum(int(r["supporting"]) for r in rows),
                "peak_state": peak,
                "closed": any(r["state_sim"] == "CLOSED" for r in rows),
            }
        )

    episodes.sort(key=lambda x: (x["opened_at"], x["symbol"]))
    return episodes


def pct(n, d):
    return n / d if d else 0.0


def median_safe(values):
    return statistics.median(values) if values else 0.0


def mean_safe(values):
    return statistics.mean(values) if values else 0.0


def summarize_config(
    sim_rows,
    episodes,
    eligible_count,
):
    state_counts = Counter(r["state_sim"] for r in sim_rows)

    active_sessions = sum(int(r["active_sim"]) for r in sim_rows)

    peak_counts = Counter(e["peak_state"] for e in episodes)

    one_hit = [e for e in episodes if e["hard_hits"] == 1]
    multi_hit = [e for e in episodes if e["hard_hits"] >= 2]

    durations = [e["active_sessions"] for e in episodes]
    linked = [e["linked_sessions"] for e in episodes]

    return {
        "episodes": len(episodes),
        "active_sessions": active_sessions,
        "active_share_eligible": pct(active_sessions, eligible_count),

        "state_no_investigation": state_counts.get("NO_INVESTIGATION", 0),
        "state_emerging": state_counts.get("EMERGING", 0),
        "state_developing": state_counts.get("DEVELOPING", 0),
        "state_established": state_counts.get("ESTABLISHED", 0),
        "state_weakening": state_counts.get("WEAKENING", 0),
        "state_closed": state_counts.get("CLOSED", 0),
        "state_ineligible": state_counts.get("INELIGIBLE_PRICE_REGIME", 0),

        "peak_emerging_episodes": peak_counts.get("EMERGING", 0),
        "peak_developing_episodes": peak_counts.get("DEVELOPING", 0),
        "peak_established_episodes": peak_counts.get("ESTABLISHED", 0),

        "single_hit_episodes": len(one_hit),
        "multi_hit_episodes": len(multi_hit),
        "single_hit_episode_share": pct(len(one_hit), len(episodes)),

        "mean_active_sessions_per_episode": mean_safe(durations),
        "median_active_sessions_per_episode": median_safe(durations),
        "max_active_sessions_per_episode": max(durations) if durations else 0,

        "mean_linked_sessions_per_episode": mean_safe(linked),
        "median_linked_sessions_per_episode": median_safe(linked),

        "mean_active_sessions_single_hit_episode": mean_safe(
            [e["active_sessions"] for e in one_hit]
        ),
        "median_active_sessions_single_hit_episode": median_safe(
            [e["active_sessions"] for e in one_hit]
        ),
    }


def active_agreement(candidate, baseline):
    cand = {
        (r["symbol"], r["date"]): bool(r["active_sim"])
        for r in candidate
    }
    base = {
        (r["symbol"], r["date"]): bool(r["active_sim"])
        for r in baseline
    }

    keys = sorted(set(cand) & set(base))
    if not keys:
        return 0.0

    return sum(cand[k] == base[k] for k in keys) / len(keys)


def state_agreement(candidate, baseline):
    cand = {
        (r["symbol"], r["date"]): r["state_sim"]
        for r in candidate
    }
    base = {
        (r["symbol"], r["date"]): r["state_sim"]
        for r in baseline
    }

    keys = sorted(set(cand) & set(base))
    if not keys:
        return 0.0

    return sum(cand[k] == base[k] for k in keys) / len(keys)


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Offline sensitivity audit for SIGNAL v0.3.1 lifecycle parameters."
        )
    )
    parser.add_argument("--timeline", required=True)
    parser.add_argument(
        "--outdir",
        default="signal_lifecycle_sensitivity_output",
    )
    args = parser.parse_args()

    all_rows = load_rows(args.timeline)

    eligible_count = sum(int(r["compression_valid"]) for r in all_rows)
    spot_hits = sum(
        int(r["spot_hit"])
        for r in all_rows
        if r["compression_valid"]
    )

    baseline_sim = simulate_all(
        all_rows,
        BASELINE["support_compression"],
        BASELINE["close_after_unsupported"],
        BASELINE["established_support_required"],
    )
    baseline_episodes = build_episodes(baseline_sim)
    baseline_metrics = summarize_config(
        baseline_sim,
        baseline_episodes,
        eligible_count,
    )

    grid_rows = []

    for comp, close_n, est_n in itertools.product(
        COMPRESSION_GRID,
        CLOSE_GRID,
        ESTABLISHED_GRID,
    ):
        sim = simulate_all(
            all_rows,
            comp,
            close_n,
            est_n,
        )
        episodes = build_episodes(sim)
        metrics = summarize_config(
            sim,
            episodes,
            eligible_count,
        )

        row = {
            "support_compression": comp,
            "close_after_unsupported": close_n,
            "established_support_required": est_n,
            "is_baseline": (
                comp == BASELINE["support_compression"]
                and close_n == BASELINE["close_after_unsupported"]
                and est_n == BASELINE["established_support_required"]
            ),
            **metrics,
            "active_agreement_vs_baseline": active_agreement(sim, baseline_sim),
            "state_agreement_vs_baseline": state_agreement(sim, baseline_sim),
            "episode_delta_vs_baseline": (
                metrics["episodes"] - baseline_metrics["episodes"]
            ),
            "active_session_delta_vs_baseline": (
                metrics["active_sessions"] - baseline_metrics["active_sessions"]
            ),
            "established_episode_delta_vs_baseline": (
                metrics["peak_established_episodes"]
                - baseline_metrics["peak_established_episodes"]
            ),
        }
        grid_rows.append(row)

    # Local neighborhood around baseline: exactly one parameter-step away or baseline itself.
    local = []
    for row in grid_rows:
        comp_steps = abs(row["support_compression"] - 40.0) / 5.0
        close_steps = abs(row["close_after_unsupported"] - 2)
        est_steps = abs(row["established_support_required"] - 4)

        total_steps = comp_steps + close_steps + est_steps

        if total_steps <= 1:
            local.append(row)

    # Stability envelope of immediate neighboring configurations.
    local_nonbase = [r for r in local if not r["is_baseline"]]

    def envelope(field):
        vals = [r[field] for r in local_nonbase]
        return {
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
            "median": statistics.median(vals) if vals else None,
        }

    summary = {
        "audit_version": "0.1.0",
        "input": {
            "rows": len(all_rows),
            "eligible_rows": eligible_count,
            "spot_hits": spot_hits,
            "grid_combinations": len(grid_rows),
        },
        "fixed_parameters": {
            "support_activity_min": SUPPORT_ACTIVITY,
            "support_core_metrics_min": SUPPORT_CORE_MIN,
            "persistence_window": PERSISTENCE_WINDOW,
            "established_min_hard_hits": ESTABLISHED_MIN_HARD_HITS,
        },
        "baseline": {
            **BASELINE,
            **baseline_metrics,
        },
        "immediate_neighbor_envelope": {
            "episodes": envelope("episodes"),
            "active_sessions": envelope("active_sessions"),
            "active_share_eligible": envelope("active_share_eligible"),
            "peak_established_episodes": envelope("peak_established_episodes"),
            "single_hit_episode_share": envelope("single_hit_episode_share"),
            "active_agreement_vs_baseline": envelope(
                "active_agreement_vs_baseline"
            ),
            "state_agreement_vs_baseline": envelope(
                "state_agreement_vs_baseline"
            ),
        },
        "interpretation": {
            "purpose": (
                "Measure lifecycle sensitivity and parameter stability, not "
                "optimize for future returns or maximize/minimize alert counts."
            ),
            "baseline_is_stable_if": (
                "Nearby parameter settings produce similar episode density and "
                "high active/state agreement without extreme changes in "
                "Established frequency or single-hit episode persistence."
            ),
        },
    }

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    grid_path = outdir / "lifecycle_sensitivity_grid.csv"
    local_path = outdir / "baseline_neighborhood.csv"
    summary_path = outdir / "lifecycle_sensitivity_summary.json"
    baseline_episode_path = outdir / "baseline_episode_audit.csv"

    grid_fields = list(grid_rows[0].keys())
    write_csv(grid_path, grid_rows, grid_fields)

    write_csv(local_path, local, grid_fields)

    episode_fields = [
        "investigation_id",
        "symbol",
        "opened_at",
        "last_linked_at",
        "active_sessions",
        "linked_sessions",
        "hard_hits",
        "support_sessions",
        "peak_state",
        "closed",
    ]
    write_csv(
        baseline_episode_path,
        baseline_episodes,
        episode_fields,
    )

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print()
    print("Saved:")
    print(grid_path)
    print(local_path)
    print(summary_path)
    print(baseline_episode_path)


if __name__ == "__main__":
    main()
