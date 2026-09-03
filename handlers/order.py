"""
handlers/order.py — Alur Pembelian & Upload Bukti Bayar
========================================================
Alur:
  buy_{id}           → Buat pesanan + tampilkan info bayar
  upload_proof_{id}  → Entry ConversationHandler (minta foto)
  [photo message]    → receive_proof → kirim ke admin
  cancel_proof       → Batalkan conversation
  cancel_order_{id}  → Batalkan pesanan (dari halaman info bayar)
"""
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import ADMIN_IDS, PAYMENT_METHODS, QRIS_FILE_ID
from utils import keyboards, messages

logger = logging.getLogger(__name__)

# State ConversationHandler
WAITING_PROOF = 0


# ── Buy ───────────────────────────────────────────────────────────

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User klik tombol Beli — buat pesanan & tampilkan info transfer."""
    query = update.callback_query
    await query.answer()

    user       = update.effective_user
    product_id = int(query.data.split("_")[1])

    # Cek banned
    if db.is_banned(user.id):
        await query.edit_message_text("❌ Akun kamu dibanned. Hubungi admin.")
        return

    # Cek apakah user punya pesanan belum selesai
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
                [InlineKeyboardButton(
                    "📸 Lanjut Upload Bukti",
                    callback_data=f"upload_proof_{existing['id']}"
                )],
                [InlineKeyboardButton(
                    "🗑️ Batalkan Pesanan Lama",
                    callback_data=f"cancel_order_{existing['id']}"
                )],
            ])
        )
        return

    product = db.get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Produk tidak ditemukan.")
        return

    # Cek stok
    if product["stock_count"] == 0:
        await query.edit_message_text(
            text=(
                f"⚠️ Maaf, stok <b>{product['name']}</b> sedang habis.\n\n"
                "Silakan pilih produk lain atau coba lagi nanti."
            ),
            parse_mode="HTML",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    # Buat pesanan
    order = db.create_order(user.id, product_id)
    if not order:
        await query.edit_message_text(
            "⚠️ Stok habis! Silakan pilih produk lain.",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    # Simpan order_id ke user_data sebagai backup
    context.user_data["pending_order_id"] = order["id"]

    # Tampilkan info pembayaran
    await query.edit_message_text(
        text=messages.payment_info_message(order, product, PAYMENT_METHODS),
        parse_mode="HTML",
        reply_markup=keyboards.upload_proof_keyboard(order["id"]),
    )

    # Kirim foto QRIS jika ada
    if QRIS_FILE_ID:
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=QRIS_FILE_ID,
                caption="📱 <b>Scan QRIS ini untuk pembayaran</b>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Gagal kirim QRIS: %s", e)


async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User membatalkan pesanan dari halaman info bayar."""
    query = update.callback_query
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
    """
    Entry point ConversationHandler.
    User klik 'Upload Bukti Bayar' → bot minta foto.
    """
    query = update.callback_query
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
    """
    State WAITING_PROOF — terima foto bukti bayar dari user.
    Kirim notifikasi + foto ke semua admin ID.
    """
    user     = update.effective_user
    order_id = context.user_data.get("pending_order_id")

    if not order_id:
        await update.message.reply_text(
            "❌ Sesi berakhir. Silakan mulai dari /start",
            reply_markup=keyboards.back_to_main_keyboard(),
        )
        return ConversationHandler.END

    # Ambil file_id foto
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    else:
        file_id = update.message.document.file_id

    # Update status order
    db.submit_proof(order_id, file_id)

    order   = db.get_order(order_id)
    product = db.get_product(order["product_id"])

    # Notifikasi ke semua admin
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

    # Konfirmasi ke buyer
    await update.message.reply_text(
        text=messages.proof_received_message(order["order_code"]),
        parse_mode="HTML",
        reply_markup=keyboards.main_menu_keyboard(),
    )

    context.user_data.pop("pending_order_id", None)
    return ConversationHandler.END


async def cancel_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Batalkan proses upload bukti (fallback conversation)."""
    query = update.callback_query
    await query.answer()

    context.user_data.pop("pending_order_id", None)

    await query.edit_message_text(
        "🚫 Upload dibatalkan.\n\nPesananmu masih tersimpan. Kamu bisa kembali dan upload bukti bayar nanti.",
        reply_markup=keyboards.main_menu_keyboard(),
    )

    return ConversationHandler.END
