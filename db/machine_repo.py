"""
machine_status, machine_event 관련 DB 접근 함수.
"""

from typing import Any


def upsert_machine_status(conn, data: dict[str, Any]) -> None:
    """
    machine_status.name 기준으로 존재하면 UPDATE, 없으면 INSERT.
    """
    sql = """
    INSERT INTO machine_status (
      name,
      state,
      current_order_id,
      last_heartbeat_at,
      plate1_state,
      plate1_temp,
      plate1_sensor_status,
      plate2_state,
      plate2_temp,
      plate2_sensor_status,
      conveyor_state,
      tcrt_status,
      ultrasonic_status,
      error_code
    ) VALUES (
      %(name)s,
      %(state)s,
      %(current_order_id)s,
      NOW(),
      %(plate1_state)s,
      %(plate1_temp)s,
      %(plate1_sensor_status)s,
      %(plate2_state)s,
      %(plate2_temp)s,
      %(plate2_sensor_status)s,
      %(conveyor_state)s,
      %(tcrt_status)s,
      %(ultrasonic_status)s,
      %(error_code)s
    )
    ON DUPLICATE KEY UPDATE
      state = VALUES(state),
      current_order_id = VALUES(current_order_id),
      last_heartbeat_at = NOW(),
      plate1_state = VALUES(plate1_state),
      plate1_temp = VALUES(plate1_temp),
      plate1_sensor_status = VALUES(plate1_sensor_status),
      plate2_state = VALUES(plate2_state),
      plate2_temp = VALUES(plate2_temp),
      plate2_sensor_status = VALUES(plate2_sensor_status),
      conveyor_state = VALUES(conveyor_state),
      tcrt_status = VALUES(tcrt_status),
      ultrasonic_status = VALUES(ultrasonic_status),
      error_code = VALUES(error_code)
    """
    with conn.cursor() as cur:
        cur.execute(sql, data)


def get_machine_by_name(conn, machine_name: str) -> dict | None:
    sql = """
    SELECT *
    FROM machine_status
    WHERE name = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (machine_name,))
        row = cur.fetchone()
    return row


def get_all_machine_status(conn) -> list[dict[str, Any]]:
    sql = "SELECT * FROM machine_status ORDER BY id"
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def insert_machine_event(conn, data: dict[str, Any]) -> int:
    sql = """
    INSERT INTO machine_event (
      machine_id,
      order_id,
      component,
      event_type,
      event_code,
      temp,
      message,
      created_at
    ) VALUES (
      %(machine_id)s,
      %(order_id)s,
      %(component)s,
      %(event_type)s,
      %(event_code)s,
      %(temp)s,
      %(message)s,
      NOW()
    )
    """
    with conn.cursor() as cur:
        cur.execute(sql, data)
        return cur.lastrowid


def update_machine_error_state(conn, machine_name: str, error_code: str, new_state: str) -> int:
    """
    머신 에러/상태 값을 한 번에 바꾸는 업데이트.
    """
    sql = """
    UPDATE machine_status
    SET error_code = %s,
        state = %s
    WHERE name = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (error_code, new_state, machine_name))
        return cur.rowcount
