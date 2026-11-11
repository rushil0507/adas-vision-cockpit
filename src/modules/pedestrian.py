"""Pedestrian Detection and Tracking Module with ByteTrack and Risk Assessment."""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import logging
import numpy as np

from src.utils.geometry import (
    point_in_polygon,
    scale_polygon,
    calculate_pinhole_distance,
    calculate_centroid,
    calculate_bottom_center,
    calculate_velocity,
)

logger = logging.getLogger(__name__)


@dataclass
class PedestrianTrack:
    """State of an individual tracked pedestrian across frames."""

    track_id: int
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float
    centroid_history: deque = field(default_factory=lambda: deque(maxlen=30))
    age: int = 1
    last_frame_idx: int = 0
    distance_m: float = 999.0
    proximity_ratio: float = 0.0
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (dx, dy, speed)
    in_danger_zone: bool = False
    risk: str = "LOW"  # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.track_id,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 2),
            "distance_m": round(self.distance_m, 1),
            "proximity_ratio": round(self.proximity_ratio, 3),
            "velocity_px": [round(self.velocity[0], 2), round(self.velocity[1], 2)],
            "speed_px": round(self.velocity[2], 2),
            "in_danger_zone": self.in_danger_zone,
            "risk": self.risk,
            "age": self.age,
        }


class PedestrianModule:
    """Detects and tracks pedestrians, computes kinematics, and assesses safety risk levels."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("pedestrian", {})
        self.weights = self.config.get("weights", "yolov8n.pt")
        self.conf_thresh = float(self.config.get("conf", 0.40))
        self.iou_thresh = float(self.config.get("iou", 0.45))
        self.tracker_cfg = self.config.get("tracker", "bytetrack.yaml")
        self.persist = bool(self.config.get("persist", True))

        self.focal_length_px = float(self.config.get("focal_length_px", 800.0))
        self.real_height_m = float(self.config.get("real_height_m", 1.70))
        self.risk_distance_medium_m = float(self.config.get("risk_distance_medium_m", 18.0))
        self.risk_distance_high_m = float(self.config.get("risk_distance_high_m", 8.0))
        self.approach_velocity_px = float(self.config.get("approach_velocity_px", 1.5))

        self.danger_zone_base = self.config.get(
            "danger_zone",
            [[220, 720], [520, 440], [760, 440], [1060, 720]],
        )

        self.model = None
        self.tracks: Dict[int, PedestrianTrack] = {}
        self.frame_count = 0
        self._init_model()

    def _init_model(self):
        """Loads YOLOv8 model."""
        try:
            from ultralytics import YOLO

            logger.info(f"Loading Pedestrian YOLO model from {self.weights}...")
            self.model = YOLO(self.weights)
            logger.info("YOLO model successfully loaded.")
        except Exception as e:
            logger.warning(f"Could not load YOLO model ({e}). Will run in fallback/mock mode if needed.")
            self.model = None

    def update_config(self, new_cfg: Dict[str, Any]):
        """Dynamically update thresholds at runtime."""
        if "conf" in new_cfg:
            self.conf_thresh = float(new_cfg["conf"])
        if "risk_distance_high_m" in new_cfg:
            self.risk_distance_high_m = float(new_cfg["risk_distance_high_m"])
        if "danger_zone" in new_cfg:
            self.danger_zone_base = new_cfg["danger_zone"]

    def process(self, frame: np.ndarray) -> Tuple[List[PedestrianTrack], List[List[int]]]:
        """
        Executes detection, tracking, and risk assessment on a frame.
        Returns:
            (active_tracks, scaled_danger_zone)
        """
        self.frame_count += 1
        h, w = frame.shape[:2]
        scaled_danger_zone = scale_polygon(self.danger_zone_base, 1280.0, 720.0, float(w), float(h))

        active_tracks: List[PedestrianTrack] = []

        if self.model is None:
            # Fallback when model is not available
            return active_tracks, scaled_danger_zone

        try:
            # Run tracker with person class (COCO class 0)
            results = self.model.track(
                frame,
                persist=self.persist,
                tracker=self.tracker_cfg,
                classes=[0],  # class 0: person
                conf=self.conf_thresh,
                iou=self.iou_thresh,
                verbose=False,
            )

            if results and len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    # Bounding box coordinates [x1, y1, x2, y2]
                    xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
                    conf = float(box.conf[0].cpu().numpy())
                    track_id = int(box.id[0].cpu().numpy()) if box.id is not None else -1

                    if track_id == -1:
                        # Unassigned detection
                        continue

                    # Centroid and bottom-center contact point
                    cx, cy = calculate_centroid(xyxy)
                    bc_x, bc_y = calculate_bottom_center(xyxy)

                    bbox_h = max(1, xyxy[3] - xyxy[1])
                    dist_m = calculate_pinhole_distance(bbox_h, self.real_height_m, self.focal_length_px)
                    proximity_ratio = bbox_h / float(h)

                    # Update or create track
                    if track_id in self.tracks:
                        track = self.tracks[track_id]
                        track.bbox = xyxy
                        track.confidence = conf
                        track.age += 1
                        track.last_frame_idx = self.frame_count
                        track.distance_m = dist_m
                        track.proximity_ratio = proximity_ratio
                        track.centroid_history.append((cx, cy))
                    else:
                        track = PedestrianTrack(
                            track_id=track_id,
                            bbox=xyxy,
                            confidence=conf,
                            age=1,
                            last_frame_idx=self.frame_count,
                            distance_m=dist_m,
                            proximity_ratio=proximity_ratio,
                        )
                        track.centroid_history.append((cx, cy))
                        self.tracks[track_id] = track

                    # Velocity calculation (dx, dy, speed)
                    track.velocity = calculate_velocity(list(track.centroid_history))

                    # Danger zone check
                    in_zone = point_in_polygon((bc_x, bc_y), scaled_danger_zone)
                    track.in_danger_zone = in_zone

                    # Risk assessment:
                    # LOW: Outside danger zone or far away (> medium threshold)
                    # MEDIUM: Inside danger zone and within medium threshold
                    # HIGH: Inside danger zone and within high threshold OR approaching fast (dy > approach_velocity_px)
                    dy = track.velocity[1]
                    if not in_zone:
                        track.risk = "LOW"
                    else:
                        if dist_m <= self.risk_distance_high_m:
                            track.risk = "HIGH"
                        elif dy > self.approach_velocity_px and dist_m <= self.risk_distance_medium_m:
                            track.risk = "HIGH"
                        else:
                            track.risk = "MEDIUM"

                    active_tracks.append(track)

            # Clean up old tracks unseen for > 30 frames
            expired = [t_id for t_id, tr in self.tracks.items() if self.frame_count - tr.last_frame_idx > 30]
            for t_id in expired:
                del self.tracks[t_id]

        except Exception as e:
            logger.error(f"Error in PedestrianModule inference: {e}")

        return active_tracks, scaled_danger_zone

