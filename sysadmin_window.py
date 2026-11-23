import hashlib
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QDialog, QFormLayout, QMessageBox)
from db import get_connection

ROLES = ["Менеджер", "Администратор цеха", "Кладовщик",
         "Системный администратор", "Директор"]

class UserDialog(QDialog):
    """Добавление/редактирование пользователя. Если user_id=None — добавление."""
    def __init__(self, user_id=None, login="", full_name="", role="Менеджер"):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Редактирование" if user_id else "Добавление пользователя")
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        form = QFormLayout(self)
        self.edit_login = QLineEdit(login)
        form.addRow(QLabel("*Логин"), self.edit_login)

        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("" if user_id else "Не менее 6 символов")
        form.addRow(QLabel("*Пароль" if not user_id else "Новый пароль (пусто = не менять)"),
                    self.edit_pass)
        self.edit_fio = QLineEdit(full_name)
        form.addRow(QLabel("*ФИО"), self.edit_fio)

        self.cmb_role = QComboBox()
        self.cmb_role.addItems(ROLES)
        self.cmb_role.setCurrentText(role)
        form.addRow(QLabel("*Роль"), self.cmb_role)

        btn_save = QPushButton("Сохранить")
        btn_save.setStyleSheet("background-color: #65beeb; font-family: 'Times New Roman'; padding: 6px;")
        btn_save.clicked.connect(self.validate_and_accept)
        form.addRow(btn_save)

    def validate_and_accept(self):
        login = self.edit_login.text().strip()
        fio = self.edit_fio.text().strip()
        password = self.edit_pass.text()

        if not login or not fio:                      # обязательные поля
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля, отмеченные звёздочкой")
            return
        if not self.user_id and len(password) < 6:    # пароль обязателен при добавлении
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
            return
        if self.user_id and password and len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
            return

        self.data = (login, fio, self.cmb_role.currentText(), password)
        self.accept()

class SysadminWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"ООО «Печенька» — Пользователи ({user['name']})")
        self.resize(760, 480)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        layout = QVBoxLayout(self)
        nav = QLabel("Меню: Пользователи системы")
        nav.setStyleSheet("background-color: #7FFF00; padding: 8px; font-size: 14px;")
        layout.addWidget(nav)

        controls = QHBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Поиск по ФИО или логину...")
        # debounce: не гоняем запрос на каждый нажатый символ
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh)
        self.edit_search.textChanged.connect(self._search_timer.start)
        controls.addWidget(self.edit_search)
        btn_add = QPushButton("Добавить"); btn_add.clicked.connect(self.add_user)
        btn_edit = QPushButton("Редактировать"); btn_edit.clicked.connect(self.edit_user)
        btn_del = QPushButton("Удалить"); btn_del.clicked.connect(self.delete_user)
        btn_back = QPushButton("Назад"); btn_back.clicked.connect(self.go_back)
        for b in (btn_add, btn_edit, btn_del, btn_back):
            controls.addWidget(b)
        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Логин", "ФИО", "Роль"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        text = self.edit_search.text().strip().lower()
        with get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT user_id, login, full_name, role FROM users"
            params = ()
            if text:
                # поиск на стороне СУБД — не тянем все строки ради фильтра
                query += " WHERE lower(full_name) LIKE %s OR lower(login) LIKE %s"
                like = "%" + text + "%"
                params = (like, like)
            cur.execute(query + " ORDER BY user_id;", params)
            rows = cur.fetchall()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, (uid, login, fio, role) in enumerate(rows):
            for j, val in enumerate([str(uid), login, fio, role]):
                item = QTableWidgetItem(val)
                if j == 0:
                    item.setData(Qt.ItemDataRole.EditRole, int(val))
                self.table.setItem(r, j, item)
        self.table.setSortingEnabled(True)

    def get_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите запись в таблице")
            return None
        return int(self.table.item(row, 0).text()), row

    def add_user(self):
        dlg = UserDialog()
        if dlg.exec():
            login, fio, role, password = dlg.data
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM users WHERE login = %s;", (login,))
                if cur.fetchone():
                    QMessageBox.warning(self, "Ошибка", "Пользователь с таким логином уже существует")
                    return
                cur.execute("""INSERT INTO users (login, password, full_name, role)
                               VALUES (%s, %s, %s, %s);""",
                            (login, hashlib.sha256(password.encode()).hexdigest(), fio, role))
                conn.commit()
            self.refresh()

    def edit_user(self):
        sel = self.get_selected()
        if sel is None:
            return
        uid, row = sel
        login = self.table.item(row, 1).text()
        fio = self.table.item(row, 2).text()
        role = self.table.item(row, 3).text()
        dlg = UserDialog(uid, login, fio, role)
        if dlg.exec():
            new_login, new_fio, new_role, password = dlg.data
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM users WHERE login = %s AND user_id <> %s;",
                            (new_login, uid))
                if cur.fetchone():
                    QMessageBox.warning(self, "Ошибка", "Пользователь с таким логином уже существует")
                    return
                if password:
                    cur.execute("""UPDATE users SET login=%s, full_name=%s, role=%s, password=%s
                                   WHERE user_id=%s;""",
                                (new_login, new_fio, new_role,
                                 hashlib.sha256(password.encode()).hexdigest(), uid))
                else:
                    cur.execute("UPDATE users SET login=%s, full_name=%s, role=%s WHERE user_id=%s;",
                                (new_login, new_fio, new_role, uid))
                conn.commit()
            self.refresh()

    def delete_user(self):
        sel = self.get_selected()
        if sel is None:
            return
        uid, _ = sel
        if uid == self.user["id"]:                    # страховка: не удаляем самого себя
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить свою учётную запись")
            return
        answer = QMessageBox.question(
            self, "Подтверждение", "Вы действительно хотите удалить этого пользователя?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE user_id = %s;", (uid,))
            conn.commit()
        self.refresh()

    def go_back(self):
        from main_window import MainWindow
        self.main = MainWindow(self.user)
        self.main.show()
        self.close()
