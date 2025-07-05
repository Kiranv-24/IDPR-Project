#include <ArduinoJson.h>

// Configuration
#define BASE_GREEN_DELAY 5000
#define MAX_GREEN_DELAY 15000
#define MIN_GREEN_DELAY 3000
#define YELLOW_DELAY 2000
#define VEHICLE_FACTOR 300
#define NUM_ROADS 4

// LED Pins
const int greenLEDs[NUM_ROADS] = {4, 7, 10, 13};
const int yellowLEDs[NUM_ROADS] = {3, 6, 9, 12};
const int redLEDs[NUM_ROADS] = {2, 5, 8, 11};

// Traffic data
int vehicleCounts[NUM_ROADS] = {0};
bool emergencyStatus[NUM_ROADS] = {false};

// System state
bool trafficSystemRunning = false;
int currentRoad = -1;
unsigned long greenEndTime = 0;
bool greenActive = false;

// Function prototypes
void sendJsonMessage(String message, bool includeStatus = false);
void handleSerialCommands();
void parseUpdateCommand(String cmd);
int getHighestPriorityRoad();
void startGreenLight(int road);
void endGreenLight(int road);
void allRedLights();

void setup() {
  Serial.begin(9600);
  while (!Serial); // Ensure serial is ready
  delay(1000); // Wait a bit after boot

  Serial.println("[BOOT] Arduino Mega Traffic Controller starting...");

  // Initialize pins
  for (int i = 0; i < NUM_ROADS; i++) {
    pinMode(greenLEDs[i], OUTPUT);
    pinMode(yellowLEDs[i], OUTPUT);
    pinMode(redLEDs[i], OUTPUT);
    digitalWrite(greenLEDs[i], LOW);
    digitalWrite(yellowLEDs[i], LOW);
    digitalWrite(redLEDs[i], HIGH);
  }

  Serial.println("[BOOT] All red lights ON");
  sendJsonMessage("Arduino Initialized", true);
  Serial.println("[BOOT] Ready to receive commands...");
}

void loop() {
  handleSerialCommands();

  if (trafficSystemRunning) {
    unsigned long now = millis();

    if (!greenActive) {
      int nextRoad = getHighestPriorityRoad();

      if (nextRoad != -1) {
        currentRoad = nextRoad;
        startGreenLight(currentRoad);
        greenActive = true;
      }
    }

    if (greenActive && now >= greenEndTime) {
      endGreenLight(currentRoad);
      greenActive = false;
      currentRoad = -1;
    }
  }
}

void sendJsonMessage(String message, bool includeStatus) {
  StaticJsonDocument<200> doc;
  doc["message"] = message;
  if (includeStatus) {
    doc["running"] = trafficSystemRunning;
    doc["currentRoad"] = currentRoad + 1;
  }

  serializeJson(doc, Serial);
  Serial.println(); // Ensure newline
  Serial.flush();   // Force send
}

void handleSerialCommands() {
  static String inputBuffer;

  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        Serial.print("[SERIAL] Received: ");
        Serial.println(inputBuffer);

        if (inputBuffer == "STATUS") {
          sendJsonMessage("System operational", true);
        } 
        else if (inputBuffer == "START") {
          trafficSystemRunning = true;
          sendJsonMessage("Traffic system started");
        } 
        else if (inputBuffer == "STOP") {
          trafficSystemRunning = false;
          allRedLights();
          greenActive = false;
          currentRoad = -1;
          sendJsonMessage("Traffic system stopped");
        } 
        else if (inputBuffer.startsWith("UPDATE:")) {
          parseUpdateCommand(inputBuffer);
        } 
        else {
          sendJsonMessage("Unknown command");
        }
      }
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}

void parseUpdateCommand(String cmd) {
  Serial.print("[UPDATE] Parsing command: ");
  Serial.println(cmd);

  cmd.replace("UPDATE:", "");
  int firstColon = cmd.indexOf(':');
  int secondColon = cmd.indexOf(':', firstColon + 1);

  if (firstColon == -1 || secondColon == -1) {
    sendJsonMessage("Invalid UPDATE format");
    return;
  }

  int road = cmd.substring(0, firstColon).toInt() - 1;
  int count = cmd.substring(firstColon + 1, secondColon).toInt();
  String emergencyStr = cmd.substring(secondColon + 1);

  if (road >= 0 && road < NUM_ROADS) {
    vehicleCounts[road] = count;
    emergencyStatus[road] = (emergencyStr == "true");

    String msg = "Updated Road " + String(road + 1) +
                 ": Vehicles=" + String(count) +
                 ", Emergency=" + (emergencyStatus[road] ? "true" : "false");
    sendJsonMessage(msg);
  } else {
    sendJsonMessage("Invalid road ID");
  }
}

int getHighestPriorityRoad() {
  for (int i = 0; i < NUM_ROADS; i++) {
    if (emergencyStatus[i]) {
      Serial.print("[PRIORITY] Emergency on Road ");
      Serial.println(i + 1);
      return i;
    }
  }

  int maxCount = 0;
  int selected = -1;
  for (int i = 0; i < NUM_ROADS; i++) {
    if (vehicleCounts[i] > maxCount) {
      maxCount = vehicleCounts[i];
      selected = i;
    }
  }

  if (selected != -1) {
    Serial.print("[PRIORITY] Selected Road ");
    Serial.println(selected + 1);
  }

  return selected;
}

void startGreenLight(int road) {
  int dynamicDelay = BASE_GREEN_DELAY + (vehicleCounts[road] * VEHICLE_FACTOR);
  dynamicDelay = constrain(dynamicDelay, MIN_GREEN_DELAY, MAX_GREEN_DELAY);
  greenEndTime = millis() + dynamicDelay;

  String msg = "Green light for Road " + String(road + 1) +
               " for " + String(dynamicDelay) + "ms";
  sendJsonMessage(msg);
  Serial.println("[LIGHT] Starting green phase");

  allRedLights();
  digitalWrite(redLEDs[road], LOW);
  digitalWrite(yellowLEDs[road], HIGH);
  delay(YELLOW_DELAY);
  digitalWrite(yellowLEDs[road], LOW);
  digitalWrite(greenLEDs[road], HIGH);

  Serial.print("[LIGHT] Green ON -> Road ");
  Serial.println(road + 1);
}

void endGreenLight(int road) {
  digitalWrite(greenLEDs[road], LOW);
  digitalWrite(yellowLEDs[road], HIGH);
  delay(YELLOW_DELAY);
  digitalWrite(yellowLEDs[road], LOW);
  digitalWrite(redLEDs[road], HIGH);

  Serial.print("[LIGHT] Green OFF -> Road ");
  Serial.println(road + 1);

  vehicleCounts[road] = 0;
  emergencyStatus[road] = false;
}

void allRedLights() {
  for (int i = 0; i < NUM_ROADS; i++) {
    digitalWrite(greenLEDs[i], LOW);
    digitalWrite(yellowLEDs[i], LOW);
    digitalWrite(redLEDs[i], HIGH);
  }
}
