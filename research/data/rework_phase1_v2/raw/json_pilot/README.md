# SIGNAL — dataset pilot JSON

Paket ini menggabungkan 68 respons hasil capture dengan dua respons manual yang sudah direview. Seluruh 70 request pada daftar awal telah menghasilkan respons yang tersimpan. Tiga percobaan Python yang ditolak tidak berisi data dan tidak dihitung sebagai respons data.

## Cakupan

Untuk masing-masing ANTM, INCO dan BBCA:

| Data | Sesi tersedia | Histori sebelum April | Sesi analisis April–September |
|---|---:|---:|---:|
| Daily | 156 | 35 | 121 |
| Foreign flow | 152 | 34 | 118 |
| Broker activity | 152 | 34 | 118 |

Foreign flow dan broker sama-sama tidak mengembalikan 27 Maret, 1 April, 15 April dan 22 April 2026 pada ketiga saham. Kalender tetap memuat tanggal tersebut dan daily tersedia. Jangan menyimpulkan libur/suspensi dari absennya broker/foreign flow, mengisi nol, atau menggantinya dengan sumber lain tanpa review. Total ada 24 kekurangan kombinasi saham–tabel–tanggal, bukan 24 tanggal berbeda.

Histori awal lebih dari 24 sesi tersedia; perhitungan baseline masih harus memeriksa 24 sesi sebelumnya yang sesuai metrik. Kekurangan dalam window baseline tidak otomatis dianggap nol atau dilewati. Data hari ini tidak boleh masuk baseline hari yang sama.

## Berkas dan validasi

- `daily.json`: 468 baris OHLC, volume saham, market cap.
- `foreign_flow.json`: 456 baris foreign flow.
- `broker_activity.json`: 28.782 baris per saham–tanggal–broker. Nilai lot tetap lot; untuk volume saham gunakan lot × 100, dan jangan menjumlahkan beli serta jual menjadi volume satu sisi.
- `broker_registry.json`: 88 kode broker; snapshot saat fetch, bukan bukti keanggotaan historis.
- `raw/`: 70 body respons yang diterima, tanpa mengubah nilainya. File manual adalah salinan body dari Postman; file capture adalah teks body Postman yang di-encode UTF-8, bukan klaim byte HTTP wire asli.
- `*_provenance.json`: sumber file/hash untuk tiap record.
- `review.json`, `request_coverage.json`, `missing_sessions.json`: audit dan kekurangan.
- `broker_daily_totals.json`: diagnostik jumlah beli/jual per sesi.
- `capture_ledger.json`: ledger 68 request capture. Dua respons manual memiliki bukti terpisah pada review sebelumnya.

Hash seluruh 68 file cocok dengan ledger, semuanya HTTP200. Tidak ditemukan konflik record atau kegagalan pemeriksaan OHLC/volume, batas foreign share, identitas net foreign, gross broker nonnegative, identitas net nilai/lot broker, dan foreign component tidak melebihi total. Seluruh 456 sesi broker memiliki jumlah beli/jual nilai, lot dan frekuensi yang seimbang. Keseimbangan internal bukan attestation independen kelengkapan atau kesetaraan market scope; scope tidak tersedia di respons. Null tetap null.

## Anggaran dan langkah berikutnya

Cadangan konservatif adalah 73 credits, sesuai plafon terakhir yang disetujui: 70 request data plus 3 percobaan Python yang ditolak. Tagihan aktual tetap perlu dicocokkan dengan dashboard Sectors. Tidak ada request baru saat audit atau pembuatan paket.

Semua request pada daftar telah dipenuhi; cakupan data belum lengkap untuk empat tanggal di atas. Jangan refetch otomatis. Implementasi SIGNAL berikutnya memakai JSON ini, menandai metrik yang belum tersedia, dan menguji baseline serta rekonsiliasi sebelum detector. Parquet dihentikan, tidak ada file Parquet baru ditulis; UI tetap belakangan.
