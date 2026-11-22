import os
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
                               QDialog, QFormLayout, QLineEdit, QLabel, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from utils import show_message, show_confirm

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
        # Оставляем SelectRows для Drag & Drop, но без визуального выделения
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
        
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        
        btn_manual = QPushButton("+ Добавить")
        btn_manual.setStyleSheet("background-color: #5cb85c; color: black; font-weight: bold;")
        btn_manual.clicked.connect(self.add_manual_item)
        
        btn_edit = QPushButton("Редактировать")
        btn_edit.setStyleSheet("background-color: #f0ad4e; color: black; font-weight: bold;")
        btn_edit.clicked.connect(self.edit_item)
        
        btn_del_selected = QPushButton("Удалить выбранные")
        btn_del_selected.setStyleSheet("background-color: #d9534f; color: black; font-weight: bold;")
        btn_del_selected.clicked.connect(self.delete_selected)
        
        btn_clear = QPushButton("Очистить всё")
        btn_clear.clicked.connect(self.clear_order)
        
        self.btn_save = QPushButton("Создать отчёт")
        self.btn_save.setStyleSheet("background-color: #0078D7; color: black; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_order)
        
        self.btn_cancel_edit = QPushButton("Отмена")
        self.btn_cancel_edit.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "№", "Артикул", "Наименование", "Кол-во"])
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

    def handle_row_move(self, source, target):
        items = self.main_app.order_manager.items
        if 0 <= source < len(items) and 0 <= target < len(items):
            item = items.pop(source)
            items.insert(target, item)
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()

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
        # Снимаем выделение при клике правой кнопкой или в пустую область
        if event.button() == Qt.RightButton:
            self.table.clearSelection()
            return
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            self.table.clearSelection()
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

        form.addRow("Артикул:", f_art)
        form.addRow("Наименование:", f_name)
        form.addRow("Кол-во:", f_qty)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Добавить")
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
            new_item = [f_art.text().strip(), f_name.text().strip(), "", "", "", "", "Вручную"]
            self.main_app.order_manager.add_item(new_item)
            self.main_app.order_manager.items[-1]["qty"] = f_qty.text().strip()
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

        form.addRow("Артикул:", f_art)
        form.addRow("Наименование:", f_name)
        form.addRow("Кол-во:", f_qty)

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
            self.main_app.order_manager.items[selected_row]["article"] = f_art.text().strip()
            self.main_app.order_manager.items[selected_row]["name"] = f_name.text().strip()
            self.main_app.order_manager.items[selected_row]["qty"] = f_qty.text().strip()
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()

    def save_order(self):
        if not self.main_app.order_manager.items:
            show_message(self, "Внимание", "Заявка пуста!", is_error=True)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Создать отчёт")
        dialog.setMinimumWidth(450)
        form = QFormLayout(dialog)

        f_org = QLineEdit()
        f_ctc = QLineEdit()
        f_fio = QLineEdit()
        f_cat = QLineEdit()
        f_note = QLineEdit()

        if self.main_app.editing_order:
            meta = self.main_app.editing_order["meta"]
            f_org.setText(meta.get("organization", ""))
            f_ctc.setText(meta.get("contact", ""))
            f_fio.setText(meta.get("fio", ""))
            f_cat.setText(meta.get("category", ""))
            f_note.setText(meta.get("note", ""))

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
            new_meta = {
                "organization": f_org.text().strip(), "contact": f_ctc.text().strip(),
                "fio": f_fio.text().strip(), "category": f_cat.text().strip(),
                "note": f_note.text().strip(),
            }
            
            items_to_save, items_to_keep, any_checked = [], [], False
            for i, item in enumerate(self.main_app.order_manager.items):
                widget = self.table.cellWidget(i, 0)
                cb = widget.findChild(QCheckBox) if widget else None
                if cb and cb.isChecked():
                    any_checked = True
                    items_to_save.append(item)
                else:
                    items_to_keep.append(item)
            
            if not any_checked:
                items_to_save = self.main_app.order_manager.items.copy()
                items_to_keep = []
                
            if not items_to_save:
                show_message(self, "Внимание", "Нет товаров для сохранения!", is_error=True)
                return
            
            if self.main_app.editing_order:
                order_id = self.main_app.editing_order["id"]
                self.main_app.report_manager.update_order(order_id, new_meta, items_to_save)
                show_message(self, "Успех", "Отчёт успешно обновлён!\nНевыделенные товары остались в заявке.")
                self.main_app.editing_order = None
                self.main_app.save_editing_order_state()
            else:
                self.main_app.report_manager.add_order(new_meta, items_to_save)
                show_message(self, "Успех", "Отчёт успешно создан!\nНевыделенные товары остались в заявке.")
            
            self.main_app.order_manager.items = items_to_keep
            self.main_app.order_manager.save_draft(self.main_app.draft_path)
            self.refresh()
            
            # Переходим на страницу отчётов и обновляем список
            self.main_app.tabs.setCurrentWidget(self.main_app.report_scr)
            self.main_app.report_scr.refresh()