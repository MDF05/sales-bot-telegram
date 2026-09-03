"""
utils/messages.py — Template Pesan Bot
"""
from datetime import datetime
from typing import List, Dict

from config import STORE_NAME, STORE_DESCRIPTION


# ── Status display ────────────────────────────────────────────────
STATUS_EMOJI = {
    "waiting_payment": "⏳",
    "pending_review":  "🔍",
    "delivered":       "✅",
    "rejected":        "❌",
    "cancelled":       "🚫",
}
STATUS_TEXT = {
    "waiting_payment": "Menunggu Pembayaran",
    "pending_review":  "Sedang Direview",
    "delivered":       "Selesai",
    "rejected":        "Ditolak",
    "cancelled":       "Dibatalkan",
}

REJECT_REASONS = {
    1: "Bukti bayar tidak valid",
    2: "Nominal tidak sesuai",
    3: "Bukti sudah expired",
    4: "Duplikat pesanan",
    5: "",
}


# ── Buyer Messages ────────────────────────────────────────────────

def welcome_message(name: str) -> str:
    return (
        f"👋 Halo, <b>{name}</b>!\n\n"
        f"Selamat datang di <b>{STORE_NAME}</b>\n"
        f"<i>{STORE_DESCRIPTION}</i>\n\n"
        "Silakan pilih menu di bawah:"
    )


def help_message(is_admin: bool = False) -> str:
    base = (
        f"❓ <b>Cara Belanja di {STORE_NAME}</b>\n\n"
        "1️⃣ Tekan <b>Katalog Produk</b>\n"
        "2️⃣ Pilih kategori game\n"
        "3️⃣ Pilih produk yang mau dibeli\n"
        "4️⃣ Tekan tombol <b>Beli</b>\n"
        "5️⃣ Transfer sesuai nominal yang tertera\n"
        "6️⃣ Upload <b>foto bukti transfer</b>\n"
        "7️⃣ Tunggu konfirmasi admin <i>(biasanya &lt; 5 menit)</i>\n"
        "8️⃣ Item langsung dikirim ke chat ini ✅\n\n"
        "<b>Commands Umum:</b>\n"
        "/start — Menu utama\n"
        "/pesananku — Riwayat pesanan kamu\n"
        "/help — Tampilkan bantuan ini\n"
        "/login — Login sebagai admin (opsional)\n\n"
    )

    admin_cmds = (
        "<b>Commands Admin:</b>\n"
        "/admin — Buka panel admin & statistik\n"
        "/addstock — Tambah stok digital produk\n"
        "/broadcast — Kirim pesan massal ke pembeli\n"
        "/maintenance on|off — Aktifkan/nonaktifkan mode pemeliharaan\n\n"
    ) if is_admin else ""

    footer = "Ada masalah? Hubungi admin."
    return base + admin_cmds + footer


def catalog_message() -> str:
    return f"🛒 <b>Katalog {STORE_NAME}</b>\n\nPilih kategori game:"


def category_message(cat_name: str) -> str:
    return (
        f"<b>{cat_name}</b>\n\n"
        "Pilih produk:\n"
        "<i>✅ = stok tersedia &nbsp;|&nbsp; ❌ = habis</i>"
    )


def product_detail_message(product) -> str:
    if product["stock_count"] > 0:
        stok_text = f"✅ Tersedia ({product['stock_count']} item)"
    else:
        stok_text = "❌ Stok Habis"

    desc = f"\n📝 {product['description']}" if product["description"] else ""

    return (
        f"{product['category_emoji']} <b>{product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Harga : <b>Rp {product['price']:,}</b>\n"
        f"📦 Stok  : {stok_text}"
        f"{desc}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        "Tekan <b>Beli</b> untuk melanjutkan."
    )


def payment_info_message(order: dict, product, payment_methods: List[Dict]) -> str:
    lines = [
        "🧾 <b>Detail Pesanan</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"🔖 Kode    : <code>{order['order_code']}</code>",
        f"🎮 Produk  : <b>{product['name']}</b>",
        f"💰 Total   : <b>Rp {product['price']:,}</b>",
        "━━━━━━━━━━━━━━━━━━━",
        "",
        "💳 <b>Cara Bayar</b>",
        "",
    ]

    for m in payment_methods:
        lines += [
            f"{m['emoji']} <b>{m['name']}</b>",
            f"   Nomor : <code>{m['number']}</code>",
            f"   A/N   : {m['account_name']}",
            "",
        ]

    lines += [
        "⚠️ <b>Penting:</b>",
        f"• Transfer <b>tepat Rp {product['price']:,}</b>",
        "• Jangan tambahkan angka random",
        "• Setelah transfer → tekan tombol di bawah",
        "",
        "⏰ Pesanan dibatalkan otomatis setelah 24 jam.",
    ]

    return "\n".join(lines)


def proof_received_message(order_code: str) -> str:
    return (
        "✅ <b>Bukti bayar diterima!</b>\n\n"
        f"🔖 Kode Pesanan: <code>{order_code}</code>\n\n"
        "⏳ Admin sedang memverifikasi pembayaran kamu.\n"
        "Item akan dikirim langsung ke chat ini setelah dikonfirmasi.\n\n"
        "<i>Estimasi proses: &lt; 5 menit (jam operasional)</i>"
    )


def order_approved_buyer_message(result: dict, product) -> str:
    return (
        "🎉 <b>Pembayaran Dikonfirmasi!</b>\n\n"
        f"🔖 Kode   : <code>{result['order_code']}</code>\n"
        f"🎮 Produk : <b>{product['name']}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Item kamu:</b>\n\n"
        f"<code>{result['item_content']}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"Terima kasih sudah berbelanja di <b>{STORE_NAME}</b>! 🙏\n"
        "Jangan lupa rekomendasikan ke teman ya! ⭐"
    )


def order_rejected_buyer_message(result: dict, reason: str) -> str:
    reason_text = f"\n📝 Alasan : {reason}" if reason else ""
    return (
        "❌ <b>Pesanan Ditolak</b>\n\n"
        f"🔖 Kode: <code>{result['order_code']}</code>"
        f"{reason_text}\n\n"
        "Silakan hubungi admin jika ada pertanyaan.\n"
        "Kamu bisa coba lagi dengan bukti bayar yang valid."
    )


def my_orders_message(orders: List) -> str:
    if not orders:
        return (
            "📭 <b>Riwayat Pesanan</b>\n\n"
            "Kamu belum memiliki pesanan.\n\n"
            "Tekan <b>Beli Lagi</b> untuk mulai berbelanja!"
        )

    lines = ["📦 <b>Riwayat Pesanan Kamu</b>\n"]
    for o in orders:
        emoji  = STATUS_EMOJI.get(o["status"], "❓")
        status = STATUS_TEXT.get(o["status"], o["status"])
        lines.append(
            f"{emoji} <code>{o['order_code']}</code>\n"
            f"   🎮 {o['product_name']} — Rp {o['product_price']:,}\n"
            f"   📅 {str(o['created_at'])[:10]}  •  {status}\n"
        )

    return "\n".join(lines)


# ── Admin Messages ────────────────────────────────────────────────

def admin_new_order_message(order, product, user) -> str:
    return (
        "🔔 <b>PESANAN BARU!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 Kode    : <code>{order['order_code']}</code>\n"
        f"👤 Buyer   : <b>{user.first_name}</b> (@{user.username or '—'})\n"
        f"🆔 User ID : <code>{user.id}</code>\n"
        f"🎮 Produk  : <b>{product['name']}</b>\n"
        f"💰 Nominal : <b>Rp {product['price']:,}</b>\n"
        f"📅 Waktu   : {order['created_at']}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>Periksa foto bukti bayar di atas, lalu klik Approve atau Reject.</i>"
    )


def admin_panel_message(stats: dict) -> str:
    return (
        "👨‍💼 <b>Panel Admin — MDFStore_bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Hari Ini</b>\n"
        f"   🛒 Order selesai : {stats['today_orders']}\n"
        f"   💰 Pendapatan    : Rp {stats['today_revenue']:,}\n\n"
        "📈 <b>All Time</b>\n"
        f"   ✅ Total order    : {stats['total_orders']}\n"
        f"   💵 Total revenue  : Rp {stats['total_revenue']:,}\n"
        f"   👥 Total customer : {stats['total_customers']}\n\n"
        f"⏳ Pending review : <b>{stats['pending_count']}</b>"
    )


def admin_report_message(stats: dict) -> str:
    return (
        "📊 <b>Laporan Penjualan</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Hari Ini:</b>\n"
        f"• Order selesai : {stats['today_orders']}\n"
        f"• Pendapatan    : Rp {stats['today_revenue']:,}\n\n"
        "<b>All Time:</b>\n"
        f"• Total order    : {stats['total_orders']}\n"
        f"• Total revenue  : Rp {stats['total_revenue']:,}\n"
        f"• Total customer : {stats['total_customers']}\n\n"
        f"<i>Diperbarui: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>"
    )
