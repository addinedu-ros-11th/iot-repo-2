"""
FastAPI 요청/응답에서 사용하는 Pydantic 모델.
"""

from typing import List, Optional

from pydantic import BaseModel


# ===== 주문 =====

class OrderItemCreate(BaseModel):
    menu_id: int
    qty: int


class OrderCreate(BaseModel):
    rfid_card_id: str
    items: List[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: str  # "CANCELED" 등


# ===== 재고 / 재고 Tx =====

class MaterialTxCreate(BaseModel):
    tx_type: str   # RESTOCK / CONSUME / ADJUST
    qty_change: int
    note: Optional[str] = None


# ===== 머신 상태 =====

class MachineStatusIn(BaseModel):
    machine_name: str

    state: str
    current_order_id: Optional[int] = None

    plate1_state: str
    plate1_temp: Optional[int] = None
    plate1_sensor_status: str

    plate2_state: str
    plate2_temp: Optional[int] = None
    plate2_sensor_status: str

    conveyor_state: str
    tcrt_status: str
    ultrasonic_status: str

    error_code: str


# ===== 머신 이벤트 =====

class MachineEventIn(BaseModel):
    machine_name: str
    order_id: Optional[int] = None

    component: str
    event_type: str
    event_code: str

    temp: Optional[int] = None
    message: Optional[str] = None
