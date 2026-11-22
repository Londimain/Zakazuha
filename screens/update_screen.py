# screens/update_screen.py
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QProgressBar, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QFileDialog, QInputDialog, QLineEdit)
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from modules.price_manager import PRICE_SOURCES
from utils import show_message, show_confirm, ask_password, show_input, verify_password

class UpdateThread(QThread):
    progress = Signal(int)
    finished = Signal(bool, str, str)

    def __init__(self, price_manager, key):
        super().__init__()
        self.price_manager = price_manager
        self.key = key

    def run(self):
        def on_progress(p):
            self.progress.emit(p)
        def on_done(ok, msg):
            self.finished.emit(ok, msg, self.key)
        self.price_manager.update_source(self.key, on_progress, on_done)

class UpdateScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.buttons = {}
        self.is_updating = False

        layout = QVBoxLayout(self)

        top_btn_layout = QHBoxLayout()
        
        btn_add_url = QPushButton("+ Добавить по ссылке")
        btn_add_url.setStyleSheet("background-color: #5cb85c; color: black; font-weight: bold; padding: 6px;")
        btn_add_url.clicked.connect(self.add_custom_url)
        
        btn_add_file = QPushButton("+ Добавить из файла")
        btn_add_file.setStyleSheet("background-color: #5cb85c; color: black; font-weight: bold; padding: 6px;")
        btn_add_file.clicked.connect(self.add_custom_file)
        
        top_btn_layout.addWidget(btn_add_url)
        top_btn_layout.addWidget(btn_add_file)
        top_btn_layout.addStretch()
        layout.addLayout(top_btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["База", "Тип", "Объём", "Дата обновления", "Действие"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        layout.addWidget(self.table)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        layout.addStretch()

    def refresh_info(self):
        self.table.setRowCount(0)
        self.buttons.clear()
        
        all_sources = self.main_app.price_manager.get_all_sources()
        custom_sources = dict(self.main_app.price_manager.get_custom_sources())
        
        for k in PRICE_SOURCES:
            if k not in all_sources:
                all_sources.append(k)

        for row_idx, key in enumerate(all_sources):
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(key))
            
            is_builtin = key in PRICE_SOURCES
            is_custom = key in custom_sources
            
            if is_builtin:
                src_type = "Встроенный"
            elif is_custom and custom_sources[key].startswith("file://"):
                src_type = "Свой файл"
            else:
                src_type = "Свой URL"
                
            self.table.setItem(row_idx, 1, QTableWidgetItem(src_type))

            info = self.main_app.price_manager.get_local_info(key)
            if not info or not info[2]:
                size_text = "—"
                date_text = "не скачан"
            else:
                size_text = f"{info[1]} МБ"
                date_text = datetime.datetime.fromtimestamp(info[2]).strftime("%d.%m.%Y %H:%M")
                
            self.table.setItem(row_idx, 2, QTableWidgetItem(size_text))
            self.table.setItem(row_idx, 3, QTableWidgetItem(date_text))
            
            # --- Кнопки действий ---
            btn_container = QWidget()
            btn_container.setStyleSheet("background-color: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            
            btn_update = QPushButton("Обновить")
            btn_update.setFixedSize(85, 28)
            btn_update.setStyleSheet("background-color: #e0e0e0; color: black; border: 1px solid #999; border-radius: 4px; font-weight: bold;")
            btn_update.clicked.connect(lambda checked, k=key: self.update_price(k))
            self.buttons[key] = btn_update
            btn_layout.addWidget(btn_update)
            
            btn_edit = QPushButton("Изменить")
            btn_edit.setFixedSize(85, 28)
            btn_edit.setStyleSheet("background-color: #f0ad4e; color: black; border: 1px solid #999; border-radius: 4px; font-weight: bold;")
            btn_edit.clicked.connect(lambda checked, k=key, t=src_type: self.edit_source(k, t))
            btn_layout.addWidget(btn_edit)
            
            btn_del = QPushButton("Удалить")
            btn_del.setFixedSize(85, 28)
            btn_del.setStyleSheet("background-color: #d9534f; color: white; border: 1px solid #999; border-radius: 4px; font-weight: bold;")
            btn_del.clicked.connect(lambda checked, k=key: self.delete_custom_price(k))
            btn_layout.addWidget(btn_del)
                
            btn_layout.addStretch()
            self.table.setCellWidget(row_idx, 4, btn_container)
        
        self.table.resizeColumnToContents(4)

    def add_custom_url(self):
        pwd = ask_password(self, "Пароль", "Введите пароль администратора:")
        if pwd is None: return
        
        admin_hash = self.main_app.export_config.get("admin_pwd_hash")
        if not verify_password(pwd, admin_hash):
            show_message(self, "Ошибка", "Неверный пароль!", is_error=True)
            return

        name, ok = show_input(self, "Название", "Введите название для прайса (например, 'Мой поставщик'):")
        if not ok or not name.strip():
            return
            
        url, ok = show_input(self, "Ссылка", "Введите прямую ссылку на файл прайса (.xls, .xlsx, .zip):")
        if not ok or not url.strip():
            return

        try:
            self.main_app.price_manager.register_custom_url(name.strip(), url.strip())
            show_message(self, "Успех", f"Прайс '{name.strip()}' добавлен. Теперь нажмите 'Обновить', чтобы скачать его.")
            self.refresh_info()
            self.main_app.search_scr.refresh_sources()
        except Exception as e:
            show_message(self, "Ошибка", str(e), is_error=True)

    def add_custom_file(self):
        pwd = ask_password(self, "Пароль", "Введите пароль администратора:")
        if pwd is None: return
        
        admin_hash = self.main_app.export_config.get("admin_pwd_hash")
        if not verify_password(pwd, admin_hash):
            show_message(self, "Ошибка", "Неверный пароль!", is_error=True)
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл прайса", "", "Excel Files (*.xlsx *.xls)")
        if not file_path:
            return
            
        name, ok = QInputDialog.getText(self, "Название", "Введите название для этого прайса (например, 'Свой прайс'):")
        if not ok or not name.strip():
            return
            
        try:
            self.main_app.price_manager.import_custom_file(file_path, name.strip())
            show_message(self, "Успех", f"Прайс '{name.strip()}' успешно добавлен!")
            self.refresh_info()
            self.main_app.search_scr.refresh_sources()
        except Exception as e:
            show_message(self, "Ошибка", str(e), is_error=True)

    def edit_source(self, key, src_type):
        # ПРОВЕРКА ПАРОЛЯ
        pwd = ask_password(self, "Пароль", "Введите пароль администратора:")
        if pwd is None: return
        
        admin_hash = self.main_app.export_config.get("admin_pwd_hash")
        if not verify_password(pwd, admin_hash):
            show_message(self, "Ошибка", "Неверный пароль!", is_error=True)
            return

        if "файл" in src_type.lower():
            file_path, _ = QFileDialog.getOpenFileName(self, "Выберите новый файл прайса", "", "Excel Files (*.xlsx *.xls)")
            if not file_path:
                return
            try:
                self.main_app.price_manager.import_custom_file(file_path, key)
                show_message(self, "Успех", f"Файл для '{key}' обновлен.")
                self.refresh_info()
            except Exception as e:
                show_message(self, "Ошибка", str(e), is_error=True)
        else:
            current_url = self.main_app.price_manager.get_source_url(key) or ""
            new_url, ok = show_input(self, "Изменить ссылку", f"Введите новую ссылку для '{key}':", current_url)
            if ok and new_url.strip():
                self.main_app.price_manager.update_custom_source_url(key, new_url.strip())
                self.refresh_info()
                show_message(self, "Успех", "Ссылка обновлена. Не забудьте обновить прайс.")

    def delete_custom_price(self, key):
        # ПРОВЕРКА ПАРОЛЯ
        pwd = ask_password(self, "Пароль", "Введите пароль администратора:")
        if pwd is None: return
        
        admin_hash = self.main_app.export_config.get("admin_pwd_hash")
        if not verify_password(pwd, admin_hash):
            show_message(self, "Ошибка", "Неверный пароль!", is_error=True)
            return

        if not show_confirm(self, "Удаление", f"Удалить прайс '{key}' из базы?\nТовары этого прайса исчезнут из поиска."):
            return
        self.main_app.price_manager.delete_source(key)
        self.refresh_info()
        self.main_app.search_scr.refresh_sources()

    def update_price(self, key):
        if self.is_updating: return
        self.is_updating = True
        
        for k, btn in self.buttons.items():
            btn.setEnabled(False)
            if k == key:
                btn.setText("Загрузка...")
                btn.setStyleSheet("background-color: #f0ad4e; color: black; border: 1px solid #999; border-radius: 4px; font-weight: bold;")
        
        self.progress.setValue(0)
        self.thread = UpdateThread(self.main_app.price_manager, key)
        self.thread.progress.connect(self.progress.setValue)
        self.thread.finished.connect(self.on_update_finished)
        self.thread.start()

    def on_update_finished(self, ok, msg, key):
        btn = self.buttons.get(key)
        if btn:
            if ok:
                btn.setText("Готово")
                btn.setStyleSheet("background-color: #5cb85c; color: white; border: 1px solid #999; border-radius: 4px; font-weight: bold;")
            else:
                btn.setText("Ошибка")
                btn.setStyleSheet("background-color: #d9534f; color: white; border: 1px solid #999; border-radius: 4px; font-weight: bold;")
        
        self.progress.setValue(100 if ok else 0)
        self.refresh_info()
        QTimer.singleShot(2500, self.reset_all_buttons)

    def reset_all_buttons(self):
        self.is_updating = False
        self.refresh_info()

    def showEvent(self, event):
        self.refresh_info()
        super().showEvent(event)