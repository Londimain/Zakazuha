# screens/order_screen.py
import os
import datetime
import sqlite3
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
                               QDialog, QFormLayout, QLineEdit, QLabel, QAbstractItemView,
                               QComboBox, QTreeWidget, QTreeWidgetItem, QMessageBox,
                               QApplication, QInputDialog)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from utils import show_message, show_confirm, ask_password, verify_password


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
        self.setSelectionMode(QAbstractItemView.NoSelection) # Отключаем синее выделение
        self.drag_start_row = -1

    def dropEvent(self, event):
        source_row = self.drag_start_row
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
        
        btn_clear = QPushButton("Очистить список")
        btn_clear.clicked.connect(self.clear_order)
        
        self.btn_save = QPushButton("Создать отчёт")
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: black; font-weight: bold; border-radius: 4px; padding: 6px; }
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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "", "№", "Артикул", "Наименование", 
            "Кол-во", "Прайс-лист", "Назначение"
        ])
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
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.setColumnWidth(5, 120)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(35)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.setSortingEnabled(False)
        
        self.table.row_moved.connect(self.handle_row_move)
        
        layout.addWidget(self.table)

        # --- Тост для уведомления о копировании ---
        self.toast = ToastLabel(self.main_app)

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
            if c in (0, 6):
                w = self.table.cellWidget(row, c)
                if w:
                    w.setStyleSheet("background-color: transparent;")
                    if c == 6:
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
            if c in (0, 6):
                w = self.table.cellWidget(row, c)
                if w:
                    w.setStyleSheet(f"background-color: {bg.name()};")
                    if c == 6:
                        lbl = w.findChild(QLabel)
                        if lbl:
                            lbl.setStyleSheet(f"background-color: transparent; color: black;")
            else:
                item = self.table.item(row, c)
                if item:
                    item.setData(Qt.BackgroundRole, bg)
                    item.setData(Qt.ForegroundRole, QColor("black"))

    def _compute_item_sources(self, items):
        """
        Возвращает dict: index -> строка для колонки «Прайс-лист».
        """
        articles_to_check = []
        for item in items:
            src = item.get("source") or ""
            art = item.get("article") or ""
            if art and (not src or src == "Вручную"):
                articles_to_check.append(art.lower())

        article_sources = {}
        if articles_to_check:
            try:
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

        result = {}
        for i, item in enumerate(items):
            src = item.get("source") or ""
            art = (item.get("article") or "").lower()

            if src and src != "Вручную":
                result[i] = src
            else:
                found = article_sources.get(art, set())
                if found:
                    if len(found) == 1:
                        result[i] = list(found)[0]
                    else:
                        result[i] = ", ".join(sorted(found))
                else:
                    result[i] = "= Своё ="
        return result

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
            self.table.drag_start_row = -1
            return
            
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            self.table.drag_start_row = -1
            QTableWidget.mousePressEvent(self.table, event)
            return
            
        col = index.column()
        row = index.row()
        
        # 0. Чекбокс
        if col == 0:
            widget = self.table.cellWidget(row, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(not cb.isChecked())
            self.table.drag_start_row = -1
            event.accept()
            return

        # 2 и 3. Артикул и Наименование (копирование)
        if col in (2, 3):
            self.copy_cell_text(row, col)
            self.table.drag_start_row = -1
            event.accept()
            return
        
        # 4. Количество (диалог)
        if col == 4:
            self.edit_qty_dialog(row)
            self.table.drag_start_row = -1
            event.accept()
            return
            
        # 6. Назначение (открытие справочника)
        if col == 6:
            self.open_purpose_dialog(row)
            self.table.drag_start_row = -1
            event.accept()
            return
            
        # Для остальных колонок (1 - номер, 5 - прайс-лист) 
        # сохраняем возможность перетаскивания строк
        self.table.drag_start_row = row
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
        item_sources = self._compute_item_sources(items)

        self.table.setRowCount(0)
        for i, item in enumerate(items):
            self.table.insertRow(i)

            # 0. Чекбокс
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

            # 1. №
            item_num = QTableWidgetItem(str(i + 1))
            item_num.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_num.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, item_num)
            
            # 2. Артикул — ТОЛЬКО КОПИРОВАНИЕ
            item_art = QTableWidgetItem(format_val(item.get("article")))
            item_art.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable) 
            self.table.setItem(i, 2, item_art)
            
            # 3. Наименование — ТОЛЬКО КОПИРОВАНИЕ
            item_name = QTableWidgetItem(format_val(item.get("name")))
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(i, 3, item_name)
            
            # 4. Кол-во (только чтение, клик открывает диалог)
            item_qty = QTableWidgetItem(format_val(item.get("qty")))
            item_qty.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_qty.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, item_qty)

            # 5. Прайс-лист
            item_price = QTableWidgetItem(item_sources.get(i, "= Своё ="))
            item_price.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_price.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, item_price)
            
            # 6. Назначение
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
            self.table.setCellWidget(i, 6, purpose_widget)
            
        self.loading_table = False
        self.table.setSortingEnabled(False)
        self.main_app.update_order_badge()

    def edit_qty_dialog(self, row):
        if row >= len(self.main_app.order_manager.items):
            return
        item = self.main_app.order_manager.items[row]
        current_qty = str(item.get("qty", "1"))
        
        try:
            current_val = int(float(current_qty.replace(",", ".")))
        except ValueError:
            current_val = 1

        dialog = QDialog(self)
        dialog.setWindowTitle("Изменить количество")
        dialog.setMinimumWidth(320)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("Укажите количество:")
        layout.addWidget(lbl)

        from PySide6.QtGui import QIntValidator
        inp = QLineEdit(str(current_val))
        inp.setValidator(QIntValidator(0, 999999, self)) # Только целые числа
        inp.setAlignment(Qt.AlignCenter) # Текст по центру
        
        # Явно задаем цвета для выделения, чтобы текст не сливался с фоном
        inp.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                font-size: 14px;
                color: black;
                selection-background-color: #0078D7; /* Синий фон при выделении */
                selection-color: white;              /* Белый текст при выделении */
            }
        """)
        layout.addWidget(inp)
        
        # Автоматическое выделение текста при открытии для быстрой замены
        inp.selectAll()

        btn_layout = QHBoxLayout()
        
        btn_ok = QPushButton("Заменить")
        btn_ok.setMinimumSize(100, 32)
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: black; font-weight: bold; border-radius: 4px; border: 1px solid #005a9e; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_ok.clicked.connect(dialog.accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setMinimumSize(100, 32)
        btn_cancel.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: black; font-weight: bold; border-radius: 4px; border: 1px solid #ac2925; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        btn_cancel.clicked.connect(dialog.reject)

        # Размещение кнопок по центру
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            new_text = inp.text().strip()
            if new_text:
                item["qty"] = new_text
                self.main_app.order_manager.save_draft(self.main_app.draft_path)
                self.refresh()

    def on_item_changed(self, item):
        pass

    def on_cell_clicked(self, row, column):
        # Чекбокс переключается только при клике на сам виджет чекбокса.
        # Клики по другим колонкам (номер, прайс-лист, назначение и т.д.) 
        # больше не будут его переключать.
        pass

    def copy_cell_text(self, row, column):
        item = self.table.item(row, column)
        if not item:
            return
        text = item.text()
        if not text:
            return
        
        QApplication.clipboard().setText(text)
        
        # Зелёная вспышка: светло-зелёный фон + тёмно-зелёный текст
        item.setBackground(QColor("#b3e5b3"))
        item.setForeground(QColor("#005500"))
        
        # Уникальный идентификатор
        self._flash_id = getattr(self, '_flash_id', 0) + 1
        current_id = self._flash_id
        QTimer.singleShot(500, lambda: self._restore_cell_after_copy(row, column, current_id))
        
        # Показываем плашку "Скопировано"
        self.toast.show_toast(text)

    def _restore_cell_after_copy(self, row, column, flash_id):
        if flash_id != getattr(self, '_flash_id', 0):
            return
        if row < 0 or row >= self.table.rowCount():
            return
        item = self.table.item(row, column)
        if not item:
            return
        if self.hover_row == row:
            item.setBackground(QColor("#e2eaf1"))
            item.setForeground(QColor("black"))
        else:
            item.setData(Qt.BackgroundRole, None)
            item.setData(Qt.ForegroundRole, None)

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
        if not self.main_app.order_manager.items:
            return
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

        f_purpose_btn = QPushButton("...")
        f_purpose_btn.setFixedSize(30, 25)
        f_purpose_btn.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold;")

        def pick_purpose():
            val = self._show_purpose_dialog(dialog, f_purpose.text().strip())
            if val is not None:
                f_purpose.setText(val)

        f_purpose_btn.clicked.connect(pick_purpose)

        purpose_row = QHBoxLayout()
        purpose_row.setContentsMargins(0, 0, 0, 0)
        purpose_row.addWidget(f_purpose, 1)
        purpose_row.addWidget(f_purpose_btn, 0)

        form.addRow("Артикул:", f_art)
        form.addRow("Наименование:", f_name)
        form.addRow("Кол-во:", f_qty)
        form.addRow("Назначение:", purpose_row)

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
        
        # Проверяем источник товара по колонке "Прайс-лист" (индекс 5)
        source_item = self.table.item(selected_row, 5)
        source_text = source_item.text() if source_item else ""
        
        if source_text != "= Своё =":
            show_message(
                self, 
                "Редактирование запрещено", 
                "Вы можете редактировать только товары, у которых в колонке «Прайс-лист» указано «= Своё =».\n\n"
                "Товары из прайс-листов (TDM, IEK и т.д.) защищены от ручного изменения.", 
                is_error=True
            )
            return

        item_data = self.main_app.order_manager.items[selected_row]

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать товар")
        dialog.setMinimumWidth(400)
        form = QFormLayout(dialog)

        f_art = QLineEdit(item_data.get("article", ""))
        f_name = QLineEdit(item_data.get("name", ""))
        f_qty = QLineEdit(str(item_data.get("qty", "")))
        
        # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
        f_purpose = QLineEdit(item_data.get("purpose", ""))
        f_purpose.setReadOnly(True) # Запрещаем редактирование
        f_purpose.setCursor(Qt.PointingHandCursor) # Курсор-рука
        f_purpose.setStyleSheet("background-color: #f8f9fa; color: black;") # Легкий серый фон для понимания, что поле только для чтения

        f_purpose_btn = QPushButton("...")
        f_purpose_btn.setFixedSize(30, 25)
        f_purpose_btn.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold;")

        def pick_purpose():
            val = self._show_purpose_dialog(dialog, f_purpose.text().strip())
            if val is not None:
                f_purpose.setText(val)

        f_purpose_btn.clicked.connect(pick_purpose)
        # Позволяем открывать справочник при клике прямо по полю ввода
        f_purpose.mousePressEvent = lambda event: pick_purpose()
        # -----------------------

        purpose_row = QHBoxLayout()
        purpose_row.setContentsMargins(0, 0, 0, 0)
        purpose_row.addWidget(f_purpose, 1)
        purpose_row.addWidget(f_purpose_btn, 0)

        form.addRow("Артикул:", f_art)
        form.addRow("Наименование:", f_name)
        form.addRow("Кол-во:", f_qty)
        form.addRow("Назначение:", purpose_row)

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

    def _show_purpose_dialog(self, parent, current_purpose=""):
        current_purpose = str(current_purpose).strip()
        dialog = QDialog(parent)
        dialog.setWindowTitle("Справочник назначений")
        dialog.setMinimumSize(450, 550)
        layout = QVBoxLayout(dialog)

        # Создаем кастомный класс дерева для перехвата кликов
        class CustomTree(QTreeWidget):
            def mousePressEvent(self, event):
                item = self.itemAt(event.pos())
                if not item:
                    self.clearSelection() # Снимаем выделение при клике в пустоту
                    self.setCurrentItem(None)
                super().mousePressEvent(event)

            def keyPressEvent(self, event):
                # Обработка нажатия Enter для подтверждения выбора
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    btn = self.window().findChild(QPushButton, "btn_select_purpose")
                    if btn:
                        btn.click()
                else:
                    super().keyPressEvent(event)

        tree = CustomTree()
        tree.setHeaderLabels(["Название"])
        tree.setSortingEnabled(True)
        tree.sortByColumn(0, Qt.AscendingOrder)
        tree.setExpandsOnDoubleClick(False)
        
        # Добавляем эффект наведения (hover) и делаем выделение светло-оранжевым
        tree.setStyleSheet("""
            QTreeWidget { background-color: white; color: black; font-size: 14px; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:hover { background-color: #f0f8ff; } 
            QTreeWidget::item:selected { background-color: #ffe0b2; color: black; }
        """)
        layout.addWidget(tree)

        current_node = None

        def load_tree():
            nonlocal current_node
            tree.clear()
            current_node = None
            purposes = self.main_app.report_manager.get_purposes()
            nodes = {}
            for pid, name, parent_id in purposes:
                node = QTreeWidgetItem([name])
                node.setData(0, Qt.UserRole, pid)
                nodes[pid] = node
                
                # Запоминаем нужный узел
                if current_purpose and name == current_purpose:
                    current_node = node
                
                if parent_id and parent_id in nodes:
                    nodes[parent_id].addChild(node)
                else:
                    tree.addTopLevelItem(node)
            
            # Делаем категории (папки) жирными. 
            # Убрано принудительное разворачивание всех папок!
            for i in range(tree.topLevelItemCount()):
                top = tree.topLevelItem(i)
                if top.childCount() > 0:
                    font = top.font(0)
                    font.setBold(True)
                    top.setFont(0, font)

        load_tree()
        
        # Выделяем текущее назначение и разворачиваем ТОЛЬКО его категорию
        if current_node:
            # Разворачиваем всех родителей, если назначение вложенное
            p = current_node.parent()
            while p:
                p.setExpanded(True)
                p = p.parent()
            tree.setCurrentItem(current_node)
            tree.scrollToItem(current_node)

        # Разворачивание/сворачивание при клике на всю строку категории
        def on_tree_item_clicked(item, column):
            if item and item.childCount() > 0:
                item.setExpanded(not item.isExpanded())

        tree.itemClicked.connect(on_tree_item_clicked)

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
            if not item:
                return
            pid = item.data(0, Qt.UserRole)
            old_name = item.text(0)
            pwd = ask_password(dialog, "Пароль", "Введите пароль администратора:")
            if not pwd or not verify_password(pwd, self.main_app.export_config.get("admin_pwd_hash")):
                return
            new_name, ok = self.ask_purpose_name("Изменить", "Новое название:", old_name)
            if ok and new_name:
                if self.main_app.report_manager.update_purpose(pid, new_name):
                    # Обновляем в текущей заявке
                    for draft_item in self.main_app.order_manager.items:
                        if draft_item.get("purpose") == old_name:
                            draft_item["purpose"] = new_name
                    self.main_app.order_manager.save_draft(self.main_app.draft_path)
                    self.refresh()
                    current_purpose = new_name
                    load_tree()
                    if current_node:
                        tree.setCurrentItem(current_node)
                else:
                    show_message(dialog, "Ошибка", "Назначение с таким именем уже существует!", is_error=True)

        def del_purpose():
            item = tree.currentItem()
            if not item:
                return
            pid = item.data(0, Qt.UserRole)
            old_name = item.text(0)
            pwd = ask_password(dialog, "Пароль", "Введите пароль администратора:")
            if not pwd or not verify_password(pwd, self.main_app.export_config.get("admin_pwd_hash")):
                return
            
            msg = f"Удалить назначение «{old_name}»?\n\nОно также исчезнет из всех товаров, где было указано."
            if show_confirm(dialog, "Удаление", msg):
                self.main_app.report_manager.delete_purpose(pid)
                # Очищаем в текущей заявке
                for draft_item in self.main_app.order_manager.items:
                    if draft_item.get("purpose") == old_name:
                        draft_item["purpose"] = ""
                self.main_app.order_manager.save_draft(self.main_app.draft_path)
                self.refresh()
                current_purpose = ""
                load_tree()

        btn_add.clicked.connect(add_purpose)
        btn_edit.clicked.connect(edit_purpose)
        btn_del.clicked.connect(del_purpose)

        result = {"value": None}

        def on_select():
            item = tree.currentItem()
            if item:
                if item.childCount() > 0:
                    show_message(dialog, "Внимание", "Вы не можете выбрать целую категорию.\nВыберите конкретное назначение внутри неё.", is_error=True)
                    return
                result["value"] = item.text(0)
                dialog.accept()

        def on_clear():
            if show_confirm(dialog, "Очистка назначения", "Вы уверены, что хотите очистить назначение для этого товара?"):
                result["value"] = ""  # Пустая строка означает сброс назначения
                dialog.accept()

        bottom_btn_layout = QHBoxLayout()
        
        btn_clear = QPushButton("Очистить назначение")
        btn_clear.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: black; font-weight: bold; padding: 8px; border-radius: 4px; border: 1px solid #999; }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #b0b0b0; }
        """)
        btn_clear.clicked.connect(on_clear)

        btn_select = QPushButton("Выбрать")
        btn_select.setObjectName("btn_select_purpose")
        btn_select.setDefault(True)
        btn_select.setAutoDefault(True)
        btn_select.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_select.clicked.connect(on_select)

        bottom_btn_layout.addWidget(btn_clear)
        bottom_btn_layout.addWidget(btn_select)
        layout.addLayout(bottom_btn_layout)

        if dialog.exec() == QDialog.Accepted:
            return result["value"]
        return None

    def open_purpose_dialog(self, row_idx):
        current = self.main_app.order_manager.items[row_idx].get("purpose", "")
        val = self._show_purpose_dialog(self, current)
        if val is not None:
            self.main_app.order_manager.items[row_idx]["purpose"] = val
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