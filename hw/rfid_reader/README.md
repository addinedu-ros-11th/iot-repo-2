# RFID RC522 리더 통합 가이드

## 하드웨어 연결

### RC522 모듈 핀 연결 (Arduino)
```
RC522 핀  ->  Arduino 핀
SDA       ->  D10
SCK       ->  D13
MOSI      ->  D11
MISO      ->  D12
IRQ       ->  연결 안함
GND       ->  GND
RST       ->  D9
3.3V      ->  3.3V (중요: 5V 아님!)
```

## 소프트웨어 설정

### 1. 아두이노 설정

1. **Arduino IDE에서 라이브러리 설치**
   - 라이브러리 매니저 열기: 스케치 → 라이브러리 포함하기 → 라이브러리 관리...
   - 검색: "MFRC522"
   - "MFRC522 by GithubCommunity" 설치

2. **코드 업로드**
   - `arduino/rfid_reader/rfid_reader.ino` 파일을 Arduino IDE로 열기
   - 보드 선택: Arduino Uno/Nano
   - 포트 선택 (예: `/dev/ttyUSB0` 또는 `COM3`)
   - 업로드 버튼 클릭

3. **동작 확인**
   - 시리얼 모니터 열기 (9600 baud)
   - RFID 카드를 리더에 가까이 대기
   - "RFID:XXXXXXXX" 형식으로 UID가 출력되는지 확인

### 2. Python 환경 설정

1. **pyserial 설치**
   ```bash
   pip install pyserial
   ```

2. **.env 파일 설정**
   프로젝트 루트의 `.env` 파일에 아래 설정 추가:
   ```
   # RFID 리더 포트 설정
   RFID_PORT=/dev/ttyUSB0
   RFID_BAUDRATE=9600
   ```
   
   **포트 찾기 (Linux)**:
   ```bash
   ls /dev/tty*
   # Arduino 연결 후 새로 생긴 포트 확인
   # 주로 /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0 등
   ```
   
   **포트 권한 설정 (Linux)**:
   ```bash
   sudo chmod 666 /dev/ttyUSB0
   # 또는 사용자를 dialout 그룹에 추가
   sudo usermod -a -G dialout $USER
   # 로그아웃 후 재로그인 필요
   ```

### 3. 사용 방법

1. **주문 화면 실행**
   ```bash
   python main.py
   ```

2. **RFID 카드 태그**
   - 주문 화면에서 장바구니에 메뉴 담기
   - RFID 카드를 리더에 가까이 대기
   - 카드 UID가 자동으로 "RFID 카드" 입력란에 입력됨
   - "결제 하기" 버튼 클릭하여 주문 완료

## 트러블슈팅

### 카드가 인식되지 않을 때

1. **하드웨어 연결 확인**
   - 3.3V 연결 확인 (5V로 연결하면 모듈 손상 가능)
   - 점퍼선 연결 상태 확인
   - RC522 모듈 LED가 켜져 있는지 확인

2. **시리얼 포트 확인**
   - Arduino IDE 시리얼 모니터에서 "RFID:XXXXXXXX" 출력 확인
   - Python 콘솔에서 `[RFID] 리더 연결됨` 메시지 확인
   - 포트 권한 문제 확인 (Linux)

3. **카드 거리 조정**
   - 카드를 리더 표면에 밀착
   - 금속 표면 위에서는 인식 거리가 짧아질 수 있음

### Python에서 RFID 데이터가 수신되지 않을 때

1. **포트 충돌 확인**
   - Arduino IDE 시리얼 모니터가 열려 있으면 닫기
   - 다른 프로그램이 포트를 사용 중인지 확인

2. **.env 설정 확인**
   - `RFID_PORT` 값이 실제 연결된 포트와 일치하는지 확인
   - `RFID_BAUDRATE`가 9600인지 확인

3. **로그 확인**
   - 콘솔에서 `[RFID] 수신:` 메시지 확인
   - 에러 메시지가 있다면 포트/권한 문제 해결

## 보안 고려사항

현재 구현은 UID를 그대로 사용합니다. 실제 운영 환경에서는:
- UID 해싱/암호화
- 카드 등록/인증 시스템 구축
- 금액 제한 및 승인 로직 추가
를 권장합니다.

## 추가 기능 아이디어

- 카드 잔액 관리 시스템
- 카드 등록/삭제 UI (관리자 화면)
- 카드 태그 시 소리/진동 피드백
- 다중 카드 타입 지원
- NFC 모바일 결제 지원
