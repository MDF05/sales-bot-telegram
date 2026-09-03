"""
Script untuk sinkronisasi products.json ke database SQLite.
Jalankan script ini setiap kali Anda merubah data/products.json
"""
import json
import sqlite3
import os

DB_PATH = "data/sales.db"
JSON_PATH = "data/products.json"

def sync_products():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database {DB_PATH} tidak ditemukan.")
        return
    if not os.path.exists(JSON_PATH):
        print(f"❌ File {JSON_PATH} tidak ditemukan.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Update kategori
        for cat in data.get("categories", []):
            conn.execute("""
                INSERT INTO categories (id, name, emoji, slug, sort_order)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    emoji = excluded.emoji,
                    slug = excluded.slug,
                    sort_order = excluded.sort_order
            """, (cat["id"], cat["name"], cat.get("emoji", "📦"), cat.get("slug", ""), cat.get("sort_order", 0)))
            
        # Update produk
        for prod in data.get("products", []):
            # Cek apakah produk ada, kalau ada update, kalau tidak insert
            # Karena di sqlite kita belum set up ON CONFLICT buat products, kita pisah UPDATE dan INSERT
            cur = conn.execute("SELECT id FROM products WHERE id = ?", (prod["id"],))
            if cur.fetchone():
                conn.execute("""
                    UPDATE products 
                    SET name = ?, description = ?, price = ?, sort_order = ?
                    WHERE id = ?
                """, (prod["name"], prod.get("description", ""), prod["price"], prod.get("sort_order", 0), prod["id"]))
            else:
                conn.execute("""
                    INSERT INTO products (id, category_id, name, description, price, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (prod["id"], prod["category_id"], prod["name"], prod.get("description", ""), prod["price"], prod.get("sort_order", 0)))
            
    print("✅ Berhasil! Database telah di-update dengan data dari products.json")

if __name__ == "__main__":
    sync_products()
