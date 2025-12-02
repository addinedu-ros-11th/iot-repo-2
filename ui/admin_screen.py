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


class AdminScreen(QWidget):
    # Signal emitted when the queue is reset so other windows can react
    queue_reset = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "admin_screen.ui")
        uic.loadUi(ui_path, self)

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
        self.btnRestock.clicked.connect(self.on_click_restock)
        self.btnReloadMachine.clicked.connect(self.load_machine_status)
        # Emergency stop / Restart buttons (UI-only handlers)
        if hasattr(self, "btnEmergencyStop"):
            self.btnEmergencyStop.clicked.connect(self.on_click_emergency_stop)
            try:
                # red button for emergency
                self.btnEmergencyStop.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
            except Exception:
                pass
        if hasattr(self, "btnRestartMachine"):
            self.btnRestartMachine.clicked.connect(self.on_click_restart_machine)
            try:
                # blue button for restart
                self.btnRestartMachine.setStyleSheet("background-color: #337ab7; color: white; font-weight: bold;")
            except Exception:
                pass

        # 머신 상태 주기적 갱신 타이머 (3초)
        self.machine_timer = QTimer(self)
        self.machine_timer.timeout.connect(self.load_machine_status)
        self.machine_timer.start(3000)

        # 실시간 대기열 테이블 (OrderScreen과 동일한 컬럼)
        # Ensure queueTable exists (UI might be missing it). If missing, create and append to main layout.
        if not hasattr(self, "queueTable") or self.queueTable is None:
            gb = QGroupBox("실시간 대기열")
            gb_layout = QVBoxLayout()
            qt = QTableWidget()
            qt.setObjectName("queueTable")
            gb_layout.addWidget(qt)
            gb.setLayout(gb_layout)
            # add to the main layout if available
            main_layout = self.layout()
            if main_layout is not None:
                main_layout.addWidget(gb)
            self.queueTable = qt

        self.queueTable.setColumnCount(4)
        # store order_id in hidden column 0 for operations; visible columns shifted by 1
        self.queueTable.setColumnCount(5)
        self.queueTable.setHorizontalHeaderLabels(["ID", "픽업번호", "상태", "주문시각", "ETA(초)"])
        self.queueTable.setColumnHidden(0, True)

        # 대기열 주기적 갱신 타이머 (3초)
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.load_queue)
        self.queue_timer.start(3000)

        # material tx table (log) setup
        if hasattr(self, "materialTxTable"):
            self.materialTxTable.setColumnCount(8)
            self.materialTxTable.setHorizontalHeaderLabels(["ID", "재료ID", "재료명", "주문ID", "타입", "수량변동", "메모", "시간"])
            self.materialTxTable.setColumnHidden(1, False)
            # prefer resizing: show other columns to contents, let '시간' expand
            try:
                header = self.materialTxTable.horizontalHeader()
                for col in range(0, 7):
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
                # last column (시간) should stretch to avoid truncation
                header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
            except Exception:
                pass

        if hasattr(self, "btnReloadMaterialTx"):
            self.btnReloadMaterialTx.clicked.connect(self.load_material_tx)

        # reset button connection (may come from .ui)
        if hasattr(self, "btnResetQueue"):
            self.btnResetQueue.clicked.connect(self.on_click_reset_queue)
        if hasattr(self, "btnCancelSelected"):
            self.btnCancelSelected.clicked.connect(self.on_click_cancel_selected)

        # 초기 로딩
        self.load_materials()
        self.load_machine_status()
        self.load_queue()
        # load material transaction logs
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

            self.materialsTable.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"재고 목록을 불러오지 못했습니다:\n{e}")

    def on_click_restock(self):
        """
        재고 보충/조정.

        요구사항:
        1) self.materialsTable 에서 현재 선택된 row 인덱스 가져오기
           - 선택 없으면 "재고 목록에서 재료를 선택하세요." 메시지
        2) 선택된 row 의 col0 에서 material_id(int) 읽기
        3) self.spinQtyChange.value() 를 qty_change 로 사용
           - 0이면 "변경량이 0입니다." 메시지
        4) self.txtNote.text() 를 note 로 사용 (빈 문자열이면 None)
        5) payload 생성:
           {
             "tx_type": "RESTOCK" if qty_change > 0 else "ADJUST",
             "qty_change": qty_change,
             "note": note_or_none
           }
        6) POST {API_BASE_URL}/api/materials/{material_id}/tx 호출
           - 성공 시 "재고가 변경되었습니다." 메시지
           - 이후 self.load_materials() 다시 호출
        7) 실패 시 QMessageBox 로 에러 표시
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

        qty_change = int(self.spinQtyChange.value())
        if qty_change == 0:
            QMessageBox.information(self, "알림", "변경량이 0입니다.")
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
            # refresh material transaction log so admin sees the new tx immediately
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
                last_hb = row.get("last_heartbeat_at") or ""

                self.machineTable.setItem(i, 0, QTableWidgetItem(str(name)))
                self.machineTable.setItem(i, 1, QTableWidgetItem(str(state)))
                self.machineTable.setItem(i, 2, QTableWidgetItem(str(error)))
                self.machineTable.setItem(i, 3, QTableWidgetItem(str(plate1)))
                self.machineTable.setItem(i, 4, QTableWidgetItem(str(plate2)))
                self.machineTable.setItem(i, 5, QTableWidgetItem(str(conveyor)))
                self.machineTable.setItem(i, 6, QTableWidgetItem(str(last_hb)))
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
                ordered_at = o.get("ordered_at") or ""
                ordered_item = QTableWidgetItem(str(ordered_at))
                eta = QTableWidgetItem(str(o.get("eta_sec", "")))
                # column mapping: 0:order_id(hidden),1:pickup_no,2:status,3:ordered_at,4:eta
                id_item = QTableWidgetItem(str(o.get("order_id", "")))
                self.queueTable.setItem(i, 0, id_item)
                self.queueTable.setItem(i, 1, pickup)

                # create a combobox for status to allow inline editing
                try:
                    combo = QComboBox()
                    statuses = ["PENDING", "COOKING", "DONE", "PICKED_UP", "CANCELED"]
                    combo.addItems(statuses)
                    # set current without emitting signals
                    combo.blockSignals(True)
                    if status_text in statuses:
                        combo.setCurrentText(status_text)
                    else:
                        combo.addItem(status_text)
                        combo.setCurrentText(status_text)
                    combo.setProperty("prev", status_text)
                    # store order id for handler
                    try:
                        combo.setProperty("order_id", int(o.get("order_id") or 0))
                    except Exception:
                        combo.setProperty("order_id", 0)
                    combo.blockSignals(False)
                    # connect handler
                    combo.currentTextChanged.connect(lambda new, c=combo: self.on_status_combo_changed(c, new))
                    self.queueTable.setCellWidget(i, 2, combo)
                except Exception:
                    # fallback to plain item if combobox fails
                    self.queueTable.setItem(i, 2, QTableWidgetItem(status_text))

                self.queueTable.setItem(i, 3, ordered_item)
                self.queueTable.setItem(i, 4, eta)
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
            # reload local view
            self.load_queue()
            # notify other components (e.g., OrderScreen) to refresh
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
                order_i = QTableWidgetItem(str(r.get("order_id", "")))
                ttype_i = QTableWidgetItem(str(r.get("tx_type", "")))
                qty_i = QTableWidgetItem(str(r.get("qty_change", "")))
                note_i = QTableWidgetItem(str(r.get("note", "")))
                created_i = QTableWidgetItem(str(r.get("created_at", "")))

                self.materialTxTable.setItem(i, 0, id_i)
                self.materialTxTable.setItem(i, 1, mid_i)
                self.materialTxTable.setItem(i, 2, mname_i)
                self.materialTxTable.setItem(i, 3, order_i)
                self.materialTxTable.setItem(i, 4, ttype_i)
                self.materialTxTable.setItem(i, 5, qty_i)
                self.materialTxTable.setItem(i, 6, note_i)
                self.materialTxTable.setItem(i, 7, created_i)
        except Exception:
            # ignore periodic UI errors
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
            # success: update prev and refresh related views
            combo.setProperty("prev", new_status)
            try:
                self.load_queue()
            except Exception:
                pass
            try:
                self.load_materials()
            except Exception:
                pass
            try:
                self.load_material_tx()
            except Exception:
                pass
            try:
                self.queue_reset.emit()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "오류", f"상태 변경에 실패했습니다:\n{e}")
            # revert selection
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

        # status might be a QTableWidgetItem (old) or a QComboBox (new)
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
            # refresh local queue view and notify others
            self.load_queue()
            # refresh material stock view so restored quantities are visible
            try:
                self.load_materials()
            except Exception:
                pass
            # refresh material transaction log so RESTOCK entries appear immediately
            try:
                self.load_material_tx()
            except Exception:
                pass
            try:
                self.queue_reset.emit()
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
