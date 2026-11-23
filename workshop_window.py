from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QDialog, QFormLayout, QMessageBox)
from db import get_connection

ROW_LOW = "#f59782"
BTN_SAVE = "#65beeb"

class ProductDialog(QDialog):
    """Диалог добавления/редактирования продукции. Если product_id=None — добавление."""
    def __init__(self, product_id=None, name="", quantity=0, expiry="01.01.2027"):
        super().__init__()
        self.product_id = product_id
        self.setWindowTitle("Редактирование" if product_id else "Добавление продукции")
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        form = QFormLayout(self)

        self.lbl_name = QLabel("*Наименование")
        self.edit_name = QLineEdit(name)
        form.addRow(self.lbl_name, self.edit_name)

        self.lbl_qty = QLabel("*Количество (целое, ≥ 0)")
        self.edit_qty = QLineEdit(str(quantity))
        form.addRow(self.lbl_qty, self.edit_qty)

        self.lbl_exp = QLabel("*Срок годности")
        self.edit_exp = QDateEdit()
        self.edit_exp.setCalendarPopup(True)                     # ввод даты через календарь
        self.edit_exp.setDisplayFormat("dd.MM.yyyy")             # формат ДД.ММ.ГГГГ
        day, month, year = map(int, expiry.split("."))
        self.edit_exp.setDate(QDate(year, month, day))
        form.addRow(self.lbl_exp, self.edit_exp)

        btn_save = QPushButton("Сохранить")
        btn_save.setStyleSheet(f"background-color: {BTN_SAVE}; font-family: 'Times New Roman'; padding: 6px;")
        btn_save.clicked.connect(self.validate_and_accept)
        form.addRow(btn_save)

    def validate_and_accept(self):
        name = self.edit_name.text().strip()
        qty_text = self.edit_qty.text().strip()

        # обязательные поля
        if not name or not qty_text:
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля, отмеченные звёздочкой")
            return
        # числовые поля: целочисленность и неотрицательность
        if not qty_text.isdigit():
            QMessageBox.warning(self, "Ошибка", "Количество должно быть целым неотрицательным числом")
            return

        self.data = (name, int(qty_text), self.edit_exp.date().toString("yyyy-MM-dd"))
        self.accept()

class WorkshopWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"ООО «Печенька» — Управление продукцией ({user['name']})")
        self.resize(760, 480)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        layout = QVBoxLayout(self)

        nav = QLabel("Меню: Управление продукцией")
        nav.setStyleSheet("background-color: #7FFF00; padding: 8px; font-size: 14px;")
        layout.addWidget(nav)

        controls = QHBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Поиск по наименованию...")
        # debounce: не гоняем запрос на каждый нажатый символ
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh)
        self.edit_search.textChanged.connect(self._search_timer.start)
        controls.addWidget(self.edit_search)

        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self.add_product)
        controls.addWidget(btn_add)

        btn_edit = QPushButton("Редактировать")
        btn_edit.clicked.connect(self.edit_product)
        controls.addWidget(btn_edit)

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self.delete_product)
        controls.addWidget(btn_del)

        btn_back = QPushButton("Назад")
        btn_back.clicked.connect(self.go_back)
        controls.addWidget(btn_back)

        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Наименование", "Количество", "Срок годности"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        text = self.edit_search.text().strip().lower()
        with get_connection() as conn:
            cur = conn.cursor()
            query = ("SELECT product_id, name, quantity, expiry_date FROM finished_products")
            params = ()
            if text:
                # поиск на стороне СУБД — не тянем все строки ради фильтра
                query += " WHERE lower(name) LIKE %s"
                params = ("%" + text + "%",)
            cur.execute(query + " ORDER BY product_id;", params)
            rows = cur.fetchall()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, (pid, name, qty, exp) in enumerate(rows):
            values = [str(pid), name, str(qty), exp.strftime("%d.%m.%Y")]
            low = qty < 5
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                if low:
                    item.setBackground(QBrush(QColor(ROW_LOW)))
                if j in (0, 2):
                    item.setData(Qt.ItemDataRole.EditRole, int(val))
                self.table.setItem(r, j, item)
        self.table.setSortingEnabled(True)

    def get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите запись в таблице")
            return None
        return int(self.table.item(row, 0).text())

    def add_product(self):
        dlg = ProductDialog()
        if dlg.exec():
            name, qty, expiry = dlg.data
            with get_connection() as conn:
                cur = conn.cursor()
                # проверка уникальности наименования
                cur.execute("SELECT 1 FROM finished_products WHERE name = %s;", (name,))
                if cur.fetchone():
                    QMessageBox.warning(self, "Ошибка", "Продукция с таким наименованием уже существует")
                    return
                cur.execute(
                    "INSERT INTO finished_products (name, quantity, expiry_date) VALUES (%s, %s, %s);",
                    (name, qty, expiry)
                )
                conn.commit()
            self.refresh()

    def edit_product(self):
        pid = self.get_selected_id()
        if pid is None:
            return
        row = self.table.currentRow()
        name = self.table.item(row, 1).text()
        qty = self.table.item(row, 2).text()
        expiry = self.table.item(row, 3).text()
        dlg = ProductDialog(pid, name, qty, expiry)
        if dlg.exec():
            new_name, new_qty, new_expiry = dlg.data
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM finished_products WHERE name = %s AND product_id <> %s;",
                            (new_name, pid))
                if cur.fetchone():
                    QMessageBox.warning(self, "Ошибка", "Продукция с таким наименованием уже существует")
                    return
                cur.execute(
                    "UPDATE finished_products SET name = %s, quantity = %s, expiry_date = %s WHERE product_id = %s;",
                    (new_name, new_qty, new_expiry, pid)
                )
                conn.commit()
            self.refresh()

    def delete_product(self):
        pid = self.get_selected_id()
        if pid is None:
            return
        # подтверждение опасного действия — обязательный критерий ТЗ
        answer = QMessageBox.question(
            self, "Подтверждение",
            "Вы действительно хотите удалить эту продукцию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM finished_products WHERE product_id = %s;", (pid,))
            conn.commit()
        self.refresh()

    def go_back(self):
        from main_window import MainWindow
        self.main = MainWindow(self.user)
        self.main.show()
        self.close()
