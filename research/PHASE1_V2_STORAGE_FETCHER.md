> Archived preparation: Parquet was deferred by the user. The current accepted JSON pilot and launcher are documented in [SIGNAL_PHASE1_JSON_PILOT.md](../SIGNAL_PHASE1_JSON_PILOT.md). Historical approval-pending statements below describe the earlier proposal, not current execution authorization.

# Phase 1 v2 — offline storage and reviewed fetching

Pilot: ANTM, INCO, BBCA. Analysis: 1 April–30 September 2026. Source envelope:
1 February–30 September 2026. Gate A approved in the chat on 6 October 2026.
Implementation starts at `426b054` on `rework/phase1-v2`. Detector/lifecycle and
UI are unchanged. There are no paid requests in this implementation run.

## Run offline

Install `research/requirements-phase1-v2.txt` in your Python environment, then
run from the repository root:

```text
python -m research.phase1_v2 --repo . --store research/data/rework_phase1_v2/raw --out research/data/rework_phase1_v2/review
python -m unittest research.phase1_v2.tests -v
```

Repeat `--cache-root PATH` to inspect additional known cache folders. Only
explicit roots are scanned. JSON and supported Parquet are imported recursively;
CSV/ZIP are catalogued as references requiring an explicit adapter. This is not
a claim that every historical file on the computer has been inspected. Missing
or unreadable paths remain unresolved in `cache_inventory.json`. Credentials
are neither read nor copied. The command has no live-execution option.

Use `--calendar research/phase1_v2/idx_calendar_2026.json` for the reviewed
published February–September calendar. It has 121 scheduled analysis sessions
and 35 scheduled warmup sessions. Holidays are excluded from targets; request
end dates are trimmed to the last missing target. Evidence/hash and calendar
counts are bound into the plan. Symbol-specific exclusions require a dated
source/reason; unscheduled closures and empty response dates are never inferred.
The calendar-aware conservative plan is 70 requests, down from 73 weekday-only
requests. This is technical preparation, not spending authorization.

Outputs include candidate and validated-only plans, exact request IDs, plan hash,
CSV request list, dry-run URLs, import manifests, field counts and conflicts.
Repeat imports of the same legacy source are idempotent. Weekdays remain
provisional targets; review exchange holidays/suspensions/no-trade sessions
before approving execution. The CLI always regenerates an unreviewed proposal.

## Cache contract

Seven tables have explicit Arrow schemas in `phase1_v2/contracts.py`: daily,
broker_activity, foreign_flow, broker_registry, company_snapshot, news and
corporate_events. Prices/values use float64, lots/volume/frequency int64,
session dates date32, known retrieval timestamps UTC. Original timestamp strings
remain available; naive timestamps are not assigned an invented timezone.
Company snapshots use a caller-supplied stable snapshot ID so unknown retrieval
times are never fabricated. Nested company/event attributes are JSON strings;
news timestamps remain original strings to preserve unknown timezone semantics.

`raw/sources/<sha256>.blob` holds original bytes. Immutable Parquet revisions
live in `raw/batches/<table>/`, with one JSON manifest per batch. Manifests record
the queried request separately from returned dates. Missing manifests from an
interrupted write are never treated as coverage. Raw is ignored by Git.

Legacy imports start as `legacy_candidate` regardless of field completeness.
`Store.promote_legacy` requires a reviewer and source-validation evidence.
Promotion creates a separate audit record; previous revisions remain intact.
Structurally valid API responses become `validated_api`; this status does not
attest that broker coverage or the trading calendar is complete.

`Store.merged` deduplicates identical values, never replaces known values with
null, retains revision/source references, and blocks conflicting fields. The
merged row is revalidated so complementary partial revisions cannot produce
invalid OHLC. `Store.resolve` records an explicit existing source-value choice;
new competing values invalidate it. `Store.export` excludes unresolved rows and
writes a provenance sidecar. Invalid source batches are preserved and quarantined
as a whole. Do not promote a conflict merely because the first source looks newer.

Foreign buy/sell gross detail is optional for the current detector; net/share
are required. Missing gross fields remain null and available coverage must be
reported separately. Broker foreign split and per-share average prices are
preserved. Broker origin/cohort does not identify its customers.

News/events are only legacy candidates; publication/announcement evidence is
needed before historical eligibility. Missing key timestamps are quarantined,
not invented. The pilot does not fetch company/news/event context or replace
application payloads.

## Completeness and calculations

Broker rows alone are insufficient to mark a session covered. After full-source
review, `Store.attest_broker_coverage` records completeness against exact current
validated revisions. Required broker fields and buy/sell totals must reconcile.
New revisions invalidate the attestation. Only attested sessions reduce broker
gap targets. Do not attest a filtered broker response as full-market coverage.

`offline.reconcile` reports buy-side value/frequency and converts lots to shares
with a factor of 100, flags sell-side and daily-volume discrepancies, and derives
no turnover from incomplete sessions. Market scope remains explicitly unverified
unless supported by source evidence; matching totals do not prove market scope.

`offline.baselines` requires 24 preceding sessions and computes medians from the
20 sessions strictly before evaluation. It refuses duplicate dates or mixed
symbols and marks missing values ineligible. It is a data-quality helper, not a
replacement scoring engine. The existing range/MAD/lifecycle implementation
remains authoritative. Legacy baseline values are not copied into new scores.

## Paid execution boundary — still awaiting approval

`fetcher.dry_run` never accesses a key or transport. `execute` is a Python API
for a future explicitly approved run; it requires an injected transport. A
fixed-origin Sectors transport is supplied, with no redirects or automatic
retries. The current CLI intentionally offers only offline preparation.

Before any paid call:

1. Review recursive inventory and field-level reuse; promote only verified legacy
   sources. Review the authoritative trading calendar and no-trade exceptions.
   Amend target windows and rehash the final plan. `calendar_reviewed`,
   `legacy_sources_reviewed`, `broker_completeness_reviewed` must be true with
   calendar evidence. These fields record completed technical reviews, not
   inferred complete data or spending authorization. The human Gate B approval
   accepts these reviews together with the exact list and budget.
   `estimated_credits` and request IDs must match the list.
   Paid execution requires `coverage_basis=validated_only`; candidate proposals
   remain non-executable even if an approval file names their hash.
2. Obtain human Gate B approval naming the exact `plan_sha256`, `request_ids`,
   integer `max_credits`, `reviewer`, timezone-aware `approved_at`, and `evidence`.
   Never manufacture these fields from an implementation approval. Approval
   records are local audit evidence, not a cryptographic user-authentication system.
3. Select one `pilot_request_id`, `remaining_fetches_approved=false`; call only
   that request. Review raw response, normalization, coverage and actual account
   credit usage with the human. The ledger reserves one credit conservatively;
   `reported_credits=null` explicitly means actual usage is not yet known.
4. Only after Gate C obtain updated approval with
   `remaining_fetches_approved=true` and `pilot_review_evidence`, preserving the
   plan hash and credit ceiling. Select remaining request IDs explicitly.

Plan changes invalidate approval. Endpoint/symbol/window/credit limits are
validated before the transport runs. An exclusive fetch lock prevents concurrent
execution against a single store. Use one designated store/ledger for the pilot;
limits are local and cannot account for external account usage or another store.

The durable attempt ledger reserves credits before the network call and retains
the exact request, approval/plan hash and outcome. Returned bytes are stored
before JSON parsing. HTTP error bodies are preserved too. Timeouts/crashes remain
ambiguous: never retry automatically, remove locks or erase attempts to resume.
Human account reconciliation is required; reserved credits remain charged against
the local ceiling. No live requests or approval records are generated by tests.

Gate D still requires score/discrepancy review before adopting new app payloads.
