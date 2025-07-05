
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain, Zap, Target } from "lucide-react";

export const ModelInfo = () => {
  return (
    <Card className="bg-black/40 backdrop-blur-md border-white/20">
      <CardHeader>
        <CardTitle className="text-white flex items-center">
          <Brain className="h-5 w-5 mr-2" />
          Model Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-purple-200 text-sm">Model Type</span>
          <Badge variant="secondary" className="bg-blue-600 text-white">
            Roboflow 3.0
          </Badge>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-purple-200 text-sm">Detection Mode</span>
          <Badge variant="secondary" className="bg-green-600 text-white">
            Object Detection
          </Badge>
        </div>
        
        <div className="bg-black/30 rounded-lg p-3 space-y-2">
          <div className="flex items-center text-purple-200 text-sm">
            <Target className="h-4 w-4 mr-2" />
            <span>mAP@50: 99.5%</span>
          </div>
          <div className="flex items-center text-purple-200 text-sm">
            <Zap className="h-4 w-4 mr-2" />
            <span>Precision: 99.9%</span>
          </div>
          <div className="flex items-center text-purple-200 text-sm">
            <Target className="h-4 w-4 mr-2" />
            <span>Recall: 100%</span>
          </div>
        </div>
        
        <div className="text-xs text-purple-300">
          <p>Optimized for real-time vehicle detection and traffic analysis</p>
        </div>
      </CardContent>
    </Card>
  );
};
