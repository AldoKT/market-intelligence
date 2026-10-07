# Summary mockups — Graphite Ice

Preview: http://127.0.0.1:5173/design/summary?variant=1&symbol=BBCA

1. Balanced: metric strip, chart plus brief, evidence plus continuation, participation plus timeline.
2. Research desk: three compact columns with brief/timeline, chart/metrics, evidence/continuation.
3. Evidence first: evidence beside chart, with brief/continuation/timeline below.
4. Compact board: chart and metrics beside brief/participation; evidence beside continuation/timeline.
5. Terminal: chart and brief left; evidence/continuation right; dense metric strip.

Standalone review routes preserve production Summary pending selection. No quality banner, data-gap lists, snapshot/version labels, or methodology explanations are rendered. Unknown values stay dash, unknown state remains distinct from inactive. Local API only; no paid requests. Stock selector supports 28 symbols. Evidence, conditions, dates and metrics use actual payloads; no synthetic confidence. Foreign net/turnover fractions are formatted as percentages.

Shared Lightweight Charts component gains optional height, default 300px; Summary uses 240–270px. Area/candle, zoom, reset, crosshair and last-price marker remain available. Graphite Ice backgrounds/foregrounds match the selected Gallery palette.

Validation: production build and Gallery regression pass. Browser visually reviewed all five layouts. All five mobile layouts at 375px have content width equal to viewport width; forbidden banner strings absent. Candle/area, zoom/reset, cursor price tested. BBCA active, ADRO inactive, and BBRI unknown tested without zero-filling unknown values. No browser console errors.
