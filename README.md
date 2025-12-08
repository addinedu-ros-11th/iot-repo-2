# 🐟 붕어빵 자동 제조·판매 시스템

IoT 프로젝트 - 붕어빵 머신 제어 및 주문·재고·머신 상태 관리 통합 시스템

---

## 📋 목차
- [프로젝트 개요](#프로젝트-개요)
- [시스템 아키텍처](#시스템-아키텍처)
- [폴더 구조](#폴더-구조)
- [설치 및 실행](#설치-및-실행)
- [주요 기능](#주요-기능)
- [API 엔드포인트](#api-엔드포인트)
- [데이터베이스 스키마](#데이터베이스-스키마)
- [개발 가이드](#개발-가이드)

---

## 프로젝트 개요

### 기술 스택
- **Frontend UI**: PyQt6 (관리자/주문 화면 이중 창)
- **Backend API**: FastAPI + Uvicorn
- **Database**: MySQL (pymysql)
- **Hardware**: Arduino (머신 제어), RFID Reader (카드 입력)
- **Communication**: Serial (Arduino/RFID), REST API (HTTP)

### 주요 특징
- 실시간 주문 대기열 동기화 (AdminScreen ↔ OrderScreen 3초마다)
- RFID 카드 기반 주문 입력 (시리얼 직접 연결, 서버 경유 ❌)
- 자동 재고 소모 및 관리자 보충/조정 기능
- 머신 비상정지/재가동 기능
- 머신 상태/이벤트 실시간 로깅

---

## 시스템 아키텍처

```
┌──────────────────────────────────────────────────────┐
│                   PyQt6 UI                           │
│  ┌─────────────────────────────────────────────────┐ │
│  │ AdminScreen: 재고관리, 주문상태, 머신모니터링   │ │
│  │ OrderScreen: 메뉴선택, 주문생성, 대기열         │ │
│  │ (3초 QTimer로 대기열 실시간 동기화)             │ │
│  └─────────────────────────────────────────────────┘ │
└────────────────┬─────────────────────────────────────┘
                 │ HTTP REST API
                 ▼
┌──────────────────────────────────────────────────────┐
│             FastAPI Server                           │
│  ├─ /api/orders (주문관리)                          │
│  ├─ /api/materials (재고)                           │
│  └─ /api/machine (머신상태/비상정지)                │
└────────────────┬─────────────────────────────────────┘
                 │ SQL
                 ▼
            MySQL Database

Serial 연결 (독립적)
┌──────────────────────────────────────────────────────┐
│  Arduino / RFID Reader                              │
│  ├─ RFID: /dev/ttyUSB0 (machine_link 직접 처리)    │
│  └─ Machine: /dev/ttyACM0 (머신상태 수신)          │
└──────────────────────────────────────────────────────┘
```

**주요 흐름:**
1. **RFID 카드 입력**: RFID Reader → PyQt (`machine_link/rfid_reader.py`) → `order_screen.py`
2. **주문 생성**: OrderScreen → `POST /api/orders` → DB (재고 자동 소모)
3. **대기열 동기화**: AdminScreen 3초 타이머 갱신 → `queue_updated` 신호 → OrderScreen 갱신
4. **비상정지**: AdminScreen 선택 → `POST /api/machine/{id}/emergency-stop` → 상태 변경
5. **머신 상태**: Arduino 지속 송신 → `POST /api/machine/status` → DB 실시간 반영

---

## 폴더 구조

```
iot-repo-2/
├── main.py                      # PyQt 앱 진입점 (UI 창 관리, 신호 연결)
├── config.py                    # 환경변수 로드 (.env)
├── bridge.py                    # API 요청 헬퍼 (requests 래퍼)
├── .env                         # 환경설정 (git ignore)
│
├── ui/                          # PyQt6 화면
│   ├── admin_screen.py          # 관리자 화면 (재고, 주문 관리, 머신 상태)
│   ├── admin_screen.ui          # Qt Designer 레이아웃
│   ├── admin_screen_ui.py       # admin_screen.ui 컴파일 결과
│   ├── order_screen.py          # 주문 화면 (메뉴 선택, 대기열)
│   ├── order_screen.ui          # Qt Designer 레이아웃
│   └── order_screen_ui.py       # order_screen.ui 컴파일 결과
│
├── server/                      # FastAPI 백엔드
│   ├── api.py                   # 엔드포인트 정의
│   ├── models.py                # Pydantic 요청/응답 모델
│   ├── order_service.py         # 주문 비즈니스 로직
│   ├── inventory_service.py     # 재고 비즈니스 로직
│   └── machine_service.py       # 머신 상태/이벤트 로직
│
├── db/                          # 데이터베이스 레이어
│   ├── db_conn.py               # DB 연결 헬퍼
│   ├── order_repo.py            # 주문 관련 쿼리
│   ├── inventory_repo.py        # 재고 관련 쿼리
│   └── machine_repo.py          # 머신 관련 쿼리
│
├── common/                      # 공통 유틸리티
│   ├── enums.py                 # 상태값/코드 상수
│   └── timeutils.py             # 시간 변환 유틸
│
├── machine_link/                # Arduino 시리얼 통신
│   ├── serial_client.py         # 시리얼 클라이언트
│   ├── rfid_reader.py           # RFID 리더 (Qt Thread)
│   └── msg_parser.py            # 메시지 파싱
│
├── hw/                          # Arduino 스케치 & 하드웨어
│   ├── bungeoppang_machine/
│   │   └── bungeoppang_machine.ino
│   └── rfid_reader/
│       ├── README.md
│       └── rfid_reader.ino
│
├── API_SPEC.md                  # API 상세 명세
└── DB_SCHEMA.dbml               # DB 스키마 (dbml 형식)
```

---

## 설치 및 실행

### 1. 환경 설정

#### 필수 요구사항
- Python 3.10 이상
- MySQL 8.0 이상
- Arduino IDE (하드웨어 연동 시)

#### Python 패키지 설치
```bash
pip install PyQt6 fastapi uvicorn pymysql python-dotenv requests pyserial
```

#### 환경변수 설정 (.env 파일 생성)
```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=fish

# API Server
API_BASE_URL=http://localhost:8000

# Arduino Serial
SERIAL_PORT=/dev/ttyACM0
SERIAL_BAUDRATE=115200

# RFID Reader
RFID_PORT=/dev/ttyUSB0
RFID_BAUDRATE=9600
```

### 2. 데이터베이스 초기화

MySQL에서 테이블 생성:
```sql
CREATE DATABASE fish;
USE fish;
-- DB_SCHEMA.dbml 기준으로 테이블 생성
```

### 3. FastAPI 서버 실행

```bash
uvicorn server.api:app --reload --port 8000
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 4. PyQt UI 실행

```bash
python main.py
```

- **AdminScreen**: 재고 관리, 주문 상태 변경, 머신 모니터링
- **OrderScreen**: 메뉴 선택, RFID 입력, 대기열 확인

---

## 주요 기능

### 1️⃣ 주문 관리
- **RFID 카드 입력**: 리더기에서 직접 읽음 (서버 경유 ❌)
- **주문 생성**: `POST /api/orders` → 재고 자동 소모
- **대기열 표시**: PENDING → COOKING → DONE → PICKED_UP
- **주문 취소**: 관리자 강제 취소 가능 (재고 복구)

### 2️⃣ 재고 관리
- **자동 소모**: 주문 생성 시 메뉴별 재료 차감
- **관리자 조정**: RESTOCK (보충) / ADJUST (조정)
- **트랜잭션 로그**: 입출고 이력 조회

### 3️⃣ 머신 상태 모니터링
- **실시간 갱신**: 관리자 화면 3초 QTimer
- **상태**: IDLE, RUNNING, ERROR, EMERGENCY_STOP
- **센서 정보**: 플레이트 온도, 컨베이어, TCRT, 초음파

### 4️⃣ 비상정지/재가동
- **비상정지**: 관리자 테이블에서 머신 선택 → 버튼 클릭
  - `state` → `EMERGENCY_STOP`
  - `error_code` → `EMERGENCY_STOP`
- **재가동**: 비상정지 머신 선택 → 재가동 버튼
  - `state` → `IDLE`
  - `error_code` → `NONE`

### 5️⃣ 이벤트 로깅
- 머신 이벤트: ORDER_STARTED, ORDER_DONE, PICKUP_DETECTED, OVERHEAT 등
- DB 저장: `machine_event` 테이블

### 6️⃣ UI 동기화
- **AdminScreen → OrderScreen**: `admin_win.queue_updated.emit()` (3초마다)
- **OrderScreen → AdminScreen**: 주문 생성 시 재고/트랜잭션 갱신
- **신호 연결**: `main.py`에서 관리

---

## API 엔드포인트

### 주문 관련
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/menu` | 메뉴 목록 |
| POST | `/api/orders` | 주문 생성 |
| GET | `/api/orders/queue` | 대기열 조회 |
| PATCH | `/api/orders/{id}/status` | 주문 상태 변경 |
| PATCH | `/api/admin/orders/{id}/status` | 관리자 강제 변경 |
| DELETE | `/api/orders/queue` | 대기열 초기화 |

### 재고 관련
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/materials` | 재고 목록 |
| POST | `/api/materials/{id}/tx` | 재고 트랜잭션 |
| GET | `/api/menu/{id}/recipe` | 레시피 조회 |
| GET | `/api/materials/txs` | 트랜잭션 로그 |

### 머신 관련
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/machine/status` | 머신 상태 업데이트 |
| GET | `/api/machine/status` | 모든 머신 상태 |
| POST | `/api/machine/events` | 이벤트 기록 |
| POST | `/api/machine/{id}/emergency-stop` | 비상정지 |
| POST | `/api/machine/{id}/restore` | 재가동 |

---

## 데이터베이스 스키마

### 핵심 테이블

**orders**: 주문 정보
- `id`, `pickup_no`, `rfid_card_id`, `status` (PENDING/COOKING/DONE/PICKED_UP/CANCELED)
- `ordered_at`

**machine_status**: 머신 현재 상태
- `id`, `name`, `state`, `error_code`
- `plate1_state`, `plate1_temp`, `plate2_state`, `plate2_temp`
- `conveyor_state`, `tcrt_status`, `ultrasonic_status`
- `last_heartbeat_at`

**material_stock**: 재고
- `id`, `name`, `unit`, `qty`

**material_recipe**: 메뉴별 재료
- `menu_id`, `material_id`, `use_per_one`

**material_tx**: 재고 입출고 로그
- `id`, `material_id`, `tx_type` (RESTOCK/CONSUME/ADJUST)
- `qty_change`, `note`, `created_at`

상세 스키마는 [DB_SCHEMA.dbml](DB_SCHEMA.dbml) 참고.

---

## 개발 가이드

### 코드 규칙
- **네이밍**: snake_case (DB ↔ JSON ↔ Python 일관성)
- **상태값**: `common/enums.py`에서 상수로 관리
- **DB 접근**: `db/` 레포지토리 함수 사용
- **비즈니스 로직**: `server/` 서비스 레이어에서 처리

### UI 스타일
- PyQt6 QSS (CSS 유사 문법) 사용
- `ui/admin_screen.py`의 `setStyleSheet()` 참고
- 붕어빵 테마 색상: #8B4513 (갈색), #FAEBD7 (베이지)

### RFID 입력 아키텍처
- `machine_link/rfid_reader.py`: Qt QThread로 시리얼 읽음
- `order_screen.py`: `card_detected` 신호 수신 → `txtRfid` 입력 필드 자동 채우기
- ⚠️ 서버를 거치지 않음 (입력 장치처럼 직접 처리)

### 대기열 실시간 동기화
- **AdminScreen**: 3초 QTimer → `load_queue()` → `queue_updated` 신호 발생
- **main.py**: `admin_win.queue_updated.connect(order_win.load_queue)`
- OrderScreen: 신호 수신 → `load_queue()` 자동 호출

### 신호-슬롯 연결 (main.py)
```python
admin_win.queue_reset.connect(order_win.load_queue)           # 초기화 시
admin_win.queue_updated.connect(order_win.load_queue)         # 3초마다
order_win.order_created.connect(admin_win.load_materials)     # 재고 갱신
order_win.order_created.connect(admin_win.load_material_tx)   # 트랜잭션 갱신
admin_win.order_changed.connect(order_win.load_queue)         # 상태변경 시
```

### 주요 개선사항
- ✅ 비상정지 400 오류 해결: `previous_state` 의존 제거
- ✅ UI 신호 중복 제거: 단일 `queue_updated` 신호로 통일
- ✅ 불필요 코드 정리: `get_machine_by_id`, 미완성 API 제거
- ✅ RFID 구조 명확화: 시리얼 직접 연결 (서버 경유 ❌)

---

## 라이선스

MIT License

---

## 개발자

addinedu-ros-11th / iot-repo-2 (2조)
