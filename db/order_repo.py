# db/order_repo.py
"""
menu, orders, order_detail 관련 DB 접근 함수.
비즈니스 로직은 server/order_service.py 에서 처리한다.
"""

from typing import Any, Iterable


def get_menu_list(conn) -> list[dict[str, Any]]:
    sql = """
    SELECT id, code, name, price, cook_time_sec
    FROM menu
    ORDER BY id
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


def get_next_pickup_no_for_today(conn) -> int:
    """
    오늘 날짜 기준으로 pickup_no의 최대값을 구하고 +1 해서 반환.
    오늘 주문이 하나도 없으면 101을 반환한다.
    기준: orders.ordered_at 의 DATE 값.
    """
    sql = """
    SELECT COALESCE(MAX(pickup_no), 100) AS last_no
    FROM orders
    WHERE DATE(ordered_at) = CURDATE()
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        last_no = row["last_no"] if row is not None else 100
    return last_no + 1  # 처음이면 101, 그 다음 102 ...


def insert_order(
    conn,
    pickup_no: int,
    rfid_card_id: str,
    status: str,
) -> int:
    """
    orders 테이블에 1건 INSERT 후, 생성된 order_id 반환.
    ordered_at 은 DB 서버 시간(NOW) 기준.
    """
    sql = """
    INSERT INTO orders (pickup_no, rfid_card_id, status, ordered_at)
    VALUES (%s, %s, %s, NOW())
    """
    with conn.cursor() as cur:
        cur.execute(sql, (pickup_no, rfid_card_id, status))
        order_id = cur.lastrowid
    return order_id


def insert_order_items(
    conn,
    order_id: int,
    items: Iterable[tuple[int, int]],
):
    """
    order_detail 테이블에 여러 건 INSERT.
    items: [(menu_id, qty), ...]
    """
    sql = """
    INSERT INTO order_detail (order_id, menu_id, qty)
    VALUES (%s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.executemany(
            sql,
            [(order_id, menu_id, qty) for (menu_id, qty) in items],
        )


def get_order_by_id(conn, order_id: int) -> dict | None:
    """
    단일 주문 기본 정보 조회.
    """
    sql = """
    SELECT id AS order_id,
           pickup_no,
           status,
           ordered_at
    FROM orders
    WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (order_id,))
        row = cur.fetchone()
    return row


def get_order_queue_with_cook_time(conn) -> list[dict[str, Any]]:
    """
    대기열/진행중/완료(픽업 전) 주문의 총 조리시간까지 함께 조회.

    cook_time_total_sec = SUM(order_detail.qty * menu.cook_time_sec)
    """
    sql = """
    SELECT
      o.id AS order_id,
      o.pickup_no,
      o.status,
      o.ordered_at,
      COALESCE(SUM(od.qty * m.cook_time_sec), 0) AS cook_time_total_sec
    FROM orders o
    JOIN order_detail od ON od.order_id = o.id
    JOIN menu m ON m.id = od.menu_id
    WHERE o.status IN ('PENDING', 'COOKING', 'DONE')
    GROUP BY o.id, o.pickup_no, o.status, o.ordered_at
    ORDER BY o.ordered_at ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


def update_order_status(conn, order_id: int, new_status: str) -> int:
    """
    주문 상태 변경. 변경된 행 수를 반환 (0이면 없는 주문).
    """
    sql = """
    UPDATE orders
    SET status = %s
    WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (new_status, order_id))
        return cur.rowcount
