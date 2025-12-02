"""
FastAPI 엔트리 포인트.

- 엔드포인트 URL, HTTP 메서드만 여기서 정의
- 실제 로직은 server/order_service.py 등으로 위임
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from db.db_conn import get_conn
from server import order_service, inventory_service, machine_service, models

app = FastAPI()

# 개발 단계에서 편하게 테스트하려면 CORS 느슨하게 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 나중에 필요하면 도메인 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/ping")
def ping():
    return {"message": "pong"}


# ===== 주문 / 메뉴 =====

@app.get("/api/menu")
def api_get_menu(db=Depends(get_db)):
    return order_service.get_menu_list(db)


@app.post("/api/orders")
def api_create_order(req: models.OrderCreate, db=Depends(get_db)):
    return order_service.create_order(db, req)


@app.get("/api/orders/queue")
def api_get_order_queue(db=Depends(get_db)):
    return order_service.get_order_queue(db)


@app.patch("/api/orders/{order_id}/status")
def api_update_order_status(order_id: int, req: models.OrderStatusUpdate, db=Depends(get_db)):
    return order_service.update_order_status(db, order_id, req.status)


# [추가됨] 대기열 초기화 엔드포인트
@app.delete("/api/orders/queue")
def api_reset_order_queue(db=Depends(get_db)):
    """
    대기열의 모든 주문을 삭제하거나 초기화합니다.
    """
    return order_service.reset_order_queue(db)


# ===== 재고 / 레시피 =====

@app.get("/api/materials")
def api_get_materials(db=Depends(get_db)):
    return inventory_service.get_materials(db)


@app.post("/api/materials/{material_id}/tx")
def api_create_material_tx(material_id: int, req: models.MaterialTxCreate, db=Depends(get_db)):
    return inventory_service.create_material_tx(db, material_id, req)


@app.get("/api/menu/{menu_id}/recipe")
def api_get_recipe(menu_id: int, db=Depends(get_db)):
    return inventory_service.get_recipe(db, menu_id)


@app.get("/api/materials/txs")
def api_get_material_txs(limit: int = 200, db=Depends(get_db)):
    """재료 입출고 로그(최신 순) 조회"""
    return inventory_service.get_material_tx(db, limit=limit)


# ===== 머신 =====

@app.post("/api/machine/status")
def api_update_machine_status(req: models.MachineStatusIn, db=Depends(get_db)):
    return machine_service.update_machine_status(db, req)


@app.get("/api/machine/status")
def api_get_machine_status(db=Depends(get_db)):
    return machine_service.get_machine_status(db)


@app.post("/api/machine/events")
def api_handle_machine_event(req: models.MachineEventIn, db=Depends(get_db)):
    return machine_service.handle_machine_event(db, req)
