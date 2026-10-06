# SIGNAL Frontend v2.0 — UI Implementation Notes

This frontend revision treats **SIGNAL UI Guidance v1.0** as the presentation-layer design contract while preserving the validated detector/lifecycle methodology.

## Design alignment

- Overview: Spotlight hero first, secondary KPI block, Latest Investigations below.
- Investigations: active explorer table + filters/sorting + right quick preview.
- Summary: interpretation owner (hypothesis, Evidence Confidence, Evidence Snapshot, 5W+1H, Look Ahead).
- Market Activity: trading-data owner (Price, Transaction Count, Turnover, Avg Trade Value) with a metric-specific detail panel.
- Context: explanation owner with All / Sector / Company / Market / News filtering.
- History: price/evidence evolution, Past Investigations table, selected-session details.
- Watchlist: monitoring workspace with state summaries, group concentration, recent signal updates and two-stock comparison.
- Methodology: framework, detection logic, key terms, confidence composition, guardrails, example snapshot and Reaction Validation.

## Intentional evidence-preserving deviations

The PDF mockups contain several visual concepts that require source data not present in the current offline payload. v2.0 does **not** fabricate these values.

1. Market Activity normal-range band: omitted until a formal normal-range definition is added to the product contract.
2. Market Activity z-score: shown as unavailable because the current payload does not expose the required statistic.
3. History Weak/Moderate/Strong zones: omitted because formal Evidence Confidence zone thresholds are not defined by the methodology.
4. Context fundamentals, corporate events and news: explicit unavailable state when source records are not bundled.
5. Context "Sector" is represented by the existing research peer group and is clearly labeled as a research grouping, not an authoritative IDX classification.
6. Price change in discovery tables is derived only from the immediately preceding point-in-time close in the frozen timeline.

## Product-contract v2 enrichment

The payload builder now adds only point-in-time-safe fields derived from already validated timeline data:

- `close`
- `daily_change_pct`
- `pattern_type`
- activity-series `evidence_confidence`
- activity-series `diagnostic_evidence_score`
- activity-series `persistence_score`
- activity-series `supporting_session`
- context `peer_comparison`
- context `source_availability`

No new Sectors API calls are required to run this package.
