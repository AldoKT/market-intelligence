# Checkpoint sebelum Phase 3

Metode acuan UI: **phase1-json-pilot-valid-baseline-1.0**, berstatus alternatif eksperimental. 28 saham; 121 sesi masing-masing, 1 April–30 September 2026. Histori awal 2 Februari; broker/OOS sampai 6 Oktober. Snapshot produk tetap 30 September.

Baseline aktivitas: 20 observasi valid sebelumnya dalam maksimum 25 sesi perdagangan. Harga/volume memakai kalender asli; sesi saat ini yang kosong/null/mismatch tetap ditahan. Gap memutus segmen lifecycle, tanpa zero-fill atau bridging. UNKNOWN tidak disamakan dengan inactive atau net-flat. 65 episode April–September; BBCA satu-satunya investigasi aktif pada snapshot. Hasil OOS empat sesi tidak membuktikan prediksi return.

Phase 3 mengubah UI/UX seluruh fitur, bukan thresholds, baseline, lifecycle, tanggal snapshot, atau nilai sumber. Perubahan metode memerlukan review tersendiri. Versi ketat expanded_v2 dan pilot_v2 tetap disimpan sebagai pembanding.

## Pemulihan data dari Git

Arsip di `research/data/checkpoints/phase2_expansion28` menyimpan semua raw expansion, capture/ledger/audit, eksperimen, dan output broker untuk profil lama dan alternatif. JSON besar tetap di cache raw lokal; Git menyimpan arsip terverifikasi agar tidak terkena batas ukuran file. Arsip tidak memuat .env atau API key. Tidak ada push/publikasi dalam checkpoint ini.

Setelah clone: `python -m research.signal_restore_checkpoint`. Tidak menimpa data yang berbeda; existing file identik dilewati. Semua hash/path diperiksa sebelum menulis. Verifikasi saja: tambah `--verify-only`.

Validasi profil: `./run_pilot_windows.ps1 -Mode Validate -Dataset valid_baseline_v1`. Jalankan aplikasi melalui launcher yang sama dengan Mode Backend/Frontend. Profil alternatif adalah default; pilih `-Dataset expanded_v2` untuk versi ketat atau `-Dataset pilot_v2` untuk tiga saham pilot.

Scope Phase 3: Overview, Investigations, Summary, Market Activity, Broker, Context, History, Watchlist, Methodology. Data dan seluruh broker buy/sell tetap tersedia; gap, nol, dan UNKNOWN harus tetap dapat dibedakan.

Cadangan terverifikasi: 7728 file dalam tiga arsip (48.0, 2.1, 37.1 MiB). Tes backend/research/restore: 31 lulus; build frontend dan 40 assertions frontend lulus.
