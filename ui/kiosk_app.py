"""
메인 윈도우.

- 기본적으로 OrderScreen을 중앙에 띄움
- 메뉴/탭 추가해서 AdminScreen으로 전환 가능
"""

from PyQt5.QtWidgets import QMainWindow, QAction, QMenuBar

from ui.order_screen import OrderScreen
from ui.admin_screen import AdminScreen


class KioskApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Fish Machine Kiosk")

        self.order_screen = OrderScreen(self)
        self.admin_screen = AdminScreen(self)

        self.setCentralWidget(self.order_screen)

        self._setup_menu()

    def _setup_menu(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        view_menu = menubar.addMenu("View")

        action_order = QAction("Order", self)
        action_order.triggered.connect(self.show_order_screen)
        view_menu.addAction(action_order)

        action_admin = QAction("Admin", self)
        action_admin.triggered.connect(self.show_admin_screen)
        view_menu.addAction(action_admin)

    def show_order_screen(self):
        self.setCentralWidget(self.order_screen)

    def show_admin_screen(self):
        self.setCentralWidget(self.admin_screen)
