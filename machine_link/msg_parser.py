"""
아두이노에서 온 JSON 문자열을 파싱해서
서버 API(/api/machine/status, /api/machine/events)로 전달한다.

JSON 형식 예:

1) 상태 보고
{"type":"status","data":{
  "machine_name":"MAIN_MACHINE",
  "state":"RUNNING",
  "current_order_id":10,
  "plate1_state":"BAKING",
  "plate1_temp":185,
  "plate1_sensor_status":"OK",
  "plate2_state":"IDLE",
  "plate2_temp":30,
  "plate2_sensor_status":"OK",
  "conveyor_state":"MOVING",
  "tcrt_status":"OK",
  "ultrasonic_status":"OK",
  "error_code":"NONE"
}}

2) 이벤트 보고
{"type":"event","data":{
  "machine_name":"MAIN_MACHINE",
  "order_id":10,
  "component":"PLATE1",
  "event_type":"STATE",
  "event_code":"ORDER_DONE",
  "temp":190,
  "message":"order 10 done"
}}
"""

import json

import requests

from config import API_BASE_URL


def handle_line(line: str):
    """
    line: 한 줄짜리 JSON 문자열.
    """
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        print(f"[msg_parser] invalid json: {line}")
        return

    msg_type = msg.get("type")
    data = msg.get("data")

    if not isinstance(data, dict):
        print(f"[msg_parser] data must be object: {line}")
        return

    if msg_type == "status":
        url = f"{API_BASE_URL}/api/machine/status"
    elif msg_type == "event":
        url = f"{API_BASE_URL}/api/machine/events"
    else:
        print(f"[msg_parser] unknown type: {msg_type}")
        return

    try:
        resp = requests.post(url, json=data, timeout=5)
        resp.raise_for_status()
        print(f"[msg_parser] POST {url} -> {resp.status_code}")
    except Exception as e:
        print(f"[msg_parser] POST {url} failed: {e}")
