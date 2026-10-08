# SIGNAL

SIGNAL membantu investor saham Indonesia menelusuri aktivitas pasar yang tidak biasa dengan menghubungkan harga, aktivitas transaksi, broker, dan konteks perusahaan dalam satu alur riset.

Proyek tim **GOTO HOLDER** untuk **Sectors Hackathon 2026**, menggunakan data dari Sectors API.

## Demo statis

**[Buka demo SIGNAL](https://aldokt.github.io/market-intelligence/#/)**

Demo mencakup **28 saham** dengan periode analisis **1 April–30 September 2026**. Snapshot harga dan status investigasi bertanggal **30 September 2026**. Data broker/OOS tertentu berlanjut sampai 6 Oktober; konteks perusahaan dan berita memiliki tanggal masing-masing.

Demo menggunakan JSON yang sudah disimpan. Tidak ada backend atau request Sectors API saat pengunjung membuka situs. Data tidak diperbarui secara real-time. Watchlist disimpan di browser masing-masing, tanpa sinkronisasi akun.

## Fitur

- **Overview:** spotlight, investigasi terbaru, dan grafik harga interaktif.
- **Investigations:** pencarian saham, filter investigasi, dan quick view.
- **Summary:** ringkasan bukti pendukung/berlawanan, confidence score, dan grafik harga.
- **Market Activity:** indikator aktivitas transaksi dan perbandingan terhadap baseline.
- **Broker:** seluruh baris buy/sell yang tersedia, pilihan sesi/episode, dan Broker Flow.
- **Context:** informasi perusahaan, fundamental, perbandingan perusahaan, dan berita yang tersedia.
- **History:** perkembangan investigasi sepanjang periode analisis.
- **Watchlist:** saham pilihan pengguna di penyimpanan lokal browser.
- **Methodology:** aturan deteksi, confidence, dan lifecycle investigasi.

Antarmuka menggunakan tema Graphite Ice, navbar liquid glass, dan grafik interaktif TradingView Lightweight Charts.

## Cara kerja

Data Sectors API disimpan sebagai JSON, dianalisis oleh modul riset, kemudian diubah menjadi payload yang dibaca aplikasi.

Hard spot terdeteksi jika seluruh syarat terpenuhi:

1. Skor kompresi harga minimal **55**.
2. Skor aktivitas minimal **50**.
3. Minimal dua indikator—nilai transaksi, volume, atau jumlah transaksi—mencapai **1,2× baseline**.

Skor aktivitas menggabungkan 40% nilai transaksi, 30% volume, dan 30% jumlah transaksi. Baseline aktivitas menggunakan 20 observasi valid dalam batas umur 25 sesi terjadwal pada dataset `valid_baseline_v1`; analisis rentang harga memerlukan minimal 24 sesi histori awal.

Confidence menggabungkan 25% kompresi harga, 30% aktivitas, 20% persistensi, 15% partisipasi, dan 10% dukungan aliran dana asing. Skor ini menunjukkan **kekuatan bukti, bukan probabilitas kenaikan harga**. Data kosong tetap tidak diketahui, bukan nol; gap dapat membatasi penilaian dan memutus segmen investigasi.

## Menjalankan lokal di Windows

Prasyarat: Git, Python **3.13**, dan Node.js **22** dengan npm. Jalankan perintah dari folder utama repository, bukan dari `backend`.

### Instalasi pertama

```powershell
git clone https://github.com/AldoKT/market-intelligence.git
cd market-intelligence
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r research/requirements-json-pilot.txt
npm --prefix frontend ci
.\.venv\Scripts\python.exe -m research.signal_restore_checkpoint
```

Restorasi checkpoint memeriksa hash dan mengembalikan data lokal yang belum ada, termasuk broker views. Tidak ada request API dan data berbeda yang sudah ada tidak ditimpa.

### Jalankan backend dan frontend bersama

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_signal_windows.ps1
```

- Website: http://127.0.0.1:5173
- Dokumentasi API: http://127.0.0.1:8001/docs

Biarkan terminal terbuka. Tekan **Ctrl+C** untuk menghentikan kedua server. Jika port sudah dipakai, hentikan server sebelumnya atau pilih port lain:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_signal_windows.ps1 -BackendPort 8002 -FrontendPort 5174
```

Tidak perlu API key untuk menjalankan data demo yang sudah tersimpan.

## Build dan preview demo statis

Mode ini hanya membutuhkan Node.js/npm dan Python untuk ekspor JSON; dependensi riset dan FastAPI tidak diperlukan.

```powershell
cd frontend
npm ci
npm run build:pages
npm run test:static
npm run preview:pages -- --port 5185
```

Buka http://127.0.0.1:5185/market-intelligence/. Hash routing mendukung reload langsung pada halaman detail saham.

Workflow [GitHub Pages](.github/workflows/pages.yml) membangun dan menerbitkan demo dari `main`. Pada **Settings → Pages**, pilih **GitHub Actions** sebagai Source. Lihat [panduan deployment](SIGNAL_GITHUB_PAGES.md). JSON yang dikirim bersama demo dapat diunduh publik.

## Validasi

Dari folder utama repository setelah instalasi dan restorasi checkpoint:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_pilot_windows.ps1 -Mode Validate -Dataset valid_baseline_v1
$env:PYTHONPATH = "$PWD;$PWD\backend"
.\.venv\Scripts\python.exe -m pytest backend/tests
```

Untuk memeriksa build statis, gunakan `npm run build:pages` dan `npm run test:static` dari `frontend`.

## Struktur repository

```text
frontend/                 React, TypeScript, Vite, Lightweight Charts
backend/                  API FastAPI read-only untuk JSON lokal
research/                 Detektor, lifecycle, audit, dan pembentuk payload
research/data/checkpoints/ Checkpoint data untuk reproduksi offline
payloads/valid_baseline_v1/ Payload aktif untuk demo 28 saham
run_signal_windows.ps1    Launcher backend dan frontend
run_pilot_windows.ps1     Validasi atau menjalankan server secara terpisah
```

Alur aplikasi lokal: **JSON → analisis riset → payload → FastAPI → React**. Alur Pages: **payload/checkpoint → ekspor JSON → React statis**. Dataset pilot dan snapshot lama tetap tersedia untuk riset; demo saat ini menggunakan `valid_baseline_v1`.

## Cakupan saham

ADRO, AMMN, ANTM, ASII, BBCA, BBNI, BBRI, BMRI, BRMS, BSDE, CPIN, CTRA, EMTK, GOTO, ICBP, INCO, INDF, ISAT, KLBF, MDKA, MIKA, MYOR, NCKL, PGAS, PTBA, TINS, TLKM, UNTR.

## Data dan batasan

SIGNAL merupakan prototipe riset berbasis data historis. Kelengkapan sumber tidak dijamin; broker menunjukkan aktivitas yang dilaporkan, bukan identitas atau maksud investor. Fitur tidak menjamin hasil investasi.

Jangan commit API key, token, atau `.env` pribadi. Fetch berbayar memerlukan persetujuan daftar request dan anggaran. Baca [Data & Secret Notice](DATA_NOTICE.md) sebelum mendistribusikan data, serta [catatan pilot JSON](SIGNAL_PHASE1_JSON_PILOT.md) untuk riwayat implementasi awal.
