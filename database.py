"""
database.py — SQLite Database Manager
=======================================
Semua operasi CRUD untuk produk, stok, pesanan, dan customer.
"""
import sqlite3
import json
import os
import logging
import random
import string
from datetime import datetime
from typing import Optional, List, Dict

from config import DB_PATH, PRODUCTS_JSON

logger = logging.getLogger(__name__)


# ── Connection ────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Init ──────────────────────────────────────────────────────────

def init_db():
    """Buat semua tabel dan load produk awal dari JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT    DEFAULT '',
                first_name  TEXT    DEFAULT '',
                last_name   TEXT    DEFAULT '',
                is_banned   INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
                updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY,
                name        TEXT    NOT NULL,
                emoji       TEXT    DEFAULT '📦',
                slug        TEXT    UNIQUE,
                is_active   INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY,
                category_id INTEGER REFERENCES categories(id),
                name        TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                price       INTEGER NOT NULL,
                is_active   INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS stock (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER REFERENCES products(id),
                content     TEXT    NOT NULL,
                is_sold     INTEGER DEFAULT 0,
                order_id    INTEGER,
                added_at    TEXT    DEFAULT (datetime('now', 'localtime')),
                sold_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code      TEXT    UNIQUE,
                user_id         INTEGER REFERENCES customers(user_id),
                product_id      INTEGER REFERENCES products(id),
                stock_id        INTEGER REFERENCES stock(id),
                status          TEXT    DEFAULT 'waiting_payment',
                proof_file_id   TEXT,
                reject_reason   TEXT    DEFAULT '',
                admin_id        INTEGER,
                created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
                updated_at      TEXT    DEFAULT (datetime('now', 'localtime'))
            );
        """)

    _load_initial_products()
    logger.info("✅ Database initialized: %s", DB_PATH)


def _load_initial_products():
    """Load kategori & produk dari products.json (hanya jika tabel masih kosong)."""
    if not os.path.exists(PRODUCTS_JSON):
        logger.warning("products.json tidak ditemukan: %s", PRODUCTS_JSON)
        return

    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] > 0:
            return  # Sudah diload sebelumnya

        with open(PRODUCTS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        for cat in data.get("categories", []):
            conn.execute(
                "INSERT OR IGNORE INTO categories (id, name, emoji, slug, sort_order) VALUES (?,?,?,?,?)",
                (cat["id"], cat["name"], cat.get("emoji", "📦"), cat.get("slug"), cat.get("sort_order", 0)),
            )

        for prod in data.get("products", []):
            conn.execute(
                "INSERT OR IGNORE INTO products (id, category_id, name, description, price, sort_order) VALUES (?,?,?,?,?,?)",
                (prod["id"], prod["category_id"], prod["name"],
                 prod.get("description", ""), prod["price"], prod.get("sort_order", 0)),
            )

    logger.info("✅ Produk awal berhasil dimuat dari products.json")


# ── Customer ──────────────────────────────────────────────────────

def upsert_customer(user_id: int, username: str, first_name: str, last_name: str = ""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO customers (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                updated_at = datetime('now', 'localtime')
        """, (user_id, username or "", first_name or "", last_name or ""))


def get_customer(user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM customers WHERE user_id = ?", (user_id,)).fetchone()


def is_banned(user_id: int) -> bool:
    row = get_customer(user_id)
    return bool(row and row["is_banned"])


def get_all_customers() -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM customers WHERE is_banned = 0"
        ).fetchall()


# ── Category ──────────────────────────────────────────────────────

def get_categories() -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order, id"
        ).fetchall()


def get_category(category_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()


# ── Product ───────────────────────────────────────────────────────

def get_products_by_category(category_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM stock s
                    WHERE s.product_id = p.id AND s.is_sold = 0) AS stock_count
            FROM products p
            WHERE p.category_id = ? AND p.is_active = 1
            ORDER BY p.sort_order, p.price
        """, (category_id,)).fetchall()


def get_product(product_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM stock s
                    WHERE s.product_id = p.id AND s.is_sold = 0) AS stock_count,
                   c.name  AS category_name,
                   c.emoji AS category_emoji
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
        """, (product_id,)).fetchone()


def get_stock_count(product_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM stock WHERE product_id = ? AND is_sold = 0",
            (product_id,),
        ).fetchone()
        return row["cnt"] if row else 0


# ── Stock ─────────────────────────────────────────────────────────

def add_stock_item(product_id: int, content: str) -> int:
    """Tambahkan satu item ke stok produk. Return ID baris baru."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO stock (product_id, content) VALUES (?, ?)",
            (product_id, content.strip()),
        )
        return cur.lastrowid


def get_all_stock(product_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM stock WHERE product_id = ? ORDER BY added_at",
            (product_id,),
        ).fetchall()


# ── Order ─────────────────────────────────────────────────────────

def _make_order_code() -> str:
    ts   = datetime.now().strftime("%y%m%d")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"DS{ts}{rand}"


def get_user_pending_order(user_id: int) -> Optional[sqlite3.Row]:
    """Cek apakah user punya pesanan waiting_payment yang belum selesai."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT o.*, p.name AS product_name, p.price AS product_price
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            WHERE o.user_id = ? AND o.status = 'waiting_payment'
            ORDER BY o.created_at DESC LIMIT 1
        """, (user_id,)).fetchone()


def create_order(user_id: int, product_id: int) -> Optional[Dict]:
    """
    Buat pesanan baru. Return dict order atau None jika stok habis.
    Hanya buat satu order per user (cegah duplikat).
    """
    with get_conn() as conn:
        # Cek stok tersedia
        stok = conn.execute(
            "SELECT id FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT 1",
            (product_id,),
        ).fetchone()
        if not stok:
            return None

        order_code = _make_order_code()
        cur = conn.execute("""
            INSERT INTO orders (order_code, user_id, product_id, status)
            VALUES (?, ?, ?, 'waiting_payment')
        """, (order_code, user_id, product_id))

        return {
            "id":         cur.lastrowid,
            "order_code": order_code,
            "user_id":    user_id,
            "product_id": product_id,
            "status":     "waiting_payment",
        }


def cancel_order(order_id: int) -> bool:
    """Batalkan pesanan (status → cancelled)."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE orders SET status = 'cancelled',
                              updated_at = datetime('now', 'localtime')
            WHERE id = ? AND status = 'waiting_payment'
        """, (order_id,))
        return True


def submit_proof(order_id: int, proof_file_id: str) -> bool:
    """User upload bukti bayar → status: pending_review."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE orders
            SET status = 'pending_review',
                proof_file_id = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ? AND status = 'waiting_payment'
        """, (proof_file_id, order_id))
        return True


def approve_order(order_id: int, admin_id: int) -> Optional[Dict]:
    """
    Admin approve pesanan → ambil stok → kirim ke buyer.
    Return dict dengan item_content, atau {'error': 'out_of_stock'}.
    """
    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order or order["status"] not in ("pending_review", "waiting_payment"):
            return None

        stok = conn.execute(
            "SELECT * FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT 1",
            (order["product_id"],),
        ).fetchone()
        if not stok:
            return {"error": "out_of_stock"}

        # Tandai stok sebagai terjual
        conn.execute("""
            UPDATE stock SET is_sold = 1, order_id = ?,
                             sold_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (order_id, stok["id"]))

        # Update order
        conn.execute("""
            UPDATE orders
            SET status = 'delivered', stock_id = ?, admin_id = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (stok["id"], admin_id, order_id))

        return {
            "order_id":     order_id,
            "order_code":   order["order_code"],
            "user_id":      order["user_id"],
            "product_id":   order["product_id"],
            "item_content": stok["content"],
        }


def reject_order(order_id: int, admin_id: int, reason: str = "") -> Optional[Dict]:
    """Admin reject pesanan."""
    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return None

        conn.execute("""
            UPDATE orders
            SET status = 'rejected', admin_id = ?, reject_reason = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (admin_id, reason, order_id))

        return {
            "order_id":   order_id,
            "order_code": order["order_code"],
            "user_id":    order["user_id"],
        }


def get_order(order_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT o.*,
                   p.name  AS product_name,
                   p.price AS product_price,
                   c.first_name, c.username
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            LEFT JOIN customers c ON o.user_id = c.user_id
            WHERE o.id = ?
        """, (order_id,)).fetchone()


def get_user_orders(user_id: int, limit: int = 10) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT o.*, p.name AS product_name, p.price AS product_price
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()


def get_pending_orders() -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT o.*,
                   p.name  AS product_name,
                   p.price AS product_price,
                   cu.first_name, cu.username
            FROM orders o
            LEFT JOIN products p  ON o.product_id = p.id
            LEFT JOIN customers cu ON o.user_id   = cu.user_id
            WHERE o.status = 'pending_review'
            ORDER BY o.created_at ASC
        """).fetchall()


# ── Stats ─────────────────────────────────────────────────────────

def get_sales_stats() -> Dict:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        def q(sql, *args):
            return conn.execute(sql, args).fetchone()[0]

        return {
            "total_orders":    q("SELECT COUNT(*) FROM orders WHERE status='delivered'"),
            "today_orders":    q("SELECT COUNT(*) FROM orders WHERE status='delivered' AND DATE(created_at)=?", today),
            "today_revenue":   q("""SELECT COALESCE(SUM(p.price),0) FROM orders o
                                    LEFT JOIN products p ON o.product_id=p.id
                                    WHERE o.status='delivered' AND DATE(o.created_at)=?""", today),
            "total_revenue":   q("""SELECT COALESCE(SUM(p.price),0) FROM orders o
                                    LEFT JOIN products p ON o.product_id=p.id
                                    WHERE o.status='delivered'"""),
            "pending_count":   q("SELECT COUNT(*) FROM orders WHERE status='pending_review'"),
            "total_customers": q("SELECT COUNT(*) FROM customers"),
        }
