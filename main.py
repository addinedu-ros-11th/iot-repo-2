"""
프로젝트 메인 엔트리.
- 여기서 PyQt 앱을 실행
"""

import sys

from PyQt6.QtWidgets import QApplication
from ui.kiosk_app import KioskApp


def main():
    app = QApplication(sys.argv)

    window = KioskApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
