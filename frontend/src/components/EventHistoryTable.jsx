import React, { useState, useEffect } from "react";
import { Database, RefreshCw, ChevronLeft, ChevronRight, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { API_BASE } from "../api.js";

export default function EventHistoryTable() {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize] = useState(8);
  const [severityFilter, setSeverityFilter] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: pageSize,
        offset: page * pageSize,
      });
      if (severityFilter) params.append("severity", severityFilter);

      const res = await fetch(`${API_BASE}/api/events?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      console.error("Error fetching event log:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [page, severityFilter]);

  const totalPages = Math.ceil(total / pageSize);

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-rose-500/20 text-rose-400 border-rose-500/40";
      case "WARNING":
        return "bg-amber-500/20 text-amber-400 border-amber-500/40";
      default:
        return "bg-sky-500/20 text-sky-400 border-sky-500/40";
    }
  };

  return (
    <div className="bg-brand-card/90 border border-brand-border rounded-xl p-5 flex flex-col space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-brand-border">
        <div className="flex items-center space-x-2">
          <Database className="h-4 w-4 text-sky-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-white">
            SQLite Incident & Alert Log
          </h2>
          <span className="text-xs text-slate-500 font-mono">
            ({total} total records)
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {/* Severity filter buttons */}
          <div className="flex space-x-1 bg-brand-panel p-1 rounded-lg border border-brand-border text-xs">
            {["", "CRITICAL", "WARNING", "INFO"].map((s) => (
              <button
                key={s}
                onClick={() => {
                  setSeverityFilter(s);
                  setPage(0);
                }}
                className={`px-2.5 py-1 rounded font-semibold transition ${
                  severityFilter === s
                    ? "bg-sky-500 text-slate-900"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {s === "" ? "ALL" : s}
              </button>
            ))}
          </div>

          <button
            onClick={fetchEvents}
            disabled={loading}
            className="p-1.5 bg-brand-panel hover:bg-brand-border border border-brand-border rounded-lg text-slate-300 transition"
            title="Refresh event log"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Events Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-brand-panel/60 text-slate-400 uppercase font-semibold border-b border-brand-border">
            <tr>
              <th className="px-4 py-2.5">ID</th>
              <th className="px-4 py-2.5">Timestamp</th>
              <th className="px-4 py-2.5">Severity</th>
              <th className="px-4 py-2.5">Alert Event</th>
              <th className="px-4 py-2.5">Message Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand-border/40 text-slate-300">
            {events.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-slate-500">
                  No alerts logged matching filter criteria.
                </td>
              </tr>
            ) : (
              events.map((evt) => (
                <tr key={evt.id} className="hover:bg-brand-panel/40 transition">
                  <td className="px-4 py-2.5 font-mono text-slate-500">#{evt.id}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-400 whitespace-nowrap">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getSeverityBadge(
                        evt.severity
                      )}`}
                    >
                      {evt.severity}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-white whitespace-nowrap">
                    {evt.alert_type}
                  </td>
                  <td className="px-4 py-2.5 text-slate-300 leading-relaxed">
                    {evt.message}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-brand-border text-xs text-slate-400">
        <div>
          Page {totalPages > 0 ? page + 1 : 0} of {totalPages}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="p-1 rounded bg-brand-panel border border-brand-border disabled:opacity-40 hover:bg-brand-border transition"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="p-1 rounded bg-brand-panel border border-brand-border disabled:opacity-40 hover:bg-brand-border transition"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

