# screens/report_screen.py
import os
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QHeaderView, QInputDialog, QCheckBox,
                               QDialog, QFormLayout, QGridLayout, QLabel, QFileDialog,
                               QTreeWidget, QTreeWidgetItem, QApplication, QDateEdit,
                               QComboBox, QMessageBox, QStyledItemDelegate, QStyleOptionViewItem,
                               QStyle, QCalendarWidget, QToolButton, QTableView)
from PySide6.QtCore import Qt, QTimer, QDate, Signal
from PySide6.QtGui import QColor, QPainter, QBrush, QPalette, QTextCharFormat, QFont
from utils import show_message, show_confirm, ask_password, verify_password

MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
          "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


class ToastLabel(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(40, 167, 69, 240);
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #218838;
            }
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_toast(self, text):
        self.setText(f"Скопировано: {text}")
        self.adjustSize()
        
        # Позиционируем по центру и в самом низу главного окна
        parent_rect = self.parent().rect()
        x = (parent_rect.width() - self.width()) // 2
        y = parent_rect.height() - self.height() - 5
        
        self.move(x, y)
        self.show()
        self.raise_()
        self._timer.start(1500)


class HighlightDelegate(QStyledItemDelegate):
    """Делегат для принудительной отрисовки фона поверх глобальных стилей."""
    def paint(self, painter, option, index):
        is_highlighted = index.data(Qt.UserRole + 3)
        bg_role = index.data(Qt.BackgroundRole)
        
        if is_highlighted:
            painter.fillRect(option.rect, QColor("#ffb74d"))
            
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            
            custom_fg = index.data(Qt.ForegroundRole)
            text_color = QColor("black")
            
            if custom_fg:
                if isinstance(custom_fg, QBrush):
                    text_color = custom_fg.color()
                elif isinstance(custom_fg, QColor):
                    text_color = custom_fg

            opt.palette.setColor(QPalette.Text, text_color)
            opt.palette.setColor(QPalette.HighlightedText, text_color)
            opt.backgroundBrush = QBrush(Qt.NoBrush)
            
            widget = option.widget
            style = widget.style() if widget else QApplication.style()
            style.drawControl(QStyle.CE_ItemViewItem, opt, painter, widget)
        elif bg_role:
            painter.fillRect(option.rect, bg_role)
            
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            opt.backgroundBrush = QBrush(Qt.NoBrush)
            
            widget = option.widget
            style = widget.style() if widget else QApplication.style()
            style.drawControl(QStyle.CE_ItemViewItem, opt, painter, widget)
        else:
            super().paint(painter, option, index)


class ClickableWidget(QWidget):
    """Виджет, который ловит клик в любом месте своей области."""
    clicked = Signal()
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class ReportScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.current_data = []
        self._order_nodes = {}
        self._current_search = ""

        layout = QVBoxLayout(self)

        # --- Фильтры поиска и дат ---
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Поиск по организации / контактам / ФИО / артикулу / наименованию..."
        )
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self.refresh)
        
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self.refresh)
        
        filter_layout.addWidget(self.search_input)
        
        self.chk_date_filter = QCheckBox("Фильтр по дате")
        self.chk_date_filter.setChecked(False)
        self.chk_date_filter.stateChanged.connect(self.on_date_filter_toggled)
        filter_layout.addWidget(self.chk_date_filter)
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setEnabled(False)
        self.date_from.dateChanged.connect(lambda: self.refresh() if self.chk_date_filter.isChecked() else None)
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("—"))
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setEnabled(False)
        self.date_to.dateChanged.connect(lambda: self.refresh() if self.chk_date_filter.isChecked() else None)
        filter_layout.addWidget(self.date_to)

        layout.addLayout(filter_layout)

        # --- Кнопки действий ---
        btn_layout = QHBoxLayout()

        btn_open = QPushButton("Открыть в Excel")
        btn_open.setStyleSheet("""
            QPushButton { background-color: #4dabf7; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #339af0; }
            QPushButton:pressed { background-color: #228be6; }
        """)
        btn_open.clicked.connect(self.open_excel)

        btn_merge = QPushButton("Объединить в Excel")
        btn_merge.setStyleSheet("""
            QPushButton { background-color: #f0ad4e; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #ec971f; }
            QPushButton:pressed { background-color: #d58512; }
        """)
        btn_merge.clicked.connect(self.merge_orders)

        btn_edit = QPushButton("Изменить отчёт")
        btn_edit.setStyleSheet("""
            QPushButton { background-color: #4dabf7; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #339af0; }
            QPushButton:pressed { background-color: #228be6; }
        """)
        btn_edit.clicked.connect(self.edit_report)

        btn_add_items = QPushButton("Добавить \\ Удалить")
        btn_add_items.setStyleSheet("""
            QPushButton { background-color: #5cb85c; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #449d44; }
            QPushButton:pressed { background-color: #398439; }
        """)
        btn_add_items.clicked.connect(self.add_items_to_report)

        btn_cols = QPushButton("⚙️ Настройки Excel")
        btn_cols.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #b0b0b0; }
        """)
        btn_cols.clicked.connect(self.config_columns)

        btn_del = QPushButton("Удалить")
        btn_del.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_del.clicked.connect(self.delete_report)

        btn_clear = QPushButton("Очистить список")
        btn_clear.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: black; font-weight: bold; border-radius: 4px; padding: 6px; border: 1px solid #999; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_clear.clicked.connect(self.clear_list)

        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_merge)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_add_items)
        btn_layout.addWidget(btn_cols)
        btn_layout.addWidget(btn_del)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Таблица (8 колонок: без "Примечание") ---
        self.table = QTreeWidget()
        self.table.setColumnCount(8)
        self.table.setHeaderLabels([
            "", "Дата", "Организация / Артикул",
            "Статус", "Кол-во", "Наименование",
            "Назначение", "Месяц"
        ])
        self.table.setRootIsDecorated(True)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionMode(QTreeWidget.NoSelection)
        self.table.setUniformRowHeights(True)
        self.table.setIndentation(18)
        self.table.setExpandsOnDoubleClick(False)

        header = self.table.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(False)
        
        self.table.setMinimumWidth(850)
        
        self.table.setItemDelegate(HighlightDelegate(self.table))

        self.table.itemExpanded.connect(self._lazy_expand)
        self.table.itemExpanded.connect(self._sync_btn_state)
        self.table.itemCollapsed.connect(self._sync_btn_state)
        self.table.itemClicked.connect(self.on_item_clicked)
        
        layout.addWidget(self.table)

        self.table.mousePressEvent = self.table_mouse_press_event
        self.table.keyPressEvent = self.table_key_press_event

        # --- ПОДСВЕТКА СТРОК ПРИ НАВЕДЕНИИ ---
        self.hover_item = None
        self.table.setMouseTracking(True)
        self.table.itemEntered.connect(self.on_item_entered)
        self.table.leaveEvent = self.table_leave_event
        self.table.mouseMoveEvent = self.table_mouse_move_event
        
        # --- Тост для уведомления о копировании ---
        self.toast = ToastLabel(self.main_app)

    # ---------- Вспомогательное ----------

    def _sync_btn_state(self, item):
        if item.parent() is not None:
            return
        widget = self.table.itemWidget(item, 5)
        if widget:
            lbl = widget.findChild(QLabel)
            if lbl:
                lbl.setText("▼ Свернуть ▼" if item.isExpanded() else "▶ Развернуть ◀")

    def _is_item_checked(self, item):
        if item is None or item.parent() is not None:
            return False
        w = self.table.itemWidget(item, 0)
        if w:
            cb = w.findChild(QCheckBox)
            if cb:
                return cb.isChecked()
        return False

    def _is_cell_highlighted(self, item, col):
        return bool(item.data(col, Qt.UserRole + 3))

    # ---------- Hover ----------

    def on_item_entered(self, item, column):
        if getattr(self, 'hover_item', None) is item:
            return
        if getattr(self, 'hover_item', None):
            self.restore_item_color(self.hover_item)
        self.hover_item = item
        self.apply_item_hover(item)

    def table_leave_event(self, event):
        if getattr(self, 'hover_item', None):
            self.restore_item_color(self.hover_item)
            self.hover_item = None
        QTreeWidget.leaveEvent(self.table, event)

    def table_mouse_move_event(self, event):
        item = self.table.itemAt(event.pos())
        if not item:
            if getattr(self, 'hover_item', None):
                self.restore_item_color(self.hover_item)
                self.hover_item = None
        QTreeWidget.mouseMoveEvent(self.table, event)

    def restore_item_color(self, item):
        if item is None:
            return
        is_checked = self._is_item_checked(item)
        is_top = item.parent() is None
        
        if is_checked:
            bg = QColor("#cce5ff")
            fg = QColor("black")
        elif is_top:
            bg = QColor("#d9e2ec")
            fg = QColor("black")
        else:
            bg = None
            fg = None

        for col in range(self.table.columnCount()):
            if self._is_cell_highlighted(item, col):
                continue
            item.setData(col, Qt.BackgroundRole, bg)
            if fg:
                item.setData(col, Qt.ForegroundRole, fg)
            else:
                item.setData(col, Qt.ForegroundRole, None)

        if is_top:
            w = self.table.itemWidget(item, 0)
            if w and not self._is_cell_highlighted(item, 0):
                color = "#cce5ff" if is_checked else "#d9e2ec"
                w.setStyleSheet(f"background-color: {color};")

    def apply_item_hover(self, item):
        if item is None:
            return
        is_checked = self._is_item_checked(item)
        is_top = item.parent() is None
        
        if is_checked:
            bg = QColor("#a8c8e8")
        elif is_top:
            bg = QColor("#c3d2e3")
        else:
            bg = QColor("#e2eaf1")
            
        fg = QColor("black")

        for col in range(self.table.columnCount()):
            if self._is_cell_highlighted(item, col):
                continue
            item.setData(col, Qt.BackgroundRole, bg)
            item.setData(col, Qt.ForegroundRole, fg)

        if is_top:
            w = self.table.itemWidget(item, 0)
            if w and not self._is_cell_highlighted(item, 0):
                w.setStyleSheet(f"background-color: {bg.name()};")

    # ---------- Разворот/сворот ----------

    def _toggle_report(self, item):
        if item.isExpanded():
            item.setExpanded(False)
        else:
            self._populate_children_if_needed(item)
            item.setExpanded(True)
        self._sync_btn_state(item)

    def clear_list(self):
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self._search_timer.stop()
        self.refresh()
        
    def on_date_filter_toggled(self):
        self.date_from.setEnabled(self.chk_date_filter.isChecked())
        self.date_to.setEnabled(self.chk_date_filter.isChecked())
        self.refresh()

    def _on_search_text_changed(self):
        self._search_timer.start()

    def _adjust_column_width(self):
        if not hasattr(self, 'table') or self.table.columnCount() == 0:
            return
        header = self.table.header()

        for i in [0, 1, 3, 4, 6, 7]:
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            self.table.resizeColumnToContents(i)

        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.resizeColumnToContents(2)
        
        header_text = self.table.headerItem().text(2)
        header_min = self.table.fontMetrics().horizontalAdvance(header_text) + 40
        
        if self.table.columnWidth(2) < header_min:
            self.table.setColumnWidth(2, header_min)

        header.setSectionResizeMode(5, QHeaderView.Stretch)

        name_header_min = self.table.fontMetrics().horizontalAdvance("Наименование") + 30
        other_cols_total = sum(
            self.table.columnWidth(i) for i in range(self.table.columnCount())
            if i != 5 and self.table.columnWidth(i) > 0
        )
        required_min_width = other_cols_total + name_header_min
        self.table.setMinimumWidth(max(required_min_width, 850))

    def table_mouse_press_event(self, event):
        idx = self.table.indexAt(event.pos())
        if not idx.isValid():
            self.clear_all_checks()
            self.table.clearSelection()
            self.table.setCurrentItem(None)
        QTreeWidget.mousePressEvent(self.table, event)

    def table_key_press_event(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_report()
        else:
            QTreeWidget.keyPressEvent(self.table, event)

    def clear_all_checks(self):
        for rid, node in getattr(self, "_order_nodes", {}).items():
            w = self.table.itemWidget(node, 0)
            if w:
                cb = w.findChild(QCheckBox)
                if cb and cb.isChecked():
                    cb.setChecked(False)

    # ---------- refresh ----------

    def refresh(self):
        self._search_timer.stop()
        self.hover_item = None
        search = self.search_input.text().strip()
        self._current_search = search.lower() if search else ""
        
        date_from = None
        date_to = None
        if self.chk_date_filter.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")

        self.current_data = self.main_app.report_manager.list_orders(search, date_from, date_to)
        self.table.clear()
        self.hover_item = None
        self._order_nodes = {}

        for order in self.current_data:
            try:
                created = datetime.datetime.fromisoformat(order[1]).strftime("%d.%m.%Y")
            except Exception:
                created = order[1][:10] if order[1] else ""

            # 8 колонок: "", created, org, status, qty, name, purpose, month
            top = QTreeWidgetItem(["", created, order[2] or "", order[11] or "",
                                    "", "", "", order[10] or ""])
            top.setData(0, Qt.UserRole, order)
            f = top.font(2)
            f.setBold(True)
            top.setFont(2, f)

            # Подсказки, что дата/месяц кликабельны
            top.setToolTip(1, "Кликните для изменения даты")
            top.setToolTip(7, "Кликните для изменения месяца")

            for col in range(self.table.columnCount()):
                top.setData(col, Qt.BackgroundRole, QColor("#d9e2ec"))
                top.setData(col, Qt.ForegroundRole, QColor("black"))

            self.table.addTopLevelItem(top)
            self._order_nodes[order[0]] = top

            # Чекбокс
            cb_widget = ClickableWidget()
            cb_widget.setStyleSheet("background-color: transparent;")
            cb = QCheckBox()
            cb.setAttribute(Qt.WA_TransparentForMouseEvents)
            cb.stateChanged.connect(lambda state, rid=order[0], node=top: self.on_checkbox_toggled(rid, node))
            cb_widget.clicked.connect(cb.toggle)
            
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setItemWidget(top, 0, cb_widget)

            # Кликабельная ячейка "Наименование" (сворачивание/разворачивание)
            name_widget = ClickableWidget()
            name_widget.setStyleSheet("background-color: transparent;")
            name_layout = QHBoxLayout(name_widget)
            name_layout.setContentsMargins(0, 0, 0, 0)
            
            lbl_toggle = QLabel("▶ Развернуть ◀")
            lbl_toggle.setAlignment(Qt.AlignCenter)
            lbl_toggle.setStyleSheet(
                "background: transparent; color: #005a9e; font-weight: bold; font-size: 14px;"
            )
            lbl_toggle.setAttribute(Qt.WA_TransparentForMouseEvents)
            
            name_layout.addWidget(lbl_toggle)
            name_widget.clicked.connect(lambda n=top: self._toggle_report(n))
            
            self.table.setItemWidget(top, 5, name_widget)

            ph = QTreeWidgetItem(["", "", "…", "", "", "", "", ""])
            ph.setDisabled(True)
            top.addChild(ph)
            top.setData(0, Qt.UserRole + 1, False)

        self._adjust_column_width()

        # Авто-раскрытие отчётов, в товарах которых есть совпадение
        if self._current_search:
            matching_ids = self.main_app.report_manager.find_orders_with_matching_items(search)
            for order_id in matching_ids:
                node = self._order_nodes.get(order_id)
                if node:
                    self._populate_children_if_needed(node)
                    node.setExpanded(True)
                    self._sync_btn_state(node)

    # ---------- Ленивая загрузка и заполнение детей ----------

    def _populate_children_if_needed(self, item):
        if item.data(0, Qt.UserRole + 1):
            return
        order = item.data(0, Qt.UserRole)
        if not order:
            return
        item.takeChildren()
        try:
            self._fill_order_children(item, order[0])
        except Exception as e:
            print(f"Ошибка загрузки товаров отчёта: {e}")
            err = QTreeWidgetItem(["", "", f"Ошибка загрузки: {e}", "", "", "", "", ""])
            err.setDisabled(True)
            item.addChild(err)
        item.setData(0, Qt.UserRole + 1, True)
        self._adjust_column_width()

    def _lazy_expand(self, item):
        if item.parent() is not None:
            return
        self._populate_children_if_needed(item)

    def _on_bought_toggled(self, item_id, checked):
        self.main_app.report_manager.set_item_bought(item_id, 1 if checked else 0)

    def _fill_order_children(self, top_item, order_id):
        items = self.main_app.report_manager.get_items(order_id)
        if not items:
            empty = QTreeWidgetItem(["", "", "— нет товаров —", "", "", "", "", ""])
            empty.setDisabled(True)
            top_item.addChild(empty)
            return

        search = getattr(self, "_current_search", "") or ""

        # Собираем артикулы, для которых надо искать источник в products
        articles_to_check = []
        for it in items:
            src = it.get("source") or ""
            art = it.get("article") or ""
            if art and (not src or src == "Вручную"):
                articles_to_check.append(art.lower())

        article_sources = {}
        if articles_to_check:
            try:
                import sqlite3
                placeholders = ",".join("?" * len(articles_to_check))
                with sqlite3.connect(self.main_app.price_manager.db_path, timeout=30) as conn:
                    rows = conn.execute(
                        f"SELECT article_lower, source FROM products "
                        f"WHERE article_lower IN ({placeholders})",
                        articles_to_check
                    ).fetchall()
                    for art_lower, src in rows:
                        if src:
                            article_sources.setdefault(art_lower, set()).add(src)
            except Exception as e:
                print(f"Ошибка проверки артикулов в прайсах: {e}")

        for it in items:
            art = it.get("article") or ""
            name = it.get("name") or ""
            qty = str(it.get("qty") or "")
            purpose = it.get("purpose") or ""
            item_source = it.get("source") or ""

            if item_source and item_source != "Вручную":
                source_display = item_source
            else:
                art_lower = art.lower() if art else ""
                if art_lower and art_lower in article_sources:
                    source_display = ", ".join(sorted(article_sources[art_lower]))
                else:
                    source_display = "= Свой ="

            # 8 колонок
            child = QTreeWidgetItem([
                source_display, "", "    " + art, "", qty,
                "    " + name, purpose, ""
            ])
            child.setTextAlignment(4, Qt.AlignCenter)
            if art:
                child.setToolTip(2, art + "\n(клик — скопировать)")
            if name:
                child.setToolTip(5, name + "\n(клик — скопировать)")

            # --- Подсветка всей строки при поиске ---
            if search:
                s = search
                art_l = art.lower()
                name_l = name.lower()
                purpose_l = purpose.lower()
                source_l = source_display.lower()
                if (s in art_l) or (s in name_l) or (s in purpose_l) or (s in source_l):
                    for col in range(self.table.columnCount()):
                        child.setData(col, Qt.UserRole + 3, True)

            top_item.addChild(child)

            # Чекбокс "Куплено"
            bought_widget = ClickableWidget()
            bought_widget.setStyleSheet("background-color: transparent;")
            bw_layout = QHBoxLayout(bought_widget)
            bw_layout.setContentsMargins(0, 0, 0, 0)
            bw_layout.setSpacing(0)

            cb_bought = QCheckBox()
            cb_bought.setStyleSheet("margin: 0px; padding: 0px;")
            cb_bought.setToolTip("Куплено")
            cb_bought.setChecked(bool(it.get("bought", 0)))
            cb_bought.setAttribute(Qt.WA_TransparentForMouseEvents)
            bought_widget.clicked.connect(cb_bought.toggle)

            item_id = it.get("id")
            if item_id is not None:
                cb_bought.toggled.connect(
                    lambda checked, iid=item_id: self._on_bought_toggled(iid, checked)
                )
            else:
                cb_bought.setEnabled(False)

            bw_layout.addWidget(cb_bought, 0, Qt.AlignCenter)
            self.table.setItemWidget(child, 3, bought_widget)

    # ---------- Цвета ----------

    def toggle_row_color(self, node, is_checked):
        is_top = node.parent() is None
        
        if is_checked:
            bg = QColor("#cce5ff")
            fg = QColor("black")
        elif is_top:
            bg = QColor("#d9e2ec")
            fg = QColor("black")
        else:
            bg = Qt.transparent
            fg = None

        for col in range(self.table.columnCount()):
            node.setBackground(col, bg)
            if fg:
                node.setForeground(col, fg)
            else:
                node.setData(col, Qt.ForegroundRole, None)

        if is_top:
            w = self.table.itemWidget(node, 0)
            if w:
                color = "#cce5ff" if is_checked else "#d9e2ec"
                w.setStyleSheet(f"background-color: {color};")

    def get_checked_rows(self):
        checked = []
        for rid, node in getattr(self, "_order_nodes", {}).items():
            w = self.table.itemWidget(node, 0)
            if w:
                cb = w.findChild(QCheckBox)
                if cb and cb.isChecked():
                    order = node.data(0, Qt.UserRole)
                    if order:
                        checked.append(order)
        return checked

    def on_checkbox_toggled(self, rid, node):
        w = self.table.itemWidget(node, 0)
        cb = w.findChild(QCheckBox) if w else None
        self.toggle_row_color(node, cb.isChecked() if cb else False)
        if getattr(self, 'hover_item', None) is node:
            self.apply_item_hover(node)

    # ---------- Копирование с зелёной вспышкой ----------

    def _copy_item_text(self, item, column):
        if item.parent() is not None and column in (2, 5):
            text = item.text(column).strip()
            if text:
                QApplication.clipboard().setText(text)
                
                # Зелёная вспышка
                item.setData(column, Qt.BackgroundRole, QColor("#b3e5b3"))
                item.setData(column, Qt.ForegroundRole, QColor("#005500"))
                
                self._flash_id = getattr(self, '_flash_id', 0) + 1
                current_id = self._flash_id
                
                QTimer.singleShot(500, lambda: self._restore_cell_after_copy(item, column, current_id))
                
                # Показ плашки
                self.toast.show_toast(text)

    def _restore_cell_after_copy(self, item, column, flash_id):
        if flash_id != getattr(self, '_flash_id', 0):
            return
            
        try:
            item.text(column)
        except RuntimeError:
            return

        if self._is_cell_highlighted(item, column):
            return

        is_checked = self._is_item_checked(item)
        is_top = item.parent() is None
        is_hovered = getattr(self, 'hover_item', None) == item

        if is_hovered:
            if is_checked:
                bg = QColor("#a8c8e8")
            elif is_top:
                bg = QColor("#c3d2e3")
            else:
                bg = QColor("#e2eaf1")
            item.setData(column, Qt.BackgroundRole, bg)
            item.setData(column, Qt.ForegroundRole, QColor("black"))
        else:
            if is_checked:
                item.setData(column, Qt.BackgroundRole, QColor("#cce5ff"))
                item.setData(column, Qt.ForegroundRole, QColor("black"))
            elif is_top:
                item.setData(column, Qt.BackgroundRole, QColor("#d9e2ec"))
                item.setData(column, Qt.ForegroundRole, QColor("black"))
            else:
                item.setData(column, Qt.BackgroundRole, None)
                item.setData(column, Qt.ForegroundRole, None)

    # ---------- Клики ----------

    def on_item_clicked(self, item, column):
        if item.parent() is None:
            if column == 1:
                self._show_date_dialog(item)
                return
            if column == 7:
                self._show_month_dialog(item)
                return
            if column == 2:
                order = item.data(0, Qt.UserRole)
                if order:
                    org = order[2] or "Не указана"
                    fio = order[5] or "Не указано"
                    phone = order[8] or "Не указан"
                    email = order[9] or "Не указан"
                    msg = f"Организация: {org}\n\nФИО: {fio}\nТелефон: {phone}\nEmail: {email}"
                    show_message(self, "Информация об организации", msg)
        elif column in (2, 5):
            if item.data(0, Qt.UserRole + 2) != "ignore_copy":
                self._copy_item_text(item, column)

    # ---------- Диалог смены даты ----------
    def _show_date_dialog(self, item):
        order = item.data(0, Qt.UserRole)
        if not order:
            return

        current = order[1] or ""
        try:
            dt = datetime.datetime.fromisoformat(current)
            qdate = QDate(dt.year, dt.month, dt.day)
        except Exception:
            qdate = QDate.currentDate()

        dialog = QDialog(self)
        dialog.setWindowTitle("Изменить дату отчёта")
        dialog.setMinimumSize(420, 400)
        layout = QVBoxLayout(dialog)

        cal = QCalendarWidget()
        cal.setSelectedDate(qdate)
        cal.setGridVisible(True)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        cal.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        
        cal.setCursor(Qt.PointingHandCursor)

        view = cal.findChild(QTableView)
        if view:
            view.setCursor(Qt.PointingHandCursor)
            view.viewport().setCursor(Qt.PointingHandCursor)

        cal.setStyleSheet("""
            QCalendarWidget QWidget {
                alternate-background-color: #f5f5f5;
                background-color: #ffffff;
                color: #000000;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #f0f0f0;
            }
            QCalendarWidget QToolButton {
                color: #000000;
                background-color: transparent;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #d0e3f5;
                border-radius: 3px;
            }
            QCalendarWidget QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #ccc;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                outline: none;
            }
            QCalendarWidget QAbstractItemView:enabled {
                selection-background-color: transparent;
                selection-color: #000000;
            }
            QCalendarWidget QAbstractItemView::item:hover {
                background-color: #e2eaf1;
            }
        """)

        fmt_selected = QTextCharFormat()
        fmt_selected.setBackground(QBrush(QColor("#0078D7")))
        fmt_selected.setForeground(QBrush(QColor("#ffffff")))
        
        font = cal.font()
        font.setBold(True)
        fmt_selected.setFont(font)

        def update_selected_format():
            cal.setDateTextFormat(QDate(), QTextCharFormat())
            cal.setDateTextFormat(cal.selectedDate(), fmt_selected)
            cal.update()

        update_selected_format()
        cal.selectionChanged.connect(update_selected_format)

        for btn_name in ("qt_calendar_monthbutton", "qt_calendar_yearbutton", 
                         "qt_calendar_prevmonth", "qt_calendar_nextmonth"):
            btn = cal.findChild(QToolButton, btn_name)
            if btn:
                btn.setCursor(Qt.PointingHandCursor)
                menu = btn.menu()
                if menu:
                    menu.setCursor(Qt.PointingHandCursor)
                    menu.setStyleSheet("""
                        QMenu {
                            background-color: #ffffff;
                            color: #000000;
                        }
                        QMenu::item {
                            padding: 4px 20px;
                            background-color: transparent;
                        }
                        QMenu::item:selected {
                            background-color: #0078D7;
                            color: #ffffff;
                        }
                    """)

        layout.addWidget(cal)

        btn_layout = QHBoxLayout()
        
        btn_ok = QPushButton("Применить")
        btn_ok.setMinimumSize(120, 34)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                border: 1px solid #005a9e;
            }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_ok.clicked.connect(dialog.accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setMinimumSize(110, 34)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: black;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                border: 1px solid #ac2925;
            }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            new_qdate = cal.selectedDate()
            new_iso_date = new_qdate.toString("yyyy-MM-dd")

            try:
                self.main_app.report_manager.update_order_date(order[0], new_iso_date)
            except Exception as e:
                show_message(self, "Ошибка", f"Не удалось обновить дату: {e}", is_error=True)
                return

            item.setText(1, new_qdate.toString("dd.MM.yyyy"))

            new_order = list(order)
            new_order[1] = new_iso_date + "T00:00:00"
            item.setData(0, Qt.UserRole, new_order)

    # ---------- Диалог смены месяца ----------

    def _show_month_dialog(self, item):
        order = item.data(0, Qt.UserRole)
        if not order:
            return

        current = order[10] or ""
        idx = MONTHS.index(current) if current in MONTHS else 0

        dialog = QDialog(self)
        dialog.setWindowTitle("Изменить месяц")
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Выберите месяц:"))

        combo = QComboBox()
        combo.addItems(MONTHS)
        combo.setCurrentIndex(idx)
        combo.setCursor(Qt.PointingHandCursor)
        combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: white;
                color: black;
                min-height: 24px;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 1px solid #0078D7;
                background-color: #e8f4ff;
            }
            QComboBox:focus {
                border: 1px solid #0078D7;
            }
            QComboBox::drop-down {
                border-left: 1px solid #bbb;
                width: 24px;
            }
            QComboBox::drop-down:hover {
                background-color: #d0e3f5;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                border: 1px solid #bbb;
                selection-background-color: #0078D7;
                selection-color: white;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8f4ff;
                color: black;
            }
        """)
        layout.addWidget(combo)

        btn_layout = QHBoxLayout()
        
        btn_ok = QPushButton("Выбрать")
        btn_ok.setMinimumSize(110, 34)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: black;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                border: 1px solid #005a9e;
            }
            QPushButton:hover { background-color: #005a9e; color: black; }
            QPushButton:pressed { background-color: #004578; color: black; }
        """)
        btn_ok.clicked.connect(dialog.accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setMinimumSize(110, 34)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: black;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                border: 1px solid #ac2925;
            }
            QPushButton:hover { background-color: #c9302c; color: black; }
            QPushButton:pressed { background-color: #ac2925; color: black; }
        """)
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            month = combo.currentText()
            try:
                self.main_app.report_manager.update_order_month(order[0], month)
            except Exception as e:
                show_message(self, "Ошибка", f"Не удалось обновить месяц: {e}", is_error=True)
                return

            item.setText(7, month)

            new_order = list(order)
            new_order[10] = month
            item.setData(0, Qt.UserRole, new_order)

    # ---------- Действия с отчётами ----------

    def merge_orders(self):
        rows = self.get_checked_rows()
        if len(rows) < 2:
            show_message(self, "Внимание", "Отметьте хотя бы две заявки для объединения!", is_error=True)
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить сводную заявку",
            os.path.join(os.path.expanduser("~"), "Desktop", "Отчёты заказа", "merged.xlsx"),
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            items_list = [self.main_app.report_manager.get_items(r[0]) for r in rows]
            self.main_app.order_manager.merge_items_to_excel(file_path, items_list, self.main_app.export_config)
            show_message(self, "Успех", f"Успешно объединено {len(rows)} заявок в файл:\n{os.path.basename(file_path)}")
            os.startfile(file_path)
        except Exception as e:
            show_message(self, "Ошибка", f"Не удалось объединить: {e}", is_error=True)

    def open_excel(self):
        rows = self.get_checked_rows()
        if not rows:
            show_message(self, "Внимание", "Поставьте галочку на нужной заявке!", is_error=True)
            return
        if len(rows) > 1:
            show_message(self, "Внимание", "Выбрано несколько отчётов.\nДля открытия выберите только ОДИН.", is_error=True)
            return

        row = rows[0]
        meta = {"organization": row[2] or "", "contact": row[3] or "",
                "fio": row[5] or "", "category": row[4] or "", "note": row[6] or "",
                "phone": row[8] or "", "email": row[9] or "", "month": row[10] or "", "status": row[11] or ""}
        items = self.main_app.report_manager.get_items(row[0])

        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Отчёты заказа")
        os.makedirs(desktop_dir, exist_ok=True)

        created_str = row[1][:10].replace("-", "_") if row[1] else "report"
        file_path = os.path.join(desktop_dir, f"Заказ_{created_str}_{row[0]}.xlsx")

        try:
            self.main_app.order_manager.save_to_excel(file_path, meta, items, self.main_app.export_config)
            os.startfile(file_path)
        except Exception as e:
            show_message(self, "Ошибка", f"Не удалось сгенерировать файл: {e}", is_error=True)

    def edit_report(self):
        rows = self.get_checked_rows()
        if not rows or len(rows) > 1:
            show_message(self, "Внимание", "Выберите ровно ОДИН отчёт для редактирования!", is_error=True)
            return

        row = rows[0]
        dialog = QDialog(self)
        dialog.setWindowTitle("Изменить отчёт")
        dialog.setMinimumWidth(450)
        form = QFormLayout(dialog)

        f_org = QLineEdit(row[2] or "")
        f_fio = QLineEdit(row[5] or "")
        f_phone = QLineEdit(row[8] or "")
        f_email = QLineEdit(row[9] or "")

        f_month = QComboBox()
        f_month.addItems(MONTHS)
        m_idx = f_month.findText(row[10] or "")
        if m_idx >= 0:
            f_month.setCurrentIndex(m_idx)

        f_status = QComboBox()
        f_status.addItems(["Ожидание", "Обработка", "Выполнено"])
        s_idx = f_status.findText(row[11] or "Ожидание")
        if s_idx >= 0:
            f_status.setCurrentIndex(s_idx)

        combo_style = """
            QComboBox {
                padding: 5px 8px;
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: white;
                color: black;
                min-height: 22px;
            }
            QComboBox:hover {
                border: 1px solid #0078D7;
                background-color: #e8f4ff;
            }
            QComboBox:focus {
                border: 1px solid #0078D7;
            }
            QComboBox::drop-down {
                border-left: 1px solid #bbb;
                width: 22px;
            }
            QComboBox::drop-down:hover {
                background-color: #d0e3f5;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                border: 1px solid #bbb;
                selection-background-color: #0078D7;
                selection-color: white;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8f4ff;
                color: black;
            }
        """
        f_month.setStyleSheet(combo_style)
        f_status.setStyleSheet(combo_style)
        f_month.setCursor(Qt.PointingHandCursor)
        f_status.setCursor(Qt.PointingHandCursor)

        form.addRow("Организация (обязательно):", f_org)
        form.addRow("ФИО:", f_fio)
        form.addRow("Контакт: № телефона", f_phone)
        form.addRow("Контакт: @ email", f_email)
        form.addRow("Месяц:", f_month)
        form.addRow("Статус отчёта:", f_status)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Сохранить")
        btn_ok.setMinimumSize(120, 32)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                border: 1px solid #005a9e;
            }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_ok.clicked.connect(dialog.accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setMinimumSize(110, 32)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: black;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                border: 1px solid #ac2925;
            }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        form.addRow(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            if not f_org.text().strip():
                show_message(self, "Внимание", "Поле 'Организация' обязательно для заполнения!", is_error=True)
                return

            # note сохраняется как было (в БД, но в UI не показывается)
            meta = {
                "organization": f_org.text().strip(),
                "fio": f_fio.text().strip(),
                "phone": f_phone.text().strip(),
                "email": f_email.text().strip(),
                "month": f_month.currentText(),
                "status": f_status.currentText(),
                "contact": row[3] or "",
                "category": row[4] or "",
                "note": row[6] or "",
            }
            self.main_app.report_manager.update_order_meta(row[0], meta)
            self.refresh()

    def delete_report(self):
        rows = self.get_checked_rows()
        if not rows:
            show_message(self, "Внимание", "Поставьте галочку на заявке!", is_error=True)
            return
        if len(rows) > 1:
            show_message(self, "Внимание", "Выбрано несколько отчётов.\nДля удаления выберите только ОДИН.", is_error=True)
            return

        row = rows[0]
        pwd = ask_password(self, "Пароль", "Введите пароль администратора для удаления:")
        if pwd is None:
            return

        admin_hash = self.main_app.export_config.get("admin_pwd_hash")
        if not verify_password(pwd, admin_hash):
            show_message(self, "Ошибка", "Неверный пароль!", is_error=True)
            return

        if not show_confirm(self, "Удаление", f"Удалить отчёт от {row[1]}?\nДействие необратимо!"):
            return

        self.main_app.report_manager.delete_order_meta(row[0])
        self.refresh()

    def config_columns(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка колонок и шапки Excel")
        dialog.setMinimumWidth(450)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)

        lbl_head = QLabel("<b>Шапка документа (сверху):</b>")
        main_layout.addWidget(lbl_head)

        grid_head = QGridLayout()
        grid_head.setSpacing(10)

        cfg = self.main_app.export_config

        cb_org = QCheckBox("Организация"); cb_org.setChecked(cfg.get("org", True))
        cb_contact = QCheckBox("Контакт"); cb_contact.setChecked(cfg.get("contact", True))
        cb_fio = QCheckBox("ФИО"); cb_fio.setChecked(cfg.get("fio", True))
        cb_cat = QCheckBox("Категория/Месяц"); cb_cat.setChecked(cfg.get("cat", True))
        cb_note = QCheckBox("Примечание"); cb_note.setChecked(cfg.get("note", True))

        grid_head.addWidget(cb_org, 0, 0)
        grid_head.addWidget(cb_contact, 0, 1)
        grid_head.addWidget(cb_fio, 1, 0)
        grid_head.addWidget(cb_cat, 1, 1)
        grid_head.addWidget(cb_note, 2, 0)

        main_layout.addLayout(grid_head)

        lbl_table = QLabel("<b>Колонки таблицы:</b>")
        main_layout.addWidget(lbl_table)

        grid_table = QGridLayout()
        grid_table.setSpacing(10)

        cb_num = QCheckBox("№"); cb_num.setChecked(cfg.get("num", True))
        cb_art = QCheckBox("Артикул"); cb_art.setChecked(cfg.get("article", True))
        cb_name = QCheckBox("Наименование"); cb_name.setChecked(cfg.get("name", True))
        cb_qty = QCheckBox("Кол-во"); cb_qty.setChecked(cfg.get("qty", True))

        grid_table.addWidget(cb_num, 0, 0)
        grid_table.addWidget(cb_art, 0, 1)
        grid_table.addWidget(cb_name, 1, 0)
        grid_table.addWidget(cb_qty, 1, 1)

        main_layout.addLayout(grid_table)
        main_layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Применить")
        btn_ok.setMinimumSize(120, 35)
        btn_ok.setStyleSheet("background-color: #0078D7; color: black; font-weight: bold; border-radius: 4px; border: 1px solid #999;")
        btn_ok.clicked.connect(dialog.accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setMinimumSize(100, 35)
        btn_cancel.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 4px; border: 1px solid #999;")
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            self.main_app.export_config = {
                "num": cb_num.isChecked(), "article": cb_art.isChecked(),
                "name": cb_name.isChecked(), "qty": cb_qty.isChecked(),
                "org": cb_org.isChecked(), "contact": cb_contact.isChecked(),
                "fio": cb_fio.isChecked(), "cat": cb_cat.isChecked(),
                "note": cb_note.isChecked(),
                "price": False, "pack": False, "unit": False, "gtin": False, "source": False
            }
            for k in ("theme", "custom_theme", "sources", "db_path"):
                if k not in self.main_app.export_config:
                    self.main_app.export_config[k] = self.main_app.load_config().get(k)
            self.main_app.save_config()
            show_message(self, "Успех", "Настройки сохранены.")

    def add_items_to_report(self):
        rows = self.get_checked_rows()
        if not rows or len(rows) > 1:
            show_message(self, "Внимание", "Выберите ровно ОДИН отчёт для добавления товаров!", is_error=True)
            return

        row = rows[0]

        if self.main_app.editing_order and self.main_app.editing_order["id"] == row[0]:
            self.main_app.tabs.setCurrentWidget(self.main_app.order_scr)
            show_message(self, "Информация", "Этот отчёт уже открыт для редактирования.")
            return

        if self.main_app.order_manager.items:
            show_message(self, "Внимание",
                         "Формируется заявка. Для добавления товаров в отчёт сначала сохраните или очистите текущую заявку на вкладке 'Заявка'.",
                         is_error=True)
            return

        self.main_app.order_manager.items = self.main_app.report_manager.get_items(row[0])
        self.main_app.editing_order = {
            "id": row[0], "path": "",
            "meta": {
                "organization": row[2] or "",
                "fio": row[5] or "",
                "phone": row[8] or "",
                "email": row[9] or "",
                "month": row[10] or "",
                "note": row[6] or "",
                "status": row[11] or "",
                "contact": row[3] or "",
                "category": row[4] or ""
            }
        }
        self.main_app.save_editing_order_state()
        self.main_app.tabs.setCurrentWidget(self.main_app.order_scr)
        self.main_app.order_scr.refresh()
        show_message(self, "Успех", "Заявка загружена. Перейдите в 'Поиск', чтобы добавить новые товары.")