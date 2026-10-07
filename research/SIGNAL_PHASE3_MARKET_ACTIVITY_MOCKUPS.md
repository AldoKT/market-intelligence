# Phase 3 — Market Activity mockups

Review route: `/design/activity?variant=1&symbol=BBCA`.

Five options: Signal desk, Activity first, Dual lens, Compact board, Session explorer.
Graphite Ice, glass navigation, compact panels, and TradingView Lightweight Charts match Overview Gallery and Summary Evidence First (selected option 03).

Switch metrics between turnover, volume, transactions and average trade; choose 20 sessions, 60 sessions or six months. Charts support bars/area, price area/candles, pan, zoom, cursor values and reset. Session explorer selects a session for details. Square markers indicate existing hard spots. Uses local payloads only; no API requests.

Missing values remain whitespace/dashes. Entirely absent actual metric series may use explicitly titled relative data; actual and relative units never mix. Foreign net ratio is current only. Pilot-quality, snapshot/version and data-method notices are omitted from these review pages. Production pages are unchanged.

Validation: frontend build; market-activity helper checks for all 28 symbols × 4 metrics × 3 windows; browser desktop/mobile review and interaction checks.
