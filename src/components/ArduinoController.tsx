// Enhanced ArduinoController.tsx with Better Delays and Stability
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Microchip, Wifi, WifiOff, Play, Square, Settings, Zap, AlertTriangle, Server, Terminal } from "lucide-react";

interface ArduinoControllerProps {
  onConnectionChange: (connected: boolean) => void;
}

const API_BASE_URL = "http://localhost:8000";

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const ArduinoController = ({ onConnectionChange }: ArduinoControllerProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [selectedPort, setSelectedPort] = useState("auto");
  const [availablePorts, setAvailablePorts] = useState<string[]>([]);
  const [systemActive, setSystemActive] = useState(false);
  const [error, setError] = useState("");
  const [backendReady, setBackendReady] = useState(false);
  const [backendChecking, setBackendChecking] = useState(true);

  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 15000); // Backend health check every 15 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (backendReady) {
      checkArduinoStatus();
      const interval = setInterval(checkArduinoStatus, 10000); // Arduino status every 10 seconds
      return () => clearInterval(interval);
    }
  }, [backendReady]);

  const checkBackendHealth = async () => {
    try {
      setBackendChecking(true);
      const response = await fetch(`${API_BASE_URL}/health`, { mode: "cors" });
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      const data = await response.json();
      setBackendReady(true);
      setError("");
    } catch (err) {
      setBackendReady(false);
      setError("⚠️ Python backend server is not running. Please start it first!");
    } finally {
      setBackendChecking(false);
    }
  };

  const checkArduinoStatus = async () => {
    if (!backendReady) return;
    try {
      const response = await fetch(`${API_BASE_URL}/arduino/status`, { method: "GET" });
      if (!response.ok) throw new Error("Arduino status check failed");
      const data = await response.json();
      setIsConnected(data.connected);
      setAvailablePorts(data.available_ports || []);
      onConnectionChange(data.connected);
    } catch (err) {
      setIsConnected(false);
      onConnectionChange(false);
    }
  };

  const connectArduino = async () => {
    if (!backendReady) {
      setError("❌ Cannot connect Arduino: Python backend is not running!");
      return;
    }
    setIsConnecting(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/arduino/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port: selectedPort === "auto" ? null : selectedPort }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to connect to Arduino");
      await delay(5000); // Increased delay after successful connection
      setIsConnected(true);
      onConnectionChange(true);
      setError("");
      await delay(2000);
      checkArduinoStatus();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to connect to Arduino";
      setError(`❌ ${msg}`);
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnectArduino = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/arduino/disconnect`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to disconnect");
      setIsConnected(false);
      setSystemActive(false);
      onConnectionChange(false);
    } catch (err) {
      setError("❌ Disconnect failed");
    }
  };

  const startTrafficSystem = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/arduino/start`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to start traffic system");
      await delay(3000);
      setSystemActive(true);
    } catch (err) {
      setError("❌ Failed to start traffic system");
    }
  };

  const stopTrafficSystem = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/arduino/stop`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to stop traffic system");
      await delay(2000);
      setSystemActive(false);
    } catch (err) {
      setError("❌ Failed to stop traffic system");
    }
  };

  return (
    <Card className="bg-black/40 backdrop-blur-md border-white/20">
      <CardHeader>
        <CardTitle className="text-white flex items-center">
          <Microchip className="h-5 w-5 mr-2" />
          Arduino Traffic Controller
          {backendChecking ? (
            <Badge className="bg-yellow-600 animate-pulse ml-2">Checking...</Badge>
          ) : backendReady ? (
            isConnected ? (
              <Badge className="bg-green-600 ml-2">Connected</Badge>
            ) : (
              <Badge className="bg-blue-600 ml-2">Ready</Badge>
            )
          ) : (
            <Badge className="bg-red-600 ml-2">Backend Down</Badge>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {!backendReady && (
          <Alert className="bg-red-900/50 border-red-500 text-white">
            Start Python backend: <code>python run.py</code>
          </Alert>
        )}

        {error && (
          <Alert className="bg-red-900/50 border-red-500 text-white">
            {error}
          </Alert>
        )}

        {backendReady && !isConnected && (
          <div className="space-y-3">
            <Select value={selectedPort} onValueChange={setSelectedPort} disabled={isConnecting}>
              <SelectTrigger className="bg-white/10 border-white/20 text-white">
                <SelectValue placeholder="Select Port" />
              </SelectTrigger>
              <SelectContent className="bg-gray-800">
                <SelectItem value="auto">Auto-detect Arduino</SelectItem>
                {availablePorts.map(port => (
                  <SelectItem key={port} value={port}>{port}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button onClick={connectArduino} disabled={isConnecting} className="w-full bg-green-600">
              {isConnecting ? "Connecting..." : "Connect Arduino"}
            </Button>
          </div>
        )}

        {backendReady && isConnected && (
          <div className="space-y-3">
            <div className="flex gap-2">
              {systemActive ? (
                <Button onClick={stopTrafficSystem} className="flex-1 bg-red-600">Stop</Button>
              ) : (
                <Button onClick={startTrafficSystem} className="flex-1 bg-green-600">Start</Button>
              )}
              <Button onClick={disconnectArduino} variant="outline" className="flex-1 text-white">Disconnect</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
