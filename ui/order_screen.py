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
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem
import requests

from config import API_BASE_URL


class OrderScreen(QWidget):
    # emitted after an order is successfully created (so other windows can refresh)
    order_created = pyqtSignal()
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
        # Note: Reset control resides in AdminScreen; OrderScreen refreshes via Admin signal.
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
        try:
            resp = requests.get(f"{API_BASE_URL}/api/menu", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.menuTable.setRowCount(len(data))
            for i, item in enumerate(data):
                id_item = QTableWidgetItem(str(item.get("id", "")))
                name_item = QTableWidgetItem(item.get("name", ""))
                price_item = QTableWidgetItem(str(item.get("price", "")))
                qty_item = QTableWidgetItem("0")

                self.menuTable.setItem(i, 0, id_item)
                self.menuTable.setItem(i, 1, name_item)
                self.menuTable.setItem(i, 2, price_item)
                self.menuTable.setItem(i, 3, qty_item)

            self.menuTable.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"메뉴를 불러오지 못했습니다:\n{e}")

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
        try:
            resp = requests.get(f"{API_BASE_URL}/api/orders/queue", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.queueTable.setRowCount(len(data))
            for i, o in enumerate(data):
                pickup = QTableWidgetItem(str(o.get("pickup_no", "")))
                status = QTableWidgetItem(str(o.get("status", "")))
                ordered_at = o.get("ordered_at") or ""
                ordered_item = QTableWidgetItem(str(ordered_at))
                eta = QTableWidgetItem(str(o.get("eta_sec", "")))

                self.queueTable.setItem(i, 0, pickup)
                self.queueTable.setItem(i, 1, status)
                self.queueTable.setItem(i, 2, ordered_item)
                self.queueTable.setItem(i, 3, eta)
        except Exception:
            # 주기적 갱신 중 에러는 조용히 무시
            return

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
        rfid = self.txtRfid.text().strip()
        if not rfid:
            QMessageBox.warning(self, "알림", "RFID 카드 ID가 없습니다.")
            return

        items = []
        row_count = self.menuTable.rowCount()
        for i in range(row_count):
            id_item = self.menuTable.item(i, 0)
            qty_item = self.menuTable.item(i, 3)
            if id_item is None or qty_item is None:
                continue
            try:
                menu_id = int(id_item.text())
                qty = int(qty_item.text())
            except Exception:
                continue
            if qty > 0:
                items.append({"menu_id": menu_id, "qty": qty})

        if not items:
            QMessageBox.information(self, "알림", "수량이 1 이상인 메뉴가 없습니다.")
            return

        payload = {"rfid_card_id": rfid, "items": items}

        try:
            resp = requests.post(f"{API_BASE_URL}/api/orders", json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            pickup_no = data.get("pickup_no")
            QMessageBox.information(self, "주문 완료", f"주문이 접수되었습니다. 픽업 번호: {pickup_no}")

            # 초기화 및 대기열 갱신
            for i in range(row_count):
                self.menuTable.setItem(i, 3, QTableWidgetItem("0"))
            self.load_queue()
            # notify other windows (e.g., AdminScreen) to refresh materials
            try:
                self.order_created.emit()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "오류", f"주문에 실패했습니다:\n{e}")

    def on_click_reset_queue(self):
        """OrderScreen에서 대기열 초기화 버튼 핸들러 (관리자와 동일하게 동작)
        확인 후 DELETE /api/orders/queue 호출
        """
        reply = QMessageBox.question(
            self,
            "대기열 초기화",
            "대기열을 초기화하시겠습니까? 삭제된 주문은 복구할 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            resp = requests.delete(f"{API_BASE_URL}/api/orders/queue", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            deleted = data.get("deleted_orders")
            QMessageBox.information(self, "완료", f"대기열이 초기화되었습니다. 삭제된 주문: {deleted}")
            self.load_queue()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"대기열 초기화에 실패했습니다:\n{e}")

