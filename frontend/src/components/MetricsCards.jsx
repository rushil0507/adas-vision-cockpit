import React from "react";
import { Gauge, Navigation, Users, Zap } from "lucide-react";

export default function MetricsCards({
  fps = 0,
  latencyMs = 0,
  lane = {},
  lastSpeedLimit = null,
  pedestrians = [],
}) {
  const offset = lane.offset_m ?? 0;
  const isDeparture = lane.departure;
  const curvature = lane.curvature_m;
  const highRiskCount = pedestrians.filter((p) => p.risk === "HIGH").length;
  const inZoneCount = pedestrians.filter((p) => p.in_danger_zone).length;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. FPS & Latency */}
      <div className="bg-brand-card/90 border border-brand-border rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">
            Inference Performance
          </span>
          <Zap className="h-4 w-4 text-sky-400" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-white font-mono">
            {fps ? fps.toFixed(1) : "0.0"}
          </span>
          <span className="text-sm font-semibold text-slate-400">FPS</span>
        </div>
        <div className="mt-2 text-xs text-slate-400 flex items-center justify-between">
          <span>End-to-End Latency:</span>
          <span className="font-mono text-slate-200">
            {latencyMs ? `${latencyMs.toFixed(1)} ms` : "--"}
          </span>
        </div>
      </div>

      {/* 2. Lane Offset & Curvature */}
      <div
        className={`border rounded-xl p-4 flex flex-col justify-between transition-colors ${
          isDeparture
            ? "bg-rose-950/30 border-rose-500/50"
            : "bg-brand-card/90 border-brand-border"
        }`}
      >
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">
            Lane Position (Offset)
          </span>
          <Navigation className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span
            className={`text-3xl font-extrabold font-mono ${
              isDeparture
                ? "text-rose-400 animate-pulse"
                : Math.abs(offset) > 0.25
                ? "text-amber-400"
                : "text-emerald-400"
            }`}
          >
            {offset !== null ? `${offset > 0 ? "+" : ""}${offset.toFixed(2)}` : "0.00"}
          </span>
          <span className="text-sm font-semibold text-slate-400">m</span>
          {isDeparture && (
            <span className="ml-auto text-xs font-bold uppercase bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded border border-rose-500/40">
              Departure
            </span>
          )}
        </div>
        <div className="mt-2 text-xs text-slate-400 flex items-center justify-between">
          <span>Radius of Curvature:</span>
          <span className="font-mono text-slate-200">
            {curvature ? (curvature > 4000 ? "Straight" : `${Math.round(curvature)} m`) : "--"}
          </span>
        </div>
      </div>

      {/* 3. Speed Limit HUD */}
      <div className="bg-brand-card/90 border border-brand-border rounded-xl p-4 flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1">
            Last Speed Limit
          </span>
          <p className="text-xs text-slate-400">Road Sign Recognition</p>
          <div className="mt-2 text-xs font-medium text-slate-300">
            {lastSpeedLimit ? "Active Advisory" : "Scanning..."}
          </div>
        </div>
        <div className="relative flex items-center justify-center">
          {lastSpeedLimit ? (
            <div className="h-14 w-14 rounded-full border-4 border-rose-500 bg-white flex items-center justify-center shadow-lg shadow-rose-500/20">
              <span className="text-xl font-black text-slate-900 font-mono">
                {lastSpeedLimit}
              </span>
            </div>
          ) : (
            <div className="h-14 w-14 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center text-slate-600 text-xs">
              None
            </div>
          )}
        </div>
      </div>

      {/* 4. Pedestrian Tracker Count */}
      <div
        className={`border rounded-xl p-4 flex flex-col justify-between transition-colors ${
          highRiskCount > 0
            ? "bg-rose-950/30 border-rose-500/50"
            : "bg-brand-card/90 border-brand-border"
        }`}
      >
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">
            Pedestrians Tracked
          </span>
          <Users className="h-4 w-4 text-sky-400" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span className="text-3xl font-extrabold text-white font-mono">
            {pedestrians.length}
          </span>
          <span className="text-sm font-semibold text-slate-400">active</span>
          {highRiskCount > 0 && (
            <span className="ml-auto text-xs font-bold uppercase bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded border border-rose-500/40 animate-pulse">
              {highRiskCount} High Risk
            </span>
          )}
        </div>
        <div className="mt-2 text-xs text-slate-400 flex items-center justify-between">
          <span>In Danger Zone:</span>
          <span
            className={`font-mono font-semibold ${
              inZoneCount > 0 ? "text-amber-400" : "text-slate-300"
            }`}
          >
            {inZoneCount}
          </span>
        </div>
      </div>
    </div>
  );
}

