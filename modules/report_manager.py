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
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")

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

            try:
                conn.execute("ALTER TABLE order_items ADD COLUMN bought INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_art_lower ON order_items(article_lower)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_name_lower ON order_items(name_lower)")

            cursor = conn.execute("SELECT id, article, name FROM order_items WHERE article_lower IS NULL OR name_lower IS NULL")
            for r in cursor.fetchall():
                conn.execute("UPDATE order_items SET article_lower=?, name_lower=? WHERE id=?",
                             (str(r[1]).lower(), str(r[2]).lower(), r[0]))
                         
    def _save_items(self, conn, order_id, items):
        existing_ids = {row[0] for row in conn.execute(
            "SELECT id FROM order_items WHERE order_id=?", (order_id,)
        ).fetchall()}
        kept_ids = set()

        for it in items:
            art = it.get("article", "")
            name = it.get("name", "")
            bought_val = it.get("bought", 0) or 0
            iid = it.get("id")

            if iid and iid in existing_ids:
                conn.execute(
                    "UPDATE order_items SET article=?, name=?, price=?, qty=?, pack=?, "
                    "unit=?, gtin=?, source=?, purpose=?, article_lower=?, name_lower=?, bought=? "
                    "WHERE id=?",
                    (art, name, it.get("price", ""), it.get("qty", ""),
                     it.get("pack", ""), it.get("unit", ""), it.get("gtin", ""),
                     it.get("source", ""), it.get("purpose", ""),
                     str(art).lower(), str(name).lower(), bought_val, iid)
                )
                kept_ids.add(iid)
            else:
                cur = conn.execute(
                    "INSERT INTO order_items (order_id, article, name, price, qty, pack, "
                    "unit, gtin, source, purpose, article_lower, name_lower, bought) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (order_id, art, name, it.get("price", ""), it.get("qty", ""),
                     it.get("pack", ""), it.get("unit", ""), it.get("gtin", ""),
                     it.get("source", ""), it.get("purpose", ""),
                     str(art).lower(), str(name).lower(), bought_val)
                )
                it["id"] = cur.lastrowid
                kept_ids.add(cur.lastrowid)

        for eid in existing_ids - kept_ids:
            conn.execute("DELETE FROM order_items WHERE id=?", (eid,))

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

    def set_item_bought(self, item_id, bought):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE order_items SET bought=? WHERE id=?",
                (1 if bought else 0, item_id)
            )
            
    def update_order_meta(self, order_id, meta):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE orders_meta SET organization=?, contact=?, category=?, fio=?, note=?, phone=?, email=?, month=?, status=? WHERE id=?",
                (meta.get("organization", ""), meta.get("contact", ""),
                 meta.get("category", ""), meta.get("fio", ""), meta.get("note", ""),
                 meta.get("phone", ""), meta.get("email", ""), meta.get("month", ""), meta.get("status", ""), order_id)
            )

    def update_order_date(self, order_id, date_str):
        """Меняет created_at отчёта. date_str — 'yyyy-MM-dd' или полный ISO."""
        if "T" not in date_str:
            iso = date_str + "T00:00:00"
        else:
            iso = date_str
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE orders_meta SET created_at=? WHERE id=?", (iso, order_id))

    def update_order_month(self, order_id, month):
        """Меняет поле month у отчёта."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE orders_meta SET month=? WHERE id=?", (month, order_id))

    def get_items(self, order_id):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, article, name, price, qty, pack, unit, gtin, source, purpose, bought "
                "FROM order_items WHERE order_id=?",
                (order_id,)
            ).fetchall()
            return [
                {"id": r[0], "article": r[1], "name": r[2], "price": r[3], "qty": r[4],
                 "pack": r[5], "unit": r[6], "gtin": r[7], "source": r[8], "purpose": r[9],
                 "bought": r[10] or 0}
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
                # Получаем старое имя, чтобы обновить его во всех товарах
                row = conn.execute("SELECT name FROM purposes WHERE id=?", (purpose_id,)).fetchone()
                if row:
                    old_name = row[0]
                    conn.execute("UPDATE order_items SET purpose=? WHERE purpose=?", (new_name, old_name))
                
                conn.execute("UPDATE purposes SET name=? WHERE id=?", (new_name, purpose_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def delete_purpose(self, purpose_id):
        with sqlite3.connect(self.db_path) as conn:
            # Получаем имя удаляемого назначения
            row = conn.execute("SELECT name FROM purposes WHERE id=?", (purpose_id,)).fetchone()
            if row:
                name = row[0]
                # Очищаем это назначение у всех сохраненных товаров в отчетах
                conn.execute("UPDATE order_items SET purpose='' WHERE purpose=?", (name,))
            
            conn.execute("DELETE FROM purposes WHERE id=?", (purpose_id,))
            conn.execute("UPDATE purposes SET parent_id = NULL WHERE parent_id=?", (purpose_id,))