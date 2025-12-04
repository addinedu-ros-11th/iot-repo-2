"""
관리자 화면.

admin_screen.ui 에서 다음 위젯 이름을 사용한다고 가정한다:

[재고]
- self.materialsTable      : QTableWidget
    - 컬럼: 0:id(숨김), 1:재료명, 2:단위, 3:수량
- self.btnReloadMaterials  : QPushButton (재고 새로고침)
- self.spinQtyChange       : QSpinBox (입고/조정 수량)
- self.txtNote             : QLineEdit (메모)
- self.btnRestock          : QPushButton (선택 재료에 qty_change 적용)

[머신 상태]
- self.machineTable        : QTableWidget
    - 컬럼 예: 0:이름, 1:상태, 2:에러, 3:plate1, 4:plate2, 5:conveyor, 6:last_heartbeat
- self.btnReloadMachine    : QPushButton (머신 상태 새로고침)

API:
- GET  {API_BASE_URL}/api/materials
- POST {API_BASE_URL}/api/materials/{material_id}/tx
- GET  {API_BASE_URL}/api/machine/status
"""

import os

from PyQt6 import uic
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QTableWidgetItem,
    QTableWidget,
    QGroupBox,
    QVBoxLayout,
    QHeaderView,
    QComboBox,
)
import requests

from config import API_BASE_URL
from common.timeutils import format_utc_to_local


class AdminScreen(QWidget):
    # 대기열이 초기화되었을 때 다른 창이 반응할 수 있도록 발생시키는 신호
    queue_reset = pyqtSignal()
    # 주문 상태 변경/취소 시 발생하는 신호 (재고/로그 갱신용)
    order_changed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "admin_screen.ui")
        uic.loadUi(ui_path, self)

        # 관리자 화면 붕어빵 테마 스타일 적용
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5DC;
                font-family: 'Malgun Gothic', 'AppleGothic', sans-serif;
                font-size: 11pt;
            }
            QGroupBox {
                background-color: #FAEBD7;
                border: 2px solid #8B4513;
                border-radius: 8px;
                margin-top: 10px;
                padding: 12px;
                font-weight: bold;
                font-size: 12pt;
                color: #654321;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                background-color: #8B4513;
                color: white;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #A0522D;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 11pt;
                font-weight: bold;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #BC8F8F;
            }
            QPushButton:pressed {
                background-color: #8B4513;
            }
            QPushButton#btnRestock {
                background-color: #228B22;
            }
            QPushButton#btnRestock:hover {
                background-color: #32CD32;
            }
            QPushButton#btnEmergencyStop {
                background-color: #DC143C;
                font-size: 12pt;
            }
            QPushButton#btnEmergencyStop:hover {
                background-color: #FF0000;
            }
            QPushButton#btnRestartMachine {
                background-color: #4169E1;
            }
            QPushButton#btnRestartMachine:hover {
                background-color: #6495ED;
            }
            QPushButton#btnCancelSelected {
                background-color: #CD5C5C;
            }
            QPushButton#btnResetQueue {
                background-color: #FF6347;
            }
            QTableWidget {
                background-color: white;
                border: 2px solid #8B4513;
                border-radius: 4px;
                gridline-color: #DEB887;
                font-size: 10pt;
            }
            QTableWidget::item {
                padding: 10px 6px;
                min-height: 30px;
            }
            QTableWidget::item:selected {
                background-color: #F4A460;
                color: white;
            }
            QHeaderView::section {
                background-color: #A0522D;
                color: white;
                padding: 10px 6px;
                border: 1px solid #8B4513;
                font-weight: bold;
                font-size: 10pt;
                min-height: 35px;
            }
            QLineEdit {
                background-color: white;
                border: 2px solid #8B4513;
                border-radius: 4px;
                padding: 6px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 2px solid #A0522D;
            }
            QSpinBox {
                background-color: white;
                border: 2px solid #8B4513;
                border-radius: 4px;
                padding: 4px;
                font-size: 11pt;
                min-height: 30px;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #8B4513;
                background-color: #A0522D;
            }
            QSpinBox::up-button:hover {
                background-color: #BC8F8F;
            }
            QSpinBox::up-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid white;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid #8B4513;
                background-color: #A0522D;
            }
            QSpinBox::down-button:hover {
                background-color: #BC8F8F;
            }
            QSpinBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid white;
            }
            QComboBox {
                background-color: white;
                border: 2px solid #8B4513;
                border-radius: 4px;
                padding: 4px;
                font-size: 10pt;
            }
            QComboBox:hover {
                border: 2px solid #A0522D;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #D2691E;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid white;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #8B4513;
                selection-background-color: #F4A460;
                selection-color: #654321;
                color: #654321;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #DEB887;
                color: #654321;
            }
            QLabel {
                color: #654321;
                font-size: 11pt;
            }
            QTabWidget::pane {
                border: 2px solid #8B4513;
                border-radius: 4px;
                background-color: #FAEBD7;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #D2B48C;
                color: #654321;
                border: 2px solid #8B4513;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 20px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11pt;
            }
            QTabBar::tab:selected {
                background-color: #FAEBD7;
                color: #8B4513;
                border-bottom: 2px solid #FAEBD7;
            }
            QTabBar::tab:hover {
                background-color: #DEB887;
            }
        """)

        # 재고 테이블 컬럼 구조
        self.materialsTable.setColumnCount(4)
        self.materialsTable.setHorizontalHeaderLabels(["ID", "재료명", "단위", "수량"])
        self.materialsTable.setColumnHidden(0, True)

        # 머신 상태 테이블 컬럼 구조
        self.machineTable.setColumnCount(7)
        self.machineTable.setHorizontalHeaderLabels(
            ["이름", "상태", "에러", "plate1", "plate2", "conveyor", "last_heartbeat"]
        )

        # 버튼 시그널 연결
        self.btnReloadMaterials.clicked.connect(self.load_materials)
        if hasattr(self, "btnIncreaseQty"):
            self.btnIncreaseQty.clicked.connect(self.on_click_increase_qty)
        if hasattr(self, "btnDecreaseQty"):
            self.btnDecreaseQty.clicked.connect(self.on_click_decrease_qty)
        self.btnReloadMachine.clicked.connect(self.load_machine_status)
        # 비상정지 / 재시작 버튼 (UI 전용 핸들러)
        if hasattr(self, "btnEmergencyStop"):
            self.btnEmergencyStop.clicked.connect(self.on_click_emergency_stop)
            try:
                # 비상용 빨간 버튼
                self.btnEmergencyStop.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
            except Exception:
                pass
        if hasattr(self, "btnRestartMachine"):
            self.btnRestartMachine.clicked.connect(self.on_click_restart_machine)
            try:
                # 재시작용 파란 버튼
                self.btnRestartMachine.setStyleSheet("background-color: #337ab7; color: white; font-weight: bold;")
            except Exception:
                pass

        # 머신 상태 주기적 갱신 타이머 (3초)
        self.machine_timer = QTimer(self)
        self.machine_timer.timeout.connect(self.load_machine_status)
        self.machine_timer.start(3000)

        # 실시간 대기열 테이블 (OrderScreen과 동일한 컬럼)
        # queueTable이 존재하는지 확인 (UI에 없을 수 있음). 없으면 생성하여 메인 레이아웃에 추가
        if not hasattr(self, "queueTable") or self.queueTable is None:
            gb = QGroupBox("실시간 대기열")
            gb_layout = QVBoxLayout()
            qt = QTableWidget()
            qt.setObjectName("queueTable")
            gb_layout.addWidget(qt)
            gb.setLayout(gb_layout)
            # 가능한 경우 메인 레이아웃에 추가
            main_layout = self.layout()
            if main_layout is not None:
                main_layout.addWidget(gb)
            self.queueTable = qt

        self.queueTable.setColumnCount(4)
        # 작업용으로 숨긴 컬럼 0에 order_id를 저장; 표시되는 컬럼은 1씩 밀림
        self.queueTable.setColumnCount(5)
        self.queueTable.setHorizontalHeaderLabels(["ID", "픽업번호", "상태", "주문시각", "ETA(초)"])
        self.queueTable.setColumnHidden(0, True)

        # 대기열 주기적 갱신 타이머 (3초)
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.load_queue)
        self.queue_timer.start(3000)

        # 재료 트랜잭션 테이블(로그) 설정
        if hasattr(self, "materialTxTable"):
            self.materialTxTable.setColumnCount(8)
            self.materialTxTable.setHorizontalHeaderLabels(["ID", "재료ID", "재료명", "주문ID", "타입", "수량변동", "메모", "시간"])
            self.materialTxTable.setColumnHidden(1, False)
            # 컬럼 크기 조정: 다른 컬럼은 내용에 맞게, '시간' 컬럼은 확장
            try:
                header = self.materialTxTable.horizontalHeader()
                for col in range(0, 7):
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
                # 마지막 컬럼('시간')은 잘림을 피하기 위해 확장하도록 설정
                header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
            except Exception:
                pass

        if hasattr(self, "btnReloadMaterialTx"):
            self.btnReloadMaterialTx.clicked.connect(self.load_material_tx)

        # 초기화 버튼 연결 (.ui에서 생성되었을 수 있음)
        if hasattr(self, "btnResetQueue"):
            self.btnResetQueue.clicked.connect(self.on_click_reset_queue)
        if hasattr(self, "btnCancelSelected"):
            self.btnCancelSelected.clicked.connect(self.on_click_cancel_selected)

        # 주문 변경 신호 연결 (재고/로그 갱신)
        self.order_changed.connect(self._on_order_changed)

        # 초기 로딩
        self.load_materials()
        self.load_machine_status()
        self.load_queue()
        # 재료 트랜잭션 로그 로드
        try:
            self.load_material_tx()
        except Exception:
            pass

    def _on_order_changed(self):
        """주문 상태 변경/취소 시 호출되는 슬롯"""
        try:
            self.load_materials()
        except Exception:
            pass
        try:
            self.load_material_tx()
        except Exception:
            pass

    def load_materials(self):
        """
        재고 목록 로딩.

        요구사항:
        1) GET {API_BASE_URL}/api/materials 호출
           - 응답: [
               { "id": int, "name": str, "unit": str, "qty": int },
               ...
             ]
        2) self.materialsTable row 개수를 응답 길이만큼 설정
        3) 각 row:
           - col0: id (문자열, 숨김)
           - col1: name
           - col2: unit
           - col3: qty
        4) self.materialsTable.resizeColumnsToContents() 호출
        5) 실패 시 QMessageBox 로 에러 표시
        """
        try:
            resp = requests.get(f"{API_BASE_URL}/api/materials", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.materialsTable.setRowCount(len(data))
            for i, item in enumerate(data):
                id_item = QTableWidgetItem(str(item.get("id", "")))
                name_item = QTableWidgetItem(item.get("name", ""))
                unit_item = QTableWidgetItem(item.get("unit", ""))
                qty_item = QTableWidgetItem(str(item.get("qty", "")))

                self.materialsTable.setItem(i, 0, id_item)
                self.materialsTable.setItem(i, 1, name_item)
                self.materialsTable.setItem(i, 2, unit_item)
                self.materialsTable.setItem(i, 3, qty_item)

            self.materialsTable.resizeRowsToContents()
            self.materialsTable.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"재고 목록을 불러오지 못했습니다:\n{e}")

    def on_click_increase_qty(self):
        """
        재고 증가 (spinQtyChange 값만큼).
        """
        qty = int(self.spinQtyChange.value())
        self._apply_qty_change(qty)

    def on_click_decrease_qty(self):
        """
        재고 감소 (spinQtyChange 값만큼).
        """
        qty = int(self.spinQtyChange.value())
        self._apply_qty_change(-qty)

    def _apply_qty_change(self, qty_change: int):
        """
        선택된 재료의 재고를 qty_change만큼 변경.

        요구사항:
        1) self.materialsTable 에서 현재 선택된 row 인덱스 가져오기
           - 선택 없으면 "재고 목록에서 재료를 선택하세요." 메시지
        2) 선택된 row 의 col0 에서 material_id(int) 읽기
        3) self.txtNote.text() 를 note 로 사용 (빈 문자열이면 None)
        4) payload 생성:
           {
             "tx_type": "RESTOCK" if qty_change > 0 else "ADJUST",
             "qty_change": qty_change,
             "note": note_or_none
           }
        5) POST {API_BASE_URL}/api/materials/{material_id}/tx 호출
           - 성공 시 "재고가 변경되었습니다." 메시지
           - 이후 self.load_materials() 다시 호출
        6) 실패 시 QMessageBox 로 에러 표시
        """
        row = self.materialsTable.currentRow()
        if row is None or row < 0:
            QMessageBox.warning(self, "알림", "재고 목록에서 재료를 선택하세요.")
            return

        id_item = self.materialsTable.item(row, 0)
        if id_item is None:
            QMessageBox.warning(self, "알림", "선택한 항목의 ID를 찾을 수 없습니다.")
            return

        try:
            material_id = int(id_item.text())
        except Exception:
            QMessageBox.warning(self, "알림", "유효한 재료 ID가 아닙니다.")
            return

        note_text = self.txtNote.text().strip()
        note = note_text if note_text != "" else None

        payload = {
            "tx_type": "RESTOCK" if qty_change > 0 else "ADJUST",
            "qty_change": qty_change,
            "note": note,
        }

        try:
            resp = requests.post(f"{API_BASE_URL}/api/materials/{material_id}/tx", json=payload, timeout=5)
            resp.raise_for_status()
            QMessageBox.information(self, "완료", "재고가 변경되었습니다.")
            self.load_materials()
            # 재료 트랜잭션 로그를 새로고침하여 관리자가 트랜잭션을 즉시 볼 수 있도록 함
            try:
                self.load_material_tx()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "오류", f"재고 변경에 실패했습니다:\n{e}")

    def load_machine_status(self):
        """
        머신 상태 로딩.

        요구사항:
        1) GET {API_BASE_URL}/api/machine/status 호출
           - 응답: machine_status 테이블 row 리스트
             각 row는 예를 들면:
             {
               "id": 1,
               "name": "MAIN_MACHINE",
               "state": "RUNNING",
               "error_code": "NONE",
               "plate1_state": "...",
               "plate1_temp": 180,
               "plate2_state": "...",
               "plate2_temp": 30,
               "conveyor_state": "...",
               "last_heartbeat_at": "2025-01-01T12:34:56",
               ...
             }
        2) self.machineTable row 개수를 응답 길이만큼 설정
        3) 각 row:
           - col0: name
           - col1: state
           - col2: error_code
           - col3: f"{plate1_state}/{plate1_temp}"
           - col4: f"{plate2_state}/{plate2_temp}"
           - col5: conveyor_state
           - col6: last_heartbeat_at 문자열 (없으면 빈 문자열)
        4) 실패 시 조용히 무시하거나, 필요하면 메시지 박스로 알려도 된다.
        """
        try:
            resp = requests.get(f"{API_BASE_URL}/api/machine/status", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.machineTable.setRowCount(len(data))
            for i, row in enumerate(data):
                name = row.get("name", "")
                state = row.get("state", "")
                error = row.get("error_code", "")

                plate1_state = row.get("plate1_state", "")
                plate1_temp = row.get("plate1_temp")
                plate1 = f"{plate1_state}/{plate1_temp}" if plate1_temp is not None else plate1_state

                plate2_state = row.get("plate2_state", "")
                plate2_temp = row.get("plate2_temp")
                plate2 = f"{plate2_state}/{plate2_temp}" if plate2_temp is not None else plate2_state

                conveyor = row.get("conveyor_state", "")
                last_hb = format_utc_to_local(row.get("last_heartbeat_at"))

                self.machineTable.setItem(i, 0, QTableWidgetItem(str(name)))
                self.machineTable.setItem(i, 1, QTableWidgetItem(str(state)))
                self.machineTable.setItem(i, 2, QTableWidgetItem(str(error)))
                self.machineTable.setItem(i, 3, QTableWidgetItem(str(plate1)))
                self.machineTable.setItem(i, 4, QTableWidgetItem(str(plate2)))
                self.machineTable.setItem(i, 5, QTableWidgetItem(str(conveyor)))
                self.machineTable.setItem(i, 6, QTableWidgetItem(str(last_hb)))
            
            self.machineTable.resizeRowsToContents()
            self.machineTable.resizeColumnsToContents()
        except Exception:
            # 조용히 무시 (UI 주기 갱신 중 에러가 발생해도 사용자에게 계속 방해하지 않음)
            return

    def load_queue(self):
        """
        관리자 화면용 실시간 대기열 로딩 (order_screen과 동일 동작).
        GET {API_BASE_URL}/api/orders/queue
        응답 각 row: { pickup_no, status, ordered_at, eta_sec }
        실패 시 조용히 무시.
        """
        try:
            resp = requests.get(f"{API_BASE_URL}/api/orders/queue", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.queueTable.setRowCount(len(data))
            for i, o in enumerate(data):
                pickup = QTableWidgetItem(str(o.get("pickup_no", "")))
                status_text = str(o.get("status", ""))
                ordered_at = o.get("ordered_at")
                ordered_item = QTableWidgetItem(format_utc_to_local(ordered_at))
                eta = QTableWidgetItem(str(o.get("eta_sec", "")))
                # 컬럼 매핑: 0:order_id(숨김),1:pickup_no,2:status,3:ordered_at,4:eta
                id_item = QTableWidgetItem(str(o.get("order_id", "")))
                self.queueTable.setItem(i, 0, id_item)
                self.queueTable.setItem(i, 1, pickup)

                # 인라인 편집을 허용하기 위해 상태용 콤보박스 생성
                try:
                    combo = QComboBox()
                    statuses = ["PENDING", "COOKING", "DONE", "PICKED_UP", "CANCELED"]
                    combo.addItems(statuses)
                    # 신호를 발생시키지 않고 현재값 설정
                    combo.blockSignals(True)
                    if status_text in statuses:
                        combo.setCurrentText(status_text)
                    else:
                        combo.addItem(status_text)
                        combo.setCurrentText(status_text)
                    combo.setProperty("prev", status_text)
                    # 핸들러를 위해 order id를 속성에 저장
                    try:
                        combo.setProperty("order_id", int(o.get("order_id") or 0))
                    except Exception:
                        combo.setProperty("order_id", 0)
                    combo.blockSignals(False)
                    # 핸들러 연결
                    combo.currentTextChanged.connect(lambda new, c=combo: self.on_status_combo_changed(c, new))
                    self.queueTable.setCellWidget(i, 2, combo)
                except Exception:
                    # 콤보박스 생성에 실패하면 일반 아이템으로 대체
                    self.queueTable.setItem(i, 2, QTableWidgetItem(status_text))

                self.queueTable.setItem(i, 3, ordered_item)
                self.queueTable.setItem(i, 4, eta)
            
            self.queueTable.resizeRowsToContents()
            self.queueTable.resizeColumnsToContents()
        except Exception:
            # 주기적 갱신 중 에러는 조용히 무시
            return
    def on_click_reset_queue(self):
        """관리자 UI에서 대기열 초기화 버튼 핸들러
        확인 대화상자 후 DELETE /api/orders/queue 호출하고 결과를 알림
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
            # Signal emission (timer will auto-refresh)
            try:
                self.queue_reset.emit()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "오류", f"대기열 초기화에 실패했습니다:\n{e}")

    def load_material_tx(self):
        """
        재료 입출고 로그 로딩.
        GET {API_BASE_URL}/api/materials/txs
        컬럼: id, material_id, material_name, order_id, tx_type, qty_change, note, created_at
        """
        try:
            resp = requests.get(f"{API_BASE_URL}/api/materials/txs", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.materialTxTable.setRowCount(len(data))
            for i, r in enumerate(data):
                id_i = QTableWidgetItem(str(r.get("id", "")))
                mid_i = QTableWidgetItem(str(r.get("material_id", "")))
                mname_i = QTableWidgetItem(str(r.get("material_name", "")))
                
                # order_id가 None이면 빈 문자열로 표시
                order_id_val = r.get("order_id")
                order_i = QTableWidgetItem("" if order_id_val is None else str(order_id_val))
                
                ttype_i = QTableWidgetItem(str(r.get("tx_type", "")))
                qty_i = QTableWidgetItem(str(r.get("qty_change", "")))
                
                # note가 None이면 빈 문자열로 표시
                note_val = r.get("note")
                note_i = QTableWidgetItem("" if note_val is None else str(note_val))
                
                created_i = QTableWidgetItem(format_utc_to_local(r.get("created_at")))

                self.materialTxTable.setItem(i, 0, id_i)
                self.materialTxTable.setItem(i, 1, mid_i)
                self.materialTxTable.setItem(i, 2, mname_i)
                self.materialTxTable.setItem(i, 3, order_i)
                self.materialTxTable.setItem(i, 4, ttype_i)
                self.materialTxTable.setItem(i, 5, qty_i)
                self.materialTxTable.setItem(i, 6, note_i)
                self.materialTxTable.setItem(i, 7, created_i)
            
            # 행 높이만 조정 (컬럼 너비는 초기화 시 설정한 ResizeMode 유지)
            self.materialTxTable.resizeRowsToContents()
        except Exception:
            # 주기적으로 발생하는 UI 오류는 무시
            return

    def on_status_combo_changed(self, combo, new_status: str):
        """Handle inline status change from combobox in the queue table.

        If change fails, revert the combobox to previous value.
        """
        try:
            order_id = int(combo.property("order_id") or 0)
        except Exception:
            QMessageBox.warning(self, "오류", "주문 ID를 읽을 수 없습니다.")
            return

        prev = combo.property("prev") or ""
        if new_status == prev:
            return

        try:
            resp = requests.patch(f"{API_BASE_URL}/api/admin/orders/{order_id}/status", json={"status": new_status}, timeout=10)
            resp.raise_for_status()
            # Success: update previous value
            combo.setProperty("prev", new_status)
            # Timer will auto-refresh, just emit signals
            try:
                self.queue_reset.emit()
                self.order_changed.emit()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "오류", f"상태 변경에 실패했습니다:\n{e}")
            # 선택 복원
            try:
                combo.blockSignals(True)
                combo.setCurrentText(prev)
                combo.blockSignals(False)
            except Exception:
                pass

    def on_click_cancel_selected(self):
        """Cancel (set CANCELED) the selected order in the queue (only allowed for PENDING)."""
        row = self.queueTable.currentRow()
        if row is None or row < 0:
            QMessageBox.warning(self, "알림", "취소할 주문을 선택하세요.")
            return

        id_item = self.queueTable.item(row, 0)
        pickup_item = self.queueTable.item(row, 1)
        status_item = self.queueTable.item(row, 2)
        if id_item is None:
            QMessageBox.warning(self, "알림", "선택한 행에 주문 ID가 없습니다.")
            return

        try:
            order_id = int(id_item.text())
        except Exception:
            QMessageBox.warning(self, "알림", "유효한 주문 ID가 아닙니다.")
            return

        # status는 이전에는 QTableWidgetItem, 새 버전에서는 QComboBox일 수 있음
        status = ""
        try:
            status_widget = self.queueTable.cellWidget(row, 2)
            if status_widget is not None and hasattr(status_widget, "currentText"):
                status = status_widget.currentText()
            else:
                status = status_item.text() if status_item is not None else ""
        except Exception:
            status = status_item.text() if status_item is not None else ""
        if status != "PENDING":
            QMessageBox.information(self, "알림", "선택한 주문은 취소할 수 없습니다 (PENDING 상태만 취소 가능).")
            return

        reply = QMessageBox.question(
            self,
            "주문 취소",
            f"픽업번호 {pickup_item.text() if pickup_item is not None else ''} 주문을 취소하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            resp = requests.patch(f"{API_BASE_URL}/api/orders/{order_id}/status", json={"status": "CANCELED"}, timeout=10)
            resp.raise_for_status()
            QMessageBox.information(self, "완료", "주문이 취소되었습니다.")
            # Signal emission (timer will auto-refresh, materials/logs updated)
            try:
                self.queue_reset.emit()
                self.order_changed.emit()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "오류", f"주문 취소에 실패했습니다:\n{e}")

    def on_click_emergency_stop(self):
        """Show a warning indicating emergency stop was triggered. Actual emergency logic is left unimplemented."""
        QMessageBox.warning(self, "비상정지", "비상정지가 실행되었습니다. (기능 미구현)")

    def on_click_restart_machine(self):
        """Show an alert indicating a restart was triggered. Actual restart logic is left unimplemented."""
        QMessageBox.information(self, "재가동", "머신 재가동이 실행되었습니다. (기능 미구현)")
