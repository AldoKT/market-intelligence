# SIGNAL Frontend — Complete Demo Build

Complete React + TypeScript UI for SIGNAL.

## Implemented pages

1. Overview
2. Investigations
3. Summary
4. Market Activity
5. Context
6. History
7. Watchlist
8. Methodology

## Product flow

```text
Overview
   ↓
Investigations
   ↓
Ticker Workspace
   ├─ Summary
   ├─ Market Activity
   ├─ Context
   └─ History

Watchlist
Methodology
```

## Run with FastAPI backend

Backend:

```powershell
cd "D:\Lain-lain\Sector\signal_backend_v1"
$env:SIGNAL_PAYLOAD_DIR="D:\Lain-lain\Sector\signal_product_payloads_v1_demo"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd "D:\Lain-lain\Sector\signal_frontend_complete_v1"
npm install
Copy-Item .env.example .env
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## macOS equivalents

Backend:

```bash
cd signal_backend_v1
export SIGNAL_PAYLOAD_DIR="../signal_product_payloads_v1_demo"
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd signal_frontend_complete_v1
npm install
cp .env.example .env
npm run dev
```

## Notes

- This historical demo does not call Sectors API.
- Watchlist membership is stored in browser localStorage.
- Missing fundamentals/corporate-events/news are shown as unavailable instead
  of being fabricated.
- Evidence Confidence is not a return probability.
- Green UI states are not buy recommendations.
- The historical snapshot must remain visibly labeled as historical.
