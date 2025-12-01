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
) -> int:
    sql = """
    INSERT INTO material_tx (material_id, order_id, tx_type, qty_change, note, created_at)
    VALUES (%s, NULL, %s, %s, %s, NOW())
    """
    with conn.cursor() as cur:
        cur.execute(sql, (material_id, tx_type, qty_change, note))
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
