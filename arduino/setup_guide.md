
# Arduino Traffic Light Controller Setup Guide

## Hardware Requirements
- Arduino Mega 2560
- 12 LEDs (3 per traffic light - Red, Yellow, Green)
- 12 Resistors (220Ω or 330Ω)
- Breadboard or PCB
- Jumper wires
- USB cable for Arduino

## Pin Connections
Based on your 4-road intersection setup:

### Road 1 (North) - Pins 22, 24, 26
- Pin 22: Red LED
- Pin 24: Yellow LED  
- Pin 26: Green LED

### Road 2 (South) - Pins 28, 30, 32
- Pin 28: Red LED
- Pin 30: Yellow LED
- Pin 32: Green LED

### Road 3 (East) - Pins 34, 36, 38
- Pin 34: Red LED
- Pin 36: Yellow LED
- Pin 38: Green LED

### Road 4 (West) - Pins 40, 42, 44
- Pin 40: Red LED
- Pin 42: Yellow LED
- Pin 44: Green LED

## Wiring Instructions
1. Connect each LED's cathode (shorter leg) to GND through a resistor
2. Connect each LED's anode (longer leg) to the corresponding Arduino pin
3. Ensure all connections are secure

## Software Setup
1. Install Arduino IDE from https://www.arduino.cc/en/software
2. Connect Arduino Mega to your computer via USB
3. Open Arduino IDE and select:
   - Board: Arduino Mega 2560
   - Port: (Select the appropriate COM port)
4. Copy the code from `traffic_controller.ino`
5. Upload the code to your Arduino
6. Open Serial Monitor (Tools > Serial Monitor) to verify communication

## Testing the System
1. Upload the Arduino code
2. Start the Python backend server
3. Connect to the web interface
4. Use the Arduino Controller panel to:
   - Connect to Arduino (auto-detects port)
   - Start the traffic system
   - The system will respond to vehicle detection data

## Serial Commands (for manual testing)
- `START` - Start the traffic control system
- `STOP` - Stop the traffic control system  
- `UPDATE:1:5:true` - Update road 1 with 5 vehicles and emergency vehicle
- `STATUS` - Get current system status

## Troubleshooting
- Check all LED connections if lights don't work
- Verify COM port in Arduino Controller
- Ensure Arduino IDE Serial Monitor is closed when using the web app
- Check that all resistors are properly connected
- Verify power supply is adequate

## Safety Notes
- Keep voltage levels appropriate for LEDs
- Double-check all connections before powering on
- Use appropriate resistor values to prevent LED burnout
