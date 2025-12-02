"""
주문/메뉴 관련 비즈니스 로직.
DB 접근은 db/order_repo.py 만 사용해야 한다.
"""

from typing import Any

from common import enums
from db import order_repo
from db import inventory_repo
from server import models


def get_menu_list(conn) -> list[dict[str, Any]]:
    """
    메뉴 전체 조회.

    요구사항:
    - db.order_repo.get_menu_list(conn) 호출
    - 반환값을 그대로 리턴 (추가 가공 없음)

    반환 형식 예:
    [
      {
        "id": 1,
        "code": "RED_BEAN",
        "name": "팥 붕어빵",
        "price": 1500,
        "cook_time_sec": 90
      },
      ...
    ]
    """
    # DB에서 메뉴 목록을 그대로 조회해서 반환
    return order_repo.get_menu_list(conn)


def create_order(conn, req: models.OrderCreate) -> dict[str, Any]:
    """
    주문 생성.

    입력: OrderCreate
    - req.rfid_card_id : str
    - req.items        : [ { menu_id:int, qty:int }, ... ]

    비즈니스 규칙 (꼭 그대로 구현):
    1) 오늘 날짜 기준으로 다음 pickup_no 계산
       - db.order_repo.get_next_pickup_no_for_today(conn) 사용
       - 오늘 첫 주문이면 101, 그 다음 102, ... (날짜 바뀌면 다시 101부터)
    2) orders INSERT
       - status = PENDING
       - pickup_no = 위에서 계산한 값
       - ordered_at = NOW() (DB에서 넣음)
       - db.order_repo.insert_order() 사용
       - 리턴된 order_id 를 기억
    3) order_detail INSERT
       - 각 item(menu_id, qty)에 대해 db.order_repo.insert_order_items() 호출
    4) conn.commit() 호출
    5) db.order_repo.get_order_by_id(conn, order_id) 로 방금 생성한 주문 조회
    6) 아래 형태의 dict 반환

    반환 형식:
    {
      "order_id": <int>,
      "pickup_no": <int>,      # 예: 101, 102, ...
      "status": "PENDING",
      "ordered_at": "<ISO8601 문자열>"  # row["ordered_at"].isoformat()
    }

    예외 처리:
    - order 삽입 후 get_order_by_id 결과가 None 이면 RuntimeError("ORDER_INSERT_FAILED") 발생
    """
    # 1) 다음 pickup_no 계산
    pickup_no = order_repo.get_next_pickup_no_for_today(conn)

    # 2) orders INSERT
    order_id = order_repo.insert_order(
      conn,
      pickup_no=pickup_no,
      rfid_card_id=req.rfid_card_id,
      status=enums.ORDER_STATUS_PENDING,
    )

    # 3) order_detail INSERT
    items = [(item.menu_id, item.qty) for item in req.items]
    if items:
      order_repo.insert_order_items(conn, order_id, items)

    # 3.1) 재고 차감 처리: 메뉴 레시피(material_recipe)를 참고해서 재료 사용량 집계
    # 각 메뉴별로 recipe를 조회하고, material_id 별 총 사용량을 계산하여 재고를 차감한다.
    # inventory_repo.get_recipe_by_menu(conn, menu_id) 를 사용
    # inventory_repo.insert_material_tx(conn, material_id, tx_type, qty_change, note)
    # inventory_repo.update_material_stock(conn, material_id, qty_change)
    try:
      # aggregate usage per material_id
      material_usage: dict[int, int] = {}
      for menu_id, qty in items:
        if qty <= 0:
          continue
        recipe_rows = inventory_repo.get_recipe_by_menu(conn, menu_id)
        for r in recipe_rows:
          mid = int(r.get("material_id"))
          use_per_one = int(r.get("use_per_one") or 0)
          total_use = use_per_one * int(qty)
          if total_use == 0:
            continue
          material_usage[mid] = material_usage.get(mid, 0) + total_use

      # apply material transactions and stock updates
      for material_id, total in material_usage.items():
        # qty_change is negative for consumption
        qty_change = -int(total)
        note = f"Order:{order_id}"
        # record tx
        inventory_repo.insert_material_tx(conn, material_id, "CONSUME", qty_change, note)
        # update stock
        inventory_repo.update_material_stock(conn, material_id, qty_change)
    except Exception:
      # If inventory update fails, raise to rollback the whole order creation
      raise

    # 4) commit
    conn.commit()

    # 5) 조회
    row = order_repo.get_order_by_id(conn, order_id)
    if row is None:
      raise RuntimeError("ORDER_INSERT_FAILED")

    # 6) 반환 형식
    ordered_at = row.get("ordered_at")
    return {
      "order_id": row["order_id"],
      "pickup_no": row["pickup_no"],
      "status": row["status"],
      "ordered_at": ordered_at.isoformat() if ordered_at is not None else None,
    }


def get_order_queue(conn) -> list[dict[str, Any]]:
    """
    대기열 / 진행중 / 완료(픽업 전) 주문 목록 + ETA(초)를 계산해서 반환.

    사용하기로 한 DB 함수:
    - db.order_repo.get_order_queue_with_cook_time(conn)
      이 함수는 다음 컬럼을 포함한 row 리스트를 반환한다:
      - order_id
      - pickup_no
      - status ('PENDING' | 'COOKING' | 'DONE')
      - ordered_at (datetime)
      - cook_time_total_sec (INT, 해당 주문 전체 조리시간 합계)

    ETA 계산 규칙 (중요):
    - orders는 ordered_at ASC 순으로 이미 정렬되어 있다고 가정.
    - 누적 시간(accumulated)을 0에서 시작.
    - 각 row 에 대해:
      - status 가 PENDING 또는 COOKING 이면:
          eta_sec = accumulated
          accumulated += cook_time_total_sec
      - status 가 DONE 이면:
          eta_sec = 0
    - 결과 리스트에는 다음 키를 포함해야 한다:

      {
        "order_id": <int>,
        "pickup_no": <int>,
        "status": "<문자열>",
        "ordered_at": "<ISO8601 문자열 또는 None>",
        "eta_sec": <int>
      }

    ※ ordered_at 이 None 이 아니면 row["ordered_at"].isoformat() 으로 문자열 변환.
    """
    rows = order_repo.get_order_queue_with_cook_time(conn)

    result: list[dict[str, Any]] = []
    accumulated = 0
    for row in rows:
      status = row.get("status")
      cook_time = int(row.get("cook_time_total_sec") or 0)

      if status in (enums.ORDER_STATUS_PENDING, enums.ORDER_STATUS_COOKING):
        eta_sec = accumulated
        accumulated += cook_time
      else:  # DONE or others
        eta_sec = 0

      ordered_at = row.get("ordered_at")
      result.append(
        {
          "order_id": row.get("order_id"),
          "pickup_no": row.get("pickup_no"),
          "status": status,
          "ordered_at": ordered_at.isoformat() if ordered_at is not None else None,
          "eta_sec": int(eta_sec),
        }
      )

    return result


def update_order_status(conn, order_id: int, new_status: str) -> dict[str, Any]:
    """
    주문 상태 변경 (손님 취소용).

    이 함수에서 처리하는 상태 변경은 "PENDING → CANCELED" 한 가지뿐이다.
    다른 상태 변경(DONE, PICKED_UP 등)은 machine_service 에서 처리한다.

    규칙:
    1) db.order_repo.get_order_by_id(conn, order_id) 로 현재 상태 조회
       - 없으면 ValueError("ORDER_NOT_FOUND") 발생
    2) new_status 가 CANCELED 인지 확인
       - 아니면 ValueError("UNSUPPORTED_STATUS_CHANGE") 발생
    3) 현재 상태가 PENDING 이 아니면
       - ValueError("CANNOT_CANCEL_NON_PENDING") 발생
    4) db.order_repo.update_order_status(conn, order_id, new_status) 호출
       - 영향받은 row 수가 0이면 RuntimeError("ORDER_STATUS_UPDATE_FAILED") 발생
    5) conn.commit() 호출
    6) 최종 상태를 다음 형식으로 반환:

      {
        "order_id": <int>,
        "pickup_no": <int>,
        "status": "CANCELED",
        "ordered_at": "<ISO8601 문자열 또는 None>"
      }
    """
    # 1) 현재 주문 조회
    row = order_repo.get_order_by_id(conn, order_id)
    if row is None:
      raise ValueError("ORDER_NOT_FOUND")

    # 2) 허용된 상태 확인 (이 함수는 취소만 처리)
    if new_status != enums.ORDER_STATUS_CANCELED:
      raise ValueError("UNSUPPORTED_STATUS_CHANGE")

    # 3) 현재 상태가 PENDING인지 확인
    current_status = row.get("status")
    if current_status != enums.ORDER_STATUS_PENDING:
      raise ValueError("CANNOT_CANCEL_NON_PENDING")

    # 4) 환불(재고 복구): 주문의 order_detail을 읽어 각 메뉴별 수량에 따라
    #    material_recipe를 참고해 material별 복구 수량을 계산하고 재고를 증가시킨다.
    #    모든 작업은 같은 트랜잭션에서 일어나므로 실패 시 롤백된다.
    if new_status == enums.ORDER_STATUS_CANCELED:
      # fetch ordered items
      items = order_repo.get_order_items(conn, order_id)
      # aggregate material usage
      material_usage: dict[int, int] = {}
      for it in items:
        menu_id = int(it.get("menu_id") or 0)
        qty = int(it.get("qty") or 0)
        if qty <= 0:
          continue
        recipe_rows = inventory_repo.get_recipe_by_menu(conn, menu_id)
        for r in recipe_rows:
          mid = int(r.get("material_id"))
          use_per_one = int(r.get("use_per_one") or 0)
          total_use = use_per_one * qty
          if total_use == 0:
            continue
          material_usage[mid] = material_usage.get(mid, 0) + total_use

      # apply restock for each material (positive qty_change)
      for material_id, total in material_usage.items():
        qty_change = int(total)
        note = f"CancelOrder:{order_id}"
        inventory_repo.insert_material_tx(conn, material_id, "RESTOCK", qty_change, note)
        inventory_repo.update_material_stock(conn, material_id, qty_change)

    # 5) 상태 변경
    affected = order_repo.update_order_status(conn, order_id, new_status)
    if affected == 0:
      raise RuntimeError("ORDER_STATUS_UPDATE_FAILED")

    # 6) commit
    conn.commit()

    # 7) 반환
    ordered_at = row.get("ordered_at")
    return {
      "order_id": row.get("order_id"),
      "pickup_no": row.get("pickup_no"),
      "status": new_status,
      "ordered_at": ordered_at.isoformat() if ordered_at is not None else None,
    }


def reset_order_queue(conn) -> dict[str, Any]:
    """
    대기열 초기화: DB에서 PENDING/COOKING/DONE 상태의 주문(및 상세)을 제거하고 삭제된 수를 반환.
    """
    deleted = order_repo.reset_order_queue(conn)
    conn.commit()
    return {"deleted_orders": int(deleted)}
