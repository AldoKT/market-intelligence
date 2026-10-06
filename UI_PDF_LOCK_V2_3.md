# SIGNAL UI PDF Lock — v2.3

This package treats `SIGNAL UI Guidance v1.0` as the locked presentation contract for the Investigation workspace.

## Rebuilt in v2.3

- Investigations explorer: dense table + filters + right-side quick preview.
- Summary: investigation-report hero, confidence ring, price chart, status panel, evidence snapshot, 5W+1H, and Look Ahead.
- Market Activity: four metric selectors, actual-vs-20D chart, normal band, anomaly highlight, metric-specific detail, cross-metric comparison.
- Context: Sector/Research Group, Company Fundamentals, Corporate Events, Peer Comparison, Market Context, Relevant News, Key Takeaways.
- History: candlestick + volume timeline, Signal Strength Over Time zones, historical session table, selected-session details.

## Data integrity rules

1. Never label a relative ratio as an actual IDR value.
2. Actual OHLC/volume/transaction count/turnover/average-trade-value are used only when cached raw data exists.
3. Missing fundamentals/sector-index series remain visibly unavailable; no fake metrics are generated.
4. Historical news and corporate actions are truncated to the snapshot date.
5. Weak/Moderate/Strong areas on the History chart are visual reading bands only and do not alter lifecycle thresholds.
6. Detector, lifecycle, Evidence Confidence formula, and point-in-time rules are unchanged.

## Bundled actual-data enrichment

ANTM, BRMS, GOTO, INCO and TINS have cached actual-market-data enrichment in the bundled payloads. Other symbols explicitly fall back to relative series where needed.
