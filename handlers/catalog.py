"""
handlers/catalog.py — Browse Katalog Produk
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from utils import keyboards, messages

logger = logging.getLogger(__name__)


async def catalog_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan daftar kategori."""
    query = update.callback_query
    await query.answer()

    categories = db.get_categories()

    if not categories:
        await query.edit_message_text(
            "📭 Belum ada produk tersedia. Cek lagi nanti!",
            reply_markup=keyboards.back_to_main_keyboard(),
        )
        return

    await query.edit_message_text(
        text=messages.catalog_message(),
        parse_mode="HTML",
        reply_markup=keyboards.categories_keyboard(categories),
    )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan produk dalam satu kategori."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    category    = db.get_category(category_id)
    products    = db.get_products_by_category(category_id)

    cat_name = (
        f"{category['emoji']} {category['name']}" if category else "Kategori"
    )

    if not products:
        await query.edit_message_text(
            f"📭 Belum ada produk di kategori <b>{cat_name}</b>.",
            parse_mode="HTML",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    await query.edit_message_text(
        text=messages.category_message(cat_name),
        parse_mode="HTML",
        reply_markup=keyboards.products_keyboard(products, category_id),
    )


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan detail satu produk."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product    = db.get_product(product_id)

    if not product:
        await query.edit_message_text(
            "❌ Produk tidak ditemukan.",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    await query.edit_message_text(
        text=messages.product_detail_message(product),
        parse_mode="HTML",
        reply_markup=keyboards.product_detail_keyboard(product),
    )
