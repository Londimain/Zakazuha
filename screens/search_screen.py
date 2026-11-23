# screens/search_screen.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QApplication)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QColor, QKeySequence
import re
from utils import show_message

SOURCES = ["TDM", "TDM_img", "IEK", "IEK_svet"]

class SearchWorker(QThread):
    result_ready = Signal(list, str)

    def __init__(self, search_engine, query, sources):
        super().__init__()
        self._engine = search_engine
        self._query = query
        self._sources = sources

    def run(self):
        try:
            results = self._engine.search(self._query, self._sources)
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            results = []
        try:
            self.result_ready.emit(results, self._query)
        except RuntimeError:
            pass

class SearchScreen(QWidget):
    _POPULATE_CHUNK = 40

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self._last_results = []
        self._workers = []
        self.hover_row = -1

        self._populate_rows = []
        self._populate_idx = 0
        self._populate_query = ""

        layout = QVBoxLayout(self)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(400)
        self._search_timer.timeout.connect(self.do_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию или артикулу...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self.do_search)
        layout.addWidget(self.search_input)

        self.src_layout = QHBoxLayout()
        layout.addLayout(self.src_layout)
        self.source_checks = {}
        self.refresh_sources()

        btn_layout = QHBoxLayout()
        
        btn_search = QPushButton("Найти")
        btn_search.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_search.clicked.connect(self.do_search)
        
        btn_paste = QPushButton("Вставить артикулы")
        btn_paste.setStyleSheet("""
            QPushButton { background-color: #f0ad4e; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #ec971f; }
            QPushButton:pressed { background-color: #d58512; }
        """)
        btn_paste.setToolTip("Скопируйте список артикулов из Excel (столбиком) и нажмите сюда.")
        btn_paste.clicked.connect(self.import_from_clipboard)
        
        btn_add = QPushButton("Добавить отмеченные")
        btn_add.setStyleSheet("""
            QPushButton { background-color: #5cb85c; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #449d44; }
            QPushButton:pressed { background-color: #398439; }
        """)
        btn_add.clicked.connect(self.add_checked)
        
        btn_clear = QPushButton("Очистить список")
        btn_clear.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_clear.clicked.connect(self.clear_results)
        
        btn_layout.addWidget(btn_search)
        btn_layout.addWidget(btn_paste)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["", "Артикул", "Наименование"])
        
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setMouseTracking(True)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 30)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(35)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.cellEntered.connect(self.on_cell_entered)
        
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.table.keyPressEvent = self.table_key_press_event
        self.table.mousePressEvent = self.table_mouse_press_event
        
        # ДОБАВЛЯЕМ ОТСЛЕЖИВАНИЕ КУРСОРА МЫШИ ДЛЯ ТАБЛИЦЫ
        self.table.setMouseTracking(True)
        self.table.mouseMoveEvent = self.table_mouse_move_event

    # НОВЫЙ МЕТОД ДЛЯ СБРОСА ВЫДЕЛЕНИЯ, КОГДА КУРСОР НИЖЕ СТРОК
    def table_mouse_move_event(self, event):
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            if self.hover_row != -1:
                self.restore_row_color(self.hover_row)
                self.hover_row = -1
        QTableWidget.mouseMoveEvent(self.table, event)

    def on_cell_entered(self, row, col):
        if self.hover_row == row: return
        if self.hover_row != -1:
            self.restore_row_color(self.hover_row)
        self.hover_row = row
        self.apply_hover_color(row)

    def leaveEvent(self, event):
        if self.hover_row != -1:
            self.restore_row_color(self.hover_row)
            self.hover_row = -1
        super().leaveEvent(event)

    def restore_row_color(self, row):
        if row < 0 or row >= self.table.rowCount(): return
        w = self.table.cellWidget(row, 0)
        cb = w.findChild(QCheckBox) if w else None
        is_checked = cb.isChecked() if cb else False
        bg = QColor("#cce5ff") if is_checked else None
        fg = QColor("black") if is_checked else None
        
        for c in range(self.table.columnCount()):
            if c == 0:
                if w: w.setStyleSheet(f"background-color: {'#cce5ff' if is_checked else 'transparent'};")
            else:
                item = self.table.item(row, c)
                if item:
                    item.setData(Qt.BackgroundRole, bg)
                    item.setData(Qt.ForegroundRole, fg)

    def apply_hover_color(self, row):
        if row < 0 or row >= self.table.rowCount(): return
        w = self.table.cellWidget(row, 0)
        cb = w.findChild(QCheckBox) if w else None
        is_checked = cb.isChecked() if cb else False
        bg = QColor("#a8c8e8") if is_checked else QColor("#e2eaf1")
        fg = QColor("black")
        
        for c in range(self.table.columnCount()):
            if c == 0:
                if w: w.setStyleSheet(f"background-color: {bg.name()};")
            else:
                item = self.table.item(row, c)
                if item:
                    item.setData(Qt.BackgroundRole, bg)
                    item.setData(Qt.ForegroundRole, fg)

    def refresh_sources(self):
        while self.src_layout.count():
            item = self.src_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.source_checks.clear()

        sources = self.main_app.price_manager.get_all_sources()
        if not sources:
            sources = SOURCES
            
        saved_sources = self.main_app.export_config.get("sources", sources)
        for s in sources:
            cb = QCheckBox(s)
            cb.setChecked(s in saved_sources)
            cb.stateChanged.connect(self.on_source_toggled)
            self.source_checks[s] = cb
            self.src_layout.addWidget(cb)
            
        self.src_layout.addStretch()

    def _on_search_text_changed(self, text):
        if not text.strip():
            self._search_timer.stop()
            self._last_results = []
            self._populate_rows = []
            self.table.setRowCount(0)
            self.hover_row = -1
        else:
            self._search_timer.start()

    def do_search(self):
        self._search_timer.stop()
        query = self.search_input.text().strip()
        if not query:
            self._last_results = []
            self._populate_rows = []
            self.table.setRowCount(0)
            self.hover_row = -1
            return

        self._workers = [w for w in self._workers if w.isRunning()]
        active = [s for s, cb in self.source_checks.items() if cb.isChecked()]

        worker = SearchWorker(self.main_app.search_engine, query, active)
        worker.result_ready.connect(self._on_search_result)
        self._workers.append(worker)
        worker.start()

    def _on_search_result(self, results, query):
        if query != self.search_input.text().strip():
            return
        self._start_populate(results, query)

    def _start_populate(self, results, query):
        self._last_results = results
        self._populate_rows = list(results)
        self._populate_idx = 0
        self._populate_query = query
        self.hover_row = -1

        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)

        QTimer.singleShot(0, self._populate_next_chunk)

    def _populate_next_chunk(self):
        if self._populate_query != self.search_input.text().strip():
            self._populate_rows = []
            self.table.setSortingEnabled(True)
            return

        total = len(self._populate_rows)
        start = self._populate_idx
        end = min(start + self._POPULATE_CHUNK, total)

        if start >= end:
            self.table.setSortingEnabled(True)
            return

        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(end)

        for row_idx in range(start, end):
            self._populate_one_row(row_idx, self._populate_rows[row_idx])

        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)

        self._populate_idx = end

        if end < total:
            QTimer.singleShot(0, self._populate_next_chunk)
        else:
            self.table.setSortingEnabled(True)

    def _populate_one_row(self, row_idx, row_data):
        def format_val(val):
            if val is None: return ""
            s = str(val).strip()
            if s.lower() == "none" or s == "": return ""
            try:
                f = float(s.replace(",", "."))
                if f.is_integer(): return str(int(f))
                return str(f)
            except ValueError:
                return s

        cb_widget = QWidget()
        cb_widget.setStyleSheet("background-color: transparent;")
        cb = QCheckBox()
        cb.stateChanged.connect(
            lambda state, r=row_idx, c=cb: self.toggle_row_color(r, c.isChecked())
        )

        cb_layout = QHBoxLayout(cb_widget)
        cb_layout.addWidget(cb)
        cb_layout.setAlignment(Qt.AlignCenter)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row_idx, 0, cb_widget)

        item_art = QTableWidgetItem(format_val(row_data[0]))
        item_art.setFlags(item_art.flags() & ~Qt.ItemIsEditable)
        item_art.setData(Qt.UserRole, row_data)
        self.table.setItem(row_idx, 1, item_art)

        item_name = QTableWidgetItem(format_val(row_data[1]))
        item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row_idx, 2, item_name)

    def import_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            show_message(self, "Внимание", "Буфер обмена пуст!", is_error=True)
            return

        articles = [a.strip().upper() for a in re.split(r'[\n\r\t,;]+', text) if a.strip()]
        if not articles:
            show_message(self, "Внимание", "Не найдено артикулов в тексте!", is_error=True)
            return

        active = [s for s, cb in self.source_checks.items() if cb.isChecked()]
        results = self.main_app.search_engine.search_articles_bulk(articles, active)

        if not results:
            show_message(self, "Поиск", "Ничего не найдено по вставленным артикулам.")
            return

        added = 0
        merged = 0
        for r in results:
            # add_item возвращает True (добавлен), False (объединен с дубликатом)
            if self.main_app.order_manager.add_item(r):
                added += 1
            else:
                merged += 1

        self.main_app.order_scr.refresh()
        self.main_app.update_order_badge()
        
        msg = f"Добавлено новых товаров по артикулам: {added}"
        if merged > 0:
            msg += f"\nОбъединено с уже существующими (увеличено кол-во): {merged}"
            
        show_message(self, "Успех", msg)

    def on_source_toggled(self):
        active = [s for s, cb in self.source_checks.items() if cb.isChecked()]
        self.main_app.export_config["sources"] = active
        self.main_app.save_config()
        if hasattr(self, "search_input") and self.search_input.text().strip():
            self._search_timer.stop()
            self.do_search()

    def table_key_press_event(self, event):
        if event.matches(QKeySequence.Paste):
            self.import_from_clipboard()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.add_checked()
        else:
            QTableWidget.keyPressEvent(self.table, event)

    def table_mouse_press_event(self, event):
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            self.clear_all_checks()
            self.table.clearSelection()
            self.table.setCurrentItem(None)
        QTableWidget.mousePressEvent(self.table, event)

    def clear_all_checks(self):
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    cb.setChecked(False)

    def toggle_row_color(self, row, is_checked):
        if row == self.hover_row:
            self.apply_hover_color(row)
        else:
            self.restore_row_color(row)

    def add_checked(self):
        added = 0
        merged = 0
        for row_idx in range(self.table.rowCount()):
            widget = self.table.cellWidget(row_idx, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    item = self.table.item(row_idx, 1)
                    if item:
                        full_row = item.data(Qt.UserRole)
                        if full_row:
                            # add_item возвращает True (добавлен), False (объединен с дубликатом)
                            if self.main_app.order_manager.add_item(full_row):
                                added += 1
                            else:
                                merged += 1

        if added == 0 and merged == 0:
            show_message(self, "Внимание", "Поставьте галочки на нужных товарах!", is_error=True)
            return

        self.clear_results()
        self.main_app.update_order_badge()
        
        msg = f"Добавлено новых: {added}"
        if merged > 0:
            msg += f"\nОбъединено с уже существующими (увеличено кол-во): {merged}"
            
        show_message(self, "Успех", msg)

    def clear_results(self):
        self._search_timer.stop()
        self._last_results = []
        self._populate_rows = []
        self.table.setRowCount(0)
        self.hover_row = -1
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.search_input.setFocus()

    def on_cell_clicked(self, row, column):
        if column != 0:
            widget = self.table.cellWidget(row, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(not cb.isChecked())