import sys
from PyQt5.QtWidgets import QApplication
from ui.kiosk_app import KioskApp

def main():
    # 1️⃣ QApplication 객체 생성 (반드시 먼저)
    app = QApplication(sys.argv)

    # 2️⃣ KioskApp(QMainWindow) 객체 생성
    window = KioskApp()
    window.show()  # 창 표시

    # 3️⃣ 이벤트 루프 시작
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
