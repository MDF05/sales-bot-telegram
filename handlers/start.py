"""
handlers/start.py — /start, /help, /pesananku
"""
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import config
import database as db
from utils import keyboards, messages

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /start dan callback menu_start."""
    user = update.effective_user

    # Simpan/update data user
    db.upsert_customer(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
    )

    text  = messages.welcome_message(user.first_name or "kamu")
    reply = keyboards.main_menu_keyboard()

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )
    else:
        await update.message.reply_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /help dan callback menu_help."""
    is_admin = update.effective_user.id in config.ADMIN_IDS
    text  = messages.help_message(is_admin)
    reply = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_start")
    ]])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )
    else:
        await update.message.reply_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )


async def my_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /pesananku dan callback menu_orders."""
    user   = update.effective_user
    orders = db.get_user_orders(user.id)
    text   = messages.my_orders_message(orders)
    reply  = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Beli Lagi", callback_data="menu_catalog"),
        InlineKeyboardButton("🏠 Menu",      callback_data="menu_start"),
    ]])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )
    else:
        await update.message.reply_text(
            text=text, parse_mode="HTML", reply_markup=reply
        )
