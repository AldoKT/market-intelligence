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

Berikutnya: backend read-only dan UI tabel lengkap dengan pencarian/sort, pilihan sesi/episode, ringkasan dominan serta detail riwayat per broker. Preview riset berakhir 6 Oktober; dashboard SIGNAL yang diterima tetap 30 September. UI perlu menyatakan tanggal agar kedua snapshot tidak tercampur. Pengukuran ini deskriptif; belum merupakan sinyal akumulasi atau identifikasi pelaku di balik akun broker.
