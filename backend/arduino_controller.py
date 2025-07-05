import serial
import time
import json
from typing import Dict, List, Optional
import threading
import queue

class ArduinoController:
    def __init__(self, port: str = 'COM11', baud_rate: int = 9600):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection = None
        self.connected = False
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.comm_thread = None
        self.response_thread = None

    def connect(self) -> bool:
        try:
            print(f"🔌 Connecting to Arduino on {self.port}...")
            self.serial_connection = serial.Serial(
                self.port, self.baud_rate, timeout=1, write_timeout=1
            )
            time.sleep(2)  # Wait for Arduino reset

            print("⏳ Waiting for Arduino ready message...")
            buffer = b""
            start_time = time.time()
            found_init = False
            while time.time() - start_time < 8:
                if self.serial_connection.in_waiting:
                    byte = self.serial_connection.read(1)
                    if byte == b'\n':
                        line = buffer.decode('utf-8', errors='ignore').strip()
                        buffer = b""
                        if line:
                            print(f"📥 Startup: {line}")
                            if "Arduino Initialized" in line:
                                found_init = True
                                break
                    else:
                        buffer += byte
            if not found_init:
                print("❌ Arduino did not send initialization message. Check wiring and code.")
                self.serial_connection.close()
                self.connected = False
                return False

            self.connected = True
            print("✅ Arduino connected")

            self.comm_thread = threading.Thread(
                target=self._communication_loop, 
                daemon=True
            )
            self.comm_thread.start()

            self.response_thread = threading.Thread(
                target=self._monitor_responses,
                daemon=True
            )
            self.response_thread.start()

            time.sleep(1)
            self.command_queue.put("STATUS\n")
            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connected = False
            if self.serial_connection:
                try:
                    self.serial_connection.close()
                except:
                    pass
            return False

    def disconnect(self):
        print("🔌 Disconnecting Arduino...")
        self.connected = False
        if self.serial_connection:
            try:
                self.command_queue.put("STOP\n")
                time.sleep(1)
                self.serial_connection.close()
            except Exception as e:
                print(f"⚠️ Disconnect error: {e}")
        print("✅ Arduino disconnected")

    def start_traffic_system(self) -> bool:
        print("Kiran V")
        if self.connected:
            self.command_queue.put("START\n")
            return True
        return False

    def stop_traffic_system(self) -> bool:
        if self.connected:
            self.command_queue.put("STOP\n")
            return True
        return False

    def update_road_data(self, road_id: int, vehicle_count: int, has_emergency: bool) -> bool:
        if not self.connected:
            print(f"[ERROR] Arduino not connected. Cannot send UPDATE for road {road_id}.")
            return False
        try:
            cmd = f"UPDATE:{road_id}:{vehicle_count}:{str(has_emergency).lower()}\n"
            self.command_queue.put(cmd)
            print(f"🚦 Sending to Lane {road_id}: {vehicle_count} vehicles, "
                  f"Emergency: {'Yes' if has_emergency else 'No'}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to queue UPDATE command for road {road_id}: {e}")
            return False

    def get_available_ports(self) -> List[str]:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            desc = (p.description or '').lower()
            if any(k in desc for k in ['arduino', 'ch340', 'mega', 'uno', 'ftdi']):
                result.append(p.device)
            elif p.device.startswith(('COM', '/dev/ttyUSB', '/dev/ttyACM')):
                result.append(p.device)
        return result

    def _communication_loop(self):
        print("🔄 Communication loop started")
        buffer = b""

        while self.connected and self.serial_connection:
            try:
                if not self.command_queue.empty():
                    cmd = self.command_queue.get()
                    self.serial_connection.write(cmd.encode('utf-8'))
                    self.serial_connection.flush()
                    print(f"📤 Sent: {cmd.strip()}")
                    time.sleep(0.1)

                while self.serial_connection.in_waiting > 0:
                    byte = self.serial_connection.read(1)
                    if byte == b'\n':
                        line = buffer.decode('utf-8', errors='ignore').strip()
                        buffer = b""
                        if line:
                            print(f"📥 Received: {line}")
                            self.response_queue.put(line)
                    else:
                        buffer += byte

                time.sleep(0.05)

            except Exception as e:
                print(f"❌ Serial error: {e}")
                self.connected = False
                break

        print("🔄 Communication loop ended")

    def _monitor_responses(self):
        print("👂 Response monitoring started")
        while self.connected:
            try:
                if not self.response_queue.empty():
                    response = self.response_queue.get()
                    try:
                        data = json.loads(response)
                        print(f"📊 Arduino status: {data.get('message')}")
                    except json.JSONDecodeError:
                        print(f"📥 Raw response: {response}")
                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Response monitoring error: {e}")
                break
        print("👂 Response monitoring ended")

# Global instance
arduino_controller = ArduinoController()

def initialize_arduino(port: Optional[str] = None) -> bool:
    if port:
        arduino_controller.port = port
    else:
        ports = arduino_controller.get_available_ports()
        if ports:
            arduino_controller.port = ports[0]
        else:
            print("⚠️ No Arduino ports found")
            return False
    return arduino_controller.connect()

def send_traffic_data(data: List[Dict]):
    """
    Send traffic data with priority handling:
    1. Emergency vehicles get highest priority
    2. Roads with more vehicles get higher priority
    """
    import time
    # Use a lock to prevent concurrent sends
    if not hasattr(send_traffic_data, "_lock"):
        from threading import Lock
        send_traffic_data._lock = Lock()
    lock = send_traffic_data._lock

    acquired = lock.acquire(blocking=False)
    if not acquired:
        print("[INFO] Arduino update in progress, skipping this request.")
        return False
    try:
        sorted_roads = sorted(
            data,
            key=lambda x: (-int(x.get('hasEmergencyVehicle', False)), 
                        -len(x.get('detections', [])))
        )
        print("\n=== SENDING TRAFFIC DATA ===")
        all_success = True
        # Wait 0.5 seconds before sending to Arduino (reduced from 2 seconds)
        print("[DELAY] Waiting 0.5 seconds before sending to Arduino...")
        time.sleep(0.5)
        for road in sorted_roads:
            success = arduino_controller.update_road_data(
                road.get('id', 1),
                len(road.get('detections', [])),
                road.get('hasEmergencyVehicle', False)
            )
            if not success:
                print(f"[ERROR] Failed to send data for road {road.get('id', 1)}")
                all_success = False
        print("=== DATA SENT ===\n")
        return all_success
    finally:
        lock.release()