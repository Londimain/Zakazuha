# screens/settings_screen.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QGroupBox, QPushButton, QGridLayout, 
                               QFrame, QLineEdit, QFileDialog)
from PySide6.QtGui import QColor
from utils import get_custom_color, show_message, verify_password, hash_password, show_input

class SettingsScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        layout = QVBoxLayout(self)

        # --- Группа: База данных ---
        db_group = QGroupBox("Настройки базы данных")
        db_layout = QVBoxLayout()

        db_info = QLabel(
            "Укажите путь к файлу базы данных (cache.db) на сетевом диске.\n"
            "Если очистить поле и применить, программа вернется к локальной базе."
        )
        db_info.setStyleSheet("color: gray; font-size: 12px; margin-bottom: 5px;")
        db_layout.addWidget(db_info)

        path_layout = QHBoxLayout()
        self.db_path_input = QLineEdit()
        
        # Загружаем текущий путь (если пусто — значит локальная)
        current_db = self.main_app.export_config.get("db_path", "")
        self.db_path_input.setText(current_db)
        self.db_path_input.setPlaceholderText("Локальная база (по умолчанию)")
        
        path_layout.addWidget(self.db_path_input)

        btn_browse_db = QPushButton("Обзор...")
        btn_browse_db.setFixedWidth(100)
        btn_browse_db.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: black; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #b0b0b0; }
        """)
        btn_browse_db.clicked.connect(self.browse_db)
        path_layout.addWidget(btn_browse_db)
        
        db_layout.addLayout(path_layout)
        
        btn_apply_db = QPushButton("Применить путь к базе")
        btn_apply_db.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_apply_db.clicked.connect(self.apply_db_path)
        db_layout.addWidget(btn_apply_db)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # --- Группа: Оформление ---
        group = QGroupBox("Оформление")
        group_layout = QVBoxLayout()

        group_layout.addWidget(QLabel("Выберите цветовую тему:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная", "Синяя", "Своя тема"])
        self.theme_combo.setCurrentText(self.main_app.export_config.get("theme", "Светлая"))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        
        group_layout.addWidget(self.theme_combo)
        
        # Настройки кастомной темы
        self.custom_frame = QFrame()
        custom_layout = QGridLayout(self.custom_frame)
        
        self.color_btns = {}
        labels = {
            "bg": "Фон приложения", "text": "Текст",
            "button_bg": "Фон кнопок", "button_text": "Текст кнопок",
            "table_bg": "Фон таблиц", "header_bg": "Шапка таблиц",
            "input_bg": "Поля ввода"
        }
        
        row = 0
        for key, text in labels.items():
            lbl = QLabel(text)
            btn = QPushButton("Выбрать цвет")
            btn.setFixedWidth(120)
            btn.clicked.connect(lambda checked, k=key: self.pick_color(k))
            self.color_btns[key] = btn
            custom_layout.addWidget(lbl, row, 0)
            custom_layout.addWidget(btn, row, 1)
            row += 1
            
        group_layout.addWidget(self.custom_frame)
        
        self.custom_frame.setVisible(self.theme_combo.currentText() == "Своя тема")
        self.update_color_btns()

        group.setLayout(group_layout)
        layout.addWidget(group)
        
        # --- Группа: Безопасность ---
        sec_group = QGroupBox("Безопасность")
        sec_layout = QVBoxLayout()
        
        btn_change_login_pwd = QPushButton("Сменить пароль на вход")
        btn_change_login_pwd.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: black; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #b0b0b0; }
        """)
        btn_change_login_pwd.clicked.connect(self.change_login_pwd)
        
        btn_change_admin_pwd = QPushButton("Сменить пароль администратора")
        btn_change_admin_pwd.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: black; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #b0b0b0; }
        """)
        btn_change_admin_pwd.clicked.connect(self.change_admin_pwd)
        
        sec_layout.addWidget(btn_change_login_pwd)
        sec_layout.addWidget(btn_change_admin_pwd)
        sec_group.setLayout(sec_layout)
        layout.addWidget(sec_group)
        
        layout.addStretch()

    def browse_db(self):
        start_dir = os.path.dirname(self.db_path_input.text()) if self.db_path_input.text() else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите файл базы данных", 
            start_dir, 
            "SQLite Database (*.db);;All Files (*)"
        )
        if file_path:
            file_path = os.path.normpath(file_path)
            self.db_path_input.setText(file_path)

    def apply_db_path(self):
        new_path = self.db_path_input.text().strip()
        
        if self.main_app.switch_db(new_path):
            show_message(self, "Успех", "Путь к базе данных успешно обновлен.\nИнтерфейс переключен на новую базу.")
        else:
            # Если переключение не удалось - возвращаем в поле прежний рабочий путь
            current_db = self.main_app.export_config.get("db_path", "")
            self.db_path_input.setText(current_db)

    def change_theme(self, theme_name):
        self.custom_frame.setVisible(theme_name == "Своя тема")
        self.main_app.apply_theme(theme_name)
        self.update_color_btns()

    def update_color_btns(self):
        ct = self.main_app.export_config.get("custom_theme", {})
        for key, btn in self.color_btns.items():
            color_hex = ct.get(key, "#ffffff")
            btn.setStyleSheet(f"background-color: {color_hex}; color: {'black' if self.is_light(color_hex) else 'white'}; border: 1px solid #999;")
            btn.setText(color_hex)

    def is_light(self, hex_color):
        c = QColor(hex_color)
        # Формула яркости
        return (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000 > 128

    def pick_color(self, key):
        ct = self.main_app.export_config.get("custom_theme", {})
        current_color = QColor(ct.get(key, "#ffffff"))
        
        new_color = get_custom_color(self, current_color)
        if new_color and new_color.isValid():
            if "custom_theme" not in self.main_app.export_config:
                self.main_app.export_config["custom_theme"] = {}
            
            self.main_app.export_config["custom_theme"][key] = new_color.name()
            self.main_app.save_config()
            self.main_app.apply_theme("Своя тема")
            self.update_color_btns()
            
    def change_login_pwd(self):
        old_pwd, ok1 = show_input(self, "Смена пароля", "Введите текущий пароль на вход:", echo_password=True)
        if not ok1: return
        if not verify_password(old_pwd, self.main_app.export_config.get("login_pwd_hash")):
            show_message(self, "Ошибка", "Неверный текущий пароль!", is_error=True)
            return
            
        new_pwd, ok2 = show_input(self, "Смена пароля", "Введите новый пароль на вход:", echo_password=True)
        if not ok2 or not new_pwd: return
        
        new_hash = hash_password(new_pwd)
        self.main_app.export_config["login_pwd_hash"] = new_hash
        self.main_app.save_config()
        show_message(self, "Успех", "Пароль на вход успешно изменен.")

    def change_admin_pwd(self):
        old_pwd, ok1 = show_input(self, "Смена пароля", "Введите текущий пароль администратора:", echo_password=True)
        if not ok1: return
        if not verify_password(old_pwd, self.main_app.export_config.get("admin_pwd_hash")):
            show_message(self, "Ошибка", "Неверный текущий пароль!", is_error=True)
            return
            
        new_pwd, ok2 = show_input(self, "Смена пароля", "Введите новый пароль администратора:", echo_password=True)
        if not ok2 or not new_pwd: return
        
        new_hash = hash_password(new_pwd)
        self.main_app.export_config["admin_pwd_hash"] = new_hash
        self.main_app.save_config()
        show_message(self, "Успех", "Пароль администратора успешно изменен.")