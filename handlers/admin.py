"""
handlers/admin.py — Panel Admin
=================================
Commands:
  /admin        — Tampilkan statistik + menu admin
  /addstock     — Tambah stok item ke produk
  /broadcast    — Kirim pesan ke semua customer
  /createvoucher — Buat voucher diskon baru
  /vouchers     — Tampilkan semua voucher aktif

Callbacks:
  admin_*           — Navigasi panel admin
  admin_voucher*    — Kelola voucher
  approve_{id}      — Approve pesanan
  reject_{id}       — Tampilkan pilihan alasan reject
  reject_do_{id}_{n} — Eksekusi reject dengan alasan
"""
import logging
from functools import wraps

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import os
from dotenv import set_key
import database as db
from config import ADMIN_IDS
import config
from utils import keyboards, messages

logger = logging.getLogger(__name__)


# ── Decorator ─────────────────────────────────────────────────────

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("❌ Akses ditolak!", show_alert=True)
            else:
                await update.message.reply_text("❌ Command ini hanya untuk admin.")
            return
        return await func(update, context)
    return wrapper


# ── Admin Panel ───────────────────────────────────────────────────

@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan panel admin dengan statistik."""
    stats = db.get_sales_stats()
    text  = messages.admin_panel_message(stats)
    reply = keyboards.admin_menu_keyboard(stats["pending_count"])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )
    else:
        await update.message.reply_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )


@admin_only
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router untuk semua callback dengan prefix admin_"""
    query = update.callback_query
    data  = query.data

    # ── admin_menu ───────────────────────────────────────────────
    if data == "admin_menu":
        await admin_command(update, context)

    # ── admin_orders ─────────────────────────────────────────────
    elif data == "admin_orders":
        orders = db.get_pending_orders()
        if not orders:
            await query.answer("✅ Tidak ada pesanan pending!", show_alert=True)
            return

        lines = [f"📋 <b>Pesanan Pending ({len(orders)})</b>\n"]
        for o in orders:
            lines.append(
                f"🔖 <code>{o['order_code']}</code> — {o['product_name']}\n"
                f"   👤 {o['first_name']} (@{o['username'] or '—'})"
                f" • Rp {o['product_price']:,}\n"
            )

        await query.edit_message_text(
            text="\n".join(lines),
            parse_mode="HTML",
            reply_markup=keyboards.pending_orders_keyboard(orders[:15]),
        )

    # ── admin_report ─────────────────────────────────────────────
    elif data == "admin_report":
        stats = db.get_sales_stats()
        await query.edit_message_text(
            text=messages.admin_report_message(stats),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Kembali", callback_data="admin_menu")
            ]])
        )

    # ── admin_stock ──────────────────────────────────────────────
    elif data == "admin_stock":
        await query.answer()
        categories = db.get_categories()
        lines = ["📦 <b>Status Stok Produk</b>\n"]
        for cat in categories:
            lines.append(f"\n<b>{cat['emoji']} {cat['name']}</b>")
            products = db.get_products_by_category(cat["id"])
            for p in products:
                icon = "✅" if p["stock_count"] > 0 else "❌"
                lines.append(
                    f"  {icon} ID <code>{p['id']:>2}</code>  {p['name']}"
                    f"  — Stok: <b>{p['stock_count']}</b>"
                )
        lines += [
            "",
            "📌 <b>Cara tambah stok:</b>",
            "<code>/addstock [ID] [isi_item]</code>",
            "",
            "Contoh:",
            "<code>/addstock 1 MLBB-XXXX-XXXX-XXXX</code>",
        ]

        await query.edit_message_text(
            text="\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Kembali", callback_data="admin_menu")
            ]])
        )

    # ── admin_broadcast ──────────────────────────────────────────
    elif data == "admin_broadcast":
        await query.answer()
        await query.edit_message_text(
            text=(
                "📢 <b>Broadcast Pesan</b>\n\n"
                "Gunakan command:\n"
                "<code>/broadcast pesan kamu di sini</code>\n\n"
                "Pesan akan dikirim ke semua customer yang pernah berinteraksi dengan bot."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Kembali", callback_data="admin_menu")
            ]])
        )

    else:
        await query.answer()


# ── Approve ───────────────────────────────────────────────────────

@admin_only
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin klik ✅ Approve."""
    query    = update.callback_query
    order_id = int(query.data.split("_")[1])

    await query.answer("⏳ Memproses...")

    result = db.approve_order(order_id, update.effective_user.id)

    if not result:
        await query.answer("❌ Order tidak valid atau sudah diproses!", show_alert=True)
        return

    if result.get("error") == "out_of_stock":
        await query.answer("❌ Stok habis! Tambah stok dulu via /addstock", show_alert=True)
        return

    # Kirim item ke buyer
    product   = db.get_product(result["product_id"])
    item_text = messages.order_approved_buyer_message(result, product)
    try:
        await context.bot.send_message(
            chat_id=result["user_id"],
            text=item_text,
            parse_mode="HTML",
            reply_markup=keyboards.main_menu_keyboard(),
        )
    except Exception as e:
        logger.error("Gagal kirim item ke buyer %s: %s", result["user_id"], e)

    # Update pesan admin (foto + caption / teks biasa)
    ok_note = (
        f"\n\n✅ <b>APPROVED</b> oleh admin\n"
        f"📦 Item: <code>{result['item_content']}</code>"
    )
    try:
        if query.message.photo:
            old = query.message.caption or ""
            await query.edit_message_caption(
                caption=old + ok_note,
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(
                text=f"✅ Order <code>{order_id}</code> di-approve!{ok_note}",
                parse_mode="HTML",
                reply_markup=keyboards.admin_menu_keyboard(),
            )
    except Exception:
        pass  # Pesan sudah lama / sudah di-edit, abaikan


# ── Reject ────────────────────────────────────────────────────────

@admin_only
async def reject_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin klik ❌ Reject → tampilkan pilihan alasan."""
    query    = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[1])

    note = "\n\n❓ <b>Pilih alasan penolakan:</b>"
    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=(query.message.caption or "") + note,
                parse_mode="HTML",
                reply_markup=keyboards.reject_reason_keyboard(order_id),
            )
        else:
            await query.edit_message_text(
                text=f"Reject order <code>{order_id}</code>{note}",
                parse_mode="HTML",
                reply_markup=keyboards.reject_reason_keyboard(order_id),
            )
    except Exception:
        pass


@admin_only
async def reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih alasan → eksekusi reject → notifikasi buyer."""
    query = update.callback_query
    await query.answer("⏳ Memproses...")

    # Format: reject_do_{order_id}_{reason_num}
    parts    = query.data.split("_")   # ["reject", "do", order_id, reason_num]
    order_id = int(parts[2])
    reason_n = int(parts[3])
    reason   = messages.REJECT_REASONS.get(reason_n, "")

    result = db.reject_order(order_id, update.effective_user.id, reason)
    if not result:
        await query.answer("❌ Order tidak valid!", show_alert=True)
        return

    # Notifikasi buyer
    try:
        await context.bot.send_message(
            chat_id=result["user_id"],
            text=messages.order_rejected_buyer_message(result, reason),
            parse_mode="HTML",
            reply_markup=keyboards.main_menu_keyboard(),
        )
    except Exception as e:
        logger.error("Gagal notifikasi buyer %s: %s", result["user_id"], e)

    # Update pesan admin
    reason_display = f" — {reason}" if reason else ""
    note = f"\n\n❌ <b>REJECTED</b> oleh admin{reason_display}"
    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=(query.message.caption or "") + note,
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(
                text=f"❌ Order <code>{order_id}</code> di-reject.{note}",
                parse_mode="HTML",
                reply_markup=keyboards.admin_menu_keyboard(),
            )
    except Exception:
        pass


# ── Add Stock ─────────────────────────────────────────────────────

@admin_only
async def add_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addstock [product_id] [item_content]

    Contoh:
      /addstock 1 MLBB-XXXX-XXXX-XXXX
    """
    args = context.args or []

    # Tampilkan daftar produk jika tanpa argumen
    if len(args) < 2:
        categories = db.get_categories()
        lines = ["📦 <b>Daftar Produk &amp; ID</b>\n"]
        for cat in categories:
            lines.append(f"<b>{cat['emoji']} {cat['name']}</b>")
            products = db.get_products_by_category(cat["id"])
            for p in products:
                lines.append(
                    f"  ID <code>{p['id']:>2}</code>  {p['name']}"
                    f"  — Stok: {p['stock_count']}"
                )
        lines += [
            "",
            "<b>Cara tambah stok:</b>",
            "<code>/addstock [ID] [isi_item]</code>",
            "",
            "Contoh:",
            "<code>/addstock 1 MLBB-XXXX-XXXX-XXXX</code>",
            "<code>/addstock 7 FF-CODE-12345</code>",
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return

    try:
        product_id   = int(args[0])
        item_content = " ".join(args[1:])
    except ValueError:
        await update.message.reply_text(
            "❌ Format salah.\nContoh: <code>/addstock 1 MLBB-XXXX-XXXX</code>",
            parse_mode="HTML",
        )
        return

    product = db.get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"❌ Produk ID <code>{product_id}</code> tidak ditemukan.\n"
            "Gunakan /addstock tanpa argumen untuk lihat daftar ID.",
            parse_mode="HTML",
        )
        return

    db.add_stock_item(product_id, item_content)
    new_count = db.get_stock_count(product_id)

    await update.message.reply_text(
        f"✅ Stok berhasil ditambahkan!\n\n"
        f"📦 Produk : <b>{product['name']}</b>\n"
        f"🔑 Item   : <code>{item_content}</code>\n"
        f"📊 Total stok sekarang: <b>{new_count}</b>",
        parse_mode="HTML",
    )


# ── Broadcast ─────────────────────────────────────────────────────

@admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /broadcast [pesan]
    Kirim pesan ke semua customer yang pernah pakai bot.
    """
    if not context.args:
        await update.message.reply_text(
            "📢 <b>Cara broadcast:</b>\n\n"
            "<code>/broadcast pesan kamu di sini</code>\n\n"
            "Pesan dikirim ke semua customer terdaftar.",
            parse_mode="HTML",
        )
        return

    text  = " ".join(context.args)
    from config import STORE_NAME
    broadcast_text = f"📢 <b>Info dari {STORE_NAME}</b>\n\n{text}"

    customers = db.get_all_customers()
    status_msg = await update.message.reply_text(
        f"📤 Mengirim ke {len(customers)} customer..."
    )

    success, failed = 0, 0
    for customer in customers:
        try:
            await context.bot.send_message(
                chat_id=customer["user_id"],
                text=broadcast_text,
                parse_mode="HTML",
            )
            success += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Broadcast selesai!</b>\n\n"
        f"• Terkirim : {success}\n"
        f"• Gagal    : {failed}",
        parse_mode="HTML",
    )


# ── Login ─────────────────────────────────────────────────────────

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /login [password]
    Login sebagai admin dari device baru.
    """
    user_id = update.effective_user.id
    if user_id in config.ADMIN_IDS:
        await update.message.reply_text("✅ Anda sudah login sebagai Admin.")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text("❌ Gunakan format: /login <password>")
        return

    password = args[0]
    if password == config.ADMIN_PASSWORD:
        config.ADMIN_IDS.append(user_id)
        
        # Simpan ke .env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            new_ids = ",".join(map(str, config.ADMIN_IDS))
            set_key(env_path, "ADMIN_IDS", new_ids)

        await update.message.reply_text(
            "✅ Login berhasil! Anda sekarang adalah Admin.\n"
            "Ketik /help untuk melihat menu Admin."
        )
    else:
        await update.message.reply_text("❌ Password salah.")


# ── Maintenance Mode ────────────────────────────────────────────────

@admin_only
async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /maintenance on  — Aktifkan mode pemeliharaan
    /maintenance off — Nonaktifkan mode pemeliharaan
    """
    args = context.args or []
    if not args or args[0].lower() not in ("on", "off"):
        status = "🔴 AKTIF" if config.MAINTENANCE_MODE else "🟢 NONAKTIF"
        await update.message.reply_text(
            f"🔧 <b>Maintenance Mode</b>\n\n"
            f"Status sekarang: <b>{status}</b>\n\n"
            "Gunakan:\n"
            "<code>/maintenance on</code>  — Aktifkan\n"
            "<code>/maintenance off</code> — Nonaktifkan",
            parse_mode="HTML",
        )
        return

    mode = args[0].lower() == "on"
    config.MAINTENANCE_MODE = mode

    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        set_key(env_path, "MAINTENANCE_MODE", "true" if mode else "false")

    if mode:
        await update.message.reply_text(
            "🔧 <b>Maintenance Mode AKTIF</b>\n\n"
            "Semua pesan dari buyer sekarang akan mendapat balasan pesan pemeliharaan.\n"
            "Gunakan <code>/maintenance off</code> untuk kembali normal.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "✅ <b>Maintenance Mode NONAKTIF</b>\n\nBot kembali beroperasi normal!",
            parse_mode="HTML",
        )


# ── Voucher ────────────────────────────────────────────────────────

@admin_only
async def admin_voucher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan menu kelola voucher."""
    query = update.callback_query
    await query.answer()
    action = query.data  # admin_voucher, admin_voucher_list, admin_voucher_deactivate

    if action == "admin_voucher_list" or action == "admin_voucher":
        vouchers = db.get_active_vouchers()
        await query.edit_message_text(
            text=messages.voucher_list_message(vouchers),
            parse_mode="HTML",
            reply_markup=keyboards.admin_voucher_menu_keyboard(),
        )

    elif action == "admin_voucher_create":
        await query.edit_message_text(
            "🎫 <b>Buat Voucher Baru</b>\n\n"
            "Gunakan command berikut di chat:\n\n"
            "<code>/createvoucher KODE TIPE NILAI MAX_PEMAKAI HARI_BERLAKU</code>\n\n"
            "<b>Contoh:</b>\n"
            "<code>/createvoucher HEMAT10 persen 10 50 7</code>\n"
            "  → Diskon 10%, maks 50 pemakai, berlaku 7 hari\n\n"
            "<code>/createvoucher FLASH5K nominal 5000 10 1</code>\n"
            "  → Potongan Rp 5.000, maks 10 pemakai, berlaku 1 hari",
            parse_mode="HTML",
            reply_markup=keyboards.admin_voucher_menu_keyboard(),
        )

    elif action == "admin_voucher_deactivate":
        await query.edit_message_text(
            "🗑️ <b>Nonaktifkan Voucher</b>\n\n"
            "Gunakan command:\n"
            "<code>/delvoucher KODE</code>\n\n"
            "<i>Contoh: /delvoucher HEMAT10</i>",
            parse_mode="HTML",
            reply_markup=keyboards.admin_voucher_menu_keyboard(),
        )


@admin_only
async def createvoucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /createvoucher KODE TIPE NILAI MAX_PEMAKAI HARI_BERLAKU
    Tipe: persen | nominal
    Contoh: /createvoucher HEMAT10 persen 10 50 7
    """
    args = context.args or []
    if len(args) < 5:
        await update.message.reply_text(
            "❌ Format salah!\n\n"
            "Gunakan:\n"
            "<code>/createvoucher KODE TIPE NILAI MAX_PEMAKAI HARI_BERLAKU</code>\n\n"
            "<b>Contoh:</b>\n"
            "<code>/createvoucher HEMAT10 persen 10 50 7</code>\n"
            "<code>/createvoucher FLASH5K nominal 5000 10 1</code>",
            parse_mode="HTML",
        )
        return

    code, tipe, nilai, max_uses, hari = args[0], args[1].lower(), args[2], args[3], args[4]

    if tipe not in ("persen", "nominal"):
        await update.message.reply_text("❌ Tipe harus \"persen\" atau \"nominal\".")
        return

    try:
        nilai    = int(nilai)
        max_uses = int(max_uses)
        hari     = int(hari)
    except ValueError:
        await update.message.reply_text("❌ Nilai, max_pemakai, dan hari_berlaku harus berupa angka.")
        return

    if tipe == "persen" and not (1 <= nilai <= 100):
        await update.message.reply_text("❌ Diskon persen harus antara 1–100.")
        return

    result = db.create_voucher(
        code=code,
        discount_type=tipe,
        discount_value=nilai,
        max_uses=max_uses,
        days_valid=hari,
        created_by=update.effective_user.id,
    )

    if not result:
        await update.message.reply_text(f"❌ Kode voucher <code>{code.upper()}</code> sudah ada!", parse_mode="HTML")
        return

    tipe_label = f"{nilai}%" if tipe == "persen" else f"Rp {nilai:,}"
    await update.message.reply_text(
        f"✅ <b>Voucher berhasil dibuat!</b>\n\n"
        f"🎫 Kode   : <code>{result['code']}</code>\n"
        f"💸 Diskon  : {tipe_label}\n"
        f"👥 Maks    : {max_uses} pemakai\n"
        f"📅 Berlaku : s/d {str(result['expires_at'])[:10]}",
        parse_mode="HTML",
    )


@admin_only
async def vouchers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/vouchers — Tampilkan semua voucher aktif."""
    vouchers = db.get_active_vouchers()
    await update.message.reply_text(
        text=messages.voucher_list_message(vouchers),
        parse_mode="HTML",
        reply_markup=keyboards.admin_voucher_menu_keyboard(),
    )


@admin_only
async def delvoucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/delvoucher KODE — Nonaktifkan voucher."""
    args = context.args or []
    if not args:
        await update.message.reply_text("❌ Gunakan: /delvoucher KODE")
        return

    code = args[0].upper()
    db.deactivate_voucher(code)
    await update.message.reply_text(
        f"✅ Voucher <code>{code}</code> berhasil dinonaktifkan.",
        parse_mode="HTML",
    )
