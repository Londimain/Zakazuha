# Активировать скрипт при создании проекта на другом устройстве
# Запуск: 
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# \setup_env.ps1

# setup_env.ps1
python -m venv venv
.\venv\Scripts\Activate.ps1

Write-Host "Проверка окружения:"
where.exe pip
python -c "import sys; print(sys.prefix)"

python -m pip install --upgrade pip setuptools
pip install -r requirements.txt

Write-Host "Проверка импортов:"
python -c "import kivy, kivymd, pandas, openpyxl, xlrd, requests; print('OK')"

Write-Host "Готово. Запуск: python main.py"