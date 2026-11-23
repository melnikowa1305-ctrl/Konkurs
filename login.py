import sys
import hashlib
import PyQt6.QtCore as QtCore
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon


from db import get_connection

ACCENT = "#00FA9A"        # кнопка «Войти»
BG_MAIN = "white"         # основной фон — белый

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.failed = 0                      # счётчик неудачных попыток
        self.user = None                     # сюда сохраним данные пользователя
        self.setWindowTitle("ООО «Печенька» — Вход")
        self.setFixedSize(400, 400)
        self.setStyleSheet(f"background-color: {BG_MAIN};")

        layout = QVBoxLayout(self)

        # логотип над заголовком
        logo = QLabel()
        logo.setPixmap(QPixmap("logo.png").scaled(
            220, 100,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)


        self.lbl_title = QLabel("Система учёта склада")
        self.lbl_title.setStyleSheet("font-family: 'Times New Roman'; font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_title)

        self.lbl_login = QLabel("Логин*")
        self.edit_login = QLineEdit()
        layout.addWidget(self.lbl_login)
        layout.addWidget(self.edit_login)

        self.lbl_pass = QLabel("Пароль*")
        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.lbl_pass)
        layout.addWidget(self.edit_pass)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setStyleSheet(f"background-color: {ACCENT}; font-family: 'Times New Roman'; padding: 6px;")
        self.btn_login.clicked.connect(self.try_login)
        layout.addWidget(self.btn_login)
               


    def try_login(self):
        login = self.edit_login.text().strip()
        password = self.edit_pass.text()

        # Валидация обязательных полей
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля, отмеченные звёздочкой")
            return

        pwd_hash = hashlib.sha256(password.encode()).hexdigest()

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, full_name, role, is_blocked, failed_attempts "
                "FROM users WHERE login = %s AND password = %s;",
                (login, pwd_hash)
            )
            row = cur.fetchone()

            if row is None:
                # Неуспешная попытка: увеличиваем счётчик у существующего логина (если есть)
                cur.execute("SELECT user_id, failed_attempts, is_blocked FROM users WHERE login = %s;", (login,))
                existing = cur.fetchone()
                if existing:
                    user_id, attempts, blocked = existing
                    if not blocked:
                        attempts += 1
                        blocked = attempts >= 3      # опционально: блокировка после 3 попыток
                        cur.execute(
                            "UPDATE users SET failed_attempts = %s, is_blocked = %s WHERE user_id = %s;",
                            (attempts, blocked, user_id)
                        )
                conn.commit()
                # Общее сообщение — не раскрываем, что именно неверно
                QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
                return

            user_id, full_name, role, blocked, _ = row
            if blocked:
                QMessageBox.warning(self, "Отказ", "Учётная запись заблокирована")
                return

            # Успех: сбрасываем счётчик попыток
            cur.execute("UPDATE users SET failed_attempts = 0 WHERE user_id = %s;", (user_id,))
            conn.commit()

        self.user = {"id": user_id, "name": full_name, "role": role}
        self.open_main()

    def open_main(self):
        from main_window import MainWindow
        self.mgr = MainWindow(self.user)
        self.mgr.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon("icon.png"))
    # закрепляем иконку в панели задач Windows
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pechenka.app.1")

    win = LoginWindow()
    win.show()
    sys.exit(app.exec())


    
