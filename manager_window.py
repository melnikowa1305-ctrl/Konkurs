from datetime import date
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QMessageBox)
from db import get_connection


BG_NAV = "#7FFF00"     # цвет навигационной панели
ROW_LOW = "#f59782"    # подсветка остатков < 5

class ManagerWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"ООО «Печенька» — Готовая продукция ({user['name']}, {user['role']})")
        self.resize(760, 480)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        layout = QVBoxLayout(self)

        # --- Навигационная панель ---
        nav = QLabel("Меню: Готовая продукция")
        nav.setStyleSheet(f"background-color: {BG_NAV}; padding: 8px; font-size: 14px;")
        layout.addWidget(nav)

        # --- Панель поиска и фильтрации ---
        controls = QHBoxLayout()

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Поиск по наименованию...")
        self.edit_search.textChanged.connect(self.refresh)
        controls.addWidget(self.edit_search)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["Все", "Только просроченные", "Количество < 5"])
        self.cmb_filter.currentTextChanged.connect(self.refresh)
        controls.addWidget(self.cmb_filter)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        controls.addWidget(self.btn_refresh)

        layout.addLayout(controls)

        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Наименование", "Количество", "Срок годности"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)   # сортировка по клику на заголовок
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        text = self.edit_search.text().strip().lower()
        flt = self.cmb_filter.currentText()
        today = date.today()

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT product_id, name, quantity, expiry_date FROM finished_products;")
            rows = cur.fetchall()

        # Фильтрация и поиск выполняем на стороне Python — наглядно для ДЭ
        filtered = []
        for pid, name, qty, exp in rows:
            if text and text not in name.lower():
                continue
            if flt == "Только просроченные" and exp >= today:
                continue
            if flt == "Количество < 5" and qty >= 5:
                continue
            filtered.append((pid, name, qty, exp))

        # Заполняем таблицу
        self.table.setSortingEnabled(False)      # отключаем на время заполнения
        self.table.setRowCount(len(filtered))
        for i, (pid, name, qty, exp) in enumerate(filtered):
            values = [str(pid), name, str(qty), exp.strftime("%d.%m.%Y")]
            low = qty < 5                        # подсветка остатков менее 5
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                if low:
                    item.setBackground(QBrush(QColor(ROW_LOW)))
                # числовые колонки сортируем как числа
                if j in (0, 2):
                    item.setData(Qt.ItemDataRole.EditRole, int(val))
                self.table.setItem(i, j, item)
        self.table.setSortingEnabled(True)
