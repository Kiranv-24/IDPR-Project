from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import base64
import requests
import time
import json
import asyncio
import logging
import random
from arduino_controller import arduino_controller, initialize_arduino, send_traffic_data

app = FastAPI(title="Vehicle Detection API with Arduino Integration")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Roboflow configuration
ROBOFLOW_CONFIG = {
    1: {  # Lane 1
        'model_url': 'https://detect.roboflow.com/idp-kxvaq/1',
        'api_key': 'jIpN9dHCZm9o5Wrr4PIu',
    },
    2: {  # Lane 2
        'model_url': 'https://detect.roboflow.com/my-first-project-zx0el/1',
        'api_key': 'ckQZ0vm1NHyF5mzEt0wB',
    },
    3: {  # Lane 3 (same as Lane 1 for now)
        'model_url': 'https://detect.roboflow.com/idp-15x6h/3',
        'api_key': 'EcJhVnWcabDRAj2MdLlD',
    },
    4: {  # Lane 4 (same as Lane 1 for now)
        'model_url': 'https://detect.roboflow.com/traffic-management-system-nlheu/1',
        'api_key': 'a1gobndnlMtcrUEtF6GX',
    },
}

# --- Robust Roboflow request function and coordination primitives ---
arduino_lock = asyncio.Lock()
last_detection_time = 0
MIN_DETECTION_INTERVAL = 0.05  # Reduced from 1.0 to 0.2 seconds for faster detection

def roboflow_detect(base64_image, confidence=0.5, overlap=0.5, max_retries=2, timeout=15, model_url=None, api_key=None):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    params = {
        'api_key': api_key,
        'confidence': confidence,
        'overlap': overlap
    }
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                model_url,
                headers=headers,
                params=params,
                data=base64_image,
                timeout=timeout
            )
            if response.status_code == 200:
                result = response.json()
                preds = result.get('predictions', [])
                if not isinstance(preds, list):
                    preds = []
                return True, preds, None
            else:
                # Do not leak Roboflow URL or API key in error
                last_error = f"Roboflow API error: {response.status_code}"
                logging.warning(f"[Roboflow] Attempt {attempt}: {last_error}")
        except Exception as e:
            # Do not leak Roboflow URL or API key in error
            last_error = "Roboflow API request failed"
            logging.warning(f"[Roboflow] Attempt {attempt} Exception: {str(e)}")
        time.sleep(0.5 * attempt)
    return False, [], last_error or "Unknown Roboflow error"

# Startup flag
startup_complete = False

# Emergency override state
emergency_override = {'active': False, 'lanes': []}

class DetectionParameters(BaseModel):
    confidence_threshold: float = 0.5
    overlap_threshold: float = 0.5
    opacity_threshold: float = 0.75
    label_display_mode: str = "Draw Confidence"

class Detection(BaseModel):
    class_name: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

class DetectionResponse(BaseModel):
    success: bool
    detections: List[Detection]
    total_detections: int
    processing_time: float

class ArduinoConnectionRequest(BaseModel):
    port: Optional[str] = None

class TrafficDataRequest(BaseModel):
    road_data: List[Dict]



@app.post("/detect", response_model=DetectionResponse)
async def detect_objects(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.5,
    overlap_threshold: float = 0.5,
    road_id: int = 1
):
    """
    Robust vehicle detection endpoint using Roboflow with retry and error handling, and detection throttling.
    """
    global last_detection_time
    try:
        now = time.time()
        if now - last_detection_time < MIN_DETECTION_INTERVAL:
            wait_time = MIN_DETECTION_INTERVAL - (now - last_detection_time)
            await asyncio.sleep(wait_time)
        last_detection_time = time.time()
        start_time = time.time()
        image_data = await file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        config = ROBOFLOW_CONFIG.get(road_id, ROBOFLOW_CONFIG[1])
        model_url = config['model_url']
        api_key = config['api_key']
        # Debug only: do not print sensitive info in production
        # print(f"[DETECT] Using model_url={model_url}, api_key={api_key} for road_id={road_id}")
        ok, preds, error = await asyncio.get_event_loop().run_in_executor(
            None, roboflow_detect, base64_image, confidence_threshold, overlap_threshold, 2, 10, model_url, api_key
        )
        processing_time = time.time() - start_time
        if not ok:
            logging.error(f"[Roboflow] Detection failed: {error}")
            return DetectionResponse(
                success=False,
                detections=[],
                total_detections=0,
                processing_time=processing_time
            )
        detections = []
        for pred in preds:
            if all(k in pred for k in ('class', 'confidence', 'x', 'y', 'width', 'height')):
                detections.append(Detection(
                    class_name=pred['class'],
                    confidence=pred['confidence'],
                    x=pred['x'],
                    y=pred['y'],
                    width=pred['width'],
                    height=pred['height']
                ))
            else:
                logging.warning(f"Skipping incomplete detection: {pred}")
        return DetectionResponse(
            success=True,
            detections=detections,
            total_detections=len(detections),
            processing_time=processing_time
        )
    except Exception as e:
        logging.error(f"Detection failed: {e}")
        return DetectionResponse(
            success=False,
            detections=[],
            total_detections=0,
            processing_time=0.0
        )



@app.post("/detect_frame")
async def detect_frame(frame_data: dict):
    """
    Robust vehicle detection from frame data using Roboflow with retry and error handling, and smooth hardware coordination.
    """
    global last_detection_time, emergency_override
    try:
        now = time.time()
        if now - last_detection_time < MIN_DETECTION_INTERVAL:
            wait_time = MIN_DETECTION_INTERVAL - (now - last_detection_time)
            await asyncio.sleep(wait_time)
        last_detection_time = time.time()
        start_time = time.time()
        base64_data = frame_data.get('image', '').split(',')[1] if ',' in frame_data.get('image', '') else frame_data.get('image', '')
        if not base64_data:
            return {"success": False, "predictions": [], "error": "No image data provided"}
        confidence_threshold = frame_data.get('confidence_threshold', 0.5)
        overlap_threshold = frame_data.get('overlap_threshold', 0.5)
        road_id = frame_data.get('road_id', 1)
        config = ROBOFLOW_CONFIG.get(road_id, ROBOFLOW_CONFIG[1])
        model_url = config['model_url']
        api_key = config['api_key']
        # Debug only: do not print sensitive info in production
        # print(f"[DETECT_FRAME] Using model_url={model_url}, api_key={api_key} for road_id={road_id}")
        ok, preds, error = await asyncio.get_event_loop().run_in_executor(
            None, roboflow_detect, base64_data, confidence_threshold, overlap_threshold, 3, 10, model_url, api_key
        )
        processing_time = time.time() - start_time
        if not ok:
            logging.error(f"[Roboflow] detect_frame failed: {error}")
            return {"success": False, "predictions": [], "error": error, "processing_time": processing_time}
        detections = []
        for pred in preds:
            if all(k in pred for k in ('class', 'confidence', 'x', 'y', 'width', 'height')):
                detections.append({
                    'class': pred['class'],
                    'confidence': pred['confidence'],
                    'x': pred['x'],
                    'y': pred['y'],
                    'width': pred['width'],
                    'height': pred['height']
                })
            else:
                logging.warning(f"Skipping incomplete detection: {pred}")
        # Print the detections received from image processing with timestamp
        process_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        print(f"\n[INFO {process_time}] Image processed for road_id={road_id}. Detections: {len(detections)}")
        road_id = frame_data.get('road_id', 1)
        has_emergency = any(
            d['class'].lower() == 'emergency-vehicle' for d in detections
        )
        road_data = [{
            'id': road_id,
            'detections': detections,
            'hasEmergencyVehicle': has_emergency
        }]

        # Emergency override logic
        if has_emergency:
            emergency_override['active'] = True
            if road_id not in emergency_override['lanes']:
                emergency_override['lanes'].append(road_id)
        elif not has_emergency and road_id in emergency_override['lanes']:
            # Remove this lane from emergency lanes if no emergency vehicle detected
            emergency_override['lanes'].remove(road_id)
            if not emergency_override['lanes']:
                # If no emergency lanes left, clear override
                emergency_override['active'] = False
        # If override is active and this is not an emergency lane, skip processing
        if emergency_override['active'] and road_id not in emergency_override['lanes']:
            return {"success": True, "predictions": [], "processing_time": 0, "arduino_sent": False, "emergency_override": True}

        # Throttle sending to Arduino: only send every 2 seconds per road (reduced from 5 seconds)
        if not hasattr(detect_frame, '_last_arduino_send'):
            detect_frame._last_arduino_send = {}
        if not hasattr(detect_frame, '_last_sent_detections'):
            detect_frame._last_sent_detections = {}
        now_time = time.time()
        last_send = detect_frame._last_arduino_send.get(road_id, 0)
        last_sent_detections = detect_frame._last_sent_detections.get(road_id, None)

        # If all vehicles are removed, clear the queue for this road
        if len(detections) == 0 and last_sent_detections and len(last_sent_detections) > 0:
            print(f"[CLEAR {process_time}] All vehicles removed from road_id={road_id}. Clearing previous detections and sending update to Arduino.")
            road_data_clear = [{
                'id': road_id,
                'detections': [],
                'hasEmergencyVehicle': False
            }]
            if emergency_override['active']:
                # Only send clear for emergency lanes
                for lane in emergency_override['lanes']:
                    async with arduino_lock:
                        if arduino_controller.connected:
                            clear_success = await asyncio.get_event_loop().run_in_executor(
                                None, send_traffic_data, road_data_clear
                            )
                            print(f"[ARDUINO {process_time}] Cleared data sent to Arduino for road_id={lane}. Success: {clear_success}")
                        else:
                            print(f"[ERROR {process_time}] Arduino not connected. Cannot send clear data from detect_frame.")
            else:
                async with arduino_lock:
                    if arduino_controller.connected:
                        clear_success = await asyncio.get_event_loop().run_in_executor(
                            None, send_traffic_data, road_data_clear
                        )
                        print(f"[ARDUINO {process_time}] Cleared data sent to Arduino for road_id={road_id}. Success: {clear_success}")
                    else:
                        print(f"[ERROR {process_time}] Arduino not connected. Cannot send clear data from detect_frame.")
            detect_frame._last_sent_detections[road_id] = []
            detect_frame._last_arduino_send[road_id] = now_time
        # Send immediately if emergency override is active, otherwise use throttling
        elif emergency_override['active'] or now_time - last_send >= 2:
            if emergency_override['active']:
                # Send immediately for emergency lanes
                for lane in emergency_override['lanes']:
                    async with arduino_lock:
                        if arduino_controller.connected:
                            success = await asyncio.get_event_loop().run_in_executor(
                                None, send_traffic_data, road_data
                            )
                        else:
                            pass
            else:
                # Normal throttled sending
                async with arduino_lock:
                    if arduino_controller.connected:
                        success = await asyncio.get_event_loop().run_in_executor(
                            None, send_traffic_data, road_data
                        )
                    else:
                        pass
            detect_frame._last_sent_detections[road_id] = detections
            detect_frame._last_arduino_send[road_id] = now_time
        else:
            print(f"[SKIP {process_time}] Not sending to Arduino for road_id={road_id}. Last sent {now_time - last_send:.2f}s ago.")

        return {
            "success": True,
            "predictions": detections,
            "processing_time": processing_time,
            "arduino_sent": True  # Always True for API response clarity
        }
    except Exception as e:
        logging.error(f"Detection failed: {e}")
        return {"success": False, "predictions": [], "error": str(e)}

@app.post("/detect_batch")
async def detect_batch(frames_data: List[dict]):
    """
    Batch detection endpoint for processing multiple camera frames simultaneously.
    This improves performance by reducing API calls and enabling parallel processing.
    """
    global last_detection_time, emergency_override
    try:
        now = time.time()
        if now - last_detection_time < MIN_DETECTION_INTERVAL:
            wait_time = MIN_DETECTION_INTERVAL - (now - last_detection_time)
            await asyncio.sleep(wait_time)
        last_detection_time = time.time()
        start_time = time.time()
        
        # First, check if any frame has emergency vehicle
        emergency_lanes = []
        for frame_data in frames_data:
            preds = frame_data.get('detections', [])
            if any(d['class'].lower() == 'emergency-vehicle' for d in preds):
                emergency_lanes.append(frame_data.get('road_id', 1))
        if emergency_lanes:
            emergency_override['active'] = True
            emergency_override['lanes'] = emergency_lanes
        else:
            # If no emergency vehicle detected in any frame, clear override
            emergency_override['active'] = False
            emergency_override['lanes'] = []
        # If override is active, only process that lane
        if emergency_override['active']:
            frames_data = [f for f in frames_data if f.get('road_id', 1) in emergency_override['lanes']]
        
        # Process all frames in parallel
        tasks = []
        for frame_data in frames_data:
            base64_data = frame_data.get('image', '').split(',')[1] if ',' in frame_data.get('image', '') else frame_data.get('image', '')
            if base64_data:
                confidence_threshold = frame_data.get('confidence_threshold', 0.5)
                overlap_threshold = frame_data.get('overlap_threshold', 0.5)
                road_id = frame_data.get('road_id', 1)
                config = ROBOFLOW_CONFIG.get(road_id, ROBOFLOW_CONFIG[1])
                model_url = config['model_url']
                api_key = config['api_key']
                # Debug only: do not print sensitive info in production
                # print(f"[DETECT_BATCH] Using model_url={model_url}, api_key={api_key} for road_id={road_id}")
                task = asyncio.get_event_loop().run_in_executor(
                    None, roboflow_detect, base64_data, confidence_threshold, overlap_threshold, 2, 10, model_url, api_key
                )
                tasks.append((task, road_id))
        
        # Wait for all detections to complete
        results = []
        for task, road_id in tasks:
            try:
                ok, preds, error = await task
                if ok:
                    detections = []
                    for pred in preds:
                        if all(k in pred for k in ('class', 'confidence', 'x', 'y', 'width', 'height')):
                            detections.append({
                                'class': pred['class'],
                                'confidence': pred['confidence'],
                                'x': pred['x'],
                                'y': pred['y'],
                                'width': pred['width'],
                                'height': pred['height']
                            })
                    results.append({
                        'road_id': road_id,
                        'success': True,
                        'detections': detections,
                        'error': None
                    })
                else:
                    results.append({
                        'road_id': road_id,
                        'success': False,
                        'detections': [],
                        'error': error
                    })
            except Exception as e:
                results.append({
                    'road_id': road_id,
                    'success': False,
                    'detections': [],
                    'error': str(e)
                })
        
        processing_time = time.time() - start_time
        
        # Process results and send to Arduino if needed
        road_data = []
        for result in results:
            if result['success']:
                has_emergency = any(
                    d['class'].lower() == 'emergency-vehicle'
                    for d in result['detections']
                )
                road_data.append({
                    'id': result['road_id'],
                    'detections': result['detections'],
                    'hasEmergencyVehicle': has_emergency
                })
        
        # After collecting results, only send to Arduino for emergency lane if override is active
        if emergency_override['active']:
            road_data = [r for r in road_data if r['id'] in emergency_override['lanes']]
        
        # Send batch data to Arduino
        if road_data:
            async with arduino_lock:
                if arduino_controller.connected:
                    await asyncio.get_event_loop().run_in_executor(
                        None, send_traffic_data, road_data
                    )
        
        return {
            'success': True,
            'results': results,
            'processing_time': processing_time,
            'total_frames': len(frames_data)
        }
        
    except Exception as e:
        logging.error(f"Batch detection failed: {e}")
        return {
            'success': False,
            'results': [],
            'processing_time': 0.0,
            'total_frames': len(frames_data),
            'error': str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint that indicates backend readiness"""
    return {
        "status": "healthy", 
        "message": "Backend server is running",
        "model": "idp-qwteg/2",
        "arduino_connected": arduino_controller.connected,
        "startup_complete": startup_complete,
        "timestamp": time.time()
    }

@app.post("/arduino/connect")
async def connect_arduino(request: ArduinoConnectionRequest):
    """Connect to Arduino controller"""
    try:
        if not startup_complete:
            return {"success": False, "message": "Backend is still starting up, please wait..."}
        
        print(f"🔌 Attempting to connect Arduino on port: {request.port}")
        success = initialize_arduino(request.port)
        
        if success:
            print("✅ Arduino connection successful!")
            return {"success": True, "message": "Arduino connected successfully"}
        else:
            print("❌ Arduino connection failed!")
            return {
                "success": False, 
                "message": "Failed to connect to Arduino. Please check:\n1. Arduino is connected via USB\n2. Traffic controller sketch is uploaded\n3. Correct COM port is selected\n4. Arduino IDE Serial Monitor is closed"
            }
    except Exception as e:
        print(f"❌ Arduino connection error: {e}")
        return {"success": False, "message": f"Connection error: {str(e)}"}

@app.post("/arduino/disconnect")
async def disconnect_arduino():
    """Disconnect from Arduino controller"""
    try:
        print("🔌 Disconnecting Arduino...")
        arduino_controller.disconnect()
        print("✅ Arduino disconnected successfully")
        return {"success": True, "message": "Arduino disconnected"}
    except Exception as e:
        print(f"❌ Arduino disconnection error: {e}")
        return {"success": False, "message": f"Disconnection error: {str(e)}"}

@app.post("/arduino/start")
async def start_traffic_system():
    """Start the Arduino traffic control system"""
    try:
        if not arduino_controller.connected:
            return {"success": False, "message": "Arduino not connected. Please connect first."}
        
        print("🚦 Starting traffic control system...")
        success = arduino_controller.start_traffic_system()
        
        if success:
            print("✅ Traffic system started successfully!")
            return {"success": True, "message": "Traffic system started"}
        else:
            return {"success": False, "message": "Failed to start traffic system"}
    except Exception as e:
        print(f"❌ Start system error: {e}")
        return {"success": False, "message": f"Start error: {str(e)}"}

@app.post("/arduino/stop")
async def stop_traffic_system():
    """Stop the Arduino traffic control system"""
    try:
        if not arduino_controller.connected:
            return {"success": False, "message": "Arduino not connected"}
        
        print("🛑 Stopping traffic control system...")
        success = arduino_controller.stop_traffic_system()
        
        if success:
            print("✅ Traffic system stopped successfully!")
            return {"success": True, "message": "Traffic system stopped"}
        else:
            return {"success": False, "message": "Failed to stop traffic system"}
    except Exception as e:
        print(f"❌ Stop system error: {e}")
        return {"success": False, "message": f"Stop error: {str(e)}"}

@app.post("/arduino/update_traffic")
async def update_traffic_data(request: TrafficDataRequest):
    """Send traffic data to Arduino"""
    try:
        if not arduino_controller.connected:
            return {"success": False, "message": "Arduino not connected"}
        
        import pprint
        print("\n🔍 RAW TRAFFIC DATA RECEIVED FROM FRONTEND:")
        pprint.pprint(request.road_data)

        success = send_traffic_data(request.road_data)
        if success:
            return {"success": True, "message": "Traffic data sent to Arduino"}
        else:
            return {"success": False, "message": "Failed to send traffic data"}
    except Exception as e:
        print(f"❌ Traffic data error: {e}")
        return {"success": False, "message": f"Traffic data error: {str(e)}"}

@app.get("/arduino/status")
async def get_arduino_status():
    """Get Arduino connection and system status"""
    try:
        if not startup_complete:
            return {
                "connected": False,
                "port": "N/A",
                "available_ports": [],
                "message": "Backend starting up..."
            }
        
        available_ports = arduino_controller.get_available_ports()
        print(f"📟 Available ports: {available_ports}")
        
        return {
            "connected": arduino_controller.connected,
            "port": arduino_controller.port,
            "available_ports": available_ports,
            "message": "Status retrieved successfully"
        }
    except Exception as e:
        print(f"❌ Status error: {e}")
        return {
            "connected": False,
            "port": "Error",
            "available_ports": [],
            "message": f"Status error: {str(e)}"
        }

@app.get("/")
async def root():
    return {
        "message": "🚦 Vehicle Detection API with Arduino Traffic Control", 
        "status": "running",
        "arduino_connected": arduino_controller.connected
    }

@app.websocket("/ws/detect")
async def websocket_detect(websocket: WebSocket):
    """WebSocket endpoint for real-time detection"""
    await websocket.accept()
    print("🔌 WebSocket connection established")
    
    # Send initial connection confirmation
    await websocket.send_json({
        'success': True,
        'message': 'WebSocket connected successfully',
        'type': 'connection'
    })
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_json()
            
            # Extract image data and parameters
            image_data = data.get('image', '')
            confidence_threshold = data.get('confidence', 0.5)
            overlap_threshold = data.get('overlap', 0.5)
            road_id = data.get('road_id', 1)
            
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Debug: Print incoming image size and confidence
            print(f"[WS] Received image for road_id={road_id}, size={len(image_data)} bytes, confidence={confidence_threshold}")
            
            if not image_data:
                await websocket.send_json({
                    'success': False,
                    'error': 'No image data provided'
                })
                continue
            
            # Perform detection
            try:
                now = time.time()
                if now - last_detection_time < MIN_DETECTION_INTERVAL:
                    wait_time = MIN_DETECTION_INTERVAL - (now - last_detection_time)
                    await asyncio.sleep(wait_time)
                
                start_time = time.time()
                config = ROBOFLOW_CONFIG.get(road_id, ROBOFLOW_CONFIG[1])
                model_url = config['model_url']
                api_key = config['api_key']
                # Debug only: do not print sensitive info in production
                # print(f"[WS] Using model_url={model_url}, api_key={api_key} for road_id={road_id}")
                ok, preds, error = await asyncio.get_event_loop().run_in_executor(
                    None, roboflow_detect, image_data, confidence_threshold, overlap_threshold, 2, 10, model_url, api_key
                )
                processing_time = time.time() - start_time
                # Debug only: do not print sensitive info in production
                # print(f"[WS] Roboflow API response for road_id={road_id}: ok={ok}, preds={preds}, error={error}")
                
                if not ok:
                    await websocket.send_json({
                        'success': False,
                        'error': error,
                        'processing_time': processing_time
                    })
                    continue
                
                # Process detections
                detections = []
                for pred in preds:
                    if all(k in pred for k in ('class', 'confidence', 'x', 'y', 'width', 'height')):
                        detections.append({
                            'class': pred['class'],
                            'confidence': pred['confidence'],
                            'x': pred['x'],
                            'y': pred['y'],
                            'width': pred['width'],
                            'height': pred['height']
                        })
                
                # Check for emergency vehicles
                has_emergency = any(
                    d['class'].lower() == 'emergency-vehicle' for d in detections
                )
                
                # Send response back to client
                await websocket.send_json({
                    'success': True,
                    'predictions': detections,
                    'processing_time': processing_time,
                    'road_id': road_id,
                    'has_emergency': has_emergency
                })
                
                # Send to Arduino if needed
                road_data = [{
                    'id': road_id,
                    'detections': detections,
                    'hasEmergencyVehicle': has_emergency
                }]
                
                async with arduino_lock:
                    if arduino_controller.connected:
                        await asyncio.get_event_loop().run_in_executor(
                            None, send_traffic_data, road_data
                        )
                            
            except Exception as e:
                print(f"WebSocket detection error: {e}")
                await websocket.send_json({
                    'success': False,
                    'error': str(e)
                })
                
    except WebSocketDisconnect:
        print("🔌 WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global startup_complete
    print("\n" + "="*60)
    print("🚀 STARTING VEHICLE DETECTION & TRAFFIC CONTROL SYSTEM")
    print("="*60)
    print("⏳ Initializing backend services...")
    
    # Give system time to fully initialize
    await asyncio.sleep(1)
    
    print("✅ Backend services ready!")
    print("🔌 Arduino connection available via web interface")
    print("🌐 Web interface can now connect to this backend")
    print("="*60)
    print("🎯 BACKEND READY FOR CONNECTIONS")
    print("="*60 + "\n")
    
    startup_complete = True
