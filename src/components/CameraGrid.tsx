import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { WebcamCapture } from "./WebcamCapture";
import { ArduinoController } from "./ArduinoController";
import {
  Maximize,
  Minimize,
  Camera,
  Grid3X3,
  Monitor,
  Play,
  Square,
  AlertTriangle,
  Settings,
  Eye,
  EyeOff,
} from "lucide-react";

interface Detection {
  class: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
  originalWidth?: number;
  originalHeight?: number;
}

interface CameraData {
  id: number;
  name: string;
  isActive: boolean;
  detections: Detection[];
  trafficCount: number;
  hasEmergencyVehicle: boolean;
}

const API_BASE_URL = "http://localhost:8000";

export const CameraGrid = () => {
  const [viewMode, setViewMode] = useState<"grid" | "single">("grid");
  const [fullscreenCamera, setFullscreenCamera] = useState<number | null>(null);
  // Remove global detection state, detection is now per camera/component
  const [arduinoConnected, setArduinoConnected] = useState(false);
  const [isDeveloperMode, setIsDeveloperMode] = useState(true);

  // Reset view mode when switching to User Mode
  useEffect(() => {
    if (!isDeveloperMode && viewMode === "single") {
      setViewMode("grid");
      setFullscreenCamera(null);
    }
  }, [isDeveloperMode, viewMode]);

  // Simple mode switching - don't interfere with camera state
  useEffect(() => {
    if (!isDeveloperMode) {
      // In User Mode, just ensure cameras are marked as active
      setCameras((prev) =>
        prev.map((camera) => ({
          ...camera,
          isActive: true,
        }))
      );
    }
  }, [isDeveloperMode]);
  const [cameras, setCameras] = useState<CameraData[]>([
    {
      id: 1,
      name: "Lane 1 - North",
      isActive: false,
      detections: [],
      trafficCount: 0,
      hasEmergencyVehicle: false,
    },
    {
      id: 2,
      name: "Lane 2 - South",
      isActive: false,
      detections: [],
      trafficCount: 0,
      hasEmergencyVehicle: false,
    },
    {
      id: 3,
      name: "Lane 3 - East",
      isActive: false,
      detections: [],
      trafficCount: 0,
      hasEmergencyVehicle: false,
    },
    {
      id: 4,
      name: "Lane 4 - West",
      isActive: false,
      detections: [],
      trafficCount: 0,
      hasEmergencyVehicle: false,
    },
  ]);

  // Send traffic data to Arduino every 2 seconds when connected
  useEffect(() => {
    if (arduinoConnected) {
      const interval = setInterval(sendTrafficDataToArduino, 1000);
      return () => clearInterval(interval);
    }
  }, [arduinoConnected, cameras]);

  // Batch detection for multiple cameras
  const [batchDetectionQueue, setBatchDetectionQueue] = useState<
    Array<{
      cameraId: number;
      imageData: string;
      timestamp: number;
    }>
  >([]);

  // Process batch detections every 500ms
  // Remove batch detection effect tied to globalDetectionActive

  const sendTrafficDataToArduino = async () => {
    try {
      const roadData = cameras.map((camera) => ({
        id: camera.id,
        detections: camera.detections,
        hasEmergencyVehicle: camera.hasEmergencyVehicle,
        isActive: camera.isActive,
      }));

      await fetch(`${API_BASE_URL}/arduino/update_traffic`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ road_data: roadData }),
      });
    } catch (error) {
      console.error("Failed to send traffic data to Arduino:", error);
    }
  };

  const handleDetectionUpdate = (
    cameraId: number,
    predictions: Detection[]
  ) => {
    setCameras((prev) =>
      prev.map((camera) => {
        if (camera.id === cameraId) {
          const hasEmergency = predictions.some(
            (detection) =>
              detection.class.toLowerCase().includes("ambulance") ||
              detection.class.toLowerCase().includes("emergency") ||
              detection.class.toLowerCase().includes("fire") ||
              detection.class.toLowerCase().includes("police")
          );

          return {
            ...camera,
            detections: predictions,
            trafficCount: camera.trafficCount + predictions.length,
            hasEmergencyVehicle: hasEmergency,
          };
        }
        return camera;
      })
    );
  };

  const handleStatusChange = (cameraId: number, isActive: boolean) => {
    setCameras((prev) =>
      prev.map((camera) => {
        if (camera.id === cameraId) {
          return {
            ...camera,
            isActive,
            hasEmergencyVehicle: isActive ? camera.hasEmergencyVehicle : false,
            detections: isActive ? camera.detections : [],
          };
        }
        return camera;
      })
    );
  };

  // Remove startAllCameras and stopAllCameras, detection is per camera

  const getHighestTrafficCamera = () => {
    const activeCameras = cameras.filter((camera) => camera.isActive);
    if (activeCameras.length === 0) return null;

    return activeCameras.reduce((prev, current) =>
      current.trafficCount > prev.trafficCount ? current : prev
    );
  };

  const getTrafficSignalColor = (camera: CameraData) => {
    if (!camera.isActive) {
      return "border-red-500";
    }

    const emergencyCamera = cameras.find(
      (cam) => cam.isActive && cam.hasEmergencyVehicle
    );

    if (emergencyCamera) {
      return camera.hasEmergencyVehicle ? "border-green-500" : "border-red-500";
    } else {
      const highestTrafficCamera = getHighestTrafficCamera();
      return highestTrafficCamera && camera.id === highestTrafficCamera.id
        ? "border-green-500"
        : "border-red-500";
    }
  };

  const getEmergencyLanes = () => {
    return cameras.filter(
      (camera) => camera.isActive && camera.hasEmergencyVehicle
    );
  };

  const toggleFullscreen = (cameraId: number) => {
    if (fullscreenCamera === cameraId) {
      setFullscreenCamera(null);
      setViewMode("grid");
    } else {
      setFullscreenCamera(cameraId);
      setViewMode("single");
    }
  };

  const switchToCamera = (cameraId: number) => {
    setFullscreenCamera(cameraId);
    setViewMode("single");
  };

  const highestTrafficCamera = getHighestTrafficCamera();
  const emergencyLanes = getEmergencyLanes();
  const activeCameraCount = cameras.filter((c) => c.isActive).length;

  const addToBatchQueue = (cameraId: number, imageData: string) => {
    setBatchDetectionQueue((prev) => [
      ...prev,
      {
        cameraId,
        imageData,
        timestamp: Date.now(),
      },
    ]);
  };

  const stopCamera = (cameraId: number) => {
    setCameras((prev) =>
      prev.map((camera) => {
        if (camera.id === cameraId) {
          return {
            ...camera,
            isActive: false,
            detections: [],
            hasEmergencyVehicle: false,
            trafficCount: 0,
          };
        }
        return camera;
      })
    );
  };

  return (
    <div className="space-y-4">
      {/* Mode Toggle - Minimal for User Mode */}
      <div className="flex justify-end">
        <Card className="bg-black/40 backdrop-blur-md border-white/20">
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                {isDeveloperMode ? (
                  <Settings className="h-4 w-4 text-blue-400" />
                ) : (
                  <Eye className="h-4 w-4 text-green-400" />
                )}
                <span className="text-white text-sm font-medium">
                  {isDeveloperMode ? "Developer Mode" : "User Mode"}
                </span>
              </div>
              <Switch
                checked={isDeveloperMode}
                onCheckedChange={setIsDeveloperMode}
                className="data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-green-600"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Developer Mode Content */}
      {isDeveloperMode && (
        <>
          {/* Arduino Controller - Only show in Developer Mode */}
          <ArduinoController onConnectionChange={setArduinoConnected} />

          {/* Control Panel */}
          <Card className="bg-black/40 backdrop-blur-md border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center justify-between">
                <div className="flex items-center">
                  <Monitor className="h-5 w-5 mr-2" />
                  Traffic Management Control Panel
                  {arduinoConnected && (
                    <Badge className="ml-2 bg-green-600 text-white">
                      Hardware Connected
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      setViewMode("grid");
                      setFullscreenCamera(null);
                    }}
                    variant={viewMode === "grid" ? "default" : "outline"}
                    size="sm"
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                  >
                    <Grid3X3 className="h-4 w-4 mr-1" />
                    Grid View
                  </Button>
                  {[1, 2, 3, 4].map((num) => (
                    <Button
                      key={num}
                      onClick={() => switchToCamera(num)}
                      variant={fullscreenCamera === num ? "default" : "outline"}
                      size="sm"
                      className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                    >
                      Lane {num}
                    </Button>
                  ))}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="text-sm text-purple-200 space-y-1">
                  {emergencyLanes.length > 0 ? (
                    <div className="flex items-center text-red-400">
                      <AlertTriangle className="h-4 w-4 mr-2" />
                      <span>
                        EMERGENCY OVERRIDE ACTIVE - Lane(s):{" "}
                        {emergencyLanes.map((lane) => lane.name).join(", ")}
                      </span>
                    </div>
                  ) : activeCameraCount > 0 ? (
                    <span>
                      Normal Traffic Mode -{" "}
                      {highestTrafficCamera
                        ? `Highest Traffic: ${highestTrafficCamera.name} (${highestTrafficCamera.trafficCount} vehicles)`
                        : "Monitoring Traffic..."}
                    </span>
                  ) : (
                    <span>
                      All Cameras Stopped - Ready to Start Traffic Management
                    </span>
                  )}
                  {arduinoConnected && (
                    <div className="text-green-400">
                      🔌 Arduino hardware controlling physical traffic lights
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <Badge
                    variant="secondary"
                    className="bg-purple-600 text-white"
                  >
                    Active: {activeCameraCount}/4
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Traffic Signal Status */}
          <Card className="bg-black/40 backdrop-blur-md border-white/20">
            <CardHeader>
              <CardTitle className="text-white text-sm">
                Traffic Light Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                {cameras.map((camera) => {
                  const signalColor = getTrafficSignalColor(camera);
                  const isGreen = signalColor.includes("green");

                  return (
                    <div
                      key={camera.id}
                      className="flex items-center space-x-2"
                    >
                      <div
                        className={`w-4 h-4 rounded-full ${
                          isGreen ? "bg-green-500" : "bg-red-500"
                        } ${!camera.isActive ? "opacity-50" : ""}`}
                      ></div>
                      <span
                        className={`text-white text-xs ${
                          !camera.isActive ? "opacity-50" : ""
                        }`}
                      >
                        {camera.name} {isGreen ? "🟢" : "🔴"}
                      </span>
                      {camera.hasEmergencyVehicle && (
                        <AlertTriangle className="h-3 w-3 text-red-400" />
                      )}
                    </div>
                  );
                })}
              </div>
              {emergencyLanes.length > 0 && (
                <div className="mt-2 p-2 bg-red-900/30 rounded border border-red-500">
                  <div className="text-red-400 text-xs font-bold">
                    🚨 EMERGENCY VEHICLE DETECTED:{" "}
                    {emergencyLanes.map((lane) => lane.name).join(", ")} -
                    PRIORITY OVERRIDE ACTIVE
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* User Mode Content - Just cameras, no text or separation lines */}
      {!isDeveloperMode && (
        <div className="grid grid-cols-2 gap-4">
          {cameras.map((camera) => (
            <div key={`camera-${camera.id}`} className="relative w-full h-full">
              <WebcamCapture
                key={`webcam-${camera.id}`}
                cameraId={camera.id}
                onDetectionUpdate={(predictions) =>
                  handleDetectionUpdate(camera.id, predictions)
                }
                onStatusChange={(isActive) =>
                  handleStatusChange(camera.id, isActive)
                }
                showControls={false}
                initialDetectionActive={true}
              />
            </div>
          ))}
        </div>
      )}

      {/* Camera Display - Developer Mode Only */}
      {viewMode === "single" && fullscreenCamera && isDeveloperMode ? (
        <Card
          className={`bg-black/40 backdrop-blur-md border-4 ${getTrafficSignalColor(
            cameras.find((c) => c.id === fullscreenCamera)!
          )}`}
        >
          <CardHeader>
            <CardTitle className="text-white flex items-center justify-between">
              <div className="flex items-center">
                <Camera className="h-5 w-5 mr-2" />
                {cameras.find((c) => c.id === fullscreenCamera)?.name} -
                Fullscreen
                {cameras.find((c) => c.id === fullscreenCamera)
                  ?.hasEmergencyVehicle && (
                  <Badge className="ml-2 bg-red-600 text-white">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    EMERGENCY
                  </Badge>
                )}
              </div>
              <Button
                onClick={() => toggleFullscreen(fullscreenCamera)}
                variant="outline"
                size="sm"
                className="bg-white/10 border-white/20 text-white hover:bg-white/20"
              >
                <Minimize className="h-4 w-4 mr-1" />
                Minimize
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <WebcamCapture
              cameraId={fullscreenCamera}
              onDetectionUpdate={(predictions) =>
                handleDetectionUpdate(fullscreenCamera, predictions)
              }
              onStatusChange={(isActive) =>
                handleStatusChange(fullscreenCamera, isActive)
              }
            />
          </CardContent>
        </Card>
      ) : isDeveloperMode ? (
        <div className="grid grid-cols-2 gap-4">
          {cameras.map((camera) => (
            <Card
              key={`camera-card-${camera.id}`}
              className={`bg-black/40 backdrop-blur-md border-4 ${getTrafficSignalColor(
                camera
              )}`}
            >
              <CardHeader>
                <CardTitle className="text-white flex items-center justify-between text-sm">
                  <div className="flex items-center">
                    <Camera className="h-4 w-4 mr-2" />
                    {camera.name}
                    <Badge
                      variant="secondary"
                      className={`ml-2 ${
                        camera.isActive ? "bg-green-600" : "bg-gray-600"
                      } text-white`}
                    >
                      {camera.isActive ? "Active" : "Inactive"}
                    </Badge>
                    {camera.hasEmergencyVehicle && (
                      <Badge className="ml-1 bg-red-600 text-white">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        EMERGENCY
                      </Badge>
                    )}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-2">
                <WebcamCapture
                  key={`webcam-dev-${camera.id}`}
                  cameraId={camera.id}
                  onDetectionUpdate={(predictions) =>
                    handleDetectionUpdate(camera.id, predictions)
                  }
                  onStatusChange={(isActive) =>
                    handleStatusChange(camera.id, isActive)
                  }
                />
                <div className="mt-2 text-xs text-purple-200">
                  Vehicles: {camera.detections.length} | Total:{" "}
                  {camera.trafficCount}
                  {camera.hasEmergencyVehicle && (
                    <span className="text-red-400 ml-2">
                      ⚠️ Emergency Vehicle Present
                    </span>
                  )}
                  {!camera.isActive && (
                    <span className="text-gray-400 ml-2">• Camera Stopped</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {/* Fallback for User Mode when view mode is single */}
      {viewMode === "single" && fullscreenCamera && !isDeveloperMode && (
        <div className="grid grid-cols-2 gap-4 h-screen">
          {cameras.map((camera) => (
            <div
              key={camera.id}
              className={`relative border-4 ${getTrafficSignalColor(camera)}`}
            >
              <WebcamCapture
                cameraId={camera.id}
                onDetectionUpdate={(predictions) =>
                  handleDetectionUpdate(camera.id, predictions)
                }
                onStatusChange={(isActive) =>
                  handleStatusChange(camera.id, isActive)
                }
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
