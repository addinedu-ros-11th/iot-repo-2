"""
RFID 리더 시리얼 통신 모듈.

RC522 RFID 리더로부터 카드 UID를 읽어서 주문 화면에 자동 입력.
"""

import time
import serial
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from config import RFID_PORT, RFID_BAUDRATE


class RFIDReaderThread(QThread):
    """RFID 리더 스레드 (QThread 사용으로 Qt 시그널과 호환)"""
    card_detected = pyqtSignal(str)
    
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
    
    def run(self):
        """스레드 실행 (QThread의 run 메서드 오버라이드)"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[RFID] 리더 연결됨: {self.port} @ {self.baudrate}")
            self.running = True
            
            while self.running:
                try:
                    if self.serial_conn and self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8').strip()
                        if line:
                            print(f"[RFID] 수신: {line}")
                            if "RFID:" in line:
                                # RFID: 이후 문자열 추출
                                rfid_index = line.find("RFID:")
                                card_uid = line[rfid_index + 5:].strip()
                                if card_uid:
                                    print(f"[RFID] 카드 감지: {card_uid}")
                                    self.card_detected.emit(card_uid)
                    else:
                        self.msleep(10)  # QThread의 msleep 사용
                except Exception as e:
                    print(f"[RFID] 읽기 오류: {e}")
                    self.msleep(100)
        except Exception as e:
            print(f"[RFID] 리더 연결 실패: {e}")
        finally:
            if self.serial_conn:
                self.serial_conn.close()
                print("[RFID] 리더 연결 종료")
    
    def stop(self):
        """스레드 중지"""
        self.running = False
        self.wait(2000)  # 최대 2초 대기


class RFIDReader(QObject):
    """RFID 카드 리더 클래스"""
    
    # 카드가 인식되면 UID 문자열을 전달하는 시그널
    card_detected = pyqtSignal(str)
    
    def __init__(self, port=None, baudrate=None):
        super().__init__()
        self.port = port or RFID_PORT
        self.baudrate = baudrate or RFID_BAUDRATE
        self.thread = None
    
    def start(self):
        """RFID 리더 시작"""
        if self.thread and self.thread.isRunning():
            return
        
        self.thread = RFIDReaderThread(self.port, self.baudrate)
        self.thread.card_detected.connect(self.card_detected.emit)
        self.thread.start()
    
    def stop(self):
        """RFID 리더 중지"""
        if self.thread:
            self.thread.stop()
