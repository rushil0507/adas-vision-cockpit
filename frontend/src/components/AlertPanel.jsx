import React from "react";
import { AlertCircle, AlertTriangle, Info, Bell, CheckCircle2 } from "lucide-react";

export default function AlertPanel({ alerts = [] }) {
  const getSeverityBadge = (severity) => {
    switch (severity) {
      case "CRITICAL":
        return {
          icon: <AlertCircle className="h-4 w-4 text-rose-400" />,
          badgeClass: "bg-rose-500/20 text-rose-400 border-rose-500/40",
          itemClass: "border-l-4 border-l-rose-500 bg-rose-950/20",
        };
      case "WARNING":
        return {
          icon: <AlertTriangle className="h-4 w-4 text-amber-400" />,
          badgeClass: "bg-amber-500/20 text-amber-400 border-amber-500/40",
          itemClass: "border-l-4 border-l-amber-500 bg-amber-950/20",
        };
      default:
        return {
          icon: <Info className="h-4 w-4 text-sky-400" />,
          badgeClass: "bg-sky-500/20 text-sky-400 border-sky-500/40",
          itemClass: "border-l-4 border-l-sky-500 bg-sky-950/20",
        };
    }
  };

  return (
    <div className="bg-brand-card/90 border border-brand-border rounded-xl p-4 flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-brand-border mb-3">
        <div className="flex items-center space-x-2">
          <Bell className="h-4 w-4 text-sky-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-white">
            Active Safety Alerts
          </h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-brand-panel border border-brand-border text-slate-300">
          {alerts.length} active
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[380px] pr-1">
        {alerts.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-slate-500 space-y-2">
            <CheckCircle2 className="h-8 w-8 text-emerald-500/60" />
            <span className="text-xs font-medium text-slate-400">
              Corridor Clear. No Safety Incidents.
            </span>
          </div>
        ) : (
          alerts.map((alert, idx) => {
            const style = getSeverityBadge(alert.severity);
            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border border-brand-border/60 flex items-start space-x-3 transition-all ${style.itemClass}`}
              >
                <div className="mt-0.5 shrink-0">{style.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono font-bold text-slate-200 truncate">
                      {alert.type}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border ${style.badgeClass}`}
                    >
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {alert.message}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

