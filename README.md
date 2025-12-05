# 🐟 붕어빵 자동 제조·판매 시스템

IoT 프로젝트 - 붕어빵 머신 제어 및 주문·재고·머신 상태 관리 통합 시스템

---

## 📋 목차
- [프로젝트 개요](#프로젝트-개요)
- [시스템 구조](#시스템-구조)
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
- **Hardware**: Arduino (머신 제어 + RFID 리더)
- **Communication**: Serial, REST API

### 주요 특징
- 실시간 주문 대기열 및 머신 상태 모니터링
- RFID 카드 기반 주문 시스템
- 재고 자동 소모 및 관리자 보충 기능
- 머신 비상정지/재가동 기능
- 이벤트 로그 기록 (과열, 센서 오류 등)

---

## 시스템 구조

```
┌─────────────┐         ┌──────────────┐
│  Arduino    │ Serial  │   PyQt UI    │
│  (머신제어)  │────────▶│ AdminScreen  │
│  RFID 리더  │         │ OrderScreen  │
└─────────────┘         └──────┬───────┘
                               │ HTTP
                               ▼
                        ┌──────────────┐
                        │  FastAPI     │
                        │  (서버)      │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   MySQL DB   │
                        └──────────────┘
```

---

## 폴더 구조

```
iot-repo-2/
├── main.py                 # PyQt 앱 진입점
├── config.py               # 환경변수 로드
├── .env                    # 환경변수 설정 (git ignore)
│
├── ui/                     # PyQt6 화면
│   ├── admin_screen.py     # 관리자 화면 (재고, 주문 관리, 머신 상태)
│   ├── admin_screen.ui     # Qt Designer 레이아웃
│   ├── order_screen.py     # 주문 화면 (메뉴 선택, 대기열)
│   └── order_screen.ui
│
├── server/                 # FastAPI 백엔드
│   ├── api.py              # 엔드포인트 정의
│   ├── models.py           # Pydantic 요청/응답 모델
│   ├── order_service.py    # 주문 비즈니스 로직
│   ├── inventory_service.py# 재고 비즈니스 로직
│   └── machine_service.py  # 머신 상태/이벤트 로직
│
├── db/                     # 데이터베이스 레이어
│   ├── db_conn.py          # DB 연결 헬퍼
│   ├── order_repo.py       # 주문 관련 쿼리
│   ├── inventory_repo.py   # 재고 관련 쿼리
│   └── machine_repo.py     # 머신 관련 쿼리
│
├── common/                 # 공통 유틸리티
│   ├── enums.py            # 상태값/코드 상수
│   └── timeutils.py        # 시간 변환 유틸
│
├── arduino/                # Arduino 스케치
│   ├── bungeoppang_machine/# 메인 머신 제어
│   └── rfid_reader/        # RFID 리더 통신
│
├── machine_link/           # PyQt-Arduino 시리얼 통신
│   ├── serial_client.py    # 시리얼 통신 클라이언트
│   ├── rfid_reader.py      # RFID 리더 인터페이스
│   └── msg_parser.py       # 메시지 파싱
│
├── API_SPEC.md             # API 명세
└── DB_SCHEMA.dbml          # 데이터베이스 스키마
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

MySQL에서 데이터베이스 생성 후 스키마 설정:
```sql
CREATE DATABASE fish;
-- 테이블 생성은 DB_SCHEMA.dbml 참고
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

두 개의 창이 실행됩니다:
- **AdminScreen**: 재고 관리, 주문 상태 변경, 머신 모니터링
- **OrderScreen**: 메뉴 선택 및 주문 생성, 대기열 확인

---

## 주요 기능

### 1. 주문 관리
- RFID 카드로 주문 생성
- 실시간 대기열 표시 (PENDING → COOKING → DONE → PICKED_UP)
- 관리자 주문 취소 (재고 자동 복구)

### 2. 재고 관리
- 주문 시 자동 재고 소모
- 관리자 재고 보충/조정 (RESTOCK, ADJUST)
- 재고 트랜잭션 로그 조회

### 3. 머신 상태 모니터링
- 실시간 머신 상태: IDLE, RUNNING, ERROR, EMERGENCY_STOP
- 플레이트 온도 및 센서 상태 표시
- 컨베이어, TCRT, 초음파 센서 상태

### 4. 비상정지 및 재가동
- **비상정지**: 관리자가 머신 테이블에서 선택 후 비상정지 버튼 클릭
  - `state` → `EMERGENCY_STOP`, `error_code` → `EMERGENCY_STOP`
- **재가동**: 비상정지된 머신 선택 후 재가동 버튼 클릭
  - `state` → `IDLE`, `error_code` → `NONE`

### 5. 이벤트 로깅
- 머신에서 발생하는 모든 이벤트 기록
- 이벤트 코드: ORDER_STARTED, ORDER_DONE, PICKUP_DETECTED, OVERHEAT, EMERGENCY_STOP 등

---

## API 엔드포인트

### 주문 관련
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/menu` | 메뉴 목록 조회 |
| POST | `/api/orders` | 주문 생성 |
| GET | `/api/orders/queue` | 대기열 조회 |
| PATCH | `/api/orders/{order_id}/status` | 주문 상태 변경 |
| PATCH | `/api/admin/orders/{order_id}/status` | 관리자 강제 상태 변경 |
| DELETE | `/api/orders/queue` | 대기열 초기화 |

### 재고 관련
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/materials` | 재고 목록 조회 |
| POST | `/api/materials/{material_id}/tx` | 재고 트랜잭션 생성 |
| GET | `/api/menu/{menu_id}/recipe` | 메뉴별 레시피 조회 |
| GET | `/api/materials/txs` | 재고 트랜잭션 로그 조회 |

### 머신 관련
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/machine/status` | 머신 상태 업데이트 (Arduino) |
| GET | `/api/machine/status` | 모든 머신 상태 조회 |
| POST | `/api/machine/events` | 머신 이벤트 기록 |
| POST | `/api/machine/{machine_id}/emergency-stop` | 비상정지 |
| POST | `/api/machine/{machine_id}/restore` | 재가동 |

상세 명세는 [API_SPEC.md](API_SPEC.md) 참고.

---

## 데이터베이스 스키마

### 주요 테이블
- `menu`: 메뉴 정보 (이름, 가격, 조리 시간)
- `orders`: 주문 정보 (픽업 번호, RFID, 상태, 주문 시각)
- `order_detail`: 주문 상세 (메뉴별 수량)
- `material_stock`: 재고 현황
- `material_recipe`: 메뉴별 재료 사용량
- `material_tx`: 재고 입출고 로그
- `machine_status`: 머신 현재 상태
- `machine_event`: 머신 이벤트 로그

상세 스키마는 [DB_SCHEMA.dbml](DB_SCHEMA.dbml) 참고.

---

## 개발 가이드

### 코드 규칙
- **네이밍**: snake_case (DB 컬럼명 = JSON 키 = Python 변수명)
- **상태값**: `common/enums.py`에서 상수로 관리
- **DB 접근**: `db/` 레포지토리 함수 사용
- **비즈니스 로직**: `server/` 서비스 레이어에서 처리

### UI 스타일
- PyQt6 QSS(CSS 유사 문법)로 스타일 적용
- `ui/admin_screen.py`의 `setStyleSheet()` 참고

### 시리얼 통신
- `machine_link/serial_client.py`에서 Arduino와 통신
- `machine_link/msg_parser.py`로 메시지 파싱

### 신호-슬롯 연결
- `main.py`에서 AdminScreen ↔ OrderScreen 신호 연결
- 주문 생성 시 재고 갱신, 대기열 초기화 시 화면 동기화 등

---

## 라이선스

MIT License

---

## 개발자

addinedu-ros-11th / iot-repo-2
