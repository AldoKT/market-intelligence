# Phase2 Broker — local read-only UI

Accepted direction: retain every broker returned by the source, including flat net and unlisted codes. Phase2 describes who traded and observed continuity; it does not change the hard Spot gate or infer investor identity.

## Run

Use the existing `run_pilot_windows.ps1 -Mode Backend` and `-Mode Frontend` launcher. The Broker tab requires the JSON pilot profile. Default data directory is `research/data/rework_phase1_v2/raw/broker_phase2_preview`; override with `SIGNAL_BROKER_DIR` if needed. The reviewed pilot, OOS and broker packages are tracked so a clone can run and reproduce the pilot offline. Other raw caches and local Postman workspaces remain ignored. See DATA_NOTICE.md before public redistribution. No API key, external requests or fetcher are used by these endpoints.

To regenerate the local preview after an independently reviewed source change:

```powershell
python -m research.signal_broker_phase2 --repo . --out research/data/rework_phase1_v2/raw/broker_phase2_preview
```

The builder uses accepted pilot data plus reviewed October OOS raw bodies and lifecycle replay. It verifies source hashes, row inclusion and gross/net identities. The fixed pilot payloads are not rebuilt or replaced.

## Endpoints

- `GET /api/brokers/{symbol}` — available dates, episodes, source cutoff and default SIGNAL date.
- `GET /api/brokers/{symbol}/sessions/{YYYY-MM-DD}` — all returned broker rows and source quality.
- `GET /api/brokers/{symbol}/episodes/{investigation_id}` — full episode aggregate and per-broker histories, closure session included.
- `GET /api/brokers/{symbol}/history/{code}?through=YYYY-MM-DD` — up to 20 preceding/selected sessions; never returns later observations.

Unknown symbols, unavailable dates/episodes and unknown broker codes return 404. Invalid date syntax returns 422. Episode membership and repository root checks prevent reading unrelated paths. Legacy profiles do not expose this research extension.

## Snapshot and data quality

SIGNAL price/status remains Sep30. Broker starts on that date by default; later dates and complete episode windows are explicitly selectable and labelled. All 22,759 returned broker/session rows are retained in 375 session views and six episode views. Missing sessions, unknown broker identity and source volume mismatch remain labelled. Unknown observations are null, never inferred zero. Registry origin refers to the broker company, not investor nationality. Aggregate prices are gross value divided by shares, not an average of daily averages.

## Validation

Run backend tests with both repository root and backend on PYTHONPATH: `python -m pytest backend/tests`. Frontend: `npm run test:broker`, `npm run test:pilot`, `npm run build`. Tests cover no top5 truncation, flat-net inclusion, cutoff isolation, null vs zero, identifier safety, legacy profile isolation, search/sorting and net-side filtering. Browser verification covers all three symbols, missing/mismatch sessions, cross-period BBCA episode, and 548/1280 widths. Backend and research validation: 21 tests pass; frontend: 35 assertions pass. No paid calls were performed.

## Grafik broker
Klik kode broker untuk grafik net buy/sell per sesi. Data tidak tersedia tetap kosong; sesi dengan kualitas belum terverifikasi ditandai. Grafik bukan kumulatif. Validasi frontend: 21 pemeriksaan broker dan 14 pilot; build berhasil.

## Pemeriksaan kestabilan 7 Oktober
Backend menolak JSON rusak, scope saham/tanggal salah, kode duplikat, angka nonfinite/negatif, dan net yang tidak sesuai beli-jual. Error data lokal menjadi 503 tanpa path disk. Jika tanggal snapshot tidak tersedia, pemilihan sesi harus eksplisit. Validasi: 21 test backend/riset, 35 pemeriksaan frontend, build produksi berhasil. Kesenjangan data sumber dan mismatch volume tetap menjadi batas riset; tidak diisi atau disembunyikan.

## Reproducibility gate

Run before changing broker source data or closing the Phase2 pilot review:

```powershell
python -m research.signal_validate_broker_phase2 --repo .
```

This command rebuilds into a temporary directory from reviewed pilot/OOS sources, checks all stored broker JSON hashes (including episode summaries, history continuity and the manifest), and verifies that the accepted pilot snapshot remains unchanged. It makes no external request and never replaces stored views. A mismatch exits with code 1 and reports changed, missing or extra files. Optional `--report` must point outside input/product data directories.

7 October result: 382/382 files identical (375 sessions, six episodes, one manifest), all 22,759 source rows retained, pilot snapshot unchanged. One regression test verifies that modified, missing and extra files fail comparison. Remaining source limitations: nine missing broker sessions across stocks and three volume mismatches; independent source completeness is still unverified. Phase3 UX work is deferred. Local pilot verification does not establish deployment security or investment validity.
