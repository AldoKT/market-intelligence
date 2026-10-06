# SIGNAL Validation Report v1

This report validates implementation correctness, point-in-time behavior, product-payload fidelity, and retrospective empirical separation. It does **not** claim labeled classification accuracy for 'institutional accumulation', because no independent ground-truth label set exists in the current project.

## Executive result

- **Implementation correctness:** PASS
- **Point-in-time calculation validity:** PASS
- **Product payload validity:** PASS
- **Data quality:** PASS_WITH_WARNINGS
- **External / methodology validity:** PARTIAL_RETROSPECTIVE_SUPPORT; OUT_OF_SAMPLE_PENDING
- **Price-prediction accuracy:** NOT_ESTABLISHED; SIGNAL IS NOT VALIDATED AS A PRICE-DIRECTION MODEL

## Dataset under test

- 2100 evaluated rows across 28 tickers and 75 evaluation dates.
- 2025 eligible observations, 63 hard Spot hits, 49 investigation episodes.
- Evaluation timeline: 2026-06-12 to 2026-09-29.

## What passed

- **DATA_UNIQUE_SYMBOL_DATE** — PASS; 2100 observations checked, 0 mismatches.
- **SPOT_GATE_PARITY** — PASS; 2100 observations checked, 0 mismatches.
- **CONTEXT_FORMULA_PARITY** — PASS; 2100 observations checked, 0 mismatches.
- **LIFECYCLE_STATE_MACHINE_PARITY** — PASS; 2100 observations checked, 0 mismatches.
- **EVIDENCE_CONFIDENCE_VISIBILITY** — PASS; 2100 observations checked, 0 mismatches.
- **EPISODE_TABLE_PARITY** — PASS; 49 observations checked, 0 mismatches.
- **POINT_IN_TIME_PREFIX_REPLAY** — PASS; 168 observations checked, 0 mismatches.
- **PRODUCT_SNAPSHOT_PARITY** — PASS; 28 observations checked, 0 mismatches.
- **PRODUCT_FUTURE_DATE_SCAN** — PASS; 144 observations checked, 0 mismatches.
- **BROKER_FREQ_VALUE_LOT_PARITY** — PASS; 28 observations checked, 0 mismatches.

## Important defect found and fixed

During validation, the original historical demo payload was found to use the full episode summary table on the History page. That exposed future `closed_at` / `last_linked_at` values for episodes that were still open on 9 Sep 2026. This was a genuine historical-display look-ahead leak.

The payload builder was patched so historical episode summaries are reconstructed only from timeline rows available on or before `as_of`. The validated 9 Sep payload now contains no JSON date later than 9 Sep 2026.

## 9 Sep 2026 snapshot audit

- Expected active investigations: 8.
- Expected state mix: 1 Established, 0 Developing, 4 Emerging, 3 Weakening.
- Expected Spotlight: **CTRA**.
- Payload contained 28 ticker rows.

## Retrospective empirical separation

The primary external-validity question for the current detector is whether a newly opened Spot investigation is followed by more continuation evidence than ordinary NO_INVESTIGATION observations. This is more appropriate than asking whether price necessarily rises.

| Horizon | Any future support: Spot open | Control | Difference | Repeat hard Spot: Spot open | Control |
|---:|---:|---:|---:|---:|---:|
| 1 | 44.9% | 11.4% | 33.5% | 18.4% | 2.6% |
| 3 | 61.2% | 28.4% | 32.8% | 30.6% | 7.8% |
| 5 | 69.4% | 42.1% | 27.3% | 34.7% | 12.6% |
| 10 | 72.9% | 68.2% | 4.7% | 43.8% | 24.1% |

Short-horizon continuation evidence is materially more common after new Spot openings than in the control group, and repeat hard Spot hits remain more common through 10 sessions. The separation in generic support fades by 10 sessions, which is consistent with a short-lived investigation lifecycle rather than a permanent regime label.

### Price outcome

End-of-horizon close returns do **not** show a stable positive advantage for Spot openings in this sample. That is an important result: the current evidence supports SIGNAL as a detector of unusual/persistent market behavior, **not** as a validated price-up prediction model.

## Data quality

- Broker frequency, value, and lot parity were true for all 28 cross-stock summaries.
- Broker-share volume vs daily volume had 33 recorded mismatches across the universe.
- 28 of those warnings occur on 29 May 2026; additional evaluable warnings occur on BBRI/TLKM/ASII (22 Jul) and BMRI (22 Jul, 29 Jul). None of those evaluable mismatch rows was a hard Spot hit.

## What is not yet proven

1. There is no independent human/market ground-truth label for 'sideways accumulation', so precision, recall, F1, sensitivity, and specificity cannot honestly be reported yet.
2. The methodology thresholds were calibrated/reviewed using the May–Sep 2026 research period. Therefore 9 Sep is a valid historical replay but **not** a blind out-of-sample test.
3. A true external validation should freeze Methodology v1.0 Candidate and evaluate a later untouched period, such as 1 Oct 2026 onward, without changing thresholds.

## GitHub recommendation

The code is suitable to share as a **research prototype / Methodology v1.0 Candidate** once the patched payload builder and validated historical payload are used. Do not describe the project as having proven predictive accuracy. Publish the validation report alongside the code so collaborators can reproduce the checks.

