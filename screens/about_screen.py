# screens/about_screen.py
import os
import sys
import json
from utils import show_message, show_confirm
from modules.updater import UpdateChecker
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
                               QPushButton, QDialog, QTextBrowser)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from version import APP_NAME, __version__, AUTHOR, YEAR, DEVELOPER

REPO_URL = "https://github.com/Londimain/Zakazuha"

class AboutScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Заголовок ---
        title = QLabel(f'<span style="color: #0078D7; font-size: 32px; font-weight: bold;">{APP_NAME}</span>')
        title.setAlignment(Qt.AlignCenter)
        title.setTextFormat(Qt.RichText)

        subtitle = QLabel(f"Версия: {__version__}")
        subtitle.setStyleSheet("font-size: 16px; color: gray;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        # --- Кнопки управления ---
        btn_control_layout = QHBoxLayout()
        btn_control_layout.addStretch()
        
        self.btn_force_update = QPushButton("Проверить обновления")
        self.btn_force_update.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: black; font-weight: bold; padding: 6px 15px; border-radius: 6px; font-size: 13px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        self.btn_force_update.setCursor(Qt.PointingHandCursor)
        self.btn_force_update.clicked.connect(self.force_check_update)
        
        self.btn_changelog = QPushButton("История обновлений")
        self.btn_changelog.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: black; font-weight: bold; padding: 6px 15px; border-radius: 6px; font-size: 13px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        self.btn_changelog.setCursor(Qt.PointingHandCursor)
        self.btn_changelog.clicked.connect(self.show_changelog)
        
        btn_control_layout.addWidget(self.btn_force_update)
        btn_control_layout.addWidget(self.btn_changelog)
        btn_control_layout.addStretch()

        # --- Описание ---
        desc = QLabel(
            "Профессиональная программа для автоматизации работы с прайс-листами: быстрый поиск товаров "
            "по нескольким поставщикам, формирование заявок на закупку и выгрузка в Excel. "
            "Рассчитана на работу в небольшой команде с возможностью использования общей сетевой базы данных."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 15px; margin-bottom: 10px;")

        # --- Основные возможности ---
        features_title = QLabel('<span style="color: #0078D7; font-size: 16px;"><b>Основные возможности:</b></span>')
        features_title.setTextFormat(Qt.RichText)

        features_text = QLabel(
            "• <b>Умный поиск:</b> молниеносный поиск по названию и артикулу по всем загруженным базам, поддержка вставки списков артикулов из Excel.<br>"
            "• <b>Защита от дубликатов:</b> при добавлении товара, который уже есть в заявке, программа не создает новую строку, а увеличивает количество.<br>"
            "• <b>Свои прайсы:</b> добавление собственных прайс-листов по прямой ссылке (URL) или из локального файла.<br>"
            "• <b>Источник товара:</b> в заявке отображается колонка «Прайс-лист», показывающая, из какой базы взят товар (или «= Своё =», если его нет в прайсах).<br>"
            "• <b>Гибкая заявка:</b> изменение количества через удобное всплывающее окно, перетаскивание строк мышкой. Защита от случайного изменения артикулов и названий товаров из прайс-листов.<br>"
            "• <b>Копирование в один клик:</b> клик по артикулу или наименованию мгновенно копирует текст, подсвечивает ячейку зеленым и показывает всплывающее уведомление.<br>"
            "• <b>Справочник назначений:</b> древовидная структура с сортировкой по алфавиту. Текущее назначение подсвечивается при открытии. При переименовании или удалении назначения изменения мгновенно применяются ко всем сохраненным отчетам.<br>"
            "• <b>Мгновенный поиск в отчётах:</b> поиск по базе сохраненных заявок работает сразу при вводе текста. Доступен фильтр по диапазону дат.<br>"
            "• <b>Умные отчёты:</b> сохранение полной информации (ФИО, телефон, email, месяц, статус). Возможность редактировать шапку, состав товаров и объединять несколько отчётов в сводную ведомость.<br>"
            "• <b>Настройка Excel:</b> выбор конкретных колонок и шапки для выгрузки в файл.<br>"
            "• <b>Сохранение состояния:</b> незакрытая заявка (черновик) и состояние редактирования отчёта автоматически сохраняются при выходе и восстанавливаются при запуске.<br>"
            "• <b>Безопасность:</b> пароли на вход и в админ-панель хранятся в виде криптографических хешей (PBKDF2). Запрещен запуск двух копий одновременно.<br>"
            "• <b>Автообновление:</b> программа сама проверяет наличие новых версий в сетевой папке и предлагает обновиться в один клик.<br>"
            "• <b>Темы оформления:</b> 3 встроенные темы и полностью настраиваемая «Своя тема».<br>"
            "• <b>Сетевая работа:</b> в «Настройках» можно указать путь к общей базе данных для работы в команде."
        )
        features_text.setWordWrap(True)
        features_text.setStyleSheet("font-size: 14px; line-height: 150%;")
        features_text.setTextFormat(Qt.RichText)

        # --- Принцип работы ---
        workflow_title = QLabel('<span style="color: #0078D7; font-size: 16px; margin-top: 10px;"><b>Принцип работы:</b></span>')
        workflow_title.setTextFormat(Qt.RichText)

        workflow_text = QLabel(
            "<b>0. Запуск:</b> введите пароль для доступа к программе.<br>"
            "<b>1. Прайсы:</b> настройте источники (включая свои) и нажмите «Загрузка» для получения актуальных цен.<br>"
            "<b>2. Поиск:</b> введите название или артикул, отметьте нужные галочками и нажмите «Добавить отмеченные».<br>"
            "<b>3. Заявка:</b> проверьте список. Кликните по количеству, чтобы изменить его. Выберите «Назначение» кликом по соответствующей ячейке. Для копирования артикула или названия просто кликните по ним.<br>"
            "<b>4. Отчёт:</b> нажмите «Создать отчёт». Заполните данные по организации, статус и контакты. Заявка сохранится в базу и появится на вкладке «Отчёты»."
        )
        workflow_text.setWordWrap(True)
        workflow_text.setStyleSheet("font-size: 14px; line-height: 150%;")
        workflow_text.setTextFormat(Qt.RichText)

        # --- Футер и кнопка ---
        footer = QLabel(
            f"Разработчик: {DEVELOPER}\n"
            f"© {YEAR} {AUTHOR}\n"
            "Все права защищены."
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 12px; margin-top: 20px;")

        btn_repo = QPushButton("Перейти в репозиторий (GitHub)")
        btn_repo.setStyleSheet("""
            QPushButton { background-color: #24292e; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; font-size: 14px; }
            QPushButton:hover { background-color: #1b1f23; }
            QPushButton:pressed { background-color: #0d1117; }
        """)
        btn_repo.setCursor(Qt.PointingHandCursor)
        btn_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))

        # Собираем всё вместе
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(btn_control_layout)
        layout.addWidget(desc)
        layout.addWidget(features_title)
        layout.addWidget(features_text)
        layout.addWidget(workflow_title)
        layout.addWidget(workflow_text)
        layout.addStretch()
        layout.addWidget(btn_repo, 0, Qt.AlignHCenter)
        layout.addWidget(footer)

        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def show_changelog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("История обновлений")
        dialog.resize(650, 500)
        dialog.setStyleSheet("QDialog { background-color: #f5f5f5; }")

        layout = QVBoxLayout(dialog)
        
        browser = QTextBrowser()
        browser.setStyleSheet("""
            QTextBrowser { 
                background-color: white; 
                color: black; 
                font-size: 14px; 
                border: 1px solid #ccc; 
                padding: 15px; 
            }
        """)
        
        # 1. Ищем в сетевой папке (рядом с базой)
        update_dir = os.path.dirname(self.main_app.db_path)
        json_path = os.path.join(update_dir, "version.json")
        
        # 2. Если нет - ищем локально рядом с exe
        if not os.path.exists(json_path):
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "version.json")
            
        # 3. Если нет - ищем внутри ресурсов программы (если встроили)
        if not os.path.exists(json_path):
            asset_dir = getattr(sys, '_MEIPASS', None)
            if asset_dir:
                json_path = os.path.join(asset_dir, "version.json")
        
        html = "<h2 style='color: #0078D7; text-align: center;'>История обновлений</h2><br>"
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Получаем историю (если она есть) или делаем из старого формата
                history = data.get("history", [])
                if not history and "latest_version" in data:
                    history.append({
                        "version": data["latest_version"],
                        "date": "Последнее обновление",
                        "notes": data.get("release_notes", "")
                    })
                    
                for item in history:
                    ver = item.get("version", "0.0.0")
                    date = item.get("date", "Без даты")
                    notes = item.get("notes", "Информация отсутствует.")
                    
                    # Форматируем текст
                    notes_html = notes.replace("\n", "<br>")
                    
                    html += f"<h3 style='color: #0078D7; margin-bottom: 5px;'>Версия {ver} <span style='color: gray; font-size: 12px; font-weight: normal;'>({date})</span></h3>"
                    html += f"<p style='line-height: 150%; margin-top: 0;'>{notes_html}</p>"
                    html += "<hr style='border: 1px solid #eee; margin-bottom: 15px;'>"
                    
            except Exception as e:
                html += f"<p style='color: red;'>Ошибка чтения файла обновлений: {e}</p>"
        else:
            html += "<p style='text-align: center;'>Файл <b>version.json</b> не найден.</p>"
            html += f"<p style='text-align: center; color: gray;'>Проверенный путь:<br>{json_path}</p>"
            
        browser.setHtml(html)
        layout.addWidget(browser)
        
        btn_close = QPushButton("Закрыть")
        btn_close.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:pressed { background-color: #004578; }
        """)
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close, 0, Qt.AlignCenter)
        
        dialog.exec()

    def force_check_update(self):
        self.btn_force_update.setText("Проверка...")
        self.btn_force_update.setEnabled(False)
        
        update_dir = os.path.dirname(self.main_app.db_path)
        self.update_checker = UpdateChecker(__version__, update_dir)
        
        self.update_checker.no_updates.connect(self.on_no_updates)
        self.update_checker.error_occurred.connect(self.on_update_error)
        self.update_checker.update_found.connect(self.on_update_found)
        
        self.update_checker.start()
        
    def reset_update_button(self):
        self.btn_force_update.setText("Проверить обновления")
        self.btn_force_update.setEnabled(True)

    def on_no_updates(self):
        self.reset_update_button()
        show_message(self, "Обновления", "У вас установлена последняя версия программы.")
        
    def on_update_error(self, err):
        self.reset_update_button()
        show_message(self, "Ошибка", err, is_error=True)
        
    def on_update_found(self, update_data):
        self.reset_update_button()
        latest = update_data.get("latest_version")
        notes = update_data.get("release_notes", "")
        url = update_data.get("download_url", "")
        
        msg = f"Доступна новая версия: {latest}\n\nЧто нового:\n{notes}\n\nОбновить сейчас?"
        if show_confirm(self, "Доступно обновление", msg):
            self.main_app.perform_update(url)