"""
재고(material_*), 레시피 관련 비즈니스 로직.
"""

from typing import Any

from db import inventory_repo
from server import models


def get_materials(conn) -> list[dict[str, Any]]:
    return inventory_repo.get_materials(conn)


def create_material_tx(conn, material_id: int, req: models.MaterialTxCreate) -> dict[str, Any]:
    tx_id = inventory_repo.insert_material_tx(
        conn,
        material_id=material_id,
        tx_type=req.tx_type,
        qty_change=req.qty_change,
        note=req.note,
    )
    inventory_repo.update_material_stock(conn, material_id, req.qty_change)
    conn.commit()

    return {
        "id": tx_id,
        "material_id": material_id,
        "tx_type": req.tx_type,
        "qty_change": req.qty_change,
        "note": req.note,
    }


def get_recipe(conn, menu_id: int) -> dict[str, Any]:
    rows = inventory_repo.get_recipe_by_menu(conn, menu_id)
    return {
        "menu_id": menu_id,
        "materials": rows,
    }
