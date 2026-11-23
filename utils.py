# utils.py
import hashlib
import os
import binascii
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QStyle, QLineEdit, QColorDialog, QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

def show_message(parent, title, text, is_error=False):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(400)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    
    dialog.setStyleSheet("""
        QDialog { background-color: #f5f5f5; }
        QLabel { color: black; font-size: 14px; border: none; background: transparent; }
        QPushButton { 
            background-color: #0078D7; color: white; font-weight: bold; 
            border-radius: 4px; border: none; padding: 5px 15px;
        }
        QPushButton:hover { background-color: #005a9e; }
    """)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(20)
    layout.setContentsMargins(25, 25, 25, 25)

    h_layout = QHBoxLayout()
    icon_label = QLabel()
    icon_enum = QStyle.SP_MessageBoxWarning if is_error else QStyle.SP_MessageBoxInformation
    
    icon = parent.style().standardIcon(icon_enum)
    icon_label.setPixmap(icon.pixmap(40, 40))
    icon_label.setAlignment(Qt.AlignCenter)

    text_label = QLabel(text)
    text_label.setWordWrap(True)
    text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    h_layout.addWidget(icon_label, 0, Qt.AlignTop)
    h_layout.addWidget(text_label, 1)
    layout.addLayout(h_layout)

    btn_ok = QPushButton("ОК")
    btn_ok.setFixedSize(100, 32)
    btn_ok.clicked.connect(dialog.accept)
    layout.addWidget(btn_ok, 0, Qt.AlignHCenter)
    
    dialog.exec()

def show_confirm(parent, title, text):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(450) # <--- ИЗМЕНЕНО С 650 НА 450
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    
    dialog.setStyleSheet("""
        QDialog { background-color: #f5f5f5; }
        QLabel { color: black; font-size: 14px; border: none; background: transparent; }
        QPushButton { font-weight: bold; border-radius: 4px; border: none; padding: 5px 15px; }
        QPushButton#btn_yes { background-color: #d9534f; color: white; }
        QPushButton#btn_yes:hover { background-color: #c9302c; }
        QPushButton#btn_no { background-color: #0078D7; color: white; }
        QPushButton#btn_no:hover { background-color: #005a9e; }
    """)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(20)
    layout.setContentsMargins(25, 25, 25, 25)

    h_layout = QHBoxLayout()
    icon_label = QLabel()
    icon = parent.style().standardIcon(QStyle.SP_MessageBoxQuestion)
    icon_label.setPixmap(icon.pixmap(40, 40))
    icon_label.setAlignment(Qt.AlignCenter)

    text_label = QLabel(text)
    text_label.setWordWrap(True)
    text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    h_layout.addWidget(icon_label, 0, Qt.AlignTop)
    h_layout.addWidget(text_label, 1)
    layout.addLayout(h_layout)

    btn_layout = QHBoxLayout()
    btn_yes = QPushButton("Да")
    btn_yes.setObjectName("btn_yes")
    btn_yes.setFixedSize(100, 32)
    btn_yes.clicked.connect(dialog.accept)
    
    btn_no = QPushButton("Отмена")
    btn_no.setObjectName("btn_no")
    btn_no.setFixedSize(100, 32)
    btn_no.clicked.connect(dialog.reject)

    btn_layout.addStretch(1)
    btn_layout.addWidget(btn_yes)
    btn_layout.addWidget(btn_no)
    btn_layout.addStretch(1)
    layout.addLayout(btn_layout)
    
    return dialog.exec() == QDialog.Accepted

def ask_password(parent, title="Пароль", prompt="Введите пароль:"):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(320)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    
    dialog.setStyleSheet("""
        QDialog { background-color: #f5f5f5; }
        QLabel { color: black; font-size: 14px; border: none; background: transparent; }
        QLineEdit { 
            background-color: white; 
            color: black; /* Принудительно делаем текст черным */
            border: 1px solid #ccc; 
            padding: 5px; 
            font-size: 14px; 
        }
        QPushButton { 
            background-color: #0078D7; color: white; font-weight: bold; 
            border-radius: 4px; border: none; padding: 5px 15px; 
        }
        QPushButton:hover { background-color: #005a9e; }
    """)
    
    layout = QVBoxLayout(dialog)
    layout.setSpacing(15)
    layout.setContentsMargins(20, 20, 20, 20)

    lbl = QLabel(prompt)
    inp = QLineEdit()
    inp.setEchoMode(QLineEdit.Password)
    
    # Гарантируем, что поле ввода может принимать фокус
    inp.setFocusPolicy(Qt.StrongFocus) 
    
    layout.addWidget(lbl)
    layout.addWidget(inp)

    btn_layout = QHBoxLayout()
    btn_ok = QPushButton("ОК")
    btn_ok.setFixedSize(90, 30)
    btn_cancel = QPushButton("Отмена")
    btn_cancel.setFixedSize(90, 30)

    btn_layout.addStretch()
    btn_layout.addWidget(btn_ok)
    btn_layout.addWidget(btn_cancel)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    btn_ok.clicked.connect(dialog.accept)
    btn_cancel.clicked.connect(dialog.reject)
    
    # Позволяет нажимать Enter для подтверждения ввода
    btn_ok.setDefault(True) 

    # Принудительно передаем фокус полю ввода при открытии окна
    dialog.setFocusProxy(inp)
    inp.setFocus()
    
    if dialog.exec() != QDialog.Accepted:
        return None
    return inp.text()

def show_input(parent, title, label, default="", echo_password=False):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(400)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    
    dialog.setStyleSheet("""
        QDialog { background-color: #f5f5f5; }
        QLabel { color: black; font-size: 14px; border: none; background: transparent; }
        QLineEdit { 
            background-color: white; 
            color: black; /* Принудительно делаем текст черным */
            border: 1px solid #ccc; 
            padding: 5px; 
            font-size: 14px; 
        }
        QPushButton { 
            background-color: #0078D7; color: white; font-weight: bold; 
            border-radius: 4px; border: none; padding: 5px 15px; 
        }
        QPushButton:hover { background-color: #005a9e; }
        QPushButton#btn_cancel { background-color: #e0e0e0; color: black; border: 1px solid #999; }
        QPushButton#btn_cancel:hover { background-color: #d0d0d0; }
    """)
    
    layout = QVBoxLayout(dialog)
    layout.setSpacing(15)
    layout.setContentsMargins(20, 20, 20, 20)

    lbl = QLabel(label)
    inp = QLineEdit(default)
    
    if echo_password:
        inp.setEchoMode(QLineEdit.Password)
        
    # Гарантируем, что поле ввода может принимать фокус
    inp.setFocusPolicy(Qt.StrongFocus)
    
    layout.addWidget(lbl)
    layout.addWidget(inp)

    btn_layout = QHBoxLayout()
    
    btn_ok = QPushButton("Выполнить")
    btn_ok.setMinimumSize(110, 32) 
    
    btn_cancel = QPushButton("Отмена")
    btn_cancel.setObjectName("btn_cancel")
    btn_cancel.setFixedSize(100, 32)

    btn_layout.addStretch()
    btn_layout.addWidget(btn_ok)
    btn_layout.addWidget(btn_cancel)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    btn_ok.clicked.connect(dialog.accept)
    btn_cancel.clicked.connect(dialog.reject)
    
    # Позволяет нажимать Enter для подтверждения ввода
    btn_ok.setDefault(True)

    # Принудительно передаем фокус полю ввода при открытии окна
    dialog.setFocusProxy(inp)
    inp.setFocus()
    
    if dialog.exec() == QDialog.Accepted:
        return inp.text().strip(), True
    return "", False

def get_custom_color(parent, initial_color=QColor("#ffffff")):
    """Окно выбора цвета с исправленной обрезкой цифр."""
    dialog = QColorDialog(initial_color, parent)
    dialog.setWindowTitle("Выбор цвета")
    dialog.setOption(QColorDialog.DontUseNativeDialog, True)
    dialog.setMinimumWidth(580) # Делаем окно еще шире

    # Стилизуем поля ввода, чтобы цифры не обрезались
    dialog.setStyleSheet("""
        QSpinBox { 
            padding-right: 5px; 
            min-width: 70px; 
            font-size: 13px;
        }
        QLineEdit { 
            min-width: 70px; 
            font-size: 13px;
        }
    """)

    # Находим стандартную панель кнопок и скрываем её
    btn_box = dialog.findChild(QDialogButtonBox)
    if btn_box:
        btn_box.hide()

    # Создаем свои кнопки
    layout = dialog.layout()
    if layout:
        my_btn_layout = QHBoxLayout()
        btn_apply = QPushButton("Применить")
        btn_apply.setFixedSize(110, 32)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setFixedSize(100, 32)

        btn_apply.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)

        my_btn_layout.addStretch()
        my_btn_layout.addWidget(btn_apply)
        my_btn_layout.addWidget(btn_cancel)
        my_btn_layout.addStretch()

        layout.addLayout(my_btn_layout)

    if dialog.exec() == QColorDialog.Accepted:
        return dialog.selectedColor()
    return None

def hash_password(password):
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{binascii.hexlify(salt).decode('utf-8')}${binascii.hexlify(pwd_hash).decode('utf-8')}"

def verify_password(password, stored_hash):
    if not stored_hash or '$' not in stored_hash:
        return False
    salt_hex, hash_hex = stored_hash.split('$')
    salt = binascii.unhexlify(salt_hex.encode('utf-8'))
    test_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return binascii.hexlify(test_hash).decode('utf-8') == hash_hex