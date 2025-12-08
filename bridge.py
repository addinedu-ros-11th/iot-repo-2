# machine_bridge_fixed.py
import serial
import requests
import time
import json
import threading

# ===================== CONFIG =====================
SERVER_URL = "http://127.0.0.1:8000"
PLATE_PORT = "/dev/ttyACM7"      # Arduino-1 (plate)
CONV_PORT = "/dev/ttyACM8"       # Arduino-2 (conveyor)
BAUD = 115200
POLL_INTERVAL = 3.0

# ===================== HTTP HELPERS =====================
def http_get(path, timeout=3, retries=3):
    url = SERVER_URL + path
    for i in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"HTTP GET error ({i+1}/{retries}):", e)
            time.sleep(0.5 * (i+1))
    return None

def http_post(path, data, timeout=3, retries=3):
    url = SERVER_URL + path
    for i in range(retries):
        try:
            r = requests.post(url, json=data, timeout=timeout)
            r.raise_for_status()
            return r.json() if r.text else {}
        except Exception as e:
            print(f"HTTP POST error ({i+1}/{retries}):", e)
            time.sleep(0.5 * (i+1))
    return None

# ===================== SERIAL WRAPPERS =====================
def open_serial(port):
    try:
        s = serial.Serial(port, BAUD, timeout=0.1)
        time.sleep(2)
        print(f"Opened serial {port}")
        return s
    except Exception as e:
        print("Failed to open", port, e)
        return None

plate_ser = open_serial(PLATE_PORT)
conv_ser = open_serial(CONV_PORT)

if plate_ser is None:
    raise SystemExit("Plate serial not available")
if conv_ser is None:
    raise SystemExit("Conveyor serial not available")

# ===================== THREADS =====================
current_order = None
order_lock = threading.Lock()
plateState = "P_IDLE"  # shared plate state for status reporting

def plate_reader():
    global plateState, current_order
    while True:
        try:
            line = plate_ser.readline().decode(errors='ignore').strip()
            if not line:
                time.sleep(0.05)
                continue
            print("[PLATE]<<", line)
            handle_plate_line(line)
        except Exception as e:
            print("plate_reader error:", e)
            time.sleep(0.5)

def conv_reader():
    while True:
        try:
            line = conv_ser.readline().decode(errors='ignore').strip()
            if not line:
                time.sleep(0.05)
                continue
            print("[CONV]<<", line)
            handle_conv_line(line)
        except Exception as e:
            print("conv_reader error:", e)
            time.sleep(0.5)

# ===================== HANDLERS =====================
def handle_plate_line(line):
    global current_order, plateState
    # DROP message: forward to conveyor
    if line.startswith("DROP"):
        try:
            n = int(line.split()[1])
        except:
            n = 1
        conv_ser.write(f"DROP {n}\n".encode())
        print("[BRIDGE] forwarded DROP", n, "to conveyor")

    # TEMP message: post status
    elif line.startswith("TEMP:"):
        val = line.split(":", 1)[1]
        try:
            temp_val = float(val)
        except:
            temp_val = 0.0

        # plate state update
        state_str = "BAKING" if plateState == "P_BAKING" else "IDLE"

        payload = {
            "machine_name": "MAIN_MACHINE",
            "state": "RUNNING" if current_order else "IDLE",
            "current_order_id": current_order.get("order_id") if current_order else 0,
            "plate1_state": state_str,
            "plate1_temp": temp_val,
            "plate1_sensor_status": "OK",
            "plate2_state": "IDLE",
            "plate2_temp": 0.0,
            "plate2_sensor_status": "OK",
            "conveyor_state": "MOVING",
            "tcrt_status": "OK",
            "ultrasonic_status": "OK",
            "error_code": "NONE",
        }
        http_post("/api/machine/status", payload)

    # ORDER_DONE
    elif line.startswith("EVENT:ORDER_DONE"):
        parts = line.split(":")
        if len(parts) >= 3:
            oid = int(parts[2])
            data = {
                "machine_name": "MAIN_MACHINE",
                "order_id": oid,
                "component": "PLATE",
                "event_type": "STATE",
                "event_code": "ORDER_DONE"
            }
            http_post("/api/machine/events", data)
            with order_lock:
                if current_order and current_order.get("order_id") == oid:
                    print("[BRIDGE] Order finished", oid)
                    current_order = None

def handle_conv_line(line):
    global current_order
    if line.startswith("IR "):
        # format: IR x/y
        parts = line.split()
        if len(parts) >= 2:
            frac = parts[1].split('/')
            if len(frac) == 2:
                try:
                    cur = int(frac[0])
                    tot = int(frac[1])
                    print(f"[BRIDGE] Conveyor IR count {cur}/{tot}")
                except:
                    pass
    elif "EVENT:WAIT_PICKUP" in line:
        print("[BRIDGE] Conveyor waiting for pickup -> instruct plate STOP")
        plate_ser.write(b"STOP\n")
        payload = {
            "machine_name": "MAIN_MACHINE",
            "order_id": current_order.get("order_id") if current_order else 0,
            "component": "CONVEYOR",
            "event_type": "STATE",
            "event_code": "PICKUP_WAIT"
        }
        http_post("/api/machine/events", payload)
    elif "EVENT:PICKUP_DONE" in line or "PICKUP_DONE" in line:
        print("[BRIDGE] PICKUP DONE -> resume plate")
        plate_ser.write(b"RESUME\n")
        payload = {
            "machine_name": "MAIN_MACHINE",
            "order_id": current_order.get("order_id") if current_order else 0,
            "component": "CONVEYOR",
            "event_type": "PICKUP",
            "event_code": "PICKUP_DETECTED"
        }
        http_post("/api/machine/events", payload)
    elif line.startswith("ACK:DROP"):
        print("[BRIDGE] Conveyor ack drop")
    elif "ULTRA:SEEN" in line:
        pass

# ===================== POLL SERVER =====================
def poll_server_loop():
    global current_order, plateState
    while True:
        try:
            with order_lock:
                if current_order is None:
                    res = http_get("/api/machine/next-order")
                    if res and isinstance(res, dict) and res.get("order_id"):
                        current_order = {
                            "order_id": res.get("order_id"),
                            "total_qty": res.get("total_qty", res.get("cook_time_sec", 0))
                        }
                        cmd = f"ORDER {current_order['order_id']} {current_order['total_qty']}\n"
                        plate_ser.write(cmd.encode())
                        print("[BRIDGE] Sent to plate:", cmd.strip())
                        plateState = "P_IDLE"
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print("poll loop exception:", e)
            time.sleep(1)

# ===================== START THREADS =====================
t1 = threading.Thread(target=plate_reader, daemon=True)
t2 = threading.Thread(target=conv_reader, daemon=True)
t3 = threading.Thread(target=poll_server_loop, daemon=True)

t1.start()
t2.start()
t3.start()

print("Bridge started. Monitoring serial and server...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down bridge.")
    plate_ser.close()
    conv_ser.close()
