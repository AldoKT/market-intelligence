# Integrasi riset 28 saham

Data 25 saham tambahan telah disalin dari hasil fetch yang diaudit ke `research/data/rework_phase1_v2/raw/expansion_2026`. Tiga saham pilot menggunakan sumber OOS yang telah diterima. Raw capture, tiga ledger, hasil audit, dan nilai null asli dipertahankan.

- Cakupan: 28 saham, histori 2 Februari–6 Oktober 2026; analisis 1 April–30 September, OOS 1–6 Oktober.
- Detector dan lifecycle tetap memakai aturan beku. Hasil tiga saham pilot dibandingkan per baris dengan replay OOS sebelumnya.
- Empat saham berstatus lifecycle belum diketahui pada 30 September: AMMN, BBRI, BMRI, GOTO. Status tersebut bukan NO_INVESTIGATION.
- Gap, mismatch volume, dan 23 baris broker BMRI 29 Juli yang null tetap membatasi evaluasi. Tidak ada zero-fill atau retry berbayar.
- `integration_manifest.json` menyimpan hash sumber, capture, audit, dan hasil replay.

Verifikasi offline:

```powershell
python -m research.signal_validate_expansion
```

Status: versi ketat 28 saham tersedia melalui `run_pilot_windows.ps1 -Dataset expanded_v2`. Default kini valid_baseline_v1 untuk history alternatif enam bulan. Snapshot produk 30 September; sesi broker sampai 6 Oktober. Kontrak produk mendukung UNKNOWN dengan active dan persistence null; tabel broker mendukung null dan filter UNKNOWN. Semua payload ticker tiga saham pilot tetap identik byte per byte. Untuk kembali ke pilot gunakan -Dataset pilot_v2.

Rebuild offline: `python -m research.signal_build_expanded`. Payload baru berada di `payloads/expanded_v2`; broker di `research/data/rework_phase1_v2/raw/expansion_2026/broker_views`. Tidak ada request API saat build.

Cache raw expansion tetap diabaikan oleh Git; cadangan terverifikasi berada di research/data/checkpoints/phase2_expansion28. Arsip dan manifest dilacak Git. Pulihkan dengan python -m research.signal_restore_checkpoint. File gabungan 139 MB tersimpan di dalam arsip, bukan sebagai blob Git yang melewati batas ukuran.

Verifikasi aktivasi: build frontend lulus, 23 tes backend/research dan 40 assertions frontend lulus; 168 endpoint per saham diperiksa. Seluruh 3500 sesi dan 43 episode broker lolos validator; 381 payload broker pilot sama secara struktural dan 15 payload ticker pilot identik byte per byte.
