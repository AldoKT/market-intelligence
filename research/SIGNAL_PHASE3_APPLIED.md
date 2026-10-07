# Phase 3 selected concepts applied

Applied to normal product routes:
- `/`: Overview 04 Gallery, Graphite Ice, recent investigation mini charts with real hard spots.
- `/investigations/:symbol/summary`: 03 Evidence First.
- `/investigations/:symbol/activity`: 04 Compact Board, aligned Period Highlights.
- `/investigations/:symbol/brokers`: reference-style Broker Summary/Flow; buyer/seller share one right scrollbar.
- `/investigations/:symbol/context`: compact Graphite Ice Context.

Review galleries remain under `/design/`. Product pages force the chosen layout, hide review controls and translate review links to product paths. Stock selection uses route symbols; watchlist actions remain available. No pilot snapshot/version/quality notices appear on selected pages. History, investigation explorer, Watchlist and Methodology retain their existing layout pending later design work.

TradingView Lightweight Charts is bundled with attribution. Daily broker flow never invents intraday observations, missing values or investor/market filters. Local backend payloads unchanged; no paid requests.

Validation: frontend production build; gallery palette/65 episodes/79 hard spots; broker filtering/chart regression checks; signed/cumulative broker flow checks; market metrics across 28 stocks and 336 views. Browser checked normal Overview→Summary→Activity→Broker→Context navigation, selected layouts, stock switching, single header, hidden concept selectors, Watchlist toggle/revert and no console errors.
