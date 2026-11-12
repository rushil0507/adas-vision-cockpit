import React, { useRef } from "react";
import { Maximize2, AlertTriangle, VideoOff } from "lucide-react";

export default function LiveFeed({ frameBase64, alerts = [], fps = 0 }) {
  const containerRef = useRef(null);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch((err) => {
        console.error(`Error attempting fullscreen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  const topAlert = alerts.length > 0 ? alerts[0] : null;

  return (
    <div
      ref={containerRef}
      className="relative bg-slate-950 rounded-2xl overflow-hidden border border-brand-border aspect-video flex items-center justify-center shadow-2xl group"
    >
      {frameBase64 ? (
        <img
          src={frameBase64}
          alt="ADAS Annotated Video Stream"
          className="w-full h-full object-contain"
        />
      ) : (
        <div className="flex flex-col items-center justify-center p-6 text-center space-y-3 text-slate-500 max-w-md">
          <VideoOff className="h-10 w-10 animate-pulse text-slate-600" />
          <p className="text-sm font-medium text-slate-300">
            Waiting for WebSocket video stream...
          </p>
          <span className="text-xs text-slate-500">
            Connecting to ADAS backend at <code>/ws/stream</code>
          </span>
          <div className="pt-2 text-[11px] text-slate-500 bg-slate-900/60 border border-brand-border/60 rounded-lg p-2.5">
            <strong>Viewing on Netlify?</strong> Connect your local or cloud backend by clicking the{" "}
            <span className="text-sky-400 font-semibold">Backend</span> button in the top navbar.
          </div>
        </div>
      )}

      {/* Floating Active Alert Banner */}
      {topAlert && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 max-w-lg w-11/12">
          <div
            className={`px-4 py-2.5 rounded-xl shadow-lg flex items-center space-x-3 text-white border backdrop-blur animate-bounce ${
              topAlert.severity === "CRITICAL"
                ? "bg-rose-600/90 border-rose-400 shadow-rose-900/50"
                : topAlert.severity === "WARNING"
                ? "bg-amber-600/90 border-amber-400 shadow-amber-900/50"
                : "bg-sky-600/90 border-sky-400 shadow-sky-900/50"
            }`}
          >
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <div className="text-sm font-bold tracking-wide">
              [{topAlert.severity}] {topAlert.message}
            </div>
          </div>
        </div>
      )}

      {/* Hover action overlay */}
      <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity z-20">
        <button
          onClick={toggleFullscreen}
          className="bg-brand-panel/80 hover:bg-brand-panel text-slate-300 hover:text-white p-2 rounded-lg border border-brand-border backdrop-blur transition"
          title="Toggle Fullscreen"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

