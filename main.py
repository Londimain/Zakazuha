# main.py
import ctypes
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Ilyenkov.PriceOrder.1")
except Exception:
    pass
import sys
import os
import json
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QLabel, QWidget, QSizePolicy
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, QTimer
from PySide6.QtNetwork import QLocalSocket, QLocalServer

from version import APP_NAME, __version__
from modules.price_manager import PriceManager
from modules.search_engine import SearchEngine
from modules.order_manager import OrderManager
from modules.report_manager import ReportManager

from screens.search_screen import SearchScreen
from screens.order_screen import OrderScreen
from screens.report_screen import ReportScreen
from screens.update_screen import UpdateScreen
from screens.settings_screen import SettingsScreen
from screens.about_screen import AboutScreen
from utils import show_confirm, ask_password, show_message
import tempfile
from modules.updater import UpdateChecker, download_installer

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    ASSET_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSET_DIR = BASE_DIR

DEFAULT_DB_PATH = os.path.join(BASE_DIR, "cache.db")
USER_DATA_DIR = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), APP_NAME)
LOCAL_PRICES_DIR = os.path.join(USER_DATA_DIR, "prices")
os.makedirs(USER_DATA_DIR, exist_ok=True)

DEFAULT_CUSTOM_THEME = {
    "bg":          "#e9ecef",
    "text":        "#000000",
    "button_bg":   "#e0e0e0",
    "button_text": "#000000",
    "table_bg":    "#ffffff",
    "header_bg":   "#dee2e6",
    "input_bg":    "#ffffff",
}


def create_desktop_shortcut():
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
                desktop = winreg.QueryValueEx(key, "Desktop")[0]
            except Exception:
                return

        folder = os.path.join(desktop, "Отчёты заказа")
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        ico_path = os.path.join(ASSET_DIR, "ico", "app.ico")
        if os.path.exists(ico_path):
            ini_path = os.path.join(folder, "desktop.ini")

            if os.path.exists(ini_path):
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(ini_path, 0x80)
                except Exception:
                    pass

            try:
                with open(ini_path, "w", encoding="utf-16") as f:
                    f.write("[.ShellClassInfo]\n")
                    f.write(f"IconResource={ico_path},0\n")

                ctypes.windll.kernel32.SetFileAttributesW(ini_path, 0x02 | 0x01)
                ctypes.windll.kernel32.SetFileAttributesW(folder, 0x04)
            except PermissionError:
                pass
            except Exception as e:
                print(f"Не удалось применить иконку папки: {e}")
    except Exception as e:
        print(f"Ошибка при проверке папки на рабочем столе: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.resize(1200, 800)
        self.is_updating = False

        self.data_dir = USER_DATA_DIR
        self.draft_path = os.path.join(self.data_dir, "draft.json")
        self.config_path = os.path.join(self.data_dir, "config.json")
        self.editing_order_path = os.path.join(self.data_dir, "editing_order.json")

        self.export_config = self.load_config()
        
        # Инициализация БД
        self.db_path = self.export_config.get("db_path", "")
        if not self.db_path:
            self.db_path = DEFAULT_DB_PATH

        self.price_manager = PriceManager(db_path=self.db_path, prices_dir=LOCAL_PRICES_DIR)
        self.search_engine = SearchEngine(self.price_manager.db_path)
        self.order_manager = OrderManager()
        self.report_manager = ReportManager(self.price_manager.db_path)

        try:
            self.order_manager.load_draft(self.draft_path)
        except Exception as e:
            print(f"Ошибка загрузки черновика: {e}")
            self.order_manager.items = []

        # Восстанавливаем состояние редактирования отчёта (если было)
        self.editing_order = None
        if os.path.exists(self.editing_order_path):
            try:
                with open(self.editing_order_path, 'r', encoding='utf-8') as f:
                    eo = json.load(f)
                if eo and eo.get("id") and self.report_manager.order_exists(eo["id"]):
                    self.editing_order = eo
                else:
                    try:
                        os.remove(self.editing_order_path)
                    except OSError:
                        pass
            except Exception as e:
                print(f"Ошибка загрузки состояния редактирования: {e}")

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.search_scr = SearchScreen(self)
        self.order_scr = OrderScreen(self)
        self.report_scr = ReportScreen(self)
        self.update_scr = UpdateScreen(self)
        self.settings_scr = SettingsScreen(self)
        self.about_scr = AboutScreen(self)

        self.tabs.addTab(self.search_scr, "Поиск")
        self.tabs.addTab(self.order_scr, "Заявка")
        self.tabs.addTab(self.report_scr, "Отчёты")
        self.tabs.addTab(self.update_scr, "Прайсы")
        self.tabs.addTab(self.settings_scr, "Настройки")
        self.tabs.addTab(self.about_scr, "О программе")

        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.apply_theme(self.export_config.get("theme", "Светлая"), save=False)
        self.update_order_badge()

        # Статус-бар для индикации БД
        self.statusBar().show()
        self.statusBar().setStyleSheet("QStatusBar::item { border: none; }")  # убирает лишнюю линию
        self.db_status_label = QLabel()
        self.statusBar().addPermanentWidget(self.db_status_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.statusBar().addPermanentWidget(spacer, 1)

        self.update_db_status()
        # Запускаем проверку обновлений через 1.5 секунды после загрузки интерфейса
        QTimer.singleShot(1500, self.check_updates_startup)

    def check_updates_startup(self):
        # Берем папку, где лежит база данных
        update_dir = os.path.dirname(self.db_path)
        self.update_checker = UpdateChecker(__version__, update_dir)
        self.update_checker.update_found.connect(self.show_update_prompt)
        # При автопроверке не показываем ошибки, если папка локальная и нет version.json
        self.update_checker.start()

    def show_update_prompt(self, update_data):
        latest = update_data.get("latest_version")
        notes = update_data.get("release_notes", "")
        url = update_data.get("download_url", "")
        
        msg = f"Доступна новая версия программы: {latest}\n\nЧто нового:\n{notes}\n\nОбновить сейчас? (Программа закроется для установки)"
        if show_confirm(self, "Доступно обновление", msg):
            self.perform_update(url)

    def perform_update(self, url):
        try:
            if not url.startswith("http") and not os.path.isabs(url):
                url = os.path.join(os.path.dirname(self.db_path), url)
                
            temp_dir = tempfile.gettempdir()
            local_file = download_installer(url, temp_dir)
            
            show_message(self, "Обновление", "Установщик успешно скачан. Программа будет закрыта для установки.")
            
            self.is_updating = True  # <--- Сообщаем программе, что мы обновляемся
            os.startfile(local_file)
            QApplication.instance().quit()
        except Exception as e:
            show_message(self, "Ошибка", f"Не удалось скачать обновление:\n{e}", is_error=True)

    def update_db_status(self):
        if os.path.abspath(self.db_path) == os.path.abspath(DEFAULT_DB_PATH):
            status, color = "Локальная", "#ff6b6b"   # ярко-красный
        else:
            status, color = "Сетевая", "#2ecc71"     # ярко-зелёный

        # Используем HTML-теги для раскрашивания разных частей текста
        rich_text = f'<span style="color: #ffffff;">База данных:</span> <span style="color: {color}; font-weight: bold;">{status}</span>'
        
        self.db_status_label.setText(rich_text)
        self.db_status_label.setTextFormat(Qt.RichText) # Включаем поддержку HTML
        
        self.db_status_label.setStyleSheet(f"""
            QLabel {{
                background-color: #000000;
                font-weight: bold;
                padding: 3px 14px;
                border: 2px solid {color};
                border-radius: 10px;
                margin: 0 0 6px 12px;
            }}
        """)

    def switch_db(self, new_path):
        if not new_path:
            new_path = DEFAULT_DB_PATH
            
        new_path = os.path.normpath(new_path)

        # Если путь не совпадает с локальной базой по умолчанию, требуем, чтобы файл существовал
        if new_path != os.path.normpath(DEFAULT_DB_PATH):
            if os.path.isdir(new_path):
                show_message(self, "Ошибка", f"Вы указали папку, а не файл базы данных:\n{new_path}\n\nПожалуйста, выберите сам файл (обычно он называется cache.db).", is_error=True)
                return False
            if not os.path.exists(new_path):
                show_message(self, "Ошибка", f"Файл базы данных не найден:\n{new_path}\n\nУбедитесь, что путь к сетевой базе указан верно.", is_error=True)
                return False

        try:
            # ПЫТАЕМСЯ подключиться к новой базе (до сохранения настроек)
            test_price_manager = PriceManager(db_path=new_path, prices_dir=LOCAL_PRICES_DIR)
            test_search_engine = SearchEngine(test_price_manager.db_path)
            test_report_manager = ReportManager(test_price_manager.db_path)
        except Exception as e:
            show_message(self, "Ошибка", f"Не удалось открыть базу данных:\n{new_path}\n\nПричина: {e}", is_error=True)
            return False

        # Если ошибок нет - применяем изменения
        self.db_path = new_path
        self.export_config["db_path"] = new_path if new_path != DEFAULT_DB_PATH else ""
        self.save_config()

        self.editing_order = None
        self.save_editing_order_state()

        self.price_manager = test_price_manager
        self.search_engine = test_search_engine
        self.report_manager = test_report_manager

        self.update_db_status()
        
        self.search_scr.refresh_sources()
        self.report_scr.refresh()
        self.update_scr.refresh_info()
        
        return True

    def update_order_badge(self):
        count = len(self.order_manager.items)
        if count > 0:
            self.tabs.setTabText(1, f"Заявка ({count})")
        else:
            self.tabs.setTabText(1, "Заявка")

    def load_config(self):
        default = {
            "num": True, "article": True, "name": True, "price": True,
            "qty": True, "pack": True, "unit": True, "gtin": True, "source": True,
            "org": True, "contact": True, "fio": True, "cat": True, "note": True,
            "sources": ["TDM", "TDM_img", "IEK", "IEK_svet"],
            "theme": "Светлая",
            "custom_theme": dict(DEFAULT_CUSTOM_THEME),
            "db_path": "",
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
        return default

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.export_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            
    def save_editing_order_state(self):
        try:
            if self.editing_order:
                with open(self.editing_order_path, 'w', encoding='utf-8') as f:
                    json.dump(self.editing_order, f, ensure_ascii=False, indent=4)
            else:
                if os.path.exists(self.editing_order_path):
                    os.remove(self.editing_order_path)
        except Exception as e:
            print(f"Ошибка сохранения состояния редактирования: {e}")

    def on_tab_changed(self, index):
        if self.tabs.widget(index) == self.search_scr:
            self.search_scr.refresh_sources()
        elif self.tabs.widget(index) == self.order_scr:
            self.order_scr.refresh()
        elif self.tabs.widget(index) == self.report_scr:
            self.report_scr.refresh()

    def closeEvent(self, event):
        # Если это автообновление - закрываемся без лишних вопросов
        if self.is_updating:
            self.order_manager.save_draft(self.draft_path)
            self.save_editing_order_state()
            self.save_config()
            event.accept()
            return

        # Обычное закрытие
        if show_confirm(self, "Выход", "Вы уверены, что хотите закрыть программу?\nНесохраненные данные останутся в черновике."):
            self.order_manager.save_draft(self.draft_path)
            self.save_editing_order_state()
            self.save_config()
            event.accept()
        else:
            event.ignore()

    def apply_theme(self, theme_name, save=True):
        base_font = ""
        checkbox_style = """
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid #777777;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #0078D7;
                border: 1px solid #0078D7;
            }
        """
        msgbox_style = """
            QMessageBox { background-color: #f0f0f0; }
            QMessageBox QLabel { color: black; font-size: 14px; }
            QMessageBox QPushButton {
                min-width: 100px; min-height: 35px;
                font-size: 14px; font-weight: bold;
                background-color: #e0e0e0; color: black; border: 1px solid #999; border-radius: 4px;
            }
            QMessageBox QPushButton:hover { background-color: #d0d0d0; }
        """
        group_style = """
            QGroupBox { font-weight: bold; margin-top: 25px; padding-top: 15px; border-radius: 5px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """
        border_style = """
            QTableWidget, QTreeWidget {
                border: 1px solid #999999;
                gridline-color: #999999;
            }
            QTreeWidget::item {
                border-right: 1px solid #999999;
                border-bottom: 1px solid #999999;
            }
            QHeaderView::section {
                border: 1px solid #999999;
                border-top: none;
                border-left: none;
            }
        """

        if theme_name == "Светлая":
            self.setStyleSheet(base_font + checkbox_style + msgbox_style + group_style + border_style + """
                QWidget { background-color: #e9ecef; color: black; }
                QTableWidget, QTreeWidget { background-color: #ffffff; alternate-background-color: #f1f3f5; }
                QTableWidget::item:selected { background-color: #b3d9ff; color: black; }
                QHeaderView::section { background-color: #dee2e6; padding: 4px; font-weight: bold; }
                QLineEdit { background-color: white; border: 1px solid #ccc; padding: 4px; }
                QLineEdit:hover { border: 1px solid #aaa; }
                QPushButton { background-color: #e0e0e0; color: black; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold;}
                QPushButton:hover { background-color: #d0d0d0; }
                QPushButton:pressed { background-color: #b0b0b0; }
                QComboBox { background-color: white; border: 1px solid #ccc; padding: 4px; }
                QGroupBox { border: 1px solid #ccc; }
            """)
            
        elif theme_name == "Тёмная":
            self.setStyleSheet(base_font + checkbox_style + group_style + border_style + """
                QWidget { background-color: #2b2b2b; color: #ffffff; }
                QTableWidget, QTreeWidget { background-color: #333333; alternate-background-color: #3c3c3c; gridline-color: #555; }
                QTableWidget::item:selected { background-color: #4a6a8a; color: white; }
                QTreeWidget::item { border-right: 1px solid #555555; border-bottom: 1px solid #555555; }
                QHeaderView::section { background-color: #444444; color: white; padding: 4px; font-weight: bold; }
                QLineEdit { background-color: #444444; color: white; border: 1px solid #555; padding: 4px; }
                QLineEdit:hover { border: 1px solid #777; }
                QPushButton { background-color: #e0e0e0; color: black; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold;}
                QPushButton:hover { background-color: #d0d0d0; }
                QPushButton:pressed { background-color: #b0b0b0; }
                QComboBox { background-color: #444444; color: white; border: 1px solid #555; }
                QGroupBox { border: 1px solid #555; }
                QMessageBox { background-color: #2b2b2b; }
                QMessageBox QLabel { color: white; font-size: 14px; }
            """)
            
        elif theme_name == "Синяя":
            self.setStyleSheet(base_font + checkbox_style + msgbox_style + group_style + border_style + """
                QWidget { background-color: #d0e3f5; color: #002244; }
                QTableWidget, QTreeWidget { background-color: #ffffff; alternate-background-color: #e2eef9; }
                QTableWidget::item:selected { background-color: #99bbdd; color: black; }
                QHeaderView::section { background-color: #b3d4f0; padding: 4px; font-weight: bold; }
                QLineEdit { background-color: white; border: 1px solid #99bbdd; padding: 4px; }
                QLineEdit:hover { border: 1px solid #7aaadd; }
                QPushButton { background-color: #e0e0e0; color: black; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold;}
                QPushButton:hover { background-color: #d0d0d0; }
                QPushButton:pressed { background-color: #b0b0b0; }
                QComboBox { background-color: white; border: 1px solid #99bbdd; padding: 4px; }
                QGroupBox { border: 1px solid #99bbdd; }
            """)

        elif theme_name == "Своя тема":
            ct = dict(DEFAULT_CUSTOM_THEME)
            ct.update(self.export_config.get("custom_theme", {}))
            bg = ct.get("bg", "#e9ecef")
            text = ct.get("text", "#000000")
            button_bg = ct.get("button_bg", "#e0e0e0")
            button_text = ct.get("button_text", "#000000")
            table_bg = ct.get("table_bg", "#ffffff")
            header_bg = ct.get("header_bg", "#dee2e6")
            input_bg = ct.get("input_bg", "#ffffff")

            self.setStyleSheet(base_font + checkbox_style + msgbox_style + group_style + border_style + f"""
                QWidget {{ background-color: {bg}; color: {text}; }}
                QTableWidget, QTreeWidget {{ background-color: {table_bg}; alternate-background-color: {bg}; }}
                QTableWidget::item:selected {{ background-color: {header_bg}; color: {text}; }}
                QTreeWidget::item {{ border-right: 1px solid #999999; border-bottom: 1px solid #999999; }}
                QHeaderView::section {{ background-color: {header_bg}; padding: 4px; font-weight: bold; color: {text}; }}
                QLineEdit {{ background-color: {input_bg}; color: {text}; border: 1px solid #ccc; padding: 4px; }}
                QLineEdit:hover {{ border: 1px solid {button_bg}; }}
                QPushButton {{ background-color: {button_bg}; color: {button_text}; border: 1px solid #999; padding: 6px; border-radius: 4px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {header_bg}; }}
                QPushButton:pressed {{ background-color: {header_bg}; border: 2px solid #555; }}
                QComboBox {{ background-color: {input_bg}; color: {text}; border: 1px solid #ccc; padding: 4px; }}
                QGroupBox {{ border: 1px solid #ccc; }}
            """)

        self.export_config["theme"] = theme_name
        if save:
            self.save_config()

if __name__ == "__main__":
    # 1. Создаем приложение (обязательно ДО создания любых Qt-объектов)
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 11))

    app_icon = QIcon(os.path.join(ASSET_DIR, "ico", "app.ico"))
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    else:
        print("Иконка не найдена:", os.path.join(ASSET_DIR, "ico", "app.ico"))

    # 2. Проверка на повторный запуск
    server_name = "PriceOrder_SingleInstance_Lock"
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    
    if socket.waitForConnected(500):
        # Если программа уже запущена — отправляем ей сигнал "Покажись" и выходим
        socket.write(b"SHOW_WINDOW")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        sys.exit(0)
    else:
        # Если не запущена — создаем сервер для приема будущих сигналов
        server = QLocalServer()
        server.removeServer(server_name) # Очистка после аварийного закрытия
        server.listen(server_name)

    # 3. Проверка пароля (только для первого запуска)
    pwd = ask_password(None, "Вход в программу", "Введите пароль для доступа:")
    
    if pwd != "1111":
        if pwd is not None: # Если не нажато "Отмена"
            show_message(None, "Доступ запрещён", "Неверный пароль!", is_error=True)
        sys.exit(0)

    # 4. Запуск основного окна
    create_desktop_shortcut()

    window = MainWindow()

    # 5. Функция для обработки сигнала от второго экземпляра
    def handle_new_connection():
        new_sock = server.nextPendingConnection()
        if new_sock:
            new_sock.waitForReadyRead(1000)
            msg = new_sock.readAll().data()
            if msg == b"SHOW_WINDOW":
                # Разворачиваем окно, если оно было свернуто
                if window.isMinimized():
                    window.showNormal()
                # Выводим на передний план
                window.activateWindow()
                window.raise_()
            new_sock.disconnectFromServer()

    # Подключаем обработчик
    server.newConnection.connect(handle_new_connection)

    window.showMaximized()
    sys.exit(app.exec())