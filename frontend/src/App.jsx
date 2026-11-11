import React, { useState, useEffect, useRef } from "react";
import Navbar from "./components/Navbar.jsx";
import MetricsCards from "./components/MetricsCards.jsx";
import LiveFeed from "./components/LiveFeed.jsx";
import AlertPanel from "./components/AlertPanel.jsx";
import TelemetryCharts from "./components/TelemetryCharts.jsx";
import ControlsPanel from "./components/ControlsPanel.jsx";
import EventHistoryTable from "./components/EventHistoryTable.jsx";
import { API_BASE, getWsUrl } from "./api.js";

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(true);
  const [frameData, setFrameData] = useState(null);
  const [config, setConfig] = useState({});
  const [offsetHistory, setOffsetHistory] = useState([]);
  const [pedHistory, setPedHistory] = useState([]);

  const wsRef = useRef(null);
  const historyIndexRef = useRef(0);

  // Fetch initial configuration
  const loadConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (e) {
      console.warn("Failed to fetch initial config:", e);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  // WebSocket lifecycle & reconnection
  useEffect(() => {
    let active = true;
    let reconnectTimeout = null;

    const connectWebSocket = () => {
      const wsUrl = getWsUrl();

      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        if (!active) return;
        setIsConnected(true);
        console.log("Connected to ADAS WebSocket stream at:", wsUrl);
      };

      socket.onmessage = (event) => {
        if (!active) return;
        try {
          const payload = JSON.parse(event.data);
          setFrameData(payload);

          // Append to rolling chart history (keep last 40 frames)
          const idx = historyIndexRef.current++;
          const offsetVal = payload.lane?.offset_m ?? 0.0;
          const pedCount = payload.pedestrians?.length ?? 0;

          setOffsetHistory((prev) => {
            const next = [...prev, { t: idx, offset: offsetVal }];
            return next.length > 40 ? next.slice(next.length - 40) : next;
          });

          setPedHistory((prev) => {
            const next = [...prev, { t: idx, count: pedCount }];
            return next.length > 40 ? next.slice(next.length - 40) : next;
          });
        } catch (e) {
          console.error("Error parsing WebSocket JSON payload:", e);
        }
      };

      socket.onclose = () => {
        if (!active) return;
        setIsConnected(false);
        console.warn("WebSocket disconnected. Retrying in 2.5s...");
        reconnectTimeout = setTimeout(connectWebSocket, 2500);
      };

      socket.onerror = (err) => {
        console.warn("WebSocket error:", err);
        socket.close();
      };
    };

    connectWebSocket();

    return () => {
      active = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleStart = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/start`, { method: "POST" });
      if (res.ok) setIsRunning(true);
    } catch (e) {
      console.error(e);
    }
  };

  const handleStop = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stop`, { method: "POST" });
      if (res.ok) setIsRunning(false);
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateSource = async (type, path) => {
    try {
      const res = await fetch(`${API_BASE}/api/source`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, path }),
      });
      if (res.ok) {
        loadConfig();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateConfig = async (patch) => {
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (res.ok) {
        loadConfig();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUploadVideo = async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      return await res.json();
    }
    throw new Error("Upload failed");
  };

  const fps = frameData?.fps ?? 0;
  const latencyMs = frameData?.metrics?.total_ms ?? 0;
  const lane = frameData?.lane ?? {};
  const lastSpeedLimit = frameData?.last_speed_limit ?? null;
  const pedestrians = frameData?.pedestrians ?? [];
  const alerts = frameData?.alerts ?? [];

  return (
    <div className="min-h-screen bg-brand-dark flex flex-col selection:bg-sky-500 selection:text-white">
      <Navbar
        isConnected={isConnected}
        isRunning={isRunning}
        fps={fps}
        onStart={handleStart}
        onStop={handleStop}
        hasActiveAlert={alerts.length > 0}
      />

      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 space-y-5">
        {/* Top 4 Real-Time Metrics Cards */}
        <MetricsCards
          fps={fps}
          latencyMs={latencyMs}
          lane={lane}
          lastSpeedLimit={lastSpeedLimit}
          pedestrians={pedestrians}
        />

        {/* Video Feed & Real-Time Alerts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-8">
            <LiveFeed
              frameBase64={frameData?.frame}
              alerts={alerts}
              fps={fps}
            />
          </div>
          <div className="lg:col-span-4">
            <AlertPanel alerts={alerts} />
          </div>
        </div>

        {/* Rolling Telemetry Line / Area Charts */}
        <TelemetryCharts
          offsetHistory={offsetHistory}
          pedHistory={pedHistory}
        />

        {/* Controls & Historical Incident Event Table */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-5">
            <ControlsPanel
              config={config}
              onUpdateSource={handleUpdateSource}
              onUpdateConfig={handleUpdateConfig}
              onUploadVideo={handleUploadVideo}
            />
          </div>
          <div className="lg:col-span-7">
            <EventHistoryTable />
          </div>
        </div>
      </main>

      <footer className="border-t border-brand-border py-4 px-6 text-center text-xs text-slate-500">
        ADAS Vision Cockpit — Autonomous Road Safety Pipeline (PyTorch • YOLOv8 • ByteTrack • OpenCV • FastAPI • React)
      </footer>
    </div>
  );
}

