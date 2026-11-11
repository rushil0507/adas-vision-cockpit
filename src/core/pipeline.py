"""ADAS Pipeline Coordinator: Ties together frame grabbing, perception modules, fusion, and visualization."""

import os
import yaml
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
import numpy as np

from src.core.frame_source import FrameGrabber
from src.modules.pedestrian import PedestrianModule
from src.modules.lanes import LaneModule
from src.modules.signs import RoadSignModule
from src.core.fusion import FusionEngine, Alert
from src.utils.visualization import Visualizer, frame_to_base64
from src.utils.metrics import FPSTracker, LatencyProfiler
from src.api.db import EventDatabase

logger = logging.getLogger(__name__)


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class ADASPipeline:
    """Master orchestrator running the end-to-end vision, perception, fusion, and HUD rendering pipeline."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        if not os.path.isabs(config_path):
            abs_cfg = os.path.join(PROJECT_ROOT, config_path)
            if os.path.exists(abs_cfg):
                config_path = abs_cfg
        self.config_path = config_path
        self.config = self._load_config(config_path)

        self.db = EventDatabase()
        self.fps_tracker = FPSTracker(window_size=30)
        self.profiler = LatencyProfiler(history_len=50)
        self.visualizer = Visualizer()

        # Perception & Fusion Modules
        self.pedestrian_module = PedestrianModule(self.config)
        self.lane_module = LaneModule(self.config)
        self.sign_module = RoadSignModule(self.config)
        self.fusion_engine = FusionEngine(self.config, db=self.db)

        # Frame Grabber and Concurrency
        self.grabber: Optional[FrameGrabber] = None
        self.running = False
        self.paused = False
        self.worker_thread: Optional[threading.Thread] = None

        # Listeners / Subscribers (e.g. WebSocket streamer)
        self._frame_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._latest_result: Optional[Dict[str, Any]] = None

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Loads YAML configuration with fallback defaults."""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        logger.warning(f"Configuration file {path} not found. Using default empty configuration.")
        return {}

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Registers a listener that receives frame results as they are processed."""
        if callback not in self._frame_callbacks:
            self._frame_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Deregisters a listener."""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)

    def get_latest_result(self) -> Optional[Dict[str, Any]]:
        return self._latest_result

    def get_stats(self) -> Dict[str, Any]:
        summary = self.profiler.get_summary()
        summary["fps"] = self.fps_tracker.fps
        summary["pipeline_running"] = self.running
        summary["pipeline_paused"] = self.paused
        return summary

    def update_config(self, new_cfg: Dict[str, Any]):
        """Updates module configurations dynamically without restarting pipeline."""
        if "pedestrian" in new_cfg:
            self.pedestrian_module.update_config(new_cfg["pedestrian"])
        if "lanes" in new_cfg:
            self.lane_module.update_config(new_cfg["lanes"])
        if "signs" in new_cfg:
            self.sign_module.update_config(new_cfg["signs"])
        if "alerts" in new_cfg:
            self.fusion_engine.update_config(new_cfg["alerts"])

    def set_source(self, source_type: str, path: Any):
        """Sets a new input source (file path, webcam index, or RTSP stream)."""
        was_running = self.running
        if self.running:
            self.stop()

        self.config["source"] = {"type": source_type, "path": path}
        if was_running:
            self.start()

    def start(self) -> bool:
        """Starts video capture and inference worker thread."""
        if self.running:
            return True

        src_cfg = self.config.get("source", {})
        source_path = src_cfg.get("path", "data/samples/demo.mp4")
        if isinstance(source_path, str) and not os.path.isabs(source_path) and not source_path.isdigit():
            abs_source = os.path.join(PROJECT_ROOT, source_path)
            if os.path.exists(abs_source):
                source_path = abs_source
        queue_size = int(self.config.get("api", {}).get("buffer_queue_size", 2))
        loop = bool(src_cfg.get("loop", True))

        self.grabber = FrameGrabber(source=source_path, queue_size=queue_size, loop=loop)
        if not self.grabber.start():
            logger.error(f"Failed to start FrameGrabber for {source_path}")
            return False

        self.running = True
        self.paused = False
        self.worker_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.worker_thread.start()
        logger.info("ADAS Pipeline started.")
        return True

    def stop(self):
        """Stops the inference pipeline and frees frame grabber resources."""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
        if self.grabber:
            self.grabber.stop()
            self.grabber = None
        logger.info("ADAS Pipeline stopped.")

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def process_single_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Runs one full cycle of perception, fusion, overlay, and serialization."""
        t_start = time.perf_counter()

        # 1. Pedestrian Detection & Tracking
        self.profiler.start("pedestrian")
        pedestrians, danger_zone = self.pedestrian_module.process(frame)
        self.profiler.stop("pedestrian")

        # 2. Lane Marking Detection
        self.profiler.start("lanes")
        lane_result = self.lane_module.process(frame)
        self.profiler.stop("lanes")

        # 3. Road Sign Localization & Classification
        self.profiler.start("signs")
        detected_signs, last_speed_limit = self.sign_module.process(frame)
        self.profiler.stop("signs")

        # 4. Fusion and Decision Engine
        self.profiler.start("fusion")
        alerts = self.fusion_engine.process(pedestrians, lane_result, detected_signs)
        self.profiler.stop("fusion")

        # 5. Visualizer Overlay & HUD
        self.profiler.start("overlay")
        fps = self.fps_tracker.tick()
        annotated_frame = self.visualizer.draw(
            frame=frame,
            pedestrians=pedestrians,
            lane=lane_result,
            signs=detected_signs,
            danger_zone=danger_zone,
            fps=fps,
            alerts=alerts,
            last_speed_limit=last_speed_limit,
        )
        self.profiler.stop("overlay")

        total_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.profiler.record("total", total_elapsed_ms)

        jpeg_quality = int(self.config.get("api", {}).get("jpeg_quality", 75))
        base64_frame = frame_to_base64(annotated_frame, quality=jpeg_quality)

        result = {
            "frame": f"data:image/jpeg;base64,{base64_frame}",
            "fps": fps,
            "pedestrians": [p.to_dict() for p in pedestrians],
            "signs": [s.to_dict() for s in detected_signs],
            "lane": lane_result.to_dict(),
            "alerts": [a.to_dict() for a in alerts],
            "last_speed_limit": last_speed_limit,
            "metrics": self.profiler.get_summary(),
            "timestamp": time.time(),
        }
        self._latest_result = result
        return result

    def _inference_loop(self):
        """Worker loop continuously pulling latest frames from grabber and running perception."""
        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue

            if not self.grabber:
                time.sleep(0.05)
                continue

            ret, frame = self.grabber.read(timeout=0.2)
            if not ret or frame is None:
                continue

            try:
                result = self.process_single_frame(frame)
                # Dispatch result to subscribers
                for cb in list(self._frame_callbacks):
                    try:
                        cb(result)
                    except Exception as e:
                        logger.warning(f"Error in frame callback: {e}")
            except Exception as e:
                logger.error(f"Error during ADAS pipeline execution: {e}")
