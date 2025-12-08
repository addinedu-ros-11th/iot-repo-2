"""
머신 상태/이벤트 관련 비즈니스 로직.
"""

from typing import Any
from datetime import datetime

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


def emergency_stop_machine(conn, machine_id: int) -> dict[str, Any]:
    """
    머신을 비상정지 상태로 변경.
    """
    try:
        sql = "UPDATE machine_status SET state = %s, error_code = %s WHERE id = %s"
        with conn.cursor() as cur:
            cur.execute(sql, ("EMERGENCY_STOP", "EMERGENCY_STOP", machine_id))
            affected = cur.rowcount
        
        if affected == 0:
            raise RuntimeError("MACHINE_NOT_FOUND")
        
        conn.commit()
        return {"ok": True, "message": "머신이 비상정지되었습니다."}
    except Exception as e:
        print(f"[machine_service] 비상정지 중 오류: {e}")
        raise


def restore_machine_state(conn, machine_id: int) -> dict[str, Any]:
    """
    비상정지된 머신을 IDLE 상태로 복구.
    """
    try:
        sql = "UPDATE machine_status SET state = %s, error_code = %s WHERE id = %s"
        with conn.cursor() as cur:
            cur.execute(sql, ("IDLE", "NONE", machine_id))
            affected = cur.rowcount
        
        if affected == 0:
            raise RuntimeError("MACHINE_NOT_FOUND")
        
        conn.commit()
        return {"ok": True, "message": "머신이 IDLE 상태로 복구되었습니다."}
    except Exception as e:
        print(f"[machine_service] 복구 중 오류: {e}")
        raise


def _ensure_machine_id(conn, machine_name: str) -> int:
    """
    machine_status 에서 name 기준으로 id를 얻는다.
    """
    row = machine_repo.get_machine_by_name(conn, machine_name)
    if row is not None:
        return row["id"]

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

    if req.event_code == enums.EVENT_ORDER_DONE and req.order_id:
        order_repo.update_order_status(conn, req.order_id, enums.ORDER_STATUS_DONE)

    elif req.event_code == enums.EVENT_PICKUP_DETECTED and req.order_id:
        order_repo.update_order_status(conn, req.order_id, enums.ORDER_STATUS_PICKED_UP)

    if req.event_code == enums.EVENT_OVERHEAT:
        machine_repo.update_machine_error_state(
            conn,
            machine_name=req.machine_name,
            error_code=enums.EVENT_OVERHEAT,
            new_state=enums.MACHINE_STATE_EMERGENCY_STOP,
        )

    conn.commit()
    return {"ok": True}

def get_next_order_for_machine(conn) -> dict | None:
    """
    현재 기계가 처리해야 할 다음 주문 1건 반환
    기준:
    - orders.status = 'PENDING'
    - 가장 먼저 들어온 주문 (ordered_at ASC)
    """

    sql = """
    SELECT 
        o.id AS order_id,
        o.pickup_no,
        o.status,
        o.ordered_at,
        SUM(od.qty) AS total_qty
    FROM orders o
    JOIN order_detail od ON od.order_id = o.id
    WHERE o.status = 'PENDING'
    GROUP BY o.id, o.pickup_no, o.status, o.ordered_at
    ORDER BY o.ordered_at ASC
    LIMIT 1
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    if not row:
        return None   # ✅ 주문 없을 때

    return {
        "order_id": row["order_id"],
        "pickup_no": row["pickup_no"],
        "status": row["status"],
        "total_qty": int(row["total_qty"]),
        "ordered_at": row["ordered_at"].isoformat() if row["ordered_at"] else None,
    }
