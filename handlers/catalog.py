"""
handlers/catalog.py — Browse Katalog Produk
"""
import logging

from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes

import database as db
from utils import keyboards, messages

logger = logging.getLogger(__name__)


async def _show_text_menu(query, context, text, reply_markup):
    """Helper untuk update pesan menjadi teks."""
    if query.message.photo:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    else:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


async def catalog_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan daftar kategori."""
    query = update.callback_query
    await query.answer()

    categories = db.get_categories()

    if not categories:
        await _show_text_menu(
            query, context,
            text="📭 Belum ada produk tersedia. Cek lagi nanti!",
            reply_markup=keyboards.back_to_main_keyboard(),
        )
        return

    await _show_text_menu(
        query, context,
        text=messages.catalog_message(),
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
        await _show_text_menu(
            query, context,
            text=f"📭 Belum ada produk di kategori <b>{cat_name}</b>.",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    text = messages.category_message(cat_name)
    kb   = keyboards.products_keyboard(products, category_id)

    if category and category["banner_file_id"]:
        # Tampilkan sebagai gambar
        file_id = category["banner_file_id"]
        if query.message.photo:
            await query.edit_message_media(
                media=InputMediaPhoto(media=file_id, caption=text, parse_mode="HTML"),
                reply_markup=kb,
            )
        else:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=file_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb,
            )
    else:
        # Tampilkan sebagai teks
        await _show_text_menu(query, context, text, kb)


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan detail satu produk."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product    = db.get_product(product_id)

    if not product:
        await _show_text_menu(
            query, context,
            text="❌ Produk tidak ditemukan.",
            reply_markup=keyboards.back_to_catalog_keyboard(),
        )
        return

    # Detail produk kita tampilkan sebagai teks biasa dulu agar bersih
    # (Bisa diubah jadi gambar juga kalau produk punya image)
    await _show_text_menu(
        query, context,
        text=messages.product_detail_message(product),
        reply_markup=keyboards.product_detail_keyboard(product),
    )
