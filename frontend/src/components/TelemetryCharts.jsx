import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { Activity, TrendingUp } from "lucide-react";

export default function TelemetryCharts({ offsetHistory = [], pedHistory = [] }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 1. Lane Lateral Offset Over Time Chart */}
      <div className="bg-brand-card/90 border border-brand-border rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Lateral Lane Offset (m)
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Warning at ±0.40m
          </span>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={offsetHistory}>
              <defs>
                <linearGradient id="offsetGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <YAxis
                domain={[-0.8, 0.8]}
                tick={{ fontSize: 10, fill: "#64748B" }}
                tickFormatter={(val) => `${val > 0 ? "+" : ""}${val.toFixed(1)}`}
                width={36}
              />
              <XAxis dataKey="t" hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#131B2A",
                  borderColor: "#2A364F",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(val) => [`${val.toFixed(2)} m`, "Offset"]}
              />
              <ReferenceLine y={0.4} stroke="#EF4444" strokeDasharray="3 3" />
              <ReferenceLine y={-0.4} stroke="#EF4444" strokeDasharray="3 3" />
              <ReferenceLine y={0.0} stroke="#475569" />
              <Area
                type="monotone"
                dataKey="offset"
                stroke="#10B981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#offsetGrad)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Tracked Pedestrian Activity Over Time */}
      <div className="bg-brand-card/90 border border-brand-border rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Activity className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Pedestrians Tracked (Rolling)
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            ByteTrack Persistent
          </span>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={pedHistory}>
              <YAxis
                domain={[0, "auto"]}
                allowDecimals={false}
                tick={{ fontSize: 10, fill: "#64748B" }}
                width={28}
              />
              <XAxis dataKey="t" hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#131B2A",
                  borderColor: "#2A364F",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(val) => [`${val}`, "Pedestrians"]}
              />
              <Line
                type="stepAfter"
                dataKey="count"
                stroke="#38BDF8"
                strokeWidth={2.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

