"""
.env 파일을 읽어서 파이썬 코드에서 쓸 수 있게 해주는 설정 모듈.

- 실제 값은 .env 에서 관리
- 다른 코드에서는 config.DB_HOST, config.API_BASE_URL 이런 식으로 사용
"""

import os
from pathlib import Path

from dotenv import load_dotenv  # pip install python-dotenv

# 프로젝트 루트 기준으로 .env 로드
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # 우분투 서버처럼 환경변수로만 세팅하는 경우도 허용
    print("[config] .env 파일을 찾지 못했습니다. OS 환경변수를 사용합니다.")


# ==== DB 설정 ====
DB_HOST: str | None = os.getenv("DB_HOST")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_USER: str | None = os.getenv("DB_USER")
DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")
DB_NAME: str = os.getenv("DB_NAME", "fish")

# ==== API ====
# PyQt / arduino_link 에서 FastAPI 서버 호출할 때 사용
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

# ==== Arduino 시리얼 ====
SERIAL_PORT: str = os.getenv("SERIAL_PORT", "/dev/ttyACM0")
SERIAL_BAUDRATE: int = int(os.getenv("SERIAL_BAUDRATE", "115200"))

# ==== RFID 리더 ====
RFID_PORT: str = os.getenv("RFID_PORT", "/dev/ttyUSB0")
RFID_BAUDRATE: int = int(os.getenv("RFID_BAUDRATE", "9600"))
