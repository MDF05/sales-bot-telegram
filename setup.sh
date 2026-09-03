#!/bin/bash
# setup.sh — Script setup MDFStore_bot Sales Bot di Ubuntu Server
# Jalankan: bash setup.sh
set -e

echo "========================================"
echo "  🚀 MDFStore_bot Sales Bot - Setup Script"
echo "========================================"
echo ""

# Pastikan python3 dan pip tersedia
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 tidak ditemukan. Install dulu: sudo apt install python3"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "❌ pip3 tidak ditemukan. Install dulu: sudo apt install python3-pip"; exit 1; }

# Buat virtual environment
echo "📦 Membuat virtual environment..."
python3 -m venv venv

# Aktifkan venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip -q

# Install dependencies
echo "📥 Menginstall dependencies..."
pip install -r requirements.txt -q

# Buat folder data jika belum ada
mkdir -p data

# Copy .env jika belum ada
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  File .env sudah dibuat dari template!"
    echo "    Sekarang edit file .env dan isi:"
    echo "    1. BOT_TOKEN  → Token dari @BotFather"
    echo "    2. PAYMENT_BCA → Nomor rekening kamu"
    echo "    3. PAYMENT_BCA_NAME → Nama di rekening"
    echo ""
    echo "    Perintah: nano .env"
fi

echo ""
echo "✅ Setup selesai!"
echo ""
echo "========================================"
echo "  📋 Langkah Selanjutnya"
echo "========================================"
echo ""
echo "1. Edit konfigurasi:"
echo "   nano .env"
echo ""
echo "2. Test jalankan bot:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "3. Install sebagai service (auto-start):"
echo "   sudo cp deploy/sales-bot.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable sales-bot"
echo "   sudo systemctl start sales-bot"
echo ""
echo "4. Cek status service:"
echo "   sudo systemctl status sales-bot"
echo "   sudo journalctl -u sales-bot -f"
echo ""
