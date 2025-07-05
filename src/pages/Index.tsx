import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CameraGrid } from "@/components/CameraGrid";
import { DetectionStats } from "@/components/DetectionStats";
import { ModelInfo } from "@/components/ModelInfo";
import { Camera, Activity, BarChart3, Settings } from "lucide-react";

const Index = () => {
  const [totalDetections, setTotalDetections] = useState(0);
  const [processingTimes, setProcessingTimes] = useState<number[]>([]);
  const [detectionCounts, setDetectionCounts] = useState<number[]>([]);
  const [isSystemActive, setIsSystemActive] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-600 rounded-lg">
                <Camera className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Multi-Camera Vehicle Detection System</h1>
                <p className="text-purple-200 text-sm">Real-time Traffic Management & Analysis - 4 Camera Grid</p>
              </div>
            </div>
            <Badge variant="secondary" className="bg-green-600 text-white">
              <Activity className="h-4 w-4 mr-1" />
              Multi-Cam Active
            </Badge>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Camera Grid */}
          <div className="lg:col-span-3">
            <CameraGrid />
          </div>

          {/* Side Panel */}
          <div className="space-y-6">
            {/* Performance Monitoring */}
            <DetectionStats 
              processingTimes={processingTimes}
              detectionCounts={detectionCounts}
              isActive={isSystemActive}
            />
            
            {/* Model Information */}
            <ModelInfo />
            
            {/* System Statistics */}
            <Card className="bg-black/40 backdrop-blur-md border-white/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <BarChart3 className="h-5 w-5 mr-2" />
                  System Stats
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-sm text-purple-200">
                  <p>Multi-Camera Mode: 4-Split Screen</p>
                  <p>Auto-Focus: Highest Traffic Camera</p>
                  <p>Model: Roboflow 3.0 Object Detection</p>
                  <p>Real-time Processing: Active</p>
                  <p>Optimized Performance: Enabled</p>
                </div>
              </CardContent>
            </Card>

            {/* Controls */}
            <Card className="bg-black/40 backdrop-blur-md border-white/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <Settings className="h-5 w-5 mr-2" />
                  System Controls
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  onClick={() => {
                    setTotalDetections(0);
                    setProcessingTimes([]);
                    setDetectionCounts([]);
                  }}
                  variant="outline"
                  className="w-full bg-white/10 border-white/20 text-white hover:bg-white/20"
                >
                  Reset All Statistics
                </Button>
                <div className="text-sm text-purple-200">
                  <p>• Click Grid View for 4-camera layout</p>
                  <p>• Click Cam 1-4 for single camera</p>
                  <p>• Use maximize/minimize controls</p>
                  <p>• System auto-highlights high traffic</p>
                  <p>• Performance monitoring active</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
