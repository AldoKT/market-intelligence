# Phase 3 Overview concepts

Preview: http://127.0.0.1:5173/design/overview?variant=1

1. Editorial: Spotlight beside price chart; recent episodes in two columns.
2. Research desk: chart and recent episodes left; Spotlight right.
3. Focus: centered introduction and unified Spotlight/chart panel.
4. Gallery: investigation cards with historical status and peak confidence.
5. Night terminal: dark glass navbar and compact investigation rows.

These are independent mockup routes; production Overview is unchanged. No snapshot, dataset version, coverage, or methodology explanation is rendered in the concepts. Local API payloads supply all metrics and episodes. Historical episodes are explicitly marked completed; active Spotlight is excluded from the latest list. No paid requests were made.

Chart: Lightweight Charts 5.2.1, area/candlestick, pan, zoom, reset, crosshair date/price and cursor coordinate price, last-price marker and line. Missing OHLC values stay whitespace. Attribution remains visible. Generated transparent SIGNAL PNG: frontend/public/signal-logo-generated.png (built-in imagegen; prompt: minimal magenta signal wave and three rising bars).

Validation: production build passes; all five concepts visually reviewed; Candle/Area, zoom/reset, crosshair price and search checked in browser; no console errors. At mobile width 375px, page width equals viewport width and forbidden snapshot strings are absent.

## Gallery refinement

Selected concept 04 retains glass navbar with navy surfaces, teal price lines, and amber accents. Each latest episode card has a price chart showing 12 preceding sessions and up to 6 sessions after closure, limited to the available payload. Rectangles span each actual hard-spot session low–high, only within that episode; hatching and explicit counts avoid reliance on color alone. Missing closes break the line, unavailable OHLC is not fabricated. Mini-charts are read-only previews; main price chart remains interactive.

Validation: gallery test checks all 65 episodes and 79 hard spots, null/unknown markers, episode boundaries and cutoff. Palette text minimum 6.46:1 across defined surfaces; chart line 9.94:1, hard-spot stroke 8.79:1. Browser checks 177 rendered text samples with no contrast failures (solid/composited backgrounds), plus gradient surface palette pairs. This is scoped contrast verification, not full WCAG certification.

Gallery palette now selected: Graphite Ice. Background #111418, cards #20262E, text #F3F6FA, accent/hard spots #93C5FD, chart #67E8F9. Palette text minimum 6.14:1; graph line 10.51:1; hard-spot stroke 8.45:1. Gallery test and production build pass.
