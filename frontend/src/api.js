/**
 * Backend API & WebSocket Endpoint Configuration
 *
 * Supports:
 * 1. User-customizable backend URL via localStorage ('adas_backend_url')
 * 2. Build-time environment variables (VITE_API_URL, VITE_WS_URL)
 * 3. Default relative paths for local development and self-hosted FastAPI
 */

export const getBackendUrl = () => {
  return localStorage.getItem("adas_backend_url") || import.meta.env.VITE_API_URL || "";
};

export const setBackendUrl = (url) => {
  if (url && url.trim().length > 0) {
    localStorage.setItem("adas_backend_url", url.trim().replace(/\/+$/, ""));
  } else {
    localStorage.removeItem("adas_backend_url");
  }
};

export const getApiBase = () => {
  const custom = getBackendUrl();
  return custom ? custom.replace(/\/+$/, "") : "";
};

export const getWsUrl = () => {
  const custom = getBackendUrl();
  if (custom) {
    const clean = custom.replace(/\/+$/, "");
    if (clean.startsWith("https://")) {
      return clean.replace(/^https:\/\//, "wss://") + "/ws/stream";
    }
    if (clean.startsWith("http://")) {
      return clean.replace(/^http:\/\//, "ws://") + "/ws/stream";
    }
    return clean + "/ws/stream";
  }

  if (import.meta.env.VITE_WS_URL) {
    const wsBase = import.meta.env.VITE_WS_URL.replace(/\/+$/, "");
    return `${wsBase}/ws/stream`;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/ws/stream`;
};

// Backwards-compatible export
export const API_BASE = getApiBase();
