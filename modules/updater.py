# modules/updater.py
import os
import json
import shutil
import requests
from PySide6.QtCore import QThread, Signal

def parse_version(v_str):
    try:
        return tuple(map(int, v_str.split('.')))
    except Exception:
        return (0, 0, 0)

class UpdateChecker(QThread):
    update_found = Signal(dict)
    no_updates = Signal()
    error_occurred = Signal(str)

    def __init__(self, current_version, update_path):
        super().__init__()
        self.current_version = current_version
        self.update_path = update_path

    def run(self):
        if not self.update_path or not os.path.exists(self.update_path):
            self.error_occurred.emit("Папка обновлений недоступна.")
            return
        
        json_path = os.path.join(self.update_path, "version.json")
        if not os.path.exists(json_path):
            self.error_occurred.emit("Файл version.json не найден.")
            return
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            latest = data.get("latest_version", "0.0.0")
            
            if parse_version(latest) > parse_version(self.current_version):
                self.update_found.emit(data)
            else:
                self.no_updates.emit()
        except Exception as e:
            self.error_occurred.emit(f"Ошибка чтения version.json: {e}")

def download_installer(url, dest_dir):
    filename = os.path.basename(url)
    filepath = os.path.join(dest_dir, filename)
    
    if url.startswith("http://") or url.startswith("https://"):
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    else:
        # Локальный или сетевой путь
        if not os.path.exists(url):
            raise Exception(f"Файл установщика не найден:\n{url}")
        shutil.copy2(url, filepath)
        
    return filepath