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
            self.serial_connection = serial.Serial(
                self.port, self.baud_rate, timeout=1, write_timeout=1
            )
            time.sleep(2)  # Wait for Arduino reset

            buffer = b""
            start_time = time.time()
            found_init = False
            while time.time() - start_time < 8:
                if self.serial_connection.in_waiting:
                    byte = self.serial_connection.read(1)
                    if byte == b'\n':
                        line = buffer.decode('utf-8', errors='ignore').strip()
                        buffer = b""
                        if line and "Arduino Initialized" in line:
                            found_init = True
                            break
                    else:
                        buffer += byte
            if not found_init:
                self.serial_connection.close()
                self.connected = False
                return False

            self.connected = True

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

        except Exception:
            self.connected = False
            if self.serial_connection:
                try:
                    self.serial_connection.close()
                except:
                    pass
            return False

    def disconnect(self):
        self.connected = False
        if self.serial_connection:
            try:
                self.command_queue.put("STOP\n")
                time.sleep(1)
                self.serial_connection.close()
            except:
                pass

    def start_traffic_system(self) -> bool:
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
            return False
        try:
            cmd = f"UPDATE:{road_id}:{vehicle_count}:{str(has_emergency).lower()}\n"
            self.command_queue.put(cmd)
            print(f"🚦 Sending to Lane {road_id}: {vehicle_count} vehicles, Emergency: {'Yes' if has_emergency else 'No'}")
            return True
        except:
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
        buffer = b""
        while self.connected and self.serial_connection:
            try:
                if not self.command_queue.empty():
                    cmd = self.command_queue.get()
                    self.serial_connection.write(cmd.encode('utf-8'))
                    self.serial_connection.flush()
                    time.sleep(0.1)

                while self.serial_connection.in_waiting > 0:
                    byte = self.serial_connection.read(1)
                    if byte == b'\n':
                        line = buffer.decode('utf-8', errors='ignore').strip()
                        buffer = b""
                        if line:
                            self.response_queue.put(line)
                    else:
                        buffer += byte

                time.sleep(0.05)
            except:
                self.connected = False
                break

    def _monitor_responses(self):
        while self.connected:
            try:
                if not self.response_queue.empty():
                    response = self.response_queue.get()
                    try:
                        json.loads(response)
                    except json.JSONDecodeError:
                        pass
                time.sleep(0.1)
            except:
                break

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
            return False
    return arduino_controller.connect()

# Global emergency vehicle state tracker
emergency_vehicle_state = {
    'active_emergencies': {},  # road_id -> {detections, timestamp, distance}
    'last_priority_check': 0,
    'priority_check_interval': 2.0  # Check priority every 2 seconds
}

def send_traffic_data(data: List[Dict]):
    import time
    if not hasattr(send_traffic_data, "_lock"):
        from threading import Lock
        send_traffic_data._lock = Lock()
    lock = send_traffic_data._lock

    acquired = lock.acquire(blocking=False)
    if not acquired:
        return False
    try:
        current_time = time.time()
        
        # Update emergency vehicle state
        for road in data:
            road_id = road.get('id', 1)
            has_emergency = road.get('hasEmergencyVehicle', False)
            detections = road.get('detections', [])
            
            if has_emergency:
                # Find emergency vehicle and calculate distance
                emergency_vehicle = None
                for detection in detections:
                    # Check both 'class' and 'class_name' fields
                    class_name = detection.get('class', detection.get('class_name', '')).lower()
                    print(f"🔍 Checking detection: {class_name} at x={detection.get('x', 0):.2f}, y={detection.get('y', 0):.2f}")
                    
                    if any(emergency_type in class_name for emergency_type in [
                        'emergency', 'ambulance', 'fire truck', 'police', 'emergency-vehicle', 
                        'emergency vehicle', 'firetruck', 'fire_truck'
                    ]):
                        emergency_vehicle = detection
                        print(f"✅ Found emergency vehicle: {class_name}")
                        break
                
                if emergency_vehicle:
                    distance = _calculate_distance_from_camera(emergency_vehicle)
                    emergency_vehicle_state['active_emergencies'][road_id] = {
                        'detections': detections,
                        'timestamp': current_time,
                        'distance': distance,
                        'emergency_vehicle': emergency_vehicle
                    }
                    print(f"🚨 Emergency vehicle on Lane {road_id}: Distance={distance:.2f} pixels")
                else:
                    print(f"⚠️ No emergency vehicle found in detections for Lane {road_id}")
                    print(f"   Available detections: {[d.get('class', d.get('class_name', 'unknown')) for d in detections]}")
            else:
                # Remove from active emergencies if no longer detected
                if road_id in emergency_vehicle_state['active_emergencies']:
                    del emergency_vehicle_state['active_emergencies'][road_id]
                    print(f"✅ Emergency vehicle cleared from Lane {road_id}")
        
        # Check for dual emergency scenarios
        active_emergencies = emergency_vehicle_state['active_emergencies']
        print(f"📊 Current active emergencies: {len(active_emergencies)} - {list(active_emergencies.keys())}")
        
        # Debug timing information
        time_since_last_check = current_time - emergency_vehicle_state['last_priority_check']
        print(f"⏰ Time since last priority check: {time_since_last_check:.2f}s (threshold: {emergency_vehicle_state['priority_check_interval']}s)")
        
        if len(active_emergencies) > 1:
            print(f"🚨 MULTIPLE EMERGENCY VEHICLES DETECTED: {len(active_emergencies)}")
            
            # Always apply priority logic when multiple emergency vehicles are detected
            print(f"🚨 APPLYING PRIORITY LOGIC: {len(active_emergencies)} emergency vehicles")
            
            # Convert to list format for processing
            emergency_lanes = []
            for road_id, emergency_data in active_emergencies.items():
                emergency_lanes.append({
                    'id': road_id,
                    'detections': emergency_data['detections'],
                    'hasEmergencyVehicle': True,
                    'distance': emergency_data['distance']
                })
            
            # Print current distances for both lanes
            print("📏 CURRENT EMERGENCY VEHICLE DISTANCES:")
            for lane in emergency_lanes:
                print(f"   Lane {lane['id']}: {lane['distance']:.2f} pixels")
            
            # Check if both can cross simultaneously
            can_cross_simultaneously = _can_emergency_vehicles_cross_simultaneously(emergency_lanes)
            
            if can_cross_simultaneously:
                print("✅ Both emergency vehicles can cross simultaneously - allowing both")
                # Send data for all roads normally
                for road in data:
                    arduino_controller.update_road_data(
                        road.get('id', 1),
                        len(road.get('detections', [])),
                        road.get('hasEmergencyVehicle', False)
                    )
            else:
                # Only one can pass at a time - compute priority scores
                prioritized_lanes = _prioritize_emergency_vehicles(emergency_lanes, data)
                print(f"⚠️ Only one emergency vehicle can pass - prioritizing: {prioritized_lanes}")
                
                # Print priority decision
                priority_lane = prioritized_lanes[0]['id']
                print(f"🏆 PRIORITY DECISION: Lane {priority_lane} gets priority (closest to camera)")
                
                # Update traffic data with priority-based timing
                for road in data:
                    road_id = road.get('id', 1)
                    is_emergency = road.get('hasEmergencyVehicle', False)
                    
                    if is_emergency:
                        # Check if this is the priority emergency vehicle
                        is_priority = road_id == priority_lane
                        if is_priority:
                            print(f"🚦 Lane {road_id}: PRIORITY EMERGENCY VEHICLE - IMMEDIATE GREEN")
                        else:
                            print(f"🚦 Lane {road_id}: NON-PRIORITY EMERGENCY VEHICLE - BRIEF WAIT")
                            # Add a small delay for non-priority emergency vehicles
                            time.sleep(0.1)
                    
                    arduino_controller.update_road_data(
                        road_id,
                        len(road.get('detections', [])),
                        is_emergency
                    )
        else:
            # Single emergency vehicle or no emergency vehicles - use existing logic
            sorted_roads = sorted(
                data,
                key=lambda x: (-int(x.get('hasEmergencyVehicle', False)), 
                            -len(x.get('detections', [])))
            )
            for road in sorted_roads:
                arduino_controller.update_road_data(
                    road.get('id', 1),
                    len(road.get('detections', [])),
                    road.get('hasEmergencyVehicle', False)
                )
        
        # Clean up old emergency data (older than 10 seconds)
        current_time = time.time()
        expired_roads = []
        for road_id, emergency_data in emergency_vehicle_state['active_emergencies'].items():
            if current_time - emergency_data['timestamp'] > 10.0:
                expired_roads.append(road_id)
        
        for road_id in expired_roads:
            del emergency_vehicle_state['active_emergencies'][road_id]
            print(f"🧹 Cleaned up expired emergency data for Lane {road_id}")
        
        return True
    finally:
        lock.release()

def _can_emergency_vehicles_cross_simultaneously(emergency_lanes: List[Dict]) -> bool:
    """
    Determine if multiple emergency vehicles can cross the junction simultaneously.
    This is based on junction design - perpendicular lanes can cross simultaneously.
    """
    if len(emergency_lanes) != 2:
        return False
    
    # Get lane IDs
    lane_ids = [lane.get('id', 0) for lane in emergency_lanes]
    
    # Define perpendicular lane pairs (can cross simultaneously)
    # Only truly perpendicular lanes that don't conflict
    perpendicular_pairs = [
        (1, 3),  # North-South (opposite directions)
    ]
    
    # Check if the emergency lanes are perpendicular
    for pair in perpendicular_pairs:
        if (lane_ids[0] in pair and lane_ids[1] in pair):
            print(f"✅ Emergency vehicles on lanes {lane_ids} can cross simultaneously (perpendicular)")
            return True
    
    print(f"❌ Emergency vehicles on lanes {lane_ids} cannot cross simultaneously (conflicting)")
    return False

def _prioritize_emergency_vehicles(emergency_lanes: List[Dict], all_lanes: List[Dict]) -> List[Dict]:
    """
    Compute priority scores for emergency vehicles and return them in priority order.
    Priority is based on actual distance from camera - vehicle closer to camera gets higher priority.
    """
    prioritized = []
    
    print(f"🔍 Analyzing {len(emergency_lanes)} emergency lanes for priority...")
    
    for emergency_lane in emergency_lanes:
        lane_id = emergency_lane.get('id', 1)
        
        # Use pre-calculated distance from emergency vehicle state
        if lane_id in emergency_vehicle_state['active_emergencies']:
            emergency_data = emergency_vehicle_state['active_emergencies'][lane_id]
            distance_from_camera = emergency_data['distance']
            detections = emergency_data['detections']
            emergency_vehicle = emergency_data['emergency_vehicle']
            
            print(f"📋 Lane {lane_id}: Using pre-calculated distance={distance_from_camera:.2f} pixels")
            
            # Calculate traffic density (number of vehicles)
            traffic_density = len(detections)
            
            # Priority score: lower distance = higher priority
            score = distance_from_camera
            
            print(f"  📏 Distance from camera: {distance_from_camera:.2f} pixels")
            
            prioritized.append({
                'id': lane_id,
                'score': score,
                'distance_from_camera': distance_from_camera,
                'traffic_density': traffic_density,
                'lane_data': emergency_lane,
                'emergency_vehicle': emergency_vehicle
            })
        else:
            # Fallback if no emergency data found
            print(f"⚠️ Warning: No emergency data found for lane {lane_id}")
            prioritized.append({
                'id': lane_id,
                'score': 9999.0,  # Low priority fallback
                'distance_from_camera': 9999.0,
                'traffic_density': len(emergency_lane.get('detections', [])),
                'lane_data': emergency_lane,
                'emergency_vehicle': None
            })
    
    # Sort by score (ascending - lower score = higher priority)
    prioritized.sort(key=lambda x: x['score'])
    
    print("📊 Emergency Vehicle Priority Analysis (Distance from Camera):")
    for i, vehicle in enumerate(prioritized):
        if vehicle['emergency_vehicle']:
            print(f"  {i+1}. Lane {vehicle['id']}: Distance from camera={vehicle['distance_from_camera']:.2f} pixels "
                  f"(Priority: {'HIGH' if i == 0 else 'LOWER'}), Traffic={vehicle['traffic_density']} vehicles")
        else:
            print(f"  {i+1}. Lane {vehicle['id']}: No emergency vehicle detected (fallback priority)")
    
    return prioritized

def _calculate_distance_from_camera(detection: Dict) -> float:
    """
    Calculate the actual distance of a vehicle from the camera.
    Uses the center point of the bounding box and assumes camera is at the top of the image.
    """
    # Get bounding box coordinates
    x = detection.get('x', 0.5)  # Center X coordinate
    y = detection.get('y', 0.5)  # Center Y coordinate
    width = detection.get('width', 0.1)  # Width of bounding box
    height = detection.get('height', 0.1)  # Height of bounding box
    
    print(f"    📐 Raw coordinates: x={x}, y={y}, width={width}, height={height}")
    
    # Assume image dimensions (can be made configurable)
    image_width = 640
    image_height = 480
    
    # Check if coordinates are already in pixels (large values) or normalized (0-1)
    if x > 1.0 or y > 1.0:
        # Already in pixels
        center_x = x
        center_y = y
        print(f"    📐 Using pixel coordinates directly")
    else:
        # Convert normalized coordinates to pixel coordinates
        center_x = x * image_width
        center_y = y * image_height
        print(f"    📐 Converting normalized to pixel coordinates")
    
    # Calculate distance from camera (assumed to be at top center of image)
    camera_x = image_width / 2  # Camera at center horizontally
    camera_y = 0  # Camera at top of image
    
    # Calculate Euclidean distance from camera to vehicle center
    distance = ((center_x - camera_x) ** 2 + (center_y - camera_y) ** 2) ** 0.5
    
    print(f"    📐 Vehicle at ({center_x:.1f}, {center_y:.1f}), Camera at ({camera_x:.1f}, {camera_y:.1f})")
    print(f"    📏 Calculated distance: {distance:.2f} pixels")
    
    return distance
