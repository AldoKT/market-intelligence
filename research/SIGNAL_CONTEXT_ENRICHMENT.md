# Context enrichment — 28 stocks

The Context page now reads reviewed Sectors JSON for all 28 stocks in `valid_baseline_v1`.

- Capture date: 8 October 2026. Company reports contain **current retrieval snapshots**, including price reference dates from 7 October. Annual financials retain their financial year. They are not inputs to historical signal scoring.
- News and corporate event dates: 1 April–30 September 2026. News archives have 4,804 stock/article rows; an article may reference multiple stocks. Offset pagination finished for every stock, but this feed is not snapshot-isolated: provider counts changed during retrieval. No claim is made that retrieval is a frozen archive.
- Market context: 121 daily observations for IHSG and total IDX market capitalization. Period change compares the first and last saved index levels. These are not market activity breadth or specificity scores.
- Peers: provider fundamental comparison, with annual revenue year shown. Stocks outside the 28-stock universe remain readable in the comparison but have no unsupported navigation.
- Corporate actions use AGM/event/ex-dividend dates; payment dates appear in detail. No action in the period is a valid empty result.
- Historical `current`, `as_of`, detector, lifecycle, and broker data were not changed.

## Storage and rebuild

Raw responses and capture ledgers live locally in `research/data/context_enrichment_2026/raw/`. Existing `.gitignore` excludes raw API caches; no credentials or capture tokens are imported. Derived Context payloads and `research/data/context_enrichment_2026/audit.json` can be reviewed in Git.

After rebuilding the base payloads, reapply enrichment offline:

```powershell
python research/signal_context_enrichment.py --source research/data/context_enrichment_2026/raw --payload payloads/valid_baseline_v1
```

The importer checks HTTP status, response SHA-256 hashes, stock coverage, date boundaries, pagination, and index coverage before producing payloads. It makes no external API requests.

Credits: initial 174 + additional news 144 = **318**. This is the planned/reserved total; confirm actual charges using the provider dashboard.

Validation: all 28 historical Context states compared to HEAD; TypeScript/Vite build; backend API contract; null/zero and event-boundary tests; browser search, pagination, peer navigation, and layout checks.
