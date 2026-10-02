# SIGNAL — Complete Project v1

SIGNAL is a post-market market-investigation engine.

This package contains the complete current prototype:

```text
SIGNAL_complete_project_v1/
├── backend/                 FastAPI application layer
├── frontend/                React + TypeScript complete UI
├── payloads/
│   ├── demo_2026-09-09/     Historical demo with active investigations
│   └── latest_2026-09-29/   Latest available historical snapshot
├── research/                Offline methodology/product-contract scripts
├── setup_windows.ps1
├── run_demo_windows.ps1
├── run_latest_windows.ps1
├── setup_mac.sh
├── run_demo_mac.sh
└── run_latest_mac.sh
```

## Implemented UI

1. Overview
2. Investigations
3. Summary
4. Market Activity
5. Context
6. History
7. Watchlist
8. Methodology

## Historical demo

Use the **09 Sep 2026** snapshot for presentation because it contains
active investigations and exposes the full lifecycle UI.

The application visibly labels the view as historical. It must not be
presented as current market data.

## Windows

From PowerShell:

```powershell
.\setup_windows.ps1
```

Then:

```powershell
.\run_demo_windows.ps1
```

Open:

```text
http://127.0.0.1:5173
```

API docs:

```text
http://127.0.0.1:8000/docs
```

For the latest snapshot:

```powershell
.\run_latest_windows.ps1
```

## macOS

You need:

- Python 3
- Node.js + npm

From Terminal:

```bash
chmod +x setup_mac.sh run_demo_mac.sh run_latest_mac.sh
./setup_mac.sh
./run_demo_mac.sh
```

Open:

```text
http://127.0.0.1:5173
```

For latest:

```bash
./run_latest_mac.sh
```

## Important: API usage

Running this package uses **zero Sectors API requests**.

Both demo snapshots are already materialized locally.

## Methodology status

Current methodology status:

```text
SIGNAL Methodology v1.0 Candidate
```

The detector is an investigation system, not a future-return optimizer.

Key semantic guardrails:

- Evidence Confidence is not probability of a price increase.
- Context Specificity is descriptive and does not alter the hard Spot gate.
- Broker/flow evidence does not identify a participant as institutional.
- No buy/sell recommendation is generated.
- Missing fundamentals/news/events are shown as unavailable instead of invented.

## Application architecture

```text
Cached Sectors-derived data
          ↓
Research / detection engine
          ↓
Methodology v1.0 Candidate
          ↓
Product payload builder
          ↓
JSON contract
          ↓
FastAPI
          ↓
React / TypeScript UI
```

## UI architecture

```text
Overview
   ↓
Investigations
   ↓
Ticker Workspace
   ├── Summary
   ├── Market Activity
   ├── Context
   └── History

Watchlist
Methodology
```

## Watchlist

Watchlist membership is saved in browser `localStorage`. It is a viewing
preference only and never changes detection logic.

## Current offline-data limitations

The demo payload contains the detector/lifecycle/context evidence required
for the research prototype. The UI intentionally displays an unavailable
state for fundamentals, corporate events, and news when those source
payloads are not bundled.

That behavior is deliberate: SIGNAL does not fabricate missing evidence.


## Validation status

The included validation suite reports:

```text
Implementation correctness      PASS
Point-in-time validity          PASS
Product payload validity        PASS
Data quality                    PASS_WITH_WARNINGS
External methodology validity   PARTIAL; OUT-OF-SAMPLE PENDING
Price-direction accuracy        NOT ESTABLISHED
```

Read:

```text
VALIDATION_REPORT.md
```

Re-run on Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\validate_windows.ps1"
```

Re-run on macOS:

```bash
./validate_mac.sh
```

A validation pass found and fixed a genuine historical-display look-ahead issue in the original History payload. The current v1.1 payload builder reconstructs historical episode summaries only from information available through the snapshot date.

## Research claim boundary

SIGNAL currently has evidence that Spot openings are followed by more short-horizon continuation evidence and repeat Spot activity than NO_INVESTIGATION controls in the retrospective sample.

It is **not** validated as a price-up prediction model, and no independent ground-truth accumulation labels exist yet. Therefore the project does not claim precision/recall/F1 for "institutional accumulation".

A true next-stage validation requires freezing the methodology and testing an untouched period after the May–Sep 2026 research window.


## Reaction Validation v1

SIGNAL now includes a separate **Reaction Validation** layer. It does not change the frozen detector thresholds.

Primary design:

```text
SPOT_OPEN
vs
same-date eligible NO_INVESTIGATION controls

Horizons:
+1 / +3 / +5 / +10 trading sessions

Metrics:
fixed-horizon return
positive-close rate
close-based MFE / MAE
+2% / +3% / +5% reaction rates
5-session closing-range breakout
positive-vs-negative first-touch tests
```

Current result:

```text
TENTATIVE_DIRECTIONAL_INFORMATION
NOT YET ROBUST FOR A <=5 SESSION CLAIM
```

The 49 SPOT_OPEN episodes show generally more favorable reaction characteristics than same-date controls, especially at +5 to +10 sessions. However, most <=5-session date-cluster bootstrap intervals still cross zero. Therefore the repository does **not** claim reliable short-horizon price prediction.

Read:

```text
REACTION_VALIDATION_REPORT.md
validation/reaction_v1/
```

Re-run on Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\validate_reaction_windows.ps1"
```

The next decisive validation is a frozen-methodology out-of-sample test using untouched data from 1 Oct 2026 onward.
