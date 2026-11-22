# modules/order_manager.py
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import json
import os

class OrderManager:
    def __init__(self):
        self.items = []

    def add_item(self, row):
        article = str(row[0]) if row[0] else ""
        name = str(row[1]) if row[1] else ""
        source = str(row[6]) if len(row) > 6 and row[6] else ""
        
        # Проверка на дубликат (совпадает артикул и источник)
        if article:
            for item in self.items:
                if item["article"] == article and item["source"] == source:
                    try:
                        current_qty = float(str(item["qty"]).replace(",", "."))
                        item["qty"] = str(int(current_qty + 1))
                    except ValueError:
                        pass
                    return False # Дубликат найден и обработан
                    
        self.items.append({
            "article": article, 
            "name": name, 
            "price": str(row[2]) if row[2] else "",
            "pack": str(row[3]) if row[3] else "", 
            "unit": str(row[4]) if row[4] else "", 
            "gtin": str(row[5]) if row[5] else "",
            "source": source, 
            "qty": "1", "checked": False,
        })
        return True

    def clear(self):
        self.items.clear()

    def save_draft(self, path):
        with open(path, 'w', encoding='utf-8') as f: json.dump(self.items, f, ensure_ascii=False, indent=4)

    def load_draft(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: self.items = json.load(f)

    def _format_excel_val(self, val):
        if val is None: return ""
        s = str(val).strip()
        if s.lower() == "none" or s == "": return ""
        try:
            f = float(s.replace(",", "."))
            if f.is_integer(): return int(f)
            return f
        except ValueError:
            return s

    def _apply_excel_styles(self, ws, header_row, active_keys):
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for cell in ws[header_row]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9E1F2")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
            for idx, key in enumerate(active_keys):
                cell = row[idx]
                cell.border = thin_border
                if key == "name":
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal="center", vertical="top")

        for col_idx, key in enumerate(active_keys):
            col_letter = ws.cell(row=header_row, column=col_idx + 1).column_letter
            max_len = 0
            for cell in ws[col_letter]:
                if cell.value: max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 100) if key == "name" else min(max_len + 2, 40)

    def _write_headers(self, ws, meta, config, active_keys, headers_map):
        header_data = []
        if config.get("org", True): header_data.append(["Организация", meta.get("organization", "")])
        if config.get("contact", True): header_data.append(["Контакт", meta.get("contact", "")])
        if config.get("fio", True): header_data.append(["ФИО", meta.get("fio", "")])
        if config.get("cat", True): header_data.append(["Категория", meta.get("category", "")])
        if config.get("note", True): header_data.append(["Примечание", meta.get("note", "")])
        for h in header_data: ws.append(h)
        ws.append([])

        headers = [headers_map[k] for k in active_keys]
        ws.append(headers)
        return ws.max_row

    def save_to_excel(self, path, meta, items, config=None):
        if not config:
            config = {"num": True, "article": True, "name": True, "price": True, "qty": True, "pack": True, "unit": True, "gtin": True, "source": True, "org": True, "contact": True, "fio": True, "cat": True, "note": True}
        
        headers_map = {"num": "№", "article": "Артикул", "name": "Наименование", "price": "Цена", "qty": "Кол-во", "pack": "Упаковка", "unit": "Ед.", "gtin": "GTIN", "source": "Источник"}
        active_keys = [k for k, v in config.items() if v and k in headers_map]

        wb = Workbook()
        ws = wb.active
        ws.title = "Заявка"
        header_row = self._write_headers(ws, meta, config, active_keys, headers_map)

        for i, item in enumerate(items, 1):
            row_data = []
            for k in active_keys:
                val = item.get(k, "")
                if k == "num":
                    row_data.append(i)
                else:
                    row_data.append(self._format_excel_val(val))
            ws.append(row_data)

        self._apply_excel_styles(ws, header_row, active_keys)
        wb.save(path)

    def merge_items_to_excel(self, output_path, items_list, config=None):
        if not config: return
        headers_map = {"num": "№", "article": "Артикул", "name": "Наименование", "price": "Цена", "qty": "Кол-во", "pack": "Упаковка", "unit": "Ед.", "gtin": "GTIN", "source": "Источник"}
        active_keys = [k for k, v in config.items() if v and k in headers_map]

        wb = Workbook()
        ws = wb.active
        ws.title = "Сводная заявка"
        
        meta = {"organization": "Сводная заявка по нескольким отчетам"}
        header_row = self._write_headers(ws, meta, config, active_keys, headers_map)

        counter = 1
        for items in items_list:
            for item in items:
                row_data = []
                for k in active_keys:
                    val = item.get(k, "")
                    if k == "num": row_data.append(counter)
                    else: row_data.append(self._format_excel_val(val))
                
                if any(row_data):
                    ws.append(row_data)
                    counter += 1

        self._apply_excel_styles(ws, header_row, active_keys)
        wb.save(output_path)