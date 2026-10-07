# Broker reference concept

Route: `/design/brokers/reference?symbol=BBCA`.

Graphite Ice with Broker Summary / Broker Flow subtabs inspired by the supplied screenshots.
Summary: side-by-side ranked buyer/seller tables, gross/net toggle, code/name search, value/lot/weighted average price. All returned brokers retained in gross view; net view keeps net-zero/unknown codes in a separate selectable strip. No inferred accumulation/distribution score or unsupported investor/market filters.
Flow: up to six selectable/removable broker lines, optional price overlay on independent right axis, value/lot, daily/segmented cumulative, 5 or 20 local daily sessions or full episode history. Missing observations and unreconciled sessions break cumulative segments; lines never connect across missing segments. This is daily data, not intraday. Current activity price payload ends Sept 30; later broker dates do not invent price data.

Validation: build passed; broker-flow pure calculation checks passed. Browser verified 71 broker rows per gross side, net counts 54 buyers +16 sellers +1 net-zero, toggle, value/lot, 5/20, broker add/remove, zoom/reset, graph rendering and no browser errors. Screenshot artifacts saved for Summary and Flow. No paid API requests.
