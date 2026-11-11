import React from "react";
import { Play, Square, Activity, ShieldAlert, Cpu } from "lucide-react";

export default function Navbar({
  isConnected,
  isRunning,
  fps,
  onStart,
  onStop,
  hasActiveAlert,
}) {
  return (
    <header className="border-b border-brand-border bg-brand-panel/80 backdrop-blur px-6 py-3.5 sticky top-0 z-50 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="h-9 w-9 rounded-lg bg-sky-500/20 border border-sky-400/40 flex items-center justify-center text-sky-400">
          <Activity className="h-5 w-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-lg font-bold tracking-tight text-white">
              ADAS Vision Cockpit
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20">
              v1.0 Real-Time
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Road Signs • Lane Markings • ByteTrack Pedestrian Kinematics
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Connection status indicator */}
        <div className="flex items-center space-x-2 bg-brand-card px-3 py-1.5 rounded-lg border border-brand-border">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              isConnected
                ? "bg-emerald-400 animate-ping"
                : "bg-rose-500"
            }`}
          />
          <span className="text-xs font-medium text-slate-300">
            {isConnected ? "WS Live Stream" : "Disconnected"}
          </span>
          <span className="text-xs text-slate-500 font-mono">
            {fps ? `${fps.toFixed(1)} FPS` : "0.0 FPS"}
          </span>
        </div>

        {/* Start / Stop Controls */}
        {isRunning ? (
          <button
            onClick={onStop}
            className="flex items-center space-x-1.5 px-4 py-1.5 bg-rose-500/15 text-rose-300 border border-rose-500/30 hover:bg-rose-500/25 rounded-lg text-sm font-medium transition"
          >
            <Square className="h-4 w-4 fill-current" />
            <span>Pause Stream</span>
          </button>
        ) : (
          <button
            onClick={onStart}
            className="flex items-center space-x-1.5 px-4 py-1.5 bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 rounded-lg text-sm font-medium transition"
          >
            <Play className="h-4 w-4 fill-current" />
            <span>Resume Stream</span>
          </button>
        )}
      </div>
    </header>
  );
}

