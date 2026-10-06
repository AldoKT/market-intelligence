# SIGNAL v2.1 — Final UI Polish

This release is a presentation-layer refinement of v2.0.

## Changed
- Global typography normalized to readable desktop sizes.
- Page spacing follows a 4/8/12/16/20/24/32/40px rhythm.
- Top navigation, ticker workspace header, buttons, badges and tables standardized.
- Overview spotlight tightened and chart/metric alignment corrected.
- Investigations filters/table/quick preview made denser and more readable.
- Summary hero, Evidence Snapshot, 5W+1H and Look Ahead compacted.
- Market Activity chart height reduced to 300px and detail panel density normalized.
- Context empty/source-unavailable states compacted.
- History charts reduced to 260px and table/session/event typography enlarged.
- Watchlist empty state and KPI row compacted.
- Methodology framework, detection cards, key terms and guardrails resized for readability.

## Unchanged
Detector thresholds, lifecycle logic, Evidence Confidence formula, reaction validation, data-quality warnings, and point-in-time safeguards are unchanged.

## v2.2 Overview fidelity pass

The Overview page was rebuilt to mirror the locked UI Guidance mockup more faithfully:
- pale pink Spotlight hero rather than white metric-container treatment
- two-zone Spotlight composition (copy left, confidence/price/chart right)
- thick magenta confidence donut with /100 label
- filled area price chart with grid, axes, endpoint marker and price tag
- 2x2 KPI card grid matching the reference composition
- Market Pulse removed from Overview because it is not present in the locked mockup
- Latest Investigations rebuilt with the reference columns and compact row density
- global navigation updated to the bar-chart SIGNAL mark, underline active nav, search, bell and avatar treatment shown in the guidance

Research methodology, detector rules, payload semantics and point-in-time behavior are unchanged.
