/**
 * Backend API & WebSocket Endpoint Configuration
 *
 * Defaults to relative paths for local development and self-hosted FastAPI serving.
 * On external hosting (such as Netlify), set VITE_API_URL and VITE_WS_URL in environment variables.
 */

export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

export const getWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    const wsBase = import.meta.env.VITE_WS_URL.replace(/\/+$/, "");
    return `${wsBase}/ws/stream`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/ws/stream`;
};
