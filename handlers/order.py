"""
handlers/order.py — Alur Pembelian, Voucher, & Upload Bukti Bayar
=================================================================
Alur:
  buy_{id}           → Tawaran pakai voucher + buat pesanan
  apply_voucher_{id} → Entry ConversationHandler state WAITING_VOUCHER
  skip_voucher_{id}  → Lewati voucher, langsung buat pesanan
  [text voucher]     → receive_voucher → validasi & terapkan
  upload_proof_{id}  → Entry ConversationHandler (minta foto)
  [photo message]    → receive_proof → kirim ke admin
  cancel_proof       → Batalkan conversation
  cancel_order_{id}  → Batalkan pesanan
"""
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import ADMIN_IDS, PAYMENT_METHODS, QRIS_FILE_ID
from utils import keyboards, messages

logger = logging.getLogger(__name__)

# State ConversationHandler
WAITING_VOUCHER = 0
WAITING_PROOF   = 1


# ── Helper ────────────────────────────────────────────────────────

async def _show_payment_info(query_or_message, context, order, product):
    """Tampilkan halaman info pembayaran (digunakan setelah buat order)."""
    text = messages.payment_info_message(order, product, PAYMENT_METHODS)
    kb   = keyboards.upload_proof_keyboard(order["id"])

    if hasattr(query_or_message, "edit_message_text"):
        await query_or_message.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await query_or_message.reply_text(text, parse_mode="HTML", reply_markup=kb)

    # Kirim QRIS jika ada
    if QRIS_FILE_ID:
        try:
            uid = query_or_message.message.chat.id if hasattr(query_or_message, "message") else query_or_message.chat.id
            await context.bot.send_photo(
                chat_id=uid,
                photo=QRIS_FILE_ID,
                caption="📱 <b>Scan QRIS ini untuk pembayaran</b>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Gagal kirim QRIS: %s", e)


# ── Buy ───────────────────────────────────────────────────────────

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User klik tombol Beli — tawari voucher dulu."""
    query = update.callback_query
    await query.answer()

    user       = update.effective_user
    product_id = int(query.data.split("_")[1])

    if db.is_banned(user.id):
        await query.edit_message_text("❌ Akun kamu dibanned. Hubungi admin.")
        return

    existing = db.get_user_pending_order(user.id)
    if existing:
        await query.edit_message_text(
            text=(
                "⚠️ <b>Kamu masih punya pesanan yang belum dibayar!</b>\n\n"
                f"🔖 Kode: <code>{existing['order_code']}</code>\n"
                f"🎮 Produk: {existing['product_name']}\n\n"
                "Selesaikan atau batalkan pesanan tersebut dulu."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 Lanjut Upload Bukti", callback_data=f"upload_proof_{existing['id']}")],
                [InlineKeyboardButton("🗑️ Batalkan Pesanan Lama", callback_data=f"cancel_order_{existing['id']}")],
            ])
        )
        return

    product = db.get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Produk tidak ditemukan.")
        return

    if product["stock_count"] == 0:
        await query.edit_message_text(
            text=(f"⚠️ Maaf, stok <b>{product['name']}</b> sedang habis.\n\nSilakan pilih produk lain."),
            parse_mode="HTML",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    # Simpan product_id di user_data
    context.user_data["buying_product_id"] = product_id

    # Tawari voucher
    await query.edit_message_text(
        text=(
            f"🛒 <b>Konfirmasi Pembelian</b>\n\n"
            f"🎮 Produk : <b>{product['name']}</b>\n"
            f"💰 Harga  : <b>Rp {product['price']:,}</b>\n\n"
            "🏷️ Apakah kamu punya <b>kode voucher</b> diskon?"
        ),
        parse_mode="HTML",
        reply_markup=keyboards.voucher_offer_keyboard(product_id),
    )


async def apply_voucher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User klik 'Punya Kode Voucher' → masuk ConversationHandler state WAITING_VOUCHER."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[2])
    context.user_data["buying_product_id"] = product_id

    await query.edit_message_text(
        "🏷️ <b>Masukkan Kode Voucher</b>\n\n"
        "Ketik kode voucher kamu di bawah ini:\n\n"
        "<i>Contoh: HEMAT10</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Batal", callback_data=f"skip_voucher_{product_id}")
        ]])
    )
    return WAITING_VOUCHER


async def receive_voucher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Terima kode voucher dari user, validasi, lalu buat pesanan."""
    user       = update.effective_user
    product_id = context.user_data.get("buying_product_id")

    if not product_id:
        await update.message.reply_text("❌ Sesi berakhir. Silakan mulai dari /start")
        return ConversationHandler.END

    product = db.get_product(product_id)
    code    = update.message.text.strip()
    result  = db.validate_voucher(code, user.id, product["price"])

    if not result["valid"]:
        await update.message.reply_text(
            f"{result['error']}\n\nKetik kode lain atau tekan Batal.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Batal / Tanpa Voucher", callback_data=f"skip_voucher_{product_id}")
            ]])
        )
        return WAITING_VOUCHER  # Tetap di state ini, beri kesempatan coba lagi

    v = result["voucher"]
    # Buat order dengan voucher
    order = db.create_order(
        user_id=user.id,
        product_id=product_id,
        voucher_id=v["id"],
        voucher_code=v["code"],
        original_price=product["price"],
        final_price=result["final_price"],
    )
    if not order:
        await update.message.reply_text("⚠️ Stok habis! Silakan pilih produk lain.")
        return ConversationHandler.END

    context.user_data["pending_order_id"] = order["id"]
    context.user_data.pop("buying_product_id", None)

    await update.message.reply_text(
        text=messages.payment_info_message(order, product, PAYMENT_METHODS, result),
        parse_mode="HTML",
        reply_markup=keyboards.upload_proof_keyboard(order["id"]),
    )

    if QRIS_FILE_ID:
        try:
            await context.bot.send_photo(chat_id=user.id, photo=QRIS_FILE_ID,
                caption="📱 <b>Scan QRIS ini untuk pembayaran</b>", parse_mode="HTML")
        except Exception as e:
            logger.warning("Gagal kirim QRIS: %s", e)

    return ConversationHandler.END


async def skip_voucher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User klik 'Tidak, lanjut bayar' — buat pesanan tanpa voucher."""
    query = update.callback_query
    await query.answer()

    user       = update.effective_user
    product_id = int(query.data.split("_")[2])
    product    = db.get_product(product_id)

    order = db.create_order(
        user_id=user.id,
        product_id=product_id,
        original_price=product["price"],
        final_price=product["price"],
    )
    if not order:
        await query.edit_message_text("⚠️ Stok habis! Silakan pilih produk lain.",
            reply_markup=keyboards.back_to_catalog_keyboard())
        return ConversationHandler.END

    context.user_data["pending_order_id"] = order["id"]
    context.user_data.pop("buying_product_id", None)

    await _show_payment_info(query, context, order, product)
    return ConversationHandler.END


# ── Cancel Order ──────────────────────────────────────────────────

async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[2])
    db.cancel_order(order_id)
    context.user_data.pop("pending_order_id", None)
    await query.edit_message_text(
        "🚫 Pesanan dibatalkan.\n\nKamu bisa memilih produk baru kapan saja.",
        reply_markup=keyboards.main_menu_keyboard(),
    )


# ── Proof Upload (ConversationHandler) ───────────────────────────

async def upload_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query    = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[-1])
    order    = db.get_order(order_id)

    if not order or order["status"] != "waiting_payment":
        await query.edit_message_text(
            "⚠️ Pesanan tidak valid atau sudah diproses.\n\nKembali ke /start",
            reply_markup=keyboards.main_menu_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["pending_order_id"] = order_id
    await query.edit_message_text(
        text=(
            "📸 <b>Upload Bukti Pembayaran</b>\n\n"
            "Kirim <b>foto/screenshot</b> bukti transfer sekarang.\n\n"
            "Pastikan terlihat:\n"
            "• ✅ Nominal transfer\n"
            "• ✅ Nama/nomor tujuan\n"
            "• ✅ Tanggal & jam transaksi"
        ),
        parse_mode="HTML",
        reply_markup=keyboards.cancel_proof_keyboard(),
    )
    return WAITING_PROOF


async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user     = update.effective_user
    order_id = context.user_data.get("pending_order_id")

    if not order_id:
        await update.message.reply_text("❌ Sesi berakhir. Silakan mulai dari /start",
            reply_markup=keyboards.back_to_main_keyboard())
        return ConversationHandler.END

    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    db.submit_proof(order_id, file_id)

    order   = db.get_order(order_id)
    product = db.get_product(order["product_id"])

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=messages.admin_new_order_message(order, product, user),
                parse_mode="HTML",
                reply_markup=keyboards.admin_order_action_keyboard(order_id),
            )
        except Exception as e:
            logger.error("Gagal notifikasi admin %s: %s", admin_id, e)

    await update.message.reply_text(
        text=messages.proof_received_message(order["order_code"]),
        parse_mode="HTML",
        reply_markup=keyboards.main_menu_keyboard(),
    )
    context.user_data.pop("pending_order_id", None)
    return ConversationHandler.END


async def cancel_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop("pending_order_id", None)
    await query.edit_message_text(
        "🚫 Upload dibatalkan.\n\nPesananmu masih tersimpan. Kamu bisa kembali dan upload bukti bayar nanti.",
        reply_markup=keyboards.main_menu_keyboard(),
    )
    return ConversationHandler.END
