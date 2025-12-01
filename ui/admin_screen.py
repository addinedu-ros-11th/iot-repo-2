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
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget

from config import API_BASE_URL


class AdminScreen(QWidget):
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

        # 머신 상태 주기적 갱신 타이머 (3초)
        self.machine_timer = QTimer(self)
        self.machine_timer.timeout.connect(self.load_machine_status)
        self.machine_timer.start(3000)

        # 초기 로딩
        self.load_materials()
        self.load_machine_status()

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
        # TODO
        raise NotImplementedError("AdminScreen.load_materials 구현 필요")

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
        # TODO
        raise NotImplementedError("AdminScreen.on_click_restock 구현 필요")

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
        # TODO
        raise NotImplementedError("AdminScreen.load_machine_status 구현 필요")
