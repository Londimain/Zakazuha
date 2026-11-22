# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ico/app.ico', 'ico')],
    hiddenimports=['openpyxl', 'xlrd', 'chardet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'PyQt5', 'PyQt6', 'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'scipy', 'IPython', 'jupyter', 'notebook', 'pytest', 'setuptools',
        'pytz', 'PySide6.QtWebEngineCore',
        'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.Qt3DCore',
        'PySide6.QtCharts', 'PySide6.QtMultimedia', 'PySide6.QtPdf',
        'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner',
        'PySide6.QtBluetooth', 'PySide6.QtPositioning', 'PySide6.QtSensors',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Zakazuha',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='ico/app.ico',
)
