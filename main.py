"""
main.py — MDFStore_bot Sales Bot Entry Point
==========================================
Jalankan: python main.py
Atau dengan venv: ./venv/bin/python main.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    TypeHandler,
    filters,
)

from config import BOT_TOKEN, STORE_NAME
import config
from database import init_db

from handlers.start   import start_command, help_command, my_orders_command
from handlers.catalog import catalog_callback, category_callback, product_callback
from handlers.order   import (
    buy_callback,
    apply_voucher_callback,
    skip_voucher_callback,
    receive_voucher,
    upload_proof_callback,
    receive_proof,
    cancel_proof_callback,
    cancel_order_callback,
    WAITING_VOUCHER,
    WAITING_PROOF,
)
from handlers.admin import (
    admin_command,
    admin_callback,
    admin_voucher_callback,
    approve_callback,
    reject_reason_callback,
    reject_callback,
    add_stock_command,
    broadcast_command,
    login_command,
    createvoucher_command,
    vouchers_command,
    delvoucher_command,
    setbanner_command,
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
    init_db()
    logger.info("🚀  %s bot starting…", STORE_NAME)

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Maintenance Gate ─────────────────────────────────────────────
    from telegram.ext import ApplicationHandlerStop

    async def maintenance_gate(update: Update, context):
        if not config.MAINTENANCE_MODE:
            return
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and user_id in config.ADMIN_IDS:
            return
        if update.message:
            await update.message.reply_text(config.MAINTENANCE_MESSAGE, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.answer(
                "🔧 Server sedang dalam pemeliharaan. Mohon tunggu ya.", show_alert=True
            )
        raise ApplicationHandlerStop

    app.add_handler(TypeHandler(Update, maintenance_gate), group=-1)

    # ── ConversationHandler: beli + voucher + upload bukti ──────────
    buy_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(apply_voucher_callback, pattern=r"^apply_voucher_\d+$"),
            CallbackQueryHandler(skip_voucher_callback,  pattern=r"^skip_voucher_\d+$"),
            CallbackQueryHandler(upload_proof_callback,  pattern=r"^upload_proof_\d+$"),
        ],
        states={
            WAITING_VOUCHER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_voucher),
                CallbackQueryHandler(skip_voucher_callback, pattern=r"^skip_voucher_\d+$"),
            ],
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

    # ── Commands ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",         start_command))
    app.add_handler(CommandHandler("help",          help_command))
    app.add_handler(CommandHandler("pesananku",     my_orders_command))
    app.add_handler(CommandHandler("admin",         admin_command))
    app.add_handler(CommandHandler("addstock",      add_stock_command))
    app.add_handler(CommandHandler("broadcast",     broadcast_command))
    app.add_handler(CommandHandler("login",         login_command))
    app.add_handler(CommandHandler("maintenance",   maintenance_command))
    app.add_handler(CommandHandler("createvoucher", createvoucher_command))
    app.add_handler(CommandHandler("vouchers",      vouchers_command))
    app.add_handler(CommandHandler("delvoucher",    delvoucher_command))
    app.add_handler(CommandHandler("setbanner",     setbanner_command))

    # ── ConversationHandler (prioritas tinggi) ────────────────────
    app.add_handler(buy_conv)

    # ── Buy callback (sebelum masuk conversation) ─────────────────
    app.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy_\d+$"))

    # ── Admin callbacks ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(approve_callback,       pattern=r"^approve_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_reason_callback, pattern=r"^reject_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_callback,        pattern=r"^reject_do_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_voucher_callback, pattern=r"^admin_voucher"))
    app.add_handler(CallbackQueryHandler(admin_callback,         pattern=r"^admin_"))

    # ── Menu callbacks ────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(start_command,     pattern="^menu_start$"))
    app.add_handler(CallbackQueryHandler(catalog_callback,  pattern="^menu_catalog$"))
    app.add_handler(CallbackQueryHandler(my_orders_command, pattern="^menu_orders$"))
    app.add_handler(CallbackQueryHandler(help_command,      pattern="^menu_help$"))

    # ── Catalog callbacks ─────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(category_callback,     pattern=r"^cat_\d+$"))
    app.add_handler(CallbackQueryHandler(product_callback,      pattern=r"^prod_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_order_callback, pattern=r"^cancel_order_\d+$"))

    # ── Noop ──────────────────────────────────────────────────────
    async def noop(update: Update, _):
        await update.callback_query.answer("Tidak tersedia saat ini.")

    app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

    logger.info("✅  %s bot is running. Ctrl+C to stop.", STORE_NAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
