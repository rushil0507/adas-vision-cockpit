import React, { useState } from "react";
import { Sliders, Video, Upload, Settings2 } from "lucide-react";

export default function ControlsPanel({
  config = {},
  onUpdateSource,
  onUpdateConfig,
  onUploadVideo,
}) {
  const [sourceType, setSourceType] = useState(config.source?.type || "file");
  const [sourcePath, setSourcePath] = useState(config.source?.path || "data/samples/demo.mp4");
  const [laneMode, setLaneMode] = useState(config.lanes?.mode || "classical");
  const [pedConf, setPedConf] = useState(config.pedestrian?.conf ?? 0.4);
  const [riskDistance, setRiskDistance] = useState(
    config.pedestrian?.risk_distance_high_m ?? 8.0
  );
  const [uploading, setUploading] = useState(false);

  const handleApplySource = (e) => {
    e.preventDefault();
    onUpdateSource(sourceType, sourcePath);
  };

  const handleLaneModeChange = (mode) => {
    setLaneMode(mode);
    onUpdateConfig({ lanes: { mode } });
  };

  const handleConfChange = (val) => {
    const num = parseFloat(val);
    setPedConf(num);
    onUpdateConfig({ pedestrian: { conf: num } });
  };

  const handleRiskDistChange = (val) => {
    const num = parseFloat(val);
    setRiskDistance(num);
    onUpdateConfig({ pedestrian: { risk_distance_high_m: num } });
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await onUploadVideo(file);
      if (res && res.path) {
        setSourceType("file");
        setSourcePath(res.path);
        onUpdateSource("file", res.path);
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-brand-card/90 border border-brand-border rounded-xl p-5 flex flex-col space-y-5">
      <div className="flex items-center space-x-2 pb-3 border-b border-brand-border">
        <Sliders className="h-4 w-4 text-sky-400" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-white">
          Pipeline Controls & Parameters
        </h2>
      </div>

      {/* 1. Input Source Selection */}
      <form onSubmit={handleApplySource} className="space-y-3">
        <label className="text-xs font-semibold text-slate-300 block">
          Video Input Source
        </label>
        <div className="grid grid-cols-3 gap-2">
          {["file", "webcam", "rtsp"].map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => {
                setSourceType(type);
                if (type === "webcam") setSourcePath("0");
                else if (type === "file") setSourcePath("data/samples/demo.mp4");
              }}
              className={`py-1.5 px-3 rounded-lg text-xs font-semibold uppercase border transition ${
                sourceType === type
                  ? "bg-sky-500/20 border-sky-400 text-sky-300"
                  : "bg-brand-panel border-brand-border text-slate-400 hover:text-slate-200"
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        <div className="flex space-x-2">
          <input
            type="text"
            value={sourcePath}
            onChange={(e) => setSourcePath(e.target.value)}
            placeholder={
              sourceType === "webcam"
                ? "Device Index (e.g. 0)"
                : sourceType === "rtsp"
                ? "rtsp://..."
                : "Path to video file..."
            }
            className="flex-1 bg-brand-panel border border-brand-border rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-sky-400"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-sky-500 hover:bg-sky-400 text-slate-900 rounded-lg text-xs font-bold transition"
          >
            Switch
          </button>
        </div>

        {/* Video File Uploader */}
        <div className="pt-1">
          <label className="flex items-center justify-center space-x-2 w-full py-2 border border-dashed border-brand-border rounded-lg text-xs text-slate-400 hover:border-sky-400/60 hover:text-slate-200 cursor-pointer bg-brand-panel/40 transition">
            <Upload className="h-3.5 w-3.5 text-sky-400" />
            <span>{uploading ? "Uploading Video..." : "Upload Local Dashcam Video (.mp4)"}</span>
            <input
              type="file"
              accept="video/mp4,video/avi"
              onChange={handleFileUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
        </div>
      </form>

      {/* 2. Lane Detection Mode Toggle */}
      <div className="space-y-2 pt-2 border-t border-brand-border">
        <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
          <span>Lane Algorithm Mode</span>
          <span className="text-[10px] font-mono text-sky-400 uppercase font-bold">
            {laneMode}
          </span>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleLaneModeChange("classical")}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold border transition ${
              laneMode === "classical"
                ? "bg-emerald-500/20 border-emerald-400 text-emerald-300"
                : "bg-brand-panel border-brand-border text-slate-400 hover:text-slate-200"
            }`}
          >
            Classical (Sliding Window)
          </button>
          <button
            type="button"
            onClick={() => handleLaneModeChange("deep")}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold border transition ${
              laneMode === "deep"
                ? "bg-sky-500/20 border-sky-400 text-sky-300"
                : "bg-brand-panel border-brand-border text-slate-400 hover:text-slate-200"
            }`}
          >
            Deep Learning (Seg)
          </button>
        </div>
      </div>

      {/* 3. Pedestrian Confidence Slider */}
      <div className="space-y-2 pt-2 border-t border-brand-border">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">
            Pedestrian Confidence Threshold
          </span>
          <span className="font-mono text-sky-400 font-bold">
            {(pedConf * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min="0.10"
          max="0.90"
          step="0.05"
          value={pedConf}
          onChange={(e) => handleConfChange(e.target.value)}
          className="w-full accent-sky-400 bg-brand-panel cursor-pointer"
        />
      </div>

      {/* 4. Danger Zone Distance Slider */}
      <div className="space-y-2 pt-2 border-t border-brand-border">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">
            High Risk Braking Distance
          </span>
          <span className="font-mono text-rose-400 font-bold">
            {riskDistance.toFixed(1)} m
          </span>
        </div>
        <input
          type="range"
          min="4.0"
          max="20.0"
          step="1.0"
          value={riskDistance}
          onChange={(e) => handleRiskDistChange(e.target.value)}
          className="w-full accent-rose-500 bg-brand-panel cursor-pointer"
        />
      </div>
    </div>
  );
}

