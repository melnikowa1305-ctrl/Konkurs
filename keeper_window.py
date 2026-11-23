from datetime import date
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QInputDialog, QDialog, QMessageBox)
from db import get_connection

ROW_LOW = "#f59782"
BTN_GREEN = "#00FA9A"   # «Списать» — по ТЗ

class RequestsDialog(QDialog):
    """Просмотр заявок кладовщика."""
    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("Мои заявки на списание")
        self.resize(520, 300)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")
        layout = QVBoxLayout(self)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Продукция", "Кол-во", "Дата", "Статус"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT w.request_id, p.name, w.quantity, w.request_date, w.status
                FROM write_off_requests w
                JOIN finished_products p ON w.product_id = p.product_id
                WHERE w.created_by = %s
                ORDER BY w.request_id DESC;
            """, (user_id,))
            rows = cur.fetchall()

        table.setRowCount(len(rows))
        for i, (rid, name, qty, rdate, status) in enumerate(rows):
            for j, val in enumerate([str(rid), name, str(qty),
                                     rdate.strftime("%d.%m.%Y"), status]):
                table.setItem(i, j, QTableWidgetItem(val))

class KeeperWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"ООО «Печенька» — Склад ({user['name']})")
        self.resize(860, 520)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        layout = QVBoxLayout(self)

        nav = QLabel("Меню: Склад — материалы и готовая продукция")
        nav.setStyleSheet("background-color: #7FFF00; padding: 8px; font-size: 14px;")
        layout.addWidget(nav)

        top = QHBoxLayout()
        self.cmb_table = QComboBox()
        self.cmb_table.addItems(["Материалы", "Готовая продукция"])
        self.cmb_table.currentTextChanged.connect(self.refresh)
        top.addWidget(self.cmb_table)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Поиск по наименованию...")
        self.edit_search.textChanged.connect(self.refresh)
        top.addWidget(self.edit_search)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.refresh)
        top.addWidget(btn_refresh)

        btn_back = QPushButton("Назад")
        btn_back.clicked.connect(self.go_back)
        top.addWidget(btn_back)
        layout.addLayout(top)

        actions = QHBoxLayout()
        btn_in = QPushButton("Приход")
        btn_in.clicked.connect(self.income)
        btn_out = QPushButton("Расход")
        btn_out.clicked.connect(self.outcome)
        btn_corr = QPushButton("Корректировка")
        btn_corr.clicked.connect(self.correction)
        btn_wo = QPushButton("Списать")
        btn_wo.setStyleSheet(f"background-color: {BTN_GREEN};")
        btn_wo.clicked.connect(self.create_write_off)
        btn_req = QPushButton("Мои заявки")
        btn_req.clicked.connect(self.show_requests)
        for b in (btn_in, btn_out, btn_corr, btn_wo, btn_req):
            actions.addWidget(b)
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.refresh()

    # ---------- отображение ----------
    def refresh(self):
        is_materials = self.cmb_table.currentText() == "Материалы"
        text = self.edit_search.text().strip().lower()

        with get_connection() as conn:
            cur = conn.cursor()
            if is_materials:
                cur.execute("SELECT ingredient_id, name, quantity, unit FROM ingredients;")
            else:
                cur.execute("SELECT product_id, name, quantity, expiry_date FROM finished_products;")
            rows = cur.fetchall()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Наименование", "Количество", "Ед. изм." if is_materials else "Срок годности"]
        )

        for pid, name, qty, extra in rows:
            if text and text not in name.lower():
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            if is_materials:
                values = [str(pid), name, str(qty), extra]
            else:
                values = [str(pid), name, str(qty), extra.strftime("%d.%m.%Y")]

            low = qty < 5
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                if low:
                    item.setBackground(QBrush(QColor(ROW_LOW)))
                if j in (0, 2):
                    # число может прийти и как '500,00' (NUMERIC), и как '500'
                    try:
                        item.setData(Qt.ItemDataRole.EditRole,
                                     int(float(val.replace(",", "."))))
                    except ValueError:
                        pass    # не число — оставляем как строку
                self.table.setItem(r, j, item)

        self.table.setSortingEnabled(True)

    # ---------- вспомогательное ----------
    def selected_row(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите запись в таблице")
            return None
        return row

    def current_db_table(self):
        if self.cmb_table.currentText() == "Материалы":
            return "ingredients", "ingredient_id"
        return "finished_products", "product_id"

    # ---------- приход / расход / корректировка ----------
    def change_quantity(self, sign):
        row = self.selected_row()
        if row is None:
            return
        pid = int(self.table.item(row, 0).text())
        qty = int(self.table.item(row, 2).text())
        title = "Приход" if sign > 0 else "Расход"
        amount, ok = QInputDialog.getInt(self, title, "Количество:", 1, 1, 1_000_000)
        if not ok:
            return
        if sign < 0 and amount > qty:
            QMessageBox.warning(self, "Ошибка", "Недостаточно остатка: нельзя уйти в минус")
            return
        new_qty = qty + sign * amount
        table, id_col = self.current_db_table()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE {table} SET quantity = %s WHERE {id_col} = %s;",
                        (new_qty, pid))
            conn.commit()
        self.refresh()

    def income(self):
        self.change_quantity(+1)

    def outcome(self):
        self.change_quantity(-1)

    def correction(self):
        row = self.selected_row()
        if row is None:
            return
        pid = int(self.table.item(row, 0).text())
        qty, ok = QInputDialog.getInt(
            self, "Корректировка (инвентаризация)",
            "Установить точное количество:", 0, 0, 1_000_000
        )
        if not ok:
            return
        table, id_col = self.current_db_table()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE {table} SET quantity = %s WHERE {id_col} = %s;",
                        (qty, pid))
            conn.commit()
        self.refresh()

    # ---------- заявка на списание ----------
    def create_write_off(self):
        if self.cmb_table.currentText() != "Готовая продукция":
            QMessageBox.information(self, "Информация",
                                    "Списание просроченной продукции — в таблице «Готовая продукция»")
            return
        row = self.selected_row()
        if row is None:
            return
        pid = int(self.table.item(row, 0).text())
        qty = int(self.table.item(row, 2).text())
        day, month, year = map(int, self.table.item(row, 3).text().split("."))
        if date(year, month, day) >= date.today():
            QMessageBox.information(self, "Информация",
                                    "Срок годности не истёк — списание не требуется")
            return
        amount, ok = QInputDialog.getInt(
            self, "Заявка на списание", f"Количество (не больше {qty}):", qty, 1, qty
        )
        if not ok:
            return
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO write_off_requests (product_id, quantity, status, created_by)
                           VALUES (%s, %s, 'pending', %s);""",
                        (pid, amount, self.user["id"]))
            conn.commit()
        QMessageBox.information(self, "Готово", "Заявка отправлена (статус pending)")
        self.refresh()

    def show_requests(self):
        dlg = RequestsDialog(self.user["id"])
        dlg.exec()

    def go_back(self):
        from main_window import MainWindow
        self.main = MainWindow(self.user)
        self.main.show()
        self.close()
