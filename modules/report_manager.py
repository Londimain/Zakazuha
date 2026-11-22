# modules/report_manager.py
import sqlite3
import datetime

class ReportManager:
    def __init__(self, db_path):
        self.db_path = db_path
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders_meta (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT,
                    organization TEXT,
                    contact TEXT,
                    category TEXT,
                    fio TEXT,
                    note TEXT,
                    file_path TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER,
                    article TEXT,
                    name TEXT,
                    price TEXT,
                    qty TEXT,
                    pack TEXT,
                    unit TEXT,
                    gtin TEXT,
                    source TEXT
                )
            """)
            try:
                conn.execute("ALTER TABLE orders_meta ADD COLUMN fio TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE orders_meta ADD COLUMN note TEXT")
            except sqlite3.OperationalError:
                pass

    def add_order(self, meta, items):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO orders_meta "
                "(created_at, organization, contact, category, fio, note, file_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(timespec="seconds"),
                 meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""), "")
            )
            order_id = cur.lastrowid
            self._save_items(conn, order_id, items)
            return order_id

    def update_order(self, order_id, meta, items):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE orders_meta SET organization=?, contact=?, category=?, fio=?, note=? WHERE id=?",
                (meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""), order_id)
            )
            self._save_items(conn, order_id, items)

    def update_order_meta(self, order_id, meta):
        """Обновляет только шапку заявки (без изменения товаров)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE orders_meta SET organization=?, contact=?, category=?, fio=?, note=? WHERE id=?",
                (meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""), order_id)
            )

    def _save_items(self, conn, order_id, items):
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        for it in items:
            conn.execute(
                "INSERT INTO order_items (order_id, article, name, price, qty, pack, unit, gtin, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (order_id, it.get("article", ""), it.get("name", ""), it.get("price", ""),
                 it.get("qty", ""), it.get("pack", ""), it.get("unit", ""), it.get("gtin", ""), it.get("source", ""))
            )

    def get_items(self, order_id):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT article, name, price, qty, pack, unit, gtin, source FROM order_items WHERE order_id=?",
                (order_id,)
            ).fetchall()
            return [
                {"article": r[0], "name": r[1], "price": r[2], "qty": r[3], 
                 "pack": r[4], "unit": r[5], "gtin": r[6], "source": r[7]}
                for r in rows
            ]

    def order_exists(self, order_id):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM orders_meta WHERE id=?", (order_id,)).fetchone()
            return row is not None

    def delete_order_meta(self, order_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
            conn.execute("DELETE FROM orders_meta WHERE id=?", (order_id,))

    def list_orders(self, search=""):
        sql = ("SELECT id, created_at, organization, contact, category, fio, note, '' "
               "FROM orders_meta")
        params = []
        if search:
            sql += " WHERE organization LIKE ? OR contact LIKE ? OR category LIKE ? OR fio LIKE ? OR note LIKE ?"
            like = f"%{search}%"
            params = [like, like, like, like, like]
        sql += " ORDER BY created_at DESC"
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(sql, params).fetchall()