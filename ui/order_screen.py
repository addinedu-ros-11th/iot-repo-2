"""
손님 주문 화면.

order_screen.ui 에서 다음 위젯 이름을 사용한다고 가정한다:

- self.menuTable      : QTableWidget (메뉴 목록)
    - 컬럼: 0:id(숨김), 1:메뉴명, 2:가격, 3:수량
- self.queueTable     : QTableWidget (대기열)
    - 컬럼: 0:픽업번호, 1:상태, 2:주문시각, 3:ETA(초)
- self.btnReloadMenu  : QPushButton (메뉴 새로고침)
- self.btnOrder       : QPushButton (주문 실행)
- self.txtRfid        : QLineEdit (RFID 카드 ID 입력/스캔 값)

API:
- GET  {API_BASE_URL}/api/menu
- GET  {API_BASE_URL}/api/orders/queue
- POST {API_BASE_URL}/api/orders
"""

import os

from PyQt6 import uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget

from config import API_BASE_URL


class OrderScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "order_screen.ui")
        uic.loadUi(ui_path, self)

        # 메뉴 테이블 기본 설정 (컬럼 구조만 잡아둠)
        self.menuTable.setColumnCount(4)
        self.menuTable.setHorizontalHeaderLabels(["ID", "메뉴명", "가격", "수량"])
        self.menuTable.setColumnHidden(0, True)

        # 대기열 테이블 기본 설정
        self.queueTable.setColumnCount(4)
        self.queueTable.setHorizontalHeaderLabels(["픽업번호", "상태", "주문시각", "ETA(초)"])

        # 버튼 시그널 연결
        self.btnReloadMenu.clicked.connect(self.load_menu)
        self.btnOrder.clicked.connect(self.on_click_order)

        # 대기열 주기적 갱신 타이머 (3초)
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.load_queue)
        self.queue_timer.start(3000)

        # 초기에 한 번 로딩
        # 실제 구현은 load_menu / load_queue 안에서 작성
        self.load_menu()
        self.load_queue()

    def load_menu(self):
        """
        메뉴 목록 로딩.

        요구사항:
        1) GET {API_BASE_URL}/api/menu 호출 (requests 사용)
           - 응답: 메뉴 리스트(JSON 배열)
        2) self.menuTable 의 row 개수를 응답 길이만큼 설정
        3) 각 row 에 다음과 같이 채운다:
           - col0: 메뉴 id (문자열, 숨김)
           - col1: 메뉴 name
           - col2: price
           - col3: 수량 (초기값 "0")
        4) self.menuTable.resizeColumnsToContents() 호출로 컬럼 너비 맞춤
        5) 에러 발생 시 QMessageBox 로 사용자에게 알림

        """
        # TODO
        raise NotImplementedError("OrderScreen.load_menu 구현 필요")

    def load_queue(self):
        """
        대기열 목록 로딩.

        요구사항:
        1) GET {API_BASE_URL}/api/orders/queue 호출
           - 응답: 주문 리스트(JSON 배열), 각 요소는
             {
               "order_id": int,
               "pickup_no": int,
               "status": str,
               "ordered_at": str or null,
               "eta_sec": int
             }
        2) self.queueTable 의 row 개수를 응답 길이만큼 설정
        3) 각 row 에 다음과 같이 채운다:
           - col0: pickup_no
           - col1: status
           - col2: ordered_at (문자열, null 이면 빈 문자열)
           - col3: eta_sec
        4) 에러 발생 시(네트워크 끊김 등) 화면에는 따로 알리지 않고 조용히 무시해도 된다.
        """
        # TODO
        raise NotImplementedError("OrderScreen.load_queue 구현 필요")

    def on_click_order(self):
        """
        주문 버튼 클릭 시 동작.

        요구사항:
        1) self.txtRfid 에서 RFID 카드 ID 문자열 읽기
           - 비어 있으면 메시지 박스로 "RFID 카드 ID가 없습니다." 표시 후 종료
        2) self.menuTable 의 각 row 에 대해:
           - col0: menu_id (int로 변환)
           - col3: 수량(qty, int로 변환)
           - qty > 0 인 row만 수집
        3) 수집된 items 가 하나도 없으면
           - "수량이 1 이상인 메뉴가 없습니다." 메시지 후 종료
        4) payload 생성:
           {
             "rfid_card_id": <txtRfid 값>,
             "items": [
               { "menu_id": <int>, "qty": <int> },
               ...
             ]
           }
        5) POST {API_BASE_URL}/api/orders 에 payload 를 JSON 으로 전송
           - 성공 시 응답 JSON 에서 pickup_no 읽기
           - QMessageBox 로 "주문이 접수되었습니다. 픽업 번호: XXX" 표시
        6) 주문 성공 후:
           - self.menuTable 의 모든 수량(col3)을 "0"으로 초기화
           - self.load_queue() 호출로 대기열 갱신
        7) 실패 시:
           - 메시지 박스로 에러 내용 표시
        """
        # TODO
        raise NotImplementedError("OrderScreen.on_click_order 구현 필요")
