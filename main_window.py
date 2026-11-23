from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox)
from db import get_connection

BG_NAV = "#7FFF00"
BTN_SAVE = "#65beeb"

# какие модули доступны каждой роли
ROLE_MODULES = {
    "Менеджер":                ["Готовая продукция"],
    "Администратор цеха":      ["Управление продукцией"],
    "Кладовщик":               ["Склад"], 
    "Системный администратор": ["Пользователи"],            
    "Директор":                ["Заявки на списание"],           
}


class MainWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"ООО «Печенька» — Главное окно ({user['name']})")
        self.resize(520, 320)
        self.setStyleSheet("background-color: white; font-family: 'Times New Roman';")

        layout = QVBoxLayout(self)

        nav = QLabel(f"Пользователь: {user['name']} | Роль: {user['role']}")
        nav.setStyleSheet(f"background-color: {BG_NAV}; padding: 8px; font-size: 14px;")
        layout.addWidget(nav)

        title = QLabel("Доступные модули")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        for module_name in ROLE_MODULES.get(user["role"], []):
            btn = QPushButton(module_name)
            btn.setStyleSheet("font-family: 'Times New Roman'; padding: 8px;")
            btn.clicked.connect(lambda _, m=module_name: self.open_module(m))
            layout.addWidget(btn)

        btn_logout = QPushButton("Выйти")
        btn_logout.setStyleSheet("font-family: 'Times New Roman'; padding: 6px;")
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)

    def open_module(self, module_name):
        if module_name == "Готовая продукция":
            from manager_window import ManagerWindow
            self.win = ManagerWindow(self.user)
        elif module_name == "Управление продукцией":
            from workshop_window import WorkshopWindow
            self.win = WorkshopWindow(self.user)
        elif module_name == "Склад":
            from keeper_window import KeeperWindow
            self.win = KeeperWindow(self.user)
        elif module_name == "Пользователи":
            from sysadmin_window import SysadminWindow
            self.win = SysadminWindow(self.user)
        elif module_name == "Заявки на списание":
            from director_window import DirectorWindow
            self.win = DirectorWindow(self.user)

        else:
            QMessageBox.information(self, "Отказ", "Доступ к модулю запрещён для вашей роли")
            return
        self.win.show()
        self.hide()



    def logout(self):
        from login import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()
