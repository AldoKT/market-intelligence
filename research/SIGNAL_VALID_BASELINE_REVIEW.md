# Eksperimen baseline aktivitas valid

Eksperimen offline pada 28 saham, analisis 1 April–30 September 2026. Aplikasi aktif dan detector asli tidak berubah; 0 request API.

| Hasil | Aturan ketat | 20 valid, batas 25 sesi | 20 valid, batas 30 sesi |
|---|---:|---:|---:|
| Sesi dapat dinilai | 1731 (51.1%) | 3271 (96.5%) | 3271 (96.5%) |
| Sesi ditahan | 1657 | 117 | 117 |
| Hard spot hits | 56 | 79 | 79 |
| Investigasi aktif 30 September | BBCA | BBCA | BBCA |

Kedua batas menghasilkan timeline detector yang sama pada dataset ini. Batas 25 lebih ketat dan cukup untuk coverage ini; tidak dioptimalkan terhadap return.

20 observasi valid sebelumnya dipakai bersama untuk baseline aktivitas (turnover, frekuensi, ticket size, konsentrasi broker). Harga/kompresi serta relative volume tetap memakai kalender sesi asli. Observasi di hari evaluasi dan masa depan dilarang masuk baseline. Sesi saat ini yang broker/foreign flow kosong, null, atau volume mismatch tetap ditahan. Tidak ada zero-fill. Kesetaraan dengan detector beku saat data lengkap, batas usia, dan pencegahan look-ahead diuji (3 tes lulus).

Lifecycle masih memakai aturan pemutusan segmen pada gap. Menjembatani gap singkat belum diuji dalam eksperimen ini, sehingga 65 episode bukan klaim kesinambungan melalui data kosong. BBRI, BMRI, GOTO tetap UNKNOWN pada snapshot. Cakupan evaluasi yang lebih besar bukan bukti akurasi atau prediksi return lebih baik. Validasi OOS ulang diperlukan sebelum promosi metode.

Ulangi: `python -m research.signal_json_valid_baseline --max-age 25` (atau 30). Output riset di `research/data/rework_phase1_v2/raw/valid_baseline_experiment`; comparison.json menyimpan hasil per saham.

## OOS 1–6 Oktober

Empat sesi perdagangan × 28 saham = 112 observasi. Aturan ketat dapat menilai 104; alternatif 109. Tiga observasi yang tetap ditahan memiliki volume mismatch: CTRA dan KLBF 2 Oktober, MIKA 5 Oktober. Gap baseline pada metode lama menahan lima observasi tambahan.

Kedua metode menghasilkan tiga hard hits BSDE pada 2, 5, 6 Oktober, dengan BSDE aktif 6 Oktober. Ini berbeda dari snapshot produk 30 September yang hanya memiliki BBCA aktif; snapshot produk belum digeser.

Replay dengan tambahan Oktober menghasilkan seluruh baris sampai 30 September identik dengan eksperimen sebelumnya (prefix assertion PASS). Seluruh payload produk tetap memiliki hash yang sama. Empat tes baseline lulus, termasuk pelestarian kalender harga/volume saat broker kosong. 0 request API.

Perintah ulang: `python -m research.signal_json_valid_baseline --max-age 25 --analysis-end 2026-10-06`. Output `valid_baseline_experiment/25_oos/comparison.json` menyimpan perbandingan lengkap. Pemeriksaan empat sesi ini bukan validasi prediksi harga/return. Kebijakan lifecycle melewati gap singkat belum diubah atau diuji.

## Aktivasi history enam bulan

Atas permintaan pengguna, profil alternatif kini tersedia di `payloads/valid_baseline_v1`, menjadi default launcher. Seluruh 28 saham menampilkan 121 sesi 1 April–30 September; 65 episode historis dan 79 hard hits. ADRO mempunyai 2 episode (19–23 Juni dan 9–11 September). Snapshot akhir tetap 30 September, dengan BBCA sebagai satu-satunya investigasi aktif. Header dan Methodology menyatakan baseline alternatif.

Broker memakai lifecycle alternatif yang sama, termasuk 66 episode hingga 6 Oktober; 3500 sesi broker divalidasi. Gap tetap memutus segmen lifecycle; fitur menjembatani gap tidak diaktifkan. Metode ini eksperimental, belum membuktikan return prediktif.

140 payload ticker, 121 sesi per saham, serta kecocokan context episode broker lulus validasi. Semua 28 endpoint activity/history berhasil dibaca melalui API lokal. Build frontend dan 40 assertions frontend lulus. Versi ketat `expanded_v2` dan pilot `pilot_v2` tetap tersimpan utuh.

Rebuild: `python -m research.signal_build_valid_baseline`. Validasi melalui launcher: `./run_pilot_windows.ps1 -Mode Validate -Dataset valid_baseline_v1`. Kembali ke metode ketat: jalankan Backend dengan `-Dataset expanded_v2`. Tidak ada API eksternal atau credits dipakai.
