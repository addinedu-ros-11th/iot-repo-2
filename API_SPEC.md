# fish_machine API SPEC

## 1. 공통

### 1.1 Base URL 
  미정

### 1.2 네이밍 규칙
- DB 컬럼명 = JSON 키 = Python 변수명 (snake_case)
- 예: `pickup_no`, `rfid_card_id`, `cook_time_sec`, `plate1_state`, `tx_type`

### 1.3 상태값 / 코드

**주문 상태 (`orders.status`)**
- `PENDING`, `COOKING`, `DONE`, `PICKED_UP`, `CANCELED`

**머신 상태 (`machine_status.state`)**
- `IDLE`, `RUNNING`, `ERROR`, `EMERGENCY_STOP`

**plate 상태 (`plate1_state`, `plate2_state`)**
- `IDLE`, `BAKING`, `DUMPING`, `ERROR`

**센서 상태**
- `plate?_sensor_status`: `OK`, `DISCONNECTED`, `OUT_OF_RANGE`, `STUCK`
- `tcrt_status`, `ultrasonic_status`: `OK`, `ERROR`, `STUCK`

**재고 트랜잭션 타입 (`material_tx.tx_type`)**
- `RESTOCK`, `CONSUME`, `ADJUST`

**머신 이벤트 코드 (`machine_event.event_code`)**
- `ORDER_STARTED`, `ORDER_DONE`, `PICKUP_DETECTED`,
- `OVERHEAT`, `EMERGENCY_STOP`,
- `TEMP_SENSOR_FAIL`, `TCRT_FAIL`, `ULTRASONIC_FAIL`

> 상수 정의는 `common/enums.py`에서 관리.

---

## 2. 엔드포인트 요약

### 2.1 주문 / 메뉴

| 도메인 | 메서드 | URL                             | 호출 주체   | 설명                          |
|--------|--------|---------------------------------|-------------|--------------------------------|
| 메뉴   | GET    | `/api/menu`                     | PyQt        | 메뉴 리스트 조회               |
| 주문   | POST   | `/api/orders`                   | PyQt        | 주문 생성                      |
| 주문   | GET    | `/api/orders/queue`             | PyQt        | 대기열 / 진행중 / 완료 조회   |
| 주문   | PATCH  | `/api/orders/{order_id}/status` | PyQt(관리자)| 주문 상태 변경 (주로 취소)    |

### 2.2 재고 / 레시피

| 도메인 | 메서드 | URL                               | 호출 주체   | 설명                     |
|--------|--------|-----------------------------------|-------------|--------------------------|
| 재고   | GET    | `/api/materials`                  | PyQt(관리자)| 재고 목록 및 수량 조회  |
| 재고Tx | POST   | `/api/materials/{material_id}/tx` | PyQt(관리자)| 재고 보충/조정 기록     |
| 레시피 | GET    | `/api/menu/{menu_id}/recipe`      | PyQt(관리자)| 메뉴 1개당 재료 사용량  |

### 2.3 머신

| 도메인 | 메서드 | URL                    | 호출 주체 | 설명                              |
|--------|--------|------------------------|-----------|-----------------------------------|
| 머신   | POST   | `/api/machine/status`  | Arduino   | 머신 상태 스냅샷 보고             |
| 머신   | GET    | `/api/machine/status`  | PyQt      | 모든 머신 현재 상태 조회          |
| 머신   | POST   | `/api/machine/events`  | Arduino   | 주문 완료 / 픽업 / 과열 등 이벤트 |

---

## 3. 엔드포인트별 필드 정의 (요약)

### 3.1 주문 / 메뉴

#### 3.1.1 `GET /api/menu`
- Request: 없음
- Response 배열 요소 필드:
  - `id: int`
  - `code: str`
  - `name: str`
  - `price: int`
  - `cook_time_sec: int`

---

#### 3.1.2 `POST /api/orders`
- Request Body 필드:
  - `rfid_card_id: str`
  - `items: List[ { menu_id: int, qty: int } ]`
- Response 필드:
  - `order_id: int`
  - `pickup_no: int`
  - `status: str` (`PENDING` 고정 시작)
  - `ordered_at: str (datetime ISO)`

---

#### 3.1.3 `GET /api/orders/queue`
- Request: 없음
- Response 배열 요소 필드:
  - `order_id: int`
  - `pickup_no: int`
  - `status: str` (`PENDING`/`COOKING`/`DONE`)
  - `ordered_at: str (datetime)`
  - `eta_sec: int` (예상 대기시간 초)

---

#### 3.1.4 `PATCH /api/orders/{order_id}/status`
- Path:
  - `order_id: int`
- Request Body:
  - `status: str` (`CANCELED`만 허용, V1 기준)
- Response:
  - `order_id: int`
  - `status: str`

---

### 3.2 재고 / 레시피

#### 3.2.1 `GET /api/materials`
- Request: 없음
- Response 배열 요소:
  - `id: int`
  - `name: str`
  - `unit: str`
  - `qty: int`

---

#### 3.2.2 `POST /api/materials/{material_id}/tx`
- Path:
  - `material_id: int`
- Request Body:
  - `tx_type: str` (`RESTOCK`/`CONSUME`/`ADJUST`)
  - `qty_change: int` (양수/음수)
  - `note: str (optional)`
- Response:
  - `id: int`
  - `material_id: int`
  - `tx_type: str`
  - `qty_change: int`
  - `note: str or null`
  - `created_at: str (datetime)`

---

#### 3.2.3 `GET /api/menu/{menu_id}/recipe`
- Path:
  - `menu_id: int`
- Response:
  - `menu_id: int`
  - `materials: List[ { material_id: int, name: str, unit: str, use_per_one: int } ]`

---

### 3.3 머신

#### 3.3.1 `POST /api/machine/status`
- Request Body:
  - `machine_name: str`
  - `state: str` (`IDLE`/`RUNNING`/`ERROR`/`EMERGENCY_STOP`)
  - `current_order_id: int or null`
  - `plate1_state: str`
  - `plate1_temp: int or null`
  - `plate1_sensor_status: str`
  - `plate2_state: str`
  - `plate2_temp: int or null`
  - `plate2_sensor_status: str`
  - `conveyor_state: str`
  - `tcrt_status: str`
  - `ultrasonic_status: str`
  - `error_code: str`
- Response:
  - `{ "ok": true }` 정도 (자유)

---

#### 3.3.2 `GET /api/machine/status`
- Request: 없음
- Response: 배열
  - 각 요소 = `machine_status` 테이블 컬럼과 동일 필드
  - 예: `id, name, state, current_order_id, last_heartbeat_at, ...`

---

#### 3.3.3 `POST /api/machine/events`
- Request Body:
  - `machine_name: str`
  - `order_id: int or null`
  - `component: str` (`MACHINE`/`PLATE1`/`PLATE2`/`CONVEYOR`/`SENSOR`)
  - `event_type: str` (`STATE`/`SAFETY`/`PICKUP`/`ERROR`)
  - `event_code: str` (위 상태값 목록 참조)
  - `temp: int or null`
  - `message: str (optional)`
- 서버 처리 규칙(요약):
  - 항상 `machine_event` INSERT
  - `ORDER_DONE` → `orders.status = 'DONE'`
  - `PICKUP_DETECTED` → `orders.status = 'PICKED_UP'`
  - `OVERHEAT` → `machine_status.error_code = 'OVERHEAT'`, `state = 'EMERGENCY_STOP'`
- Response:
  - `{ "ok": true }`

---

## 4. 역할 분담 기준

- PyQt: 이 문서에 있는 엔드포인트/필드명 그대로 HTTP 호출
- FastAPI: `server/api.py`에서 이 스펙대로 구현
- DB: `DB_SCHEMA.dbml` 기준으로 스키마 생성
- Arduino: `/api/machine/status`, `/api/machine/events` 요청 형식만 정확히 맞추기
