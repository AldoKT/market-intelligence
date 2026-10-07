# Phase2 Broker — review awal

- **Semua broker yang dikembalikan API dipertahankan**, termasuk net nol: 22.759 baris broker/sesi, 375 tampilan harian, enam episode SIGNAL.
- Tabel lengkap memuat beli/jual (IDR, lot, shares, frekuensi), net, harga rata-rata tertimbang, dan porsi aktivitas. Top5 hanya ringkasan, bukan filter tabel.
- Riwayat episode menunjukkan sesi net buy/sell, durasi berurutan, dan pergantian arah. Broker tidak muncul tetap unknown, bukan transaksi nol.
- Sembilan sesi saham kehilangan data broker; tiga sesi 29 Mei memiliki selisih volume. Baris mentah tetap terlihat dengan keterangan; sesi bermasalah tidak memperpanjang streak.
- Kode `--`, `AN`, `JB` belum cocok dengan registry, tetap ditampilkan tanpa nama rekaan. Origin registry adalah asal perusahaan broker, bukan identitas investor.
- Enam pengujian perhitungan lolos. Data OOS diperiksa kembali dari raw; episode BBCA September diteruskan sampai penutupan 2 Oktober. Tidak ada fetch baru atau perubahan aturan SIGNAL.

Contoh daftar lengkap 6 Oktober:

| Saham | Broker yang dikembalikan | Net buy teratas | Net sell teratas |
|---|---:|---|---|
| ANTM | 60 | YU, AK, SQ, SS, AI | XL, KK, XC, CP, YP |
| INCO | 51 | KZ, YP, XL, PP, YU | CC, BK, AK, MG, DR |
| BBCA | 63 | AK, ZP, YU, BB, SQ | KZ, DX, BK, CC, PD |

Backend dan UI tabel broker lengkap sudah tersedia: pencarian/sort, pilihan sesi/episode, ringkasan dominan, detail riwayat, serta grafik net buy/sell per sesi. Snapshot SIGNAL tetap 30 September; data broker sampai 6 Oktober ditampilkan dengan periode terpilih yang eksplisit.

Pemeriksaan penutupan pilot 7 Oktober: 382 file broker cocok persis dengan hasil ulang sumber yang direview, seluruh 22.759 baris tetap tersimpan, dan payload pilot tidak berubah. Pengujian fungsi serta kondisi data bermasalah lolos. Perintah validasi berulang tersedia di `research/signal_validate_broker_phase2.py`.

Batas tersisa: sembilan sesi saham tanpa data broker, tiga mismatch volume 29 Mei, dan tiga kode belum cocok dengan registry. Pengukuran tetap deskriptif; belum menjadi sinyal akumulasi atau identifikasi investor. Fetch tambahan memerlukan daftar request dan persetujuan anggaran. Rework UX masuk Phase3 setelah review Phase2 diterima.
