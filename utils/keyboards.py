"""
utils/keyboards.py — Inline Keyboard Builders
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List


# ── Buyer Keyboards ───────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Katalog Produk", callback_data="menu_catalog")],
        [
            InlineKeyboardButton("📦 Pesanan Saya", callback_data="menu_orders"),
            InlineKeyboardButton("❓ Bantuan",       callback_data="menu_help"),
        ],
    ])


def categories_keyboard(categories: List) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(f"{c['emoji']} {c['name']}", callback_data=f"cat_{c['id']}")]
        for c in categories
    ]
    kb.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_start")])
    return InlineKeyboardMarkup(kb)


def products_keyboard(products: List, category_id: int) -> InlineKeyboardMarkup:
    kb = []
    for p in products:
        icon  = "✅" if p["stock_count"] > 0 else "❌"
        label = f"{icon} {p['name']} — Rp {p['price']:,}"
        kb.append([InlineKeyboardButton(label, callback_data=f"prod_{p['id']}")])
    kb.append([InlineKeyboardButton("◀️ Kembali ke Kategori", callback_data="menu_catalog")])
    return InlineKeyboardMarkup(kb)


def product_detail_keyboard(product) -> InlineKeyboardMarkup:
    kb = []
    if product["stock_count"] > 0:
        kb.append([InlineKeyboardButton(
            f"🛒 Beli — Rp {product['price']:,}",
            callback_data=f"buy_{product['id']}",
        )])
    else:
        kb.append([InlineKeyboardButton("❌ Stok Habis", callback_data="noop")])

    kb.append([InlineKeyboardButton(
        f"◀️ {product['category_emoji']} {product['category_name']}",
        callback_data=f"cat_{product['category_id']}",
    )])
    return InlineKeyboardMarkup(kb)


def voucher_offer_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Tombol tawaran voucher sebelum checkout."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏷️ Ya, saya punya kode voucher!", callback_data=f"apply_voucher_{product_id}")],
        [InlineKeyboardButton("🛒 Tidak, langsung bayar", callback_data=f"skip_voucher_{product_id}")],
        [InlineKeyboardButton("◀️ Batal", callback_data="menu_catalog")],
    ])


def upload_proof_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Upload Bukti Bayar", callback_data=f"upload_proof_{order_id}")],
        [InlineKeyboardButton("❌ Batal Pesanan",      callback_data=f"cancel_order_{order_id}")],
    ])


def cancel_proof_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Batal", callback_data="cancel_proof")
    ]])


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_start")
    ]])


def back_to_catalog_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ Kembali ke Katalog", callback_data="menu_catalog")
    ]])


# ── Admin Keyboards ───────────────────────────────────────────────

def admin_menu_keyboard(pending_count: int = 0) -> InlineKeyboardMarkup:
    pending_label = (
        f"📋 Pesanan Pending ({pending_count})" if pending_count > 0
        else "📋 Pesanan Pending"
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(pending_label,         callback_data="admin_orders")],
        [
            InlineKeyboardButton("📦 Kelola Stok",   callback_data="admin_stock"),
            InlineKeyboardButton("📊 Laporan",        callback_data="admin_report"),
        ],
        [InlineKeyboardButton("🎫 Kelola Voucher",   callback_data="admin_voucher")],
        [InlineKeyboardButton("📢 Broadcast",         callback_data="admin_broadcast")],
    ])


def admin_voucher_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Buat Voucher Baru",    callback_data="admin_voucher_create")],
        [InlineKeyboardButton("📋 Daftar Voucher Aktif", callback_data="admin_voucher_list")],
        [InlineKeyboardButton("🗑️ Nonaktifkan Voucher",  callback_data="admin_voucher_deactivate")],
        [InlineKeyboardButton("◀️ Panel Admin",           callback_data="admin_menu")],
    ])


def admin_order_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{order_id}"),
        ],
        [InlineKeyboardButton("📋 Panel Admin", callback_data="admin_menu")],
    ])


def reject_reason_keyboard(order_id: int) -> InlineKeyboardMarkup:
    reasons = [
        ("Bukti bayar tidak valid", 1),
        ("Nominal tidak sesuai",    2),
        ("Bukti sudah expired",     3),
        ("Duplikat pesanan",        4),
        ("Tanpa alasan",            5),
    ]
    kb = [
        [InlineKeyboardButton(r, callback_data=f"reject_do_{order_id}_{code}")]
        for r, code in reasons
    ]
    kb.append([InlineKeyboardButton("◀️ Batal", callback_data="admin_menu")])
    return InlineKeyboardMarkup(kb)


def pending_orders_keyboard(orders: List) -> InlineKeyboardMarkup:
    kb = []
    for o in orders:
        kb.append([
            InlineKeyboardButton(f"✅ {o['order_code']}", callback_data=f"approve_{o['id']}"),
            InlineKeyboardButton("❌",                    callback_data=f"reject_{o['id']}"),
        ])
    kb.append([InlineKeyboardButton("◀️ Panel Admin", callback_data="admin_menu")])
    return InlineKeyboardMarkup(kb)
