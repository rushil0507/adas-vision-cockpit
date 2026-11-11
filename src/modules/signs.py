"""Road Sign Localization and Classification Module with Temporal Smoothing."""

from collections import Counter, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import os
import logging
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# Complete GTSRB 43 Classes mapping
GTSRB_CLASSES = [
    "Speed limit (20km/h)",
    "Speed limit (30km/h)",
    "Speed limit (50km/h)",
    "Speed limit (60km/h)",
    "Speed limit (70km/h)",
    "Speed limit (80km/h)",
    "End speed limit (80km/h)",
    "Speed limit (100km/h)",
    "Speed limit (120km/h)",
    "No passing",
    "No passing vehicles > 3.5t",
    "Right-of-way at intersection",
    "Priority road",
    "Yield",
    "Stop",
    "No vehicles",
    "Vehicles > 3.5t prohibited",
    "No entry",
    "General caution",
    "Dangerous curve left",
    "Dangerous curve right",
    "Double curve",
    "Bumpy road",
    "Slippery road",
    "Road narrows on right",
    "Road work",
    "Traffic signals",
    "Pedestrians crossing",
    "Children crossing",
    "Bicycles crossing",
    "Beware of ice/snow",
    "Wild animals crossing",
    "End of all limits",
    "Turn right ahead",
    "Turn left ahead",
    "Ahead only",
    "Go straight or right",
    "Go straight or left",
    "Keep right",
    "Keep left",
    "Roundabout mandatory",
    "End of no passing",
    "End of no passing > 3.5t",
]


class TrafficSignCNN(nn.Module):
    """Compact and fast CNN architecture for 43-class GTSRB sign classification."""

    def __init__(self, num_classes: int = 43):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.pool1 = nn.MaxPool2d(2, 2)

        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool2 = nn.MaxPool2d(2, 2)

        self.fc1 = nn.Linear(128 * 12 * 12, 256)
        self.dropout = nn.Dropout(0.4)
        self.fc2 = nn.Linear(256, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input: (B, 3, 48, 48)
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.pool1(F.relu(self.bn2(self.conv2(x))))  # (B, 64, 24, 24)
        x = self.pool2(F.relu(self.bn3(self.conv3(x))))  # (B, 128, 12, 12)
        x = x.reshape(x.size(0), -1)
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        return x


@dataclass
class DetectedSign:
    """Detection & classification representation for a road sign."""

    bbox: List[int]
    label: str
    confidence: float
    is_speed_limit: bool = False
    speed_value: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "label": self.label,
            "conf": round(self.confidence, 2),
            "is_speed_limit": self.is_speed_limit,
            "speed_value": self.speed_value,
        }


class RoadSignModule:
    """Road sign localization, CNN classification, and temporal majority-vote smoothing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("signs", {})
        self.det_weights = self.config.get("detector", "weights/sign_det.pt")
        self.cls_weights = self.config.get("classifier", "weights/sign_cls.pt")
        self.conf_thresh = float(self.config.get("conf", 0.50))
        self.iou_thresh = float(self.config.get("iou", 0.45))
        self.smooth_frames = int(self.config.get("smooth_frames", 5))
        self.crop_size = tuple(self.config.get("crop_size", [48, 48]))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.last_speed_limit: Optional[int] = None
        self.tracked_signs: List[Dict[str, Any]] = []  # [{bbox, history: deque, label, conf}]
        self.detector = None
        self.classifier = None
        self.fallback_mode = False

        self._init_models()

    def _init_models(self):
        """Loads detector and classifier, falling back to COCO YOLO or classical locator."""
        from ultralytics import YOLO

        # 1. Detector
        if os.path.exists(self.det_weights):
            try:
                logger.info(f"Loading custom sign detector: {self.det_weights}")
                self.detector = YOLO(self.det_weights)
            except Exception as e:
                logger.warning(f"Failed to load custom sign detector ({e}), loading yolov8n.pt fallback.")
                self.detector = YOLO("yolov8n.pt")
                self.fallback_mode = True
        else:
            logger.info("Custom sign detector not found, using YOLOv8 COCO detector as fallback.")
            self.detector = YOLO("yolov8n.pt")
            self.fallback_mode = True

        # 2. Classifier
        self.classifier = TrafficSignCNN(num_classes=len(GTSRB_CLASSES)).to(self.device)
        if os.path.exists(self.cls_weights):
            try:
                state_dict = torch.load(self.cls_weights, map_location=self.device)
                self.classifier.load_state_dict(state_dict)
                self.classifier.eval()
                logger.info(f"Loaded sign classifier weights from {self.cls_weights}")
            except Exception as e:
                logger.warning(f"Could not load classifier weights ({e}).")
        else:
            self.classifier.eval()

    def update_config(self, new_cfg: Dict[str, Any]):
        if "conf" in new_cfg:
            self.conf_thresh = float(new_cfg["conf"])
        if "smooth_frames" in new_cfg:
            self.smooth_frames = int(new_cfg["smooth_frames"])

    def _extract_speed_limit(self, label: str) -> Optional[int]:
        """Extracts integer speed from label string (e.g. 'Speed limit (50km/h)' -> 50)."""
        if "Speed limit" in label:
            for part in label.split():
                clean = part.strip("()km/h")
                if clean.isdigit():
                    return int(clean)
        return None

    def _classify_crop(self, crop: np.ndarray) -> Tuple[str, float]:
        """Runs CNN on sign image crop."""
        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            return "Unknown", 0.0

        resized = cv2.resize(crop, self.crop_size)
        # Convert BGR to RGB and normalize to [0, 1]
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        # Standard PyTorch normalization
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.classifier(tensor)
            probs = F.softmax(outputs, dim=1)[0]
            cls_idx = int(torch.argmax(probs).cpu().numpy())
            conf = float(probs[cls_idx].cpu().numpy())

        if 0 <= cls_idx < len(GTSRB_CLASSES):
            return GTSRB_CLASSES[cls_idx], conf
        return "Sign", conf

    def _match_track(self, bbox: List[int]) -> int:
        """Finds closest tracked sign by bbox overlap."""
        best_iou = 0.0
        best_idx = -1
        x1, y1, x2, y2 = bbox

        for idx, tr in enumerate(self.tracked_signs):
            tx1, ty1, tx2, ty2 = tr["bbox"]
            xx1 = max(x1, tx1)
            yy1 = max(y1, ty1)
            xx2 = min(x2, tx2)
            yy2 = min(y2, ty2)

            w = max(0, xx2 - xx1)
            h = max(0, yy2 - yy1)
            inter = w * h
            area1 = (x2 - x1) * (y2 - y1)
            area2 = (tx2 - tx1) * (ty2 - ty1)
            union = area1 + area2 - inter

            iou = inter / max(1.0, union)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx

        if best_iou > 0.30:
            return best_idx
        return -1

    def process(self, frame: np.ndarray) -> Tuple[List[DetectedSign], Optional[int]]:
        """Detects and classifies road signs in the frame."""
        h, w = frame.shape[:2]
        raw_detections: List[Tuple[List[int], str, float]] = []

        if self.detector is not None:
            try:
                if self.fallback_mode:
                    # In fallback COCO mode, look for Stop sign (11) and Traffic light (9)
                    results = self.detector(
                        frame,
                        classes=[9, 11],
                        conf=self.conf_thresh,
                        iou=self.iou_thresh,
                        verbose=False,
                    )
                else:
                    results = self.detector(
                        frame,
                        conf=self.conf_thresh,
                        iou=self.iou_thresh,
                        verbose=False,
                    )

                if results and len(results) > 0 and results[0].boxes is not None:
                    for box in results[0].boxes:
                        xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
                        conf = float(box.conf[0].cpu().numpy())
                        cls_id = int(box.cls[0].cpu().numpy())

                        # Crop and classify if two-stage pipeline or classify based on fallback
                        if not self.fallback_mode and os.path.exists(self.cls_weights):
                            crop = frame[max(0, xyxy[1]) : min(h, xyxy[3]), max(0, xyxy[0]) : min(w, xyxy[2])]
                            label, cls_conf = self._classify_crop(crop)
                            conf = (conf + cls_conf) / 2.0
                        else:
                            if cls_id == 11:
                                label = "Stop"
                            elif cls_id == 9:
                                label = "Traffic signals"
                            elif cls_id < len(GTSRB_CLASSES):
                                label = GTSRB_CLASSES[cls_id]
                            else:
                                label = "Road Sign"

                        raw_detections.append((xyxy, label, conf))
            except Exception as e:
                logger.error(f"Error during sign detection: {e}")

        # Temporal majority-vote smoothing
        current_detected_signs: List[DetectedSign] = []
        for bbox, label, conf in raw_detections:
            match_idx = self._match_track(bbox)
            if match_idx >= 0:
                tr = self.tracked_signs[match_idx]
                tr["bbox"] = bbox
                tr["history"].append(label)
                tr["conf"] = conf
                # Majority vote over history
                smoothed_label = Counter(tr["history"]).most_common(1)[0][0]
            else:
                hist = deque(maxlen=self.smooth_frames)
                hist.append(label)
                self.tracked_signs.append({"bbox": bbox, "history": hist, "conf": conf})
                smoothed_label = label

            speed_val = self._extract_speed_limit(smoothed_label)
            is_speed = speed_val is not None
            if is_speed and conf >= 0.60:
                self.last_speed_limit = speed_val

            current_detected_signs.append(
                DetectedSign(
                    bbox=bbox,
                    label=smoothed_label,
                    confidence=conf,
                    is_speed_limit=is_speed,
                    speed_value=speed_val,
                )
            )

        # Prune old tracks
        if len(self.tracked_signs) > 20:
            self.tracked_signs = self.tracked_signs[-10:]

        return current_detected_signs, self.last_speed_limit

