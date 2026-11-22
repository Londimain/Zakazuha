# modules/price_manager.py
import os
import zipfile
import sqlite3
import threading
import requests
import pandas as pd
import time
import datetime
from urllib.parse import urlparse

PRICE_SOURCES = {
    "TDM":      "https://tdme.ru/download/priceTDM.xls",
    "TDM_img":  "https://tdme.ru/download/priceTDM_img.xls",
    "IEK":      "https://www.iek.ru/products/price/price-IEK.zip",
    "IEK_svet": "https://www.iek.ru/products/price/price_svetotehnika.xlsm",
}

class PriceManager:
    def __init__(self, db_path, prices_dir):
        self.db_path    = db_path
        self.data_dir   = os.path.dirname(db_path)
        self.prices_dir = prices_dir
        os.makedirs(self.prices_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    source TEXT, article TEXT, name TEXT,
                    price REAL, old_price REAL, pack TEXT, unit TEXT,
                    gtin TEXT, extra TEXT,
                    name_lower TEXT, article_lower TEXT
                )
            """)
            try:
                conn.execute("ALTER TABLE products ADD COLUMN old_price REAL")
            except sqlite3.OperationalError:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_sources (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_name_lower ON products(name_lower)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_article_lower ON products(article_lower)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON products(source)")

    # ---------- Источники ----------

    def get_all_sources(self):
        """Возвращает список всех источников: встроенные + загруженные + пользовательские."""
        result = list(PRICE_SOURCES.keys())
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            rows = conn.execute(
                "SELECT DISTINCT source FROM products WHERE source IS NOT NULL AND source != ''"
            ).fetchall()
            for r in rows:
                if r[0] not in result:
                    result.append(r[0])
            customs = conn.execute("SELECT name FROM custom_sources").fetchall()
            for c in customs:
                if c[0] not in result:
                    result.append(c[0])
        return result

    def get_source_url(self, name):
        """Возвращает URL для источника: сначала из custom_sources, потом из PRICE_SOURCES."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            row = conn.execute("SELECT url FROM custom_sources WHERE name=?", (name,)).fetchone()
            if row and row[0]:
                return row[0]
        return PRICE_SOURCES.get(name)

    def get_custom_sources(self):
        """Возвращает список (name, url) пользовательских источников."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            return conn.execute("SELECT name, url FROM custom_sources ORDER BY name").fetchall()

    def is_custom_source(self, name):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            row = conn.execute("SELECT 1 FROM custom_sources WHERE name=?", (name,)).fetchone()
            return row is not None

    def register_custom_url(self, name, url):
        """Добавляет источник по URL в таблицу (без загрузки)."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("DELETE FROM custom_sources WHERE name=?", (name,))
            conn.execute(
                "INSERT INTO custom_sources (name, url, created_at) VALUES (?, ?, ?)",
                (name, url, datetime.datetime.now().isoformat(timespec="seconds"))
            )

    def update_custom_source_url(self, name, new_url):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("UPDATE custom_sources SET url=? WHERE name=?", (new_url, name))

    def delete_source(self, source_name):
        """Удаляет источник из базы (товары + запись custom_sources)."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("DELETE FROM products WHERE source = ?", (source_name,))
            conn.execute("DELETE FROM custom_sources WHERE name = ?", (source_name,))

    # ---------- Информация о локальном файле ----------

    def get_local_info(self, key):
        """Возвращает (путь, размер_МБ, mtime) или None."""
        url = self.get_source_url(key)
        if not url:
            return None
        if url.startswith("file://"):
            local = url[7:]
        else:
            parsed = urlparse(url)
            fname = os.path.basename(parsed.path) or "download"
            local = os.path.join(self.prices_dir, fname)
        if not os.path.exists(local):
            return (local, 0, None)
        size_mb = round(os.path.getsize(local) / (1024 * 1024), 2)
        return (local, size_mb, os.path.getmtime(local))

    # ---------- Загрузка ----------

    def download(self, url, progress_cb=None):
        parsed = urlparse(url)
        base_name = os.path.basename(parsed.path) or "download"
        name, ext = os.path.splitext(base_name)
        if not ext:
            name = base_name
            ext = ""

        tmp = os.path.join(self.prices_dir, base_name + ".tmp")

        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(1024 * 64):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(int(downloaded / total * 100))

        # Определяем расширение, если его не было в URL
        if not ext:
            with open(tmp, 'rb') as f:
                magic = f.read(8)
            if magic[:2] == b'PK':
                if zipfile.is_zipfile(tmp):
                    with zipfile.ZipFile(tmp) as z:
                        names = z.namelist()
                        is_xlsx = 'xl/workbook.xml' in names or '[Content_Types].xml' in names
                        if is_xlsx:
                            ext = ".xlsx"
                        elif any(n.lower().endswith(('.xls', '.xlsx', '.xlsm')) for n in names):
                            ext = ".zip"
                        else:
                            ext = ".zip"
                else:
                    ext = ".xlsx"
            elif magic[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                ext = ".xls"
            else:
                ext = ".dat"
            base_name = name + ext

        local = os.path.join(self.prices_dir, base_name)
        try:
            if os.path.exists(local):
                os.remove(local)
            os.rename(tmp, local)
        except PermissionError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise Exception(f"Файл {os.path.basename(local)} заблокирован. Закройте Excel!")
        return local

    def extract_if_zip(self, path):
        if path.lower().endswith(".zip"):
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                z.extractall(self.prices_dir)
                return [os.path.join(self.prices_dir, n) for n in names]
        return [path]

    def _get_current_prices(self, source):
        prices = {}
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            rows = conn.execute(
                "SELECT article, price FROM products WHERE source = ?", (source,)
            ).fetchall()
            for r in rows:
                prices[r[0]] = r[1]
        return prices

    def import_to_cache(self, file_path, source, old_prices, sheet_name=0):
        ext = os.path.splitext(file_path)[1].lower()
        print(f"[*] Чтение файла {os.path.basename(file_path)}...")

        try:
            if ext == ".xls":
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine="xlrd", dtype=str, header=None)
            elif ext in (".xlsx", ".xlsm"):
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl", dtype=str, header=None)
            else:
                return
        except Exception as e:
            print(f"[!] Ошибка чтения {file_path}: {e}")
            return

        header_row_idx = None
        for i in range(min(50, len(df))):
            row_vals = [str(val).strip().lower() for val in df.iloc[i].values if pd.notna(val)]
            row_str = " ".join(row_vals)
            if ("артикул" in row_str or "код" in row_str) and (
                "наименование" in row_str or "номенклатура" in row_str or "товар" in row_str
            ):
                header_row_idx = i
                break

        if header_row_idx is None:
            print(f"[!] Не найдены заголовки в {os.path.basename(file_path)}")
            return

        raw_headers = df.iloc[header_row_idx]
        df.columns = [str(c).strip().lower() for c in raw_headers]

        df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        df = df.loc[:, ~df.columns.duplicated()]

        rename_map = {}
        used_targets = set()

        for col in df.columns:
            target = None
            if "артикул" in col or "код" in col:
                target = "article"
            elif "наименование" in col or "название" in col or "номенклатура" in col:
                target = "name"
            elif "цена" in col:
                target = "price"
            elif "упак" in col:
                target = "pack"
            elif "ед" in col and "изм" not in col:
                target = "unit"
            elif "gtin" in col:
                target = "gtin"

            if target and target not in used_targets:
                rename_map[col] = target
                used_targets.add(target)

        df = df.rename(columns=rename_map)

        if "name" not in df.columns or "article" not in df.columns:
            return

        for c in ["price", "pack", "unit", "gtin"]:
            if c not in df.columns:
                df[c] = ""
            else:
                df[c] = df[c].fillna("").astype(str).str.strip()

        df = df[["article", "name", "price", "pack", "unit", "gtin"]].copy()
        df["name"] = df["name"].fillna("").astype(str).str.strip()

        df["old_price"] = df["article"].map(old_prices)
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        df["source"] = source
        df["extra"] = ""
        df = df[df["name"] != ""]
        df = df[df["name"] != "nan"]

        df["name_lower"] = df["name"].str.lower()
        df["article_lower"] = df["article"].str.lower()

        with sqlite3.connect(self.db_path, timeout=30) as conn:
            df.to_sql("products", conn, if_exists="append", index=False)
        print(f"[+] Импортировано {len(df)} строк ({source})")

    def _clear_source(self, source):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("DELETE FROM products WHERE source = ?", (source,))

    def update_source(self, key, progress_cb=None, done_cb=None):
        def job():
            lock_path = None
            try:
                lock_path = self._acquire_lock(timeout=15)

                url = self.get_source_url(key)
                if not url:
                    raise Exception(f"Источник '{key}' не найден")

                old_prices = self._get_current_prices(key)

                if url.startswith("file://"):
                    file_path = url[7:]
                    if not os.path.exists(file_path):
                        raise Exception(f"Исходный файл не найден: {file_path}")
                    files = self.extract_if_zip(file_path)
                else:
                    path = self.download(url, progress_cb)
                    files = self.extract_if_zip(path)

                self._clear_source(key)
                for f in files:
                    if f.lower().endswith((".xls", ".xlsx", ".xlsm")):
                        self.import_to_cache(f, key, old_prices)
                if done_cb:
                    done_cb(True, "OK")
            except Exception as e:
                print(f"[!] ОШИБКА обновления {key}: {e}")
                if done_cb:
                    done_cb(False, str(e))
            finally:
                if lock_path:
                    self._release_lock(lock_path)

        threading.Thread(target=job, daemon=True).start()

    # ---------- Блокировка ----------

    def _acquire_lock(self, timeout=15):
        lock_path = os.path.join(self.data_dir, "update.lock")
        start = time.time()
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return lock_path
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(lock_path) > 600:
                        os.remove(lock_path)
                        continue
                except OSError:
                    continue
                if time.time() - start > timeout:
                    raise Exception(
                        "Обновление уже выполняется другим пользователем. "
                        "Подождите пару минут и попробуйте снова."
                    )
                time.sleep(0.5)

    def _release_lock(self, lock_path):
        try:
            os.remove(lock_path)
        except OSError:
            pass

    # ---------- Пользовательский файл ----------

    def import_custom_file(self, file_path, source_name):
        """Читает пользовательский Excel-файл и добавляет в базу, регистрирует источник."""
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".xls":
                df = pd.read_excel(file_path, engine="xlrd", dtype=str, header=None)
            elif ext in (".xlsx", ".xlsm"):
                df = pd.read_excel(file_path, engine="openpyxl", dtype=str, header=None)
            else:
                raise Exception("Формат не поддерживается. Нужен .xls или .xlsx")

            header_row_idx = None
            for i in range(min(50, len(df))):
                row_vals = [str(val).strip().lower() for val in df.iloc[i].values if pd.notna(val)]
                row_str = " ".join(row_vals)
                if ("артикул" in row_str or "код" in row_str) and (
                    "наименование" in row_str or "номенклатура" in row_str or "товар" in row_str
                ):
                    header_row_idx = i
                    break

            if header_row_idx is None:
                raise Exception("Не найдены колонки 'Артикул' и 'Наименование' в файле.")

            raw_headers = df.iloc[header_row_idx]
            df.columns = [str(c).strip().lower() for c in raw_headers]
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
            df = df.loc[:, ~df.columns.duplicated()]

            rename_map = {}
            used_targets = set()
            for col in df.columns:
                target = None
                if "артикул" in col or "код" in col:
                    target = "article"
                elif "наименование" in col or "название" in col or "номенклатура" in col:
                    target = "name"
                elif "цена" in col:
                    target = "price"
                elif "упак" in col:
                    target = "pack"
                elif "ед" in col and "изм" not in col:
                    target = "unit"
                elif "gtin" in col:
                    target = "gtin"

                if target and target not in used_targets:
                    rename_map[col] = target
                    used_targets.add(target)

            df = df.rename(columns=rename_map)
            if "name" not in df.columns or "article" not in df.columns:
                raise Exception("Не удалось распознать колонки Артикул/Наименование.")

            for c in ["price", "pack", "unit", "gtin"]:
                if c not in df.columns:
                    df[c] = ""
                else:
                    df[c] = df[c].fillna("").astype(str).str.strip()

            df = df[["article", "name", "price", "pack", "unit", "gtin"]].copy()
            df["name"] = df["name"].fillna("").astype(str).str.strip()
            df["price"] = pd.to_numeric(df["price"], errors="coerce")

            df["old_price"] = None
            df["source"] = source_name
            df["extra"] = ""
            df = df[df["name"] != ""]
            df = df[df["name"] != "nan"]

            df["name_lower"] = df["name"].str.lower()
            df["article_lower"] = df["article"].str.lower()

            abs_path = os.path.abspath(file_path)
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("DELETE FROM products WHERE source = ?", (source_name,))
                df.to_sql("products", conn, if_exists="append", index=False)
                conn.execute("DELETE FROM custom_sources WHERE name=?", (source_name,))
                conn.execute(
                    "INSERT INTO custom_sources (name, url, created_at) VALUES (?, ?, ?)",
                    (source_name, "file://" + abs_path,
                     datetime.datetime.now().isoformat(timespec="seconds"))
                )
        except Exception as e:
            raise e