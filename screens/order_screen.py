# screens/order_screen.py
import os
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
                               QDialog, QFormLayout, QLineEdit, QLabel, QAbstractItemView,
                               QComboBox, QTreeWidget, QTreeWidgetItem, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from utils import show_message, show_confirm, ask_password, verify_password

class CheckBoxHeader(QHeaderView):
    clicked_all = Signal(bool)

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.isOn = False
        self.setSectionsClickable(True)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()
        if logicalIndex == 0:
            size = 16
            x = rect.x() + (rect.width() - size) // 2
            y = rect.y() + (rect.height() - size) // 2
            painter.setPen(QPen(QColor("#777777"), 1))
            if self.isOn:
                painter.setBrush(QBrush(QColor("#0078D7")))
                painter.drawRect(x, y, size, size)
                painter.setPen(QPen(QColor("white"), 2))
                painter.drawLine(x + 3, y + 8, x + 6, y + 11)
                painter.drawLine(x + 6, y + 11, x + 12, y + 4)
            else:
                painter.setBrush(QBrush(QColor("white")))
                painter.drawRect(x, y, size, size)

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if index == 0:
            self.isOn = not self.isOn
            self.clicked_all.emit(self.isOn)
            self.viewport().update()
            event.accept() 
        else:
            super().mousePressEvent(event)

class DraggableOrderTable(QTableWidget):
    row_moved = Signal(int, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection) 

    def dropEvent(self, event):
        source_row = self.currentRow()
        target_row = self.rowAt(event.pos().y())
        
        if target_row == -1:
            target_row = self.rowCount() - 1
            
        if source_row != target_row and source_row != -1:
            self.row_moved.emit(source_row, target_row)
            
        event.ignore()

class OrderScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.loading_table = False
        self.hover_row = -1
        
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        
        btn_manual = QPushButton("+ Добавить")
        btn_manual.setStyleSheet("""
            QPushButton { background-color: #5cb85c; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #449d44; }
            QPushButton:pressed { background-color: #398439; }
        """)
        btn_manual.clicked.connect(self.add_manual_item)
        
        btn_edit = QPushButton("Редактировать")
        btn_edit.setStyleSheet("""
            QPushButton { background-color: #f0ad4e; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #ec971f; }
            QPushButton:pressed { background-color: #d58512; }
        """)
        btn_edit.clicked.connect(self.edit_item)
        
        btn_del_selected = QPushButton("Удалить выбранные")
        btn_del_selected.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_del_selected.clicked.connect(self.delete_selected)
        
        btn_clear = QPushButton("Очистить всё")
        btn_clear.clicked.connect(self.clear_order)
        
        self.btn_save = QPushButton("Создать отчёт")
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        self.btn_save.clicked.connect(self.save_order)
        
        self.btn_cancel_edit = QPushButton("Отмена")
        self.btn_cancel_edit.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        self.btn_cancel_edit.clicked.connect(self.cancel_edit)
        self.btn_cancel_edit.setVisible(False)
        
        btn_layout.addWidget(btn_manual)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_del_selected)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel_edit)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = DraggableOrderTable()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["", "№", "Артикул", "Наименование", "Кол-во", "Назначение"])
        self.table.setAlternatingRowColors(False)
        
        self.header = CheckBoxHeader(Qt.Horizontal, self.table)
        self.table.setHorizontalHeader(self.header)
        self.header.clicked_all.connect(self.on_select_all)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 35)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(35)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.setSortingEnabled(False)
        
        self.table.row_moved.connect(self.handle_row_move)
        
        layout.addWidget(self.table)

        self.table.mousePressEvent = self.table_mouse_press_event
        self.table.keyPressEvent = self.table_key_press_event

        # --- ПОДСВЕТКА СТРОК ПРИ НАВЕДЕНИИ ---
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.on_cell_entered)
        self.table.leaveEvent = self.table_leave_event
        self.table.mouseMoveEvent = self.table_mouse_move_event

    def handle_row_move(self, source, target):
        items = self.main_app.order_manager.items
        if 0 <= source < len(items) and 0 <= target < len(items):
            item = items.pop(source)
            items.insert(target, item)
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()
    # --- ПОДСВЕТКА СТРОК ПРИ НАВЕДЕНИИ ---
    def on_cell_entered(self, row, col):
        if self.hover_row == row:
            return
        if self.hover_row != -1:
            self.restore_row_color(self.hover_row)
        self.hover_row = row
        self.apply_hover_color(row)

    def table_leave_event(self, event):
        if self.hover_row != -1:
            self.restore_row_color(self.hover_row)
            self.hover_row = -1
        QTableWidget.leaveEvent(self.table, event)

    def table_mouse_move_event(self, event):
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            if self.hover_row != -1:
                self.restore_row_color(self.hover_row)
                self.hover_row = -1
        QTableWidget.mouseMoveEvent(self.table, event)

    def restore_row_color(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        for c in range(self.table.columnCount()):
            if c in (0, 5):
                w = self.table.cellWidget(row, c)
                if w:
                    w.setStyleSheet("background-color: transparent;")
                    # Если это колонка "Назначение", возвращаем цвет текста темы (сбрасываем стиль)
                    if c == 5:
                        lbl = w.findChild(QLabel)
                        if lbl:
                            lbl.setStyleSheet("background-color: transparent;")
            else:
                item = self.table.item(row, c)
                if item:
                    item.setData(Qt.BackgroundRole, None)
                    item.setData(Qt.ForegroundRole, None)

    def apply_hover_color(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        bg = QColor("#e2eaf1")
        for c in range(self.table.columnCount()):
            if c in (0, 5):
                w = self.table.cellWidget(row, c)
                if w:
                    w.setStyleSheet(f"background-color: {bg.name()};")
                    # Принудительно делаем текст в "Назначении" черным на время наведения
                    if c == 5:
                        lbl = w.findChild(QLabel)
                        if lbl:
                            lbl.setStyleSheet(f"background-color: transparent; color: black;")
            else:
                item = self.table.item(row, c)
                if item:
                    item.setData(Qt.BackgroundRole, bg)
                    item.setData(Qt.ForegroundRole, QColor("black"))
                    
    def update_header_checkbox_state(self):
        if self.table.rowCount() == 0:
            self.header.isOn = False
            self.header.viewport().update()
            return
        all_checked = True
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and not cb.isChecked():
                    all_checked = False
                    break
        self.header.isOn = all_checked
        self.header.viewport().update()

    def on_row_checkbox_changed(self, row, cb):
        self.update_header_checkbox_state()

    def on_select_all(self, is_checked):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(is_checked)
                    cb.blockSignals(False)
        self.table.blockSignals(False)

    def table_key_press_event(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        else:
            QTableWidget.keyPressEvent(self.table, event)

    def table_mouse_press_event(self, event):
        if event.button() == Qt.RightButton:
            self.table.clearSelection()
            self.table.setCurrentItem(None)
            return
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            self.table.clearSelection()
            self.table.setCurrentItem(None)
        QTableWidget.mousePressEvent(self.table, event)

    def clear_all_checks(self):
        self.header.isOn = False
        self.header.viewport().update()
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    cb.setChecked(False)

    def refresh(self):
        self.loading_table = True
        self.hover_row = -1
        self.table.setSortingEnabled(False)
        self.header.isOn = False
        self.header.viewport().update()
        
        self.btn_save.setText("Обновить отчёт" if self.main_app.editing_order else "Создать отчёт")
        self.btn_cancel_edit.setVisible(bool(self.main_app.editing_order))

        def format_val(val):
            if val is None: return ""
            s = str(val).strip()
            if s.lower() == "none" or s == "": return ""
            try:
                f = float(s.replace(",", "."))
                return str(int(f)) if f.is_integer() else str(f)
            except ValueError:
                return s

        items = self.main_app.order_manager.items
        self.table.setRowCount(0)
        for i, item in enumerate(items):
            self.table.insertRow(i)
            cb_widget = QWidget()
            cb_widget.setStyleSheet("background-color: transparent;")
            cb = QCheckBox()
            cb.setStyleSheet("margin: 0px; padding: 0px;")
            cb.stateChanged.connect(lambda state, r=i, c=cb: self.on_row_checkbox_changed(r, c))
            
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setSpacing(0)
            cb_layout.addWidget(cb, 0, Qt.AlignCenter)
            self.table.setCellWidget(i, 0, cb_widget)

            item_num = QTableWidgetItem(str(i + 1))
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            item_num.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, item_num)
            
            item_art = QTableWidgetItem(format_val(item.get("article")))
            self.table.setItem(i, 2, item_art)
            
            self.table.setItem(i, 3, QTableWidgetItem(format_val(item.get("name"))))
            
            item_qty = QTableWidgetItem(format_val(item.get("qty")))
            item_qty.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, item_qty)
            
            # Колонка "Назначение"
            purpose_widget = QWidget()
            purpose_widget.setStyleSheet("background-color: transparent;")
            purpose_layout = QHBoxLayout(purpose_widget)
            purpose_layout.setContentsMargins(2, 2, 2, 2)
            purpose_layout.setSpacing(5)
            
            purpose_lbl = QLabel(item.get("purpose", ""))
            purpose_lbl.setStyleSheet("background-color: transparent;")
            purpose_lbl.setWordWrap(False)
            
            btn_purpose = QPushButton("...")
            btn_purpose.setFixedSize(30, 25)
            btn_purpose.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold;")
            btn_purpose.clicked.connect(lambda checked, r=i: self.open_purpose_dialog(r))
            
            purpose_layout.addWidget(purpose_lbl, 1)
            purpose_layout.addWidget(btn_purpose, 0)
            self.table.setCellWidget(i, 5, purpose_widget)
            
        self.loading_table = False
        self.table.setSortingEnabled(False)
        self.table.clearSelection()
        self.main_app.update_order_badge()

    def on_item_changed(self, item):
        if self.loading_table: return
        row = item.row()
        col = item.column()
        if row >= len(self.main_app.order_manager.items): return
        try:
            if col == 2: self.main_app.order_manager.items[row]["article"] = item.text()
            elif col == 3: self.main_app.order_manager.items[row]["name"] = item.text()
            elif col == 4: self.main_app.order_manager.items[row]["qty"] = item.text()
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
        except Exception:
            pass

    def on_cell_clicked(self, row, column):
        if column == 0: return
        widget = self.table.cellWidget(row, 0)
        if widget:
            cb = widget.findChild(QCheckBox)
            if cb:
                cb.setChecked(not cb.isChecked())

    def delete_selected(self):
        rows_to_delete = []
        for row_idx in range(self.table.rowCount()):
            widget = self.table.cellWidget(row_idx, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    rows_to_delete.append(row_idx)
                    
        if not rows_to_delete:
            show_message(self, "Внимание", "Отметьте товары для удаления!", is_error=True)
            return
            
        if not show_confirm(self, "Подтверждение", f"Удалить выбранные товары ({len(rows_to_delete)} шт.)?"):
            return

        for row_idx in reversed(rows_to_delete):
            del self.main_app.order_manager.items[row_idx]
        
        self.main_app.order_manager.save_draft(self.main_app.draft_path)
        self.refresh()

    def clear_order(self):
        if not self.main_app.order_manager.items: return
        if not show_confirm(self, "Подтверждение", "Вы уверены, что хотите полностью очистить заявку?"):
            return
            
        self.main_app.order_manager.clear()
        self.main_app.editing_order = None
        self.main_app.save_editing_order_state()
        self.main_app.order_manager.save_draft(self.main_app.draft_path)
        self.refresh()
        self.main_app.update_order_badge()

    def cancel_edit(self):
        if not show_confirm(self, "Отмена", "Вы уверены, что хотите отменить редактирование отчёта?\nТекущая заявка будет очищена."):
            return
        self.main_app.editing_order = None
        self.main_app.save_editing_order_state()
        self.main_app.order_manager.clear()
        self.main_app.order_manager.save_draft(self.main_app.draft_path)
        self.refresh()

    def add_manual_item(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить товар вручную")
        dialog.setMinimumWidth(400)
        form = QFormLayout(dialog)

        f_art = QLineEdit()
        f_name = QLineEdit()
        f_qty = QLineEdit("1")
        f_purpose = QLineEdit()

        form.addRow("Артикул:", f_art)
        form.addRow("Наименование:", f_name)
        form.addRow("Кол-во:", f_qty)
        form.addRow("Назначение:", f_purpose)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Добавить")
        btn_ok.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
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
            new_item = [f_art.text().strip(), f_name.text().strip(), "", "", "", "", "Вручную"]
            self.main_app.order_manager.add_item(new_item)
            self.main_app.order_manager.items[-1]["qty"] = f_qty.text().strip()
            self.main_app.order_manager.items[-1]["purpose"] = f_purpose.text().strip()
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()

    def edit_item(self):
        selected_rows = []
        for row_idx in range(self.table.rowCount()):
            widget = self.table.cellWidget(row_idx, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    selected_rows.append(row_idx)

        if len(selected_rows) == 0:
            show_message(self, "Внимание", "Отметьте галочкой ОДИН товар для редактирования!", is_error=True)
            return
        if len(selected_rows) > 1:
            show_message(self, "Внимание", "Выбрано несколько товаров. Для редактирования отметьте только ОДИН!", is_error=True)
            return

        selected_row = selected_rows[0]
        item_data = self.main_app.order_manager.items[selected_row]

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать товар")
        dialog.setMinimumWidth(400)
        form = QFormLayout(dialog)

        f_art = QLineEdit(item_data.get("article", ""))
        f_name = QLineEdit(item_data.get("name", ""))
        f_qty = QLineEdit(str(item_data.get("qty", "")))
        f_purpose = QLineEdit(item_data.get("purpose", ""))

        form.addRow("Артикул:", f_art)
        form.addRow("Наименование:", f_name)
        form.addRow("Кол-во:", f_qty)
        form.addRow("Назначение:", f_purpose)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Сохранить")
        btn_ok.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
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
            self.main_app.order_manager.items[selected_row]["article"] = f_art.text().strip()
            self.main_app.order_manager.items[selected_row]["name"] = f_name.text().strip()
            self.main_app.order_manager.items[selected_row]["qty"] = f_qty.text().strip()
            self.main_app.order_manager.items[selected_row]["purpose"] = f_purpose.text().strip()
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()

    def ask_purpose_name(self, title, prompt, default=""):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(320)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(prompt))
        
        inp = QLineEdit(default)
        layout.addWidget(inp)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Отмена")
        
        btn_ok.setFixedSize(80, 30)
        btn_cancel.setFixedSize(80, 30)
        btn_ok.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px;")
        btn_cancel.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 4px;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        btn_ok.setDefault(True)
        
        if dialog.exec() == QDialog.Accepted:
            return inp.text().strip(), True
        return "", False

    def open_purpose_dialog(self, row_idx):
        dialog = QDialog(self)
        dialog.setWindowTitle("Справочник назначений")
        dialog.setMinimumSize(400, 500)
        layout = QVBoxLayout(dialog)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Название"])
        tree.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                color: black;
            }
            QTreeWidget::item:selected {
                background-color: #cce5ff;
                color: black;
            }
        """)
        layout.addWidget(tree)

        def load_tree():
            tree.clear()
            purposes = self.main_app.report_manager.get_purposes()
            nodes = {}
            for pid, name, parent_id in purposes:
                node = QTreeWidgetItem([name])
                node.setData(0, Qt.UserRole, pid)
                nodes[pid] = node
                if parent_id and parent_id in nodes:
                    nodes[parent_id].addChild(node)
                else:
                    tree.addTopLevelItem(node)

        load_tree()

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_add.setStyleSheet("""
            QPushButton { background-color: #5cb85c; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #449d44; }
            QPushButton:pressed { background-color: #398439; }
        """)
        btn_edit = QPushButton("Изменить")
        btn_edit.setStyleSheet("""
            QPushButton { background-color: #f0ad4e; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #ec971f; }
            QPushButton:pressed { background-color: #d58512; }
        """)
        btn_del = QPushButton("Удалить")
        btn_del.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)

        def add_purpose():
            name, ok = self.ask_purpose_name("Добавить", "Название назначения:")
            if ok and name:
                parent_item = tree.currentItem()
                parent_id = parent_item.data(0, Qt.UserRole) if parent_item else None
                if self.main_app.report_manager.add_purpose(name, parent_id):
                    load_tree()
                else:
                    show_message(dialog, "Ошибка", "Такое назначение уже существует!", is_error=True)

        def edit_purpose():
            item = tree.currentItem()
            if not item: return
            pid = item.data(0, Qt.UserRole)
            old_name = item.text(0)
            
            pwd = ask_password(dialog, "Пароль", "Введите пароль администратора:")
            if not pwd or not verify_password(pwd, self.main_app.export_config.get("admin_pwd_hash")):
                return
                
            new_name, ok = self.ask_purpose_name("Изменить", "Новое название:", old_name)
            if ok and new_name:
                if self.main_app.report_manager.update_purpose(pid, new_name):
                    load_tree()
                else:
                    show_message(dialog, "Ошибка", "Назначение с таким именем уже существует!", is_error=True)

        def del_purpose():
            item = tree.currentItem()
            if not item: return
            pid = item.data(0, Qt.UserRole)
            
            pwd = ask_password(dialog, "Пароль", "Введите пароль администратора:")
            if not pwd or not verify_password(pwd, self.main_app.export_config.get("admin_pwd_hash")):
                return
            
            if show_confirm(dialog, "Удаление", "Удалить это назначение?"):
                self.main_app.report_manager.delete_purpose(pid)
                load_tree()

        btn_add.clicked.connect(add_purpose)
        btn_edit.clicked.connect(edit_purpose)
        btn_del.clicked.connect(del_purpose)

        def on_select():
            item = tree.currentItem()
            if item:
                self.main_app.order_manager.items[row_idx]["purpose"] = item.text(0)
                self.main_app.order_manager.save_draft(self.main_app.draft_path)
                self.refresh()
                dialog.accept()

        tree.itemDoubleClicked.connect(on_select)
        
        btn_select = QPushButton("Выбрать")
        btn_select.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 8px;")
        btn_select.clicked.connect(on_select)
        layout.addWidget(btn_select)

        dialog.exec()

    def save_order(self):
        if not self.main_app.order_manager.items:
            show_message(self, "Внимание", "Заявка пуста!", is_error=True)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Создать отчёт")
        dialog.setMinimumWidth(450)
        form = QFormLayout(dialog)

        f_org = QLineEdit()
        f_fio = QLineEdit()
        f_phone = QLineEdit()
        f_email = QLineEdit()
        
        f_month = QComboBox()
        f_month.addItems(["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"])
        
        f_note = QLineEdit()
        
        f_status = QComboBox()
        f_status.addItems(["Ожидание", "Обработка", "Выполнено"])

        if self.main_app.editing_order:
            meta = self.main_app.editing_order["meta"]
            f_org.setText(meta.get("organization", ""))
            f_fio.setText(meta.get("fio", ""))
            f_phone.setText(meta.get("phone", ""))
            f_email.setText(meta.get("email", ""))
            m_idx = f_month.findText(meta.get("month", ""))
            if m_idx >= 0: f_month.setCurrentIndex(m_idx)
            f_note.setText(meta.get("note", ""))
            s_idx = f_status.findText(meta.get("status", "Ожидание"))
            if s_idx >= 0: f_status.setCurrentIndex(s_idx)

        form.addRow("Организация (обязательно):", f_org)
        form.addRow("ФИО:", f_fio)
        form.addRow("Контакт: № телефона", f_phone)
        form.addRow("Контакт: @ email", f_email)
        form.addRow("Месяц:", f_month)
        form.addRow("Примечание:", f_note)
        form.addRow("Статус отчёта:", f_status)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Сохранить")
        btn_ok.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
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
            if not f_org.text().strip():
                show_message(self, "Внимание", "Поле 'Организация' обязательно для заполнения!", is_error=True)
                return

            new_meta = {
                "organization": f_org.text().strip(), 
                "fio": f_fio.text().strip(),
                "phone": f_phone.text().strip(),
                "email": f_email.text().strip(),
                "month": f_month.currentText(),
                "note": f_note.text().strip(),
                "status": f_status.currentText(),
                "contact": "" 
            }
            
            # Теперь сохраняются ВСЕ товары, независимо от галочек
            items_to_save = self.main_app.order_manager.items.copy()
            
            if self.main_app.editing_order:
                order_id = self.main_app.editing_order["id"]
                self.main_app.report_manager.update_order(order_id, new_meta, items_to_save)
                show_message(self, "Успех", "Отчёт успешно обновлён!")
                self.main_app.editing_order = None
                self.main_app.save_editing_order_state()
            else:
                self.main_app.report_manager.add_order(new_meta, items_to_save)
                show_message(self, "Успех", "Отчёт успешно создан!")
            
            self.main_app.order_manager.items = []
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()
            
            self.main_app.tabs.setCurrentWidget(self.main_app.report_scr)
            self.main_app.report_scr.refresh()