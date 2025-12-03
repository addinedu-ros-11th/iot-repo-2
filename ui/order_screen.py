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
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem, QPushButton, QHBoxLayout, QGridLayout, QSizePolicy
from functools import partial
import requests

from config import API_BASE_URL


class OrderScreen(QWidget):
    # 주문이 성공적으로 생성된 후 발생하는 신호 (다른 창이 갱신하도록)
    order_created = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "order_screen.ui")
        uic.loadUi(ui_path, self)

        # 메뉴 목록은 버튼형 UI로 표시하도록 변경: 기존 테이블/리로드 버튼은 숨김
        try:
            self.menuTable.hide()
        except Exception:
            pass
        try:
            self.btnReloadMenu.hide()
        except Exception:
            pass

        # 장바구니 구조 초기화
        # cart는 dict: menu_id -> {"menu_id":..., "name":..., "price":..., "qty":...}
        self.cart: dict[int, dict] = {}
        # 구버전 UI에는 `cartTable`이 없을 수 있으므로 존재 여부를 확인
        if hasattr(self, "cartTable"):
            # 마지막 컬럼은 조절 버튼(+/-)을 배치함
            self.cartTable.setColumnCount(5)
            self.cartTable.setHorizontalHeaderLabels(["메뉴명", "가격", "수량", "합계", "조절"])

        # 총합 레이블과 버튼은 .ui에서 제공될 수 있음
        # '장바구니에 담기' 버튼은 UI에서 제거됨
        if hasattr(self, "btnClearCart"):
            self.btnClearCart.clicked.connect(self.on_click_clear_cart)
        # 장바구니가 비어있을 때 주문 버튼을 비활성화
        try:
            self.btnOrder.setEnabled(False)
        except Exception:
            pass

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
        # 참고: 대기열 초기화 컨트롤은 AdminScreen에 있으며, OrderScreen은 Admin의 신호로 갱신됨.
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

            # 이전에 생성된 버튼 위젯이 있으면 제거
            try:
                if hasattr(self, "menu_buttons_widget") and self.menu_buttons_widget is not None:
                    self.menu_buttons_widget.setParent(None)
            except Exception:
                pass

            # 버튼 그리드 위젯 생성 (최대 6개 버튼)
            self.menu_buttons_widget = QWidget()
            grid = QGridLayout(self.menu_buttons_widget)
            grid.setContentsMargins(4, 4, 4, 4)
            grid.setSpacing(6)

            # 사용자 요청: 버튼 6개로 표시 (or fewer)
            max_buttons = 6
            for idx, item in enumerate(data[:max_buttons]):
                menu_id = int(item.get("id", 0) or 0)
                name = item.get("name", "")
                price = int(item.get("price", 0) or 0)
                btn = QPushButton(f"{name}\n{price}원")
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                btn.clicked.connect(lambda _checked, m=menu_id, n=name, p=price: self._menu_add_clicked(m, n, p))
                r = idx // 3
                c = idx % 3
                grid.addWidget(btn, r, c)

            # groupBox_menu의 레이아웃에 버튼 위젯을 삽입
            try:
                layout = self.groupBox_menu.layout()
                layout.insertWidget(0, self.menu_buttons_widget)
            except Exception:
                pass
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

        # 주문 시 장바구니 내용을 사용함 (cart -> menu_id, qty)
        items = []
        for menu_id, it in self.cart.items():
            try:
                qty = int(it.get("qty", 0))
            except Exception:
                qty = 0
            if qty > 0:
                items.append({"menu_id": int(menu_id), "qty": qty})

        if not items:
            QMessageBox.information(self, "알림", "장바구니가 비어 있습니다. 먼저 장바구니에 담아주세요.")
            return

        payload = {"rfid_card_id": rfid, "items": items}

        try:
            resp = requests.post(f"{API_BASE_URL}/api/orders", json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            pickup_no = data.get("pickup_no")
            QMessageBox.information(self, "주문 완료", f"주문이 접수되었습니다. 픽업 번호: {pickup_no}")

            # 초기화 및 대기열 갱신
            # 메뉴 테이블의 '추가' 버튼은 그대로 두고, 장바구니만 초기화
            # 주문 성공 후 장바구니 비우기
            try:
                self.on_click_clear_cart()
            except Exception:
                pass
            self.load_queue()
            # 다른 창들(예: AdminScreen)에 재고 갱신을 알림
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

    def on_click_add_to_cart(self):
        """Collect menu rows with qty>0 and add to cart, then update cartTable and total.

        After adding, reset the menuTable qty cell to 0 for those rows.
        """
        # 메뉴 테이블에서 현재 선택된 행을 장바구니에 qty=1로 추가
        row = self.menuTable.currentRow()
        if row < 0:
            QMessageBox.information(self, "알림", "먼저 메뉴를 선택하세요.")
            return
        id_item = self.menuTable.item(row, 0)
        name_item = self.menuTable.item(row, 1)
        price_item = self.menuTable.item(row, 2)
        if id_item is None or name_item is None or price_item is None:
            QMessageBox.information(self, "알림", "선택한 메뉴 정보를 읽을 수 없습니다.")
            return
        try:
            menu_id = int(id_item.text())
            name = name_item.text()
            price = int(price_item.text())
        except Exception:
            QMessageBox.information(self, "알림", "선택한 메뉴의 데이터가 올바르지 않습니다.")
            return

        if menu_id in self.cart:
            self.cart[menu_id]["qty"] += 1
        else:
            self.cart[menu_id] = {"menu_id": menu_id, "name": name, "price": price, "qty": 1}

        self._refresh_cart_ui()

    def _menu_add_clicked(self, menu_id: int, name: str, price: int):
        """Handler for per-menu '추가' button: add qty=1 to cart."""
        if menu_id in self.cart:
            self.cart[menu_id]["qty"] += 1
        else:
            self.cart[menu_id] = {"menu_id": menu_id, "name": name, "price": price, "qty": 1}
        self._refresh_cart_ui()

    def _cart_inc(self, menu_id: int):
        if menu_id in self.cart:
            self.cart[menu_id]["qty"] += 1
            self._refresh_cart_ui()

    def _cart_dec(self, menu_id: int):
        if menu_id in self.cart:
            self.cart[menu_id]["qty"] -= 1
            if self.cart[menu_id]["qty"] <= 0:
                del self.cart[menu_id]
            self._refresh_cart_ui()

    def on_click_clear_cart(self):
        """Empty the cart and refresh UI."""
        self.cart.clear()
        # cartTable의 행을 지움
        if hasattr(self, "cartTable"):
            self.cartTable.setRowCount(0)
        # 총합을 갱신하고 주문 버튼 상태를 업데이트(비활성화)
        try:
            if hasattr(self, "lblTotal"):
                self.lblTotal.setText("총합: 0")
            self.btnOrder.setEnabled(False)
        except Exception:
            pass

    def _refresh_cart_ui(self):
        """Rebuild cartTable from self.cart and update total and order button state."""
        if not hasattr(self, "cartTable"):
            return
        items = list(self.cart.values())
        self.cartTable.setRowCount(len(items))
        total = 0
        for i, it in enumerate(items):
            name_i = QTableWidgetItem(str(it.get("name", "")))
            price_i = QTableWidgetItem(str(it.get("price", 0)))
            qty_i = QTableWidgetItem(str(it.get("qty", 0)))
            subtotal = int(it.get("price", 0)) * int(it.get("qty", 0))
            total += subtotal
            subtotal_i = QTableWidgetItem(str(subtotal))
            self.cartTable.setItem(i, 0, name_i)
            self.cartTable.setItem(i, 1, price_i)
            self.cartTable.setItem(i, 2, qty_i)
            self.cartTable.setItem(i, 3, subtotal_i)
            # 조절 버튼(+/-) 추가
            menu_id = int(it.get("menu_id") or 0)
            control_w = QWidget()
            hl = QHBoxLayout(control_w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(4)
            btn_minus = QPushButton("-")
            btn_plus = QPushButton("+")
            btn_minus.clicked.connect(partial(self._cart_dec, menu_id))
            btn_plus.clicked.connect(partial(self._cart_inc, menu_id))
            hl.addWidget(btn_minus)
            hl.addWidget(btn_plus)
            self.cartTable.setCellWidget(i, 4, control_w)

        # 총합 레이블을 갱신하고 장바구니가 비어있지 않으면 주문 버튼을 활성화
        try:
            if hasattr(self, "lblTotal"):
                self.lblTotal.setText(f"총합: {total}")
            self.btnOrder.setEnabled(total > 0)
        except Exception:
            pass

