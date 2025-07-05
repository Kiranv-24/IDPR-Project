import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Clock, Zap, TrendingUp, AlertTriangle } from "lucide-react";

interface DetectionStatsProps {
  processingTimes: number[];
  detectionCounts: number[];
  isActive: boolean;
}

export const DetectionStats = ({ processingTimes, detectionCounts, isActive }: DetectionStatsProps) => {
  const [avgProcessingTime, setAvgProcessingTime] = useState(0);
  const [totalDetections, setTotalDetections] = useState(0);
  const [detectionRate, setDetectionRate] = useState(0);
  const [performanceStatus, setPerformanceStatus] = useState<'excellent' | 'good' | 'poor'>('good');

  useEffect(() => {
    if (processingTimes.length > 0) {
      const avg = processingTimes.reduce((a, b) => a + b, 0) / processingTimes.length;
      setAvgProcessingTime(avg);
      
      // Performance classification
      if (avg < 0.5) setPerformanceStatus('excellent');
      else if (avg < 1.0) setPerformanceStatus('good');
      else setPerformanceStatus('poor');
    }
  }, [processingTimes]);

  useEffect(() => {
    if (detectionCounts.length > 0) {
      const total = detectionCounts.reduce((a, b) => a + b, 0);
      setTotalDetections(total);
      
      // Calculate detection rate (detections per second)
      const recentCounts = detectionCounts.slice(-10); // Last 10 detections
      const rate = recentCounts.reduce((a, b) => a + b, 0) / Math.max(recentCounts.length, 1);
      setDetectionRate(rate);
    }
  }, [detectionCounts]);

  const getPerformanceColor = () => {
    switch (performanceStatus) {
      case 'excellent': return 'text-green-400';
      case 'good': return 'text-yellow-400';
      case 'poor': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getPerformanceIcon = () => {
    switch (performanceStatus) {
      case 'excellent': return <Zap className="h-4 w-4" />;
      case 'good': return <Activity className="h-4 w-4" />;
      case 'poor': return <AlertTriangle className="h-4 w-4" />;
      default: return <Activity className="h-4 w-4" />;
    }
  };

  return (
    <Card className="bg-black/40 backdrop-blur-md border-white/20">
      <CardHeader>
        <CardTitle className="text-white flex items-center">
          <TrendingUp className="h-5 w-5 mr-2" />
          Performance Metrics
          {isActive && (
            <Badge className="ml-2 bg-green-600 text-white">
              <Activity className="h-3 w-3 mr-1" />
              Active
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-white">
              {avgProcessingTime.toFixed(2)}s
            </div>
            <div className="text-xs text-gray-400">Avg Processing Time</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">
              {detectionRate.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400">Detections/sec</div>
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {getPerformanceIcon()}
            <span className={`ml-2 text-sm ${getPerformanceColor()}`}>
              {performanceStatus.charAt(0).toUpperCase() + performanceStatus.slice(1)} Performance
            </span>
          </div>
          <div className="text-right">
            <div className="text-sm text-white">{totalDetections}</div>
            <div className="text-xs text-gray-400">Total Detections</div>
          </div>
        </div>

        {performanceStatus === 'poor' && (
          <div className="p-2 bg-red-900/30 rounded border border-red-500">
            <div className="text-red-400 text-xs">
              ⚠️ Slow detection detected. Consider:
              <ul className="mt-1 ml-4 list-disc">
                <li>Reducing image quality</li>
                <li>Lowering frame rate</li>
                <li>Checking network connection</li>
              </ul>
            </div>
          </div>
        )}

        {performanceStatus === 'excellent' && (
          <div className="p-2 bg-green-900/30 rounded border border-green-500">
            <div className="text-green-400 text-xs">
              ⚡ Optimal performance achieved! System running at peak efficiency.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
