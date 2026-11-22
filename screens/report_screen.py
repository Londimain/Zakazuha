# screens/report_screen.py
import os
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QHeaderView, QInputDialog, QCheckBox,
                               QDialog, QFormLayout, QGridLayout, QLabel, QFileDialog,
                               QTreeWidget, QTreeWidgetItem, QApplication, QDateEdit)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QColor
from utils import show_message, show_confirm, ask_password, verify_password

class ReportScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.current_data = []
        self._order_nodes = {}

        layout = QVBoxLayout(self)

        # --- Фильтры поиска и дат ---
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по организации / контактам / ФИО / примечанию...")
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
        btn_open.clicked.connect(self.open_excel)
        btn_merge = QPushButton("Объединить в Excel")
        btn_merge.setStyleSheet("background-color: #f0ad4e; color: black; font-weight: bold;")
        btn_merge.clicked.connect(self.merge_orders)
        btn_edit = QPushButton("Изменить отчёт")
        btn_edit.clicked.connect(self.edit_report)
        btn_add_items = QPushButton("Добавить \\ Удалить")
        btn_add_items.setStyleSheet("background-color: #5cb85c; color: black; font-weight: bold;")
        btn_add_items.clicked.connect(self.add_items_to_report)
        btn_cols = QPushButton("⚙️ Настройки Excel")
        btn_cols.clicked.connect(self.config_columns)
        btn_del = QPushButton("Удалить")
        btn_del.setStyleSheet("background-color: #d9534f; color: black; font-weight: bold;")
        btn_del.clicked.connect(self.delete_report)

        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_merge)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_add_items)
        btn_layout.addWidget(btn_cols)
        btn_layout.addWidget(btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Таблица ---
        self.table = QTreeWidget()
        self.table.setColumnCount(7)
        self.table.setHeaderLabels([
            "", "Дата", "Организация / Артикул",
            "Контакты / Кол-во", "ФИО / Наименование",
            "Категория", "Примечание"
        ])
        self.table.setRootIsDecorated(True)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionMode(QTreeWidget.NoSelection)
        self.table.setUniformRowHeights(True)
        self.table.setIndentation(18)

        header = self.table.header()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch) # Растягивается
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # Упирается в правый край
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(False)

        self.table.itemExpanded.connect(self._lazy_expand)
        self.table.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.table)

        self.table.mousePressEvent = self.table_mouse_press_event
        self.table.keyPressEvent = self.table_key_press_event

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

        for i in [1, 3, 5, 6]:
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            self.table.resizeColumnToContents(i)

        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.resizeColumnToContents(2)
        
        header_text = self.table.headerItem().text(2)
        header_min = self.table.fontMetrics().horizontalAdvance(header_text) + 40
        
        if self.table.columnWidth(2) < header_min:
            self.table.setColumnWidth(2, header_min)

        header.setSectionResizeMode(4, QHeaderView.Stretch)

    def table_mouse_press_event(self, event):
        idx = self.table.indexAt(event.pos())
        if not idx.isValid():
            self.clear_all_checks()
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

    def refresh(self):
        self._search_timer.stop()
        search = self.search_input.text().strip()
        
        date_from = None
        date_to = None
        if self.chk_date_filter.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")

        self.current_data = self.main_app.report_manager.list_orders(search, date_from, date_to)
        self.table.clear()
        self._order_nodes = {}

        for order in self.current_data:
            try:
                created = datetime.datetime.fromisoformat(order[1]).strftime("%d.%m.%Y %H:%M")
            except Exception:
                created = order[1] or ""

            top = QTreeWidgetItem(["", created, order[2] or "", order[3] or "",
                                    order[5] or "", order[4] or "", order[6] or ""])
            top.setData(0, Qt.UserRole, order)
            f = top.font(2)
            f.setBold(True)
            top.setFont(2, f)
            self.table.addTopLevelItem(top)
            self._order_nodes[order[0]] = top

            cb_widget = QWidget()
            cb_widget.setStyleSheet("background-color: transparent;")
            cb = QCheckBox()
            cb.stateChanged.connect(lambda state, rid=order[0], node=top: self.on_checkbox_toggled(rid, node))
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setItemWidget(top, 0, cb_widget)

            ph = QTreeWidgetItem(["", "", "…", "", "", "", ""])
            ph.setDisabled(True)
            top.addChild(ph)
            top.setData(0, Qt.UserRole + 1, False)

        self._adjust_column_width()

    def _lazy_expand(self, item):
        if item.parent() is not None or item.data(0, Qt.UserRole + 1):
            return
        order = item.data(0, Qt.UserRole)
        if not order:
            return
        item.takeChildren()
        self._fill_order_children(item, order[0])
        item.setData(0, Qt.UserRole + 1, True)
        self._adjust_column_width()

    def _fill_order_children(self, top_item, order_id):
        items = self.main_app.report_manager.get_items(order_id)
        if not items:
            empty = QTreeWidgetItem(["", "", "— нет товаров —", "", "", "", ""])
            empty.setDisabled(True)
            top_item.addChild(empty)
            return

        summary_text = f"В заявке: {len(items)} позиций"
        if len(items) % 10 == 1 and len(items) % 100 != 11:
            summary_text = f"В заявке: {len(items)} позиция"
        elif 2 <= len(items) % 10 <= 4 and not (10 <= len(items) % 100 <= 20):
            summary_text = f"В заявке: {len(items)} позиции"

        summary_item = QTreeWidgetItem(["", "", summary_text, "", "", "", ""])
        f = summary_item.font(2)
        f.setItalic(True)
        summary_item.setFont(2, f)
        summary_item.setData(0, Qt.UserRole + 2, "ignore_copy")
        top_item.addChild(summary_item)

        for it in items:
            art = it.get("article") or ""
            name = it.get("name") or ""
            qty = str(it.get("qty") or "")

            child = QTreeWidgetItem(["", "", "    " + art, qty, "    " + name, "", ""])
            child.setTextAlignment(3, Qt.AlignCenter)
            if art:
                child.setToolTip(2, f"{art}\nКлик — скопировать артикул.")
            if name:
                child.setToolTip(4, f"{name}\nКлик — скопировать наименование.")
            top_item.addChild(child)

    def toggle_row_color(self, node, is_checked):
        bg = QColor("#cce5ff") if is_checked else Qt.transparent
        fg = QColor("black") if is_checked else None
        for col in range(self.table.columnCount()):
            node.setBackground(col, bg)
            if fg:
                node.setForeground(col, fg)
            else:
                node.setData(col, Qt.ForegroundRole, None)

        w = self.table.itemWidget(node, 0)
        if w:
            w.setStyleSheet(f"background-color: {'#cce5ff' if is_checked else 'transparent'};")

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

    def _copy_item_text(self, item, column):
        if item.parent() is not None and column in (2, 4):
            text = item.text(column).strip()
            if text:
                QApplication.clipboard().setText(text)
                original_fg = item.foreground(column)
                item.setForeground(column, QColor("#28a745"))
                QTimer.singleShot(400, lambda: item.setForeground(column, original_fg))

    def on_item_clicked(self, item, column):
        if item.parent() is not None and column in (2, 4):
            if item.data(0, Qt.UserRole + 2) != "ignore_copy":
                self._copy_item_text(item, column)

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
                "fio": row[5] or "", "category": row[4] or "", "note": row[6] or ""}
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
        f_ctc = QLineEdit(row[3] or "")
        f_fio = QLineEdit(row[5] or "")
        f_cat = QLineEdit(row[4] or "")
        f_note = QLineEdit(row[6] or "")

        form.addRow("Организация:", f_org)
        form.addRow("Контакты:", f_ctc)
        form.addRow("ФИО:", f_fio)
        form.addRow("Категория:", f_cat)
        form.addRow("Примечание:", f_note)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Сохранить")
        btn_ok.setStyleSheet("background-color: #0078D7; color: black; font-weight: bold; padding: 6px;")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold; padding: 6px;")
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        form.addRow(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            meta = {
                "organization": f_org.text().strip(),
                "contact": f_ctc.text().strip(),
                "fio": f_fio.text().strip(),
                "category": f_cat.text().strip(),
                "note": f_note.text().strip()
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
        cb_cat = QCheckBox("Категория"); cb_cat.setChecked(cfg.get("cat", True))
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
        main_layout.addSpacing(20) # Отступ

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
        
        # Если этот отчёт уже открыт для редактирования
        if self.main_app.editing_order and self.main_app.editing_order["id"] == row[0]:
            self.main_app.tabs.setCurrentWidget(self.main_app.order_scr)
            show_message(self, "Информация", "Этот отчёт уже открыт для редактирования.")
            return
            
        # Если в заявке уже есть товары (независимо от того, редактируется ли другой отчёт или просто черновик)
        if self.main_app.order_manager.items:
            show_message(self, "Внимание", 
                         "Формируется заявка. Для добавления товаров в отчёт сначала сохраните или очистите текущую заявку на вкладке 'Заявка'.", 
                         is_error=True)
            return

        # Если заявка пуста - загружаем отчёт
        self.main_app.order_manager.items = self.main_app.report_manager.get_items(row[0])
        self.main_app.editing_order = {
            "id": row[0], "path": "",
            "meta": {
                "organization": row[2] or "",
                "contact": row[3] or "",
                "fio": row[5] or "",
                "category": row[4] or "",
                "note": row[6] or ""
            }
        }
        self.main_app.save_editing_order_state()
        self.main_app.tabs.setCurrentWidget(self.main_app.order_scr)
        self.main_app.order_scr.refresh()
        show_message(self, "Успех", "Заявка загружена. Перейдите в 'Поиск', чтобы добавить новые товары.")