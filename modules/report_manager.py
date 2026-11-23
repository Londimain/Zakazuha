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
                    file_path TEXT,
                    phone TEXT,
                    email TEXT,
                    month TEXT,
                    status TEXT
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
                    source TEXT,
                    purpose TEXT,
                    article_lower TEXT,
                    name_lower TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS purposes (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    parent_id INTEGER
                )
            """)
            
            # Индекс для order_id безопасен, так как эта колонка была всегда
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")

            # Миграции для существующих БД (добавляем колонки, если их нет)
            for col, col_type in [("fio", "TEXT"), ("note", "TEXT"), ("phone", "TEXT"), ("email", "TEXT"), ("month", "TEXT"), ("status", "TEXT")]:
                try:
                    conn.execute(f"ALTER TABLE orders_meta ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass
                    
            for col in ["purpose", "article_lower", "name_lower"]:
                try:
                    conn.execute(f"ALTER TABLE order_items ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass

            # ТЕПЕРЬ создаем индексы, когда колонки гарантированно существуют
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_art_lower ON order_items(article_lower)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_name_lower ON order_items(name_lower)")

            # Заполнение старых данных (одноразово при запуске)
            cursor = conn.execute("SELECT id, article, name FROM order_items WHERE article_lower IS NULL OR name_lower IS NULL")
            rows = cursor.fetchall()
            for r in rows:
                conn.execute("UPDATE order_items SET article_lower=?, name_lower=? WHERE id=?", 
                             (str(r[1]).lower(), str(r[2]).lower(), r[0]))

    def add_order(self, meta, items):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO orders_meta "
                "(created_at, organization, contact, category, fio, note, file_path, phone, email, month, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(timespec="seconds"),
                 meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""), "",
                 meta.get("phone", ""), meta.get("email", ""), meta.get("month", ""), meta.get("status", ""))
            )
            order_id = cur.lastrowid
            self._save_items(conn, order_id, items)
            return order_id

    def update_order(self, order_id, meta, items):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE orders_meta SET organization=?, contact=?, category=?, fio=?, note=?, phone=?, email=?, month=?, status=? WHERE id=?",
                (meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""),
                 meta.get("phone", ""), meta.get("email", ""), meta.get("month", ""), meta.get("status", ""), order_id)
            )
            self._save_items(conn, order_id, items)

    def update_order_meta(self, order_id, meta):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE orders_meta SET organization=?, contact=?, category=?, fio=?, note=?, phone=?, email=?, month=?, status=? WHERE id=?",
                (meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""),
                 meta.get("phone", ""), meta.get("email", ""), meta.get("month", ""), meta.get("status", ""), order_id)
            )

    def _save_items(self, conn, order_id, items):
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        for it in items:
            art = it.get("article", "")
            name = it.get("name", "")
            conn.execute(
                "INSERT INTO order_items (order_id, article, name, price, qty, pack, unit, gtin, source, purpose, article_lower, name_lower) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (order_id, art, name, it.get("price", ""),
                 it.get("qty", ""), it.get("pack", ""), it.get("unit", ""), it.get("gtin", ""), 
                 it.get("source", ""), it.get("purpose", ""), str(art).lower(), str(name).lower())
            )

    def get_items(self, order_id):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT article, name, price, qty, pack, unit, gtin, source, purpose FROM order_items WHERE order_id=?",
                (order_id,)
            ).fetchall()
            return [
                {"article": r[0], "name": r[1], "price": r[2], "qty": r[3], 
                 "pack": r[4], "unit": r[5], "gtin": r[6], "source": r[7], "purpose": r[8]}
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

    def list_orders(self, search="", date_from=None, date_to=None):
        sql = ("SELECT id, created_at, organization, contact, category, fio, note, '', phone, email, month, status "
               "FROM orders_meta WHERE 1=1")
        params = []
        if search:
            sql += (" AND (LOWER(organization) LIKE ? OR LOWER(contact) LIKE ? OR LOWER(category) LIKE ? OR LOWER(fio) LIKE ? "
                    "OR LOWER(note) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(email) LIKE ? "
                    "OR EXISTS (SELECT 1 FROM order_items oi "
                    "WHERE oi.order_id = orders_meta.id "
                    "AND (oi.article_lower LIKE ? OR oi.name_lower LIKE ?)))")
            like = f"%{search.lower()}%"
            params.extend([like, like, like, like, like, like, like, like, like])
        if date_from:
            sql += " AND created_at >= ?"
            params.append(date_from + "T00:00:00")
        if date_to:
            sql += " AND created_at <= ?"
            params.append(date_to + "T23:59:59")

        sql += " ORDER BY created_at DESC"
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(sql, params).fetchall()

    def find_orders_with_matching_items(self, search):
        """Возвращает set(order_id) отчётов, в товарах которых есть совпадение по артикулу/наименованию."""
        if not search:
            return set()
        like = f"%{search.lower()}%"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT order_id FROM order_items "
                "WHERE article_lower LIKE ? OR name_lower LIKE ?",
                (like, like)
            ).fetchall()
            return {r[0] for r in rows}
        
    # --- Методы для работы со справочником назначений ---
    def get_purposes(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT id, name, parent_id FROM purposes ORDER BY name").fetchall()

    def add_purpose(self, name, parent_id=None):
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("INSERT INTO purposes (name, parent_id) VALUES (?, ?)", (name, parent_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def update_purpose(self, purpose_id, new_name):
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("UPDATE purposes SET name=? WHERE id=?", (new_name, purpose_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def delete_purpose(self, purpose_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM purposes WHERE id=?", (purpose_id,))
            conn.execute("UPDATE purposes SET parent_id = NULL WHERE parent_id=?", (purpose_id,))