# 🛒 DigiStore Sales Bot

Modul ini bertanggung jawab untuk melayani pembelian produk digital (top-up game, voucher, dll) secara otomatis melalui Telegram. Sistem menggunakan **SQLite** sebagai database dan dibangun menggunakan arsitektur *asynchronous* (`python-telegram-bot` v20+).

## ✨ Fitur Utama
1. **Katalog Produk Dinamis**
   - Mendukung berbagai kategori permainan (Mobile Legends, Free Fire, PUBG).
   - Katalog awal di-*load* otomatis dari `products.json`.
   - Menampilkan status stok secara real-time ("Tersedia" atau "Habis").

2. **Sistem Pembayaran Manual & Upload Bukti**
   - Konfigurasi pembayaran fleksibel melalui file `.env`.
   - Mendukung berbagai Bank/E-Wallet (BCA, BSI, Seabank, Bank Jago, DANA, GoPay, ShopeePay).
   - Mendukung QRIS (di-setting menggunakan *file_id* gambar).
   - Terdapat alur *Conversation Handler* yang membimbing pembeli untuk mengunggah foto bukti transfer.

3. **Manajemen Pesanan & Keamanan Stok**
   - Pembeli hanya diperbolehkan memiliki 1 pesanan "menunggu pembayaran" untuk mencegah *spamming*.
   - Saat Admin menekan tombol *Approve*, sistem akan secara otomatis mengambil satu item stok dan mengirimkannya langsung ke *chat* pembeli.

4. **Panel Admin (Interaktif)**
   - Semua bukti bayar baru akan di-*forward* langsung ke Admin beserta tombol *Approve* atau *Reject*.
   - Jika pesanan ditolak (*Reject*), Admin dapat memilih alasan (misal: "Nominal tidak sesuai", "Bukti expired").
   - Command `/admin` untuk melihat laporan harian/total, pendapatan, dan sisa pesanan pending.
   - Command `/addstock` untuk menambah *stock* digital ke produk tertentu.
   - Command `/broadcast` untuk mengirim siaran pesan (promo/info) ke seluruh pelanggan terdaftar.

## 📁 Struktur File & Direktori
Sistem dirancang modular untuk mempermudah perawatan dan pembaharuan (*maintenance*).

- `main.py` — *Entry point* utama yang menggabungkan *handlers*, menghubungkan ke Telegram, dan menjalankan polling.
- `config.py` — Pemroses dan *loader* variabel lingkungan dari file `.env`.
- `database.py` — Pengendali SQLite. Melakukan operasi CRUD untuk tabel *customers*, *categories*, *products*, *stock*, dan *orders*.
- **`handlers/`** — Logika respons pesan pengguna:
  - `start.py` — Merespons `/start`, `/help`, `/pesananku` dan tombol navigasi utamanya.
  - `catalog.py` — Merespons navigasi penjelajahan katalog (dari kategori hingga detil produk).
  - `order.py` — Menangani alur pembuatan pesanan (*checkout*) dan *conversation* unggah bukti bayar.
  - `admin.py` — Diproteksi *decorator* `@admin_only`. Menangani panel `/admin`, persetujuan pesanan, dan penambahan stok.
- **`utils/`** — Modul fungsi pembantu (*helpers*):
  - `keyboards.py` — Generator untuk seluruh tombol *Inline Keyboard* UI bot.
  - `messages.py` — Seluruh templat pesan (teks HTML) yang dikirim oleh bot untuk menjaga kode *handlers* tetap bersih.
- **`data/`** — Tempat menyimpan persisten data (`sales.db`) dan inisialisasi awal (`products.json`).
- **`deploy/`** — File konfigurasi *systemd* daemon (`sales-bot.service`) untuk menjamin bot menyala 24/7 di Ubuntu.
- `setup.sh` — Skrip instalasi satu-klik untuk server Ubuntu.

## 🛠️ Cara Deploy ke Server (Ubuntu)

**1. Persiapan File Konfigurasi (.env)**
Salin file `.env.example` menjadi `.env`. Masukkan token dari `@BotFather` dan nomor rekening/e-wallet pembayaran.
*(Penting: File .env tidak boleh di-commit ke Git!)*

**2. Instalasi dan Virtual Environment**
Jika server Ubuntu menggunakan Python versi terbaru (misal: 3.14), pastikan *package* `venv` sudah terinstal:
```bash
sudo apt install python3.14-venv -y
```
Kemudian jalankan *script setup*:
```bash
bash setup.sh
```

**3. Test Menjalankan Bot**
Sebelum dijalankan di *background*, test secara manual untuk melihat *logs*:
```bash
source venv/bin/activate
python3 main.py
```

**4. Konfigurasi Systemd (Auto-Start)**
Agar bot selalu menyala meski terminal ditutup, dan *auto-restart* jika terjadi *crash*:
```bash
sudo cp deploy/sales-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sales-bot
sudo systemctl start sales-bot
```

## 📝 Panduan Operasional Admin
Pastikan Telegram User ID kamu tercantum dalam `ADMIN_IDS` di file `.env`.
- `/addstock <ID_Produk> <Item>` — Menambah satu stok digital (Contoh: `/addstock 1 MLBB-KODE-123`).
- `/addstock` (Tanpa ID) — Menampilkan daftar lengkap *ID Produk* dan sisa stok masing-masing.
- `/admin` — Membuka panel kontrol.
- `/broadcast <pesan>` — Mengirim pesan langsung ke semua pembeli.

## 🚀 Next Implementation (Roadmap)

Sistem telah dirancang agar mudah diskalakan. Berikut adalah prioritas pengembangan fitur selanjutnya:

### 1. Payment Gateway Otomatis 💸
Sistem verifikasi manual (menunggu admin klik "Approve") seringkali memperlambat proses transaksi, terutama di luar jam operasional.
- **Rencana:** Integrasi dengan API Tripay, Moota, atau Paydisini.
- **Flow:** User checkout → Bot memberikan QRIS/Virtual Account dinamis dari Payment Gateway → Saat user membayar, sistem Payment Gateway akan mengirim sinyal (*Webhook*) ke bot → Bot otomatis merubah status menjadi *Approved* dan mengirim item ke pembeli tanpa campur tangan admin sama sekali (100% otomatis 24/7).

### 2. Fitur Broadcast & Promo 📢
- **Rencana:** Menu khusus di panel admin Telegram untuk mengirim pesan massal.
- **Fungsi:** Mengirimkan info produk baru, diskon, atau kode voucher ke semua user yang pernah menekan `/start` di bot. Sangat krusial untuk mendatangkan pelanggan kembali (*retention*).

### 3. Manajemen Stok Massal (CSV/Excel) 📦
- **Rencana:** Kemampuan untuk *upload* banyak kode item sekaligus tanpa harus mengetik `/addstock` satu per satu.
- **Fungsi:** Admin cukup mengunggah file `.csv` ke bot Telegram, lalu bot akan membacanya dan memasukkan ratusan stok sekaligus ke database SQLite secara otomatis.

### 4. Tampilan Web (Admin Dashboard & Etalase) 🌐
- **Rencana:** Pembuatan aplikasi Web menggunakan framework modern (misal: Next.js atau React).
- **Fungsi Admin:** Dashboard visual yang indah dengan grafik penjualan (*charts*), manajemen kategori, manajemen voucher, dan pemantauan stok yang lebih rapi ketimbang dari obrolan Telegram.
- **Fungsi Pembeli:** Katalog produk (*etalase*) versi website, dimana pembeli bisa melihat-lihat produk layaknya di *e-commerce*, lalu saat menekan tombol "Beli", mereka akan diarahkan (*deep link*) ke bot Telegram untuk transaksi.

### 5. Auto Backup & Restore 💾
Untuk menjaga keamanan data transaksi dan sisa stok, kita memerlukan skrip pencadangan otomatis (Auto Backup).

**Gambaran Flow Backup Otomatis:**
1. Di server, kita memasang sebuah *Cron Job* (penjadwal tugas) yang berjalan setiap 12 atau 24 jam sekali.
2. Saat jadwalnya tiba, *Cron Job* menjalankan script Python/Bash yang akan men-*zip* file `data/sales.db` (database SQLite).
3. Script kemudian memanggil API Telegram untuk mengirim file zip tersebut secara otomatis ke obrolan pribadi Anda (atau grup khusus Admin) sebagai dokumen.
4. Hasilnya: Setiap hari Anda akan menerima pesan masuk dari bot berupa file backup database terbaru.

**Gambaran Flow Restorasi (Restore):**
Jika server mengalami kerusakan parah atau Anda memindahkan bot ke VPS/Server baru:
1. Anda cukup mengunduh (download) file backup `.zip` terbaru dari obrolan Telegram Anda.
2. Ekstrak file tersebut, Anda akan mendapatkan `sales.db`.
3. Pindahkan file tersebut ke folder `data/` di dalam server baru Anda.
4. Jalankan bot (`sudo systemctl restart sales-bot`).
5. Selesai! Seluruh data pesanan, pelanggan, sisa stok, dan saldo akan kembali persis seperti semula.
