"""
아두이노와 시리얼 통신을 담당하는 모듈.

- 특정 포트(/dev/ttyACM0 등)를 열어서 한 줄씩 읽는다.
- 읽은 문자열은 msg_parser.handle_line()으로 넘긴다.
"""

import time

import serial

from config import SERIAL_PORT, SERIAL_BAUDRATE
from arduino_link import msg_parser


def run_serial_loop():
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
    print(f"[serial_client] Opened {SERIAL_PORT} @ {SERIAL_BAUDRATE}")

    try:
        while True:
            line_bytes = ser.readline()
            if not line_bytes:
                time.sleep(0.01)
                continue

            try:
                line = line_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue

            if not line:
                continue

            print(f"[serial_client] recv: {line}")
            msg_parser.handle_line(line)

    finally:
        ser.close()
        print("[serial_client] Closed serial port")
