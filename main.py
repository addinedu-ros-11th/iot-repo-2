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

    # Admin 및 Order 화면을 각각의 창으로 엶
    admin_win = AdminScreen()
    admin_win.show()

    order_win = OrderScreen()
    order_win.show()
    # Admin의 초기화 신호를 Order 화면의 로드에 연결하여 동기화 유지
    try:
        admin_win.queue_reset.connect(order_win.load_queue)
    except Exception:
        pass

    # 주문 생성 신호를 Admin의 재고 로드에 연결하여 소모된 재고가 Admin UI에 반영되도록 함
    try:
        order_win.order_created.connect(admin_win.load_materials)
    except Exception:
        pass
    try:
        order_win.order_created.connect(admin_win.load_material_tx)
    except Exception:
        pass
    
    # 주문 상태 변경/취소 시 OrderScreen도 대기열 갱신하도록 연결
    try:
        admin_win.order_changed.connect(order_win.load_queue)
    except Exception:
        pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
