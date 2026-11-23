from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox)
from db import get_connection

STATUS_LABEL = {"pending": "Ожидает", "approved": "Одобрена", "rejected": "Отклонена"}
ROW_PENDING = "#fff3cd"   # мягкая жёлтая подсветка для заявок в ожидании

class DirectorWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"ООО «Печенька» — Заявки на списание ({user['name']})")
        self.resize(820, 500)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        layout = QVBoxLayout(self)
        nav = QLabel("Меню: Заявки на списание продукции")
        nav.setStyleSheet("background-color: #7FFF00; padding: 8px; font-size: 14px;")
        layout.addWidget(nav)

        controls = QHBoxLayout()
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["Все", "Ожидает", "Одобрена", "Отклонена"])
        self.cmb_filter.currentTextChanged.connect(self.refresh)
        controls.addWidget(self.cmb_filter)
        btn_ok = QPushButton("Одобрить"); btn_ok.clicked.connect(self.approve)
        btn_no = QPushButton("Отклонить"); btn_no.clicked.connect(self.reject)
        btn_back = QPushButton("Назад"); btn_back.clicked.connect(self.go_back)
        for b in (btn_ok, btn_no, btn_back):
            controls.addWidget(b)
        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Продукция", "Кол-во", "Дата заявки", "Статус", "Кто создал"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        flt = self.cmb_filter.currentText()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT w.request_id, p.name, w.quantity, w.request_date, w.status, u.full_name
                FROM write_off_requests w
                JOIN finished_products p ON w.product_id = p.product_id
                LEFT JOIN users u ON w.created_by = u.user_id
                ORDER BY w.request_id DESC;
            """)
            rows = cur.fetchall()

        self.table.setRowCount(0)
        for rid, name, qty, rdate, status, author in rows:
            if flt != "Все" and STATUS_LABEL[status] != flt:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            values = [str(rid), name, str(qty), rdate.strftime("%d.%m.%Y"),
                      STATUS_LABEL[status], author or "—"]
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                if j == 0:
                    item.setData(Qt.ItemDataRole.EditRole, int(val))
                if status == "pending":
                    item.setBackground(QBrush(QColor(ROW_PENDING)))
                self.table.setItem(r, j, item)

    def selected_request(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите заявку в таблице")
            return None
        rid = int(self.table.item(row, 0).text())
        status = self.table.item(row, 4).text()
        if status != "Ожидает":
            QMessageBox.information(self, "Информация", "Эта заявка уже обработана")
            return None
        return rid

    def approve(self):
        rid = self.selected_request()
        if rid is None:
            return
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT w.product_id, w.quantity, p.quantity
                           FROM write_off_requests w
                           JOIN finished_products p ON w.product_id = p.product_id
                           WHERE w.request_id = %s;""", (rid,))
            result = cur.fetchone()
            if result is None:
                QMessageBox.warning(self, "Ошибка", "Заявка не найдена")
                return
            pid, w_qty, stock = result
            if w_qty > stock:                       # не уходим в минус при списании
                QMessageBox.warning(self, "Ошибка",
                                    f"На складе только {stock} шт. — недостаточно для списания {w_qty}")
                return
            cur.execute("UPDATE finished_products SET quantity = quantity - %s WHERE product_id = %s;",
                        (w_qty, pid))
            cur.execute("UPDATE write_off_requests SET status = 'approved' WHERE request_id = %s;", (rid,))
            conn.commit()
        self.refresh()

    def reject(self):
        rid = self.selected_request()
        if rid is None:
            return
        cur_ = QMessageBox.question(
            self, "Подтверждение", "Отклонить эту заявку?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cur_ != QMessageBox.StandardButton.Yes:
            return
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE write_off_requests SET status = 'rejected' WHERE request_id = %s;", (rid,))
            conn.commit()
        self.refresh()

    def go_back(self):
        from main_window import MainWindow
        self.main = MainWindow(self.user)
        self.main.show()
        self.close()
