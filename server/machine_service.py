"""
머신 상태/이벤트 관련 비즈니스 로직.
"""

from typing import Any

from common import enums
from db import machine_repo, order_repo
from server import models


def update_machine_status(conn, req: models.MachineStatusIn) -> dict[str, Any]:
    """
    machine_status 테이블 upsert.
    """
    data = {
        "name": req.machine_name,
        "state": req.state,
        "current_order_id": req.current_order_id,
        "plate1_state": req.plate1_state,
        "plate1_temp": req.plate1_temp,
        "plate1_sensor_status": req.plate1_sensor_status,
        "plate2_state": req.plate2_state,
        "plate2_temp": req.plate2_temp,
        "plate2_sensor_status": req.plate2_sensor_status,
        "conveyor_state": req.conveyor_state,
        "tcrt_status": req.tcrt_status,
        "ultrasonic_status": req.ultrasonic_status,
        "error_code": req.error_code,
    }

    machine_repo.upsert_machine_status(conn, data)
    conn.commit()
    return {"ok": True}


def get_machine_status(conn) -> list[dict[str, Any]]:
    """
    모든 머신 상태를 반환.
    """
    rows = machine_repo.get_all_machine_status(conn)
    # datetime을 문자열로 바꿔주는 정도만 처리
    for row in rows:
        if row.get("last_heartbeat_at"):
            row["last_heartbeat_at"] = row["last_heartbeat_at"].isoformat()
    return rows


def _ensure_machine_id(conn, machine_name: str) -> int:
    """
    machine_status 에서 name 기준으로 id를 얻는다.
    없으면 기본 상태로 하나 만들어서 id를 반환한다.
    """
    row = machine_repo.get_machine_by_name(conn, machine_name)
    if row is not None:
        return row["id"]

    # 없으면 기본값으로 생성
    default_data = {
        "name": machine_name,
        "state": enums.MACHINE_STATE_IDLE,
        "current_order_id": None,
        "plate1_state": enums.PLATE_STATE_IDLE,
        "plate1_temp": None,
        "plate1_sensor_status": enums.SENSOR_STATUS_OK,
        "plate2_state": enums.PLATE_STATE_IDLE,
        "plate2_temp": None,
        "plate2_sensor_status": enums.SENSOR_STATUS_OK,
        "conveyor_state": "IDLE",
        "tcrt_status": enums.SIMPLE_SENSOR_OK,
        "ultrasonic_status": enums.SIMPLE_SENSOR_OK,
        "error_code": "NONE",
    }
    machine_repo.upsert_machine_status(conn, default_data)
    row = machine_repo.get_machine_by_name(conn, machine_name)
    if row is None:
        raise RuntimeError("FAILED_TO_CREATE_MACHINE_STATUS")
    return row["id"]


def handle_machine_event(conn, req: models.MachineEventIn) -> dict[str, Any]:
    """
    machine_event INSERT + 주문/머신 상태 반영.

    이벤트 처리 규칙:
    - ORDER_DONE:
        해당 order_id 의 상태를 DONE 으로 변경
    - PICKUP_DETECTED:
        해당 order_id 의 상태를 PICKED_UP 으로 변경
    - OVERHEAT:
        machine_status.error_code = OVERHEAT,
        machine_status.state = EMERGENCY_STOP
    - 그 외 이벤트:
        로그만 남기고 추가 동작 없음
    """
    machine_id = _ensure_machine_id(conn, req.machine_name)

    data = {
        "machine_id": machine_id,
        "order_id": req.order_id,
        "component": req.component,
        "event_type": req.event_type,
        "event_code": req.event_code,
        "temp": req.temp,
        "message": req.message,
    }
    machine_repo.insert_machine_event(conn, data)

    # 주문 상태 반영
    if req.event_code == enums.EVENT_ORDER_DONE and req.order_id:
        order_repo.update_order_status(conn, req.order_id, enums.ORDER_STATUS_DONE)

    elif req.event_code == enums.EVENT_PICKUP_DETECTED and req.order_id:
        order_repo.update_order_status(conn, req.order_id, enums.ORDER_STATUS_PICKED_UP)

    # 머신 에러/비상 정지 반영
    if req.event_code == enums.EVENT_OVERHEAT:
        machine_repo.update_machine_error_state(
            conn,
            machine_name=req.machine_name,
            error_code=enums.EVENT_OVERHEAT,
            new_state=enums.MACHINE_STATE_EMERGENCY_STOP,
        )

    conn.commit()
    return {"ok": True}
