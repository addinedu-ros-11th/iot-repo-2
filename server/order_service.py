"""
주문/메뉴 관련 비즈니스 로직.
DB 접근은 db/order_repo.py 만 사용해야 한다.
"""

from typing import Any

from common import enums
from db import order_repo
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
    # TODO
    raise NotImplementedError("get_menu_list 구현 필요")


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
    # TODO
    raise NotImplementedError("create_order 구현 필요")


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
    # TODO
    raise NotImplementedError("get_order_queue 구현 필요")


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
    # TODO
    raise NotImplementedError("update_order_status 구현 필요")
