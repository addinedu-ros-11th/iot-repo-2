"""
material_* (재고, 레시피, 재고 트랜잭션) 관련 DB 접근 함수.
"""

from typing import Any


def get_materials(conn) -> list[dict[str, Any]]:
    sql = """
    SELECT id, name, unit, qty
    FROM material_stock
    ORDER BY id
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def insert_material_tx(
    conn,
    material_id: int,
    tx_type: str,
    qty_change: int,
    note: str | None,
    order_id: int | None = None,
) -> int:
    sql = """
    INSERT INTO material_tx (material_id, order_id, tx_type, qty_change, note, created_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
    """
    with conn.cursor() as cur:
        cur.execute(sql, (material_id, order_id, tx_type, qty_change, note))
        return cur.lastrowid


def update_material_stock(conn, material_id: int, qty_change: int) -> int:
    sql = """
    UPDATE material_stock
    SET qty = qty + %s
    WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (qty_change, material_id))
        return cur.rowcount


def get_recipe_by_menu(conn, menu_id: int) -> list[dict[str, Any]]:
    sql = """
    SELECT
      mr.menu_id,
      mr.material_id,
      ms.name,
      ms.unit,
      mr.use_per_one
    FROM material_recipe AS mr
    JOIN material_stock AS ms ON mr.material_id = ms.id
    WHERE mr.menu_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (menu_id,))
        return cur.fetchall()


def get_material_tx(conn, limit: int = 200) -> list[dict[str, Any]]:
        """
        재료 입출고 로그를 반환한다. 최근 항목을 생성시간 내림차순으로 반환.
        각 row는 다음 키를 포함: id, material_id, material_name, order_id, tx_type, qty_change, note, created_at
        """
        sql = """
        SELECT
            mt.id,
            mt.material_id,
            ms.name AS material_name,
            mt.order_id,
            mt.tx_type,
            mt.qty_change,
            mt.note,
            mt.created_at
        FROM material_tx mt
        LEFT JOIN material_stock ms ON mt.material_id = ms.id
        ORDER BY mt.created_at DESC
        LIMIT %s
        """
        with conn.cursor() as cur:
                cur.execute(sql, (limit,))
                return cur.fetchall()
