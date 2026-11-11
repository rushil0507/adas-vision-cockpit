"""Performance metrics, FPS tracking, and per-module profiling."""

import time
from collections import deque
from typing import Dict, Any


class FPSTracker:
    """Calculates smoothed running FPS and latency across a rolling window."""

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)
        self.last_frame_time = None
        self._fps = 0.0

    def tick(self) -> float:
        """Record a frame arrival and return current moving-average FPS."""
        now = time.perf_counter()
        self.timestamps.append(now)
        if len(self.timestamps) > 1:
            duration = self.timestamps[-1] - self.timestamps[0]
            if duration > 0:
                self._fps = (len(self.timestamps) - 1) / duration
        return self.fps

    @property
    def fps(self) -> float:
        return float(round(self._fps, 1))


class LatencyProfiler:
    """Profiles execution time for individual ADAS pipeline modules."""

    def __init__(self, history_len: int = 50):
        self.history_len = history_len
        self.timings: Dict[str, deque] = {
            "pedestrian_ms": deque(maxlen=history_len),
            "signs_ms": deque(maxlen=history_len),
            "lanes_ms": deque(maxlen=history_len),
            "fusion_ms": deque(maxlen=history_len),
            "overlay_ms": deque(maxlen=history_len),
            "total_ms": deque(maxlen=history_len),
        }
        self._start_times: Dict[str, float] = {}

    def start(self, section: str):
        self._start_times[section] = time.perf_counter()

    def stop(self, section: str) -> float:
        start_t = self._start_times.pop(section, None)
        if start_t is None:
            return 0.0
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        key = f"{section}_ms"
        if key not in self.timings:
            self.timings[key] = deque(maxlen=self.history_len)
        self.timings[key].append(elapsed_ms)
        return elapsed_ms

    def record(self, section: str, elapsed_ms: float):
        key = f"{section}_ms"
        if key not in self.timings:
            self.timings[key] = deque(maxlen=self.history_len)
        self.timings[key].append(elapsed_ms)

    def get_summary(self) -> Dict[str, Any]:
        """Return latest and average latency per section."""
        summary = {}
        for k, values in self.timings.items():
            if values:
                summary[k] = round(values[-1], 2)
                summary[f"{k}_avg"] = round(sum(values) / len(values), 2)
            else:
                summary[k] = 0.0
                summary[f"{k}_avg"] = 0.0
        return summary

