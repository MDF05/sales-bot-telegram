"""
config.py — Konfigurasi MDFStore_bot Sales Bot
=============================================
Jangan commit file .env ke git!
"""
import os
from dotenv import load_dotenv

# Load .env dari direktori yang sama dengan file ini
_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_dir, ".env"))


# ── Bot ───────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "GANTI_DENGAN_TOKEN_BOT_BARU")

ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "8821874054").split(",")
    if x.strip().isdigit()
]
ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin123")

# ── Maintenance Mode ──────────────────────────────────────────────
MAINTENANCE_MODE: bool = os.environ.get("MAINTENANCE_MODE", "false").lower() == "true"
MAINTENANCE_MESSAGE: str = os.environ.get(
    "MAINTENANCE_MESSAGE",
    "🔧 <b>Server sedang dalam pemeliharaan</b>\n\n"
    "Mohon maaf atas ketidaknyamanannya. Bot akan kembali normal sebentar lagi.\n\n"
    "Terima kasih atas kesabarannya 🙏",
)

# ── Info Toko ─────────────────────────────────────────────────────
STORE_NAME: str = os.environ.get("STORE_NAME", "🎮 MDFStore_bot")
STORE_DESCRIPTION: str = os.environ.get(
    "STORE_DESCRIPTION",
    "Toko top up game terpercaya • Proses cepat & aman ✅",
)

# ── Pembayaran Manual ─────────────────────────────────────────────
# List metode pembayaran yang aktif (hanya yang ada di .env)
PAYMENT_METHODS: list[dict] = []

_bca = os.environ.get("PAYMENT_BCA", "")
if _bca:
    PAYMENT_METHODS.append({
        "name": "BCA", "emoji": "🏦",
        "number": _bca,
        "account_name": os.environ.get("PAYMENT_BCA_NAME", "Nama Pemilik"),
    })

_ovo = os.environ.get("PAYMENT_OVO", "")
if _ovo:
    PAYMENT_METHODS.append({
        "name": "OVO", "emoji": "💜",
        "number": _ovo,
        "account_name": os.environ.get("PAYMENT_OVO_NAME", "Nama Pemilik"),
    })

_dana = os.environ.get("PAYMENT_DANA", "")
if _dana:
    PAYMENT_METHODS.append({
        "name": "DANA", "emoji": "💙",
        "number": _dana,
        "account_name": os.environ.get("PAYMENT_DANA_NAME", "Nama Pemilik"),
    })

_seabank = os.environ.get("PAYMENT_SEABANK", "")
if _seabank:
    PAYMENT_METHODS.append({
        "name": "SEABANK", "emoji": "🏦",
        "number": _seabank,
        "account_name": os.environ.get("PAYMENT_SEABANK_NAME", "Nama Pemilik"),
    })

_bsi = os.environ.get("PAYMENT_BSI", "")
if _bsi:
    PAYMENT_METHODS.append({
        "name": "BSI", "emoji": "🏦",
        "number": _bsi,
        "account_name": os.environ.get("PAYMENT_BSI_NAME", "Nama Pemilik"),
    })

_gopay = os.environ.get("PAYMENT_GOPAY", "")
if _gopay:
    PAYMENT_METHODS.append({
        "name": "GOPAY", "emoji": "💚",
        "number": _gopay,
        "account_name": os.environ.get("PAYMENT_GOPAY_NAME", "Nama Pemilik"),
    })

_shopeepay = os.environ.get("PAYMENT_SHOPEEPAY", "")
if _shopeepay:
    PAYMENT_METHODS.append({
        "name": "SHOPEEPAY", "emoji": "🧡",
        "number": _shopeepay,
        "account_name": os.environ.get("PAYMENT_SHOPEEPAY_NAME", "Nama Pemilik"),
    })

_jago = os.environ.get("PAYMENT_JAGO", "")
if _jago:
    PAYMENT_METHODS.append({
        "name": "BANK JAGO", "emoji": "🏦",
        "number": _jago,
        "account_name": os.environ.get("PAYMENT_JAGO_NAME", "Nama Pemilik"),
    })

# Default jika tidak ada yang dikonfigurasi (fallback agar bot tidak crash)
if not PAYMENT_METHODS:
    PAYMENT_METHODS = [{
        "name": "BCA", "emoji": "🏦",
        "number": "BELUM_DIKONFIGURASI",
        "account_name": "Isi di .env",
    }]

# File ID foto QRIS (opsional). Upload sekali ke bot, copy file_id-nya.
QRIS_FILE_ID: str = os.environ.get("QRIS_FILE_ID", "")

# ── Database ──────────────────────────────────────────────────────
DB_PATH: str = os.environ.get("DB_PATH", os.path.join(_dir, "data", "sales.db"))
PRODUCTS_JSON: str = os.path.join(_dir, "data", "products.json")

# ── Order Settings ────────────────────────────────────────────────
ORDER_EXPIRY_HOURS: int = int(os.environ.get("ORDER_EXPIRY_HOURS", "24"))

# ── Tripay (untuk upgrade nanti) ──────────────────────────────────
PAYMENT_MODE: str = os.environ.get("PAYMENT_MODE", "manual")  # "manual" | "tripay"
TRIPAY_API_KEY: str = os.environ.get("TRIPAY_API_KEY", "")
TRIPAY_PRIVATE_KEY: str = os.environ.get("TRIPAY_PRIVATE_KEY", "")
TRIPAY_MERCHANT_CODE: str = os.environ.get("TRIPAY_MERCHANT_CODE", "")
TRIPAY_SANDBOX: bool = os.environ.get("TRIPAY_SANDBOX", "true").lower() == "true"
