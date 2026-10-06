# SIGNAL Phase 1 — accepted JSON pilot

Branch `rework/phase1-v2`, base `426b054` (main v2.3). Pilot ANTM, INCO,
BBCA, analysis 1 April–30 September 2026; source history begins 2 February
and supplies 35 scheduled warmup sessions. Gate D and the UI were accepted
in the chat. UI acceptance evidence: “oke ui sudah bagus, mari kita lanjut”.
This is a research pilot, not full-market or out-of-sample approval.

## Current data and results

Approved JSON is in `research/data/rework_phase1_v2/raw/json_pilot` (Git ignored).
Seventy response bodies are retained, including two initial manual responses.
Merged source hashes are recorded in `payloads/pilot_v2/manifest.json`.
Parquet storage is deferred; the earlier `research/phase1_v2` package and its
documentation are archived preparation, not the current pilot run path.

- Daily: 156 sessions per symbol; analysis: 121 sessions per symbol.
- Broker/foreign flow missing on 27 March, 1 April, 15 April and 22 April.
- Broker volume does not match daily volume on 29 May, for all three symbols.
- 65 analysis sessions evaluated and 56 withheld per symbol.
- Seven hard hits; six observed episode candidates. At Sep30 only BBCA is active
  (EMERGING). ANTM and INCO have no active investigation at that snapshot.
- Gaps and unknown initial lifecycle states remain null. No zero-fill,
  shortened baseline, synthetic unsupported session or synthetic gap closure.
- Detector v0.2 and lifecycle v0.3.1 logic and thresholds remain frozen.
- Broker scope and independent completeness remain unverified. Market/peer
  specificity is not scored. Older reaction validation is hidden in pilot UI.

## Install once

Use a local Python virtual environment and install
`backend/requirements.txt` plus `research/requirements-json-pilot.txt`.
Run `npm ci` in `frontend`. No API key is needed to validate or serve this pilot.
The research runtime tested here is pandas 3.0.1 and numpy 2.3.5.

## Run from repository root

```powershell
.\run_pilot_windows.ps1 -Mode Validate
.\run_pilot_windows.ps1 -Mode Backend
```

Keep the backend terminal running. In another terminal:

```powershell
.\run_pilot_windows.ps1 -Mode Frontend
```

Open `http://127.0.0.1:5173/`. Local API is on port 8001.
If using an existing Python runtime, pass `-PythonPath PATH`; an isolated package
folder may be passed with `-DependencyPath PATH`. Launcher variables are process
scoped and restored when it exits. It does not read `.env`, install packages,
fetch, retry, start hidden background tasks or change legacy snapshot defaults.
Use Ctrl+C in each terminal to stop. Do not start a duplicate server on an occupied port.

`Validate` recomputes detector, lifecycle and all 19 payloads in temporary storage,
then compares them with the accepted snapshot. Only `manifest.generated_at` is
excluded. Source hashes must match. Existing payloads are never overwritten.
The validation report is placed beside the ignored source JSON.

Frontend checks: `npm run test:pilot` and `npm run build` from `frontend`.
The focused regression checks cover null/false, initial unknown state, chart
segmentation, latest missing values and nullable status rendering.

## Remaining boundaries

Activity charts label reconstructed baseline values as approximately equal
(actual / rounded stored detector ratio); pilot z-score and standard-deviation
bands are unavailable. This presentation does not change detector scoring.
Actual billed credits still require account-side reconciliation; local request
counts are not a billing statement. No extra spending approval is inferred.

Next research scope may address source gaps/scope evidence or an out-of-sample
period from 1 October 2026. Prepare and review an exact request list and budget
before any additional paid Sectors request. Do not automatically expand the pilot.
