"""
main.py — MDFStore_bot Sales Bot Entry Point
==========================================
Jalankan: python main.py
Atau dengan venv: ./venv/bin/python main.py
"""
import logging
import os
import sys

# Pastikan direktori ini ada di sys.path agar import relatif berjalan
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN, STORE_NAME
import config
from database import init_db

from handlers.start   import start_command, help_command, my_orders_command
from handlers.catalog import catalog_callback, category_callback, product_callback
from handlers.order   import (
    buy_callback,
    upload_proof_callback,
    receive_proof,
    cancel_proof_callback,
    cancel_order_callback,
    WAITING_PROOF,
)
from handlers.admin import (
    admin_command,
    admin_callback,
    approve_callback,
    reject_reason_callback,
    reject_callback,
    add_stock_command,
    broadcast_command,
    login_command,
    maintenance_command,
)

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("sales_bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def main():
    # Inisialisasi database & load produk awal
    init_db()
    logger.info("🚀  %s bot starting…", STORE_NAME)

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Maintenance Gate ─────────────────────────────────────────────
    # Ditempatkan di group=-1 (prioritas tertinggi). Jika maintenance aktif
    # dan user bukan admin, balas lalu raise ApplicationHandlerStop agar
    # handler lain di group 0 tidak ikut dieksekusi.
    from telegram.ext import TypeHandler
    from telegram.ext import ApplicationHandlerStop

    async def maintenance_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Blok semua interaksi buyer saat maintenance mode aktif."""
        if not config.MAINTENANCE_MODE:
            return  # normal, biarkan handler lain jalan

        user_id = update.effective_user.id if update.effective_user else None
        if user_id and user_id in config.ADMIN_IDS:
            return  # admin tetap bebas

        # Balas buyer dengan pesan maintenance
        if update.message:
            await update.message.reply_text(
                config.MAINTENANCE_MESSAGE,
                parse_mode="HTML",
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "🔧 Server sedang dalam pemeliharaan. Mohon tunggu ya.",
                show_alert=True,
            )
        raise ApplicationHandlerStop  # Hentikan semua handler selanjutnya

    app.add_handler(TypeHandler(Update, maintenance_gate), group=-1)


    # ── ConversationHandler: upload bukti bayar ──────────────────
    proof_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(upload_proof_callback, pattern=r"^upload_proof_\d+$"),
        ],
        states={
            WAITING_PROOF: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_proof),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_proof_callback, pattern="^cancel_proof$"),
            CommandHandler("start", start_command),
        ],
        per_message=False,
        per_chat=True,
    )

    # ── Commands ──────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",     start_command))
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("pesananku", my_orders_command))
    app.add_handler(CommandHandler("admin",       admin_command))
    app.add_handler(CommandHandler("addstock",    add_stock_command))
    app.add_handler(CommandHandler("broadcast",   broadcast_command))
    app.add_handler(CommandHandler("login",       login_command))
    app.add_handler(CommandHandler("maintenance", maintenance_command))

    # ── ConversationHandler (sebelum handler callback biasa) ──────
    app.add_handler(proof_conv)

    # ── Admin callbacks (prioritas tinggi) ────────────────────────
    app.add_handler(CallbackQueryHandler(approve_callback,       pattern=r"^approve_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_reason_callback, pattern=r"^reject_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_callback,        pattern=r"^reject_do_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_callback,         pattern=r"^admin_"))

    # ── Menu callbacks ────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(start_command,      pattern="^menu_start$"))
    app.add_handler(CallbackQueryHandler(catalog_callback,   pattern="^menu_catalog$"))
    app.add_handler(CallbackQueryHandler(my_orders_command,  pattern="^menu_orders$"))
    app.add_handler(CallbackQueryHandler(help_command,       pattern="^menu_help$"))

    # ── Catalog callbacks ─────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(category_callback,      pattern=r"^cat_\d+$"))
    app.add_handler(CallbackQueryHandler(product_callback,       pattern=r"^prod_\d+$"))
    app.add_handler(CallbackQueryHandler(buy_callback,           pattern=r"^buy_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_order_callback,  pattern=r"^cancel_order_\d+$"))

    # ── Noop (tombol disabled, misal stok habis) ──────────────────
    async def noop(update: Update, _):
        await update.callback_query.answer("Tidak tersedia saat ini.")

    app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

    logger.info("✅  %s bot is running. Ctrl+C to stop.", STORE_NAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
