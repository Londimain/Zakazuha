# screens/about_screen.py
import os
from utils import show_message, show_confirm
from modules.updater import UpdateChecker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton
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
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(f"Версия: {__version__}")
        subtitle.setStyleSheet("font-size: 16px; color: gray;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        # --- Кнопка обновления ---
        self.btn_force_update = QPushButton("Проверить обновления")
        self.btn_force_update.setStyleSheet(
            "background-color: #0078D7; color: white; font-weight: bold; "
            "padding: 6px 15px; border-radius: 6px; font-size: 13px;"
        )
        self.btn_force_update.setCursor(Qt.PointingHandCursor)
        self.btn_force_update.clicked.connect(self.force_check_update)

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
        features_title = QLabel("<b>Основные возможности:</b>")
        features_title.setStyleSheet("font-size: 16px;")

        features_text = QLabel(
            "• <b>Умный поиск:</b> молниеносный поиск по названию и артикулу по всем загруженным базам, поддержка вставки списков артикулов из Excel.<br>"
            "• <b>Свои прайсы:</b> добавление собственных прайс-листов по прямой ссылке (URL) или из локального файла. Защищено паролем.<br>"
            "• <b>Гибкая заявка:</b> ручное редактирование количества, перетаскивание строк мышкой, умная защита от перезаписи данных при редактировании отчётов.<br>"
            "• <b>Настройка Excel:</b> выбор конкретных колонок и шапки для выгрузки в файл.<br>"
            "• <b>Черновик:</b> незакрытая заявка автоматически сохраняется при выходе, а состояние редактирования отчёта не теряется после перезапуска.<br>"
            "• <b>База отчётов:</b> все созданные заявки хранятся в базе данных. Их можно просматривать, дополнять товарами, удалять (по паролю) и объединять в сводные ведомости.<br>"
            "• <b>Автообновление:</b> программа сама проверяет наличие новых версий в сетевой папке и предлагает обновиться в один клик.<br>"
            "• <b>Безопасность:</b> вход в программу защищён паролем, а также запрещён запуск двух копий одновременно.<br>"
            "• <b>Темы оформления:</b> 3 встроенные темы и полностью настраиваемая «Своя тема».<br>"
            "• <b>Сетевая работа:</b> в «Настройках» можно указать путь к общей базе данных для работы в команде (с проверкой целостности файла)."
        )
        features_text.setWordWrap(True)
        features_text.setStyleSheet("font-size: 14px; line-height: 150%;")

        # --- Принцип работы ---
        workflow_title = QLabel("<b>Принцип работы:</b>")
        workflow_title.setStyleSheet("font-size: 16px; margin-top: 10px;")

        workflow_text = QLabel(
            "0. <b>Запуск:</b> введите пароль для доступа к программе.<br>"
            "1. <b>Прайсы:</b> настройте источники (включая свои) и нажмите «Обн.» для загрузки актуальных цен.<br>"
            "2. <b>Поиск:</b> введите название или артикул, выберите нужное галочками и нажмите «Добавить отмеченные».<br>"
            "3. <b>Заявка:</b> измените количество, перетащите строки для сортировки или удалите лишнее.<br>"
            "4. <b>Отчёт:</b> нажмите «Создать отчёт». Заявка сохранится в базу. При необходимости её можно открыть для редактирования на вкладке «Отчёты»."
        )
        workflow_text.setWordWrap(True)
        workflow_text.setStyleSheet("font-size: 14px; line-height: 150%;")

        # --- Футер и кнопка ---
        footer = QLabel(
            f"Разработчик: {DEVELOPER}\n"
            f"© {YEAR} {AUTHOR}\n"
            "Все права защищены."
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 12px; margin-top: 20px;")

        btn_repo = QPushButton("Перейти в репозиторий (GitHub)")
        btn_repo.setStyleSheet(
            "background-color: #24292e; color: white; font-weight: bold; "
            "padding: 10px 20px; border-radius: 6px; font-size: 14px;"
        )
        btn_repo.setCursor(Qt.PointingHandCursor)
        btn_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))

        # Собираем всё вместе
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.btn_force_update, 0, Qt.AlignHCenter)
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
        
    def force_check_update(self):
        # Блокируем кнопку и меняем текст на время проверки
        self.btn_force_update.setText("Проверка...")
        self.btn_force_update.setEnabled(False)
        
        update_dir = os.path.dirname(self.main_app.db_path)
        self.update_checker = UpdateChecker(__version__, update_dir)
        
        self.update_checker.no_updates.connect(self.on_no_updates)
        self.update_checker.error_occurred.connect(self.on_update_error)
        self.update_checker.update_found.connect(self.on_update_found)
        
        self.update_checker.start()
        
    def reset_update_button(self):
        # Возвращаем кнопку в исходное состояние
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
            # Вызываем метод скачивания из главного окна
            self.main_app.perform_update(url)