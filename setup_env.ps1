# setup_env.ps1
# Создание виртуального окружения и установка зависимостей для проекта "Заказуха".
#
# Запуск (из корня проекта, PowerShell):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup_env.ps1
#
# Требования: Windows, Python 3.10+ в PATH.

$ErrorActionPreference = "Stop"

Write-Host "==> Проверка Python..." -ForegroundColor Cyan
try {
    $pyVersion = python --version 2>&1
    Write-Host "    $pyVersion"
} catch {
    Write-Host "ОШИБКА: Python не найден в PATH. Установите Python 3.10+ и добавьте в PATH." -ForegroundColor Red
    exit 1
}

Write-Host "==> Создание виртуального окружения venv..." -ForegroundColor Cyan
if (Test-Path ".\venv") {
    Write-Host "    Папка venv уже существует, пропускаем создание."
} else {
    python -m venv venv
}

Write-Host "==> Активация venv..." -ForegroundColor Cyan
. .\venv\Scripts\Activate.ps1

Write-Host "==> Обновление pip и setuptools..." -ForegroundColor Cyan
python -m pip install --upgrade pip setuptools wheel

Write-Host "==> Установка зависимостей из requirements.txt..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host "==> Проверка импортов..." -ForegroundColor Cyan
python -c "import PySide6, pandas, openpyxl, xlrd, requests, chardet; print('OK: все ключевые модули импортируются')"

Write-Host ""
Write-Host "Готово." -ForegroundColor Green
Write-Host "Запуск приложения:" -ForegroundColor Green
Write-Host "    python main.py"