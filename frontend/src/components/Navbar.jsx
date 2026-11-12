import React, { useState } from "react";
import { Play, Square, Activity, Globe, Check, X, Server } from "lucide-react";
import { getBackendUrl, setBackendUrl } from "../api.js";

export default function Navbar({
  isConnected,
  isRunning,
  fps,
  onStart,
  onStop,
  hasActiveAlert,
}) {
  const [showServerModal, setShowServerModal] = useState(false);
  const [inputUrl, setInputUrl] = useState(getBackendUrl());

  const handleSaveUrl = (e) => {
    e.preventDefault();
    setBackendUrl(inputUrl);
    setShowServerModal(false);
    window.location.reload();
  };

  const handleResetUrl = () => {
    setBackendUrl("");
    setInputUrl("");
    setShowServerModal(false);
    window.location.reload();
  };

  const currentBackend = getBackendUrl() || "Same Host (Default)";

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

      <div className="flex items-center space-x-3">
        {/* Backend URL Config Button */}
        <button
          onClick={() => {
            setInputUrl(getBackendUrl());
            setShowServerModal(true);
          }}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-brand-card hover:bg-brand-panel text-slate-300 hover:text-white border border-brand-border rounded-lg text-xs font-medium transition"
          title="Configure Backend Server Address"
        >
          <Server className="h-3.5 w-3.5 text-sky-400" />
          <span className="hidden sm:inline">Backend:</span>
          <span className="font-mono text-sky-400 max-w-[120px] truncate">
            {getBackendUrl() ? new URL(getBackendUrl()).host : "Local"}
          </span>
        </button>

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

      {/* Backend Server Configuration Modal */}
      {showServerModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-brand-border rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-brand-border pb-3">
              <div className="flex items-center space-x-2">
                <Globe className="h-5 w-5 text-sky-400" />
                <h3 className="text-base font-bold text-white">Connect Backend Server</h3>
              </div>
              <button
                onClick={() => setShowServerModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              When hosting the frontend publicly on <strong>Netlify</strong>, enter the public HTTPS URL of your running ADAS backend (from a tunnel or cloud container).
            </p>

            <form onSubmit={handleSaveUrl} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Backend API & WebSocket Server URL:
                </label>
                <input
                  type="url"
                  placeholder="https://your-tunnel.loca.lt or https://adas-backend.railway.app"
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-brand-border rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-sky-500 transition"
                  autoFocus
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Current: <code className="text-slate-400">{currentBackend}</code>
                </span>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={handleResetUrl}
                  className="text-xs text-slate-400 hover:text-slate-200 underline transition"
                >
                  Reset to Default
                </button>
                <div className="flex space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowServerModal(false)}
                    className="px-3.5 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 rounded-lg transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-xs font-bold bg-sky-500 hover:bg-sky-400 text-slate-950 rounded-lg flex items-center space-x-1.5 shadow-lg shadow-sky-500/25 transition"
                  >
                    <Check className="h-4 w-4" />
                    <span>Save & Connect</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
}
