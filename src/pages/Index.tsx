import { useState } from "react";
import { Camera } from "lucide-react";
import { CameraGrid } from "@/components/CameraGrid";

const Index = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-600 rounded-lg">
              <Camera className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">
                Multi-Camera Vehicle Detection System
              </h1>
              <p className="text-purple-200 text-sm">
                Real-time Traffic Management & Analysis - 4 Camera Grid
              </p>
            </div>
          </div>
        </div>
      </header>
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
          {/* Main Camera Grid - always full width */}
          <div className="lg:col-span-1">
            <CameraGrid />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
