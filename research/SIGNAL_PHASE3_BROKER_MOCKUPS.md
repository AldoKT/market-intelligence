# Phase 3 — Broker concepts

Review: `/design/brokers?variant=4&symbol=BBCA`.

Five layouts: Flow board, Broker desk, Evidence first, Compact terminal, Split explorer.
Graphite Ice, glass navigation, compact panels match selected Overview Gallery, Summary Evidence First and Market Activity Compact Board.

All returned brokers remain in a scrollable table including net zero; search by code/name, net-side filters, numeric/code sorting and optional full lot/frequency columns. Choose session or episode; select a broker or leader for details and interactive TradingView signed net-flow history. Missing values remain null/dashes. Session dates and episode scope are shown; pilot snapshot/version/methodology notices are omitted.

Local API reads only; no Sectors requests. Existing production Broker page unchanged.

Validation: production build passed; existing broker UI/data tests and Market Activity data checks passed. Desktop visual review of all five; browser checks search, selection, net-zero filter, full columns, sorting, session/episode switching and missing session. Responsive CSS supplied; tool viewport override did not affect this tab, so phone rendering not independently verified.
