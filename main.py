"""
프로젝트 메인 엔트리.
- 여기서 PyQt 앱을 실행
"""

import sys

from PyQt6.QtWidgets import QApplication
from ui.admin_screen import AdminScreen
from ui.order_screen import OrderScreen


def main():
    app = QApplication(sys.argv)

    # Open both Admin and Order screens in separate windows
    admin_win = AdminScreen()
    admin_win.show()

    order_win = OrderScreen()
    order_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
